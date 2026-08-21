"""Unit tests for scripts/validate.py against references/schemas.json."""
import unittest

from scripts import validate


def _task_packet(**over):
    base = {
        "intent": "add a helper",
        "success_criteria": ["tests pass"],
        "scope_paths": ["src/"],
        "verify_cmd": "python3 -m unittest",
        "baseline_sha": "abc123",
        "debug_tokens": ["TODO"],
        "test_glob": "tests/test_*.py",
        "invocation_form": "headless",
    }
    base.update(over)
    return base


def _context(**over):
    base = {
        "run_id": "run-1",
        "intent": "add a helper",
        "success_criteria": ["tests pass"],
        "stages": {},
        "refine_passes": 0,
        "draft_ref": "",
        "verify_cmd": "python3 -m unittest",
        "scope_paths": ["src/"],
        "baseline_sha": "abc123",
    }
    base.update(over)
    return base


def _critic(**over):
    base = {"dimensions": {}, "defects": [], "verdict": "OK"}
    base.update(over)
    return base


class TestValidateTaskPacket(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate.validate(_task_packet(), "task-packet"), [])

    def test_missing_field(self):
        pkt = _task_packet()
        del pkt["verify_cmd"]
        errs = validate.validate(pkt, "task-packet")
        self.assertIn("missing field: verify_cmd", errs)

    def test_wrong_type(self):
        errs = validate.validate(_task_packet(success_criteria="not a list"), "task-packet")
        self.assertIn("field success_criteria must be list", errs)

    def test_empty_object_reports_all_missing(self):
        errs = validate.validate({}, "task-packet")
        self.assertEqual(len(errs), 8)

    def test_invocation_form_accepts_interactive(self):
        self.assertEqual(
            validate.validate(_task_packet(invocation_form="interactive"), "task-packet"), []
        )

    def test_invocation_form_accepts_headless(self):
        self.assertEqual(
            validate.validate(_task_packet(invocation_form="headless"), "task-packet"), []
        )

    def test_invocation_form_rejects_unknown_value(self):
        errs = validate.validate(_task_packet(invocation_form="banana"), "task-packet")
        self.assertIn("field invocation_form must be one of ['interactive', 'headless']", errs)

    def test_invocation_form_missing_is_reported(self):
        pkt = _task_packet()
        del pkt["invocation_form"]
        errs = validate.validate(pkt, "task-packet")
        self.assertIn("missing field: invocation_form", errs)

    def test_invocation_form_wrong_type_reported_once_not_double_reported(self):
        # A non-str invocation_form fails the type check (required-field loop);
        # the values-membership loop must not ALSO fire a redundant error for it.
        errs = validate.validate(_task_packet(invocation_form=["headless"]), "task-packet")
        self.assertIn("field invocation_form must be str", errs)
        self.assertNotIn(
            "field invocation_form must be one of ['interactive', 'headless']", errs
        )
        self.assertEqual(len(errs), 1)


class TestValidateContext(unittest.TestCase):
    def test_valid_without_optional(self):
        # Init-time state (pre-CLARIFY) omits clarify_resolution and must validate.
        self.assertEqual(validate.validate(_context(), "context"), [])

    def test_valid_with_optional(self):
        ctx = _context(clarify_resolution="user chose verify_cmd=make test")
        self.assertEqual(validate.validate(ctx, "context"), [])

    def test_optional_wrong_type(self):
        ctx = _context(clarify_resolution=["not", "a", "string"])
        errs = validate.validate(ctx, "context")
        self.assertIn("optional field clarify_resolution must be str", errs)

    def test_missing_required(self):
        ctx = _context()
        del ctx["stages"]
        errs = validate.validate(ctx, "context")
        self.assertIn("missing field: stages", errs)

    def test_refine_passes_wrong_type(self):
        errs = validate.validate(_context(refine_passes="0"), "context")
        self.assertIn("field refine_passes must be int", errs)


class TestValidateCritic(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate.validate(_critic(), "critic"), [])

    def test_missing_verdict(self):
        c = _critic()
        del c["verdict"]
        errs = validate.validate(c, "critic")
        self.assertIn("missing field: verdict", errs)

    def test_wrong_type(self):
        errs = validate.validate(_critic(dimensions=[]), "critic")
        self.assertIn("field dimensions must be dict", errs)


class TestValidateBoundary(unittest.TestCase):
    def test_unknown_schema_raises(self):
        with self.assertRaises(KeyError):
            validate.validate({}, "does-not-exist")


if __name__ == "__main__":
    unittest.main()
