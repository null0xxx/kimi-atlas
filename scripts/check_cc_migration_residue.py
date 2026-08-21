"""Claude Code migration residue sweep -- catches retired Kimi-migration tokens.

Stage 5 of the Kimi Code -> Claude Code CLI migration ported three SKILL.md
files, seven role files, and the deterministic backbone's dispatch/harness
plumbing. This module is the structural backstop: it sweeps every TRACKED file
in the repository for a small denylist of tokens/patterns that are load-bearing
evidence a port is incomplete if they survive in LIVE (non-historical) content --

  * literal ``${KIMI_SKILL_DIR}`` -- Kimi CLI's per-invocation plugin-root
    token; unbound and dead under Claude Code (see ``hooks/init-env.sh``).
  * literal ``${KIMI_SESSION_ID}`` -- Kimi CLI's SKILL-body session-id
    substitution, replaced by ``$ATLAS_SESSION_ID`` (Claude Code's own
    SessionStart ``session_id``, persisted by ``hooks/init-env.sh``).
  * an old-style dispatch value shaped like ``subagent_type="explore"`` /
    ``"coder"`` / ``"plan"`` -- Kimi CLI's fixed 3-built-in-type dispatch,
    replaced by Claude Code's by-name dispatch against ``agents/*.md``.
  * ``ReadMediaFile`` -- not a real Claude Code tool; ``Read`` already
    handles media inline.
  * ``FetchURL`` -- Claude Code's equivalent is ``WebFetch``.
  * ``.kimi-plugin`` -- the retired Kimi Code plugin-manifest directory,
    replaced by ``.claude-plugin``.

A match is real residue only outside the historical-record exclusions this
whole migration has consistently respected: ``PLAN.md``,
``references/kimi-runtime.md``, ``CHANGELOG.md``, ``docs/superpowers/plans/*``
dated before this migration, and ``docs/superpowers/specs/*`` -- plus a small
number of additional whole-file/prefix exclusions verified by hand (2026-08-21)
to be the same kind of frozen historical record even though they were not
individually named up front: ``AGENTS.md`` (still describes the Kimi Code-era
project end to end and already self-declares the migration blueprint as
authoritative for anything migration-related -- bringing it current is a
dedicated documentation pass, not this sweep's job), the six pre-Claude-Code
``probe/*.sh`` scripts that test/record Kimi CLI's OWN behavior (the ``probe/``
analogue of ``references/kimi-runtime.md`` -- the two live ``probe_cc_*.sh``
Claude Code probes are NOT in this set), and ``tests/corpus/historical/`` (frozen
diff/tree snapshots between old version tags, consumed as read-only regression
fixtures, not living instructional content).

``${KIMI_SKILL_DIR}``/``${KIMI_SESSION_ID}`` carry one further, pattern-scoped
exemption (every other pattern above stays fully in scope in these same
files/directories): every live occurrence of either token outside the
whole-file exclusions above was, as of 2026-08-21, hand-verified to be either
deliberate historical/comparison prose that explicitly names "Kimi CLI" as the
token's former owner (``hooks/init-env.sh``, ``scripts/contextgraph.py``,
``skills/atlas/SKILL.md``, ``skills/atlas-resume/SKILL.md``), or a
regression-test fixture under ``tests/`` whose entire point is asserting the
token's ABSENCE elsewhere (an ``assertNotIn``/"must never reappear" guard) or
neutralising it via ``.replace(TOKEN, "PLACEHOLDER")`` before parsing an
extracted SKILL.md snippet -- never a live, still-substituted reference. A
``ReadMediaFile``/``FetchURL``/``.kimi-plugin``/old-style-dispatch hit in any
of those same files is still real residue and stays fully in scope.

:func:`is_historical`, :func:`find_residue_in_text`, and :func:`find_residue`
are pure (no filesystem access); only :func:`main` and its two small helpers
touch the filesystem/subprocess.
"""
from __future__ import annotations

import argparse
import pathlib
import posixpath
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Denylist
# ---------------------------------------------------------------------------

# (human label, compiled pattern). Label doubles as the reported finding name
# and, for the two KIMI_* entries, as the key into _KIMI_TOKEN_LABELS below.
_DENYLIST: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("${KIMI_SKILL_DIR}", re.compile(re.escape("${KIMI_SKILL_DIR}"))),
    ("${KIMI_SESSION_ID}", re.compile(re.escape("${KIMI_SESSION_ID}"))),
    (
        "old-style subagent_type dispatch",
        re.compile(r"""subagent_type\s*[:=]\s*["'](?:explore|coder|plan)["']"""),
    ),
    ("ReadMediaFile", re.compile(re.escape("ReadMediaFile"))),
    ("FetchURL", re.compile(re.escape("FetchURL"))),
    (".kimi-plugin", re.compile(re.escape(".kimi-plugin"))),
)

# ---------------------------------------------------------------------------
# Historical-record exclusions (whole file/prefix -- every pattern skipped)
# ---------------------------------------------------------------------------

EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        "PLAN.md",
        "references/kimi-runtime.md",
        "CHANGELOG.md",
        "AGENTS.md",
        "probe/probe_agents_md.sh",
        "probe/probe_agentswarm.sh",
        "probe/probe_hook_block.sh",
        "probe/probe_loopcontrol.sh",
        "probe/probe_runid_stability.sh",
        "probe/probe_sessionstart.sh",
        # Self-referential: this checker's own source embeds the denylist's literal
        # string patterns, and its test file deliberately embeds each pattern in a
        # fixture to prove detection -- both trip the sweep the moment they are
        # tracked, unless excluded here.
        "scripts/check_cc_migration_residue.py",
        "tests/test_cc_migration_residue.py",
    }
)

EXCLUDED_PREFIXES: tuple[str, ...] = (
    "docs/superpowers/specs/",
    "tests/corpus/historical/",
)

# docs/superpowers/plans/<YYYY-MM-DD>-*.md is excluded when its leading date is
# strictly before this cutoff -- the day this residue sweep was authored.
# Every plan doc in the directory as of that date, INCLUDING the migration
# blueprint itself (dated 2026-08-20 -- a planning artifact ABOUT the
# migration, not a ported deliverable, hence full of literal Kimi-token
# examples by design), predates it. A plan doc dated on/after the cutoff falls
# back into scope.
_PLANS_DATE_CUTOFF = "2026-08-21"
_PLANS_PREFIX = "docs/superpowers/plans/"
_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def is_historical(relpath: str) -> bool:
    """Return True iff ``relpath`` is a whole-file/prefix historical exclusion (pure)."""
    if relpath in EXCLUDED_FILES:
        return True
    if any(relpath.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    if relpath.startswith(_PLANS_PREFIX):
        match = _DATE_PREFIX_RE.match(posixpath.basename(relpath))
        if match and match.group(1) < _PLANS_DATE_CUTOFF:
            return True
    return False


# ---------------------------------------------------------------------------
# ${KIMI_SKILL_DIR} / ${KIMI_SESSION_ID} pattern-scoped exemption
# ---------------------------------------------------------------------------

_KIMI_TOKEN_LABELS: frozenset[str] = frozenset({"${KIMI_SKILL_DIR}", "${KIMI_SESSION_ID}"})

_KIMI_TOKEN_EXEMPT_FILES: frozenset[str] = frozenset(
    {
        "hooks/init-env.sh",
        "scripts/contextgraph.py",
        "skills/atlas/SKILL.md",
        "skills/atlas-resume/SKILL.md",
    }
)

_KIMI_TOKEN_EXEMPT_PREFIX = "tests/"


def _kimi_token_exempt(relpath: str) -> bool:
    """Return True iff ``relpath`` is exempted from the two KIMI_* patterns only (pure)."""
    return relpath in _KIMI_TOKEN_EXEMPT_FILES or relpath.startswith(_KIMI_TOKEN_EXEMPT_PREFIX)


# ---------------------------------------------------------------------------
# Pure detection core
# ---------------------------------------------------------------------------


def find_residue_in_text(relpath: str, text: str) -> list[dict]:
    """Return every denylist hit in one file's content, as ``{file, line, pattern, text}`` (pure).

    Does not consult :func:`is_historical` -- callers (:func:`find_residue`)
    decide which files reach this function at all. Applies the
    ``${KIMI_SKILL_DIR}``/``${KIMI_SESSION_ID}`` pattern-scoped exemption
    (:func:`_kimi_token_exempt`) per line.
    """
    hits: list[dict] = []
    exempt_kimi = _kimi_token_exempt(relpath)
    for lineno, line in enumerate(text.split("\n"), start=1):
        for label, pattern in _DENYLIST:
            if exempt_kimi and label in _KIMI_TOKEN_LABELS:
                continue
            if pattern.search(line):
                hits.append(
                    {"file": relpath, "line": lineno, "pattern": label, "text": line.strip()}
                )
    return hits


def find_residue(files: dict[str, str]) -> list[dict]:
    """Sweep ``{relpath: text}`` for denylist residue, skipping historical files (pure).

    Returns findings sorted by ``(file, line)``; empty means clean.
    """
    hits: list[dict] = []
    for relpath, text in files.items():
        if is_historical(relpath):
            continue
        hits.extend(find_residue_in_text(relpath, text))
    return sorted(hits, key=lambda h: (h["file"], h["line"]))


# ---------------------------------------------------------------------------
# CLI (impure: git + filesystem)
# ---------------------------------------------------------------------------


def _tracked_files(root: pathlib.Path) -> list[str]:
    """Every tracked file under ``root``, as repo-relative POSIX paths (impure).

    Derived from ``git ls-files`` when ``root`` IS a git work tree; falls back
    to a plain filesystem walk (pruning ``.git``/``__pycache__``) otherwise --
    ``git ls-files`` returns empty outside a work tree (same precedent as
    ``tests/test_predcov.py``'s ``_repo_files``), which would silently sweep
    nothing rather than failing loudly.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = proc.stdout.split() if proc.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        out = []
    if out:
        return sorted(out)
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
    )


def _read_tracked_files(root: pathlib.Path, relpaths: list[str]) -> dict[str, str]:
    """Read each tracked file as UTF-8 text; a binary/unreadable file is skipped (impure)."""
    files: dict[str, str] = {}
    for relpath in relpaths:
        try:
            files[relpath] = (root / relpath).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return files


def main(argv: list[str] | None = None) -> int:
    """CLI: fail (exit 1) if any tracked, non-historical file carries denylist residue."""
    parser = argparse.ArgumentParser(
        description=(
            "Fail if a retired Kimi-migration token/pattern survives in a live "
            "(non-historical) tracked file."
        )
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    relpaths = _tracked_files(root)
    files = _read_tracked_files(root, relpaths)
    hits = find_residue(files)

    for hit in hits:
        sys.stderr.write(
            f"RESIDUE: {hit['file']}:{hit['line']}: {hit['pattern']} -- {hit['text']}\n"
        )

    if hits:
        sys.stderr.write(f"\n{len(hits)} migration-residue match(es) found.\n")
        return 1

    sys.stdout.write(f"No Kimi-migration residue found across {len(files)} tracked file(s).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
