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

    def test_a_dimension_that_is_a_prefix_of_the_heading_does_not_match(self):
        """The `\\b` after the dimension is load-bearing and its loss is the MIS-SLICE
        failure mode, strictly worse than the empty-slice one: without it,
        `## Lens 1 — CORRECTNESSX` matches the CORRECTNESS request and the critic is
        handed a rubric for a lens it is not judging — with a NON-empty slice, so the
        caller's "treat an empty slice as a hard failure" contract cannot see it.
        Pinned on a REAL dimension; `references/rubric.md` matches either way."""
        self.assertEqual(
            rubric.lens_section("## Lens 1 — CORRECTNESSX\nbody\n", "CORRECTNESS"), "")

    def test_terminator_is_any_h2_not_only_a_lens_h2(self):
        md = "## Lens 6 — REQUIREMENTS-COVERAGE\nbody\n\n## Per-critic verdict\nOTHER\n"
        got = rubric.lens_section(md, "REQUIREMENTS-COVERAGE")
        self.assertIn("body", got)
        self.assertNotIn("OTHER", got)


class TestV7NamesTheDeterministicFloor(unittest.TestCase):
    """E3: rubric.md's V7 narrowing ("any defect **a critic emits**") was
    adjudicated WRONG — floorsynth's CORRECTNESS/SECURITY-category syntheses
    (empty-diff, pathcheck, sast) DO drive the loop, and V7 must keep naming
    them explicitly so it cannot silently re-narrow.

    v1.5.2.1 correction: this class used to also assert the phrase "no origin
    filter". That phrase was itself a documentation fiction, and it is NOT
    relaxed here — it is replaced by a strictly stronger pair. Proven by
    execution against the shipped REFINE? block, which reads

        actionable = [d for d in merged["defects"]
                      if d.get("id") not in floorsynth.ORCHESTRATOR_DEFECT_IDS]

    *before* evaluating both ``should_refine`` and the V7 clause: a HIGH
    ``dimension-dissent:correctness`` gives ``should_refine=False v7=False``.
    So there IS an origin filter. The replacement assertions are (a) the false
    phrase is gone, (b) V7 states the exclusion by naming
    ``ORCHESTRATOR_DEFECT_IDS``, and (c) the coupled behavioural pin below —
    every floor id V7 names as forcing a pass really is outside that set."""

    def _rubric_text(self):
        return (pathlib.Path(__file__).resolve().parents[1]
                / "references" / "rubric.md").read_text(encoding="utf-8")

    def _v7_paragraph(self):
        v7 = self._rubric_text().split("Severity-trust caveat (V7)", 1)[1]
        return v7.split("\n## ", 1)[0]

    def test_v7_names_the_floor_and_rejects_the_narrowed_phasing(self):
        v7 = self._v7_paragraph()
        for token in ("pathcheck", "sast", "empty-diff"):
            self.assertIn(token, v7, "V7 no longer names the deterministic floor")
        self.assertNotIn("any defect a critic emits", v7,
                         "the adjudicated-wrong narrowing is back")

    def test_v7_does_not_claim_there_is_no_origin_filter(self):
        """The shipped REFINE? block filters by id before filtering by category."""
        self.assertNotIn(
            "no origin filter", self._v7_paragraph(),
            "V7 again claims the REFINE? decision applies no origin filter; the "
            "shipped block drops every ORCHESTRATOR_DEFECT_IDS member first, so a "
            "HIGH dimension-dissent:correctness forces no refine pass",
        )

    def test_v7_names_the_orchestrator_exclusion(self):
        self.assertIn("ORCHESTRATOR_DEFECT_IDS", self._v7_paragraph(),
                      "V7 must name the id set that decides coder-actionability")

    def test_every_v7_forcing_floor_id_is_outside_the_orchestrator_set(self):
        """Coupled pin: the ids V7 promises will drive the loop must be able to.

        Not a restatement of the constant — these ids are read out of the prose
        and checked against the code. Moving any of them into
        ORCHESTRATOR_DEFECT_IDS (or renaming one in the docs) fails here.
        """
        from scripts import floorsynth
        v7 = self._v7_paragraph()
        forcing = ("pathcheck", "sast", "empty-diff", "out-of-scope")
        for name in forcing:
            self.assertIn(name, v7, f"V7 no longer names {name} as forcing")
        # The concrete ids those names produce, all of which must stay actionable.
        for did in ("empty-diff", "out-of-scope:src/x.py", "P1", "rules.python.foo"):
            self.assertNotIn(
                did, floorsynth.ORCHESTRATOR_DEFECT_IDS,
                f"{did!r} joined ORCHESTRATOR_DEFECT_IDS, so REFINE? now drops it "
                f"and V7's promise that it forces a pass is false",
            )
        # ...and the ids V7 says are excluded really are.
        for did in ("stale-verdict", "critic-schema", "evidence-incomplete",
                    "dimension-dissent:correctness", "critic-missing:security"):
            self.assertIn(did, floorsynth.ORCHESTRATOR_DEFECT_IDS)


if __name__ == "__main__":
    unittest.main()
