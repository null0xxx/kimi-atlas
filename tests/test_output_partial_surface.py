"""Pin: the OUTPUT gate must SURFACE the ContextGraph tool-use completeness signal.

The 6-lens harness flagged (reqcov-reconciliation-surface): `contextgraph.project`
already computes a run's tool-use completeness — `used_tools` ("PARTIAL"/"COMPLETE")
and the `partial_stages` list (stages that dispatched a subagent but recorded NO
matching root-observable `tool_call`) — and it is injected at CODED, but it was
NEVER re-surfaced at the terminal OUTPUT gate. So a run where a subagent did
unobserved tool use shipped with a SILENT gap in the human-facing summary.

This test pins the additive, informational surfacing the OUTPUT prose now encodes:

1. **Symbol existence + signature** — `contextgraph.project(base, run_id)` really
   exists with that exact two-parameter signature (import+inspect discipline: the
   cited symbol is not a fiction).
2. **Prose pin** — the OUTPUT stage reads `contextgraph.project(".atlas",
   "${KIMI_SESSION_ID}")` (the same ledger coordinates the rest of the SKILL uses)
   and surfaces `partial_stages`/`used_tools` in the human summary, alongside the
   existing `missing_stages` completeness reporting.
3. **Behavioral pin** — `project(...)` on a crafted on-disk ledger where a stage
   dispatched a subagent but has NO matching `tool_call` yields `used_tools ==
   "PARTIAL"` with that stage in `partial_stages` (the surfaced signal is real),
   and the fully-covered ledger yields `"COMPLETE"` with no partial stages.

Informational ONLY: this asserts the signal reaches the human at OUTPUT; it never
asserts the signal computes pass/fail (the NO-LLM-verdict invariant and the OUTPUT
human gate are untouched — this is DATA about the run, never a gate).
"""
import inspect
import json
import pathlib
import tempfile
import unittest

from scripts import contextgraph, ctxstore

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


def _section(text: str, header: str, next_header: str) -> str:
    """Return the SKILL body between `header` and the next `next_header`."""
    start = text.index(header)
    end = text.index(next_header, start + len(header))
    return text[start:end]


class TestProjectSymbol(unittest.TestCase):
    def test_project_exists_with_cited_signature(self):
        self.assertTrue(callable(contextgraph.project))
        sig = inspect.signature(contextgraph.project)
        self.assertEqual(
            list(sig.parameters), ["base", "run_id"],
            "OUTPUT prose cites contextgraph.project(base, run_id) — the real "
            "signature must match, or the surfacing names a symbol that does not exist",
        )

    def test_project_return_carries_completeness_fields(self):
        # The exact fields the OUTPUT prose surfaces must be real keys of the return.
        with tempfile.TemporaryDirectory() as tmp:
            ctxstore.init_run(tmp, "r", {"intent": "x"})
            graph = contextgraph.project(tmp, "r")
        self.assertIn("partial_stages", graph)
        self.assertIn("used_tools", graph)


class TestOutputStageSurfacesCompleteness(unittest.TestCase):
    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        self.output = _section(self.text, "### OUTPUT", "## Timeout handling")

    def test_output_stage_invokes_project(self):
        # The OUTPUT summary must actually read the real read-path symbol.
        self.assertIn("contextgraph.project", self.output)

    def test_output_surfaces_completeness_fields(self):
        # Both trusted completeness fields are named in the surfaced line.
        self.assertIn("used_tools", self.output)
        self.assertIn("partial_stages", self.output)
        # PARTIAL is the literal that triggers the informational line.
        self.assertIn("PARTIAL", self.output)

    def test_output_uses_real_ledger_coordinates(self):
        # base=".atlas", run_id="${KIMI_SESSION_ID}" — the same coordinates every
        # ctxstore call in the SKILL uses; no invented base/run_id.
        self.assertIn(".atlas", self.output)
        self.assertIn("${KIMI_SESSION_ID}", self.output)

    def test_output_surfacing_is_informational_not_a_gate(self):
        # Additive DATA about the run; degrades to nothing and never gates.
        self.assertIn("informational", self.output.lower())
        # The existing missing_stages completeness reporting is untouched.
        self.assertIn("missing", self.output)

    def test_output_does_not_surface_untrusted_node_text(self):
        # ONLY the trusted stage names / literal are surfaced — never the untrusted
        # tool/error node text. The prose must state that exclusion explicitly (SAFE-2),
        # AND the executable surfacing snippet must emit `partial_stages`, never any
        # `untrusted_*` field (the surfaced string cannot leak untrusted node text).
        self.assertIn("SAFE-2", self.output)
        self.assertRegex(self.output, r"untrusted.{0,90}never")
        completeness = self.output[self.output.index("Tool-use completeness"):]
        fence = completeness[completeness.index("```") + 3:]
        snippet = fence[:fence.index("```")]
        self.assertIn("partial_stages", snippet)
        self.assertNotIn("untrusted", snippet)


class TestCompletenessSignalIsReal(unittest.TestCase):
    """Behaviorally verify the surfaced signal on a crafted on-disk ledger."""

    def _project(self, log_lines, hooks_lines):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base, run = tmp.name, "run1"
        ctxstore.init_run(base, run, {"intent": "do the thing"})
        d = pathlib.Path(base) / run
        (d / "log.jsonl").write_text(
            "".join(json.dumps(x) + "\n" for x in log_lines), encoding="utf-8")
        (d / "hooks.jsonl").write_text(
            "".join(json.dumps(x) + "\n" for x in hooks_lines), encoding="utf-8")
        return contextgraph.project(base, run)

    def test_unobserved_subagent_tool_use_surfaces_as_partial(self):
        # GROUNDED dispatched a subagent but no tool_call covers it → PARTIAL.
        graph = self._project(
            log_lines=[
                {"stage": "CODED", "agent": "elite-coder"},
                {"stage": "GROUNDED", "agent": "scout"},
            ],
            hooks_lines=[
                {"kind": "tool_call", "payload": {"tool": "Bash", "stage": "CODED"}},
            ],
        )
        self.assertEqual(graph["used_tools"], "PARTIAL")
        self.assertIn("GROUNDED", graph["partial_stages"])
        self.assertNotIn("CODED", graph["partial_stages"])

    def test_fully_covered_run_surfaces_as_complete(self):
        # Every dispatching stage has a matching tool_call → COMPLETE, no partials.
        graph = self._project(
            log_lines=[{"stage": "CODED", "agent": "elite-coder"}],
            hooks_lines=[{"kind": "tool_call", "payload": {"stage": "CODED"}}],
        )
        self.assertEqual(graph["used_tools"], "COMPLETE")
        self.assertEqual(graph["partial_stages"], [])


if __name__ == "__main__":
    unittest.main()
