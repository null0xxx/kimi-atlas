"""Unit tests for scripts/quality.py (enforce_critic_schema + lint_deliverable)."""
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


if __name__ == "__main__":
    unittest.main()
