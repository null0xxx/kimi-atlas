"""Per-test-id suite runner for the ATLAS-WEAVE INTEGRATE sink (I/O hand).

`parse_junit` is the PURE core (unit-tested without subprocess): it turns a JUnit
XML string into ``{test_id: status}`` where a green testcase is EXACTLY the
lowercase token ``"pass"`` — the contract `differential.regressions` relies on
(any other spelling is treated as a regression). `run_suite` is the subprocess
"hand": it shells a command that writes JUnit, reads the file, and delegates to
`parse_junit`.

Fail-safe by construction: every parse/subprocess/timeout failure degrades to an
EMPTY dict. An empty combined-suite keeps the caller's ``baseline_pass``
conservative (a baseline-green test absent from ``combined`` reads as a
regression), so a broken runner can never manufacture a false green.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

# A JUnit ``<testcase>`` child tag → the status token we emit. Anything with none
# of these children is green and maps to the literal ``"pass"``.
_CHILD_STATUS = {"failure": "fail", "error": "error", "skipped": "skip"}


def _localname(tag: str) -> str:
    """Strip any XML namespace (``{ns}tag`` → ``tag``)."""
    return tag.rsplit("}", 1)[-1]


def parse_junit(xml_text: str) -> dict:
    """Parse a JUnit XML string → ``{test_id: status}`` (pure, fail-safe).

    ``test_id = f"{classname}::{name}"`` (or the bare ``name`` when there is no
    non-empty classname). ``status`` is exactly ``"pass"`` when the ``<testcase>``
    has no ``<failure>``/``<error>``/``<skipped>`` child, else ``"fail"``,
    ``"error"``, or ``"skip"``. Malformed/empty XML degrades to ``{}``.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}
    except Exception:  # defence-in-depth: any parser surprise degrades safe
        return {}

    results: dict = {}
    for tc in root.iter():
        if _localname(tc.tag) != "testcase":
            continue
        name = tc.get("name")
        if not name:
            continue  # a testcase without a name has no addressable id — skip it
        classname = tc.get("classname")
        test_id = f"{classname}::{name}" if classname else name

        status = "pass"
        for child in tc:
            mapped = _CHILD_STATUS.get(_localname(child.tag))
            if mapped is not None:
                status = mapped
                break
        results[test_id] = status
    return results


def run_suite(cmd: str, cwd: str, timeout_s: int = 1800) -> dict:
    """Shell ``cmd`` so it writes JUnit, then parse it (I/O hand, fail-safe).

    A ``{junit}`` placeholder in ``cmd`` is substituted with the JUnit output path
    (for commands that already know how to write JUnit); otherwise
    ``--junit-xml=<path>`` is appended (the pytest convention). The command's exit
    status is intentionally ignored — pytest exits non-zero on failing tests but
    still writes the report — the report file is the source of truth. Any
    subprocess/timeout/read failure degrades to ``{}``.
    """
    fd, junit_path = tempfile.mkstemp(suffix=".xml", prefix="suiterun-")
    os.close(fd)
    try:
        if "{junit}" in cmd:
            full = cmd.replace("{junit}", junit_path)
        else:
            full = f"{cmd} --junit-xml={junit_path}"

        try:
            subprocess.run(
                full,
                shell=True,
                cwd=cwd,
                timeout=timeout_s,
                capture_output=True,
            )
        except (subprocess.SubprocessError, OSError):
            return {}

        try:
            with open(junit_path, "r", encoding="utf-8") as fh:
                xml_text = fh.read()
        except OSError:
            return {}
        return parse_junit(xml_text)
    finally:
        try:
            os.remove(junit_path)
        except OSError:
            pass
