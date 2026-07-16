# ATLAS-WEAVE P12 — Runtime hands + negative-gate teeth + dogfood

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Wire the (complete, tested, but caller-less) ATLAS-WEAVE pure decision cores into runnable deterministic "hands", give the combined-tree gate red-team teeth, and prove the whole pipeline composes end-to-end on a real git repo.

**Architecture:** The pure spine (`plandag`/`planstage`/`scheduler`/`integrate`/`differential`/`budget`/`bestofn`/`verdict.aggregate`/`resume`) is done. P12 adds only the I/O boundary + one outer SKILL: a per-test-id suite runner, a union `git-apply`-on-worktree, a lease/deadline clock, fuel/halting run-caps, an atomic DAG write, a combined-tree negative-gate, a deterministic end-to-end dogfood harness (scripted coders on a real temp git repo), and the `skills/atlas-weave` orchestrator prose. The LIVE Kimi Q/T-delta dogfood is delivered as an instrumented harness + documented procedure (it needs the Kimi agent runtime, not this build env) — honestly labeled, never faked.

**Tech Stack:** Python 3 stdlib only for scripts (subprocess for git/pytest is allowed in the I/O hands — these are the "hands", not the pure cores); `unittest` for tests; real `git` in temp dirs for worktree/apply tests; Markdown for the SKILL.

## Global Constraints

- **The pure cores stay pure and unchanged.** P12 code CALLS them; it must not move logic into them or weaken any invariant (no LLM computes pass/fail; halting via gas+MAX_ATTEMPTS; degrade byte-identical on a 1-node DAG).
- **The hands are deterministic and fail-safe.** Every subprocess/parse failure degrades toward BLOCK/UNVERIFIED, never toward a false green. No time/random in a pure function; where wall-clock is needed (lease clock), `now` is an INJECTED parameter so tests are deterministic.
- **`differential.regressions` contract:** the suite runner MUST emit each test's green status as EXACTLY the lowercase token `"pass"` (any other string is treated as a regression).
- **Lease no-rotation invariant (`resume.py`):** the lease token `f"{job_id}#{attempts}"` does not rotate across a resume, so a killed turn's in-flight receipts MUST be discarded after resume — the clock/reaper and SKILL must honor this.
- **Union-worktree branch naming (§4):** flat branch names `atlas__${SESSION}__task_<id>` to avoid the `.git/refs` directory/file collision that `atlas/${SESSION}/...` nesting causes.
- **Standard commit trailer:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## File Structure

- Create `scripts/suiterun.py` — per-test-id suite runner (→ `differential`).
- Create `scripts/uniontree.py` — union `git-apply`-on-worktree (→ `integrate`).
- Create `scripts/leaseclock.py` — lease/deadline stamp + expiry (→ `scheduler.reap_expired`).
- Create `scripts/runcaps.py` — fuel/halting caps + soft token budget provisioning.
- Modify `scripts/ctxstore.py` — add `write_artifact_atomic` (tmp+rename).
- Create `scripts/run_weave_negative_gate.py` + `tests/fixtures/weave/*` — combined-tree red-team gate.
- Create `scripts/dogfood_weave.py` — deterministic end-to-end dogfood harness.
- Create `skills/atlas-weave/SKILL.md`, `agents/integration-critic.md`; modify `skills/atlas-resume/SKILL.md` — outer orchestrator prose (graph-aware).
- Tests: `tests/test_suiterun.py`, `tests/test_uniontree.py`, `tests/test_leaseclock.py`, `tests/test_runcaps.py`, `tests/test_ctxstore_atomic.py`, `tests/test_dogfood_weave.py`; extend `tests/test_run_weave_negative_gate.py`.
- Link this plan from `references/atlas-weave.md` §9 (inventory_drift requirement).

---

### Task 1: Fuel/halting run-caps — `scripts/runcaps.py`

**Files:** Create `scripts/runcaps.py`; Test `tests/test_runcaps.py`.
**Interfaces:**
- Produces: `seed_caps(packet: dict, node_max: int = 12) -> dict` → `{"depth_max", "node_max", "gas", "token_budget"}`.

Pure. `node_max` from the arg (default 12, the locked K). `depth_max = 4` (locked). **`gas` MUST bound the run and be provisioned strictly above the worst-case dispatch count:** `gas = node_max * MAX_ATTEMPTS + node_max` (every node dispatched up to `MAX_ATTEMPTS` times, plus a margin for DECOMPOSE expands) — import `plandag.MAX_ATTEMPTS`. `token_budget` is a soft SIZING hint only (never gates): `token_budget = budget.risk_score(packet) * 50000` (import `budget`), floored at a constant `_MIN_TOKEN_BUDGET = 100000`. A malformed/empty packet degrades to the atlas-safe minimum (`node_max=1`-consistent caps still valid).

- [ ] Write failing tests: `seed_caps({...})` returns all four keys; `gas > node_max * plandag.MAX_ATTEMPTS`; `depth_max == 4`; `token_budget >= 100000`; a `{}` packet returns valid caps (no crash) with `token_budget == _MIN_TOKEN_BUDGET` when `risk_score` is minimal.
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(runcaps): fuel/halting caps + soft token budget provisioning`.

### Task 2: Per-test-id suite runner — `scripts/suiterun.py`

**Files:** Create `scripts/suiterun.py`; Test `tests/test_suiterun.py`.
**Interfaces:**
- Produces: `parse_junit(xml_text: str) -> dict[str, str]` and `run_suite(cmd: str, cwd: str, timeout_s: int = 1800) -> dict[str, str]`.

`parse_junit` is the PURE core (unit-tested without subprocess): parse a JUnit XML string (`<testsuite><testcase classname=.. name=..>` with optional child `<failure>`/`<error>`/`<skipped>`) → `{test_id: status}` where `test_id = f"{classname}::{name}"` (or just `name` if no classname) and `status` is exactly `"pass"` when the `<testcase>` has no failure/error/skipped child, else `"fail"`/`"error"`/`"skip"`. Use `xml.etree.ElementTree`. A malformed XML degrades to `{}` (empty → the caller's baseline_pass stays conservative). `run_suite` shells the cmd with `--junitxml` (append ` --junit-xml=<tmp>` for pytest, or accept a cmd that already writes JUnit), reads the file, delegates to `parse_junit`; any subprocess/timeout failure → `{}`. Green MUST be the literal `"pass"` (matches `differential.regressions`).

- [ ] Write failing tests for `parse_junit`: a 3-testcase XML (1 pass, 1 failure, 1 skipped) → `{"T::a": "pass", "T::b": "fail", "T::c": "skip"}`; a pass testcase yields EXACTLY `"pass"`; malformed XML → `{}`; a testcase with no classname → id is bare name.
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(suiterun): per-test-id JUnit runner emitting the "pass" token for differential`.

### Task 3: Union git-apply-on-worktree — `scripts/uniontree.py`

**Files:** Create `scripts/uniontree.py`; Test `tests/test_uniontree.py`.
**Interfaces:**
- Produces: `apply_union(baseline_sha: str, changes: list[dict], repo_cwd: str, session: str) -> dict` → `{"worktree": str|None, "applied": list[str], "failed": list[dict], "combined_diff": str}`.

`changes = [{"id", "diff"}]`. Create an isolated worktree at `baseline_sha` with a FLAT branch name `atlas__{session}__union` under `.atlas/{session}/union-worktree` via `git worktree add -b <branch> <path> <baseline_sha>`. `git apply` each change's `diff` (in list order) inside the worktree; a change whose apply exits non-zero is recorded in `failed` as `{"id", "reason"}` (a hidden overlap the pure `actual_conflicts` gate should ALSO have caught — this is the third net per §5). `applied` lists the ids that applied clean. `combined_diff = git diff <baseline_sha>` in the worktree after all applies. All git failures degrade safe (a failed `worktree add` → `worktree=None`, everything `failed`). Provide `cleanup(worktree, repo_cwd, session)` (`git worktree remove --force`). Uses `subprocess`; NO reliance on cwd (`git -C`).

- [ ] Write failing tests using a REAL temp git repo (init, commit a baseline, capture sha): two disjoint-file diffs both apply → `failed == []`, `combined_diff` contains both files; two same-file overlapping diffs → the second is in `failed`; a garbage diff → `failed`. Clean up worktrees in `tearDown`.
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(uniontree): union git-apply on an isolated worktree (the third disjointness net)`.

### Task 4: Lease/deadline clock + reaper — `scripts/leaseclock.py`

**Files:** Create `scripts/leaseclock.py`; Test `tests/test_leaseclock.py`.
**Interfaces:**
- Produces: `stamp(job_id: str, attempts: int, now: float, ttl_s: int = 1800) -> dict` → `{"token": f"{job_id}#{attempts}", "deadline": now + ttl_s}`; `expired(leases: dict, now: float) -> list[str]`.

Pure (INJECTED `now`, no wall-clock inside). `leases = {job_id: {"token", "deadline"}}`. `expired` returns the sorted `job_id`s whose `deadline <= now` (feeds `scheduler.reap_expired`). The `token` intentionally omits any timestamp so it does NOT rotate across a resume (honors the `resume.py` invariant); document that the SKILL discards post-resume in-flight receipts. `ttl_s = 1800` (the 30-min subagent timeout).

- [ ] Write failing tests: `stamp("a", 0, now=1000)` → token `"a#0"`, deadline `2800`; `expired({"a": {"deadline": 2800}, "b": {"deadline": 500}}, now=1000)` → `["b"]`; boundary `deadline == now` → expired; deterministic sorted output.
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(leaseclock): injected-clock lease deadlines + expiry for reap_expired`.

### Task 5: Atomic DAG write — `ctxstore.write_artifact_atomic`

**Files:** Modify `scripts/ctxstore.py`; Test `tests/test_ctxstore_atomic.py`.
**Interfaces:**
- Produces: `write_artifact_atomic(base, run_id, name, obj) -> Path` — serialize to a `.tmp` sibling then `os.replace` onto the target (atomic on POSIX), so a crash mid-write never leaves a torn `plan.dag.json`.

Match the existing `write_artifact` signature/behavior (JSON for `.json`), only adding atomicity. Do not change `write_artifact`.

- [ ] Write failing tests: round-trips via `read_artifact`; no `.tmp` file remains after a successful write; overwriting an existing artifact is atomic (the target is always either the old or the new full content).
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(ctxstore): atomic write_artifact_atomic for the plan-DAG`.

### Task 6: Combined-tree negative-gate teeth — `scripts/run_weave_negative_gate.py`

**Files:** Create `scripts/run_weave_negative_gate.py`; Test `tests/test_run_weave_negative_gate.py`.
**Interfaces:**
- Produces: `run_scenario(scenario: dict) -> dict` → `{"name", "expected", "actual", "matched"}`; `main()` returns exit 0 iff every scenario's gate outcome matches expectation.

Five PURE combined-tree red-team scenarios (no agents, no git — feed crafted inputs through the real pure cores and assert the gate BLOCKS, i.e. final verdict != `"OK"`):
1. **hidden-same-file-overlap** — two changes touching one file → `integrate.actual_conflicts` yields a CRITICAL → `integration_verdict` FAIL.
2. **combined-red-while-leaves-green** — `baseline_pass={"t1"}`, `combined={"t1":"fail"}` → `differential.regressions` → `integration_defects` HIGH → FAIL.
3. **cyclic-DAG** — a 2-cycle planner DAG → `planstage.validate_planner_dag` non-empty → `coerce_dag` degrades (assert the degrade, i.e. the cyclic DAG never ships).
4. **dropped-requirement** — a frozen criterion on no node → `verdict.coverage_partition` non-empty → aggregate FAIL.
5. **gas-exhausted-partial** — a DAG with an unresolved node + gas 0 → `scheduler.final_aggregate` FAIL and `run_status` UNVERIFIED.

Each scenario asserts `matched` (the gate produced the expected BLOCK). `main` prints a per-scenario line and exits non-zero on any mismatch (mirrors `run_negative_gate.py`'s contract).

- [ ] Write failing tests: each of the 5 scenarios `matched is True`; `main()` exit 0; a deliberately-broken scenario (expect BLOCK but feed a clean input) → `matched is False` (proves the harness can detect a rubber stamp).
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(weave-negative-gate): 5 combined-tree red-team scenarios with teeth`.

### Task 7: End-to-end deterministic dogfood harness — `scripts/dogfood_weave.py`

**Files:** Create `scripts/dogfood_weave.py`; Test `tests/test_dogfood_weave.py`.
**Interfaces:**
- Produces: `dogfood(repo_cwd, packet, scripted_nodes) -> dict` → `{"verdict", "run_status", "nodes", "waves", "gas_spent", "conflicts", "regressions"}`.

Runs the FULL flow on a REAL temp git repo with SCRIPTED coder outputs (no live agents): `runcaps.seed_caps` → `planstage.coerce_dag` (a provided multi-node planner DAG or degrade) → `scheduler.seed_jobs` → trampoline `[scheduler.plan_wave(dag, free_mb=8192) → scheduler.dispatch_wave → (apply each dispatched job's SCRIPTED diff via `uniontree` into per-node worktrees, run its suite via `suiterun`, build its node verdict via the real `verdict` harness pieces) → scheduler.apply_receipt]` until `scheduler.is_terminated` → `uniontree.apply_union` of all node diffs → `integrate.actual_conflicts` + `suiterun` on the union + `differential.regressions` → `integrate.integration_verdict` → `scheduler.final_aggregate` (folding `verdict.coverage_partition`) → `scheduler.run_status`.

- [ ] Write failing tests (real temp git repo, scripted diffs as fixtures):
  - **clean multi-file change** (2 disjoint nodes, both suites green, union green) → `verdict == "OK"`, `run_status == "OK"`, `conflicts == []`, `regressions == []`.
  - **hidden overlap** (2 nodes editing the same file) → `verdict == "FAIL"` (via `actual_conflicts`).
  - **combined regression** (each node green alone, union red) → `verdict == "FAIL"` (via `differential`).
  - **1-node degrade == atlas** — a `single_node_dag` run of one node → same OK verdict a single-change atlas run would produce (byte-identical schedule reduces to INIT→OUTPUT).
- [ ] Run → FAIL. Implement. Run → PASS. Commit `feat(dogfood): deterministic end-to-end ATLAS-WEAVE proof on a real repo`.

### Task 8: Outer SKILL prose + integration-critic persona + graph-aware resume

**Files:** Create `skills/atlas-weave/SKILL.md`, `agents/integration-critic.md`; Modify `skills/atlas-resume/SKILL.md`.
**Interfaces:** prose (reviewed against the pure API, not unit-tested). No code — but every referenced function/artifact name MUST match the real modules.

- `skills/atlas-weave/SKILL.md`: the outer meta-machine. Stages `DECOMPOSED → BUDGETED → SCHEDULE* → INTEGRATE → AGGREGATE → OUTPUT`. Documents: dispatch the planner (`agents/planner.md`) → `coerce_dag`/`validate_planner_dag` (degrade-to-atlas on failure) → `runcaps.seed_caps` → `seed_jobs` → the trampoline (`plan_wave` with the `free -m` sample → `dispatch_wave` → spawn each node as a hierarchical `${SESSION}/tasks/<id>` inner-atlas sub-run → `leaseclock.stamp` → collect thin receipts → `apply_receipt`/`reap_expired`) → `uniontree.apply_union` → `integrate`/`differential`/`integration_verdict` (seam wave via `agents/integration-critic.md`) → `final_aggregate` (fold `coverage_partition`) → `run_status` → OUTPUT gate. MUST state: ≤3 concurrent agents, builds-in-pool, degrade-to-atlas on a 1-node DAG, discard post-resume in-flight receipts. Include a **"Live dogfood (manual, in Kimi)"** section: how to run a real multi-file change and record the Q/T delta vs single-shot atlas, honestly noting this build shipped the deterministic proof (`dogfood_weave`) and the live delta is a manual measurement.
- `agents/integration-critic.md`: the seam-critic persona (scoped to touched exported symbols across the union) → critic-schema defect JSON. Mirror the existing critic personas' shape.
- `skills/atlas-resume/SKILL.md`: rewrite to be graph-aware — scan `.atlas/*`, call `resume.select_graph_run` (skip `is_task_subrun`), `resume.resume(dag)` to reset orphaned RUNNING→PENDING, reset dirty worktrees, re-derive the frontier; discard in-flight receipts (lease no-rotation). Keep the single-change fallback.

- [ ] Author the three prose files; verify every referenced symbol/artifact exists (grep the modules). Commit `feat(atlas-weave): outer SKILL loop + integration-critic + graph-aware resume`.

### Task 9: Green the full gate + wire the plan link

**Files:** whole repo; `references/atlas-weave.md` §9.
- [ ] Link this plan from `references/atlas-weave.md` §9 (so inventory_drift stays green).
- [ ] `make ci` → all green (unit suite OK, inventory in sync, shell OK).
- [ ] Commit any fixups `chore(atlas-weave): P12 green under make ci`.

## Self-Review

- Coverage: every §9 P12 deliverable maps to a task — fuel/halting caps (T1), soft token_budget (T1), negative-gate teeth for all 5 scenarios (T6), dogfood (T7); plus the hands the dogfood requires (T2/T3/T4/T5) and the orchestrator prose (T8).
- The pure cores are unchanged; P12 only calls them. The one place a false green could hide (the union gate) is netted three ways (declared scope, `actual_conflicts` on actual touched files, real `git apply`) exactly per §5.
- Honesty: the live Q/T delta is not fabricated — T7 ships a deterministic composition proof; T8 documents the manual live run.
