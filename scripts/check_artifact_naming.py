#!/usr/bin/env python3
"""Check artifact file naming conventions across the kimi-atlas tree.

Migrated from the Track A ``check-artifact-naming.py`` (renamed to an importable
underscore module). Structural rules for every ``.md`` artifact: ``.md``
extension, all-lowercase, kebab-case stem, no generic stem. The legacy
``analysis/``-``design/`` recommended-prefix warnings are retained so the rule
engine stays backward-compatible.

Two behavioural changes for kimi-atlas:

* **Explicit exclusion set (DS-9):** ``README.md``, ``SKILL.md``, ``LICENSE``,
  ``Makefile`` and ``PLAN.md`` are project fixtures whose names are fixed by
  convention; they are exempt from every rule so uppercase docs never fail CI.
* **Nested-subdirectory fix:** the old ``main`` iterated a single directory level
  and *silently skipped* any subdirectory, so nested ``.md`` files went
  unchecked. ``main`` now walks the tree recursively.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Project fixtures whose filenames are fixed by convention — exempt from all
# naming rules (DS-9) so uppercase docs (README.md, SKILL.md, …) never fail CI.
EXCLUSION_SET = {"README.md", "SKILL.md", "LICENSE", "Makefile", "PLAN.md"}

# Files predating these conventions: exempt from recommended-prefix warnings but
# still bound by the structural rules (lowercase, kebab-case, .md, non-generic).
GRANDFATHERED = {
    "analysis/kimi-architecture-spec.md",
    "analysis/validation-resume-checklist.md",
    "analysis/validation-parallel-explore.md",
    "analysis/validation-multifile-coder.md",
    "analysis/artifact-index.md",
    "analysis/compact-ready-state.md",
    "analysis/post-compact-state-repair.md",
    "design/verified-constraints-and-build-strategy.md",
    "design/track-a-overlay-architecture.md",
    "design/session-state.md",
    "design/next-step-brief.md",
    "design/artifact-conventions.md",
    "design/plan-first-real-task.md",
}

GENERIC_NAMES = {"notes", "temp", "draft", "misc"}

# Valid kebab-case: lowercase letters/digits separated by single hyphens.
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

PREFIX_PATTERNS = {
    "analysis": (
        re.compile(r"^(explore|test|background|exec)-"),
        ["explore-", "test-", "background-", "exec-"],
    ),
    "design": (re.compile(r"^(plan|decisions)-"), ["plan-", "decisions-"]),
}

# Directory segments never walked when scanning the tree.
_SKIP_SEGMENTS = {".git", "__pycache__", "node_modules"}


def check_file(project_root: Path, rel_path: str) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` for a single artifact path.

    ``rel_path`` is a repo-relative POSIX path. Files whose basename is in
    :data:`EXCLUSION_SET` are exempt from every rule and return no findings.
    """
    errors: list[str] = []
    warnings: list[str] = []
    path = project_root / rel_path
    name = path.name
    stem = path.stem

    if name in EXCLUSION_SET:
        return errors, warnings

    if not name.endswith(".md"):
        errors.append(f"{rel_path}: must use '.md' extension")
        return errors, warnings

    if name != name.lower():
        errors.append(f"{rel_path}: filename must be all lowercase")

    if not KEBAB_RE.match(stem):
        errors.append(
            f"{rel_path}: filename must be kebab-case "
            "(lowercase letters, digits, single hyphens)"
        )

    if stem in GENERIC_NAMES:
        errors.append(f"{rel_path}: generic filename '{stem}.md' is not allowed")

    folder = path.parent.name
    if folder in PREFIX_PATTERNS and rel_path not in GRANDFATHERED:
        pattern, expected = PREFIX_PATTERNS[folder]
        if not pattern.match(stem):
            warnings.append(
                f"{rel_path}: recommended prefix missing "
                f"(expected one of: {', '.join(expected)})"
            )

    return errors, warnings


def _iter_markdown(project_root: Path):
    """Yield repo-relative POSIX paths of every ``.md`` file (recursive).

    Walks the whole tree (fixing the legacy single-level skip of nested
    subdirectories) while skipping version-control and cache directories.
    """
    for path in sorted(project_root.rglob("*.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(project_root).as_posix()
        if any(seg in _SKIP_SEGMENTS for seg in rel.split("/")):
            continue
        yield rel


def main(argv: list[str] | None = None) -> int:
    """CLI: scan the tree recursively; fail on any naming violation."""
    parser = argparse.ArgumentParser(
        description="Check artifact naming conventions across the kimi-atlas tree."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current working directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as fatal errors (default: false)",
    )
    args = parser.parse_args(argv)

    project_root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for rel_path in _iter_markdown(project_root):
        file_errors, file_warnings = check_file(project_root, rel_path)
        errors.extend(file_errors)
        warnings.extend(file_warnings)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} naming violation(s) found.", file=sys.stderr)
        return 1

    if args.strict and warnings:
        print(
            f"\n{len(warnings)} naming warning(s) found "
            "(treated as fatal in strict mode).",
            file=sys.stderr,
        )
        return 1

    print("All checked artifact files conform to naming conventions.")
    if warnings:
        print(f"{len(warnings)} prefix warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
