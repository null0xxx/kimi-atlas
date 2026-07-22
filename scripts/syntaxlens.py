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
   is a HIGH ``DOES-IT-RUN`` defect (``id="SYN<n>-config-<basename>"``, the
   ``SYN<n>-`` prefix minted per-file-unique after sorting); valid → no defect. The parse is byte-bounded (oversize → not parsed) and guarded against
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


# A single leading UTF-8 BOM; npm and node's JSON loader strip it and accept the file.
_BOM = "﻿"


def _loads_json_bom(text: str):
    """``json.loads`` after stripping a single leading UTF-8 BOM (npm/node parity).

    The ONE JSON-parse entry point BOTH config paths share — ``_read_package_type``
    (the on-disk ``package.json`` ``type``) and :func:`_config_defect` (a strict
    JSON config) — so their BOM handling can never drift again. npm/node strip a
    leading BOM and accept the file, so a valid BOM-prefixed ``package.json`` must
    never be misread as type-absent (which would degrade ESM→CJS and latently
    false-block on node 18/20) nor blocked as invalid config. Raises ``ValueError``
    (``json.JSONDecodeError``) exactly like ``json.loads`` on malformed input; each
    caller guards/interprets that raise. Pure.
    """
    return json.loads(text[1:] if text.startswith(_BOM) else text)


def _read_package_type(path: str) -> str | None:
    """Return the ``"type"`` string of the ``package.json`` at ``path``, else None.

    Fail-safe AND bounded, because ``path`` is read straight from the UNTRUSTED
    repo tree (reached via :func:`_nearest_package_type` for any changed ``.js``):

    * ``os.path.isfile(path)`` is checked FIRST. It follows the ``package.json``
      symlink to its target, so a link that points at ``/dev/zero`` (a character
      device — an unbounded read that would HANG ``check()``), a FIFO, a directory,
      or a dangling link is all rejected up front → ``None``. Only a real regular
      file is ever opened.
    * The read is capped at :data:`_CONFIG_MAX_BYTES` (the same byte cap the config
      parse uses), so a genuinely huge regular ``package.json`` can never exhaust
      memory — at most the cap is read (an over-cap file is then almost always
      invalid-truncated JSON → treated as absent, never a raise).

    A single leading UTF-8 BOM is stripped before parsing (npm/node parity, via
    :func:`_loads_json_bom`) so a BOM-prefixed ``{"type":"module"}`` still resolves
    to ``"module"`` (ESM) rather than being misread as type-absent.

    A missing/unreadable file (``OSError``), malformed JSON (``ValueError``), or a
    pathological input (``MemoryError``/``RecursionError``) is treated as absent, as
    is a non-object root or a non-string (or absent) ``type``. This is what makes
    the guarantee "``check()`` NEVER hangs or raises on any repo input" hold along
    the ESM/CJS resolution path. Pure-ish: reads one file (bounded), no other effect.
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_CONFIG_MAX_BYTES)
        data = _loads_json_bom(raw.decode("utf-8", errors="replace"))
    except (OSError, ValueError, MemoryError, RecursionError):
        return None
    if isinstance(data, dict):
        value = data.get("type")
        if isinstance(value, str):
            return value
    return None


def _nearest_package_type(rel: str, cwd: str) -> str | None:
    """Walk up from ``dirname(rel)`` for the NEAREST ``package.json``, mirroring node.

    Resolves node's ESM/CJS mode EXACTLY the way node itself does: resolution stops
    at the nearest enclosing ``package.json`` — that file is authoritative and the
    walk NEVER inherits an ancestor's ``type``. At each directory:

    * ``package.json`` PRESENT (``os.path.isfile``) → its type decides and the walk
      STOPS here. ``"type":"module"`` → return ``"module"`` (ESM); a present file
      that is type-less, ``"type":"commonjs"``, malformed, or unreadable →
      :func:`_read_package_type` returns ``None`` and we return that ``None`` (CJS,
      node's default) — crucially WITHOUT climbing to an ancestor.
    * ``package.json`` ABSENT → continue to the parent directory.

    This ``os.path.isfile`` presence check in the CALLER is what distinguishes
    "present-but-type-less" (stop → CJS) from "absent" (keep climbing); the old code
    conflated both as ``_read_package_type``'s ``None`` and wrongly kept climbing,
    inheriting an ancestor ``type:module`` and false-blocking valid sloppy-CJS
    ``.js`` (e.g. ``var x = 0777;``) materialized as ``.mjs``. ``os.path.isfile``
    follows a symlink to its target, so a ``package.json`` pointing at ``/dev/zero``
    (a char device) reads as absent and is skipped — no hang. Terminates at ``cwd``
    (never reads above it for an in-tree ``rel``) and is bounded at the filesystem
    root, so it never loops. Returns ``None`` (→ CJS default) when no enclosing
    ``package.json`` selects ESM.
    """
    cwd_abs = os.path.abspath(cwd)
    cur = os.path.abspath(os.path.join(cwd_abs, os.path.dirname(rel)))
    while True:
        pkg = os.path.join(cur, "package.json")
        if os.path.isfile(pkg):
            # NEAREST package.json is authoritative: its type decides and the walk
            # STOPS — "module" → ESM; type-less/commonjs/unreadable (None) → CJS.
            return _read_package_type(pkg)
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
    configs in different dirs report distinct locations; the ``config-<basename>``
    id built here is later made per-file-unique by :func:`check`'s ``SYN<n>-``
    prefixing pass (so the two no longer collide). A non-``str`` ``text`` (contract is
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
            # npm/node strip a single leading BOM and accept the file; the shared
            # helper does it so this path and _read_package_type cannot drift.
            _loads_json_bom(text)
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
        # Contract is dict[str, str]; a non-str KEY (defensive) is skipped rather
        # than raising a TypeError out of check() at os.path.basename — symmetry
        # with the non-str VALUE guard in _config_defect, so a malformed entry
        # degrades rather than crashing the VERIFIED lens.
        if not isinstance(rel, str):
            continue
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

    # Per-file-unique, DETERMINISTIC ids (parity with astlens's ``AST<n>-*``).
    # Defects are already sorted by their unique ``location`` above (each changed
    # file yields at most one defect, so locations never collide), so a 1-based
    # index over the sorted list mints a stable ``SYN<n>-*`` id. This is what makes
    # two same-named broken configs in different dirs — both ``config-package.json``
    # — report DISTINCT ids instead of colliding into one. The descriptive suffix
    # (``config-<basename>`` / ``syntax-<ext>``) is preserved after the prefix.
    defects.sort(key=lambda defect: defect["location"])
    for index, defect in enumerate(defects, start=1):
        defect["id"] = f"SYN{index}-{defect['id']}"
    return defects
