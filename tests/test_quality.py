"""Unit tests for scripts/quality.py (enforce_critic_schema + lint_deliverable)."""
import json
import unittest

from scripts import quality


def _well_formed_critic(verdict="OK", defects=None):
    dims = {d: "no" for d in quality._DIMENSIONS}
    return {"dimensions": dims, "defects": defects or [], "verdict": verdict}


def _defect(category="CORRECTNESS", severity="HIGH"):
    return {
        "id": "D1",
        "category": category,
        "severity": severity,
        "location": "foo.py:1",
        "fix": "fix it",
    }


class TestEnforceCriticSchema(unittest.TestCase):
    # ---- happy ----
    def test_well_formed_ok(self):
        self.assertEqual(quality.enforce_critic_schema(_well_formed_critic()), [])

    def test_well_formed_fail_with_blocking_defect(self):
        critic = _well_formed_critic(verdict="FAIL", defects=[_defect(severity="CRITICAL")])
        self.assertEqual(quality.enforce_critic_schema(critic), [])

    def test_medium_defect_stays_ok(self):
        # A MEDIUM defect is non-blocking, so verdict must stay OK.
        critic = _well_formed_critic(verdict="OK", defects=[_defect(severity="MEDIUM")])
        self.assertEqual(quality.enforce_critic_schema(critic), [])

    # ---- failure: schema violations the task mandates ----
    def test_object_valued_dimensions(self):
        critic = _well_formed_critic()
        critic["dimensions"]["CORRECTNESS"] = {"verdict": True}  # object, not yes/no
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("CORRECTNESS" in e and "yes" in e for e in errs))

    def test_inconsistent_verdict(self):
        # OK verdict but a HIGH defect present → inconsistent.
        critic = _well_formed_critic(verdict="OK", defects=[_defect(severity="HIGH")])
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("inconsistent" in e for e in errs))

    def test_stray_top_level_key(self):
        critic = _well_formed_critic()
        critic["extra"] = 1
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("unexpected top-level keys" in e for e in errs))

    def test_missing_dimension(self):
        critic = _well_formed_critic()
        del critic["dimensions"]["SECURITY"]
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("missing dimension 'SECURITY'" in e for e in errs))

    def test_unknown_dimension_key_rejected(self):
        # A dissent filed under a made-up dimension key must not merge clean.
        critic = _well_formed_critic()
        critic["dimensions"]["EXTRA"] = "no"
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("unknown dimension keys" in e for e in errs), errs)

    def test_non_dict_critic_is_a_violation_not_a_crash(self):
        # S4: a valid-JSON non-object critic reaches the documented
        # CRITIC_SCHEMA_ERRORS path — the validator never raises.
        for bad in ([{"dimensions": {}}], 42, None, "oops"):
            with self.subTest(bad=bad):
                errs = quality.enforce_critic_schema(bad)
                self.assertEqual(len(errs), 1)
                self.assertIn("must be a JSON object", errs[0])

    def test_bad_severity_and_category(self):
        bad = {"id": "D", "category": "NONSENSE", "severity": "SEV0",
               "location": "x", "fix": "y"}
        critic = _well_formed_critic(verdict="OK", defects=[bad])
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("severity" in e for e in errs))
        self.assertTrue(any("category" in e for e in errs))

    def test_defects_not_a_list(self):
        critic = _well_formed_critic()
        critic["defects"] = "nope"
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("defects: must be a list" in e for e in errs))

    def test_bad_verdict_value(self):
        critic = _well_formed_critic(verdict="MAYBE")
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("verdict: must be 'OK' or 'FAIL'" in e for e in errs))

    # ---- boundary ----
    def test_empty_dict(self):
        errs = quality.enforce_critic_schema({})
        # dimensions missing (object error), defects missing (list error), verdict bad.
        self.assertTrue(any("dimensions" in e for e in errs))
        self.assertTrue(any("defects" in e for e in errs))
        self.assertTrue(any("verdict" in e for e in errs))

    def test_defect_missing_keys(self):
        critic = _well_formed_critic(verdict="OK", defects=[{"id": "D"}])
        errs = quality.enforce_critic_schema(critic)
        self.assertTrue(any("missing keys" in e for e in errs))


class TestLintDeliverable(unittest.TestCase):
    CONFIG = {"debug_tokens": ["TODO", "FIXME", "XXX", "console.log"],
              "test_glob": "tests/test_*.py"}

    # ---- happy ----
    def test_clean_change_with_tests(self):
        changed = {"src/a.py": "def add(a, b):\n    return a + b\n"}
        tests = {"tests/test_a.py": "assert add(1, 2) == 3\n"}
        self.assertEqual(quality.lint_deliverable(changed, tests, self.CONFIG), [])

    # ---- failure ----
    def test_debug_token_flagged(self):
        changed = {"src/a.py": "def add(a, b):\n    # TODO: handle overflow\n    return a + b\n"}
        tests = {"tests/test_a.py": "assert True\n"}
        defects = quality.lint_deliverable(changed, tests, self.CONFIG)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CODE-QUALITY")
        self.assertEqual(d["location"], "src/a.py:2")

    def test_missing_tests_flagged(self):
        changed = {"src/a.py": "def add(a, b):\n    return a + b\n"}
        defects = quality.lint_deliverable(changed, {}, self.CONFIG)
        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0]["category"], "TEST-ADEQUACY")

    def test_config_driven_tokens_only(self):
        # A token NOT in config is not flagged; language-agnostic (no hard-coding).
        changed = {"src/a.js": "console.log('hi');\nprint('py');\n"}
        cfg = {"debug_tokens": ["console.log"], "test_glob": "*.test.js"}
        defects = quality.lint_deliverable(changed, {"x.test.js": "expect(1)"}, cfg)
        # Only console.log flagged; the un-configured 'print' is ignored.
        self.assertEqual(len(defects), 1)
        self.assertIn("console.log", defects[0]["fix"])

    def test_never_emits_high(self):
        changed = {"src/a.py": "# TODO x\n# FIXME y\n"}
        defects = quality.lint_deliverable(changed, {}, self.CONFIG)
        self.assertTrue(defects)
        for d in defects:
            self.assertEqual(d["severity"], "MEDIUM")

    # ---- boundary ----
    def test_empty_inputs(self):
        self.assertEqual(quality.lint_deliverable({}, {}, self.CONFIG), [])

    def test_no_debug_tokens_in_config(self):
        changed = {"src/a.py": "# TODO nothing configured\n"}
        cfg = {"test_glob": "t"}  # no debug_tokens key at all
        defects = quality.lint_deliverable(changed, {"t": "assert"}, cfg)
        self.assertEqual(defects, [])

    def test_test_files_not_scanned_for_tokens(self):
        # A debug token living only in a test file is not flagged (avoids
        # false-positive on legitimate test prints/markers).
        changed = {"src/a.py": "return 1\n"}
        tests = {"tests/test_a.py": "print('debugging')\n# TODO clean up\n"}
        cfg = {"debug_tokens": ["print(", "TODO"], "test_glob": "t"}
        self.assertEqual(quality.lint_deliverable(changed, tests, cfg), [])

    def test_deterministic_ordering(self):
        changed = {"z.py": "TODO\n", "a.py": "TODO\n"}
        defects = quality.lint_deliverable(changed, {"t": "x"}, self.CONFIG)
        locations = [d["location"] for d in defects]
        # sorted by path: a.py before z.py.
        self.assertEqual(locations[:2], ["a.py:1", "z.py:1"])


class TestRoleFileExamplesValidate(unittest.TestCase):
    """C1 (Task-3 review): the critic role files must model the shape the
    Step-3.4 raw validation accepts — a role-file example the validator rejects
    manufactures a RED on every honest run whose critic imitates it. Pin every
    ```json example in the four role files against the REAL schema."""

    def test_every_role_file_json_example_is_schema_clean(self):
        import pathlib
        agents = pathlib.Path(__file__).resolve().parents[1] / "agents"
        seen = 0
        for name in ("correctness-critic.md", "code-quality-critic.md",
                     "security-critic.md", "integration-critic.md"):
            text = (agents / name).read_text(encoding="utf-8")
            for block in text.split("```json")[1:]:
                raw = block.split("```", 1)[0]
                with self.subTest(role=name, example=seen):
                    obj = json.loads(raw)
                    self.assertEqual(quality.enforce_critic_schema(obj), [],
                                     "%s models a shape Step 3.4 rejects" % name)
                seen += 1
        self.assertGreaterEqual(seen, 4, "each role file must carry an example")


class TestReservedDefectIds(unittest.TestCase):
    """H4 (v1.5.2.1): a RAW critic may not claim an id the orchestrator synthesizes.

    Those ids are fenced OUT of the coder re-dispatch, so a critic wearing one
    deletes its own CRITICAL from the refine loop. The seam is a KEYWORD-ONLY
    parameter defaulting to the empty set, because the MERGED object legitimately
    carries floor ids and every pre-existing call site validates the merged shape.
    """

    def _critic(self, defect_id):
        return _well_formed_critic(
            verdict="FAIL", defects=[dict(_defect(), id=defect_id)])

    def test_reserved_ids_is_keyword_only_with_an_empty_default(self):
        """The seam's whole safety argument is 'every existing call site is
        untouched'. Positional would silently re-bind ``critic``'s neighbours;
        a non-empty default would reserve ids for the MERGED object too, which
        legitimately carries them — that is the manufactured-RED direction."""
        import inspect
        sig = inspect.signature(quality.enforce_critic_schema)
        p = sig.parameters["reserved_ids"]
        self.assertIs(p.kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(p.default, frozenset())
        self.assertEqual(len(sig.parameters), 2, "no third parameter was added")

    def test_a_reserved_id_is_a_schema_error_naming_the_id(self):
        errs = quality.enforce_critic_schema(
            self._critic("stale-verdict"), reserved_ids=frozenset({"stale-verdict"}))
        self.assertTrue(errs)
        self.assertTrue(any("stale-verdict" in e for e in errs), errs)
        self.assertTrue(any(e.startswith("defects[0].id:") for e in errs), errs)

    def test_only_the_named_ids_are_rejected(self):
        """The honest direction: reserving one id must not reject its neighbours."""
        for honest in ("C1", "Q7", "S12", "runcheck", "docs-naming", "empty-diff",
                       "out-of-scope:\"lib/x.py\"", "stale-verdicts", "tale-verdict"):
            with self.subTest(id=honest):
                self.assertEqual(
                    quality.enforce_critic_schema(
                        self._critic(honest), reserved_ids=frozenset({"stale-verdict"})),
                    [], "reserving one id manufactured a RED on %r" % honest)

    def test_the_default_call_accepts_a_reserved_id(self):
        """``floorsynth.merge_and_validate`` and ``run_negative_gate`` validate the
        MERGED object, which really does carry floor ids — the default must not
        break them."""
        self.assertEqual(quality.enforce_critic_schema(self._critic("stale-verdict")), [])

    def test_reservation_never_raises_on_a_non_string_id(self):
        """S4 never-raise: an unhashable ``id`` must not blow up the membership
        test — a valid-JSON garbage critic has to reach CRITIC_SCHEMA_ERRORS, not
        crash the validate block with a bare TypeError."""
        for bad in ([], {}, {"a": 1}, 7, None, set()):
            with self.subTest(id=repr(bad)):
                errs = quality.enforce_critic_schema(
                    self._critic(bad), reserved_ids=frozenset({"stale-verdict"}))
                self.assertIsInstance(errs, list)

    def test_the_reserved_check_survives_a_malformed_defect_list(self):
        """A non-dict entry must be skipped, not indexed into."""
        critic = _well_formed_critic(verdict="FAIL", defects=["nope", _defect()])
        errs = quality.enforce_critic_schema(
            critic, reserved_ids=frozenset({"stale-verdict"}))
        self.assertTrue(any("defects[0]" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
