"""Structural validation of kimi-atlas data artifacts against the canonical schemas.

The single source of truth for schemas is ``references/schemas.json`` (each
named schema declares a ``required`` — and optionally ``optional`` — field→type
map, plus an optional ``values`` field→closed-value-list map and an optional
``formats`` field→regex map). This module holds NO orchestration knowledge —
only data-contract enforcement (required-field presence + type + closed-value
membership + value format). Ported from apex
``scripts/validate.py``; the schema path is resolved relative to this file
exactly as apex does, and an ``optional`` block (present on the ``context``
schema for ``clarify_resolution``) is type-checked only when the field is
actually present, so a pre-CLARIFY state still validates.

The ``values`` block (present on ``task-packet`` for ``invocation_form``) is
enforced the same way ``required``/``optional`` already are — declaratively, in
``schemas.json``, checked by this one function — never as ad-hoc per-caller
prose. A field only gets a closed-value check when its schema explicitly lists
one; every existing schema without a ``values`` block is unaffected.

The ``formats`` block (on ``task-packet`` and ``context``, for ``baseline_sha``)
is that same idea for a field whose legal set is too large to enumerate: a
regular expression the WHOLE value must match. It exists because ``"str"`` was
the only constraint on ``baseline_sha`` while that string was being handed to
git in a revision slot, where a value beginning with ``-`` is an option, not a
revision (SEC-2 / plan VIP-A2; ``scripts/difftool.py`` refuses it at the sink —
this is the contract that says so where the packet is written). The pattern
deliberately admits the EMPTY string: "no baseline recorded" is honest and
supported (a non-git target), and rejecting it would turn an honest run red.
"""
from __future__ import annotations

import json
import pathlib
import re

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
    (an absent optional field is never an error). If the schema declares a
    ``values`` block, each listed field is checked for closed-set membership
    *only when present* — a missing/wrong-type field already errors above via
    ``required``/``optional`` and is not double-reported here. If the schema
    declares a ``formats`` block, each listed field's value must match its
    pattern in FULL (``re.fullmatch``), under the same present-and-well-typed
    precondition. Raises ``KeyError`` if ``schema_name`` is not defined in
    ``schemas.json``.
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

    type_by_field = {**schema["required"], **schema.get("optional", {})}
    for field, allowed in schema.get("values", {}).items():
        if field not in obj:
            continue
        typename = type_by_field.get(field)
        if typename is not None and not isinstance(obj[field], _TYPES[typename]):
            continue  # already reported as a type error above; do not double-report
        if obj[field] not in allowed:
            errs.append(f"field {field} must be one of {allowed}")

    for field, pattern in schema.get("formats", {}).items():
        if field not in obj or not isinstance(obj[field], str):
            continue  # absent or wrong-typed: already reported above
        if re.fullmatch(pattern, obj[field]) is None:
            errs.append(f"field {field} must match {pattern}")

    return errs
