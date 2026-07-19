"""Skill-registry builder — classifies the bundled ``Skills/`` zips into one registry.

The 117 skill archives under ``Skills/<Category>/`` are the source of truth; this
module distils each one into a compact, machine-readable entry of
``references/skill-registry.json`` so tooling (``scripts/skillselect.py``) can rank
skills for a task intent without opening zips at selection time. Every archive is
read **in memory** via ``zipfile`` — nothing is ever extracted into the tracked
tree — and each zip-internal ``SKILL.md`` is third-party **UNTRUSTED DATA**
(SAFE-2): it is parsed for classification, never interpreted as instructions.

Parsing is stdlib-only. The frontmatter reader handles the simple ``key: value``
YAML-subset the zips actually carry (top-level keys such as ``name`` /
``description`` / ``license``; nested blocks like ``metadata:`` are ignored), and
trigger extraction (E1) lifts the explicit intent signals out of description
phrasings like "Triggered when users ask for X, Y …" / "Use when the user
mentions …" into a ``triggers`` list. Trigger text is a heuristic signal and stays
advisory (V6) — it never gates anything.

The build is deterministic: entries are sorted by ``(category, name, zip)`` with a
stable key order and no timestamps, so a rebuild over an unchanged tree is a no-op
diff. The CLI prints an audit (E4) — per-category counts, parse failures, and a
``registry-count == zip-count`` check — and exits non-zero if any zip failed to
parse or the counts disagree. The registry is validated against the canonical
``skill-registry``/``skill-entry`` schemas (``scripts/validate.py``) before it is
written, and the file is written ONLY when the registry is schema-valid AND the
audit is clean — a partial or failed registry is never committed to disk.

:func:`parse_frontmatter`, :func:`extract_triggers`, :func:`build_registry`,
:func:`validate_registry` and :func:`audit` are pure; :func:`classify_zip`,
:func:`iter_zip_paths` and :func:`build_entries` are filesystem READERS;
:func:`main` is the only WRITER.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import zipfile

# When run directly as ``python3 scripts/skillregistry.py`` the interpreter puts
# ``scripts/`` (not the repo root) on ``sys.path[0]``, so ``from scripts import ...``
# would fail. Put the plugin root on the path so the package imports resolve both when
# run directly and when imported as ``scripts.skillregistry`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import validate  # noqa: E402  (path shim must precede this import)

# The registry and the Skills tree live at <plugin-root>/references and
# <plugin-root>/Skills (same resolution idiom as scripts/validate.py).
_DEFAULT_SKILLS_ROOT = _ROOT / "Skills"
_DEFAULT_OUT = _ROOT / "references" / "skill-registry.json"

REGISTRY_VERSION = 1

# A SKILL.md opens with a YAML frontmatter block between two `---` fences.
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)
# Top-level `key: value` (indented lines belong to nested blocks and are skipped).
_KV_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)[ \t]*:[ \t]*(.*)$")

# E1 — the trigger phrasings used across the shipped descriptions:
#   "Triggered when the user asks for …", "Trigger when users mention …",
#   "Triggers when …", "Triggered by phrases like …", "Trigger on requests to …",
#   "Use when the user mentions …".
_TRIGGER_RE = re.compile(
    r"(?:trigger(?:ed|s)?\s+(?:when|by|on)|use\s+when)\b(.*?)(?:\.\s|\.$|$)",
    re.IGNORECASE | re.DOTALL,
)
# Trigger signals are comma/enumeration separated ("…, beating X, or mentions Y").
_SIGNAL_SPLIT_RE = re.compile(r",|\s+or\s+")
# Leading filler verbs that carry no intent signal; stripped (repeatedly) from the
# front of each raw signal so "the user asks for help organizing" → "organizing".
_SIGNAL_PREFIX_RE = re.compile(
    r"^(?:the\s+user|users?|they)\s+"
    r"(?:asks?\s+(?:for|to)|mentions?|wants?\s+to|needs?\s+to|talks?\s+about|"
    r"requests?(?:\s+for|\s+to)?|phrases?|keywords?|terms?)\s*"
    r"|^(?:phrases?|keywords?|terms?|requests?|mentions?)\s+(?:like|such\s+as|for|to|of)\s+"
    r"|^(?:like|such\s+as|help\s+with|help|for|to|when|and|by|on)\s+",
    re.IGNORECASE,
)
# Quotes that wrap example phrases in descriptions ('polish this', "analyze it").
_QUOTE_CHARS = "\"'‘’“”"


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the top-level ``key: value`` pairs of a SKILL.md frontmatter block.

    stdlib-only YAML subset: only unindented ``key: value`` lines are read —
    nested blocks (``metadata:``, ``tags:`` lists, …) are ignored, a key with an
    empty value maps to ``""``, and one level of surrounding single/double quotes
    is stripped. Raises ``ValueError`` when the ``---`` fences are absent.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("SKILL.md has no '---' frontmatter fence")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line[0] in " \t":
            continue  # blank line or nested (indented) content — not a top-level key
        kv = _KV_RE.match(line)
        if not kv:
            continue
        value = kv.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[kv.group(1)] = value
    return fields


def extract_triggers(description: str) -> list[str]:
    """Lift explicit intent signals out of a skill description (E1).

    Finds the "Triggered when/by/on …" / "Use when …" fragment, splits it into
    its enumerated signals, strips filler prefixes and quoting, and returns the
    deduplicated signal list in order of appearance. ``[]`` when the description
    carries no trigger phrasing — the selector then falls back to
    name/description matching. Heuristic and advisory (V6).
    """
    if not description:
        return []
    match = _TRIGGER_RE.search(description)
    if not match:
        return []
    signals: list[str] = []
    for piece in _SIGNAL_SPLIT_RE.split(match.group(1)):
        piece = piece.strip()
        previous = None
        while previous != piece:  # strip stacked prefixes ("the user asks for help …")
            previous = piece
            piece = _SIGNAL_PREFIX_RE.sub("", piece).strip()
        piece = piece.strip(_QUOTE_CHARS).strip(" .;:").strip(_QUOTE_CHARS)
        if len(piece) >= 2 and piece not in signals:
            signals.append(piece)
    return signals


def classify_zip(zip_path: pathlib.Path, category: str) -> dict:
    """Classify one skill archive into its registry entry.

    Reads the zip fully in memory (never extracted) and parses its top-level
    SKILL.md. Raises ``ValueError`` on an unreadable archive, a missing
    SKILL.md, or a SKILL.md without a frontmatter fence.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            if "SKILL.md" not in names:
                raise ValueError("archive has no top-level SKILL.md")
            raw = archive.read("SKILL.md")
    except zipfile.BadZipFile as exc:
        raise ValueError(f"not a readable zip archive: {exc}") from exc
    fields = parse_frontmatter(raw.decode("utf-8", errors="replace"))
    name = fields.get("name", "").strip() or zip_path.stem
    description = fields.get("description", "")
    return {  # stable key order — keep in sync with the `skill-entry` schema
        "name": name,
        "category": category,
        "description": description,
        "triggers": extract_triggers(description),
        "zip": zip_path.name,
    }


def iter_zip_paths(skills_root: pathlib.Path) -> list[pathlib.Path]:
    """Return every ``<category>/<skill>.zip`` path, sorted by (category, name)."""
    return sorted(
        skills_root.glob("*/*.zip"),
        key=lambda p: (p.parent.name, p.name),
    )


def build_entries(
    skills_root: pathlib.Path, zip_paths: list[pathlib.Path] | None = None
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Classify every zip under ``skills_root``.

    Returns ``(entries, failures)`` where ``failures`` is a list of
    ``(zip_path, reason)`` for archives that could not be classified. Entries are
    sorted by ``(category, name, zip)`` for a deterministic registry. Pass
    ``zip_paths`` (the :func:`iter_zip_paths` scan) to reuse an existing glob;
    ``None`` globs the tree here.
    """
    entries: list[dict] = []
    failures: list[tuple[str, str]] = []
    paths = zip_paths if zip_paths is not None else iter_zip_paths(skills_root)
    for zip_path in paths:
        try:
            entries.append(classify_zip(zip_path, zip_path.parent.name))
        except ValueError as exc:
            failures.append((zip_path.as_posix(), str(exc)))
    entries.sort(key=lambda e: (e["category"], e["name"], e["zip"]))
    return entries, failures


def build_registry(entries: list[dict]) -> dict:
    """Assemble the registry document (stable key order, no timestamps)."""
    return {
        "version": REGISTRY_VERSION,
        "skill_count": len(entries),
        "skills": entries,
    }


def validate_registry(registry: dict) -> list[str]:
    """Validate a registry document against the canonical schemas; [] means valid."""
    errors = validate.validate(registry, "skill-registry")
    skills = registry.get("skills")
    if isinstance(skills, list):
        if registry.get("skill_count") != len(skills):
            errors.append("skill_count does not match len(skills)")
        for i, entry in enumerate(skills):
            for err in validate.validate(entry, "skill-entry"):
                errors.append(f"skills[{i}]: {err}")
    return errors


def audit(
    entries: list[dict], zip_count: int, failures: list[tuple[str, str]]
) -> tuple[list[str], bool]:
    """Build the E4 audit lines and own the single pass/fail verdict.

    Returns ``(lines, ok)``: per-category counts, one line per parse failure,
    the count-equality check, and the trailing ``AUDIT ok`` / ``AUDIT MISMATCH``
    line — ``ok`` is the verdict that line carries (no failures AND
    ``registry-count == zip-count``), so callers never re-derive the predicate.
    """
    by_category: dict[str, int] = {}
    for entry in entries:
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1
    lines = [f"AUDIT category={cat} skills={by_category[cat]}" for cat in sorted(by_category)]
    for path, reason in failures:
        lines.append(f"AUDIT parse-failure zip={path} reason={reason}")
    lines.append(f"AUDIT zips={zip_count} registry={len(entries)}")
    ok = not failures and zip_count == len(entries)
    lines.append("AUDIT ok" if ok else "AUDIT MISMATCH")
    return lines, ok


def main(argv: list[str] | None = None) -> int:
    """CLI: rebuild ``references/skill-registry.json`` from ``Skills/`` (E4 audit)."""
    parser = argparse.ArgumentParser(
        description="Build references/skill-registry.json from the bundled Skills/ zips."
    )
    parser.add_argument(
        "--skills-root",
        type=pathlib.Path,
        default=_DEFAULT_SKILLS_ROOT,
        help="Directory holding <category>/*.zip (default: <plugin-root>/Skills).",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=_DEFAULT_OUT,
        help="Registry output path (default: <plugin-root>/references/skill-registry.json).",
    )
    args = parser.parse_args(argv)

    skills_root = args.skills_root
    if not skills_root.is_dir():
        sys.stderr.write(f"skillregistry: skills root not found: {skills_root}\n")
        return 1

    zip_paths = iter_zip_paths(skills_root)
    entries, failures = build_entries(skills_root, zip_paths)
    registry = build_registry(entries)
    schema_errors = validate_registry(registry)
    for err in schema_errors:
        sys.stderr.write(f"skillregistry: registry invalid: {err}\n")
    if schema_errors:
        return 1  # never write a registry that violates the schema

    lines, ok = audit(entries, len(zip_paths), failures)
    for line in lines:
        sys.stdout.write(line + "\n")
    if not ok:
        return 1  # failed audit — never write a partial/failed registry

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    sys.stdout.write(f"skillregistry: wrote {args.out} ({len(entries)} skills)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
