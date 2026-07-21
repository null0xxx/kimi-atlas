"""Property tests for scripts.fsm — pure canonical-transition legality.

Asserts the legality graph on fsm ALONE. It NEVER asserts over advance() call
sites: the suite deliberately performs out-of-order advances (test_ctxstore.py),
which stay green and characterize the frozen permissive-recorder contract.
"""
from __future__ import annotations

import unittest

from scripts import fsm
from scripts.ctxstore import CONDITIONAL_STAGES, MANDATORY_STAGES, STAGES


class TestDerivedForwardEdges(unittest.TestCase):
    def test_every_forward_adjacent_pair_is_legal(self):
        for a, b in zip(STAGES, STAGES[1:]):
            with self.subTest(edge=(a, b)):
                self.assertTrue(fsm.legal_transition(a, b))

    def test_verified_to_refine_is_derived_legal(self):
        # VERIFIED->REFINE is a derived forward-adjacent edge (not the declared one).
        self.assertTrue(fsm.legal_transition("VERIFIED", "REFINE"))
        self.assertIn(("VERIFIED", "REFINE"), fsm._derived_edges())

    def test_conditional_skip_edges_are_legal(self):
        # CLARIFY skip: INTENT_CAPTURED->TRIAGED ; REFINE skip: VERIFIED->OUTPUT.
        self.assertTrue(fsm.legal_transition("INTENT_CAPTURED", "TRIAGED"))
        self.assertTrue(fsm.legal_transition("VERIFIED", "OUTPUT"))


class TestDeclaredLoopEdge(unittest.TestCase):
    def test_refine_to_coded_is_declared_legal(self):
        # The one non-derivable edge: the backward refine loop (SKILL.md:594-598).
        self.assertTrue(fsm.legal_transition("REFINE", "CODED"))

    def test_declared_edge_is_not_derivable(self):
        self.assertNotIn(("REFINE", "CODED"), fsm._derived_edges())
        self.assertIn(("REFINE", "CODED"), fsm._DECLARED_EDGES)
        self.assertIn(("REFINE", "CODED"), fsm._LEGAL_EDGES)


class TestIllegalTransitions(unittest.TestCase):
    def test_forward_skip_over_mandatory_is_illegal(self):
        # Skipping the mandatory CODED stage is rejected.
        self.assertFalse(fsm.legal_transition("GROUNDED", "VERIFIED"))

    def test_multi_stage_forward_skip_is_illegal(self):
        self.assertFalse(fsm.legal_transition("INTENT_CAPTURED", "GROUNDED"))

    def test_arbitrary_backward_jump_is_illegal(self):
        self.assertFalse(fsm.legal_transition("OUTPUT", "INIT"))

    def test_unknown_stage_is_illegal_either_side(self):
        self.assertFalse(fsm.legal_transition("NOPE", "INIT"))
        self.assertFalse(fsm.legal_transition("INIT", "NOPE"))

    def test_self_loop_is_illegal(self):
        self.assertFalse(fsm.legal_transition("CODED", "CODED"))


class TestMembershipGuard(unittest.TestCase):
    def test_every_declared_edge_node_is_a_real_stage(self):
        nodes = frozenset(STAGES) | frozenset(CONDITIONAL_STAGES)
        for a, b in fsm._DECLARED_EDGES:
            with self.subTest(edge=(a, b)):
                self.assertIn(a, nodes)
                self.assertIn(b, nodes)

    def test_all_nodes_is_the_stages_union(self):
        self.assertEqual(
            fsm._ALL_NODES, frozenset(STAGES) | frozenset(CONDITIONAL_STAGES)
        )


class TestLegalPath(unittest.TestCase):
    def test_empty_and_single_are_vacuously_legal(self):
        self.assertTrue(fsm.legal_path([]))
        self.assertTrue(fsm.legal_path(["CODED"]))

    def test_refine_loop_path_is_legal(self):
        # VERIFIED->REFINE (derived) ; REFINE->CODED (declared) ; CODED->VERIFIED (derived).
        self.assertTrue(
            fsm.legal_path(["VERIFIED", "REFINE", "CODED", "VERIFIED"])
        )

    def test_mandatory_only_chain_is_a_legal_path(self):
        # Both conditionals skipped: INTENT_CAPTURED->TRIAGED and VERIFIED->OUTPUT.
        # Derived from MANDATORY_STAGES so it self-adjusts if STAGES changes.
        self.assertTrue(fsm.legal_path(list(MANDATORY_STAGES)))

    def test_full_chain_with_conditionals_is_legal(self):
        self.assertTrue(fsm.legal_path(list(STAGES)))

    def test_path_with_a_forward_skip_is_illegal(self):
        # GROUNDED->VERIFIED skips mandatory CODED.
        self.assertFalse(fsm.legal_path(["GROUNDED", "VERIFIED", "OUTPUT"]))

    def test_path_with_illegal_backward_jump_is_illegal(self):
        self.assertFalse(fsm.legal_path(["VERIFIED", "OUTPUT", "INIT"]))


if __name__ == "__main__":
    unittest.main()
