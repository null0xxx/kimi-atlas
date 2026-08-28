"""Unit tests for scripts/validate.py against references/schemas.json."""
import unittest

from scripts import validate

# A real 40-hex sha. The fixtures used to carry ``"abc123"``, which the
# ``baseline_sha`` format (SEC-2 / plan VIP-A2) now refuses: six hex characters
# are not a sha, and the field is handed to git in a revision slot.
_SHA = "02144f07f76e440a03037265a9040544468b63c8"


def _task_packet(**over):
    base = {
        "intent": "add a helper",
        "success_criteria": ["tests pass"],
        "scope_paths": ["src/"],
        "verify_cmd": "python3 -m unittest",
        "baseline_sha": _SHA,
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
        "baseline_sha": _SHA,
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


class TestBaselineShaFormat(unittest.TestCase):
    """The ``formats`` block on ``baseline_sha`` (SEC-2 / plan VIP-A2).

    ``baseline_sha`` was constrained to ``"str"`` while being handed to git in a
    revision slot, where a leading ``-`` makes it an OPTION. The schema now
    states the shape and this module enforces it — at the contract, on top of
    ``scripts/difftool.py``'s refusal at the sink, because one layer defending
    itself is exactly what let the hole live.

    Restoring ``"baseline_sha": "str"`` in ``references/schemas.json``, deleting
    the ``formats`` loop in ``validate.validate``, or relaxing its
    ``re.fullmatch`` to ``re.match`` each turns this class red — the last one
    because an all-optional pattern matches the empty prefix of ANY string, so
    ``--output=/tmp/pwned`` would validate.
    """

    _ERR = "field baseline_sha must match ([0-9a-fA-F]{7,40})?"

    def test_accepts_a_full_sha(self):
        self.assertEqual(validate.validate(_task_packet(baseline_sha=_SHA), "task-packet"), [])

    def test_accepts_the_short_and_long_boundaries(self):
        for sha in ("0" * 7, "a" * 40, "AbCdEf0"):
            with self.subTest(sha=sha):
                self.assertEqual(
                    validate.validate(_task_packet(baseline_sha=sha), "task-packet"), []
                )

    def test_accepts_the_empty_baseline(self):
        # "No baseline recorded" is honest and supported (a non-git target, and
        # scripts/run_negative_gate.py's own capture). A schema that rejected it
        # would turn an honest lane red at CLARIFY — worse than the bug.
        self.assertEqual(validate.validate(_task_packet(baseline_sha=""), "task-packet"), [])
        self.assertEqual(validate.validate(_context(baseline_sha=""), "context"), [])

    def test_rejects_the_option_injection_payloads(self):
        for payload in ("--output=/tmp/pwned", "--upload-pack=/tmp/pwned", "-deadbeef"):
            with self.subTest(payload=payload):
                self.assertIn(
                    self._ERR,
                    validate.validate(_task_packet(baseline_sha=payload), "task-packet"),
                )

    def test_rejects_refs_and_revision_expressions(self):
        # No live caller records one (measured), and each is a string git would
        # RESOLVE rather than a baseline anyone recorded.
        for value in ("HEAD", "HEAD~1", "HEAD^", "origin/main", "@{-1}", "deadbeef..cafebabe"):
            with self.subTest(value=value):
                self.assertIn(
                    self._ERR,
                    validate.validate(_task_packet(baseline_sha=value), "task-packet"),
                )

    def test_rejects_out_of_range_and_ragged_shas(self):
        for value in ("abc123", "0" * 6, "f" * 41, "deadbeeg", " deadbeef", "deadbeef\n"):
            with self.subTest(value=value):
                self.assertIn(
                    self._ERR,
                    validate.validate(_task_packet(baseline_sha=value), "task-packet"),
                )

    def test_context_schema_carries_the_same_format(self):
        self.assertIn(self._ERR, validate.validate(_context(baseline_sha="HEAD~1"), "context"))

    def test_wrong_type_reported_once_not_double_reported(self):
        errs = validate.validate(_task_packet(baseline_sha=["deadbeef"]), "task-packet")
        self.assertEqual(errs, ["field baseline_sha must be str"])

    def test_missing_field_reports_only_the_absence(self):
        pkt = _task_packet()
        del pkt["baseline_sha"]
        self.assertEqual(validate.validate(pkt, "task-packet"), ["missing field: baseline_sha"])

    def test_a_schema_without_a_formats_block_is_unaffected(self):
        self.assertEqual(validate.validate(_critic(), "critic"), [])


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
