# ATLAS-WEAVE P9 — Risk-funded Best-of-N (pure decision core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure decision core of ATLAS-WEAVE's risk-funded best-of-N mode (`scripts/bestofn.py`) — on a high-risk node the scheduler funds N diverse coder drafts, and this module picks the ONE winner deterministically before that node's VERIFIED (the **N→1 collapse**), so best-of-N never touches the merge/combined-tree machinery. Two pieces: a **lexicographic winner-selection** (a deterministic-floor gate-passer beats a non-passer, then fewer weighted blocking defects, then fewer tokens, then lower index — with a guaranteed best-of-1 floor so more drafts can never lower the bar) and a **risk-funded fan-out decision** (N=n_max only when the node is high-risk AND the budget funds it, else 1).

**Architecture:** All pure over plain candidate dicts + scalar inputs. **Honest scope (§0-C / §8):** on the single-model, no-temperature runtime, draft diversity is prompt-persona-only and *correlated*, so the lift is modest and the risk allocator rarely funds N>1 — best-of-N is a bounded MODE with a guaranteed best-of-1 floor, **not** an independence / `1−(1−p)^N` claim. The actual N coder dispatches, the `PreToolUse` build-block hook that makes "write-only" mechanical, and the SKILL GENERATE-stage prose are the ROOT's deferred wiring, mirroring how prior phases deferred live orchestration.

**Tech Stack:** Python 3 (standard library only — no imports needed), `unittest`. Composes with the P8 scheduler (which funds/dispatches the N drafts and feeds their floor results here) and the P7 `budget`/`risk_score` (which supplies the risk input).

## Global Constraints

- **Stdlib only** (no imports needed). Pure functions: no file I/O, subprocess, network, LLM, `time`, `random`; no input mutation.
- **Style mirrors `scripts/verdict.py`/`scheduler.py`:** `from __future__ import annotations`, docstrings, type hints; module docstring stating the file holds only deterministic logic, the honest-scope caveat, and that the N dispatches / build-block hook / SKILL prose are deferred.
- **Best-of-1 floor is guaranteed:** the best-of-1 draft (index 0) is always in the candidate pool, so `select` is never worse than best-of-1, and a deterministic-floor passer always outranks a non-passer — more drafts can NEVER lower the bar.
- **No model computes pass/fail:** `select` ranks; the winner still faces the node's real VERIFIED (the judgment wave). Best-of-N buys generation diversity, never verification authority.
- **Determinism:** stable tie-break (lowest index).
- **`make ci` must stay green.** Tests auto-discovered by `python3 -m unittest discover -s tests`.
- **Imports resolve as** `from scripts import bestofn`. No import cycle (imports nothing from `scripts`).
- **Conventional commits**, one per task, ending with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## Deferred to runtime (NOT this phase)
The actual N diverse coder dispatches (the scheduler funds them and runs each draft's Tier-1 deterministic floor); the `PreToolUse` hook (`hooks/*.sh`) that denies build commands during GENERATE so "write-only" is mechanical; the SKILL GENERATE-stage prose that reranks the floor results via `select` and hands the winner to VERIFIED.

---

## File Structure
- **Create `scripts/bestofn.py`** — `weighted_blocking`, `rank_key`, `select`, `fanout_n`.
- **Create `tests/test_bestofn.py`** — unit tests (happy + boundary + red-team).

Data shape: a **candidate** = `{"index": int, "gate_pass": bool, "defects": [ {severity, ...} ], "token_cost": int}` — one coder draft plus its deterministic-floor (Tier-1) result.

---

### Task 1: The rerank — `weighted_blocking` + `rank_key` + `select`

**Files:** Create `scripts/bestofn.py`; Test `tests/test_bestofn.py`.
**Interfaces:** `weighted_blocking(defects: list) -> int`; `rank_key(candidate: dict) -> tuple`; `select(candidates: list) -> dict | None`.

- [ ] **Step 1: Write the failing test** — create `tests/test_bestofn.py`:

```python
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
```

- [ ] **Step 2: Run** — `python3 -m unittest tests.test_bestofn -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation** — create `scripts/bestofn.py`:

```python
"""Risk-funded best-of-N selection for ATLAS-WEAVE (pure decision core).

On a high-risk node the scheduler funds N diverse coder drafts; this module picks the
ONE winner deterministically before that node's VERIFIED (the N->1 collapse), so
best-of-N never touches the merge/combined-tree machinery. Selection is a pure
lexicographic rank: a deterministic-floor (Tier-1) gate-passer beats a non-passer,
then fewer weighted blocking defects, then fewer tokens, then lower index. Because the
best-of-1 draft (index 0) is always in the pool, select() >= best-of-1 by construction
(more candidates can never LOWER the bar). The actual N coder dispatches, the
PreToolUse build-block hook that makes 'write-only' mechanical, and the SKILL
GENERATE-stage prose are the ROOT's deferred wiring.

Honest scope (§0-C / §8): on the single-model, no-temperature runtime, draft diversity
is prompt-persona-only and CORRELATED, so the lift is modest and the risk allocator
rarely funds N>1 -- best-of-N is a bounded MODE with a guaranteed best-of-1 floor, NOT
an independence / 1-(1-p)^N claim. No model computes pass/fail: select ranks; the
winner still faces the node's real VERIFIED judgment wave.
"""
from __future__ import annotations

# Only blocking severities weight the rerank; CRITICAL outweighs HIGH. MEDIUM/LOW = 0.
_SEVERITY_WEIGHT: dict[str, int] = {"CRITICAL": 2, "HIGH": 1}


def weighted_blocking(defects: list) -> int:
    """Sum the blocking weight of a draft's defects (CRITICAL=2, HIGH=1, MEDIUM/LOW=0)."""
    return sum(_SEVERITY_WEIGHT.get(d.get("severity"), 0) for d in (defects or []))


def rank_key(candidate: dict) -> tuple:
    """Lexicographic rerank key for a candidate draft -- LOWER is better.

    ``(0 if gate_pass else 1, weighted_blocking, token_cost, index)``: a Tier-1
    deterministic-floor passer sorts ahead of every non-passer, then fewer weighted
    blocking defects, then fewer tokens, then the lower index (a stable tie-break that
    keeps the best-of-1 draft as the default).
    """
    return (
        0 if candidate.get("gate_pass") else 1,
        weighted_blocking(candidate.get("defects", [])),
        candidate.get("token_cost", 0),
        candidate.get("index", 0),
    )


def select(candidates: list) -> dict | None:
    """Return the winning draft (min ``rank_key``), or None if there are no candidates.

    The N->1 collapse: exactly one draft advances to the node's VERIFIED. Because the
    best-of-1 draft is always present, the winner is never worse than best-of-1 (more
    candidates can only improve or tie), and a floor-passer is always preferred over a
    non-passer -- so more drafts can never LOWER the bar.
    """
    return min(candidates, key=rank_key) if candidates else None
```

- [ ] **Step 4: Run** — PASS (10 tests).
- [ ] **Step 5: Commit** — `feat(bestofn): lexicographic rerank + N->1 winner select`.

---

### Task 2: The risk-funded fan-out — `fanout_n`

**Files:** Modify `scripts/bestofn.py`; Test `tests/test_bestofn.py`.
**Interfaces:** `fanout_n(risk: int, risk_threshold: int, can_fund: bool, n_max: int = 3) -> int` — `n_max` iff `risk >= risk_threshold` AND `can_fund` AND `n_max >= 1`, else `1` (the best-of-1 floor). Never returns < 1.

- [ ] **Step 1: Write the failing test** — append:

```python
class FanoutTests(unittest.TestCase):
    def test_high_risk_and_funded_gives_n_max(self) -> None:
        self.assertEqual(bestofn.fanout_n(risk=5, risk_threshold=4, can_fund=True, n_max=3), 3)

    def test_below_threshold_gives_one(self) -> None:
        self.assertEqual(bestofn.fanout_n(risk=3, risk_threshold=4, can_fund=True, n_max=3), 1)

    def test_unfunded_gives_one(self) -> None:
        self.assertEqual(bestofn.fanout_n(risk=9, risk_threshold=4, can_fund=False, n_max=3), 1)

    def test_at_threshold_is_high_risk(self) -> None:  # >= threshold
        self.assertEqual(bestofn.fanout_n(risk=4, risk_threshold=4, can_fund=True, n_max=3), 3)

    def test_never_below_one(self) -> None:  # a degenerate n_max still yields the floor draft
        self.assertEqual(bestofn.fanout_n(risk=9, risk_threshold=4, can_fund=True, n_max=0), 1)
```

- [ ] **Step 2: Run** — `python3 -m unittest tests.test_bestofn.FanoutTests -v` → FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** — append to `scripts/bestofn.py`:

```python
def fanout_n(risk: int, risk_threshold: int, can_fund: bool, n_max: int = 3) -> int:
    """How many drafts to generate for a node: ``n_max`` iff high-risk AND funded, else 1.

    Consequence-weighted spend: best-of-N fires only when the node's risk score meets
    the threshold AND the budget can fund ``n_max`` drafts; otherwise the single
    best-of-1 draft. Never returns < 1 -- there is always at least the floor draft.
    """
    if risk >= risk_threshold and can_fund and n_max >= 1:
        return n_max
    return 1
```

- [ ] **Step 4: Run** — PASS (5 tests).
- [ ] **Step 5: Commit** — `feat(bestofn): risk-funded fanout_n (best-of-N only when high-risk + funded)`.

---

### Task 3: Green the full gate

**Files:** whole repo (`make ci`).
**Interfaces:** a green `make ci` proving P9 integrates with the P6/P7/P10/P8/P11 backbone.

- [ ] **Step 1: Run the full unit suite** — `python3 -m unittest discover -s tests -v 2>&1 | tail -5` → `OK` with the P9 tests added.
- [ ] **Step 2: Run the full CI pipeline** — `make ci` → `check-strict` clean, all unit tests `OK`, `Inventory in sync`, `Shell scripts syntax OK.` (The `FAIL … RUBBER STAMP` line from `test_run_negative_gate.py` is expected simulated stdout — rely on the exit code + final `OK`.)
- [ ] **Step 3: If red, fix and re-run.** P9 adds no `.md`/`references/` files, so naming/inventory stay green.
- [ ] **Step 4: Commit any fixups (only if Step 3 changed files)** — `chore(atlas-weave): P9 best-of-N core green under make ci`.

---

## Self-Review

**1. Spec coverage** (against `references/atlas-weave.md` §9 P9 + §8):
- Deterministic-floor Tier-1 rerank + lexicographic winner select (gate-pass → fewest weighted blocking → fewest tokens → index) — `weighted_blocking` + `rank_key` + `select` (Task 1). ✓
- N→1 collapse before VERIFIED with a guaranteed best-of-1 floor, so more drafts can never lower the bar — `select` (Task 1); pinned by `test_more_candidates_never_lower_the_bar`. ✓
- Risk-funded N∈{1,n_max} (fire only when high-risk + budget funds it) — `fanout_n` (Task 2). ✓
- **Deferred (runtime wiring):** the N diverse coder dispatches; the `PreToolUse` build-block hook that makes "write-only" mechanical; the SKILL GENERATE-stage prose that runs each draft's floor and hands `select`'s winner to VERIFIED.

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"/"similar to Task N" — complete code + exact commands throughout.

**3. Type consistency:** `weighted_blocking(defects:list)->int`, `rank_key(candidate:dict)->tuple`, `select(candidates:list)->dict|None`, `fanout_n(risk:int, risk_threshold:int, can_fund:bool, n_max:int)->int` — signatures used identically; the candidate `{index,gate_pass,defects,token_cost}` shape matches the File Structure block.

---

## Execution Handoff

Execute task-by-task via `superpowers:subagent-driven-development` (haiku implementers for the complete-code tasks, sonnet task reviewers, an opus final whole-branch review — verify the best-of-1-floor / never-lower-the-bar property holds).

**Next phase after P9 lands:** `2026-07-16-atlas-weave-p12-dogfood.md` (fuel/halting caps + negative-gate teeth + a real multi-file dogfood measuring the Q/T delta vs single-shot atlas), the final phase per the spec's order.
