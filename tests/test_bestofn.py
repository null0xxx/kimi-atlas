"""Unit tests for scripts.bestofn — risk-funded best-of-N selection (pure decision core).

Pure: a lexicographic rerank picks the ONE winning draft (N->1 collapse) before the
node's VERIFIED, with a guaranteed best-of-1 floor. The N dispatches / build-block
hook / SKILL GENERATE prose are the ROOT's deferred wiring.
"""
from __future__ import annotations

import unittest

from scripts import bestofn


def _cand(index, gate_pass=True, blocking=(), token_cost=0):
    return {"index": index, "gate_pass": gate_pass,
            "defects": [{"severity": s} for s in blocking], "token_cost": token_cost}


class WeightedBlockingTests(unittest.TestCase):
    def test_severity_weights(self) -> None:
        self.assertEqual(bestofn.weighted_blocking([{"severity": "CRITICAL"}]), 2)
        self.assertEqual(bestofn.weighted_blocking([{"severity": "HIGH"}]), 1)
        self.assertEqual(bestofn.weighted_blocking([{"severity": "MEDIUM"}]), 0)
        self.assertEqual(bestofn.weighted_blocking([{"severity": "LOW"}]), 0)

    def test_sum_and_empty(self) -> None:
        self.assertEqual(bestofn.weighted_blocking(
            [{"severity": "CRITICAL"}, {"severity": "HIGH"}, {"severity": "LOW"}]), 3)
        self.assertEqual(bestofn.weighted_blocking([]), 0)
        self.assertEqual(bestofn.weighted_blocking(None), 0)


class RankKeyTests(unittest.TestCase):
    def test_gate_pass_is_primary(self) -> None:
        # a non-passer with zero defects still ranks BELOW a passer with defects
        passer = _cand(0, gate_pass=True, blocking=("HIGH",), token_cost=999)
        failer = _cand(1, gate_pass=False, blocking=(), token_cost=0)
        self.assertLess(bestofn.rank_key(passer), bestofn.rank_key(failer))

    def test_then_blocking_then_tokens_then_index(self) -> None:
        a = _cand(0, blocking=("CRITICAL",), token_cost=10)
        b = _cand(1, blocking=("HIGH",), token_cost=99)   # fewer weighted blocking wins
        self.assertLess(bestofn.rank_key(b), bestofn.rank_key(a))
        c = _cand(2, blocking=(), token_cost=50)
        d = _cand(3, blocking=(), token_cost=20)           # fewer tokens wins
        self.assertLess(bestofn.rank_key(d), bestofn.rank_key(c))
        e = _cand(4, blocking=(), token_cost=5)
        f = _cand(1, blocking=(), token_cost=5)            # tie -> lower index wins
        self.assertLess(bestofn.rank_key(f), bestofn.rank_key(e))


class SelectTests(unittest.TestCase):
    def test_prefers_passer_over_nonpasser(self) -> None:
        cands = [_cand(0, gate_pass=False, token_cost=0), _cand(1, gate_pass=True, token_cost=500)]
        self.assertEqual(bestofn.select(cands)["index"], 1)

    def test_among_passers_fewest_blocking_then_tokens(self) -> None:
        cands = [_cand(0, blocking=("CRITICAL",), token_cost=1),
                 _cand(1, blocking=("HIGH",), token_cost=100),
                 _cand(2, blocking=("HIGH",), token_cost=50)]
        self.assertEqual(bestofn.select(cands)["index"], 2)  # HIGH(1) + fewest tokens

    def test_best_of_one_floor(self) -> None:  # a single (best-of-1) draft selects itself
        self.assertEqual(bestofn.select([_cand(0, gate_pass=False)])["index"], 0)

    def test_empty_is_none(self) -> None:
        self.assertIsNone(bestofn.select([]))

    def test_more_candidates_never_lower_the_bar(self) -> None:
        # adding worse drafts to a pool never changes the winner away from the best one
        base = [_cand(0, gate_pass=True, blocking=(), token_cost=10)]
        worse = base + [_cand(1, gate_pass=False), _cand(2, blocking=("CRITICAL",), token_cost=1)]
        self.assertEqual(bestofn.select(base)["index"], bestofn.select(worse)["index"])
