"""Wiring pin: the ContextGraph read-path (GRAPH_LOOKUP) must be CONSUMED at CODED.

`scripts/contextgraph.py` builds + caches the graph and exposes
`graph_lookup(base, run_id) -> str` (the SAFE-2-wrapped current graph), but the
projection is inert until a SKILL actually injects it into a model's packet. This
test pins the wiring the SKILL's CODED-stage prose now encodes:

1. **Symbol existence + signature** — `contextgraph.graph_lookup(base, run_id)`
   really exists with that exact two-parameter signature (mirrors the P3B.5/P4.3
   import+inspect discipline: the cited symbol is not a fiction).
2. **Prose pin** — the CODED stage (the elite-coder packet assembly) invokes
   `contextgraph.graph_lookup(...)` and injects the returned string as the
   "current run state graph" architectural-state DATA context, and the injection
   RECURS on a REFINE re-dispatch. It is a HINT, never a gate.

Prose + read-path only: this asserts the graph reaches the coder; it never
asserts the graph computes pass/fail (the NO-LLM-verdict invariant is untouched).
"""
import inspect
import pathlib
import unittest

from scripts import contextgraph

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


def _section(text: str, header: str, next_header: str) -> str:
    """Return the SKILL body between `### <header>` and the next `### <next_header>`."""
    start = text.index(header)
    end = text.index(next_header, start + len(header))
    return text[start:end]


class TestGraphLookupSymbol(unittest.TestCase):
    def test_graph_lookup_exists_with_cited_signature(self):
        self.assertTrue(callable(contextgraph.graph_lookup))
        sig = inspect.signature(contextgraph.graph_lookup)
        self.assertEqual(
            list(sig.parameters), ["base", "run_id"],
            "SKILL cites contextgraph.graph_lookup(base, run_id) — the real "
            "signature must match, or the wiring names a symbol that does not exist",
        )
        # It renders a SAFE-2-wrapped string (injected as-is as DATA).
        self.assertEqual(sig.return_annotation, "str")


class TestCodedStageGraphInjection(unittest.TestCase):
    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        self.coded = _section(self.text, "### CODED", "### VERIFIED")

    def test_coded_stage_invokes_graph_lookup(self):
        # The CODED packet assembly must actually CALL the real read-path symbol.
        self.assertIn("GRAPH_LOOKUP", self.coded)
        self.assertIn("contextgraph.graph_lookup", self.coded)

    def test_injected_as_run_state_graph_data_context(self):
        # Injected as architectural-state DATA — the "current run state graph".
        self.assertIn("current run state graph", self.coded)
        # It is a HINT/context that degrades to no-injection, never a gate.
        self.assertIn("no-injection", self.coded)

    def test_uses_real_ledger_coordinates(self):
        # base=".atlas", run_id="${KIMI_SESSION_ID}" — the same coordinates every
        # ctxstore call in the SKILL uses; no invented base/run_id.
        self.assertIn(".atlas", self.coded)
        self.assertIn("${KIMI_SESSION_ID}", self.coded)

    def test_recurs_on_refine_redispatch(self):
        # A REFINE loop re-enters CODED, so the graph is recomputed (reflecting the
        # pass's failure/error events) — the wiring must say so.
        refine = _section(self.text, "### REFINE?", "### Checkpoints")
        self.assertIn("GRAPH_LOOKUP", refine)


if __name__ == "__main__":
    unittest.main()
