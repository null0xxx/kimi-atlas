"""The rubric vocabulary lives in exactly one module and every pure core imports
it (F6)."""
import unittest

from scripts import quality, rubric, run_negative_gate, verdict


class TestRubricSingleSource(unittest.TestCase):
    def test_dimensions_canonical(self):
        self.assertEqual(
            rubric.DIMENSIONS,
            ("CORRECTNESS", "CODE-QUALITY", "SECURITY",
             "TEST-ADEQUACY", "DOES-IT-RUN", "REQUIREMENTS-COVERAGE"),
        )

    def test_all_cores_share_one_dimensions_object(self):
        self.assertIs(verdict._DIMENSIONS, rubric.DIMENSIONS)
        self.assertIs(quality._DIMENSIONS, rubric.DIMENSIONS)

    def test_all_cores_share_one_blocking_set(self):
        self.assertIs(verdict._BLOCKING, rubric.BLOCKING)
        self.assertIs(quality._BLOCKING, rubric.BLOCKING)
        self.assertIs(run_negative_gate._BLOCKING, rubric.BLOCKING)

    def test_schema_key_sets_shared(self):
        self.assertIs(quality._SEVERITIES, rubric.SEVERITIES)
        self.assertIs(quality._CRITIC_TOP_KEYS, rubric.CRITIC_TOP_KEYS)
        self.assertIs(quality._DEFECT_KEYS, rubric.DEFECT_KEYS)


import pathlib

RUBRIC = pathlib.Path(__file__).resolve().parents[1] / "references" / "rubric.md"


class TestLensSection(unittest.TestCase):
    def setUp(self):
        self.md = RUBRIC.read_text(encoding="utf-8")
        self.slices = {d: rubric.lens_section(self.md, d) for d in rubric.DIMENSIONS}

    def test_every_dimension_yields_a_non_empty_slice(self):
        for d, s in self.slices.items():
            with self.subTest(dimension=d):
                self.assertTrue(s.strip(), "empty slice for %s" % d)

    def test_slice_starts_with_its_own_heading(self):
        for d, s in self.slices.items():
            with self.subTest(dimension=d):
                self.assertRegex(s, r"\A## Lens \d+ — %s" % d)

    def test_slice_contains_no_other_lens_heading(self):
        for d, s in self.slices.items():
            for other in rubric.DIMENSIONS:
                if other == d:
                    continue
                with self.subTest(dimension=d, other=other):
                    self.assertNotIn("— %s" % other, s.split("\n", 1)[1])

    def test_slice_carries_no_gate_knowledge(self):
        """The :17-33 preamble states 'Only CRITICAL and HIGH are blocking … never flip
        final_status'. That is gate knowledge; a single-lens critic must not receive it."""
        for d, s in self.slices.items():
            for banned in ("verdict.gate", "_BLOCKING", "never flip", "final_status",
                           "The PASS bar"):
                with self.subTest(dimension=d, banned=banned):
                    self.assertNotIn(banned, s)

    def test_slices_are_pairwise_disjoint(self):
        spans = {d: (self.md.index(s), self.md.index(s) + len(s))
                 for d, s in self.slices.items()}
        for a in rubric.DIMENSIONS:
            for b in rubric.DIMENSIONS:
                if a >= b:
                    continue
                with self.subTest(a=a, b=b):
                    (a0, a1), (b0, b1) = spans[a], spans[b]
                    self.assertTrue(a1 <= b0 or b1 <= a0, "%s and %s overlap" % (a, b))

    def test_unknown_dimension_returns_empty(self):
        self.assertEqual(
            rubric.lens_section("## Lens 9 — NOT-A-LENS\nbody\n", "NOT-A-LENS"), "")

    def test_hyphen_instead_of_em_dash_does_not_match(self):
        """Guards the exact failure mode where every slice silently comes back empty."""
        self.assertEqual(rubric.lens_section("## Lens 1 - CORRECTNESS\nbody\n", "CORRECTNESS"), "")

    def test_terminator_is_any_h2_not_only_a_lens_h2(self):
        md = "## Lens 6 — REQUIREMENTS-COVERAGE\nbody\n\n## Per-critic verdict\nOTHER\n"
        got = rubric.lens_section(md, "REQUIREMENTS-COVERAGE")
        self.assertIn("body", got)
        self.assertNotIn("OTHER", got)


if __name__ == "__main__":
    unittest.main()
