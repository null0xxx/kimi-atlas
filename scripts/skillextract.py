"""Skill extractor — unpacks the bundled ``Skills/`` zips into tracked ``skills/`` packages.

The 117 skill archives under ``Skills/<Category>/`` are a one-time import
source: this module extracts them **byte-identically** into ``skills/<name>/``
packages (Claude Code auto-discovers ``skills/`` at the plugin root, so
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
package dir (an empty, ``.`` or ``..`` segment, or a backslash — a Windows
separator POSIX-only parsing would miss — is rejected, and the segments are
read RAW: normalizing first would turn ``"SKILL.md/."`` into a clean-looking
``SKILL.md`` that ALIASES a second member onto an already-audited target), and
the joined write target is re-validated against ``out_root`` before a single
byte of that plan is written (a plan carrying an unsafe entry is a failure
recorded before the write phase starts, so no hostile archive is ever
partially extracted).

Name shapes alone do not converge, so the group is also held to an INVARIANT
over the resolved targets (:func:`_target_conflicts`): its members must claim
DISTINCT, mutually non-nesting on-disk targets, or the whole group is a plan
FAILURE. That is what stops the two aliases no name ban catches — ``SKILL.md``
beside ``skill.md`` on a case-insensitive filesystem, and a plain ``sub``
beside ``sub/x.md``.

The CLI is validate → audit → write. A plan-time failure extracts NOTHING at
all. A write-time failure is a recorded audit failure rather than a traceback,
but every member already written STAYS: **writes may be partial**, and no path
in this module deletes a directory or a file it did not create in this process.

That is the contract stated as what the code delivers. The promise is not "no
partial writes" but **your undo is clean**. ``skills/`` is committed
source-of-truth (the ``Skills/`` zips are a one-time import and need not even
be present), so git — not this tool — is the transaction log: :func:`main`
REFUSES to start when anything this run writes is dirty in a git worktree,
which is what makes ``git checkout``/``git clean`` restore exactly what the
operator had, and on failure it PRINTS those exact commands and runs none of
them.

"Anything this run writes" is BOTH destinations (:func:`_written_pathspecs`),
not just the package tree. The manifest is written too, and scoping the
precondition to ``skills/`` alone was a measured hole: ``--out-root <scratch>``
with no ``--manifest`` extracted into the scratch dir while still aiming the
manifest write at the PLUGIN root, so a 1-package scratch run replaced the
committed 115-package manifest — the dirty check had been evaluated against the
scratch root (a non-worktree: warning only), and the warning named ``skills/``,
which is not where the damage landed. Two changes close it: ``--manifest``
DEFAULTS off ``--out-root`` instead of off the plugin root, so a redirected
extraction cannot aim back at the repo; and the dirty pathspec plus the printed
recovery both cover the manifest whenever it lives under ``out_root``.

``--allow-dirty`` overrides the refusal. A destination that is not a git
worktree is legitimate (a scratch extraction) and only warns — but a
destination that IS a worktree git could not answer for (a held ``index.lock``,
an interrupted rebase, permissions, a timeout) is REFUSED, because failing open
there would silently skip the precondition over a genuinely dirty subtree while
telling the operator there was no worktree at all. An ``rmtree`` unwind lived
here and was REMOVED: it deleted pre-existing and untracked files the failure
never touched, which is what an undo built inside a tool that runs inside a VCS
costs.

The manifest is validated against the ``skills-manifest`` /
``skills-manifest-entry`` schemas (``scripts/validate.py``) and the audit must
be clean before the manifest is committed to disk, so a failed run never leaves
a NEW manifest behind and never damages the old one: the document is staged as
a sibling temp file and swapped in with ``os.replace``, because ``write_text``
opens ``'w'`` and TRUNCATES first — a full disk there used to leave the
committed anchor empty or half-written. ``--verify`` re-hashes the on-disk tree
against the committed manifest (missing file, hash drift, byte-size drift,
extra file) and exits non-zero on any mismatch — the zip-free integrity gate CI
runs.

:func:`plan_extractions`, :func:`build_manifest` and :func:`verify_manifest`
are filesystem READERS (as is the ``git status`` probe :func:`_dirty_subtree`,
which shells out but writes nothing); :func:`validate_manifest` and
:func:`audit` are pure; :func:`extract` and :func:`main` are the WRITERS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import unicodedata
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

# The manifest path RELATIVE to out_root — never an absolute plugin-root
# default. ``--manifest`` is resolved against ``--out-root`` (see :func:`main`)
# so redirecting the extraction cannot leave the manifest write pointed at the
# plugin's own committed anchor.
_MANIFEST_RELPATH = "references/skills-manifest.json"

# The single repo-relative subtree every package dir lives under. It is the one
# thing three separate concerns must agree on: the plan-dir prefix, the subtree
# the dirty precondition scopes to (unrelated dirt elsewhere in the repo is NOT
# this run's business), and the path the recovery hint names.
_PACKAGE_ROOT = "skills"

MANIFEST_VERSION = 2

# git status lines shown before the refusal is summarised — a 715-line refusal
# is a wall, not a message. The COUNT is always exact; only the listing is cut.
_DIRTY_PREVIEW = 10

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

    Raises ``ValueError`` on ANY unreadable archive or a missing top-level
    SKILL.md, so :func:`plan_extractions` records an AUDIT failure line: a bad
    archive is a recorded FAILURE, never a traceback. The archive is UNTRUSTED
    DATA (SAFE-2), and ``zipfile`` reports unreadability through three
    unrelated exception hierarchies — catching only ``BadZipFile`` let two of
    them escape the audit contract entirely:

    * ``zipfile.BadZipFile`` — not a zip, truncated, or a corrupt payload
      (``zipfile`` funnels a failed inflate here rather than raising
      ``zlib.error``).
    * ``RuntimeError`` — an ENCRYPTED member: ``read`` refuses without a
      password. ``NotImplementedError`` (an unsupported compression method
      such as deflate64) is a ``RuntimeError`` SUBCLASS and arrives here too.
    * ``OSError`` — the archive file itself unreadable mid-read (permissions,
      a vanished file, an I/O error).

    ``RecursionError`` is re-raised FIRST, un-wrapped. Every call in the
    guarded block belongs to ``zipfile``, which is why the broad
    ``RuntimeError`` is safe for the two causes above — but that is not the
    absolute claim it reads like: ``RecursionError`` is a ``RuntimeError``
    SUBCLASS, so a genuine runaway-recursion defect (ours or the stdlib's)
    would otherwise be laundered into ``unreadable zip archive:
    RecursionError: ...`` and blamed on the operator's file. A defect must stay
    a traceback. The bytes are returned, never interpreted.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            members: dict[str, bytes] = {}
            for info in archive.infolist():
                if info.is_dir() or info.filename.endswith("/"):
                    continue
                members[info.filename] = archive.read(info.filename)
    except RecursionError:
        raise  # a defect, not an unreadable archive — never blame the zip
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        # The exception TYPE names the cause (corrupt vs encrypted vs I/O) and
        # the audit line is the only record of it, so carry it.
        raise ValueError(
            f"unreadable zip archive: {type(exc).__name__}: {exc}"
        ) from exc
    if "SKILL.md" not in members:
        raise ValueError("archive has no top-level SKILL.md")
    return members


def _is_safe_entry(entry_name: str) -> bool:
    """True iff a zip entry name stays inside its package dir when extracted.

    Entry names come straight from the archive (untrusted) and are judged on
    their RAW ``/``-separated segments, BEFORE ``PurePosixPath`` is allowed to
    normalize them: an empty segment (an empty name, a leading or trailing
    ``/``, or a ``//``), a ``.`` segment, and a ``..`` segment are all
    rejected. Normalizing first would hide two of those three — ``"."`` and
    ``"SKILL.md/."`` both parse to a name with no ``.`` left in it, and the
    second is the dangerous one: it ALIASES a second member onto an
    already-planned target, so sorted-order extraction lets the alias
    overwrite the audited bytes while ``--verify`` re-normalizes onto that
    same file and still reports the tree intact. A backslash — the Windows
    separator POSIX-only parsing would miss, letting a ``..``-prefixed
    backslash name traverse on Windows — is rejected outright.

    The normalized guards are kept as a second layer (the SEC-1 belt-and-braces
    the module applies throughout): the entry stays confined even if the raw
    scan is ever loosened.
    """
    if not entry_name or entry_name.endswith("/") or "\\" in entry_name:
        return False
    # RAW segments — this must precede every PurePosixPath-derived check below.
    if any(segment in ("", ".", "..") for segment in entry_name.split("/")):
        return False
    # Second layer: the normalized view. Subsumed by the scan above today —
    # kept so a loosened raw scan cannot on its own reopen the escape.
    pure = pathlib.PurePosixPath(entry_name)
    if not pure.parts:
        return False
    return not pure.is_absolute() and ".." not in pure.parts


def _simple_fold(segment: str) -> str:
    """Case-fold one segment the way a real filesystem folds a NAME.

    PER CODEPOINT: simple uppercase, then simple lowercase — and each mapping
    is taken only when it stays ONE codepoint, which is precisely what makes it
    "simple" rather than "full". That composition is not decoration; each half
    models one destination and neither half alone is correct:

    * The uppercase half is the NTFS rule. Windows compares names through the
      volume's ``$UpCase`` table, a per-codepoint SIMPLE UPPERCASE map.
    * The lowercase half is the rule the case-insensitive Apple filesystems
      apply, a per-codepoint lowercase-based fold.

    The invariant refuses when EITHER destination merges two names, so the fold
    has to merge under either — and the two are not inverses of each other.
    ``str.lower()`` alone accepted a REAL alias: ``aσ.md`` and ``aς.md`` (sigma
    vs FINAL sigma) lower to different strings, but both upper to ``AΣ.MD``,
    so NTFS hands them ONE file and sorted extraction would let the second
    overwrite the audited bytes of the first while ``--verify`` re-hashed that
    single file for both recorded paths and reported the tree intact. A
    whole-Unicode scan finds 21 such classes, not one — final sigma, the micro
    sign, the Greek symbol variants, the historic Cyrillic letters, long s, and
    Turkish DOTLESS ı against ``i`` — so a targeted ``replace`` of the one
    codepoint that happened to be noticed would have left twenty more open.

    Skipping the LENGTH-CHANGING mappings is what keeps this from becoming
    ``str.casefold()`` again. ``casefold()`` is FULL Unicode case folding, for
    caseless STRING matching: it maps ``ß`` to ``ss`` and ``ﬁ`` to ``fi``. No
    filesystem does that, so ``straße.md`` and ``strasse.md`` really are two
    distinct files everywhere, and refusing that archive printed a message that
    was untrue on the machine printing it. Python's ``str.upper()`` is full
    uppercase too (``ß`` → ``SS``), so a naive ``.upper().lower()`` on the whole
    string would reintroduce exactly that false reject; taking a mapping only
    when it is length-preserving is what makes this the SIMPLE map the
    filesystems actually use.

    MEASURED against every Unicode codepoint: idempotent (so the key is a
    well-defined canonical form), it merges every class single-codepoint
    ``casefold()`` merges, and the only class it merges that ``casefold()``
    does not is ``I``/``i``/dotless ``ı`` — a true positive on NTFS, not a
    false reject.

    RESIDUALS, stated rather than implied away. This models per-codepoint
    folding only: a filesystem rule that is multi-codepoint or locale-dependent
    is out of scope, and so is HFS+'s own normalization table, which is neither
    NFC nor NFD. Both are stated because the guarantee here is "no alias a
    per-codepoint fold can see", never "no alias".
    """
    folded: list[str] = []
    for char in segment:
        upper = char.upper()
        char = upper if len(upper) == 1 else char  # simple upper, else unchanged
        lower = char.lower()
        folded.append(lower if len(lower) == 1 else char)
    return "".join(folded)


def _target_key(entry_name: str) -> tuple[str, ...]:
    """The on-disk target identity a member CLAIMS, as normalized segments.

    Two members share a key exactly when a real filesystem can hand them the
    same file. Each segment is Unicode-normalized (Apple filesystems treat the
    composed and decomposed spellings of ``é`` as one name), case-folded with
    :func:`_simple_fold` (macOS APFS is case-insensitive by default, as is
    Windows — see there for why it is neither ``lower()`` nor ``casefold()``)
    and stripped of trailing dots and spaces (the Win32 path layer drops them),
    so ``SKILL.md``, ``skill.md``, ``SKILL.md.`` and ``SKILL.md `` all key
    alike. A segment that is EMPTY after the strip (``"..."``, ``"  "``) names
    nothing on disk and is caller-rejected.
    """
    return tuple(
        _simple_fold(unicodedata.normalize("NFC", segment)).rstrip(". ")
        for segment in entry_name.split("/")
    )


def _target_conflicts(entry_names: list[str]) -> list[str]:
    """Return why ``entry_names`` fail to map to distinct targets ([] = they do).

    An INVARIANT, deliberately not another name ban: shape enumeration cannot
    converge, because the list of unsafe entry-name shapes has no end. A
    correct-looking predicate has already been defeated twice here — first by
    ``"SKILL.md/."``, then by a plain ``"sub"`` sitting beside ``"sub/x.md"``,
    which carries no ``.`` at all. Injectivity over the RESOLVED TARGETS is
    checkable and complete instead: N members must claim N distinct,
    mutually non-nesting targets whatever their names look like. Do not replace
    this with more shape bans.

    Two rules, both keyed on :func:`_target_key`:

    * COLLISION — two members claiming one target. The alias would overwrite
      the audited member in sorted order while the frontmatter classification
      read the other one, and ``--verify`` re-hashes that single file for BOTH
      recorded paths and still reports the tree intact: silent content
      substitution. An empty-after-strip segment is rejected here too — it
      names no target at all.

      The message says **may** resolve, and names the filesystems that make it
      so, because the collision is a PROPERTY OF THE DESTINATION, not of the
      archive: ``SKILL.md`` beside ``skill.md`` really is two files on ext4.
      The refusal is still right — the archive is unshippable to the platforms
      this plugin installs on — but a line claiming they DO collide would be
      false on the very machine that printed it.
    * PARENT CONSISTENCY — one member's target is a proper path prefix of
      another's (``"sub"`` before ``"sub/x.md"``). Sorted-order extraction
      writes ``sub`` as a regular FILE, and the nested member then dies in
      ``mkdir(parents=True, exist_ok=True)`` with a FileExistsError.

    Either way the whole group is a plan FAILURE, so nothing is extracted.
    """
    conflicts: list[str] = []
    claimed: dict[tuple[str, ...], str] = {}
    for entry_name in sorted(entry_names):
        key = _target_key(entry_name)
        if "" in key:
            conflicts.append(f"{entry_name!r} has a segment that names no file on disk")
        elif key in claimed:
            conflicts.append(
                f"{entry_name!r} and {claimed[key]!r} may resolve to one target "
                "on a case-insensitive or name-normalizing filesystem"
            )
        else:
            claimed[key] = entry_name
    for key, entry_name in sorted(claimed.items()):
        for depth in range(1, len(key)):
            parent = claimed.get(key[:depth])
            if parent is not None:
                conflicts.append(f"{parent!r} is a parent path of {entry_name!r}")
    return conflicts


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
    hostile name is a traversal / first-party-overwrite vector), a group
    carrying an unsafe entry name, or a group whose members do not map to
    distinct, non-nesting on-disk targets (:func:`_target_conflicts`) is
    likewise a failure, so a bad archive can never be half-extracted. Plans are
    sorted by ``(category, name)`` for a deterministic build.
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
        # Every member is name-safe; they must still claim DISTINCT, non-nesting
        # targets. This is the invariant that closes the alias shapes no name
        # ban catches — see _target_conflicts for why it is not more bans.
        conflicts = _target_conflicts(list(canonical_members))
        if conflicts:
            failures.append(
                (name, "colliding zip entry target(s): " + ", ".join(conflicts))
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
            "dir": f"{_PACKAGE_ROOT}/{name}",
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
    package dir that would escape ``out_root``, and re-raises whatever the
    write itself raised.

    **Writes may be partial, and this function DELETES NOTHING.** A member can
    be name-legal yet write-illegal (an embedded NUL raises ``ValueError`` from
    the path layer, a segment past ``NAME_MAX`` raises ``ENAMETOOLONG``) and
    ``out_root`` can be read-only or full — no name predicate can foresee any
    of it. When it happens, the members already written STAY on disk and the
    exception propagates to :func:`main`, which records it as an audit failure
    and PRINTS the operator's recovery command. Nothing in this module removes
    a directory or a file it did not create in this process.

    That is a deliberate reversal, not an omission. An ``rmtree`` of the
    in-flight package dir stood here and caused measured data loss: a package
    dir is not this run's property, so unwinding it deleted a pre-existing
    committed file and an untracked stray the failure had never touched, and
    ``ignore_errors=True`` made a failed unwind indistinguishable from a clean
    one. ``skills/`` is committed source-of-truth against eight readers, so the
    undo belongs to git, which already has one. :func:`main` earns that by
    REFUSING to start over a dirty subtree — see :func:`_dirty_subtree`.
    Stage-and-swap is not the missing answer either: ``os.replace`` will not
    overwrite a non-empty directory, so the swap is two steps with a window in
    which ``skills/`` does not exist, which trades a rare failure-path bug for
    a concurrency hazard against a host that auto-discovers that directory.

    No manifest is written for a failed run, so ``--verify`` still anchors the
    tree against the last good manifest.
    """
    written = 0
    for plan in plans:
        with zipfile.ZipFile(plan["zip"]) as archive:
            for entry_name in plan["members"]:
                # Re-validated per member: this is the write sink's own
                # confinement, independent of plan-time validation.
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
    skills_root = root / _PACKAGE_ROOT
    if skills_root.is_dir():
        manifest_dirs = {skill.get("dir", "") for skill in skills}
        for package_dir in skillregistry.iter_skill_dirs(skills_root):
            package_rel = f"{_PACKAGE_ROOT}/{package_dir.name}"
            if package_rel not in manifest_dirs:
                mismatches.append(f"extra package dir: {package_rel}")
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
    plans: list[dict], manifest: dict, failures: list[tuple[str, str]]
) -> tuple[list[str], bool]:
    """Build the E4 audit lines and own the single pass/fail verdict.

    ``failures`` comes LAST, matching the sibling
    :func:`skillregistry.audit` — the two modules share one audit-line
    contract, so a cross-module copy-paste must not be able to slot the
    failure list into a different position and still compile.

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


def _written_pathspecs(
    out_root: pathlib.Path, manifest: pathlib.Path
) -> list[str]:
    """Every ``out_root``-relative path THIS RUN writes, as git pathspecs.

    The dirty precondition and the printed undo are both only as honest as this
    list. ``skills/`` was once the whole of it, and that was wrong by one
    directory: the run also writes the manifest, so an operator with
    uncommitted edits to a TRACKED ``references/skills-manifest.json`` got no
    refusal, no warning, and a recovery command
    (``git checkout -- skills``) that restored nothing where the damage was.

    A manifest OUTSIDE ``out_root`` is deliberately omitted: it belongs to no
    pathspec of this worktree, and git would reject it. That is not a silent
    gap — :func:`main` derives the manifest FROM ``out_root`` by default, so
    the outside case only arises when the operator named it explicitly.
    """
    pathspecs = [_PACKAGE_ROOT]
    try:
        relative = pathlib.Path(manifest).resolve().relative_to(
            pathlib.Path(out_root).resolve()
        )
    except (OSError, ValueError):
        return pathspecs  # outside out_root (or unresolvable): not our pathspec
    posix = relative.as_posix()
    # A manifest already inside skills/ is covered by the package pathspec.
    if posix != "." and not posix.startswith(f"{_PACKAGE_ROOT}/"):
        pathspecs.append(posix)
    return pathspecs


# The four answers :func:`_dirty_subtree` can give. ABSENT and UNREADABLE were
# ONE answer (a bare ``None``) and had to be split, because they demand
# OPPOSITE responses: see that docstring.
_GIT_CLEAN = "clean"
_GIT_DIRTY = "dirty"
_GIT_ABSENT = "absent"          # not a worktree, or git is not installed
_GIT_UNREADABLE = "unreadable"  # a worktree git declined to answer for


def _dirty_subtree(
    root: pathlib.Path, pathspecs: list[str]
) -> tuple[str, list[str]]:
    """Classify ``<root>``'s worktree state for ``pathspecs``; ``(state, lines)``.

    The precondition that replaces the deleted rollback. This module writes
    into ``skills/`` and the manifest and can leave those writes PARTIAL, so
    the operator's undo has to be trustworthy: it is exactly trustworthy when
    those paths are clean, because ``git checkout``/``git clean`` then restores
    precisely what was there. A modified tracked file or an untracked stray
    under them is content that undo would destroy, so :func:`main` refuses.

    ``state`` is one of four, and the last two are the reason this returns a
    pair instead of ``list | None``:

    * :data:`_GIT_CLEAN` / :data:`_GIT_DIRTY` — git answered. ``lines`` carries
      the porcelain output (empty when clean).
    * :data:`_GIT_ABSENT` — ``root`` is not a git worktree, or git is not
      installed. "No VCS undo here" is a WARNING and never a refusal: a
      scratch-dir extraction is legitimate use and blocking it would be worse
      than the gap it closes.
    * :data:`_GIT_UNREADABLE` — ``root`` IS a worktree and the status query
      still failed (a held ``index.lock``, an interrupted rebase, permissions,
      the timeout). Collapsing this into ABSENT failed OPEN in the one place it
      must not: the refusal silently never fired over a genuinely dirty
      subtree, and the operator was told ``not a git worktree`` on a machine
      where that was FALSE. Fail-open is defensible for a real non-worktree; it
      is not defensible for "git is here, this IS a worktree, and I could not
      read it", so :func:`main` refuses on this one.

    That is why the worktree question is asked SEPARATELY, with
    ``rev-parse --is-inside-work-tree``, instead of being inferred from a
    non-zero ``git status``: a non-zero exit cannot tell the two apart.
    Shelling out to git is the established idiom here
    (``scripts/check_cc_migration_residue.py`` reads ``git ls-files`` the same
    way).

    The pathspecs SCOPE the verdict to what this run writes: dirt anywhere else
    in the operator's repo is none of its business. ``--`` terminates the
    options so a pathspec can never be read as a flag, and the argv list is
    passed to ``subprocess`` WITHOUT a shell.

    Known limit, stated rather than hidden: git-IGNORED files under those paths
    are invisible to ``git status`` and to ``git clean -fd`` alike, so an
    ignored file this run overwrites has no undo either way. Reporting them as
    dirt would refuse every extraction in a repo that ignores, say,
    ``__pycache__`` under ``skills/`` — a false reject, which this module ranks
    worse. They are left to the operator.
    """
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        # git itself could not be run at all — indistinguishable from having no
        # VCS, and warning is the right response to that.
        return _GIT_ABSENT, []
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return _GIT_ABSENT, []
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", *pathspecs],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return _GIT_UNREADABLE, []
    if proc.returncode != 0:
        # A worktree that would not answer. NOT parsed for dirt — no git error
        # message is ever mistaken for a porcelain line — and NOT downgraded to
        # ABSENT, which is what used to make the refusal disappear.
        return _GIT_UNREADABLE, []
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return (_GIT_DIRTY if lines else _GIT_CLEAN), lines


def _recovery_lines(
    root: pathlib.Path, pathspecs: list[str], under_git: bool
) -> list[str]:
    """The operator's undo for this run's writes — REPORTED, never executed.

    Naming the command is the whole point: this module performs no rollback, so
    a run that fails owes the operator the exact lines that undo it.
    ``git checkout`` restores tracked files the run overwrote and ``git clean``
    removes the ones it created; both are scoped to this run's pathspecs, so
    neither reaches anything else in the repo. Outside a worktree there is no
    undo to name, and saying so plainly beats printing a command that would not
    work.

    The manifest gets its OWN pair of lines rather than joining the package
    pathspec, and that is deliberate: MEASURED, ``git checkout -- a b`` fails
    ENTIRELY when one pathspec matches nothing git knows, so folding an
    untracked manifest into the ``skills/`` line would take the recovery that
    does work down with the one that cannot. Both commands are named because
    the manifest has two possible states and each needs a different one —
    ``checkout`` restores it when the run overwrote a COMMITTED manifest,
    ``clean`` removes it when the run CREATED one. ``git clean`` is quiet on a
    tracked or absent pathspec (measured), so the pair is always safe to paste;
    only the ``checkout`` of a never-committed manifest is rejected, and the
    trailing note says so rather than leaving the operator to find out.

    Callers supply their own leading sentence — the refusal and the
    write-failure report need different ones — so this returns the commands
    alone and never a mixed message.
    """
    if not under_git:
        return [
            f"{root} is not a git worktree, so there is no undo to run — "
            f"inspect {', '.join(pathspecs)} by hand.",
        ]
    lines = ["recover with (this tool runs neither):"]
    for pathspec in pathspecs:
        lines.append(f"  git -C {root} checkout -- {pathspec}")
        lines.append(f"  git -C {root} clean -fd {pathspec}")
    if len(pathspecs) > 1:
        lines.append(
            "for the manifest, ONE of its two lines applies: checkout restores "
            "it if it was COMMITTED (git rejects that pathspec if it was not), "
            "clean removes it if this run created it."
        )
    return lines


def _emit(lines: list[str]) -> None:
    """Write operator guidance to stderr, one prefixed line each.

    stdout stays MACHINE-READABLE (only ``AUDIT``/``VERIFY`` lines and the
    final success note); every human-facing message goes here, matching the
    ``skillextract: ...`` stderr convention the rest of :func:`main` uses.
    """
    for line in lines:
        sys.stderr.write(f"skillextract: {line}\n")


def main(argv: list[str] | None = None) -> int:
    """CLI: extract ``Skills/`` into ``skills/`` + write the manifest, or ``--verify``.

    Owns the write-side precondition this module trades a rollback for: a
    dirty write-set in a git worktree is a REFUSAL before any byte is written
    (``--allow-dirty`` overrides), a non-worktree destination is a warning and
    proceeds, a worktree git could not answer for is a refusal, and a
    write-time failure prints the operator's exact recovery command without
    running it.

    The write-set is BOTH destinations (:func:`_written_pathspecs`), and
    ``--manifest`` defaults off ``--out-root`` so redirecting the extraction
    redirects the manifest with it. The only deletion on any path here is the
    module's own manifest temp file, on the failed-swap branch.
    """
    parser = argparse.ArgumentParser(
        description="Extract the bundled Skills/ zips into <out-root>/skills/<name>/ "
        f"packages and write <out-root>/{_MANIFEST_RELPATH} (audit-gated; a "
        "failed plan extracts nothing, a failed run never replaces the "
        "manifest, but a write-time failure MAY leave partial writes — it is "
        "never rolled back, and the git recovery command is printed instead)."
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
        default=None,
        help=f"Manifest path (default: <out-root>/{_MANIFEST_RELPATH}). It "
        "FOLLOWS --out-root: redirecting the extraction redirects the manifest "
        "with it, so a scratch run cannot write the plugin's own manifest.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the committed manifest against the on-disk tree; exit "
        "non-zero on any mismatch (writes nothing).",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Extract even when this run's write-set has uncommitted changes, "
        "or when git could not report whether it does. Writes are never rolled "
        "back, so your git undo will also discard whatever was already "
        "uncommitted there.",
    )
    args = parser.parse_args(argv)
    # --manifest is resolved against --out-root, NOT against the plugin root.
    # The two options used to be independent, so `--out-root <scratch>` alone
    # extracted into the scratch dir while still writing the PLUGIN's committed
    # manifest — a 1-package scratch run replacing the repo's 115-package
    # source-of-truth, with the dirty precondition evaluated against the
    # scratch root and the warning naming skills/, which was not where the
    # damage landed. Deriving the default is what makes one --out-root enough.
    if args.manifest is None:
        args.manifest = args.out_root / _MANIFEST_RELPATH

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

    # PRECONDITION, before a single byte: this run cannot undo itself, so it
    # only starts where the operator's undo is guaranteed clean — over
    # EVERYTHING it writes, the manifest included.
    pathspecs = _written_pathspecs(args.out_root, args.manifest)
    written_set = ", ".join(pathspecs)
    state, dirty = _dirty_subtree(args.out_root, pathspecs)
    under_git = state != _GIT_ABSENT
    if state == _GIT_ABSENT:
        _emit([
            f"warning: {args.out_root} is not a git worktree (or git is "
            "unavailable) —",
            f"no undo is available for {written_set}, and a write-time "
            "failure may leave them partially written.",
        ])
    elif state == _GIT_UNREADABLE and not args.allow_dirty:
        # NOT the warning above: git IS here and this IS a worktree, so
        # proceeding would skip the precondition over a subtree that may well
        # be dirty while claiming there was no VCS at all.
        _emit([
            f"refusing to extract: {args.out_root} is a git worktree, but git "
            "could not report",
            f"whether {written_set} is clean (a held index.lock, an "
            "interrupted rebase, permissions, or a timeout).",
            "this run is never rolled back, so it only starts where your undo "
            "is known to be clean.",
            "resolve the git state first, or pass --allow-dirty to extract "
            "anyway.",
            "nothing was written.",
        ])
        return 1
    elif state == _GIT_DIRTY and not args.allow_dirty:
        _emit([
            f"refusing to extract: this run writes {written_set}, and git "
            f"reports {len(dirty)} uncommitted change(s) there:",
            *(f"  {line}" for line in dirty[:_DIRTY_PREVIEW]),
            *([f"  … and {len(dirty) - _DIRTY_PREVIEW} more"]
              if len(dirty) > _DIRTY_PREVIEW else []),
            "this run is never rolled back, so it only starts where your undo "
            "is clean.",
            "commit or discard the entries above first, or pass --allow-dirty "
            "to extract anyway.",
            "nothing was written.",
        ])
        return 1

    plans, failures = plan_extractions(args.skills_root)
    # The plan-side counts stand in for the manifest on every path that fails
    # before one exists, so the audit still reconciles what WOULD have shipped.
    planned = {
        "skill_count": len(plans),
        "file_count": sum(len(plan["members"]) for plan in plans),
    }
    if failures:
        # A failed plan extracts NOTHING — this path never writes a byte.
        # (The WRITE path below is the one that may leave partial writes.)
        lines, _ok = audit(plans, planned, failures)
        for line in lines:
            sys.stdout.write(line + "\n")
        return 1

    try:
        written = extract(plans, args.out_root)
    except (OSError, ValueError) as exc:
        # Write-time failures no name predicate can foresee (an embedded NUL, a
        # segment past NAME_MAX, a read-only or full out_root). Recorded as an
        # audit failure with no manifest, never a traceback — but the members
        # already written STAY, so report the undo instead of performing one.
        lines, _ok = audit(
            plans, planned, [(args.out_root.as_posix(), f"extraction failed: {exc}")]
        )
        for line in lines:
            sys.stdout.write(line + "\n")
        _emit([
            f"extraction failed part-way; {_PACKAGE_ROOT}/ may hold partial "
            "writes and nothing was rolled back.",
            *_recovery_lines(args.out_root, pathspecs, under_git),
        ])
        return 1

    manifest = build_manifest(plans, args.out_root)
    schema_errors = validate_manifest(manifest)
    for err in schema_errors:
        sys.stderr.write(f"skillextract: manifest invalid: {err}\n")
    if schema_errors:
        return 1  # never write a manifest that violates the schema

    lines, ok = audit(plans, manifest, failures)
    for line in lines:
        sys.stdout.write(line + "\n")
    if not ok:
        return 1  # failed audit — never write a partial/failed manifest

    # The manifest write was the last failure that could still be a traceback,
    # and the only one that could DAMAGE a committed file: it ran outside every
    # try, after skills/ was fully written, and ``write_text`` opens 'w' —
    # which TRUNCATES the target before the first byte lands, so an ENOSPC left
    # the committed anchor empty or half-written and falsified the promise that
    # a failed run never leaves a bad manifest behind.
    #
    # Stage a sibling and swap. ``os.replace`` is atomic for a FILE, so a
    # reader sees either the whole previous manifest or the whole new one, and
    # a failure leaves the previous one byte-intact. NOTE THE DISTINCTION: the
    # stage-and-swap objection recorded in :func:`extract`'s docstring is about
    # non-empty DIRECTORIES, which ``os.replace`` refuses — it does not
    # transfer here. The temp file is a sibling so the swap stays within one
    # filesystem, where ``os.replace`` is atomic.
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_tmp = args.manifest.with_name(args.manifest.name + ".tmp")
    try:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest_tmp.write_text(payload, encoding="utf-8")
        os.replace(manifest_tmp, args.manifest)
    except OSError as exc:
        # The module's ONLY deletion, and squarely inside its rule: this is a
        # file THIS process created at a path it chose, not an unwind of a
        # directory it does not own. A cleanup must not itself traceback, so a
        # failure to remove the stage is swallowed rather than raised over the
        # error that actually matters.
        try:
            manifest_tmp.unlink(missing_ok=True)
        except OSError:
            pass
        sys.stderr.write(f"skillextract: cannot write manifest: {exc}\n")
        _emit([
            f"the manifest was NOT replaced (any previous one is intact), but "
            f"{_PACKAGE_ROOT}/ already holds this run's writes.",
            *_recovery_lines(args.out_root, pathspecs, under_git),
        ])
        return 1
    sys.stdout.write(
        f"skillextract: wrote {args.manifest} ({len(plans)} packages, {written} files)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
