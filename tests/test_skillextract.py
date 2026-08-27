"""Unit tests for scripts/skillextract.py (skill extractor + sha256 manifest).

Fixtures are synthetic zip trees built with tempfile + zipfile — the tests
never depend on the real Skills/ tree. The committed-data cases are the first
exception: TestCommittedNamePolicy calibrates both untrusted-name predicates on
references/skill-registry.json + references/skills-manifest.json, and
TestCommittedManifest re-hashes the extracted skills/ tree against that same
manifest — both zip-free, so they run anywhere the repo is checked out
(GitHub CI).

Scope is the second exception: one TestAudit case
(test_failures_is_the_last_parameter_in_both_siblings) also pins a signature
invariant on the sibling scripts/skillregistry.py, because the shared ``audit``
parameter-order contract spans the two modules and is only meaningful when
asserted against both from one place.

Real git is the third: the module's write-side precondition IS a git question,
so TestDirtyPrecondition builds throwaway repos with the real binary rather
than mocking subprocess (a mocked ``git status`` would only prove the mock).
Those cases skipUnless git is installed, the same convention
tests/test_difftool.py uses.
"""
import ast
import contextlib
import errno
import inspect
import io
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock

from scripts import skillextract, skillregistry, validate

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_HAS_GIT = shutil.which("git") is not None

_FRONTMATTER = """---
name: {name}
description: "{description}"
license: MIT
---

# Body
"""


def _skill_md(name="demo-skill", description="Does demo things."):
    return _FRONTMATTER.format(name=name, description=description)


def _make_zip(category_dir: pathlib.Path, filename: str, skill_md=None, extra=None):
    """Write a synthetic skill zip: SKILL.md (unless None) + extras."""
    category_dir.mkdir(parents=True, exist_ok=True)
    zip_path = category_dir / filename
    with zipfile.ZipFile(zip_path, "w") as archive:
        if skill_md is not None:
            archive.writestr("SKILL.md", skill_md)
        for member, content in (extra or {}).items():
            archive.writestr(member, content)
    return zip_path


def _plan(name, zip_path, entry_names, category="Alpha", sources=None):
    """Hand-build an extraction plan (members sorted by entry name)."""
    return {
        "name": name,
        "category": category,
        "dir": f"skills/{name}",
        "zip": zip_path,
        "members": sorted(entry_names),
        "sources": sources if sources is not None else [zip_path],
    }


def _extract_tree(tmp: pathlib.Path):
    """Plan + extract a synthetic Skills/ tree under tmp; return (plans, failures)."""
    plans, failures = skillextract.plan_extractions(tmp / "Skills")
    if not failures:
        skillextract.extract(plans, tmp)
    return plans, failures


def _mark_member_encrypted(zip_path: pathlib.Path):
    """Set the zip 'encrypted' general-purpose flag bit on a one-member archive.

    ``zipfile`` cannot WRITE an encrypted member, so the bit is patched into
    the bytes: offset +6 of the local file header and +8 of the central
    directory entry. Both offsets are read from the archive's own structures
    (``header_offset`` and the end-of-central-directory record) rather than
    scanned for, so no payload byte can be mistaken for a signature. Reading
    the member then raises RuntimeError, exactly as a real password-protected
    archive does.
    """
    data = bytearray(zip_path.read_bytes())
    with zipfile.ZipFile(zip_path) as archive:
        local = archive.infolist()[0].header_offset
    eocd = data.rindex(b"PK\x05\x06")
    central = int.from_bytes(data[eocd + 16:eocd + 20], "little")
    data[local + 6] |= 0x1
    data[central + 8] |= 0x1
    zip_path.write_bytes(bytes(data))


def _set_compression_method(zip_path: pathlib.Path, method: int):
    """Rewrite a one-member archive's compression method (same offsets as above).

    Method 9 is deflate64, which ``zipfile`` refuses with NotImplementedError —
    a RuntimeError SUBCLASS, and the second way a real archive escapes a
    BadZipFile-only guard.
    """
    data = bytearray(zip_path.read_bytes())
    with zipfile.ZipFile(zip_path) as archive:
        local = archive.infolist()[0].header_offset
    eocd = data.rindex(b"PK\x05\x06")
    central = int.from_bytes(data[eocd + 16:eocd + 20], "little")
    data[local + 8:local + 10] = method.to_bytes(2, "little")
    data[central + 10:central + 12] = method.to_bytes(2, "little")
    zip_path.write_bytes(bytes(data))


@contextlib.contextmanager
def _no_git_discovery(root: pathlib.Path):
    """Make ``root`` provably NOT a git worktree, wherever TMPDIR happens to be.

    ``git`` walks UP from its cwd looking for a repository, so a temp dir that
    happened to live inside somebody's checkout would be reported as a worktree
    and the non-git cases would pass or fail by accident.
    ``GIT_CEILING_DIRECTORIES`` stops that walk: git refuses to ascend INTO a
    listed directory, so the entry has to be ``root``'s PARENT for ``root``
    itself to still be examined and found repo-less. It is a real git feature
    applied from the TEST side only — the module under test carries no
    accommodation for being tested.
    """
    ceiling = str(root.resolve().parent)
    with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": ceiling}):
        yield


def _restore_bytes(path: pathlib.Path, data: bytes):
    """Put ``path`` back if something under test overwrote it (else a no-op)."""
    if path.read_bytes() != data:
        path.write_bytes(data)


def _git(root: pathlib.Path, *args):
    """Run one git command in ``root``; returns stdout, raises on non-zero."""
    return subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True
    ).stdout


def _git_repo(testcase, files):
    """Create a temp git repo with ``files`` committed as the baseline.

    Returns the root Path; cleanup is registered on ``testcase``. Same idiom as
    tests/test_difftool.py's ``_git_repo``, with signing forced off so a
    developer's global ``commit.gpgsign`` cannot break the fixture.
    """
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    root = pathlib.Path(tmp.name)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "commit.gpgsign", "false")
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline")
    return root


class TestPlanExtractions(unittest.TestCase):
    def test_happy_path_plan_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            zip_path = _make_zip(
                root / "Skills" / "Engineering",
                "demo.zip",
                _skill_md("demo"),
                extra={"scripts/run.sh": "#/bin/sh\n", "notes.md": "hi"},
            )
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(failures, [])
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertEqual(plan["name"], "demo")
        self.assertEqual(plan["category"], "Engineering")
        self.assertEqual(plan["dir"], "skills/demo")
        self.assertEqual(plan["zip"], zip_path)
        self.assertEqual(
            plan["members"],  # sorted entry names, one canonical archive
            ["SKILL.md", "notes.md", "scripts/run.sh"],
        )
        self.assertEqual(plan["sources"], [zip_path])

    def test_plans_sorted_by_category_then_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Zeta", "beta.zip", _skill_md("beta"))
            _make_zip(root / "Skills" / "Alpha", "omega.zip", _skill_md("omega"))
            _make_zip(root / "Skills" / "Alpha", "alpha.zip", _skill_md("alpha"))
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(failures, [])
        self.assertEqual(
            [(p["category"], p["name"]) for p in plans],
            [("Alpha", "alpha"), ("Alpha", "omega"), ("Zeta", "beta")],
        )

    def test_coalesce_identical_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            extra = {"payload.md": "same bytes"}
            _make_zip(root / "Skills" / "Alpha", "dup.zip", _skill_md("dup"), extra=extra)
            _make_zip(root / "Skills" / "Alpha", "dup (1).zip", _skill_md("dup"), extra=extra)
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(failures, [])
        self.assertEqual(len(plans), 1)  # two archives, ONE package
        self.assertEqual(len(plans[0]["sources"]), 2)
        self.assertEqual(plans[0]["dir"], "skills/dup")

    def test_same_name_different_bytes_is_failure(self):
        # The coalesce rule is byte-identity: a same-name group that differs is
        # an audit FAILURE, never a silent pick.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "dup.zip", _skill_md("dup"),
                      extra={"payload.md": "version one"})
            _make_zip(root / "Skills" / "Alpha", "dup (1).zip", _skill_md("dup"),
                      extra={"payload.md": "version two"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], "dup")
        self.assertIn("differ in bytes", failures[0][1])

    # ---- failure paths: unreadable archive / missing manifest / unsafe names ----
    def test_bad_zip_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Skills" / "Alpha").mkdir(parents=True)
            (root / "Skills" / "Alpha" / "broken.zip").write_text("nope", encoding="utf-8")
            _make_zip(root / "Skills" / "Alpha", "good.zip", _skill_md("good"))
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual([p["name"] for p in plans], ["good"])
        self.assertEqual(len(failures), 1)
        self.assertIn("broken.zip", failures[0][0])

    def test_encrypted_member_is_recorded_as_a_failure(self):
        # C4: an ENCRYPTED member makes zipfile raise RuntimeError, not
        # BadZipFile, so a BadZipFile-only guard let it escape as a traceback
        # with NO audit line at all — contradicting the contract that a bad
        # archive is a recorded FAILURE. The good archive beside it must still
        # plan, proving the failure is CONTAINED to the archive that caused it.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            locked = _make_zip(root / "Skills" / "Alpha", "locked.zip",
                               _skill_md("locked"))
            _mark_member_encrypted(locked)
            # The fixture really is what this case claims to be.
            with zipfile.ZipFile(locked) as archive:
                with self.assertRaises(RuntimeError):
                    archive.read("SKILL.md")
            _make_zip(root / "Skills" / "Alpha", "good.zip", _skill_md("good"))
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual([p["name"] for p in plans], ["good"])
        self.assertEqual(len(failures), 1)
        self.assertIn("locked.zip", failures[0][0])
        self.assertIn("unreadable zip archive", failures[0][1])
        self.assertIn("RuntimeError", failures[0][1])  # the CAUSE is recorded

    def test_unsupported_compression_member_is_recorded_as_a_failure(self):
        # The RuntimeError SUBCLASS route: deflate64 (method 9) raises
        # NotImplementedError, which a `except RuntimeError` catches and a
        # `except BadZipFile` does not.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            exotic = _make_zip(root / "Skills" / "Alpha", "d64.zip", _skill_md("d64"))
            _set_compression_method(exotic, 9)
            with zipfile.ZipFile(exotic) as archive:
                with self.assertRaises(NotImplementedError):
                    archive.read("SKILL.md")
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("unreadable zip archive", failures[0][1])
        self.assertIn("NotImplementedError", failures[0][1])
        self.assertTrue(issubclass(NotImplementedError, RuntimeError))  # why

    def test_unreadable_archive_file_is_recorded_as_a_failure(self):
        # The third hierarchy: the archive FILE itself unreadable (OSError).
        # Skipped for root, who can read a 0o000 file regardless.
        if os.geteuid() == 0:
            self.skipTest("root bypasses file permissions")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            locked = _make_zip(root / "Skills" / "Alpha", "noperm.zip",
                               _skill_md("noperm"))
            locked.chmod(0o000)
            try:
                plans, failures = skillextract.plan_extractions(root / "Skills")
            finally:
                locked.chmod(0o644)  # so the tmpdir cleanup can proceed
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("unreadable zip archive", failures[0][1])

    def test_recursion_error_is_not_laundered_into_an_archive_failure(self):
        # C7: the broad `except RuntimeError` is right for encrypted and
        # deflate64 members, but RecursionError IS a RuntimeError subclass, so
        # a genuine runaway-recursion defect was being reported as
        # "unreadable zip archive: RecursionError: ..." — blaming the
        # operator's file for a bug of ours. A defect must stay a traceback.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            zip_path = _make_zip(root / "Skills" / "Alpha", "demo.zip",
                                 _skill_md("demo"))
            self.assertTrue(issubclass(RecursionError, RuntimeError))  # why
            with mock.patch.object(
                zipfile.ZipFile, "read",
                side_effect=RecursionError("maximum recursion depth exceeded"),
            ):
                # It PROPAGATES: not converted to ValueError, so
                # plan_extractions cannot record it as an archive failure.
                with self.assertRaises(RecursionError):
                    skillextract._read_members(zip_path)
                with self.assertRaises(RecursionError):
                    skillextract.plan_extractions(root / "Skills")

    def test_missing_skill_md_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "empty.zip", skill_md=None)
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("SKILL.md", failures[0][1])

    def test_unsafe_entry_name_is_failure(self):
        # Preflight: a plan carrying an unsafe entry is rejected BEFORE anything
        # is extracted, so a hostile archive can never be half-extracted.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "evil.zip", _skill_md("evil"),
                      extra={"../evil.md": "escape"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("unsafe zip entry", failures[0][1])

    def test_backslash_entry_name_is_failure(self):
        # SEC-2: a ``..\evil.md`` member is one POSIX segment but a Windows
        # traversal — backslash is rejected outright, not parsed POSIX-only.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "evil.zip", _skill_md("evil"),
                      extra={"..\\evil.md": "escape"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("unsafe zip entry", failures[0][1])

    def test_dot_entry_name_is_failure(self):
        # A ``.`` member addresses the package DIR, not a file inside it: the
        # write sink would land on the dir itself, so it must be rejected at
        # plan time (keyed on the skill name) with nothing extracted — never an
        # unhandled IsADirectoryError/FileExistsError mid-extract.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "dot.zip", _skill_md("demo"),
                      extra={".": "dot member"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
            extracted = (root / "skills").exists()
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], "demo")  # keyed on the skill name
        self.assertIn("unsafe zip entry", failures[0][1])
        self.assertIn("'.'", failures[0][1])
        self.assertFalse(extracted)

    def test_aliasing_entry_name_is_failure_not_a_silent_overwrite(self):
        # An archive carrying BOTH ``SKILL.md`` and ``SKILL.md/.`` maps two
        # members onto ONE target: sorted order writes the audited member first
        # and the alias overwrites it, while the frontmatter classification read
        # members['SKILL.md'] — the shipped file would hold different bytes than
        # the audited one, and --verify re-normalizes onto that same path and
        # still passes. Silent content substitution, so it must be a RECORDED
        # PLAN FAILURE with nothing extracted.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "alias.zip", _skill_md("demo"),
                      extra={"SKILL.md/.": "substituted body"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
            extracted = (root / "skills").exists()
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], "demo")  # keyed on the skill name
        self.assertIn("unsafe zip entry", failures[0][1])
        self.assertIn("'SKILL.md/.'", failures[0][1])
        self.assertFalse(extracted)  # nothing on disk to substitute

    def test_nested_dot_entry_name_is_failure(self):
        # The crash shape: ``'sub/.'`` normalizes to ``sub`` and would be
        # written as a REGULAR FILE, then ``'sub/x.md'`` (sorts after — '.' is
        # 0x2E, below 'x') dies in target.parent.mkdir with an unhandled
        # FileExistsError, leaving the half-extracted package this module
        # promises is impossible.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "nested.zip", _skill_md("demo"),
                      extra={"sub/.": "dir-as-file", "sub/x.md": "real member"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
            extracted = (root / "skills").exists()
        self.assertEqual(plans, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("'sub/.'", failures[0][1])
        self.assertFalse(extracted)

    def test_is_safe_entry_backslash_rejected(self):
        self.assertFalse(skillextract._is_safe_entry("..\\evil.md"))
        self.assertFalse(skillextract._is_safe_entry("a\\b.md"))
        self.assertTrue(skillextract._is_safe_entry("a/b.md"))

    def test_is_safe_entry_segmentless_dot_rejected(self):
        # ``PurePosixPath('.')`` drops the dot, leaving NO segment — it cleared
        # both the absolute and the ``..`` guard until the raw-segment check.
        self.assertFalse(skillextract._is_safe_entry("."))
        # The neighbours are unchanged: already-rejected names stay rejected …
        for unsafe in ("./", "..", "", "x/../y"):
            with self.subTest(entry=unsafe):
                self.assertFalse(skillextract._is_safe_entry(unsafe))
        # … and a real nested member stays accepted.
        self.assertTrue(skillextract._is_safe_entry("a/b"))

    def test_is_safe_entry_rejects_segments_normalization_would_hide(self):
        # The guard must read the RAW segments: ``PurePosixPath`` drops EVERY
        # ``.`` and collapses ``//``, not just a leading one, so each name below
        # reaches a normalized-only guard already laundered into a name that
        # looks safe. ``'SKILL.md/.'`` is the dangerous one — it normalizes onto
        # the SAME target as a real ``SKILL.md`` member (see the plan-level
        # aliasing case) — and ``'sub/.'`` writes a REGULAR FILE where a
        # sibling ``'sub/x.md'`` then needs a directory.
        for unsafe in ("sub/.", "SKILL.md/.", "x/.", "a//b", "./a.md", "a/./b.md"):
            with self.subTest(entry=unsafe):
                laundered = pathlib.PurePosixPath(unsafe)
                self.assertNotIn(".", laundered.parts)  # normalization hid it
                self.assertFalse(skillextract._is_safe_entry(unsafe))
        # A leading-dot FILE name is a real, shipped member and stays accepted:
        # only a BARE ``.`` segment is unsafe.
        self.assertTrue(skillextract._is_safe_entry(".security-scan-passed"))
        self.assertTrue(skillextract._is_safe_entry("sub/.security-scan-passed"))

    def test_confined_target_rejects_segmentless_dot(self):
        # The enforcement twin refuses it too, so the write sink can never
        # resolve a member onto the package dir itself.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                skillextract._confined_target(pathlib.Path(tmp), "skills/demo", ".")

    def test_confined_target_rejects_the_aliasing_entry(self):
        # Without the raw-segment guard ``'SKILL.md/.'`` resolved to the very
        # same path as ``'SKILL.md'``; the sink must refuse it outright rather
        # than hand back a target that already belongs to another member.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            real = skillextract._confined_target(root, "skills/demo", "SKILL.md")
            with self.assertRaises(ValueError):
                skillextract._confined_target(root, "skills/demo", "SKILL.md/.")
            # Pin WHY it must be refused: pathlib alone cannot tell them apart.
            self.assertEqual(real, root.resolve() / "skills/demo" / "SKILL.md/.")


class TestTargetInjectivity(unittest.TestCase):
    """SEC-1/COR-1: name-safe members must still claim DISTINCT targets.

    The invariant that replaces shape enumeration. Every case below carries a
    member set every name predicate accepts — none of them contains a ``.``,
    ``..``, empty segment or backslash — yet the members do not map one-to-one
    onto the filesystem, which is the property that actually matters.
    """

    def _failures_for(self, extra):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"),
                      extra=extra)
            plans, failures = skillextract.plan_extractions(root / "Skills")
            extracted = (root / "skills").exists()
        self.assertEqual(plans, [])
        self.assertFalse(extracted)  # a conflicting group extracts NOTHING
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], "demo")  # keyed on the skill name
        self.assertIn("colliding zip entry target(s)", failures[0][1])
        return failures[0][1]

    def test_parent_path_member_is_a_plan_failure(self):
        # The crash route with no ``.`` anywhere: sorted order writes ``sub`` as
        # a regular FILE, then ``sub/x.md`` dies in mkdir(parents=True) with an
        # unhandled FileExistsError over a half-written package.
        for member_names in ("sub", "sub/x.md"), ("a/b", "a/b/c/d.md"):
            with self.subTest(members=member_names):
                for name in member_names:
                    self.assertTrue(skillextract._is_safe_entry(name))  # name-legal
                reason = self._failures_for({name: b"x" for name in member_names})
                self.assertIn("is a parent path of", reason)
                self.assertIn(repr(member_names[0]), reason)

    def test_case_colliding_members_are_a_plan_failure(self):
        # On a case-insensitive filesystem (APFS by default, Windows) both
        # members resolve to ONE file: build_manifest would then re-read that
        # single file for BOTH recorded paths, so --verify reports the tree
        # intact while the shipped SKILL.md holds bytes the frontmatter
        # classifier never saw. Silent content substitution.
        reason = self._failures_for({"skill.md": b"substituted body"})
        # The message says MAY, and names why: on ext4 these really are two
        # files, so a line claiming they DO collide would be false on the
        # very machine printing it.
        self.assertIn(
            "may resolve to one target on a case-insensitive or "
            "name-normalizing filesystem", reason,
        )
        self.assertIn("'skill.md'", reason)
        self.assertIn("'SKILL.md'", reason)

    def test_win32_stripped_members_collide_with_their_plain_twin(self):
        # The Win32 path layer drops trailing dots and spaces, so each of these
        # lands on the plain SKILL.md the manifest audited.
        for alias in ("SKILL.md.", "SKILL.md ", "SKILL.MD..  "):
            with self.subTest(alias=alias):
                self.assertTrue(skillextract._is_safe_entry(alias))  # name-legal
                reason = self._failures_for({alias: b"substituted body"})
                self.assertIn("may resolve to one target", reason)
                self.assertIn(repr(alias), reason)

    def test_unicode_equivalent_members_collide(self):
        # Apple filesystems treat the composed and decomposed spellings of the
        # same character as ONE name, so these two byte-different members are
        # one file there — the same substitution as the case twin.
        composed = "caf\N{LATIN SMALL LETTER E WITH ACUTE}.md"
        decomposed = "cafe\N{COMBINING ACUTE ACCENT}.md"
        self.assertNotEqual(composed, decomposed)  # different bytes …
        self.assertEqual(  # … one target
            skillextract._target_key(composed), skillextract._target_key(decomposed)
        )
        reason = self._failures_for({composed: b"one", decomposed: b"two"})
        self.assertIn("may resolve to one target", reason)

    def test_full_case_folding_would_falsely_reject_distinct_members(self):
        # C7: the key must NOT use full folding. casefold() is FULL Unicode
        # case folding for caseless STRING matching — it is length-changing and
        # maps 'ß' to 'ss'. No filesystem does that: NTFS ($UpCase) and the
        # case-insensitive Apple filesystems both use per-codepoint SIMPLE
        # mappings that leave 'ß' one character, so these two members are two
        # distinct files EVERYWHERE.
        sharp, doubled = "stra\N{LATIN SMALL LETTER SHARP S}e.md", "strasse.md"
        self.assertEqual(sharp.casefold(), doubled.casefold())  # casefold conflates
        # And the trap on the OTHER side: Python's str.upper() is full
        # uppercase too ('ß' -> 'SS'), so folding through a whole-string
        # .upper() would reintroduce this very false reject. The fold takes a
        # mapping only when it stays ONE codepoint, which is what makes it the
        # simple map the filesystems actually apply.
        self.assertEqual(sharp.upper(), doubled.upper())
        self.assertNotEqual(
            skillextract._simple_fold(sharp), skillextract._simple_fold(doubled)
        )
        self.assertNotEqual(
            skillextract._target_key(sharp), skillextract._target_key(doubled)
        )
        # So the archive is ACCEPTED. Under casefold it was refused with a
        # message that was untrue on the machine printing it — and a false
        # reject is worse here than the aliasing the invariant prevents.
        self.assertEqual(skillextract._target_conflicts([sharp, doubled]), [])
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "sharp.zip", _skill_md("demo"),
                      extra={sharp: b"one", doubled: b"two"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
            skillextract.extract(plans, root)
            both = sorted(p.name for p in (root / "skills" / "demo").iterdir())
        self.assertEqual(failures, [])
        self.assertEqual(both, ["SKILL.md", doubled, sharp])

    def test_simple_case_folding_still_catches_every_real_alias(self):
        # The other side of that trade: dropping full casefold() must not
        # loosen the invariant on any alias a real filesystem actually
        # produces. The NON-ASCII rows are the load-bearing ones — an
        # ASCII-only version of this case cannot falsify a claim about Unicode
        # folding, which is exactly how the final-sigma hole below survived.
        for a, b in (("SKILL.md", "skill.md"),          # ASCII case (APFS, NTFS)
                     ("README.MD", "readme.md"),
                     ("Notes.md", "notes.md."),         # case + Win32 strip
                     ("a\N{GREEK SMALL LETTER SIGMA}.md",
                      "a\N{GREEK SMALL LETTER FINAL SIGMA}.md"),
                     ("\N{LATIN SMALL LETTER DOTLESS I}.md", "i.md"),
                     ("\N{MICRO SIGN}.md", "\N{GREEK SMALL LETTER MU}.md"),
                     ("\N{LATIN SMALL LETTER LONG S}.md", "s.md"),
                     ("\N{LATIN SMALL LETTER SHARP S}.md",
                      "\N{LATIN CAPITAL LETTER SHARP S}.md")):
            with self.subTest(pair=(a, b)):
                self.assertNotEqual(a, b)  # genuinely different bytes …
                self.assertEqual(  # … one target
                    skillextract._target_key(a), skillextract._target_key(b)
                )
                self.assertNotEqual(skillextract._target_conflicts([a, b]), [])

    def test_final_sigma_aliases_its_plain_twin_on_ntfs(self):
        # C1, the hole a plain str.lower() opened while closing the ß one.
        # MEASURED: casefold() merged these, lower() does NOT — and NTFS
        # compares through $UpCase, a simple UPPERCASE table, under which both
        # become 'AΣ.MD' and are ONE file. Simple-lower is not the inverse of
        # simple-upper, so reasoning from lowercase alone got the destination
        # wrong. Accepting the group means sorted extraction overwrites the
        # audited member, build_manifest re-reads that one file for BOTH
        # recorded paths, and --verify calls the tree intact: the exact silent
        # content substitution this invariant exists to stop.
        sigma = "a\N{GREEK SMALL LETTER SIGMA}.md"
        final = "a\N{GREEK SMALL LETTER FINAL SIGMA}.md"
        self.assertNotEqual(sigma.lower(), final.lower())   # lower() splits …
        self.assertEqual(sigma.upper(), final.upper())      # … $UpCase merges
        reason = self._failures_for({sigma: b"one", final: b"two"})
        self.assertIn("may resolve to one target", reason)

    def test_turkish_dotless_i_aliases_ascii_i_on_ntfs(self):
        # The residual the review expected to remain open, MEASURED as closed:
        # 'ı'.upper() is 'I', so $UpCase hands 'ı.md' and 'i.md' one file —
        # a class casefold() never merged either. The fold catches it because
        # it models the uppercase table rather than reasoning from lowercase.
        dotless = "\N{LATIN SMALL LETTER DOTLESS I}.md"
        self.assertNotEqual(dotless.casefold(), "i.md")  # full folding misses it
        self.assertEqual(dotless.upper(), "I.MD")        # the table does not
        reason = self._failures_for({dotless: b"one", "i.md": b"two"})
        self.assertIn("may resolve to one target", reason)

    def test_the_fold_is_an_idempotent_canonical_form(self):
        # A key is only a canonical form if folding twice changes nothing —
        # otherwise two members could key apart purely by how often the fold
        # ran. Checked across the whole BMP plus the pinned cases above.
        for cp in range(0x10000):
            char = chr(cp)
            once = skillextract._simple_fold(char)
            self.assertEqual(skillextract._simple_fold(once), once, hex(cp))

    def test_member_that_names_no_file_is_a_plan_failure(self):
        # ``...`` and ``"   "`` are empty once Win32 strips them: they address
        # no file at all, so they can only alias or fail at write time.
        for empty in ("...", "   ", "sub/.../x.md"):
            with self.subTest(entry=empty):
                reason = self._failures_for({empty: b"x"})
                self.assertIn("names no file on disk", reason)

    def test_distinct_members_are_accepted(self):
        # Boundary: the invariant must not reject real member shapes — nested
        # dirs, a leading-dot FILE, and case-differing names in DIFFERENT dirs
        # (those are distinct targets everywhere).
        self.assertEqual(
            skillextract._target_conflicts([
                "SKILL.md", "scripts/run.sh", "scripts/lib/util.py",
                "sub/x.md", ".security-scan-passed", "a/README.md", "b/readme.md",
            ]),
            [],
        )
        self.assertEqual(skillextract._target_conflicts([]), [])
        self.assertEqual(skillextract._target_conflicts(["SKILL.md"]), [])

    def test_conflicts_are_reported_deterministically(self):
        # Plan failures are audit lines: the same member set must always
        # produce the same reason string, whatever order it arrives in.
        members = ["sub/x.md", "SKILL.md", "sub", "skill.md"]
        self.assertEqual(
            skillextract._target_conflicts(members),
            skillextract._target_conflicts(list(reversed(members))),
        )
        self.assertEqual(len(skillextract._target_conflicts(members)), 2)


class TestUnsafePackageName(unittest.TestCase):
    """SEC-1/COR-1: the frontmatter ``name`` builds the package dir.

    A hostile name is a plan FAILURE (recorded against the zip path, never
    the hostile name), never a sanitized rewrite — and nothing is extracted.
    """

    def test_hostile_names_are_plan_failures(self):
        hostiles = (
            "..", "../x", "a/b", "..\\x", ".", "", "UPPER", "has space",
            "atlas", "atlas-weave", "atlas-resume",  # first-party collisions
        )
        for hostile in hostiles:
            with self.subTest(name=hostile):
                with tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    zip_path = _make_zip(
                        root / "Skills" / "Alpha", "evil.zip", _skill_md(hostile),
                        extra={"scripts/quality.py": "# payload\n"},
                    )
                    plans, failures = skillextract.plan_extractions(root / "Skills")
                self.assertEqual(plans, [])
                self.assertEqual(len(failures), 1)
                self.assertEqual(failures[0][0], zip_path.as_posix())
                self.assertIn("unsafe skill name", failures[0][1])

    def test_safe_names_are_accepted(self):
        # Boundary: the allow-pattern admits the shipped-name shapes.
        for safe in ("a", "0x", "demo-skill", "a1-b2"):
            with self.subTest(name=safe):
                with tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    _make_zip(root / "Skills" / "Alpha", "ok.zip", _skill_md(safe))
                    plans, failures = skillextract.plan_extractions(root / "Skills")
                self.assertEqual(failures, [])
                self.assertEqual([p["name"] for p in plans], [safe])


class TestExtract(unittest.TestCase):
    def test_byte_identical_and_deterministic_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            payload = bytes(range(256))  # binary, never decoded
            _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"),
                      extra={"scripts/run.sh": "#/bin/sh\necho hi\n"})
            zip_path = root / "Skills" / "Alpha" / "demo.zip"
            with zipfile.ZipFile(zip_path, "a") as archive:
                archive.writestr("data.bin", payload)
            plans, failures = skillextract.plan_extractions(root / "Skills")
            self.assertEqual(failures, [])
            written = skillextract.extract(plans, root)
            skill_dir = root / "skills" / "demo"
            data = (skill_dir / "data.bin").read_bytes()
            sh_mode = stat.S_IMODE((skill_dir / "scripts" / "run.sh").stat().st_mode)
            md_mode = stat.S_IMODE((skill_dir / "SKILL.md").stat().st_mode)
            bin_mode = stat.S_IMODE((skill_dir / "data.bin").stat().st_mode)
        self.assertEqual(written, 3)
        self.assertEqual(data, payload)  # byte-identical, payload included
        self.assertEqual(sh_mode, 0o755)  # *.sh is executable
        self.assertEqual(md_mode, 0o644)
        self.assertEqual(bin_mode, 0o644)

    def test_path_confinement_dotdot_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            zip_path = _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"))
            plans = [_plan("demo", zip_path, ["../evil.md"])]
            with self.assertRaises(ValueError):
                skillextract.extract(plans, root)
            escaped = (root / "skills" / "evil.md").exists() or (root / "evil.md").exists()
        self.assertFalse(escaped)  # nothing written outside the package dir

    def test_path_confinement_absolute_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            zip_path = _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"))
            plans = [_plan("demo", zip_path, ["/abs/evil.md"])]
            with self.assertRaises(ValueError):
                skillextract.extract(plans, root)
        self.assertFalse((root / "abs" / "evil.md").exists())

    def test_hostile_plan_dir_rejected_at_the_sink(self):
        # Defense in depth: even with a hostile plan dir forced PAST
        # plan_extractions, the write sink refuses it before any byte lands.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            zip_path = _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"))
            for hostile_dir in ("../escape", "skills/../../escape", "/abs/escape"):
                with self.subTest(dir=hostile_dir):
                    plan = _plan("demo", zip_path, ["SKILL.md"])
                    plan["dir"] = hostile_dir
                    with self.assertRaises(ValueError):
                        skillextract.extract([plan], root)
            escaped = (root / "escape").exists() or (root.parent / "escape").exists()
        self.assertFalse(escaped)

    def test_symlinked_package_dir_escape_rejected(self):
        # The joined-path guard: every segment is lexically safe, but the
        # package dir is a symlink pointing OUTSIDE out_root — the resolved
        # target escapes and the write is refused.
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as elsewhere:
            root = pathlib.Path(tmp)
            outside = pathlib.Path(elsewhere)
            zip_path = _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"))
            (root / "skills").mkdir()
            (root / "skills" / "demo").symlink_to(outside)
            with self.assertRaises(ValueError):
                skillextract.extract([_plan("demo", zip_path, ["SKILL.md"])], root)
            remaining = list(outside.iterdir())
        self.assertEqual(remaining, [])  # nothing written through the symlink

    def test_write_failure_deletes_nothing_it_did_not_create(self):
        # The MEASURED harm of the removed rmtree unwind, pinned as a
        # regression. An in-flight package dir is not this run's property: it
        # can already hold a committed file and an untracked stray, and the
        # unwind deleted both although the failure never touched either. On a
        # tracked tree the stray was unrecoverable, and ignore_errors=True made
        # a FAILED unwind look identical to a clean one.
        real_write_bytes = pathlib.Path.write_bytes
        written_names: list[str] = []

        def _fail_on_the_second_write(self, data):
            written_names.append(self.name)
            if len(written_names) == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_write_bytes(self, data)

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"),
                      extra={"scripts/run.sh": "#/bin/sh\n"})
            package = root / "skills" / "demo"
            package.mkdir(parents=True)
            (package / "PRE_EXISTING.md").write_text("committed", encoding="utf-8")
            (package / "stray.txt").write_text("untracked", encoding="utf-8")
            plans, failures = skillextract.plan_extractions(root / "Skills")
            self.assertEqual(failures, [])
            with mock.patch.object(
                pathlib.Path, "write_bytes", _fail_on_the_second_write
            ):
                with self.assertRaises(OSError):  # the real failure propagates
                    skillextract.extract(plans, root)
            survivors = sorted(p.name for p in package.iterdir())
            pre_existing = (package / "PRE_EXISTING.md").read_text(encoding="utf-8")
        self.assertEqual(written_names, ["SKILL.md", "run.sh"])  # SKILL.md landed
        # Both bystanders survive, byte-intact — and so does the one member the
        # run did write. extract() removes nothing at all.
        self.assertEqual(
            survivors, ["PRE_EXISTING.md", "SKILL.md", "scripts", "stray.txt"]
        )
        self.assertEqual(pre_existing, "committed")

    def _source_ast(self):
        return ast.parse(
            (_REPO_ROOT / "scripts" / "skillextract.py").read_text(encoding="utf-8")
        )

    def _called_names(self, tree):
        """Every callee spelling in the module: ``x.attr(...)`` and ``name(...)``."""
        called: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                called.add(node.func.id)
        return called

    def test_module_owns_no_deletion_primitive(self):
        # The structural pin behind that promise, asserted on the SOURCE so a
        # future "small" rollback cannot creep back in silently. Both call
        # spellings are collected — ``shutil.rmtree(x)`` (an Attribute, through
        # ANY receiver, so ``os.rmdir`` and ``Path.rmdir`` come with it) and a
        # bare ``rmtree(x)`` after a from-import (a Name).
        called = self._called_names(self._source_ast())
        self.assertEqual(
            called & {
                "rmtree", "rmdir", "remove", "removedirs", "move", "copytree",
                "rename",   # Path.rename/os.rename would relocate a tree too
                "getattr",  # getattr(mod, "rmtree")(p) evades every name ban
            },
            set(),
        )
        # Guard the guard: the walk really does see the calls it must judge, so
        # a broken collector cannot pass this vacuously.
        self.assertIn("write_bytes", called)
        self.assertIn("mkdir", called)

    def test_module_imports_no_deletion_capability(self):
        # C6: a name ban over CALLS is not enough — ``from shutil import rmtree
        # as _rm`` renames the callee, and the previous guard never asserted
        # that ``shutil`` was gone at all. Judge the IMPORTS too, so the module
        # cannot even reach a tree-deleting primitive.
        tree = self._source_ast()
        imported: set[str] = set()
        from_imported: set[tuple[str, str]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    from_imported.add((node.module or "", alias.name))
        self.assertNotIn("shutil", imported)
        self.assertNotIn("importlib", imported)  # no dynamic re-entry either
        self.assertEqual({module for module, _ in from_imported} & {
            "shutil", "importlib", "subprocess",
        }, set())
        # No deletion symbol is from-imported under ANY local alias.
        self.assertEqual({name for _, name in from_imported} & {
            "rmtree", "unlink", "rmdir", "remove", "removedirs", "move",
        }, set())
        # Guard the guard: the collectors really do see this module's imports.
        self.assertIn("subprocess", imported)
        self.assertIn("os", imported)
        self.assertIn(("scripts", "skillregistry"), from_imported)

    def test_the_only_deletion_is_the_modules_own_manifest_stage(self):
        # ``unlink`` is NOT in the banned set above, because the atomic manifest
        # write legitimately removes a file THIS process just created at a path
        # it chose — which is inside the module's rule, not an exception to it.
        # So it is pinned exactly rather than waved through: ONE call, on the
        # temp-file variable, with missing_ok. Any other unlink fails this.
        unlinks = [
            node for node in ast.walk(self._source_ast())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "unlink"
        ]
        self.assertEqual(len(unlinks), 1)
        (only,) = unlinks
        self.assertIsInstance(only.func.value, ast.Name)
        self.assertEqual(only.func.value.id, "manifest_tmp")
        self.assertEqual([kw.arg for kw in only.keywords], ["missing_ok"])

    def test_the_only_replace_is_the_atomic_manifest_swap(self):
        # C5 adds ``os.replace``, which relocates a path and therefore has to be
        # allowed DELIBERATELY and by assertion rather than by omission from a
        # ban list. Exactly one, and it must be os.replace — a str.replace()
        # would key here too, so the receiver is pinned.
        replaces = [
            node for node in ast.walk(self._source_ast())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "replace"
        ]
        self.assertEqual(len(replaces), 1)
        (only,) = replaces
        self.assertIsInstance(only.func.value, ast.Name)
        self.assertEqual(only.func.value.id, "os")

    def test_every_subprocess_call_is_a_literal_read_only_git_query(self):
        # C6: banning five deletion NAMES is weak while ``import subprocess`` is
        # real — ``subprocess.run(["rm", "-rf", str(pkg)])`` reintroduces the
        # rollback with every name-based guard still green. So judge the
        # process-spawning calls themselves: each must be subprocess.<runner>
        # with a LITERAL argv, and the whole set must be exactly the two
        # read-only git probes this module documents.
        runners = [
            node for node in ast.walk(self._source_ast())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {
                "run", "call", "check_call", "check_output", "Popen",
            }
        ]
        verbs = []
        for node in runners:
            self.assertIsInstance(node.func.value, ast.Name)
            self.assertEqual(node.func.value.id, "subprocess")
            argv = node.args[0]
            self.assertIsInstance(argv, ast.List)  # never a variable or f-string
            head = argv.elts[:2]
            self.assertTrue(all(isinstance(el, ast.Constant) for el in head))
            self.assertEqual(head[0].value, "git")
            verbs.append(head[1].value)
            # No shell, ever: shell=True would make argv a command string.
            self.assertNotIn("shell", [kw.arg for kw in node.keywords])
        self.assertEqual(sorted(verbs), ["rev-parse", "status"])


class TestManifest(unittest.TestCase):
    def _build(self, tmp: pathlib.Path):
        _make_zip(tmp / "Skills" / "Alpha", "one.zip", _skill_md("one"),
                  extra={"scripts/run.sh": "#/bin/sh\n"})
        _make_zip(tmp / "Skills" / "Beta", "two.zip", _skill_md("two"),
                  extra={"notes.md": "hello"})
        plans, failures = _extract_tree(tmp)
        self.assertEqual(failures, [])
        return skillextract.build_manifest(plans, tmp)

    def test_round_trip_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._build(pathlib.Path(tmp))
            errors = skillextract.validate_manifest(manifest)
            mismatches = skillextract.verify_manifest(manifest, tmp)
        self.assertEqual(errors, [])
        self.assertEqual(mismatches, [])
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["skill_count"], 2)
        self.assertEqual(manifest["file_count"], 4)
        self.assertEqual([s["name"] for s in manifest["skills"]], ["one", "two"])
        files = manifest["skills"][0]["files"]
        self.assertEqual([f["path"] for f in files],
                         ["skills/one/SKILL.md", "skills/one/scripts/run.sh"])
        self.assertTrue(all(len(f["sha256"]) == 64 for f in files))
        self.assertTrue(all(f["bytes"] > 0 for f in files))

    # ---- failure paths: tamper / extra / missing are all detected ----
    def test_verify_detects_tampered_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manifest = self._build(root)
            target = root / "skills" / "two" / "notes.md"
            target.write_bytes(b"tampered bytes")
            mismatches = skillextract.verify_manifest(manifest, root)
        self.assertTrue(any("skills/two/notes.md" in m for m in mismatches))
        self.assertTrue(any("drift" in m for m in mismatches))

    def test_verify_detects_extra_file(self):
        # Per-dir completeness: a file the manifest does not record is drift.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manifest = self._build(root)
            (root / "skills" / "one" / "stray.md").write_text("x", encoding="utf-8")
            mismatches = skillextract.verify_manifest(manifest, root)
        self.assertEqual(mismatches, ["extra file: skills/one/stray.md"])

    def test_verify_detects_stowaway_package_dir(self):
        # COR-2: a package dir the manifest does not record is drift even when
        # every manifest dir is intact — verify must enumerate skills/ itself.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manifest = self._build(root)
            stowaway = root / "skills" / "zzz-stowaway"
            stowaway.mkdir()
            (stowaway / "SKILL.md").write_text(
                "---\nname: zzz-stowaway\n---\n", encoding="utf-8"
            )
            mismatches = skillextract.verify_manifest(manifest, root)
        self.assertIn("extra package dir: skills/zzz-stowaway", mismatches)

    def test_verify_ignores_first_party_dirs(self):
        # atlas / atlas-weave / atlas-resume are plugin machinery, absent from
        # the manifest by design — never flagged as stowaways.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manifest = self._build(root)
            for name in ("atlas", "atlas-weave", "atlas-resume"):
                first_party = root / "skills" / name
                first_party.mkdir()
                (first_party / "SKILL.md").write_text("x\n", encoding="utf-8")
            mismatches = skillextract.verify_manifest(manifest, root)
        self.assertEqual(mismatches, [])

    def test_verify_detects_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manifest = self._build(root)
            (root / "skills" / "two" / "notes.md").unlink()
            mismatches = skillextract.verify_manifest(manifest, root)
        self.assertIn("missing file: skills/two/notes.md", mismatches)

    def test_validate_manifest_count_drift_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._build(pathlib.Path(tmp))
        manifest["skill_count"] = 99
        self.assertTrue(skillextract.validate_manifest(manifest))
        manifest2 = {"version": 2, "skill_count": 0, "file_count": 0}  # no "skills"
        self.assertTrue(skillextract.validate_manifest(manifest2))


class TestAudit(unittest.TestCase):
    def test_counts_coalesce_and_ok_line(self):
        plans = [
            _plan("a", pathlib.Path("a.zip"), ["SKILL.md"], category="Alpha"),
            _plan("b", pathlib.Path("b.zip"), ["SKILL.md"], category="Alpha"),
            _plan("c", pathlib.Path("c.zip"), ["SKILL.md"], category="Beta",
                  sources=[pathlib.Path("c.zip"), pathlib.Path("c (1).zip")]),
        ]
        manifest = {"skill_count": 3, "file_count": 3}
        lines, ok = skillextract.audit(plans, manifest, [])
        self.assertIn("AUDIT category=Alpha packages=2", lines)
        self.assertIn("AUDIT category=Beta packages=1", lines)
        self.assertIn("AUDIT coalesced name=c archives=2 dir=skills/c", lines)
        self.assertEqual(lines[-2], "AUDIT zips=4 packages=3 coalesced=1 files=3")
        self.assertEqual(lines[-1], "AUDIT ok")
        self.assertTrue(ok)

    # ---- E4 failure paths: plan failures and manifest drift ----
    def test_failures_flag_mismatch(self):
        plans = [_plan("a", pathlib.Path("a.zip"), ["SKILL.md"])]
        manifest = {"skill_count": 1, "file_count": 1}
        lines, ok = skillextract.audit(plans, manifest, [("bad.zip", "not a readable zip")])
        self.assertIn("AUDIT failure target=bad.zip reason=not a readable zip", lines)
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)

    def test_manifest_count_drift_flagged(self):
        plans = [_plan("a", pathlib.Path("a.zip"), ["SKILL.md"])]
        lines, ok = skillextract.audit(plans, {"skill_count": 2, "file_count": 1}, [])
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)

    def test_failures_is_the_last_parameter_in_both_siblings(self):
        # The two modules share ONE audit-line contract; ``failures`` sits in
        # the same (last) slot in both, so a cross-module copy-paste cannot
        # slot the failure list into the wrong position and still compile.
        for module in (skillextract, skillregistry):
            with self.subTest(module=module.__name__):
                params = list(inspect.signature(module.audit).parameters)
                self.assertEqual(params[-1], "failures")


class TestMain(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = skillextract.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def _args(self, root: pathlib.Path):
        return [
            "--skills-root", str(root / "Skills"),
            "--out-root", str(root),
            "--manifest", str(root / "refs" / "skills-manifest.json"),
        ]

    def _plugin_manifest_bytes(self):
        """Snapshot the committed manifest and put it back if a case writes it.

        Every case that runs the CLI WITHOUT ``--manifest`` needs this. Those
        are the cases that prove the manifest follows ``--out-root``, so if the
        derivation ever regresses they detect it by letting the damage happen —
        and the committed 115-package anchor is exactly what gets damaged. The
        assertions are what fail; this only stops the failure from taking the
        repository's source-of-truth with it.
        """
        plugin_manifest = _REPO_ROOT / "references" / "skills-manifest.json"
        data = plugin_manifest.read_bytes()
        self.addCleanup(_restore_bytes, plugin_manifest, data)
        return plugin_manifest, data

    def test_cli_happy_path_then_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"),
                      extra={"scripts/run.sh": "#/bin/sh\n"})
            _make_zip(root / "Skills" / "Alpha", "one (1).zip", _skill_md("one"),
                      extra={"scripts/run.sh": "#/bin/sh\n"})
            rc, stdout, _ = self._run(self._args(root))
            manifest_path = root / "refs" / "skills-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            verify_rc, verify_out, _ = self._run(["--out-root", str(root),
                                                  "--manifest", str(manifest_path),
                                                  "--verify"])
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT coalesced name=one archives=2 dir=skills/one", stdout)
        self.assertIn("AUDIT zips=2 packages=1 coalesced=1 files=2", stdout)
        self.assertIn("AUDIT ok", stdout)
        self.assertEqual(manifest["skill_count"], 1)
        self.assertEqual(manifest["file_count"], 2)
        self.assertEqual(skillextract.validate_manifest(manifest), [])
        self.assertEqual(validate.validate(manifest, "skills-manifest"), [])
        self.assertEqual(verify_rc, 0)
        self.assertIn("VERIFY ok skills=1 files=2", verify_out)

    # ---- C2: --manifest FOLLOWS --out-root, so a scratch run cannot aim home --
    def test_out_root_without_manifest_never_writes_the_plugin_manifest(self):
        # MEASURED harm, pinned as a regression. ``--out-root <tmp>`` with no
        # ``--manifest`` extracted into <tmp> but still wrote the PLUGIN's
        # committed references/skills-manifest.json, replacing the real
        # 115-package / 712-file source-of-truth with a 1-package one. Every
        # guard missed it: the dirty precondition was evaluated against the
        # scratch root (a non-worktree, so warning only), and the warning named
        # skills/ — which is not where the damage landed.
        #
        # Every other CLI case here passes --out-root and --manifest TOGETHER,
        # which is precisely why the suite could not see this.
        plugin_manifest, before = self._plugin_manifest_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            with _no_git_discovery(root):
                rc, stdout, _ = self._run(
                    ["--skills-root", str(root / "Skills"), "--out-root", str(root)]
                )
            after = plugin_manifest.read_bytes()
            derived = root / "references" / "skills-manifest.json"
            wrote_derived = derived.is_file()
            derived_doc = (
                json.loads(derived.read_text(encoding="utf-8")) if wrote_derived else {}
            )
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT ok", stdout)
        # The plugin's own manifest is byte-untouched …
        self.assertEqual(after, before)
        # … because the manifest followed --out-root instead.
        self.assertTrue(wrote_derived)
        self.assertEqual(derived_doc.get("skill_count"), 1)

    def test_verify_without_manifest_also_follows_out_root(self):
        # The read side of the same derivation: --verify must anchor the tree
        # it was pointed at, not the plugin's tree.
        self._plugin_manifest_bytes()  # the extract below omits --manifest too
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            with _no_git_discovery(root):
                rc, _, _ = self._run(
                    ["--skills-root", str(root / "Skills"), "--out-root", str(root)]
                )
                self.assertEqual(rc, 0)
                verify_rc, verify_out, _ = self._run(
                    ["--out-root", str(root), "--verify"]
                )
                # And it really is checking that tree: tamper, and it fails.
                (root / "skills" / "one" / "SKILL.md").write_text("x", encoding="utf-8")
                bad_rc, bad_out, _ = self._run(["--out-root", str(root), "--verify"])
        self.assertEqual(verify_rc, 0)
        self.assertIn("VERIFY ok skills=1 files=1", verify_out)
        self.assertEqual(bad_rc, 1)
        self.assertIn("VERIFY FAILED", bad_out)

    def test_explicit_manifest_still_overrides_the_derived_default(self):
        # The derivation is a DEFAULT, not a confinement: an operator who names
        # a manifest outside out_root still gets exactly that path.
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as away:
            root, elsewhere = pathlib.Path(tmp), pathlib.Path(away)
            named = elsewhere / "custom.json"
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            with _no_git_discovery(root):
                rc, _, _ = self._run(
                    ["--skills-root", str(root / "Skills"), "--out-root", str(root),
                     "--manifest", str(named)]
                )
            wrote_named = named.is_file()
            wrote_derived = (root / "references" / "skills-manifest.json").exists()
        self.assertEqual(rc, 0)
        self.assertTrue(wrote_named)
        self.assertFalse(wrote_derived)

    # ---- E4 failure: a corrupt zip fails the run with NO partial writes ----
    def test_cli_failure_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Skills" / "Alpha").mkdir(parents=True)
            (root / "Skills" / "Alpha" / "broken.zip").write_text("nope", encoding="utf-8")
            _make_zip(root / "Skills" / "Alpha", "good.zip", _skill_md("good"))
            rc, stdout, _ = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            extracted = (root / "skills").exists()
        self.assertEqual(rc, 1)
        self.assertIn("AUDIT failure", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)  # no partial manifest
        self.assertFalse(extracted)  # and nothing extracted at all

    # ---- SEC-1 end-to-end: a hostile frontmatter name escapes NOTHING ----
    def test_cli_hostile_name_writes_nothing(self):
        # The packet scenario: ``name: ..`` + member scripts/quality.py would
        # write <root>/scripts/quality.py without name validation.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "evil.zip", _skill_md(".."),
                      extra={"scripts/quality.py": "# payload\n"})
            rc, stdout, _ = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            escaped = (root / "scripts").exists()
            extracted = (root / "skills").exists()
        self.assertEqual(rc, 1)
        self.assertIn("unsafe skill name", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)
        self.assertFalse(extracted)
        self.assertFalse(escaped)

    # ---- COR-1 end-to-end: members that alias one target write NOTHING ----
    def test_cli_parent_path_member_writes_nothing(self):
        # The route with no ``.`` in it at all. Before the target invariant this
        # archive PASSED every entry-name check, planned cleanly, and then died
        # in extract with an unhandled FileExistsError — leaving
        # skills/demo/SKILL.md plus a regular file at skills/demo/sub, the exact
        # half-extracted package this module promises is impossible.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "nest.zip", _skill_md("demo"),
                      extra={"sub": "dir-as-file", "sub/x.md": "real member"})
            rc, stdout, _ = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            extracted = (root / "skills").exists()
        self.assertEqual(rc, 1)
        self.assertIn("AUDIT failure target=demo", stdout)
        self.assertIn("is a parent path of", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)
        self.assertFalse(extracted)  # not one byte on disk

    def test_cli_case_colliding_members_write_nothing(self):
        # The silent-substitution twin: on a case-insensitive filesystem both
        # members are ONE file, so the manifest would record two paths hashing
        # the alias's bytes and --verify would still call the tree intact.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "alias.zip", _skill_md("demo"),
                      extra={"skill.md": "substituted body"})
            rc, stdout, _ = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            extracted = (root / "skills").exists()
        self.assertEqual(rc, 1)
        self.assertIn("AUDIT failure target=demo", stdout)
        self.assertIn("may resolve to one target", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)
        self.assertFalse(extracted)

    # ---- C3: a write-time failure is RECORDED, and rolled back by nobody ----
    def test_cli_write_illegal_member_reports_instead_of_unwinding(self):
        # A member can be name-legal yet write-illegal, and no name predicate
        # can foresee it: this segment is past NAME_MAX, so the write raises
        # ENAMETOOLONG mid-package AFTER SKILL.md has landed. The run must
        # report an audit failure rather than raise a traceback — and must
        # leave what it wrote exactly where it is.
        long_member = "x" * 300 + ".md"
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "long.zip", _skill_md("demo"),
                      extra={long_member: "past NAME_MAX"})
            plans, failures = skillextract.plan_extractions(root / "Skills")
            # It really does clear every plan-time guard — otherwise this case
            # would prove nothing about the WRITE path.
            self.assertEqual(failures, [])
            self.assertEqual(len(plans), 1)
            self.assertTrue(skillextract._is_safe_entry(long_member))
            rc, stdout, stderr = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            left = sorted(p.name for p in (root / "skills" / "demo").iterdir())
        self.assertEqual(rc, 1)
        self.assertIn("AUDIT failure", stdout)
        self.assertIn("extraction failed", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)  # still no manifest for a failed run
        self.assertEqual(left, ["SKILL.md"])  # the partial write STAYS
        self.assertIn("may hold partial writes", stderr)
        self.assertIn("nothing was rolled back", stderr)

    def test_cli_write_failure_keeps_written_members_and_names_the_undo(self):
        # The other unforeseeable write failure — a full or read-only out_root —
        # strikes MID-package, after real bytes have landed. SKILL.md is written
        # first and the second member then fails. The already-written SKILL.md
        # stays, and because this destination is not a git worktree the run says
        # so plainly instead of printing a git command that would not work.
        real_write_bytes = pathlib.Path.write_bytes
        written_names: list[str] = []

        def _fail_on_the_second_write(self, data):
            written_names.append(self.name)
            if len(written_names) == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_write_bytes(self, data)

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "demo.zip", _skill_md("demo"),
                      extra={"scripts/run.sh": "#/bin/sh\n"})
            with _no_git_discovery(root), mock.patch.object(
                pathlib.Path, "write_bytes", _fail_on_the_second_write
            ):
                rc, stdout, stderr = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            survived = (root / "skills" / "demo" / "SKILL.md").exists()
        self.assertEqual(rc, 1)
        self.assertEqual(written_names, ["SKILL.md", "run.sh"])  # SKILL.md landed
        self.assertIn("AUDIT failure", stdout)
        self.assertIn("extraction failed", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)
        self.assertTrue(survived)  # the member that succeeded is NOT deleted
        self.assertIn("nothing was rolled back", stderr)
        self.assertIn("is not a git worktree", stderr)
        self.assertNotIn("git -C", stderr)  # no undo is offered that cannot work

    def test_cli_non_worktree_destination_warns_once_and_proceeds(self):
        # A scratch-dir extraction is legitimate use and must NOT be refused:
        # the run warns that no undo exists there, then does the work. A fix
        # that blocks honest use is worse than the gap it closes.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            with _no_git_discovery(root):
                rc, stdout, stderr = self._run(self._args(root))
            extracted = (root / "skills" / "one" / "SKILL.md").exists()
        self.assertEqual(rc, 0)  # proceeds
        self.assertIn("AUDIT ok", stdout)
        self.assertTrue(extracted)
        self.assertIn("is not a git worktree", stderr)
        self.assertIn("no undo is available", stderr)
        # Warned ONCE, not once per package.
        self.assertEqual(stderr.count("is not a git worktree"), 1)

    def test_cli_verify_nonzero_on_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            rc, _, _ = self._run(self._args(root))
            self.assertEqual(rc, 0)
            (root / "skills" / "one" / "SKILL.md").write_text("tampered", encoding="utf-8")
            verify_rc, verify_out, _ = self._run(
                ["--out-root", str(root),
                 "--manifest", str(root / "refs" / "skills-manifest.json"), "--verify"]
            )
        self.assertEqual(verify_rc, 1)
        self.assertIn("VERIFY FAILED", verify_out)
        self.assertIn("skills/one/SKILL.md", verify_out)

    def test_cli_verify_missing_manifest_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            rc, _, stderr = self._run(
                ["--manifest", str(root / "absent.json"), "--verify"]
            )
        self.assertEqual(rc, 1)
        self.assertIn("cannot load manifest", stderr)

    def test_cli_missing_skills_root_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            rc, _, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertIn("skills root not found", stderr)

    # ---- C5: the manifest write is atomic, and its failure is not a traceback --
    def test_manifest_write_failure_leaves_the_previous_manifest_intact(self):
        # This was the LAST failure that could still raise: the write sat
        # outside every try, AFTER skills/ was fully written, and write_text
        # opens 'w' — so it TRUNCATES first and an ENOSPC left a truncated or
        # empty committed manifest, falsifying "a failed run never leaves a bad
        # manifest behind". Staging a sibling and os.replace-ing it means the
        # previous document survives byte-for-byte.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            manifest_path = root / "refs" / "skills-manifest.json"
            manifest_path.parent.mkdir(parents=True)
            previous = b'{"version": 2, "skill_count": 99, "the": "old anchor"}\n'
            manifest_path.write_bytes(previous)

            real_write_text = pathlib.Path.write_text

            def _fail_on_the_stage(self, data, **kwargs):
                if self.name.endswith(".tmp"):
                    raise OSError(errno.ENOSPC, "No space left on device")
                return real_write_text(self, data, **kwargs)

            with _no_git_discovery(root), mock.patch.object(
                pathlib.Path, "write_text", _fail_on_the_stage
            ):
                rc, stdout, stderr = self._run(self._args(root))  # no traceback
            after = manifest_path.read_bytes()
            leftovers = sorted(p.name for p in manifest_path.parent.iterdir())
            extracted = (root / "skills" / "one" / "SKILL.md").is_file()
        self.assertEqual(rc, 1)
        self.assertEqual(after, previous)  # byte-intact, never truncated
        self.assertIn("cannot write manifest", stderr)
        self.assertIn("was NOT replaced", stderr)
        self.assertIn("AUDIT ok", stdout)  # the EXTRACTION really did succeed
        self.assertTrue(extracted)  # and its writes stay, as ever
        # The stage is cleaned up: no stray .tmp is left beside the manifest,
        # where the dirty precondition's pathspec would never have seen it.
        self.assertEqual(leftovers, ["skills-manifest.json"])

    def test_manifest_swap_failure_also_leaves_the_previous_manifest_intact(self):
        # The other half: the stage is written fine and the SWAP fails (a
        # cross-device rename, an EACCES on the directory). Same contract.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            manifest_path = root / "refs" / "skills-manifest.json"
            manifest_path.parent.mkdir(parents=True)
            previous = b'{"the": "old anchor"}\n'
            manifest_path.write_bytes(previous)
            with _no_git_discovery(root), mock.patch.object(
                skillextract.os, "replace",
                side_effect=OSError(errno.EXDEV, "Invalid cross-device link"),
            ):
                rc, _, stderr = self._run(self._args(root))
            after = manifest_path.read_bytes()
            leftovers = sorted(p.name for p in manifest_path.parent.iterdir())
        self.assertEqual(rc, 1)
        self.assertEqual(after, previous)
        self.assertIn("cannot write manifest", stderr)
        self.assertEqual(leftovers, ["skills-manifest.json"])  # stage removed

    def test_manifest_is_staged_then_swapped_not_written_in_place(self):
        # The mechanism itself, so a revert to a plain write_text is caught:
        # the target is never opened for writing — a sibling is, and os.replace
        # moves it onto the target.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            manifest_path = root / "refs" / "skills-manifest.json"
            written_to: list[str] = []
            replaced: list[tuple[str, str]] = []
            real_write_text = pathlib.Path.write_text
            real_replace = skillextract.os.replace

            def _record_write(self, data, **kwargs):
                written_to.append(str(self))
                return real_write_text(self, data, **kwargs)

            def _record_replace(src, dst):
                replaced.append((str(src), str(dst)))
                return real_replace(src, dst)

            with _no_git_discovery(root), mock.patch.object(
                pathlib.Path, "write_text", _record_write
            ), mock.patch.object(skillextract.os, "replace", _record_replace):
                rc, _, _ = self._run(self._args(root))
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(doc["skill_count"], 1)  # the swap really landed
        self.assertNotIn(str(manifest_path), written_to)  # never truncated
        self.assertIn(f"{manifest_path}.tmp", written_to)
        self.assertEqual(replaced, [(f"{manifest_path}.tmp", str(manifest_path))])

    def test_cli_encrypted_archive_is_an_audit_failure_not_a_traceback(self):
        # C4 end-to-end: the whole point of widening the guard is that this
        # exits 1 with an AUDIT line instead of a traceback, and writes nothing.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            locked = _make_zip(root / "Skills" / "Alpha", "locked.zip",
                               _skill_md("locked"))
            _mark_member_encrypted(locked)
            rc, stdout, _ = self._run(self._args(root))
            manifest_written = (root / "refs" / "skills-manifest.json").exists()
            extracted = (root / "skills").exists()
        self.assertEqual(rc, 1)
        self.assertIn("AUDIT failure", stdout)
        self.assertIn("unreadable zip archive", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertFalse(manifest_written)
        self.assertFalse(extracted)


@unittest.skipUnless(_HAS_GIT, "git is required")
class TestDirtyPrecondition(unittest.TestCase):
    """The precondition that REPLACED the rollback.

    This module cannot undo itself and no longer pretends to: writes may be
    partial and nothing is ever deleted. What it owes the operator instead is
    that their undo is CLEAN, and that is only true when the output subtree
    starts clean — otherwise ``git checkout``/``git clean`` would take their
    uncommitted work with it. So a dirty subtree is refused before a byte is
    written, and ``--allow-dirty`` is the explicit escape.

    Real repos, real git: mocking ``subprocess`` here would only prove the mock.
    """

    def _args(self, root, *extra, manifest=None):
        return [
            "--skills-root", str(root / "Skills"),
            "--out-root", str(root),
            "--manifest", str(manifest or root / "refs" / "skills-manifest.json"),
            *extra,
        ]

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = skillextract.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def _repo(self, extra_files=None):
        """A repo whose skills/ subtree is committed and clean, plus a Skills/ zip."""
        files = {"skills/one/SKILL.md": _skill_md("one"), "README.md": "top\n"}
        files.update(extra_files or {})
        root = _git_repo(self, files)
        _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
        return root

    # ---- the probe itself ----
    def test_dirty_subtree_reports_absent_outside_a_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with _no_git_discovery(root):
                self.assertEqual(
                    skillextract._dirty_subtree(root, ["skills"]),
                    (skillextract._GIT_ABSENT, []),
                )

    def test_dirty_subtree_reports_clean_for_a_clean_subtree(self):
        root = self._repo()
        self.assertEqual(
            skillextract._dirty_subtree(root, ["skills"]),
            (skillextract._GIT_CLEAN, []),
        )

    def test_dirty_subtree_is_scoped_to_the_output_subtree(self):
        # Unrelated dirt elsewhere in the operator's repo is NOT this run's
        # business: blocking on it would be a false reject.
        root = self._repo()
        (root / "README.md").write_text("edited elsewhere\n", encoding="utf-8")
        (root / "untracked-elsewhere.md").write_text("stray\n", encoding="utf-8")
        state, lines = skillextract._dirty_subtree(root, ["skills"])
        self.assertEqual((state, lines), (skillextract._GIT_CLEAN, []))
        # Sanity: git DOES see that dirt when the scope is widened.
        state, lines = skillextract._dirty_subtree(root, ["."])
        self.assertEqual(state, skillextract._GIT_DIRTY)
        self.assertNotEqual(lines, [])

    def test_dirty_subtree_reports_git_unavailable_as_absent(self):
        # A git that cannot run AT ALL means "no undo here" (a warning), never
        # dirt (a refusal) — failing closed would block honest use.
        root = self._repo()
        with mock.patch.object(
            skillextract.subprocess, "run", side_effect=OSError("no git")
        ):
            self.assertEqual(
                skillextract._dirty_subtree(root, ["skills"]),
                (skillextract._GIT_ABSENT, []),
            )

    def test_dirty_subtree_separates_a_broken_worktree_from_no_worktree(self):
        # C4: these were ONE answer (a bare None) and had to be split. Inside a
        # REAL worktree whose `git status` fails — a held index.lock, a
        # mid-rebase, permissions, the timeout — the old code returned None, so
        # the refusal silently never fired over a possibly-dirty subtree and
        # the operator was told "not a git worktree" on a machine where that
        # was FALSE. rev-parse still says `true`, so the state must be
        # UNREADABLE, not ABSENT.
        root = self._repo()
        (root / "skills" / "one" / "NOTES.md").write_text("dirty\n", encoding="utf-8")
        real_run = skillextract.subprocess.run

        def _status_fails(argv, **kwargs):
            if argv[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(
                    argv, 128, "", "fatal: Unable to create index.lock: File exists\n"
                )
            return real_run(argv, **kwargs)

        with mock.patch.object(skillextract.subprocess, "run", _status_fails):
            state, lines = skillextract._dirty_subtree(root, ["skills"])
        self.assertEqual(state, skillextract._GIT_UNREADABLE)
        self.assertEqual(lines, [])  # git's error text is never parsed as dirt
        # And the un-mocked probe on the very same repo answers DIRTY, which is
        # what the failed query was hiding.
        self.assertEqual(
            skillextract._dirty_subtree(root, ["skills"])[0], skillextract._GIT_DIRTY
        )

    def test_dirty_subtree_reports_unreadable_when_status_cannot_run(self):
        # The other half of the same split: rev-parse answers, the status call
        # then raises. That is a worktree we could not read, never an absent one.
        root = self._repo()
        real_run = skillextract.subprocess.run

        def _status_raises(argv, **kwargs):
            if argv[:2] == ["git", "status"]:
                raise subprocess.TimeoutExpired(argv, 30)
            return real_run(argv, **kwargs)

        with mock.patch.object(skillextract.subprocess, "run", _status_raises):
            self.assertEqual(
                skillextract._dirty_subtree(root, ["skills"]),
                (skillextract._GIT_UNREADABLE, []),
            )

    def test_unreadable_worktree_refuses_and_writes_nothing(self):
        # The end-to-end consequence: a refusal, not the "not a git worktree"
        # warning that was FALSE here, and not one byte written.
        root = self._repo()
        real_run = skillextract.subprocess.run

        def _status_fails(argv, **kwargs):
            if argv[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(argv, 128, "", "fatal: bad state\n")
            return real_run(argv, **kwargs)

        with mock.patch.object(skillextract.subprocess, "run", _status_fails):
            rc, stdout, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertIn("refusing to extract", stderr)
        self.assertIn("could not report", stderr)
        self.assertIn("nothing was written", stderr)
        # It must NOT claim the destination has no VCS — that was the lie.
        self.assertNotIn("is not a git worktree", stderr)
        self.assertEqual(stdout, "")  # refused before the audit even runs
        self.assertFalse((root / "refs" / "skills-manifest.json").exists())

    def test_allow_dirty_overrides_an_unreadable_worktree(self):
        # The same explicit escape the dirty refusal has: the operator can say
        # "I accept the risk" rather than being hard-blocked by a stuck lock.
        root = self._repo()
        real_run = skillextract.subprocess.run

        def _status_fails(argv, **kwargs):
            if argv[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(argv, 128, "", "fatal: bad state\n")
            return real_run(argv, **kwargs)

        with mock.patch.object(skillextract.subprocess, "run", _status_fails):
            rc, stdout, stderr = self._run(self._args(root, "--allow-dirty"))
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT ok", stdout)
        self.assertNotIn("refusing to extract", stderr)

    # ---- the refusal ----
    def test_modified_tracked_file_refuses_and_writes_nothing(self):
        root = self._repo()
        victim = root / "skills" / "one" / "SKILL.md"
        victim.write_text("operator's uncommitted edit\n", encoding="utf-8")
        rc, stdout, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertIn("refusing to extract", stderr)
        self.assertIn("skills/one/SKILL.md", stderr)
        self.assertIn("--allow-dirty", stderr)
        self.assertIn("nothing was written", stderr)
        self.assertEqual(stdout, "")  # refused before the audit even runs
        # The refusal PRESERVED the work it was protecting …
        self.assertEqual(victim.read_text(encoding="utf-8"),
                         "operator's uncommitted edit\n")
        # … and wrote no manifest.
        self.assertFalse((root / "refs" / "skills-manifest.json").exists())

    def test_untracked_stray_in_the_subtree_refuses(self):
        # The stray is the case with no other copy: `git checkout` would not
        # restore it and `git clean` would delete it, so it must block.
        root = self._repo()
        stray = root / "skills" / "one" / "NOTES.md"
        stray.write_text("untracked, unrecoverable\n", encoding="utf-8")
        rc, _, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertIn("refusing to extract", stderr)
        self.assertIn("NOTES.md", stderr)
        self.assertTrue(stray.is_file())  # untouched

    def test_staged_change_in_the_subtree_refuses(self):
        # Staged-but-uncommitted is dirt too: `git checkout -- skills` restores
        # from the INDEX, so a staged edit survives the undo unnoticed.
        root = self._repo()
        (root / "skills" / "one" / "SKILL.md").write_text("staged\n", encoding="utf-8")
        _git(root, "add", "skills/one/SKILL.md")
        rc, _, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertIn("refusing to extract", stderr)

    def test_dirty_listing_is_capped_but_the_count_stays_exact(self):
        # A 715-line refusal is a wall, not a message — but an under-reported
        # COUNT would be a lie, so only the listing is cut.
        root = self._repo()
        extra = skillextract._DIRTY_PREVIEW + 3
        for i in range(extra):
            (root / "skills" / f"stray{i:02d}.md").write_text("x\n", encoding="utf-8")
        rc, _, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertIn(f"{extra} uncommitted change(s)", stderr)
        self.assertIn("and 3 more", stderr)
        self.assertEqual(stderr.count("stray"), skillextract._DIRTY_PREVIEW)

    # ---- C3: the write-set is BOTH destinations, not just skills/ ----
    def test_dirty_tracked_manifest_refuses_too(self):
        # "Your undo will be clean" was false one directory over. The run also
        # writes references/skills-manifest.json, but the precondition scoped
        # to skills/ alone: an operator with uncommitted edits to that TRACKED
        # file got no refusal, no warning, and `git checkout -- skills`
        # restored nothing where the damage was.
        root = self._repo({"references/skills-manifest.json": '{"old": true}\n'})
        victim = root / "references" / "skills-manifest.json"
        victim.write_text('{"operator": "uncommitted"}\n', encoding="utf-8")
        rc, stdout, stderr = self._run(
            self._args(root, manifest=root / "references" / "skills-manifest.json")
        )
        self.assertEqual(rc, 1)
        self.assertIn("refusing to extract", stderr)
        self.assertIn("references/skills-manifest.json", stderr)
        self.assertIn("nothing was written", stderr)
        self.assertEqual(stdout, "")
        # The edit it was protecting is exactly as the operator left it.
        self.assertEqual(victim.read_text(encoding="utf-8"),
                         '{"operator": "uncommitted"}\n')

    def test_written_pathspecs_cover_the_manifest_under_out_root(self):
        root = pathlib.Path("/nonexistent-root")
        self.assertEqual(
            skillextract._written_pathspecs(
                root, root / "references" / "skills-manifest.json"
            ),
            ["skills", "references/skills-manifest.json"],
        )
        # A manifest OUTSIDE out_root is no pathspec of this worktree …
        self.assertEqual(
            skillextract._written_pathspecs(root, pathlib.Path("/elsewhere/m.json")),
            ["skills"],
        )
        # … and one already inside skills/ is not listed twice.
        self.assertEqual(
            skillextract._written_pathspecs(root, root / "skills" / "m.json"),
            ["skills"],
        )

    def test_recovery_names_the_manifest_on_its_own_lines(self):
        # `git checkout -- a b` fails ENTIRELY when one pathspec matches
        # nothing git knows, so folding an untracked manifest into the skills/
        # line would take the recovery that DOES work down with it. Both
        # commands are named per path because the manifest has two states and
        # each needs a different one.
        root = pathlib.Path("/repo")
        lines = skillextract._recovery_lines(
            root, ["skills", "references/skills-manifest.json"], under_git=True
        )
        for expected in (
            "  git -C /repo checkout -- skills",
            "  git -C /repo clean -fd skills",
            "  git -C /repo checkout -- references/skills-manifest.json",
            "  git -C /repo clean -fd references/skills-manifest.json",
        ):
            self.assertIn(expected, lines)
        self.assertTrue(any("COMMITTED" in line for line in lines))
        # With only the package pathspec there is no manifest line and no
        # caveat to explain.
        plain = skillextract._recovery_lines(root, ["skills"], under_git=True)
        self.assertEqual(len(plain), 3)
        self.assertFalse(any("COMMITTED" in line for line in plain))

    def test_the_printed_manifest_recovery_really_runs(self):
        # A recovery command is only a recovery if it EXECUTES, so the printed
        # lines are parsed back out and run verbatim against real git — the
        # same thing the operator would paste. `_git` uses check=True, so a
        # command that errors on the other state's pathspec fails this case.
        root = self._repo({"references/skills-manifest.json": '{"committed": 1}\n'})
        committed = root / "references" / "skills-manifest.json"
        committed.write_text('{"overwritten": 1}\n', encoding="utf-8")
        stray = root / "skills" / "one" / "NOTES.md"
        stray.write_text("created by the run\n", encoding="utf-8")
        pathspecs = ["skills", "references/skills-manifest.json"]
        prefix = f"  git -C {root} "
        ran = 0
        for line in skillextract._recovery_lines(root, pathspecs, under_git=True):
            if line.startswith(prefix):
                _git(root, *line[len(prefix):].split())
                ran += 1
        self.assertEqual(ran, 4)  # both commands for both pathspecs
        # The committed manifest is back and the run's stray is gone …
        self.assertEqual(committed.read_text(encoding="utf-8"), '{"committed": 1}\n')
        self.assertFalse(stray.exists())
        # … which is the whole claim: the undo really is clean.
        self.assertEqual(
            skillextract._dirty_subtree(root, pathspecs),
            (skillextract._GIT_CLEAN, []),
        )

    def test_write_failure_recovery_names_the_manifest_too(self):
        # End-to-end: the printed undo covers every path the run writes.
        def _fail_immediately(self, data):
            raise OSError(errno.ENOSPC, "No space left on device")

        root = self._repo({"references/skills-manifest.json": '{"old": true}\n'})
        with mock.patch.object(pathlib.Path, "write_bytes", _fail_immediately):
            rc, _, stderr = self._run(
                self._args(root, manifest=root / "references" / "skills-manifest.json")
            )
        self.assertEqual(rc, 1)
        self.assertIn(f"git -C {root} checkout -- skills", stderr)
        self.assertIn(
            f"git -C {root} checkout -- references/skills-manifest.json", stderr
        )
        # The named commands really are the operator's undo, so they must RUN.
        _git(root, "checkout", "--", "skills", "references/skills-manifest.json")
        _git(root, "clean", "-qfd", "skills")
        self.assertEqual(
            skillextract._dirty_subtree(
                root, ["skills", "references/skills-manifest.json"]
            ),
            (skillextract._GIT_CLEAN, []),
        )

    # ---- the escapes ----
    def test_allow_dirty_extracts_anyway(self):
        root = self._repo()
        stray = root / "skills" / "one" / "NOTES.md"
        stray.write_text("untracked\n", encoding="utf-8")
        rc, stdout, stderr = self._run(self._args(root, "--allow-dirty"))
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT ok", stdout)
        self.assertNotIn("refusing to extract", stderr)
        self.assertTrue((root / "skills" / "one" / "SKILL.md").is_file())

    def test_clean_subtree_extracts_without_a_warning(self):
        root = self._repo()
        rc, stdout, stderr = self._run(self._args(root))
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT ok", stdout)
        self.assertEqual(stderr, "")  # a clean worktree says nothing at all
        self.assertTrue((root / "refs" / "skills-manifest.json").is_file())

    def test_dirt_outside_the_subtree_does_not_block(self):
        root = self._repo()
        (root / "README.md").write_text("unrelated edit\n", encoding="utf-8")
        rc, stdout, stderr = self._run(self._args(root))
        self.assertEqual(rc, 0)
        self.assertIn("AUDIT ok", stdout)
        self.assertNotIn("refusing to extract", stderr)

    # ---- the report ----
    def test_write_failure_names_the_exact_git_recovery_and_runs_nothing(self):
        # The tool performs no rollback, so a failed run owes the operator the
        # two commands that undo it — and must run neither.
        real_write_bytes = pathlib.Path.write_bytes
        written_names: list[str] = []

        def _fail_after_a_real_new_file(self, data):
            # Writes land as skills/one/SKILL.md (byte-identical, no diff),
            # skills/two/SKILL.md (a genuinely NEW file), then run.sh — which
            # fails, leaving package "two" half written.
            written_names.append(self.name)
            if len(written_names) == 3:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_write_bytes(self, data)

        root = self._repo()
        _make_zip(root / "Skills" / "Alpha", "two.zip", _skill_md("two"),
                  extra={"scripts/run.sh": "#/bin/sh\n"})
        with mock.patch.object(
            pathlib.Path, "write_bytes", _fail_after_a_real_new_file
        ):
            rc, stdout, stderr = self._run(self._args(root))
        self.assertEqual(rc, 1)
        self.assertEqual(written_names, ["SKILL.md", "SKILL.md", "run.sh"])
        self.assertIn("AUDIT MISMATCH", stdout)
        self.assertIn("may hold partial writes", stderr)
        self.assertIn(f"git -C {root} checkout -- skills", stderr)
        self.assertIn(f"git -C {root} clean -fd skills", stderr)
        # REPORTED, not performed: the partial write is still on disk and the
        # subtree is still dirty, exactly as the message says.
        self.assertTrue((root / "skills" / "two" / "SKILL.md").is_file())
        self.assertEqual(
            skillextract._dirty_subtree(root, ["skills"])[0], skillextract._GIT_DIRTY
        )
        # And the named commands really are the undo — run them by hand here,
        # which is the operator's job, and the subtree comes back clean.
        _git(root, "checkout", "--", "skills")
        _git(root, "clean", "-qfd", "skills")
        self.assertEqual(
            skillextract._dirty_subtree(root, ["skills"]),
            (skillextract._GIT_CLEAN, []),
        )
        self.assertFalse((root / "skills" / "two").exists())  # partial swept
        self.assertEqual(
            (root / "skills" / "one" / "SKILL.md").read_text(encoding="utf-8"),
            _skill_md("one"),
        )


class TestCommittedNamePolicy(unittest.TestCase):
    """CALIBRATION, not falsification: the guards still admit what ships.

    Every case here is a one-way check on the REAL inventory — the 115
    committed skill names in references/skill-registry.json against the
    package-name allow-pattern, and the 712 committed member entry names in
    references/skills-manifest.json against _is_safe_entry and the
    target-injectivity invariant. None of them fails if a guard is loosened
    (the shipped inventory carries no hostile shape to catch); they fail if a
    guard is TIGHTENED past what really ships, which is the regression the
    falsifying cases above cannot see. If a future real name ever fails one,
    widen that predicate minimally and document why — never weaken it silently.
    """

    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (_REPO_ROOT / "references" / "skill-registry.json").read_text(encoding="utf-8")
        )
        cls.names = [entry["name"] for entry in registry["skills"]]
        cls.manifest = json.loads(
            (_REPO_ROOT / "references" / "skills-manifest.json").read_text(encoding="utf-8")
        )

    def test_all_committed_names_match_allow_pattern(self):
        self.assertEqual(len(self.names), 115)  # pin the real inventory
        for name in self.names:
            self.assertTrue(skillextract._NAME_RE.match(name), name)

    def test_all_committed_names_are_safe_package_names(self):
        # Belt and braces: the full predicate (pattern AND the first-party
        # collision check) accepts every shipped name.
        for name in self.names:
            self.assertTrue(skillextract._is_safe_package_name(name), name)
        self.assertEqual(skillregistry.FIRST_PARTY_DIRS.isdisjoint(self.names), True)

    def test_committed_entry_names_stay_admissible(self):
        # The entry-name predicate is the one the zip layer applies to every
        # member, so calibrate it on the same committed inventory: strip each
        # skill's dir prefix back off its recorded paths and re-run the guard.
        checked = 0
        dotfiles = []
        for skill in self.manifest["skills"]:
            prefix = skill["dir"] + "/"
            for file_entry in skill["files"]:
                path = file_entry["path"]
                self.assertTrue(path.startswith(prefix), path)
                entry = path[len(prefix):]
                with self.subTest(entry=path):
                    self.assertTrue(skillextract._is_safe_entry(entry), path)
                if entry.startswith("."):
                    dotfiles.append(path)
                checked += 1
        # Pin the count so an under-iteration cannot pass vacuously.
        self.assertEqual(checked, self.manifest["file_count"])
        self.assertEqual(checked, 712)  # pin the real inventory
        # Leading-dot FILE names really do ship (the .security-scan-passed
        # markers): the guard rejects a bare ``.`` SEGMENT, never these.
        self.assertEqual(len(dotfiles), 4)
        for path in dotfiles:
            self.assertTrue(path.endswith("/.security-scan-passed"), path)

    def test_committed_packages_map_to_distinct_targets(self):
        # Calibrate the target invariant on the same inventory: all 712 shipped
        # members must still be accepted. A rejection here means the invariant
        # is too strict for real archives — say so and fix it, never weaken it.
        checked = 0
        for skill in self.manifest["skills"]:
            prefix = skill["dir"] + "/"
            entries = [f["path"][len(prefix):] for f in skill["files"]]
            with self.subTest(package=skill["dir"]):
                self.assertEqual(skillextract._target_conflicts(entries), [])
            checked += len(entries)
        self.assertEqual(checked, 712)  # pin the real inventory
        # The keys must also be as distinct as the paths are: one key per member.
        keys = {
            skillextract._target_key(f["path"])
            for skill in self.manifest["skills"] for f in skill["files"]
        }
        self.assertEqual(len(keys), 712)

    def test_committed_entries_key_identically_under_every_folding(self):
        # Calibration for the fold changes: replacing casefold() had to be a
        # NO-OP for everything that actually ships, and this MEASURES that
        # rather than assuming it. Every committed member entry is ASCII, where
        # simple folding, lower() and casefold() all agree — so all 712 stay
        # accepted and the change can only affect what a FUTURE non-ASCII
        # archive may carry.
        checked = 0
        for skill in self.manifest["skills"]:
            for file_entry in skill["files"]:
                path = file_entry["path"]
                with self.subTest(entry=path):
                    self.assertEqual(path.lower(), path.casefold())
                    self.assertEqual(skillextract._simple_fold(path), path.lower())
                checked += 1
        self.assertEqual(checked, 712)  # pin the real inventory


class TestCommittedManifest(unittest.TestCase):
    """E3-style integrity: the COMMITTED manifest proves the extracted tree.

    Zip-free by design — runs anywhere the repo is checked out (GitHub CI),
    re-hashing every file under skills/ against references/skills-manifest.json.
    """

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (_REPO_ROOT / "references" / "skills-manifest.json").read_text(encoding="utf-8")
        )

    def test_committed_manifest_validates_against_schemas(self):
        self.assertEqual(validate.validate(self.manifest, "skills-manifest"), [])
        for i, entry in enumerate(self.manifest["skills"]):
            self.assertEqual(
                validate.validate(entry, "skills-manifest-entry"), [],
                f"skills[{i}] invalid",
            )
        self.assertEqual(skillextract.validate_manifest(self.manifest), [])

    def test_committed_manifest_skill_count(self):
        # Pin the real inventory so an under-count regeneration fails in CI.
        self.assertEqual(self.manifest["skill_count"], 115)
        self.assertEqual(len(self.manifest["skills"]), 115)

    def test_extracted_tree_matches_manifest(self):
        self.assertEqual(skillextract.verify_manifest(self.manifest, _REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
