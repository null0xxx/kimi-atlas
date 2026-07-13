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
        self.assertEqual(len(errs), 7)


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
