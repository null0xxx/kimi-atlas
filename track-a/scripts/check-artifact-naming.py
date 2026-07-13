#!/usr/bin/env python3
"""Check artifact file naming conventions in analysis/ and design/."""

import argparse
import re
import sys
from pathlib import Path

# Files existing before these conventions were adopted.
# They are exempt from recommended-prefix warnings but must still obey
# structural naming rules (lowercase, kebab-case, .md, non-generic).
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

# Valid kebab-case pattern: lowercase letters/digits separated by single hyphens.
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

PREFIX_PATTERNS = {
    "analysis": (re.compile(r"^(explore|test|background|exec)-"), ["explore-", "test-", "background-", "exec-"]),
    "design": (re.compile(r"^(plan|decisions)-"), ["plan-", "decisions-"]),
}


def check_file(project_root: Path, rel_path: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single file path."""
    errors: list[str] = []
    warnings: list[str] = []
    path = project_root / rel_path
    name = path.name
    stem = path.stem

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check artifact naming conventions in analysis/ and design/."
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
    args = parser.parse_args()

    project_root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for folder in ("analysis", "design"):
        folder_path = project_root / folder
        if not folder_path.is_dir():
            warnings.append(f"{folder}/ directory not found; skipping")
            continue
        for entry in sorted(folder_path.iterdir()):
            if not entry.is_file():
                continue
            rel_path = f"{folder}/{entry.name}"
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
