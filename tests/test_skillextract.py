"""Unit tests for scripts/skillextract.py (skill extractor + sha256 manifest).

Fixtures are synthetic zip trees built with tempfile + zipfile — the tests
never depend on the real Skills/ tree. The one exception is
TestCommittedManifest, which loads the COMMITTED
references/skills-manifest.json and re-hashes the extracted skills/ tree
against it — zip-free, so it runs anywhere the repo is checked out (GitHub CI).
"""
import contextlib
import io
import json
import pathlib
import stat
import tempfile
import unittest
import zipfile

from scripts import skillextract, skillregistry, validate

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

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

    def test_is_safe_entry_backslash_rejected(self):
        self.assertFalse(skillextract._is_safe_entry("..\\evil.md"))
        self.assertFalse(skillextract._is_safe_entry("a\\b.md"))
        self.assertTrue(skillextract._is_safe_entry("a/b.md"))


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
        lines, ok = skillextract.audit(plans, [], manifest)
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
        lines, ok = skillextract.audit(plans, [("bad.zip", "not a readable zip")], manifest)
        self.assertIn("AUDIT failure target=bad.zip reason=not a readable zip", lines)
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)

    def test_manifest_count_drift_flagged(self):
        plans = [_plan("a", pathlib.Path("a.zip"), ["SKILL.md"])]
        lines, ok = skillextract.audit(plans, [], {"skill_count": 2, "file_count": 1})
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)


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


class TestCommittedNamePolicy(unittest.TestCase):
    """The package-name allow-pattern is calibrated on the real inventory.

    Every one of the 115 committed skill names in
    references/skill-registry.json must match it — if a future real name ever
    fails, widen the pattern minimally and document why.
    """

    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (_REPO_ROOT / "references" / "skill-registry.json").read_text(encoding="utf-8")
        )
        cls.names = [entry["name"] for entry in registry["skills"]]

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
