"""The single source of run/floor language facts (universal-floor P1, blueprint §3).

One registry — no run-signal counting, no orchestration, no LLM knowledge. The
ONLY I/O is a minimal, fail-SAFE read of a ``Makefile`` / ``package.json`` when a
wrapper command (``make test`` / ``npm test``) must be expanded to the runner(s)
it actually invokes; every other function is pure over its arguments.

Invariants (mirroring ``verdict.py``/``plandag.py`` discipline):
  * **Positive-ID only, fail-CLOSED.** :func:`resolve_runner_tag` returns the
    *ordered* set of runner tags a frozen ``verify_cmd`` resolves to; an
    unrecognized command (or a missing/malformed wrapper file) → ``()`` so the
    caller degrades to ``UNVERIFIED`` — never a fabricated pass, never a false red.
  * **Word-boundary token matching.** ``cargo test`` contains the substring
    ``go test``; tags are matched with ``\\b`` boundaries so ``cargo test`` never
    leaks the ``go test`` tag (R7 COR).
  * **Recursive pytest discovery.** :func:`collectable_pytest` mirrors pytest's
    rootdir discovery — any ``test_*.py``/``*_test.py`` ANYWHERE under cwd (not
    only ``tests/``), or a declared ``[tool.pytest.ini_options]``/``[tool:pytest]``
    section (R7 COR-COLLECTABLE).
  * **Polyglot recipes → an ordered tuple of tags** (deduped, in first-appearance
    order); the caller folds per-tag pairs into the single gate result.

``SYNTAX_ARGV`` and ``CONFIG_ALLOWLIST`` are declared here for P2's consumers
(``nativefloor``/``syntaxlens``); in P1 they carry no behavior beyond being the
one importable definition.
"""
from __future__ import annotations

import json
import os
import pathlib
import re

# ---------------------------------------------------------------------------
# The ONE ordered marker→cmd probe list (blueprint §3). Each entry maps a set of
# candidate marker filenames to the verify ``cmd`` that marker implies, the
# canonical ``runner_tag`` for that cmd, and its discovery ``prec``(edence). The
# discover order in ``runcheck`` (a later task) applies make→npm→pytest first and
# consults these language markers only AFTER pytest declines (R6 COR-1), so a
# Python+``Cargo.toml`` repo still resolves to pytest.
RUNNERS: tuple[dict, ...] = (
    {"marker": ("Makefile",), "cmd": "make test", "runner_tag": "make test", "prec": 0},
    {"marker": ("package.json",), "cmd": "npm test", "runner_tag": "npm test", "prec": 1},
    {"marker": ("Cargo.toml",), "cmd": "cargo test", "runner_tag": "cargo test", "prec": 2},
    {"marker": ("go.mod",), "cmd": "go test -json ./...", "runner_tag": "go test", "prec": 3},
    {"marker": ("Gemfile", ".rspec"), "cmd": "bundle exec rspec", "runner_tag": "rspec", "prec": 4},
)

# ext → argv for the P2 syntax floor (parse-ONLY, argv-only, hermetic — §2.6).
# Declared here as the one registry; no execution happens in P1.
SYNTAX_ARGV: dict[str, list[str]] = {
    ".js": ["node", "--check"],
    ".cjs": ["node", "--check"],
    ".mjs": ["node", "--check"],
    ".rb": ["ruby", "-cw"],
    ".php": ["php", "-l"],
    ".go": ["gofmt", "-e"],
    ".sh": ["bash", "-n"],
    ".bash": ["bash", "-n"],
}

# Config files whose in-process JSON/TOML parse is BLOCKING (blueprint §9); every
# member is an ``fnmatch`` glob pattern (so ``*.lock`` covers ``Cargo.lock`` etc.).
CONFIG_ALLOWLIST: frozenset[str] = frozenset({
    "package.json",
    "tsconfig.json",
    "pyproject.toml",
    "Cargo.toml",
    "composer.json",
    "*.lock",
})

# Direct runner tokens → canonical tag. Ordered only as a positional tie-breaker;
# the returned order follows first-appearance in the command string. Each pattern
# is \\b-anchored so a tag never matches inside another word (``cargo test`` must
# NOT yield ``go test``; ``vitest`` must NOT yield ``jest``).
_DIRECT_TAG_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpytest\b"), "pytest"),
    (re.compile(r"\bunittest\b"), "unittest"),
    (re.compile(r"\bcargo\s+test\b"), "cargo test"),
    (re.compile(r"\bgo\s+test\b"), "go test"),
    (re.compile(r"\bjest\b"), "jest"),
    (re.compile(r"\bvitest\b"), "vitest"),
    (re.compile(r"\bmocha\b"), "mocha"),
    (re.compile(r"\brspec\b"), "rspec"),
    (re.compile(r"\bphpunit\b"), "phpunit"),
)

# Wrapper commands whose real runner lives in an on-disk recipe (the only I/O).
_MAKE_TEST_RE = re.compile(r"\bmake\s+test\b")
_NPM_TEST_RE = re.compile(r"\bnpm\s+(?:run\s+)?test\b")

# A Makefile ``test:`` target header (start-of-line; ``test`` then ``:``), matched
# per-line — mirrors ``runcheck._TEST_TARGET_RE`` so the two agree on what a test
# target looks like.
_TEST_TARGET_RE = re.compile(r"^test\s*:")

# Declared pytest config sections (TOML/cfg), matched at line start.
_PYTEST_SECTION_RE = re.compile(r"^\s*\[tool\.pytest\.ini_options\]", re.MULTILINE)
_PYTEST_CFG_SECTION_RE = re.compile(r"^\s*\[tool:pytest\]", re.MULTILINE)

# Directories pruned during pytest discovery: vendored/build/cache trees that a
# real ``pytest`` invocation never collects from. A stray ``test_*.py`` shipped
# inside one of these (a dependency's own tests under ``.venv``/``node_modules``,
# a copied fixture under ``build``/``dist``) must NOT make a non-Python repo
# resolve to pytest (Task-2 reviewed Minor). Every dot-prefixed directory
# (``.venv``/``.git``/``.tox``/…) is pruned in addition to these explicit names.
_PYTEST_PRUNE_DIRS: frozenset[str] = frozenset({
    "node_modules", "build", "dist", "__pycache__", "venv",
})


def _is_pruned_dir(name: str) -> bool:
    """Return True iff a directory ``name`` is skipped by pytest discovery (pure)."""
    return name.startswith(".") or name in _PYTEST_PRUNE_DIRS


def _tags_from_command(cmd: str) -> tuple[str, ...]:
    """Return the ordered, deduped runner tags directly present in ``cmd`` (pure).

    Every :data:`_DIRECT_TAG_PATTERNS` entry is searched; matches are ordered by
    first-appearance position so a polyglot line (``pytest && go test ./...``)
    yields ``("pytest", "go test")``. No I/O and no wrapper expansion — this is
    the bounded leaf that a Makefile/npm recipe is fed into.
    """
    if not cmd:
        return ()
    hits: list[tuple[int, str]] = []
    for pattern, tag in _DIRECT_TAG_PATTERNS:
        match = pattern.search(cmd)
        if match is not None:
            hits.append((match.start(), tag))
    hits.sort(key=lambda pair: pair[0])
    ordered: list[str] = []
    for _, tag in hits:
        if tag not in ordered:
            ordered.append(tag)
    return tuple(ordered)


def _safe_read(path: pathlib.Path) -> str | None:
    """Read ``path`` fail-safely; return ``None`` on any missing-file/IO error.

    Wrapper expansion must never raise — a missing or unreadable recipe simply
    means "unresolved" (``()`` → UNVERIFIED), never a crash or a false result.
    """
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _makefile_test_recipe(makefile_text: str) -> str:
    """Extract the ``test:`` target's recipe body from Makefile text (pure).

    A recipe is the block of TAB-indented lines following the ``test:`` header,
    up to the first line that is not TAB-indented (a blank line or the next
    target ends it). Multiple recipe lines are joined by newlines so a
    multi-command target keeps every runner it invokes. Returns ``""`` when no
    ``test:`` target is present.
    """
    lines = makefile_text.splitlines()
    recipe: list[str] = []
    in_target = False
    for line in lines:
        if not in_target:
            if _TEST_TARGET_RE.match(line):
                in_target = True
            continue
        if line.startswith("\t"):
            recipe.append(line[1:])
        else:
            break
    return "\n".join(recipe)


def _npm_test_script(package_json_text: str) -> str:
    """Return ``scripts.test`` from package.json text, or ``""`` (fail-safe, pure).

    Malformed JSON, a non-object root, a missing/non-object ``scripts`` map, or a
    non-string ``test`` entry all degrade to ``""`` (→ unresolved), never an error.
    """
    try:
        data = json.loads(package_json_text)
    except (ValueError, RecursionError, MemoryError):
        return ""
    if not isinstance(data, dict):
        return ""
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return ""
    test_cmd = scripts.get("test")
    return test_cmd if isinstance(test_cmd, str) else ""


def resolve_runner_tag(verify_cmd: str, cwd: str) -> tuple[str, ...]:
    """Resolve a frozen ``verify_cmd`` to its ordered set of runner tags.

    Precedence:
      * ``make test`` → read the ``Makefile`` ``test:`` recipe and resolve the
        runner tag(s) it invokes (a polyglot recipe → several tags, in order);
      * ``npm test`` / ``npm run test`` → read ``package.json scripts.test`` and
        resolve its tag(s);
      * otherwise a direct token — ``pytest``/``python -m pytest``,
        ``unittest``/``python -m unittest``, ``go test``, ``cargo test``,
        ``jest``/``vitest``/``mocha``/``rspec``/``phpunit`` — and the
        ``bundle exec``/``poetry run``/``uv run`` wrappers, whose wrapped runner
        token is recognized directly.

    Unknown commands and missing/malformed wrapper files both return ``()`` — the
    fail-closed "unresolved → UNVERIFIED" signal. Reading the Makefile /
    package.json is the ONLY I/O.
    """
    cmd = (verify_cmd or "").strip()
    if not cmd:
        return ()
    if _MAKE_TEST_RE.search(cmd):
        text = _safe_read(pathlib.Path(cwd) / "Makefile")
        return _tags_from_command(_makefile_test_recipe(text)) if text is not None else ()
    if _NPM_TEST_RE.search(cmd):
        text = _safe_read(pathlib.Path(cwd) / "package.json")
        return _tags_from_command(_npm_test_script(text)) if text is not None else ()
    return _tags_from_command(cmd)


def collectable_pytest(cwd: str) -> bool:
    """Return True iff pytest would discover a suite rooted at ``cwd``.

    Mirrors pytest's recursive rootdir discovery: True when a
    ``[tool.pytest.ini_options]`` (pyproject.toml) or ``[tool:pytest]``
    (setup.cfg) section is declared, OR any ``test_*.py``/``*_test.py`` file
    exists ANYWHERE under ``cwd`` (recursive — NOT only ``tests/``; R7
    COR-COLLECTABLE). Vendored/build/cache directories (``.venv``/``node_modules``/
    ``build``/``dist``/``__pycache__`` and any dot-dir) are pruned mid-walk so a
    stray test file shipped inside a dependency cannot make a non-Python repo
    resolve to pytest (Task-2 reviewed Minor). Fail-safe: unreadable trees simply
    stop contributing matches rather than raising. Reading the config files is I/O.
    """
    root = pathlib.Path(cwd)
    pyproject = _safe_read(root / "pyproject.toml")
    if pyproject is not None and _PYTEST_SECTION_RE.search(pyproject):
        return True
    setup_cfg = _safe_read(root / "setup.cfg")
    if setup_cfg is not None and _PYTEST_CFG_SECTION_RE.search(setup_cfg):
        return True
    try:
        for _dirpath, dirnames, filenames in os.walk(str(root)):
            # Prune in-place so os.walk never descends into denylisted trees.
            dirnames[:] = [d for d in dirnames if not _is_pruned_dir(d)]
            for name in filenames:
                if (name.startswith("test_") and name.endswith(".py")) or \
                        name.endswith("_test.py"):
                    return True
    except OSError:
        return False
    return False
