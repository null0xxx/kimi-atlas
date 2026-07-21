"""Pin (REQCOV-1): the orchestrator RECORDS a stage-tagged tool_call marker per dispatch.

The ContextGraph tool-use completeness signal (`used_tools` / `partial_stages`) can only
DISCRIMINATE if something actually covers a dispatched stage. Before this wiring nothing
populated `reconcile`'s `covered` set, so `used_tools` was a CONSTANT `PARTIAL` on every
real run and `COMPLETE` was unreachable — the signal carried no information.

The fix makes emitting a stage-tagged `ctxevents.record(<run-dir>, "tool_call",
{"stage": S})` a REQUIRED orchestrator step immediately after each subagent-dispatch
`ctxstore.advance(..., agent=...)` — GROUNDED (context-scout) and CODED (elite-coder).

This test pins BOTH halves of the wiring:

* PROSE — the GROUNDED and CODED dispatch sections of the SKILL now record a
  stage-tagged `tool_call` marker for their OWN stage, right AFTER the `agent=` advance
  (so a crash/skip between the dispatch and its record legitimately surfaces PARTIAL).
* BEHAVIOR — driving the REAL functions (`ctxstore.advance(..., agent=...)` +
  `ctxevents.record(..., "tool_call", {"tool": "Agent", "stage": S})`) makes
  `contextgraph.project` report `used_tools == "COMPLETE"`; dropping one marker makes
  exactly that stage PARTIAL — a genuine recording gap, not a per-run constant.
"""
import pathlib
import tempfile
import unittest

from scripts import contextgraph, ctxevents, ctxstore

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


def _section(text: str, header: str, next_header: str) -> str:
    """Return the SKILL body between `header` and the next `next_header`."""
    start = text.index(header)
    end = text.index(next_header, start + len(header))
    return text[start:end]


class TestSkillRecordsStageTaggedMarkers(unittest.TestCase):
    """Prose pin: each dispatch section records a stage-tagged tool_call marker."""

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")

    def test_grounded_dispatch_records_grounded_marker(self):
        section = _section(self.text, "### GROUNDED", "### PRE-CODE HUMAN GATE")
        self.assertIn('"GROUNDED", agent="context-scout"', section)
        self.assertIn("ctxevents.record", section)
        # the marker names GROUNDED as its stage (a tool_call tagged for this stage).
        self.assertRegex(
            section, r"ctxevents\.record[\s\S]{0,240}tool_call[\s\S]{0,80}GROUNDED")

    def test_coded_dispatch_records_coded_marker(self):
        section = _section(self.text, "### CODED", "### VERIFIED")
        self.assertIn('"CODED", agent="elite-coder"', section)
        self.assertIn("ctxevents.record", section)
        self.assertRegex(
            section, r"ctxevents\.record[\s\S]{0,240}tool_call[\s\S]{0,80}CODED")

    def test_marker_is_recorded_after_the_agent_advance(self):
        # dispatch-integrity ordering: the record must come AFTER its own advance,
        # so a crash/skip between them legitimately surfaces PARTIAL at OUTPUT.
        g = _section(self.text, "### GROUNDED", "### PRE-CODE HUMAN GATE")
        self.assertLess(
            g.index('"GROUNDED", agent="context-scout"'),
            g.rindex("ctxevents.record"),
            "the GROUNDED marker must be recorded after the GROUNDED agent= advance",
        )
        c = _section(self.text, "### CODED", "### VERIFIED")
        self.assertLess(
            c.index('"CODED", agent="elite-coder"'),
            c.rindex("ctxevents.record"),
            "the CODED marker must be recorded after the CODED agent= advance",
        )

    def test_marker_run_dir_is_the_run_directory_not_base_plus_run(self):
        # ctxevents.record's first arg is the RUN directory .atlas/${KIMI_SESSION_ID},
        # NOT the (base, run_id) pair ctxstore/contextgraph take. Pin the correct seam.
        for header, nxt in (("### GROUNDED", "### PRE-CODE HUMAN GATE"),
                            ("### CODED", "### VERIFIED")):
            section = _section(self.text, header, nxt)
            self.assertRegex(
                section,
                r'ctxevents\.record\(\s*["\']\.atlas/\$\{KIMI_SESSION_ID\}["\']',
                f"{header} marker must target run dir .atlas/${{KIMI_SESSION_ID}}",
            )


class TestWiredMarkersDiscriminate(unittest.TestCase):
    """Behavior pin: drive the REAL wiring functions; the signal must discriminate."""

    def _dispatched_run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base, run = tmp.name, "run1"
        ctxstore.init_run(base, run, {"intent": "do the thing"})
        run_dir = str(pathlib.Path(base) / run)
        # the two subagent-dispatch advances the SKILL performs (agent= => dispatched).
        ctxstore.advance(base, run, "GROUNDED", agent="context-scout")
        ctxstore.advance(base, run, "CODED", agent="elite-coder", status="OK")
        return base, run, run_dir

    def test_both_markers_recorded_yields_complete(self):
        base, run, run_dir = self._dispatched_run()
        # the REQUIRED stage-tagged markers, recorded exactly as the SKILL prescribes.
        ctxevents.record(run_dir, "tool_call", {"tool": "Agent", "stage": "GROUNDED"})
        ctxevents.record(run_dir, "tool_call", {"tool": "Agent", "stage": "CODED"})
        graph = contextgraph.project(base, run)
        self.assertEqual(graph["used_tools"], "COMPLETE")
        self.assertEqual(graph["partial_stages"], [])

    def test_missing_marker_flags_only_that_stage_partial(self):
        base, run, run_dir = self._dispatched_run()
        # only CODED's marker is recorded; the GROUNDED marker never happened (a
        # crash/skip between its dispatch and record) => GROUNDED is a recording gap.
        ctxevents.record(run_dir, "tool_call", {"tool": "Agent", "stage": "CODED"})
        graph = contextgraph.project(base, run)
        self.assertEqual(graph["used_tools"], "PARTIAL")
        self.assertEqual(graph["partial_stages"], ["GROUNDED"])


if __name__ == "__main__":
    unittest.main()
