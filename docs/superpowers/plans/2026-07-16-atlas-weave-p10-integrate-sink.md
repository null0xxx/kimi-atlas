# ATLAS-WEAVE P10 — INTEGRATE Sink (deterministic decision core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure, deterministic decision core of the ATLAS-WEAVE INTEGRATE sink — the combined-tree gate that closes the "individual green ≠ combined green" gap: the **actual-file cross-change conflict gate** (`integrate.py`), the **differential regression oracle** (`differential.py`), and the **integration verdict fold**. These are the mechanically-decided outputs of the sink; the runtime "hands" (real `git apply` of the union onto a worktree, and running the union of suites to produce combined results) are the scheduler-wiring layer, deferred exactly as P6/P7 deferred the live SKILL orchestration.

**Architecture:** After the scheduler produces N disjoint per-node diffs, the INTEGRATE sink must catch what per-node verification cannot: two changes that are each green alone but red together. This plan builds the deterministic detectors. `integrate.actual_conflicts` re-validates disjointness against the files each diff *actually* touched (not the planner's declared scope, and not `git-apply`-clean — which is silent on same-file-different-hunk edits). `differential.regressions` is a zero-false-positive oracle: a test in the union of per-node baseline-green suites whose status on the combined tree is not "pass" is a mathematically-certain cross-change regression, with no model judgment. `integrate.integration_verdict` folds both into the canonical `{dimensions, defects, verdict}` shape `verdict.aggregate` (P6) already consumes. No model computes any of this.

**Tech Stack:** Python 3 (standard library only), `unittest`, the existing `scripts/`+`tests/` conventions. Builds on P6's `scripts/verdict.py` (`merge`).

## Global Constraints

- **Stdlib only.** No new dependencies. Pure functions: no file I/O, subprocess, network, LLM, `time`, or `random`; no mutation of inputs. (The git-apply and suite-runner I/O are explicitly OUT OF SCOPE for this phase — see the scoping note.)
- **Style mirrors `scripts/verdict.py`/`scripts/plandag.py`:** `from __future__ import annotations`, docstrings, type hints; module docstring stating the file holds NO orchestration/LLM knowledge — only deterministic logic — and (for both new modules) that the git-apply / suite-runner mechanics are deferred to runtime wiring.
- **No model computes pass/fail** (DS-3). The differential is a deterministic set-difference over test statuses; the conflict gate is a deterministic set-intersection over touched files.
- **Canonical defect shape** `{id, category, severity, location, fix}`; `category` ∈ `{CORRECTNESS, CODE-QUALITY, SECURITY, TEST-ADEQUACY, DOES-IT-RUN, REQUIREMENTS-COVERAGE}`; blocking = `{CRITICAL, HIGH}`. A cross-change file conflict = **CORRECTNESS/CRITICAL** (two coders corrupting one file); a combined-tree regression = **CORRECTNESS/HIGH** (green alone, wrong combined).
- **Determinism:** every function's output is order-stable (sort where a set/dict would otherwise leak iteration order).
- **`make ci` must stay green.** Tests auto-discovered by `python3 -m unittest discover -s tests`.
- **Imports resolve as** `from scripts import integrate` / `from scripts import differential`. `integrate` imports `verdict` (P6, pure); no cycle. `differential` imports nothing from `scripts`.
- **Conventional commits**, one per task, ending with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Create `scripts/integrate.py`** — `touched_files`, `actual_conflicts`, `integration_verdict`.
- **Create `scripts/differential.py`** — `regressions`, `integration_defects`.
- **Create `tests/test_integrate.py`**, **`tests/test_differential.py`** — unit tests (happy + boundary + red-team).

Data shapes:
- **change** = `{"id": str, "diff": str}` (a node's id + its unified diff patch).
- **combined results** = `{test_id: "pass"|"fail"|...}` — the status of each test on the merged tree (produced by the deferred runner).
- **baseline pass set** = `set[str]` — the union of test-ids that passed in each node's own isolated suite run.

---

### Task 1: `integrate.touched_files` — parse the files a diff actually touches

**Files:**
- Create: `scripts/integrate.py`
- Test: `tests/test_integrate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `touched_files(diff_text: str) -> list[str]` — the repo-relative paths a unified diff touches, parsed from `+++ b/<path>` and `--- a/<path>` headers, dropping `/dev/null`. Order-preserving, de-duplicated.

- [ ] **Step 1: Write the failing test**

Create `tests/test_integrate.py`:

```python
"""Unit tests for scripts.integrate — the INTEGRATE sink's deterministic decision core.

Pure: parses diffs and folds defects; the actual git-apply / suite-runner mechanics
are deferred to runtime wiring. Covers happy + boundary + the same-file conflict
red-team.
"""
from __future__ import annotations

import unittest

from scripts import integrate

_DIFF_A = """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,2 +1,3 @@
 x = 1
+y = 2
"""

_DIFF_NEW = """diff --git a/src/new.py b/src/new.py
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1 @@
+z = 3
"""

_DIFF_DEL = """diff --git a/src/gone.py b/src/gone.py
--- a/src/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-obsolete = 1
"""


class TouchedFilesTests(unittest.TestCase):
    def test_modified_file(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_A), ["src/a.py"])

    def test_new_file_drops_dev_null(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_NEW), ["src/new.py"])

    def test_deleted_file_drops_dev_null(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_DEL), ["src/gone.py"])

    def test_multiple_files_deduped_order_preserved(self) -> None:
        combined = _DIFF_A + _DIFF_NEW + _DIFF_A
        self.assertEqual(integrate.touched_files(combined), ["src/a.py", "src/new.py"])

    def test_empty_diff(self) -> None:
        self.assertEqual(integrate.touched_files(""), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_integrate.TouchedFilesTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.integrate'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/integrate.py`:

```python
"""INTEGRATE-sink decision core for ATLAS-WEAVE (pure, deterministic).

Mirrors verdict.py/plandag.py discipline: NO orchestration/LLM/I/O — only
deterministic functions over diffs and defect lists. This module decides what the
combined-tree sink must FLAG (cross-change file conflicts, folded integration
verdict); the runtime "hands" — actually `git apply`-ing the union of diffs onto a
worktree and running the union of suites — are the scheduler-wiring layer and are
deliberately OUT OF SCOPE here (mirrors how P6/P7 built pure cores first).
"""
from __future__ import annotations

import re

from scripts import verdict

# A unified-diff file header: the path after `+++ ` / `--- ` (optionally `b/`/`a/`).
_PLUS = re.compile(r"^\+\+\+ (?:b/)?(.+)$", re.M)
_MINUS = re.compile(r"^--- (?:a/)?(.+)$", re.M)


def touched_files(diff_text: str) -> list[str]:
    """Return the repo-relative paths a unified diff touches (order-preserving, deduped).

    Reads both `+++ b/<path>` (adds/modifies) and `--- a/<path>` (deletes) headers so
    a deleted file (whose `+++` is `/dev/null`) is still counted; `/dev/null` is
    dropped. This is the ACTUAL touched-file set — the ground truth for the
    cross-change conflict gate, which the planner's declared scope_paths and a clean
    `git apply` cannot be trusted to reflect.
    """
    seen: set[str] = set()
    out: list[str] = []
    for match in list(_PLUS.finditer(diff_text)) + list(_MINUS.finditer(diff_text)):
        path = match.group(1).strip()
        if path and path != "/dev/null" and path not in seen:
            seen.add(path)
            out.append(path)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_integrate.TouchedFilesTests -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/integrate.py tests/test_integrate.py
git commit -m "feat(integrate): touched_files diff parser for the INTEGRATE sink

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `integrate.actual_conflicts` — the actual-file cross-change conflict gate

**Files:**
- Modify: `scripts/integrate.py` (append)
- Test: `tests/test_integrate.py` (append)

**Interfaces:**
- Consumes: `touched_files`.
- Produces: `actual_conflicts(changes: list[dict]) -> list[dict]` — `changes` is `[{"id": str, "diff": str}]`; returns one **CORRECTNESS/CRITICAL** defect per file touched by **≥2** changes (sorted by path). Empty list = the changes are actually disjoint. This catches same-file-different-hunk edits that a clean `git apply` silently concatenates.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_integrate.py`:

```python
class ActualConflictsTests(unittest.TestCase):
    def test_disjoint_changes_no_conflict(self) -> None:
        changes = [{"id": "n1", "diff": _DIFF_A}, {"id": "n2", "diff": _DIFF_NEW}]
        self.assertEqual(integrate.actual_conflicts(changes), [])

    def test_same_file_two_changes_is_critical_conflict(self) -> None:  # RED-TEAM
        # Both touch src/a.py — a clean git apply would silently concatenate them.
        changes = [{"id": "n1", "diff": _DIFF_A}, {"id": "n2", "diff": _DIFF_A}]
        defects = integrate.actual_conflicts(changes)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertEqual(d["location"], "src/a.py")
        self.assertIn("n1", d["fix"])
        self.assertIn("n2", d["fix"])

    def test_defect_shape_is_canonical(self) -> None:
        changes = [{"id": "n1", "diff": _DIFF_A}, {"id": "n2", "diff": _DIFF_A}]
        d = integrate.actual_conflicts(changes)[0]
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})

    def test_conflicts_sorted_by_path(self) -> None:
        d2 = _DIFF_A.replace("src/a.py", "src/z.py")
        d3 = _DIFF_A.replace("src/a.py", "src/m.py")
        changes = [{"id": "n1", "diff": _DIFF_A + d2}, {"id": "n2", "diff": _DIFF_A + d2 + d3},
                   {"id": "n3", "diff": d3}]
        locations = [d["location"] for d in integrate.actual_conflicts(changes)]
        self.assertEqual(locations, sorted(locations))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_integrate.ActualConflictsTests -v`
Expected: FAIL — `AttributeError: module 'scripts.integrate' has no attribute 'actual_conflicts'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/integrate.py`:

```python
def actual_conflicts(changes: list[dict]) -> list[dict]:
    """Return a CORRECTNESS/CRITICAL defect per file touched by more than one change.

    ``changes`` = ``[{"id": str, "diff": str}]``. Re-validates disjointness against
    the files each diff ACTUALLY touched — the post-coding backstop the P6 review
    required, because a planner's declared ``scope_paths`` and a clean ``git apply``
    both miss same-file-different-hunk edits (which concatenate silently). Two
    changes editing one file would corrupt each other, so each shared file is a
    blocking conflict. Defects are sorted by path for deterministic output; empty
    list means the changes are actually disjoint.
    """
    file_to_ids: dict[str, list[str]] = {}
    for change in changes:
        for path in touched_files(change.get("diff", "")):
            file_to_ids.setdefault(path, []).append(change.get("id"))
    defects: list[dict] = []
    for path in sorted(file_to_ids):
        ids = sorted({i for i in file_to_ids[path] if i is not None})
        if len(file_to_ids[path]) >= 2 and len(ids) >= 2:
            defects.append({
                "id": f"integrate-conflict:{path}",
                "category": "CORRECTNESS",
                "severity": "CRITICAL",
                "location": path,
                "fix": f"file {path} is edited by multiple changes ({', '.join(ids)}); "
                       f"make the node scopes actually disjoint",
            })
    return defects
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_integrate.ActualConflictsTests -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/integrate.py tests/test_integrate.py
git commit -m "feat(integrate): actual_conflicts cross-change file gate

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `differential.regressions` — the combined-tree regression oracle

**Files:**
- Create: `scripts/differential.py`
- Test: `tests/test_differential.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `regressions(baseline_pass: set, combined: dict) -> list[str]` — `baseline_pass` = the union of test-ids that passed in each node's own isolated suite; `combined` = `{test_id: status}` on the merged tree. Returns the **sorted** list of test-ids in `baseline_pass` whose combined status is not `"pass"` (failed OR missing) — a zero-false-positive cross-change regression, no model judgment.

- [ ] **Step 1: Write the failing test**

Create `tests/test_differential.py`:

```python
"""Unit tests for scripts.differential — the combined-tree regression oracle (pure).

A test green in every node's isolated suite but not green on the merged tree is a
mathematically-certain cross-change regression. The suite-RUNNER that produces
`combined` is deferred to runtime wiring; this module is the deterministic oracle
over its results.
"""
from __future__ import annotations

import unittest

from scripts import differential


class RegressionsTests(unittest.TestCase):
    def test_all_still_passing_no_regression(self) -> None:
        baseline = {"t1", "t2"}
        combined = {"t1": "pass", "t2": "pass"}
        self.assertEqual(differential.regressions(baseline, combined), [])

    def test_green_alone_red_combined_is_regression(self) -> None:  # the headline
        baseline = {"t1", "t2"}
        combined = {"t1": "pass", "t2": "fail"}
        self.assertEqual(differential.regressions(baseline, combined), ["t2"])

    def test_missing_from_combined_is_regression(self) -> None:
        # A baseline-green test not present on the combined run (e.g. errored/uncollected).
        baseline = {"t1", "t2"}
        combined = {"t1": "pass"}
        self.assertEqual(differential.regressions(baseline, combined), ["t2"])

    def test_new_combined_failure_not_in_baseline_is_ignored(self) -> None:
        # A test that was NOT green in isolation is out of scope for the differential.
        baseline = {"t1"}
        combined = {"t1": "pass", "t3": "fail"}
        self.assertEqual(differential.regressions(baseline, combined), [])

    def test_result_is_sorted(self) -> None:
        baseline = {"t3", "t1", "t2"}
        combined = {"t1": "fail", "t2": "fail", "t3": "fail"}
        self.assertEqual(differential.regressions(baseline, combined), ["t1", "t2", "t3"])

    def test_empty_baseline(self) -> None:
        self.assertEqual(differential.regressions(set(), {"t1": "fail"}), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_differential.RegressionsTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.differential'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/differential.py`:

```python
"""Combined-tree differential oracle for the ATLAS-WEAVE INTEGRATE sink (pure).

A test that is green in every node's OWN baseline suite but is not green when the
union of suites runs on the merged tree is a mathematically-certain cross-change
regression — detected deterministically, with no model judgment. This module is
only the ORACLE over test results; the RUNNER that executes the union of suites on
the merged tree to produce ``combined`` is subprocess I/O, deferred to the
scheduler-wiring layer (mirrors how P6/P7 deferred live-runtime execution).
"""
from __future__ import annotations


def regressions(baseline_pass: set, combined: dict) -> list[str]:
    """Return the sorted test-ids green-in-isolation but not green on the merged tree.

    ``baseline_pass`` = the union of test-ids that passed in each node's own suite.
    ``combined`` = ``{test_id: status}`` from running the union on the merged tree.
    A test in ``baseline_pass`` whose combined status is not exactly ``"pass"``
    (failed, errored, or absent) is a cross-change regression. Zero false positives:
    only tests proven green in isolation can appear, so any non-pass is a genuine
    interaction introduced by combining the changes.
    """
    return sorted(t for t in baseline_pass if combined.get(t) != "pass")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_differential.RegressionsTests -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/differential.py tests/test_differential.py
git commit -m "feat(differential): combined-tree regression oracle

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `differential.integration_defects` — map regressions to blocking defects

**Files:**
- Modify: `scripts/differential.py` (append)
- Test: `tests/test_differential.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `integration_defects(regressed: list) -> list[dict]` — one **CORRECTNESS/HIGH** defect per regressed test-id (a change green alone but wrong combined). Canonical defect shape.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_differential.py`:

```python
class IntegrationDefectsTests(unittest.TestCase):
    def test_no_regressions_no_defects(self) -> None:
        self.assertEqual(differential.integration_defects([]), [])

    def test_regression_is_high_correctness_defect(self) -> None:
        defects = differential.integration_defects(["t2"])
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "HIGH")
        self.assertEqual(d["location"], "t2")
        self.assertIn("t2", d["fix"])

    def test_defect_shape_is_canonical(self) -> None:
        d = differential.integration_defects(["t2"])[0]
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})

    def test_one_defect_per_regression(self) -> None:
        self.assertEqual(len(differential.integration_defects(["t1", "t2", "t3"])), 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_differential.IntegrationDefectsTests -v`
Expected: FAIL — `AttributeError: ... 'integration_defects'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/differential.py`:

```python
def integration_defects(regressed: list) -> list[dict]:
    """Map each cross-change regression to a blocking CORRECTNESS/HIGH defect.

    A test that passes in isolation but fails on the combined tree means the
    combination produces a wrong result — HIGH (likely wrong), blocking. One defect
    per regressed test-id, canonical shape.
    """
    return [
        {
            "id": f"integration-regression:{test_id}",
            "category": "CORRECTNESS",
            "severity": "HIGH",
            "location": test_id,
            "fix": f"test {test_id} passes in isolation but fails on the combined "
                   f"tree; resolve the cross-change interaction",
        }
        for test_id in regressed
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_differential.IntegrationDefectsTests -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/differential.py tests/test_differential.py
git commit -m "feat(differential): map regressions to blocking integration defects

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `integrate.integration_verdict` — fold conflict + differential into one canonical critic

**Files:**
- Modify: `scripts/integrate.py` (append)
- Test: `tests/test_integrate.py` (append)

**Interfaces:**
- Consumes: `scripts.verdict.merge` (P6, pure, already list-shaped).
- Produces: `integration_verdict(defect_lists) -> dict` — flattens an iterable of defect lists (e.g. `actual_conflicts(...)` + `differential.integration_defects(...)`) and returns the canonical `{dimensions, defects, verdict}` shape `verdict.aggregate`/`gate` consume. `verdict` is `"FAIL"` iff any folded defect is blocking.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_integrate.py`:

```python
class IntegrationVerdictTests(unittest.TestCase):
    def _conflict(self):
        return {"id": "c", "category": "CORRECTNESS", "severity": "CRITICAL",
                "location": "src/a.py", "fix": "..."}

    def _regression(self):
        return {"id": "r", "category": "CORRECTNESS", "severity": "HIGH",
                "location": "t2", "fix": "..."}

    def test_clean_integration_is_ok(self) -> None:
        merged = integrate.integration_verdict([[], []])
        self.assertEqual(merged["verdict"], "OK")
        self.assertEqual(merged["defects"], [])
        self.assertEqual(set(merged.keys()), {"dimensions", "defects", "verdict"})

    def test_any_conflict_or_regression_fails(self) -> None:
        merged = integrate.integration_verdict([[self._conflict()], [self._regression()]])
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(len(merged["defects"]), 2)
        self.assertEqual(merged["dimensions"]["CORRECTNESS"], "no")

    def test_output_is_merge_shaped(self) -> None:
        merged = integrate.integration_verdict([[self._regression()]])
        for dim in ("CORRECTNESS", "CODE-QUALITY", "SECURITY", "TEST-ADEQUACY",
                    "DOES-IT-RUN", "REQUIREMENTS-COVERAGE"):
            self.assertIn(merged["dimensions"][dim], ("yes", "no"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_integrate.IntegrationVerdictTests -v`
Expected: FAIL — `AttributeError: ... 'integration_verdict'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/integrate.py`:

```python
def integration_verdict(defect_lists) -> dict:
    """Fold conflict + differential defect lists into one canonical integration critic.

    ``defect_lists`` is an iterable of defect lists (e.g. ``actual_conflicts(...)``
    plus ``differential.integration_defects(...)``). Reuses ``verdict.merge`` (which
    already accepts a list of script defects), so the result is the canonical
    ``{dimensions, defects, verdict}`` shape that ``verdict.aggregate``/``gate``
    consume, with ``verdict == "FAIL"`` iff any folded defect is blocking. Pure.
    """
    all_defects = [defect for lst in defect_lists for defect in (lst or [])]
    return verdict.merge([], all_defects)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_integrate.IntegrationVerdictTests -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/integrate.py tests/test_integrate.py
git commit -m "feat(integrate): integration_verdict fold via verdict.merge

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Green the full gate

**Files:**
- Test: whole repo (`make ci`)

**Interfaces:**
- Consumes: every P10 module.
- Produces: a green `make ci` proving P10 integrates with the P6/P7 backbone.

- [ ] **Step 1: Run the full unit suite**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -5`
Expected: `OK` with the P10 tests added (no failures/errors).

- [ ] **Step 2: Run the full CI pipeline**

Run: `make ci`
Expected: `check-strict` clean, all unit tests `OK`, `Inventory in sync`, `Shell scripts syntax OK.` (The `FAIL … RUBBER STAMP` line printed by `test_run_negative_gate.py` is expected simulated stdout, not a failure — rely on the exit code and the final `OK`.)

- [ ] **Step 3: If anything is red, fix it and re-run**

P10 adds no `.md` docs and no `references/` files, so `check-strict` and `inventory-drift` should stay green. Re-run `make ci` until green.

- [ ] **Step 4: Commit any fixups (only if Step 3 changed files)**

```bash
git add -A
git commit -m "chore(atlas-weave): P10 integrate-sink decision core green under make ci

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage** (against `references/atlas-weave.md` §5 Tier-3 + §9 P10 deliverable):
- Combined-tree **cross-suite differential** (newly-red = deterministic INTEGRATION defect) — `differential.regressions` (Task 3) + `differential.integration_defects` (Task 4). ✓
- **POST-coding actual-file disjointness re-check** — `integrate.touched_files` (Task 1) + `integrate.actual_conflicts` (Task 2). ✓ (This is the P6-review-mandated backstop: declared scope + git-apply-clean are insufficient.)
- **Aggregate roll-up** into the canonical verdict shape — `integrate.integration_verdict` (Task 5), reusing P6's `verdict.merge`; the run-level `verdict.aggregate(node_verdicts, integration_verdict)` from P6 consumes it directly. ✓
- **Deferred by design (runtime wiring, not this phase — mirrors P6/P7 deferring the live SKILL):** the real `git apply` of the union onto a fresh baseline worktree; the suite RUNNER that executes the union of per-node suites on the merged tree to produce `combined`; the combined 6-lens harness pass; the integration-critic seam wave; bounded INTEGRATION_REPAIR. These are I/O the scheduler drives (`runcheck`/`difftool` pattern) and land with the scheduler-wiring phase.

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"/"similar to Task N" — every step shows complete code and an exact command with expected output. ✓

**3. Type consistency:** `touched_files(diff_text:str)->list[str]`, `actual_conflicts(changes:list[dict])->list[dict]`, `integration_verdict(defect_lists)->dict`, `regressions(baseline_pass:set, combined:dict)->list[str]`, `integration_defects(regressed:list)->list[dict]` — names/signatures used identically wherever referenced; the `change`/`combined`/defect shapes match the File Structure block and the canonical defect shape. ✓

---

## Execution Handoff

Execute task-by-task via `superpowers:subagent-driven-development` (haiku implementers for the complete-code tasks, sonnet task reviewers, opus final whole-branch review), or inline via `superpowers:executing-plans`.

**Next phase after P10 lands:** `2026-07-16-atlas-weave-p8-scheduler.md` (the flat W=3 work-stealing pool — the throughput engine and the runtime "hands" that drive plandag's gas/attempt bounds, coerce_dag, and this sink's git-apply/suite-runner), per the spec's phased order (P6→P7→P10→**P8**→P11→P9→P12).
