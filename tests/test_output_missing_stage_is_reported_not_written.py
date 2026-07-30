"""The OUTPUT missing-stage rung must REPORT a gap, never write over it.

THE DEFECT. `skills/atlas/SKILL.md`'s OUTPUT block computes `verdict.missing_stages(...)` and, when
it is non-empty, used to offer as a records-only repair: *"note them in the status / call `advance`
for each"*. `ctxstore.advance` has exactly one mechanism — ``st["current_state"] = stage`` — so that
call does not annotate anything. It **rewinds a terminated, human-gated run to a non-terminal
state**, hands it back to the resume path, and appends an out-of-order ledger line that
`floorsynth.stale_verdict_defects` folds into a blocking CRITICAL at OUTPUT — after REFINE, where
nothing can remedy it.

Measured on a real ledger with GROUNDED skipped::

    BEFORE current_state: OUTPUT
    advance(".atlas", run, "GROUNDED")        # the advertised repair
    AFTER  current_state: GROUNDED            # terminal run is resumable again
    stale_verdict_defects -> [('stale-verdict', 'CRITICAL')]

WHAT THIS FILE PINS. The behavioural half executes the real modules and needs no SKILL text. The
contract half asserts the instruction is gone — and deliberately does NOT use a bare
``assertNotIn("advance", slice)``: the corrected passage legitimately contains the word twice, once
naming the skipped transition and once in the prohibition itself. A pin that banned the token would
manufacture a RED on the correct text — the failure shape this repo has shipped six times.

STANDING LIMITATION. A prose program cannot be executed by a unit test, so the contract pins assert
what the orchestrator reads. This file asserts repository bytes only, never a property of the
process it runs in.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import ctxstore, floorsynth  # noqa: E402

_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


class TestTheRepairIsWorseThanTheGap(unittest.TestCase):
    """Why the instruction had to go — executed against the real modules."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.run = "S"
        ctxstore.init_run(".atlas", self.run, {
            "intent": "i", "success_criteria": ["c"], "verify_cmd": "true",
            "scope_paths": ["src"], "baseline_sha": "",
        })
        # an honest run whose GROUNDED advance was skipped, terminated at OUTPUT
        for stage in ("INIT", "INTENT_CAPTURED", "TRIAGED", "CODED", "VERIFIED", "OUTPUT"):
            ctxstore.advance(".atlas", self.run, stage)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_the_run_is_terminal_before_the_repair(self):
        self.assertEqual(
            ctxstore.get_state(".atlas", self.run)["current_state"], "OUTPUT",
            "the fixture must start terminal, or the rest of this class proves nothing")

    def test_advancing_the_missing_stage_rewinds_a_terminated_run(self):
        """The load-bearing fact: `advance` writes current_state. It cannot annotate.

        Killed by: a ctxstore change that records a stage without moving current_state.
        """
        ctxstore.advance(".atlas", self.run, "GROUNDED")
        self.assertEqual(
            ctxstore.get_state(".atlas", self.run)["current_state"], "GROUNDED",
            "advance() moved a terminated run back to a non-terminal state — this is why the "
            "'repair' is worse than the gap it claims to fix")

    def test_advancing_the_missing_stage_manufactures_a_blocking_critical(self):
        """And the ledger line it appends is folded into a blocking defect at OUTPUT.

        Killed by: a floorsynth change that stops folding out-of-order adjacencies.
        """
        ctxstore.advance(".atlas", self.run, "GROUNDED")
        recs = list(ctxstore._iter_log_records(".atlas", self.run))
        ids = [(d["id"], d["severity"]) for d in floorsynth.stale_verdict_defects(recs)]
        self.assertIn(("stale-verdict", "CRITICAL"), ids,
                      "the advertised repair emits the very defect class that ends a run "
                      "UNVERIFIED with no in-loop remedy")


class TestTheContractNoLongerOffersIt(unittest.TestCase):

    def setUp(self):
        text = _SKILL.read_text(encoding="utf-8")
        start = text.index("If `missing` is non-empty")
        self.rung = text[start:text.index("- **Present the labelled STOP block**", start)]

    def test_the_advance_repair_is_not_offered(self):
        """Killed by: re-inserting the clause in any wording that calls advance for the gap."""
        self.assertNotIn("call `advance` for each", self.rung,
                         "the OUTPUT rung must not offer advance() as a records-only repair")

    def test_it_is_forbidden_explicitly_rather_than_merely_absent(self):
        """A silent deletion invites the next author to re-derive it.

        Killed by: removing the prohibition sentence while leaving the clause gone.
        """
        self.assertIn("Never", self.rung)
        self.assertIn('st["current_state"] = stage', self.rung,
                      "the prohibition must name the MECHANISM — advance has exactly one, and "
                      "that is the whole reason it cannot annotate a missing key")

    def test_the_reporting_half_survives(self):
        """The instruction's true half must not be lost with its false half.

        Killed by: dropping 'note them in the status'.
        """
        self.assertIn("note them in the status", self.rung)
        self.assertIn("do **NOT** re-execute", self.rung,
                      "the no-re-execution rule is the other half of this rung and is correct")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
