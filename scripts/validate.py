"""Structural validation of kimi-atlas data artifacts against the canonical schemas.

The single source of truth for schemas is ``references/schemas.json`` (six
schemas: ``task-packet`` / ``context`` / ``critic`` / ``task-dag`` / ``dag-node``
/ ``job``). This module holds NO
orchestration knowledge — only data-contract enforcement (required-field
presence + type). Ported from apex ``scripts/validate.py``; the schema path is
resolved relative to this file exactly as apex does, and an ``optional`` block
(present on the ``context`` schema for ``clarify_resolution``) is type-checked
only when the field is actually present, so a pre-CLARIFY state still validates.
"""
from __future__ import annotations

import json
import pathlib

# Schema file lives at <plugin-root>/references/schemas.json; this script lives
# at <plugin-root>/scripts/validate.py, so parents[1] is the plugin root.
_SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[1] / "references" / "schemas.json"

_TYPES: dict[str, type] = {"str": str, "list": list, "dict": dict, "int": int}


def _schemas() -> dict:
    """Load and parse the canonical schema document."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(obj: dict, schema_name: str) -> list[str]:
    """Return a list of error strings for ``obj`` against ``schema_name``; empty means valid.

    Enforces required-field presence and type. If the schema declares an
    ``optional`` block, each optional field is type-checked *only when present*
    (an absent optional field is never an error). Raises ``KeyError`` if
    ``schema_name`` is not defined in ``schemas.json``.
    """
    schema = _schemas()[schema_name]
    errs: list[str] = []

    for field, typename in schema["required"].items():
        if field not in obj:
            errs.append(f"missing field: {field}")
        elif not isinstance(obj[field], _TYPES[typename]):
            errs.append(f"field {field} must be {typename}")

    for field, typename in schema.get("optional", {}).items():
        if field in obj and not isinstance(obj[field], _TYPES[typename]):
            errs.append(f"optional field {field} must be {typename}")

    return errs
