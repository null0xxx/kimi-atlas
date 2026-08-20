#!/usr/bin/env python3
"""Validate the Claude Code plugin manifest at ``.claude-plugin/plugin.json``.

Checks that the manifest file exists, parses as valid JSON, and declares a
non-empty kebab-case ``"name"`` field. :func:`validate_manifest` is the pure
check — it returns a list of error strings, empty when the manifest passes.
:func:`main` is the CLI wrapper: exit 0 on pass, exit 1 with the errors
written to stderr on failure. Stdlib only — no third-party imports.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_manifest(manifest_path: str | Path) -> list[str]:
    """Return validation error strings for the manifest at ``manifest_path``.

    An empty list means the manifest is present, valid JSON, and declares a
    non-empty kebab-case ``"name"`` field.
    """
    manifest_path = Path(manifest_path)
    errors: list[str] = []

    if not manifest_path.is_file():
        errors.append(f"{manifest_path}: manifest not found")
        return errors

    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except json.JSONDecodeError as exc:
        errors.append(f"{manifest_path}: not valid JSON ({exc})")
        return errors

    name = manifest.get("name") if isinstance(manifest, dict) else None
    if not name or not isinstance(name, str):
        errors.append(f'{manifest_path}: missing a non-empty "name" field')
    elif not _KEBAB_RE.match(name):
        errors.append(
            f'{manifest_path}: "name" must be kebab-case '
            f"(lowercase letters, digits, single hyphens): got {name!r}"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI: validate ``.claude-plugin/plugin.json`` under the given root (default: cwd)."""
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path.cwd()
    manifest_path = root / ".claude-plugin" / "plugin.json"

    errors = validate_manifest(manifest_path)
    if errors:
        for error in errors:
            sys.stderr.write(f"ERROR: {error}\n")
        return 1

    sys.stdout.write(f"{manifest_path}: OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
