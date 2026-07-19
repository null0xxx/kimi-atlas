"""Unit tests for scripts/skillregistry.py (skill-registry builder + E4 audit).

Fixtures are synthetic ``skills/<name>/`` package trees written with tempfile —
the tests never depend on the real skills/ tree. The one exception is the E3
test, which validates the COMMITTED references/skill-registry.json against the
canonical schemas and cross-checks it against the committed skills manifest
(zip-free — both are committed, so it runs anywhere the repo is checked out).
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

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


def _make_skill(skills_root: pathlib.Path, name: str, skill_md=None, extra=None):
    """Write a synthetic extracted package: ``skills/<name>/SKILL.md`` + extras."""
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        _skill_md(name) if skill_md is None else skill_md, encoding="utf-8"
    )
    for member, content in (extra or {}).items():
        target = skill_dir / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return skill_dir


def _manifest_for(mapping: dict[str, str]) -> dict:
    """Build a synthetic skills manifest document for a name→category mapping."""
    return {
        "version": 2,
        "skill_count": len(mapping),
        "file_count": 0,
        "skills": [
            {"name": name, "category": category, "dir": f"skills/{name}", "files": []}
            for name, category in sorted(mapping.items())
        ],
    }


def _write_manifest(root: pathlib.Path, mapping: dict[str, str]) -> pathlib.Path:
    path = root / "refs" / "skills-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_manifest_for(mapping)), encoding="utf-8")
    return path


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


class TestClassifyDir(unittest.TestCase):
    def test_full_entry_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill(
                pathlib.Path(tmp) / "skills",
                "demo-skill",
                _skill_md("demo-skill", "Does demos. Trigger when users mention demos."),
                extra={"scripts/run.sh": "#/bin/sh\n"},
            )
            entry = skillregistry.classify_dir(skill_dir, "Engineering")
        self.assertEqual(entry["name"], "demo-skill")
        self.assertEqual(entry["category"], "Engineering")
        self.assertEqual(entry["triggers"], ["demos"])
        self.assertEqual(entry["path"], "skills/demo-skill/")
        # The registry stays compact: payload member lists are not carried.
        self.assertNotIn("entries", entry)
        self.assertNotIn("has_payload", entry)
        self.assertNotIn("zip", entry)  # the tree build retired the archive field

    # ---- failure paths: missing manifest file / no frontmatter ----
    def test_missing_skill_md_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = pathlib.Path(tmp) / "skills" / "empty"
            skill_dir.mkdir(parents=True)
            with self.assertRaises(ValueError):
                skillregistry.classify_dir(skill_dir, "Finance")

    def test_no_frontmatter_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill(
                pathlib.Path(tmp) / "skills", "bare", "# just a body\n"
            )
            with self.assertRaises(ValueError):
                skillregistry.classify_dir(skill_dir, "Finance")

    # ---- boundary: a missing description is tolerated (entry still classifies) ----
    def test_missing_description_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill(
                pathlib.Path(tmp) / "skills",
                "nodesc",
                "---\nname: nodesc\nlicense: MIT\n---\n",
            )
            entry = skillregistry.classify_dir(skill_dir, "Finance")
        self.assertEqual(entry["description"], "")
        self.assertEqual(entry["triggers"], [])

    def test_empty_name_falls_back_to_dir_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill(
                pathlib.Path(tmp) / "skills", "dir-name", "---\nname: \n---\n"
            )
            entry = skillregistry.classify_dir(skill_dir, "Finance")
        self.assertEqual(entry["name"], "dir-name")


class TestIterSkillDirs(unittest.TestCase):
    def test_first_party_dirs_excluded(self):
        # atlas / atlas-weave / atlas-resume are plugin machinery, never vendored
        # packages — they must be skipped BEFORE the manifest-membership check.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            for first_party in ("atlas", "atlas-weave", "atlas-resume"):
                _make_skill(root, first_party, "---\nname: x\ndescription: y\n---\n")
            _make_skill(root, "vendored")
            dirs = skillregistry.iter_skill_dirs(root)
        self.assertEqual([d.name for d in dirs], ["vendored"])

    def test_dirs_without_skill_md_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            (root / "not-a-package").mkdir(parents=True)
            _make_skill(root, "packaged")
            dirs = skillregistry.iter_skill_dirs(root)
        self.assertEqual([d.name for d in dirs], ["packaged"])


class TestBuildEntries(unittest.TestCase):
    def test_deterministic_category_then_name_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            # Created in reverse order; build_entries must sort by (category, name).
            _make_skill(root, "beta", _skill_md("beta"))
            _make_skill(root, "omega", _skill_md("omega"))
            _make_skill(root, "alpha", _skill_md("alpha"))
            entries, failures = skillregistry.build_entries(
                root, manifest=_manifest_for(
                    {"beta": "Zeta", "omega": "Alpha", "alpha": "Alpha"}
                )
            )
        self.assertEqual(failures, [])
        self.assertEqual(
            [(e["category"], e["name"], e["path"]) for e in entries],
            [
                ("Alpha", "alpha", "skills/alpha/"),
                ("Alpha", "omega", "skills/omega/"),
                ("Zeta", "beta", "skills/beta/"),
            ],
        )

    def test_category_comes_from_manifest_not_disk(self):
        # The manifest is the anchor: a dir's category is whatever the manifest
        # records, independent of where the fixture happens to live.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            _make_skill(root, "demo", _skill_md("demo"))
            entries, failures = skillregistry.build_entries(
                root, manifest=_manifest_for({"demo": "Finance"})
            )
        self.assertEqual(failures, [])
        self.assertEqual(entries[0]["category"], "Finance")

    def test_skill_dirs_can_be_presupplied(self):
        # A caller that already listed the tree passes the scan in — same result.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            _make_skill(root, "one", _skill_md("one"))
            manifest = _manifest_for({"one": "Alpha"})
            skill_dirs = skillregistry.iter_skill_dirs(root)
            entries, failures = skillregistry.build_entries(root, skill_dirs, manifest)
        self.assertEqual(failures, [])
        self.assertEqual([e["name"] for e in entries], ["one"])

    def test_dir_missing_from_manifest_is_failure(self):
        # A skill dir the manifest does not anchor is an audit FAILURE, never
        # silently categorized.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            _make_skill(root, "anchored", _skill_md("anchored"))
            _make_skill(root, "stowaway", _skill_md("stowaway"))
            entries, failures = skillregistry.build_entries(
                root, manifest=_manifest_for({"anchored": "Alpha"})
            )
        self.assertEqual([e["name"] for e in entries], ["anchored"])
        self.assertEqual(len(failures), 1)
        self.assertIn("stowaway", failures[0][0])
        self.assertIn("missing from the skills manifest", failures[0][1])

    def test_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            _make_skill(root, "one", _skill_md("one"))
            _make_skill(root, "two", _skill_md("two"))
            manifest = _manifest_for({"one": "Alpha", "two": "Beta"})
            first = json.dumps(
                skillregistry.build_registry(skillregistry.build_entries(root, manifest=manifest)[0]),
                indent=2, ensure_ascii=False,
            )
            second = json.dumps(
                skillregistry.build_registry(skillregistry.build_entries(root, manifest=manifest)[0]),
                indent=2, ensure_ascii=False,
            )
        self.assertEqual(first, second)

    def test_bad_skill_md_recorded_as_failure_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            _make_skill(root, "broken", "# no frontmatter fence\n")
            _make_skill(root, "good", _skill_md("good"))
            entries, failures = skillregistry.build_entries(
                root, manifest=_manifest_for({"broken": "Alpha", "good": "Alpha"})
            )
        self.assertEqual([e["name"] for e in entries], ["good"])
        self.assertEqual(len(failures), 1)
        self.assertIn("broken", failures[0][0])


class TestRegistryValidation(unittest.TestCase):
    def test_valid_registry_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "skills"
            _make_skill(root, "one", _skill_md("one"))
            registry = skillregistry.build_registry(
                skillregistry.build_entries(root, manifest=_manifest_for({"one": "Alpha"}))[0]
            )
        self.assertEqual(registry["version"], 2)
        self.assertEqual(skillregistry.validate_registry(registry), [])

    # ---- failure: schema violations and count drift are caught ----
    def test_missing_field_detected(self):
        registry = {"version": 2, "skill_count": 0}  # no "skills"
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

    def test_zip_keyed_entry_detected(self):
        # The v1 archive-keyed shape no longer satisfies the schema (path now).
        old = {"name": "x", "category": "A", "description": "", "triggers": [],
               "zip": "x.zip"}
        errors = skillregistry.validate_registry(skillregistry.build_registry([old]))
        self.assertTrue(any("path" in err for err in errors))


class TestAudit(unittest.TestCase):
    def test_counts_and_ok_line(self):
        entries = [
            {"name": "a", "category": "Alpha"},
            {"name": "b", "category": "Alpha"},
            {"name": "c", "category": "Beta"},
        ]
        lines, ok = skillregistry.audit(entries, manifest_skill_count=3, failures=[])
        self.assertIn("AUDIT category=Alpha skills=2", lines)
        self.assertIn("AUDIT category=Beta skills=1", lines)
        self.assertEqual(lines[-2], "AUDIT manifest=3 registry=3")
        self.assertEqual(lines[-1], "AUDIT ok")
        self.assertTrue(ok)

    # ---- E4 failure paths: count mismatch and parse failures ----
    def test_count_mismatch_flagged(self):
        lines, ok = skillregistry.audit([{"name": "a", "category": "Alpha"}], 2, [])
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)

    def test_failure_flagged(self):
        lines, ok = skillregistry.audit([], 1, [("skills/bad", "no frontmatter fence")])
        self.assertIn("AUDIT failure dir=skills/bad reason=no frontmatter fence", lines)
        self.assertEqual(lines[-1], "AUDIT MISMATCH")
        self.assertFalse(ok)


class TestMain(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = skillregistry.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def _args(self, root, mapping, out_name="registry.json"):
        return [
            "--skills-root", str(root / "skills"),
            "--manifest", str(_write_manifest(root, mapping)),
            "--out", str(root / "out" / out_name),
        ]

    def test_happy_path_writes_registry_and_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_skill(root / "skills", "one", _skill_md("one"))
            _make_skill(root / "skills", "two", _skill_md("two"))
            out_path = root / "out" / "registry.json"
            rc, stdout, _ = self._run(self._args(root, {"one": "Alpha", "two": "Alpha"}))
            registry = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(registry["version"], 2)
        self.assertEqual(registry["skill_count"], 2)
        self.assertEqual([e["path"] for e in registry["skills"]],
                         ["skills/one/", "skills/two/"])
        self.assertEqual(skillregistry.validate_registry(registry), [])
        self.assertIn("AUDIT manifest=2 registry=2", stdout)
        self.assertIn("AUDIT ok", stdout)

    # ---- E4 failure: a stowaway dir fails the run with a non-zero exit ----
    def test_stowaway_dir_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_skill(root / "skills", "good", _skill_md("good"))
            _make_skill(root / "skills", "stowaway", _skill_md("stowaway"))
            out_path = root / "out" / "registry.json"
            rc, stdout, _ = self._run(self._args(root, {"good": "Alpha"}))
            out_written = out_path.exists()
        self.assertEqual(rc, 1)
        self.assertIn("missing from the skills manifest", stdout)
        self.assertIn("AUDIT MISMATCH", stdout)
        # A failed audit must never leave a partial registry behind.
        self.assertFalse(out_written)

    def test_count_mismatch_exits_nonzero(self):
        # Manifest records two packages; disk holds one — the counts disagree.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_skill(root / "skills", "one", _skill_md("one"))
            out_path = root / "out" / "registry.json"
            rc, stdout, _ = self._run(
                self._args(root, {"one": "Alpha", "ghost": "Alpha"})
            )
            out_written = out_path.exists()
        self.assertEqual(rc, 1)
        self.assertIn("AUDIT manifest=2 registry=1", stdout)
        self.assertFalse(out_written)

    # ---- failure: missing skills root / manifest are hard errors ----
    def test_missing_skills_root_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            rc, _, stderr = self._run(self._args(root, {"one": "Alpha"}))
        self.assertEqual(rc, 1)
        self.assertIn("skills root not found", stderr)

    def test_missing_manifest_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_skill(root / "skills", "one", _skill_md("one"))
            rc, _, stderr = self._run([
                "--skills-root", str(root / "skills"),
                "--manifest", str(root / "absent.json"),
                "--out", str(root / "registry.json"),
            ])
        self.assertEqual(rc, 1)
        self.assertIn("cannot load skills manifest", stderr)


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
        self.assertEqual(self.registry["version"], 2)
        self.assertEqual(self.registry["skill_count"], len(skills))
        self.assertGreater(len(skills), 0)
        self.assertEqual(
            [(e["category"], e["name"]) for e in skills],
            sorted((e["category"], e["name"]) for e in skills),
        )
        self.assertEqual(skillregistry.validate_registry(self.registry), [])

    def test_committed_registry_exact_inventory(self):
        # Pin the real inventory so an under-count regeneration fails in CI.
        self.assertEqual(self.registry["skill_count"], 115)
        self.assertEqual(len(self.registry["skills"]), 115)
        expected = {
            "Academic": 8,
            "Creative": 15,
            "Engineering": 28,
            "Featured": 18,
            "Finance": 19,
            "Marketing": 11,
            "Productivity": 16,
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

    def test_registry_matches_committed_manifest(self):
        # Zip-free cross-check (runs in GitHub CI): every manifest package is
        # registered exactly once, with the manifest's category, and its path
        # points at a real on-disk package dir holding a SKILL.md.
        manifest = json.loads(
            (_REPO_ROOT / "references" / "skills-manifest.json").read_text(encoding="utf-8")
        )
        by_name = {e["name"]: e for e in manifest["skills"]}
        self.assertEqual(len(by_name), len(self.registry["skills"]))
        for entry in self.registry["skills"]:
            anchored = by_name.get(entry["name"])
            self.assertIsNotNone(anchored, f"{entry['name']} missing from the manifest")
            self.assertEqual(entry["category"], anchored["category"])
            self.assertEqual(entry["path"], anchored["dir"] + "/")
            self.assertTrue(
                (_REPO_ROOT / entry["path"] / "SKILL.md").is_file(),
                f"{entry['path']} has no SKILL.md on disk",
            )


if __name__ == "__main__":
    unittest.main()
