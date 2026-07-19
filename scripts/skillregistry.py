"""Skill-registry builder — distils the extracted ``skills/`` tree into one registry.

The 115 extracted skill packages under ``skills/<name>/`` — built by
``scripts/skillextract.py`` from the bundled ``Skills/`` zips and anchored by
the committed sha256 manifest ``references/skills-manifest.json`` — are the
source of truth; this module distils each one into a compact, machine-readable
entry of ``references/skill-registry.json`` so tooling
(``scripts/skillselect.py``) can rank skills for a task intent without walking
payload files at selection time. Each package's ``SKILL.md`` is third-party
**UNTRUSTED DATA** (SAFE-2): it is parsed for classification, never interpreted
as instructions.

Parsing is stdlib-only. The frontmatter reader handles the simple ``key: value``
YAML-subset the skills actually carry (top-level keys such as ``name`` /
``description`` / ``license``; nested blocks like ``metadata:`` are ignored), and
trigger extraction (E1) lifts the explicit intent signals out of description
phrasings like "Triggered when users ask for X, Y …" / "Use when the user
mentions …" into a ``triggers`` list. Trigger text is a heuristic signal and stays
advisory (V6) — it never gates anything.

The build is deterministic and manifest-anchored: a package's ``category`` comes
from the committed skills manifest (a skill dir the manifest does not record is
an audit FAILURE, never silently categorized), entries are sorted by
``(category, name)`` with a stable key order and no timestamps, so a rebuild over
an unchanged tree is a no-op diff. The CLI prints an audit (E4) — per-category
counts, failures, and a ``registry-count == manifest-skill-count`` check — and
exits non-zero if any package failed to parse or the counts disagree. The
registry is validated against the canonical ``skill-registry``/``skill-entry``
schemas (``scripts/validate.py``) before it is written, and the file is written
ONLY when the registry is schema-valid AND the audit is clean — a partial or
failed registry is never committed to disk.

:func:`parse_frontmatter`, :func:`extract_triggers`, :func:`build_registry`,
:func:`validate_registry` and :func:`audit` are pure; :func:`classify_dir`,
:func:`iter_skill_dirs`, :func:`load_manifest` and :func:`build_entries` are
filesystem READERS; :func:`main` is the only WRITER.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# When run directly as ``python3 scripts/skillregistry.py`` the interpreter puts
# ``scripts/`` (not the repo root) on ``sys.path[0]``, so ``from scripts import ...``
# would fail. Put the plugin root on the path so the package imports resolve both when
# run directly and when imported as ``scripts.skillregistry`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import validate  # noqa: E402  (path shim must precede this import)

# The extracted skills tree lives at <plugin-root>/skills, the manifest and the
# registry at <plugin-root>/references (same resolution idiom as
# scripts/validate.py).
_DEFAULT_SKILLS_ROOT = _ROOT / "skills"
_DEFAULT_MANIFEST = _ROOT / "references" / "skills-manifest.json"
_DEFAULT_OUT = _ROOT / "references" / "skill-registry.json"

REGISTRY_VERSION = 2

# First-party orchestrator skills living under skills/ next to the vendored
# packages: plugin machinery (state machine / weave / resume), NOT official
# vendored skills — never registered, and absent from the skills manifest by
# design. A NEW first-party dir added here must be named in this set or the
# audit fails it as missing-from-manifest (the intended tripwire).
FIRST_PARTY_DIRS: frozenset[str] = frozenset({"atlas", "atlas-weave", "atlas-resume"})

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


def classify_dir(skill_dir: pathlib.Path, category: str) -> dict:
    """Classify one extracted skill package into its registry entry.

    Reads ``<skill_dir>/SKILL.md`` from disk and parses its frontmatter; the
    entry's ``path`` is the repo-relative package dir ``skills/<dir-name>/``.
    Raises ``ValueError`` on an unreadable SKILL.md or one without a
    frontmatter fence.
    """
    try:
        raw = (skill_dir / "SKILL.md").read_bytes()
    except OSError as exc:
        raise ValueError(f"SKILL.md is unreadable: {exc}") from exc
    fields = parse_frontmatter(raw.decode("utf-8", errors="replace"))
    name = fields.get("name", "").strip() or skill_dir.name
    description = fields.get("description", "")
    return {  # stable key order — keep in sync with the `skill-entry` schema
        "name": name,
        "category": category,
        "description": description,
        "triggers": extract_triggers(description),
        "path": f"skills/{skill_dir.name}/",
    }


def iter_skill_dirs(skills_root: pathlib.Path) -> list[pathlib.Path]:
    """Return every extracted package dir (``skills/<name>/`` holding a SKILL.md).

    The first-party orchestrator dirs (:data:`FIRST_PARTY_DIRS`) are excluded —
    they are plugin machinery, not vendored official skills. Sorted by dir name
    for a deterministic scan.
    """
    return sorted(
        (
            d
            for d in skills_root.iterdir()
            if d.is_dir() and (d / "SKILL.md").is_file() and d.name not in FIRST_PARTY_DIRS
        ),
        key=lambda d: d.name,
    )


def load_manifest(manifest_path: pathlib.Path) -> dict:
    """Load the committed skills manifest; raises ``OSError``/``JSONDecodeError``."""
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def build_entries(
    skills_root: pathlib.Path,
    skill_dirs: list[pathlib.Path] | None = None,
    manifest: dict | None = None,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Classify every extracted package dir under ``skills_root``.

    Returns ``(entries, failures)`` where ``failures`` is a list of
    ``(dir_path, reason)``: a package whose SKILL.md could not be parsed, or a
    package dir the manifest does not record (a dir the manifest does not
    anchor is an audit failure, never silently categorized). A package's
    ``category`` comes from the manifest; its ``path`` is
    ``skills/<name>/``. Entries are sorted by ``(category, name)`` for a
    deterministic registry. Pass ``skill_dirs`` (the :func:`iter_skill_dirs`
    scan) to reuse an existing listing; ``None`` lists the tree here. Pass
    ``manifest`` (the :func:`load_manifest` read) to reuse a loaded manifest;
    ``None`` loads the committed one.
    """
    if manifest is None:
        manifest = load_manifest(_DEFAULT_MANIFEST)
    categories = {
        entry.get("name", ""): entry.get("category", "")
        for entry in manifest.get("skills", [])
        if isinstance(entry, dict)
    }
    entries: list[dict] = []
    failures: list[tuple[str, str]] = []
    dirs = skill_dirs if skill_dirs is not None else iter_skill_dirs(skills_root)
    for skill_dir in dirs:
        category = categories.get(skill_dir.name)
        if category is None:
            failures.append(
                (skill_dir.as_posix(), "skill dir missing from the skills manifest")
            )
            continue
        try:
            entries.append(classify_dir(skill_dir, category))
        except ValueError as exc:
            failures.append((skill_dir.as_posix(), str(exc)))
    entries.sort(key=lambda e: (e["category"], e["name"]))
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
    entries: list[dict], manifest_skill_count: int, failures: list[tuple[str, str]]
) -> tuple[list[str], bool]:
    """Build the E4 audit lines and own the single pass/fail verdict.

    Returns ``(lines, ok)``: per-category counts, one line per failure, the
    count-equality check, and the trailing ``AUDIT ok`` / ``AUDIT MISMATCH``
    line — ``ok`` is the verdict that line carries (no failures AND
    ``registry-count == manifest-skill-count``), so callers never re-derive the
    predicate.
    """
    by_category: dict[str, int] = {}
    for entry in entries:
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1
    lines = [f"AUDIT category={cat} skills={by_category[cat]}" for cat in sorted(by_category)]
    for path, reason in failures:
        lines.append(f"AUDIT failure dir={path} reason={reason}")
    lines.append(f"AUDIT manifest={manifest_skill_count} registry={len(entries)}")
    ok = not failures and manifest_skill_count == len(entries)
    lines.append("AUDIT ok" if ok else "AUDIT MISMATCH")
    return lines, ok


def main(argv: list[str] | None = None) -> int:
    """CLI: rebuild ``references/skill-registry.json`` from ``skills/`` (E4 audit)."""
    parser = argparse.ArgumentParser(
        description="Build references/skill-registry.json from the extracted skills/ tree."
    )
    parser.add_argument(
        "--skills-root",
        type=pathlib.Path,
        default=_DEFAULT_SKILLS_ROOT,
        help="Directory holding the extracted skills/<name>/ packages "
        "(default: <plugin-root>/skills).",
    )
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=_DEFAULT_MANIFEST,
        help="Skills manifest path (default: <plugin-root>/references/"
        "skills-manifest.json).",
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
    try:
        manifest = load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"skillregistry: cannot load skills manifest: {exc}\n")
        return 1

    skill_dirs = iter_skill_dirs(skills_root)
    entries, failures = build_entries(skills_root, skill_dirs, manifest)
    registry = build_registry(entries)
    schema_errors = validate_registry(registry)
    for err in schema_errors:
        sys.stderr.write(f"skillregistry: registry invalid: {err}\n")
    if schema_errors:
        return 1  # never write a registry that violates the schema

    manifest_skills = manifest.get("skills")
    manifest_skill_count = manifest.get(
        "skill_count", len(manifest_skills) if isinstance(manifest_skills, list) else 0
    )
    lines, ok = audit(entries, manifest_skill_count, failures)
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
