"""Skill extractor — unpacks the bundled ``Skills/`` zips into tracked ``skills/`` packages.

The 117 skill archives under ``Skills/<Category>/`` are a one-time import
source: this module extracts them **byte-identically** into ``skills/<name>/``
packages (``.kimi-plugin/plugin.json`` declares ``"skills": "./skills/"``, so
the extracted tree is what a git install registers) and anchors the result with
a committed sha256 manifest (``references/skills-manifest.json``). Zip content
is third-party **UNTRUSTED DATA** (SAFE-2): member bytes are copied verbatim,
never interpreted — the only reads are the frontmatter ``name`` parse (via the
``skillregistry`` module's ``parse_frontmatter``) used for grouping, plus the
entry-name confinement checks.

Duplicate archives coalesce: zips are grouped by frontmatter ``name`` and a
same-name group must be **byte-identical** (same member names, same bytes) —
an identical group yields ONE package dir plus an audit note (117 zips → 115
packages, 2 duplicates); a same-name group whose bytes differ is an audit
FAILURE, never a silent pick.

Determinism: member modes are fixed (``0o755`` for ``*.sh``, ``0o644``
otherwise — the zip ``external_attr`` is never trusted), members are planned
and written in sorted order, and the manifest carries no timestamps, so a
re-extract over an unchanged tree is a no-op diff. Confinement is enforced at
BOTH layers (SEC-1): the frontmatter ``name`` that builds the package dir must
be a single safe path segment (a strict allow-pattern — empty, dotted,
slashed, backslashed, or first-party-colliding names are plan FAILURES,
recorded, with nothing extracted), each member entry name must stay inside its
package dir (an empty name, an absolute path, a trailing ``/``, a backslash —
a Windows separator POSIX-only parsing would miss — or a ``..`` segment is
rejected), and the joined write target is re-validated against ``out_root``
before a single byte of that plan is written (a plan carrying an unsafe entry
is a failure, so the real CLI never half-extracts).

The CLI is validate → audit → write with **no partial writes**: the manifest is
validated against the ``skills-manifest`` / ``skills-manifest-entry`` schemas
(``scripts/validate.py``) and the audit must be clean before the manifest is
committed to disk. ``--verify`` re-hashes the on-disk tree against the
committed manifest (missing file, hash drift, byte-size drift, extra file) and
exits non-zero on any mismatch — the zip-free integrity gate CI runs.

:func:`plan_extractions`, :func:`build_manifest` and :func:`verify_manifest`
are filesystem READERS; :func:`validate_manifest` and :func:`audit` are pure;
:func:`extract` and :func:`main` are the WRITERS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import zipfile

# When run directly as ``python3 scripts/skillextract.py`` the interpreter puts
# ``scripts/`` (not the repo root) on ``sys.path[0]``, so ``from scripts import ...``
# would fail. Put the plugin root on the path so the package imports resolve both when
# run directly and when imported as ``scripts.skillextract`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import skillregistry, validate  # noqa: E402  (path shim precedes this import)

# The zip import source lives at <plugin-root>/Skills, the extracted packages at
# <plugin-root>/skills, and the manifest at <plugin-root>/references (same
# resolution idiom as scripts/validate.py). ``out_root`` is the REPO ROOT:
# plan dirs are repo-relative ("skills/<name>").
_DEFAULT_SKILLS_ROOT = _ROOT / "Skills"
_DEFAULT_OUT_ROOT = _ROOT
_DEFAULT_MANIFEST = _ROOT / "references" / "skills-manifest.json"

MANIFEST_VERSION = 2

# Deterministic member modes — the zip external_attr is never trusted.
_MODE_EXEC = 0o755  # *.sh members
_MODE_FILE = 0o644  # everything else

# A package dir is built from the UNTRUSTED frontmatter ``name``: it must be a
# single safe path segment. The strict allow-pattern below matches every one
# of the 115 shipped names (pinned by a committed-data test — if a future real
# name ever fails it, widen the pattern minimally and document why). The
# pattern alone excludes empty names, ``.`` / ``..``, and any ``/`` or
# backslash; a collision with a first-party orchestrator dir
# (:data:`skillregistry.FIRST_PARTY_DIRS`) is excluded separately so a
# vendored archive can never overwrite the plugin machinery. Anything else is
# a plan FAILURE, never a sanitized rewrite.
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _is_safe_package_name(name: str) -> bool:
    """True iff a frontmatter ``name`` is a single safe package-dir segment."""
    return bool(_NAME_RE.match(name)) and name not in skillregistry.FIRST_PARTY_DIRS


def _read_members(zip_path: pathlib.Path) -> dict[str, bytes]:
    """Read one archive fully in memory: ``{entry_name: bytes}`` (dirs skipped).

    Raises ``ValueError`` on an unreadable archive or a missing top-level
    SKILL.md. The bytes are UNTRUSTED DATA (SAFE-2) — returned, never
    interpreted.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            members: dict[str, bytes] = {}
            for info in archive.infolist():
                if info.is_dir() or info.filename.endswith("/"):
                    continue
                members[info.filename] = archive.read(info.filename)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"not a readable zip archive: {exc}") from exc
    if "SKILL.md" not in members:
        raise ValueError("archive has no top-level SKILL.md")
    return members


def _is_safe_entry(entry_name: str) -> bool:
    """True iff a zip entry name stays inside its package dir when extracted.

    Entry names come straight from the archive (untrusted): an empty name, an
    absolute path, a trailing ``/`` (a directory, not a file), a backslash
    (the Windows separator — POSIX-only parsing would let a ``..``-prefixed
    backslash name traverse on Windows), or a ``..`` segment would escape the
    package dir.
    """
    if not entry_name or entry_name.endswith("/") or "\\" in entry_name:
        return False
    pure = pathlib.PurePosixPath(entry_name)
    return not pure.is_absolute() and ".." not in pure.parts


def plan_extractions(
    skills_root: pathlib.Path,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Group ``Skills/*/*.zip`` by frontmatter ``name`` into extraction plans.

    Returns ``(plans, failures)``. A plan is::

        {"name": ..., "category": ...,   # the canonical zip's parent dir
         "dir": "skills/<name>",         # repo-relative package dir
         "zip": canonical_zip_path,      # the single archive members come from
         "members": [entry_name, ...],   # sorted entry names
         "sources": [zip_path, ...]}     # every coalesced archive, sorted

    A same-name group whose member sets are byte-identical coalesces into one
    plan (the first archive in ``(category, filename)`` order is canonical); a
    group that differs in bytes is a FAILURE, never a silent pick. An archive
    whose frontmatter ``name`` is not a single safe path segment
    (:func:`_is_safe_package_name` — the name builds the package dir, so a
    hostile name is a traversal / first-party-overwrite vector), or a group
    carrying an unsafe entry name, is likewise a failure, so a bad archive can
    never be half-extracted. Plans are sorted by ``(category, name)`` for a
    deterministic build.
    """
    groups: dict[str, list[tuple[pathlib.Path, dict[str, bytes]]]] = {}
    failures: list[tuple[str, str]] = []
    zip_paths = sorted(
        skills_root.glob("*/*.zip"), key=lambda p: (p.parent.name, p.name)
    )
    for zip_path in zip_paths:
        try:
            members = _read_members(zip_path)
            fields = skillregistry.parse_frontmatter(
                members["SKILL.md"].decode("utf-8", errors="replace")
            )
        except ValueError as exc:
            failures.append((zip_path.as_posix(), str(exc)))
            continue
        name = fields.get("name", "").strip()
        if not _is_safe_package_name(name):
            # The zip path (not the hostile name) anchors the failure line.
            failures.append((zip_path.as_posix(), f"unsafe skill name: {name!r}"))
            continue
        groups.setdefault(name, []).append((zip_path, members))

    plans: list[dict] = []
    for name in sorted(groups):
        group = groups[name]
        canonical_path, canonical_members = group[0]
        unsafe = sorted(
            entry_name for entry_name in canonical_members
            if not _is_safe_entry(entry_name)
        )
        if unsafe:
            failures.append(
                (name, "unsafe zip entry name(s): " + ", ".join(repr(e) for e in unsafe))
            )
            continue
        differing = sorted(
            zip_path.as_posix()
            for zip_path, members in group
            if members != canonical_members
        )
        if differing:
            failures.append(
                (name, "same-name archives differ in bytes: " + ", ".join(differing))
            )
            continue
        plans.append({
            "name": name,
            "category": canonical_path.parent.name,
            "dir": f"skills/{name}",
            "zip": canonical_path,
            "members": sorted(canonical_members),
            "sources": sorted(zip_path for zip_path, _ in group),
        })
    plans.sort(key=lambda plan: (plan["category"], plan["name"]))
    return plans, failures


def _confined_target(root: pathlib.Path, plan_dir: str, entry_name: str) -> pathlib.Path:
    """Resolve one member's on-disk target, confined under ``root``.

    The enforcement twin of :func:`_is_safe_entry`, applied to BOTH inputs and
    to the joined path: raises ``ValueError`` on an unsafe entry name, on an
    unsafe package dir, or when the resolved target would escape ``root``
    (a ``..`` resolution escape or a symlinked package dir pointing outside).
    Defense in depth — the write sink stays safe even if a future caller
    bypasses plan-time validation.
    """
    if not _is_safe_entry(entry_name):
        raise ValueError(f"unsafe zip entry name: {entry_name!r}")
    if not _is_safe_entry(plan_dir):
        raise ValueError(f"unsafe package dir: {plan_dir!r}")
    root_path = pathlib.Path(root).resolve()
    target = root_path / plan_dir / entry_name
    resolved = target.resolve()
    if resolved != root_path and root_path not in resolved.parents:
        raise ValueError(f"zip entry escapes the output root: {entry_name!r}")
    return target


def extract(plans: list[dict], out_root: pathlib.Path) -> int:
    """Write every planned member byte-identically; return the file count.

    Each member lands at ``<out_root>/<dir>/<entry>`` with a deterministic mode
    (``0o755`` for ``*.sh``, ``0o644`` otherwise); the plan's single canonical
    archive is opened exactly once. Raises ``ValueError`` on an entry name or
    package dir that would escape ``out_root``.
    """
    written = 0
    for plan in plans:
        with zipfile.ZipFile(plan["zip"]) as archive:
            for entry_name in plan["members"]:
                target = _confined_target(out_root, plan["dir"], entry_name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry_name))
                target.chmod(_MODE_EXEC if entry_name.endswith(".sh") else _MODE_FILE)
                written += 1
    return written


def build_manifest(plans: list[dict], out_root: pathlib.Path) -> dict:
    """Hash the extracted tree under ``out_root`` into the manifest document.

    Stable key order, sorted skills/files, no timestamps — a rebuild over an
    unchanged tree is a no-op diff. Pure reader (never writes).
    """
    out_root = pathlib.Path(out_root)
    skills: list[dict] = []
    file_count = 0
    for plan in plans:
        files: list[dict] = []
        for entry_name in plan["members"]:
            target = _confined_target(out_root, plan["dir"], entry_name)
            data = target.read_bytes()
            files.append({  # stable key order — keep in sync with the docs
                "path": f"{plan['dir']}/{entry_name}",
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            })
            file_count += 1
        skills.append({  # stable key order — keep in sync with the schema
            "name": plan["name"],
            "category": plan["category"],
            "dir": plan["dir"],
            "files": files,
        })
    return {
        "version": MANIFEST_VERSION,
        "skill_count": len(skills),
        "file_count": file_count,
        "skills": skills,
    }


def verify_manifest(manifest: dict, root: pathlib.Path) -> list[str]:
    """Re-hash the tree against ``manifest``; return every mismatch ([] = intact).

    Detects a missing file, sha256 drift, byte-size drift, any EXTRA file
    inside a manifest skill dir the manifest does not record (per-dir
    completeness), and any EXTRA package dir on disk the manifest does not
    record (the stowaway sweep: ``skills/`` itself is enumerated, minus the
    first-party orchestrator dirs — a stray package can never hide behind a
    green per-dir check). Pure reader — nothing is written.
    """
    root = pathlib.Path(root)
    mismatches: list[str] = []
    skills = manifest.get("skills")
    if not isinstance(skills, list):
        return ["manifest has no skills list"]
    for skill in skills:
        recorded: set[str] = set()
        for file_entry in skill.get("files", []):
            rel = file_entry.get("path", "")
            recorded.add(rel)
            target = root / rel
            if not target.is_file():
                mismatches.append(f"missing file: {rel}")
                continue
            data = target.read_bytes()
            if len(data) != file_entry.get("bytes"):
                mismatches.append(
                    f"byte-size drift: {rel} "
                    f"(manifest={file_entry.get('bytes')} disk={len(data)})"
                )
            if hashlib.sha256(data).hexdigest() != file_entry.get("sha256"):
                mismatches.append(f"hash drift: {rel}")
        skill_dir = root / skill.get("dir", "")
        if skill_dir.is_dir():
            for path in sorted(skill_dir.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(root).as_posix()
                    if rel not in recorded:
                        mismatches.append(f"extra file: {rel}")
    # Stowaway sweep: a package dir on disk the manifest does not anchor is
    # drift even when every manifest dir is intact. First-party dirs are
    # excluded by the shared scan (they are plugin machinery, never vendored
    # packages).
    skills_root = root / "skills"
    if skills_root.is_dir():
        manifest_dirs = {skill.get("dir", "") for skill in skills}
        for package_dir in skillregistry.iter_skill_dirs(skills_root):
            if f"skills/{package_dir.name}" not in manifest_dirs:
                mismatches.append(f"extra package dir: skills/{package_dir.name}")
    return mismatches


def validate_manifest(manifest: dict) -> list[str]:
    """Validate a manifest document against the canonical schemas; [] means valid."""
    errors = validate.validate(manifest, "skills-manifest")
    skills = manifest.get("skills")
    if isinstance(skills, list):
        if manifest.get("skill_count") != len(skills):
            errors.append("skill_count does not match len(skills)")
        file_total = 0
        for i, entry in enumerate(skills):
            for err in validate.validate(entry, "skills-manifest-entry"):
                errors.append(f"skills[{i}]: {err}")
            if isinstance(entry.get("files"), list):
                file_total += len(entry["files"])
        if manifest.get("file_count") != file_total:
            errors.append("file_count does not match the summed len(files)")
    return errors


def audit(
    plans: list[dict], failures: list[tuple[str, str]], manifest: dict
) -> tuple[list[str], bool]:
    """Build the E4 audit lines and own the single pass/fail verdict.

    Returns ``(lines, ok)``: per-category package counts, one line per
    coalesced duplicate group, one line per failure, the zips-vs-packages
    reconciliation, and the trailing ``AUDIT ok`` / ``AUDIT MISMATCH`` line —
    ``ok`` is the verdict that line carries (no failures AND a manifest
    consistent with the plans), so callers never re-derive the predicate.
    """
    by_category: dict[str, int] = {}
    for plan in plans:
        by_category[plan["category"]] = by_category.get(plan["category"], 0) + 1
    lines = [f"AUDIT category={cat} packages={by_category[cat]}" for cat in sorted(by_category)]
    zip_count = 0
    coalesced = 0
    for plan in plans:
        sources = plan.get("sources", [])
        zip_count += len(sources)
        if len(sources) > 1:
            coalesced += len(sources) - 1
            lines.append(
                f"AUDIT coalesced name={plan['name']} "
                f"archives={len(sources)} dir={plan['dir']}"
            )
    for target, reason in failures:
        lines.append(f"AUDIT failure target={target} reason={reason}")
    member_count = sum(len(plan["members"]) for plan in plans)
    lines.append(
        f"AUDIT zips={zip_count} packages={len(plans)} "
        f"coalesced={coalesced} files={manifest.get('file_count')}"
    )
    ok = (
        not failures
        and manifest.get("skill_count") == len(plans)
        and manifest.get("file_count") == member_count
    )
    lines.append("AUDIT ok" if ok else "AUDIT MISMATCH")
    return lines, ok


def main(argv: list[str] | None = None) -> int:
    """CLI: extract ``Skills/`` into ``skills/`` + write the manifest, or ``--verify``."""
    parser = argparse.ArgumentParser(
        description="Extract the bundled Skills/ zips into skills/<name>/ packages "
        "and write references/skills-manifest.json (audit-gated, no partial writes)."
    )
    parser.add_argument(
        "--skills-root",
        type=pathlib.Path,
        default=_DEFAULT_SKILLS_ROOT,
        help="Directory holding <category>/*.zip (default: <plugin-root>/Skills).",
    )
    parser.add_argument(
        "--out-root",
        type=pathlib.Path,
        default=_DEFAULT_OUT_ROOT,
        help="Repo root the skills/ tree is extracted under (default: plugin root).",
    )
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=_DEFAULT_MANIFEST,
        help="Manifest path (default: <plugin-root>/references/skills-manifest.json).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the committed manifest against the on-disk tree; exit "
        "non-zero on any mismatch (writes nothing).",
    )
    args = parser.parse_args(argv)

    if args.verify:
        try:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"skillextract: cannot load manifest: {exc}\n")
            return 1
        schema_errors = validate_manifest(manifest)
        for err in schema_errors:
            sys.stderr.write(f"skillextract: manifest invalid: {err}\n")
        if schema_errors:
            return 1  # a schema-invalid manifest proves nothing
        mismatches = verify_manifest(manifest, args.out_root)
        for mismatch in mismatches:
            sys.stdout.write(f"VERIFY mismatch: {mismatch}\n")
        if mismatches:
            sys.stdout.write(f"VERIFY FAILED ({len(mismatches)} mismatch(es))\n")
            return 1
        sys.stdout.write(
            f"VERIFY ok skills={manifest['skill_count']} files={manifest['file_count']}\n"
        )
        return 0

    if not args.skills_root.is_dir():
        sys.stderr.write(f"skillextract: skills root not found: {args.skills_root}\n")
        return 1

    plans, failures = plan_extractions(args.skills_root)
    if failures:
        # A failed plan extracts NOTHING — no partial writes, ever.
        lines, _ok = audit(plans, failures, {
            "skill_count": len(plans),
            "file_count": sum(len(plan["members"]) for plan in plans),
        })
        for line in lines:
            sys.stdout.write(line + "\n")
        return 1

    written = extract(plans, args.out_root)
    manifest = build_manifest(plans, args.out_root)
    schema_errors = validate_manifest(manifest)
    for err in schema_errors:
        sys.stderr.write(f"skillextract: manifest invalid: {err}\n")
    if schema_errors:
        return 1  # never write a manifest that violates the schema

    lines, ok = audit(plans, failures, manifest)
    for line in lines:
        sys.stdout.write(line + "\n")
    if not ok:
        return 1  # failed audit — never write a partial/failed manifest

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    sys.stdout.write(
        f"skillextract: wrote {args.manifest} ({len(plans)} packages, {written} files)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
