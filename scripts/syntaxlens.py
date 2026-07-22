"""syntaxlens — language dispatch + in-process config parse → canonical defects.

The **sole** consumer of :mod:`scripts.nativefloor` and the last stage of the
universal SYNTAX floor (spec §2.5/§2.9). It turns the reviewed ``{path: text}``
map into the canonical ``{id, category, severity, location, fix}`` defect shape
the backbone merges identically to an ``astlens``/``sast`` defect. A thin I/O
"hand": the ONE side effect (running a real parse checker) is delegated to
``nativefloor``; the only other I/O is a fail-safe read of the nearest
``package.json`` to resolve node's ESM/CJS ``type``. Every classification below is
a pure decision over the file's basename/extension.

Two dispositions, decided per changed file (config is checked FIRST — a
``.json``/``.toml`` is config, not source):

1. **Config (in-process, NO subprocess).** Only a file whose *basename* is in
   :data:`_STRICT_CONFIG` — a format that is GUARANTEED strict JSON/TOML, so a
   parse failure is a real syntax error — is parsed for BLOCKING. A parse failure
   is a HIGH ``DOES-IT-RUN`` defect (``id="config-<basename>"``); valid → no
   defect. The parse is byte-bounded (oversize → not parsed) and guarded against
   ``ValueError``/``RecursionError``/``MemoryError`` (``tomllib.TOMLDecodeError``
   is a ``ValueError`` subclass). Every OTHER ``.json``/``.toml`` — ``tsconfig.json``
   (JSONC: comments + trailing commas), ``yarn.lock``/``Gemfile.lock``/opaque
   lockfiles, arbitrary data files — is NEVER parsed for blocking (skipped). This
   is the corrected policy: the plan-challenge proved that blocking on
   ``tsconfig.json`` + bare ``*.lock`` false-rejects valid repos.

2. **Source (ext in :data:`langfloor.SYNTAX_ARGV`).** One ``nativefloor`` job is
   built and dispatched. A ``signature_matched=True`` result → HIGH
   ``DOES-IT-RUN`` blocking defect; ``ran=False`` or ``signature_matched=False``
   → no defect (fail-open, per nativefloor's contract). node ESM/CJS mode is
   carried by the MATERIALIZED extension (the hermetic tempdir has no
   ``package.json``): ``.mjs``/``.cjs`` materialize as themselves; a ``.js`` file
   materializes as ``.mjs`` iff :func:`_nearest_package_type` resolves to
   ``"module"`` (making the resolved type load-bearing — it picks the ext), else
   ``.js`` (CJS default). ``.jsx``/``.ts``/``.tsx`` have NO ``SYNTAX_ARGV`` entry
   (``node --check`` cannot parse JSX/TS) so they are never dispatched and never a
   defect.

A file is EITHER config (strict basename, or a non-strict ``.json``/``.toml`` →
skip) OR source (ext in ``SYNTAX_ARGV``). ``SYNTAX_ARGV`` has no ``.json``/
``.toml`` entry, so there is no double-dispatch. Defects are returned sorted by
``location`` for determinism.
"""
from __future__ import annotations

import json
import os
import tomllib

from scripts import langfloor, nativefloor

_DOES_IT_RUN = "DOES-IT-RUN"

# Basename -> parser, for config files whose format is GUARANTEED, so a parse
# failure is a real syntax error and BLOCKS. Everything NOT in this map
# (tsconfig.json = JSONC with comments; yarn.lock/Gemfile.lock/pnpm-lock = opaque;
# arbitrary *.json/*.toml data) is advisory at most (skipped for blocking). This
# CORRECTS blueprint §2.9's file list (the plan-challenge proved tsconfig.json +
# bare *.lock false-block valid repos); §2.9's intent (invalid config blocks,
# invalid data advises) is preserved.
_STRICT_CONFIG: dict[str, str] = {
    "package.json": "json", "composer.json": "json",
    "package-lock.json": "json", "composer.lock": "json",
    "pyproject.toml": "toml", "Cargo.toml": "toml",
    "Cargo.lock": "toml", "poetry.lock": "toml",
}

# Byte bound for an in-process config parse (mirrors nativefloor's source cap): a
# config larger than this is not parsed for blocking (advisory at most).
_CONFIG_MAX_BYTES = 1_000_000


def _d(did: str, category: str, severity: str, location: str, fix: str) -> dict:
    """Build one defect in the canonical ``{id, category, severity, location, fix}`` shape."""
    return {"id": did, "category": category, "severity": severity,
            "location": location, "fix": fix}


def _read_package_type(path: str) -> str | None:
    """Return the ``"type"`` string of the ``package.json`` at ``path``, else None.

    Fail-safe: a missing/unreadable file (``OSError``) or malformed JSON
    (``ValueError``) is treated as absent, as is a non-object root or a non-string
    (or absent) ``type``. Pure-ish: reads one file, no other effect.
    """
    try:
        with open(path, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict):
        value = data.get("type")
        if isinstance(value, str):
            return value
    return None


def _nearest_package_type(rel: str, cwd: str) -> str | None:
    """Walk up from ``dirname(rel)`` to ``cwd`` for the nearest ``package.json`` ``type``.

    Resolves node's ESM/CJS mode the way node itself does — the closest enclosing
    ``package.json`` wins. Starts at the directory containing ``rel`` and reads
    each ``package.json`` fail-safe (:func:`_read_package_type`); the first that
    declares a string ``type`` returns it. Terminates at ``cwd`` (never reads
    above it for an in-tree ``rel``) and is bounded at the filesystem root, so it
    never loops. Returns ``None`` when no enclosing package declares a ``type``.
    """
    cwd_abs = os.path.abspath(cwd)
    cur = os.path.abspath(os.path.join(cwd_abs, os.path.dirname(rel)))
    while True:
        found = _read_package_type(os.path.join(cur, "package.json"))
        if found is not None:
            return found
        if cur == cwd_abs:
            return None
        parent = os.path.dirname(cur)
        if parent == cur:  # filesystem root — stop (bounds a pathological ``../`` rel)
            return None
        cur = parent


def _materialize_ext(ext: str, rel: str, cwd: str) -> str:
    """Choose the extension ``nativefloor`` materializes a source file under (pure-ish).

    node mode MUST be carried by the on-disk extension (the hermetic tempdir has
    no ``package.json``): ``.mjs``/``.cjs`` keep their explicit mode; a bare
    ``.js`` becomes ``.mjs`` iff the nearest ``package.json`` ``type`` is
    ``"module"`` (ESM), else ``.js`` (CJS default). Every non-node source ext
    (``.rb``/``.php``/``.go``/``.sh``/``.bash``) materializes under its own ext.
    Resolving the ``.js`` case is the one place ``_nearest_package_type`` becomes
    load-bearing — it literally picks the extension.
    """
    if ext == ".mjs":
        return ".mjs"
    if ext == ".cjs":
        return ".cjs"
    if ext == ".js":
        return ".mjs" if _nearest_package_type(rel, cwd) == "module" else ".js"
    return ext


def _config_defect(basename: str, location: str, parser: str, text: str) -> dict | None:
    """Return a BLOCKING defect if a STRICT config fails to parse, else ``None`` (pure).

    ``location`` is the real changed-files path (``rel``), so two same-named
    configs in different dirs report distinct locations; ``id`` stays the
    spec-mandated ``config-<basename>``. A non-``str`` ``text`` (contract is
    ``dict[str, str]``; defensive) is skipped — never raised — so a malformed
    entry degrades rather than crashing the VERIFIED lens.

    Byte-bounded: a config larger than :data:`_CONFIG_MAX_BYTES` is NOT parsed
    (advisory at most → no defect). For JSON, a single leading UTF-8 BOM is
    stripped before parsing — npm and node's loader strip it and accept the file,
    so a BOM-prefixed valid ``package.json`` must NOT false-block. (The TOML branch
    does NOT strip: ``tomllib`` rejecting a BOM matches cargo/tomllib behavior, so
    that is correct, not a false-block.) The parse (``json.loads`` /
    ``tomllib.loads``) is guarded against ``ValueError`` (covers
    ``json.JSONDecodeError`` and ``tomllib.TOMLDecodeError``, both subclasses),
    ``RecursionError``, and ``MemoryError``; any of those → a HIGH ``DOES-IT-RUN``
    defect. Valid → ``None``.
    """
    if not isinstance(text, str):
        return None
    if len(text.encode("utf-8", errors="replace")) > _CONFIG_MAX_BYTES:
        return None
    try:
        if parser == "json":
            # npm/node strip a single leading BOM and accept the file; match that
            # so a BOM-prefixed valid package.json never false-blocks.
            json.loads(text[1:] if text.startswith("﻿") else text)
        else:  # "toml"
            tomllib.loads(text)
    except (ValueError, RecursionError, MemoryError) as exc:
        return _d(
            f"config-{basename}", _DOES_IT_RUN, "HIGH", location,
            f"{basename} is not valid {parser.upper()} ({exc}); the build cannot "
            f"read it, so nothing downstream can run — fix the syntax error.",
        )
    return None


def check(changed_files: dict[str, str], cwd: str) -> list[dict]:
    """Classify the changed files into canonical defects, sorted by ``location``.

    Config files (basename in :data:`_STRICT_CONFIG`) are parsed in-process for
    blocking; every other ``.json``/``.toml`` is skipped (never blocked). Source
    files (ext in :data:`langfloor.SYNTAX_ARGV`) are dispatched to
    :func:`nativefloor.run` as one batch — the single side effect — and a
    ``signature_matched`` result becomes a HIGH ``DOES-IT-RUN`` defect;
    ``ran=False``/``signature_matched=False`` is fail-open (no defect). ``cwd`` is
    the review root, used only to resolve node's nearest-``package.json`` ``type``.
    """
    defects: list[dict] = []
    source_jobs: list[dict] = []

    for rel, text in changed_files.items():
        basename = os.path.basename(rel)
        ext = os.path.splitext(basename)[1].lower()

        # 1) Config FIRST — a .json/.toml is config, not source.
        if basename in _STRICT_CONFIG:
            defect = _config_defect(basename, rel, _STRICT_CONFIG[basename], text)
            if defect is not None:
                defects.append(defect)
            continue
        # A non-strict .json/.toml (tsconfig.json / *.lock / arbitrary data) is
        # NEVER parsed for blocking — this is the fix for the four CRITICAL
        # false-blocks. SYNTAX_ARGV has no .json/.toml entry, so this also prevents
        # any double-dispatch.
        if ext in (".json", ".toml"):
            continue

        # 2) Source — dispatch only exts nativefloor has a parse checker for. Every
        # other ext (.jsx/.ts/.tsx and any non-source file) has no SYNTAX_ARGV
        # entry -> never dispatched, never a defect.
        argv = langfloor.SYNTAX_ARGV.get(ext)
        if argv is None:
            continue
        source_jobs.append({
            "rel": rel,
            "text": text,
            "argv": argv,
            "ext": _materialize_ext(ext, rel, cwd),
        })

    # The one side effect: run every source job hermetically in a single batch.
    if source_jobs:
        results = nativefloor.run(source_jobs)
        for job, result in zip(source_jobs, results):
            if result.get("signature_matched"):
                rel = job["rel"]
                src_ext = os.path.splitext(os.path.basename(rel))[1].lower().lstrip(".")
                tool = (job["argv"] or [""])[0]
                defects.append(_d(
                    f"syntax-{src_ext}", _DOES_IT_RUN, "HIGH", rel,
                    f"{tool} reported a syntax error; the file cannot be parsed, so "
                    f"it cannot be imported or run — fix the syntax error.",
                ))

    defects.sort(key=lambda defect: defect["location"])
    return defects
