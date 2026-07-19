"""Unit tests for scripts/skillregistry.py (skill-registry builder + E4 audit).

Fixtures are synthetic zip trees built with tempfile + zipfile — the tests never
depend on the real Skills/ tree. The one exception is the E3 test, which validates
the COMMITTED references/skill-registry.json against the canonical schemas and,
when the (untracked) Skills/ tree is present on disk, cross-checks it against the
live zips.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

from scripts import skillregistry, validate

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

_FRONTMATTER = """---
name: {name}
description: "{description}"
license: MIT
metadata:
  author: someone
  tags: ["x", "y"]
---

# Body
"""


def _skill_md(name="demo-skill", description="Does demo things."):
    return _FRONTMATTER.format(name=name, description=description)


def _make_zip(category_dir: pathlib.Path, filename: str, skill_md=None, extra=None):
    """Write a synthetic skill zip: SKILL.md (unless None) + LICENSE + extras."""
    category_dir.mkdir(parents=True, exist_ok=True)
    zip_path = category_dir / filename
    with zipfile.ZipFile(zip_path, "w") as archive:
        if skill_md is not None:
            archive.writestr("SKILL.md", skill_md)
        archive.writestr("LICENSE", "MIT")
        for member, content in (extra or {}).items():
            archive.writestr(member, content)
    return zip_path


class TestParseFrontmatter(unittest.TestCase):
    def test_happy_path_quoted_and_unquoted(self):
        fields = skillregistry.parse_frontmatter(_skill_md())
        self.assertEqual(fields["name"], "demo-skill")
        self.assertEqual(fields["description"], "Does demo things.")
        self.assertEqual(fields["license"], "MIT")

    def test_nested_blocks_are_ignored(self):
        fields = skillregistry.parse_frontmatter(_skill_md())
        self.assertNotIn("author", fields)  # indented under metadata:
        self.assertNotIn("tags", fields)
        self.assertEqual(fields["metadata"], "")  # key with empty value

    def test_single_quoted_value(self):
        fields = skillregistry.parse_frontmatter(
            "---\nname: demo\ndescription: 'single quoted'\n---\n"
        )
        self.assertEqual(fields["description"], "single quoted")

    # ---- failure: no fence is a hard parse error ----
    def test_missing_fence_raises(self):
        with self.assertRaises(ValueError):
            skillregistry.parse_frontmatter("name: nope\ndescription: nope\n")


class TestExtractTriggers(unittest.TestCase):
    def test_triggered_when_users_ask(self):
        triggers = skillregistry.extract_triggers(
            "Assistant for planning. Triggered when the user asks for help organizing, "
            "planning their day, or beating procrastination."
        )
        self.assertEqual(
            triggers, ["organizing", "planning their day", "beating procrastination"]
        )

    def test_use_when_form(self):
        triggers = skillregistry.extract_triggers(
            "OKR coach. Use when the user mentions OKR, goal management, or quarterly goals."
        )
        self.assertEqual(triggers, ["OKR", "goal management", "quarterly goals"])

    def test_triggered_by_phrases(self):
        triggers = skillregistry.extract_triggers(
            "Polishes paragraphs. Triggered by phrases like 'polish this', "
            "'check the grammar'."
        )
        self.assertEqual(triggers, ["polish this", "check the grammar"])

    # ---- boundary: no phrasing / empty input yields no signals ----
    def test_no_trigger_phrasing(self):
        self.assertEqual(
            skillregistry.extract_triggers("Renders charts as images and nothing else."), []
        )

    def test_empty_description(self):
        self.assertEqual(skillregistry.extract_triggers(""), [])


class TestClassifyZip(unittest.TestCase):
    def test_full_entry_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = _make_zip(
                pathlib.Path(tmp) / "Engineering",
                "demo-skill.zip",
                _skill_md(description="Does demos. Trigger when users mention demos."),
                extra={"scripts/run.sh": "#/bin/sh\n"},
            )
            entry = skillregistry.classify_zip(zip_path, "Engineering")
        self.assertEqual(entry["name"], "demo-skill")
        self.assertEqual(entry["category"], "Engineering")
        self.assertEqual(entry["triggers"], ["demos"])
        self.assertEqual(entry["zip"], "demo-skill.zip")
        # The registry stays compact: archive member lists are not carried.
        self.assertNotIn("entries", entry)
        self.assertNotIn("has_payload", entry)

    # ---- failure paths: missing manifest / corrupt archive / no frontmatter ----
    def test_missing_skill_md_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = _make_zip(pathlib.Path(tmp) / "Finance", "empty.zip", skill_md=None)
            with self.assertRaises(ValueError):
                skillregistry.classify_zip(zip_path, "Finance")

    def test_non_zip_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "Finance"
            bad.mkdir()
            zip_path = bad / "broken.zip"
            zip_path.write_text("this is not a zip archive", encoding="utf-8")
            with self.assertRaises(ValueError):
                skillregistry.classify_zip(zip_path, "Finance")

    def test_no_frontmatter_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = _make_zip(
                pathlib.Path(tmp) / "Finance", "bare.zip", "# just a body\n"
            )
            with self.assertRaises(ValueError):
                skillregistry.classify_zip(zip_path, "Finance")

    # ---- boundary: a missing description is tolerated (entry still classifies) ----
    def test_missing_description_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = _make_zip(
                pathlib.Path(tmp) / "Finance", "nodesc.zip", "---\nname: nodesc\nlicense: MIT\n---\n"
            )
            entry = skillregistry.classify_zip(zip_path, "Finance")
        self.assertEqual(entry["description"], "")
        self.assertEqual(entry["triggers"], [])


class TestBuildEntries(unittest.TestCase):
    def test_deterministic_category_then_name_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # Created in reverse order; build_entries must sort by (category, name, zip).
            _make_zip(root / "Zeta", "beta.zip", _skill_md("beta"))
            _make_zip(root / "Alpha", "omega.zip", _skill_md("omega"))
            _make_zip(root / "Alpha", "alpha.zip", _skill_md("alpha"))
            entries, failures = skillregistry.build_entries(root)
        self.assertEqual(failures, [])
        self.assertEqual(
            [(e["category"], e["name"]) for e in entries],
            [("Alpha", "alpha"), ("Alpha", "omega"), ("Zeta", "beta")],
        )

    def test_zip_paths_can_be_presupplied(self):
        # A caller that already globbed passes the scan in — same result, one glob.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Alpha", "one.zip", _skill_md("one"))
            zip_paths = skillregistry.iter_zip_paths(root)
            entries, failures = skillregistry.build_entries(root, zip_paths)
        self.assertEqual(failures, [])
        self.assertEqual([e["name"] for e in entries], ["one"])

    def test_duplicate_names_are_all_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Alpha", "dup.zip", _skill_md("dup"))
            _make_zip(root / "Alpha", "dup (1).zip", _skill_md("dup"))
            entries, failures = skillregistry.build_entries(root)
        self.assertEqual(failures, [])
        self.assertEqual(len(entries), 2)
        self.assertEqual([e["zip"] for e in entries], ["dup (1).zip", "dup.zip"])

    def test_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Alpha", "one.zip", _skill_md("one"))
            _make_zip(root / "Beta", "two.zip", _skill_md("two"))
            first = json.dumps(skillregistry.build_registry(skillregistry.build_entries(root)[0]),
                               indent=2, ensure_ascii=False)
            second = json.dumps(skillregistry.build_registry(skillregistry.build_entries(root)[0]),
                                indent=2, ensure_ascii=False)
        self.assertEqual(first, second)

    def test_bad_zip_recorded_as_failure_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Alpha").mkdir()
            (root / "Alpha" / "broken.zip").write_text("nope", encoding="utf-8")
            _make_zip(root / "Alpha", "good.zip", _skill_md("good"))
            entries, failures = skillregistry.build_entries(root)
        self.assertEqual([e["name"] for e in entries], ["good"])
        self.assertEqual(len(failures), 1)
        self.assertIn("broken.zip", failures[0][0])


class TestRegistryValidation(unittest.TestCase):
    def test_valid_registry_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Alpha", "one.zip", _skill_md("one"))
            registry = skillregistry.build_registry(skillregistry.build_entries(root)[0])
        self.assertEqual(skillregistry.validate_registry(registry), [])

    # ---- failure: schema violations and count drift are caught ----
    def test_missing_field_detected(self):
        registry = {"version": 1, "skill_count": 0}  # no "skills"
        errors = skillregistry.validate_registry(registry)
        self.assertTrue(any("skills" in err for err in errors))

    def test_count_mismatch_detected(self):
        registry = skillregistry.build_registry([])
        registry["skill_count"] = 3
        self.assertTrue(skillregistry.validate_registry(registry))

    def test_bad_entry_detected(self):
        registry = skillregistry.build_registry([{"name": "x"}])  # not a full entry
        registry["skill_count"] = 1
        errors = skillregistry.validate_registry(registry)
        self.assertTrue(any("skills[0]" in err for err in errors))


class TestAudit(unittest.TestCase):
    def test_counts_and_ok_line(self):
        entries = [
            {"name": "a", "category": "Alpha"},
            {"name": "b", "category": "Alpha"},
            {"name": "c", "category": "Beta"},
        ]
        lines, ok = skillregistry.audit(entries, zip_count=3, failures=[])
        self.assertIn("AUDIT category=Alpha skills=2", lines)
        self.assertIn("AUDIT category=Beta skills=1", lines)
        self.assertEqual(lines[-2], "AUDIT zips=3 registry=3")
        self.assertEqual(lines[-1], "AUDIT ok")
        self.assertTrue(ok)

    # ---- E4 failure paths: count mismatch and parse failures ----
    def test_count_mismatch_flagged(self):
        lines, ok = skillregistry.audit([{"name": "a", "category": "Alpha"}], 2, [])
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)

    def test_parse_failure_flagged(self):
        lines, ok = skillregistry.audit([], 1, [("Skills/A/bad.zip", "not a readable zip")])
        self.assertIn("AUDIT parse-failure zip=Skills/A/bad.zip reason=not a readable zip", lines)
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)


class TestMain(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = skillregistry.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_happy_path_writes_registry_and_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_zip(root / "Skills" / "Alpha", "one.zip", _skill_md("one"))
            _make_zip(root / "Skills" / "Alpha", "two.zip", _skill_md("two"))
            out_path = root / "out" / "registry.json"
            rc, stdout, _ = self._run(
                ["--skills-root", str(root / "Skills"), "--out", str(out_path)]
            )
            registry = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(registry["skill_count"], 2)
        self.assertEqual(skillregistry.validate_registry(registry), [])
        self.assertIn("AUDIT zips=2 registry=2", stdout)
        self.assertIn("AUDIT ok", stdout)

    # ---- E4 failure: a corrupt zip fails the run with a non-zero exit ----
    def test_corrupt_zip_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Skills" / "Alpha").mkdir(parents=True)
            (root / "Skills" / "Alpha" / "broken.zip").write_text("nope", encoding="utf-8")
            _make_zip(root / "Skills" / "Alpha", "good.zip", _skill_md("good"))
            out_path = root / "registry.json"
            rc, stdout, _ = self._run(
                ["--skills-root", str(root / "Skills"), "--out", str(out_path)]
            )
            out_written = out_path.exists()
        self.assertEqual(rc, 1)
        self.assertIn("parse-failure", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        # A failed audit must never leave a partial registry behind.
        self.assertFalse(out_written)

    # ---- failure: a missing skills root is a hard error ----
    def test_missing_skills_root_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, stderr = self._run(
                ["--skills-root", str(pathlib.Path(tmp) / "absent"),
                 "--out", str(pathlib.Path(tmp) / "registry.json")]
            )
        self.assertEqual(rc, 1)
        self.assertIn("skills root not found", stderr)


class TestCommittedRegistry(unittest.TestCase):
    """E3 — the COMMITTED references/skill-registry.json satisfies the schemas."""

    @classmethod
    def setUpClass(cls):
        cls.registry_path = _REPO_ROOT / "references" / "skill-registry.json"
        cls.registry = json.loads(cls.registry_path.read_text(encoding="utf-8"))

    def test_committed_registry_validates_against_schemas(self):
        self.assertEqual(validate.validate(self.registry, "skill-registry"), [])
        for i, entry in enumerate(self.registry["skills"]):
            self.assertEqual(
                validate.validate(entry, "skill-entry"), [], f"skills[{i}] invalid"
            )

    def test_committed_registry_count_and_order(self):
        skills = self.registry["skills"]
        self.assertEqual(self.registry["skill_count"], len(skills))
        self.assertGreater(len(skills), 0)
        self.assertEqual(
            [(e["category"], e["name"], e["zip"]) for e in skills],
            sorted((e["category"], e["name"], e["zip"]) for e in skills),
        )
        self.assertEqual(skillregistry.validate_registry(self.registry), [])

    def test_committed_registry_exact_inventory(self):
        # Pin the real inventory so an under-count regeneration fails in CI.
        self.assertEqual(self.registry["skill_count"], 117)
        self.assertEqual(len(self.registry["skills"]), 117)
        expected = {
            "Academic": 8,
            "Creative": 15,
            "Engineering": 28,
            "Featured": 19,
            "Finance": 19,
            "Marketing": 11,
            "Productivity": 17,
        }
        self.assertEqual({e["category"] for e in self.registry["skills"]}, set(expected))
        counts: dict[str, int] = {}
        for entry in self.registry["skills"]:
            counts[entry["category"]] = counts.get(entry["category"], 0) + 1
        self.assertEqual(counts, expected)

    def test_committed_overrides_validates(self):
        overrides_path = _REPO_ROOT / "references" / "skill-overrides.json"
        overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
        self.assertEqual(validate.validate(overrides, "skill-overrides"), [])

    def test_registry_matches_live_zips_when_present(self):
        skills_root = _REPO_ROOT / "Skills"
        if not skills_root.is_dir():
            self.skipTest("Skills/ tree not present on disk (untracked; absent in CI)")
        live = sorted(
            (p.parent.name, p.name) for p in skillregistry.iter_zip_paths(skills_root)
        )
        registered = sorted((e["category"], e["zip"]) for e in self.registry["skills"])
        self.assertEqual(registered, live)


if __name__ == "__main__":
    unittest.main()
