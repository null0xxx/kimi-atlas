# Live validation — kimi-atlas / ATLAS-WEAVE on Kimi 3

This records the first end-to-end validation of the whole system on the **live Kimi CLI v0.26.0**
(the `k3` model, 1M context). The design was authored against v0.23.5 / 256K; this is the proof it
runs, correctly and safely, on the newer runtime. All runs were headless (`kimi -p`) on a clone of
this repo; every ledger cited lives under the run's `.atlas/<session>/`.

## Runtime compatibility (Stage 0)

- **Both skills load and dispatch:** `/skill:atlas ping` and `/skill:atlas-weave ping` each return
  their exact one-liner — plugin discovery, the `Skill` tool, and SKILL-body execution all survive
  the v0.23.5 → v0.26.0 jump.
- **Six runtime-physics probes** (each in a throwaway home): the `PreToolUse` block mechanism is
  honored (both exit-2 and permissionDecision-JSON); `AGENTS.md` discovery works; the `loop_control`
  governor exists but the self-cap `MAX_PASSES=2` holds regardless; session-start / run-id behaviors
  degrade to the on-disk ledger fallback as designed. No blocker.
- **AgentSwarm is present** on v0.26.0 (`concurrency`/`tasks`/`subagent_type` params) — a future path
  to lift the ≤3-wave cap, adopted only behind a dedicated behavior probe.
- **Context window:** the runtime is multi-model — `kimi-for-coding*` = 256K, **`k3` = 1M**, and
  `default_model` is already `k3`. No code hardcodes a 256K-derived threshold (the disk-state / resume
  backbone is window-agnostic), so 1M is pure headroom: FullCompaction now triggers ~891K instead of
  ~223K, making compaction rare rather than the normal path for large runs.

## Stage 1 — atlas (single change)

**Task:** fix a real leap-year century-rule bug so a failing unit test passes. **Result:** `INIT → OUTPUT`
in ~13 min, exit 0.

- Full state machine drained; `context-scout`, `elite-coder`, and all three critics dispatched.
- The coder produced the correct Gregorian rule in an **isolated worktree** (`review_root = worktree`).
- The 6-lens harness returned verdict **`OK`**, all six dimensions `yes`; `runcheck` reported the 4
  tests green.
- **Never auto-applied** — the real file stayed buggy on disk, the fix awaiting the human OUTPUT gate.
- Plain `-p` auto-resolves the AskUserQuestion gates and reaches OUTPUT without blocking (note:
  `-p` rejects `--yolo`/`--auto`; plain `-p` handles the gates itself).

## Stage 2 — ATLAS-WEAVE (first-ever live multi-agent run)

**Task:** add a `__all__` public-API list to each of `scripts/budget.py`, `scripts/leaseclock.py`,
`scripts/runcaps.py` — three genuinely disjoint files — keeping the full suite green.
**Result:** ~29.7 min, exit 0, verdict **`OK`**, run_status **`OK`**.

| stage | what happened |
|---|---|
| **DECOMPOSED** | planner produced **3 file-disjoint LEAF nodes** (one per file), each with its own success criterion — a real decomposition, not a degrade. |
| **SCHEDULE ×2** | the flat pool drained all 3 nodes; the **root itself drove each node's scout → coder → critics** (hierarchy-in-data, coders in parallel within the ≤3 wave). Gas stayed bounded — halting held. |
| per-node | all 3 nodes `DONE`, each merged verdict **`OK`** (6 lenses `yes`). |
| **INTEGRATE** | union `git apply` of the 3 diffs (clean); the **combined-tree differential ran the union suite: 585/585 `pass`** — zero cross-tree regressions; the seam critic raised one non-blocking `SEAM1`. (The task ran on a clone of *this* repo, so the union suite here **is** this repo's own 585-test suite — the run is a genuine dogfood.) |
| **AGGREGATE** | one pure fold → verdict **`OK`**, full coverage, zero blocking defects (non-blocking: 3× the missing-test heuristic, correctly suppressed by the "change nothing else" intent). |
| **OUTPUT** | presented verdict + per-node summaries + combined diff at the human gate. **The real tree was untouched** (`git status` clean). |

The verified change (in the combined diff, never applied):

```python
scripts/leaseclock.py:  +__all__ = ["stamp", "expired"]
scripts/runcaps.py:     +__all__ = ["seed_caps"]
scripts/budget.py:      +__all__ = [ ... ]
```

**Agent economy:** ~17 quality-gated agents for this 3-node run (1 planner + 3 scouts + 3 coders +
9 critics + 1 integration critic). Extrapolated to a genuine K=12 task, that is the ~60-agent
envelope — every one gated by the same 6-lens + combined-tree machinery. This is the design's thesis
made concrete: *many agents, each of whose output is mechanically verified.*

Two fixes made during the pre-flight SKILL review — the orchestrator **synthesizing** the fenced
receipt (the inner atlas emits none), and calling `ctxstore.init_run` before the first persist —
executed correctly live, confirming the review caught real integration gaps.

## Stage 3 — Q/T comparison (atlas-weave vs single-shot atlas)

Same task, same model (`k3`/1M), same baseline, run through single-shot `/skill:atlas`:

| metric | single-shot `atlas` | `atlas-weave` |
|---|---|---|
| wall-clock | **~18.8 min** (1128 s) | ~29.7 min (1782 s) — **~1.6×** |
| agents dispatched | ~5 (1 scout + 1 coder + 3 critics) | ~17 (1 planner + 3 scouts + 3 coders + 9 critics + 1 integration) |
| nodes | 1 (one coder holds the whole 3-file change) | 3 (one disjoint LEAF per file) |
| verdict | `OK` | `OK` |
| tests | 585 green | 585 green (union) |
| non-blocking advisories | 5 (1 code-quality + 1 missing-test + 3 per-file coverage) | 4 (3 missing-test + 1 seam) |
| extra verification | — | combined-tree differential (585/585) + seam-critic wave |

**Result:** for this small, cleanly-separable change, **single-shot `atlas` wins on time and cost at
equal quality** (both `OK`, both 585 green) — one coder held all three files in ~1.6× less wall-clock
with ~3× fewer agents. `atlas-weave` spent its extra agents on machinery (planner, per-node isolation,
union differential, seam critic) that a task this small does not need — though it did produce slightly
cleaner *per-file* verdicts, since each node's coder saw only one file.


**Reading.** For a small, cleanly-separable change the decompose → integrate overhead of ATLAS-WEAVE
is not free, and single-shot atlas is expected to finish faster with equal quality (both verify
green). This is the design working as intended: weave earns its overhead on **larger, genuinely
independent** multi-file work — where isolated per-node verification and the combined-tree differential
catch what a single coder holding the whole change cannot — and **degrades to exactly atlas** when it
would not. The honest rule: reach for `atlas` on a focused change, `atlas-weave` when the work is a
real ≥3-way disjoint split.
