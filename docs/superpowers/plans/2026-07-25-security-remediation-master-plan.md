# Security Remediation — Master Plan (executable handoff)

> **You are picking this up cold.** This document is the complete instruction set for closing nineteen
> confirmed security findings in shipped kimi-atlas v1.5.1. It assumes you have no prior context. Read it
> top to bottom before touching anything. Every claim in it was proven by execution; every fix that was
> *proposed and refuted* is recorded so you do not re-propose it.

**Source of truth for the findings:** [`docs/superpowers/specs/2026-07-25-security-audit-remediation-design.md`](../specs/2026-07-25-security-audit-remediation-design.md). Read it second.

**Baseline:** `main` = `a99101b` (v1.5.1) · `make ci` EXIT 0 · 1327 tests · 34 tracked docs.

---

## 0. What this project is, in one screen

**kimi-atlas** is a many-agent, quality-calibrated code-review orchestrator plugin for the Kimi Code CLI
(public MIT repo: `github.com/null0xxx/kimi-atlas`; installs to `~/.kimi-code/plugins/managed/kimi-atlas`).

- `skills/atlas/SKILL.md` is **not documentation — it is a program an LLM executes.** Its ambiguities are
  bugs and its contradictions are exploitable. It drives
  `INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT`.
- It reviews an **untrusted TARGET repository** and, by design, runs that repository's build, test suite
  and linter. That is the most dangerous thing it does.
- Verification is a 6-lens harness: a deterministic floor (`runcheck`, `astlens`, `syntaxlens`, `quality`,
  `reqcoverage`, `pathcheck`, `sast`, `lintlens`) plus three isolated adversarial judgment critics
  (CORRECTNESS / CODE-QUALITY / SECURITY).
- **`verdict.merge` / `verdict.gate` are pure functions. No LLM ever computes pass/fail.**
  `scripts/verdict.py` is **FROZEN**: read it, never edit it, and never propose a change whose correctness
  depends on editing it.
- Durable run state lives in `.atlas/<run_id>/` (gitignored in *this* repo, **not** in a target's).

**The nine invariants.** Every task below is rejected if it breaks one:

1. THE ONE GUARANTEE — never report a green it cannot substantiate.
2. The pure gate — `verdict.merge`/`gate` pure and FROZEN.
3. The deterministic floor is never weakened; the P3 advisory firewall holds (`lintlens_advisory` must
   never reach `script_defects` / `gate_results`).
4. COMPLETION INVARIANT — `INIT → OUTPUT` is one uninterrupted run with exactly three sanctioned
   turn-ending pauses (CLARIFY `AskUserQuestion`, pre-CODE approval, OUTPUT gate) plus the one sanctioned
   terminal abort (`ATLAS-PRECONDITION-FAILED`).
5. `ctxstore.advance` per transition and it must RETURN before the stage counts as done; `log.jsonl`
   append-only; the refine counter monotonic.
6. Never auto-apply; headless isolates.
7. SAFE-2 framing on every untrusted blob (`scripts/safewrap.py` is the single canonical wrapper).
8. Compaction survival via the on-disk ledger.
9. Critic isolation (F6 anti-anchoring).

**Conventions any edit must match** — the full list is in `AGENTS.md`; the ones that bite most often:
stdlib-only Python 3.12, `from __future__ import annotations`, pure cores + thin I/O "hands", stdlib
`unittest` only, `tests/test_<module>.py` per `scripts/<module>.py`, tempfile fixture trees, behaviour AND
failure-path assertions, backticked path citations in changed text must exist on disk, new `.md` must be
lowercase kebab-case AND markdown-linked from `references/*.md` or `README.md`, and if the tracked-doc
count changes you must update `AGENTS.md` (`tests/test_tracked_docs_count.py` enforces it).

---

## 1. The mandate

Nineteen confirmed findings — 6 CRITICAL, 5 HIGH, 8 MEDIUM — must be closed. They were produced by six
independent security lenses that were required to prove everything **by execution**, then filtered by three
adversarial verifiers instructed to **refute by default**. What is listed here is what survived refutation.

### The one-sentence diagnosis — internalise this, it predicts the next bug

> **A value the gate depends on is read from a place the code under review can write, and nothing checks
> that the plugin itself put it there.**

The `sys.path` hijack closed in v1.5.1 was *one instance*. The remaining instances are the `.atlas/` ledger,
`merged_critic.json`, the evidence diff, the critic artifacts, and the plugin's own modules.

### The governing rule for every fix

> **A fix that manufactures a RED on an honest repository is worse than the bug it closes.**

It fires on every run instead of only on an attacked one. Two of the confirmed findings (S9, S15) are
already instances of exactly that failure. **R3 is the change most at risk of becoming the next one** —
treat its false-positive behaviour as the primary acceptance criterion, not an afterthought.

---

## 2. DO NOT re-propose these — measured and refuted

Each of these looks obviously right and is wrong. They cost real time to disprove; do not spend it again.

| Rejected fix | Why |
|---|---|
| Strip `PYTHONPATH` in `proccap.target_env` | Closes nothing. Measured: the plugin root is writable by the target's build regardless, and overwriting `scripts/verdict.py` directly is simpler than planting `sitecustomize.py`. v1.5.1's deliberate scope note was **correct**. |
| Make `target_env` an allowlist | Measured breakages: `SSH_AUTH_SOCK` (private git deps via `cargo`/`go mod`/`npm` on `git+ssh://`), `NPM_TOKEN`/`CARGO_REGISTRIES_*`, corporate `HTTP_PROXY`/`NO_PROXY`/`NODE_EXTRA_CA_CERTS`/`REQUESTS_CA_BUNDLE`, `JAVA_HOME`/`GRADLE_USER_HOME`, and `XDG_RUNTIME_DIR`/`DBUS_SESSION_BUS_ADDRESS` which playwright/cypress/electron suites need. Only a narrow **denylist of env-only credential patterns** is proportionate. |
| `unshare -n` for `runcheck` | Would false-RED every build that fetches dependencies — `npm test` on a cold `node_modules`, `cargo test` without a vendored registry, any maven/gradle build. `lintlens` can afford it only because it parses one file. |
| Treat `\|\| true` / `-`-prefixed make recipes as an exit-masking hole | **Refuted.** `runsignal.count` folds *any tag passed>0 AND no tag failed*; both forms measurably fail CLOSED (`test_count=0, new_tests_collected=False, green=False`). |
| `TasksMax=256` on `runcheck`'s cgroup wrapper (lintlens parity) | Would kill `make -j$(nproc)` on a large C++ target and `pytest-xdist -n auto` on a many-core host. If you add a fork bound, make it generous (≥2048) and say why. |
| Drop `--metrics off` from `sast.py` to make `--config auto` work | Reverses flaw-register fix FIX.3 (semgrep telemetry egress). Use `--config p/default` instead — verified to keep `--metrics off` **and** find the canonical `subprocess-shell-true` ERROR→HIGH. |

Two more corrections to your priors: `git clone` transfers **neither** `.git/config` **nor** `.git/hooks`, so
the git-config execution findings (S12) require the target to arrive as a directory tree, not via clone; and
on any **non-root** install `proccap` selects the `ulimit` backend, not cgroup, which makes several
cgroup-only findings unreachable there.

---

## 3. The process you must follow

This process has caught 4 CRITICALs in one plan, 5 in another, and 2 in a third — **including outright bugs
in the proposing agent's own code, three separate times.** Do not skip a stage.

```
spec → per-release plan → adversarial plan-challenge → SDD build → whole-branch review → merge → release
```

- **Per-release plan.** Write it to `docs/superpowers/plans/YYYY-MM-DD-<name>.md`. Bite-sized TDD steps:
  write the failing test → run it and record the exact failure → implement → run → mutation-check → commit.
- **Adversarial plan-challenge (mandatory).** Before building, dispatch a reviewer whose job is to ATTACK
  the plan and probe the real repo. Fold its verified findings into the plan and commit that fold as its
  own commit. The task specs below contain proposed code — **assume it has bugs**; it has not been executed.
- **SDD build.** One fresh implementer per task, then a task review (spec compliance AND code quality),
  then a fix wave on Critical/Important. Append every task outcome to `.superpowers/sdd/progress.md` —
  that ledger is the recovery map if your context is lost.
- **Whole-branch review** before merge, on the most capable model available.
- Commit with `git commit -F <file>`. If you are on `main`, branch first.

**Mutation-testing harness (this project has been bitten five times).** Always run mutants with
`PYTHONDONTWRITEBYTECODE=1` and a purged `__pycache__` — a size-neutral mutation otherwise runs against
stale bytecode and looks like a false survivor. When running a copied module, `cwd=<copy>` and assert
`mod.__file__` is inside the copy: for `python3 -m`, `sys.path[0]` is the CWD and **shadows** `PYTHONPATH`.

**Watch for vacuous tests.** Five times a test here has asserted something by iterating the very constant it
was meant to pin — it shrinks with the mutation and cannot fail. And twice a pin has asserted only that a
call *happens*, not what it is called *with*, or only that code *exists*, not what it *does*. Every pin you
write must be killed by a mutation you actually ran.

---

## 4. Release v1.5.2 — what damages an ordinary, non-attacked run

**Branch:** `fix/security-v152` off `main`. **Every task ends with `make ci` EXIT 0.**

These are ranked by (probability on an honest run) × (damage), which is deliberately *not* the adversarial
ranking. S7 fires on 100% of runs. S3's `["."]` case is the documented headless default. S4 is an ordinary
LLM failure mode, not an attack.

---

### Task 1 — S7: the SECURITY deterministic floor has never fired

**Files:** modify `scripts/sast.py` (`:193` argv, `:18-24` egress docstring, `:175` docstring); modify
`tests/test_sast.py`.

**The defect, reproduced:**

```
$ semgrep --config auto --metrics off --json --quiet -- src
[ERROR]: Cannot create auto config when metrics are off.   EXIT=2
$ python3 -c "from scripts import sast; print(sast.scan(['src'], '.'))"
[]                                   # fail-open, silent, on 100% of runs
$ semgrep --config auto --json --quiet -- src
results: 1   python.lang.security.audit.subprocess-shell-true
```

The two flags are mutually exclusive. This is a **regression introduced by our own flaw-register fix FIX.3**
(`docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md`, "Task FIX.3"), which
changed a working argv into this one. `README.md`, `references/rubric.md` and `skills/atlas/SKILL.md:430-436`
all promise that a mechanically-detectable vulnerability "blocks the gate regardless of whether the critic
notices it". It never blocks.

**Why no test caught it:** every SAST test mocks the subprocess boundary — including FIX.3's own
`TestSastMetricsOff`, which is a pure argv assertion with `subprocess.run` patched. It is *structurally
incapable* of observing that two flags conflict. No `make` target or CI lane runs the real binary.

- [ ] **Step 1 — write the failing integration test.** In `tests/test_sast.py`, add a class that skips
      unless `sast.semgrep_path()` resolves, writes a fixture containing `subprocess.run(cmd, shell=True)`,
      calls the **real** `sast.scan([...], tmpdir)`, and asserts at least one defect with
      `severity in ("CRITICAL", "HIGH")` and `category == "SECURITY"`.
      This test must FAIL at HEAD. Record its exact output.
- [ ] **Step 2 — run it, confirm RED**, and record that the failure is an empty list, not an exception
      (proving the fail-open path).
- [ ] **Step 3 — fix the argv.** `scripts/sast.py:193`:
      `argv = [executable, "--config", "p/default", "--metrics", "off", "--json", "--quiet", "--", *paths]`
      Keep `--metrics off` — dropping it reverses FIX.3.
- [ ] **Step 4 — correct both docstrings.** `:175` currently describes an argv the code does not run.
      `:18-24`'s egress paragraph must say "a pinned registry ruleset" rather than `--config auto`, and must
      state honestly that rule *fetch* still reaches the network on first use.
- [ ] **Step 5 — run the suite.** The new test passes; the existing 30 mocked tests still pass; the FIX.3
      argv pin must be updated to the new literal **and must still fail if `--metrics off` is removed**.
- [ ] **Step 6 — mutation check.** Revert the argv to `auto`; the new integration test must FAIL. Remove
      `--metrics off`; the FIX.3 pin must FAIL. Restore; green.
- [ ] **Step 7 — `make ci`, commit.**

**Open question for the plan-challenge:** `p/default` is a *registry* ruleset, so first use fetches over the
network and coverage differs from `auto`'s per-language selection. A vendored offline ruleset under
`references/semgrep-rules/` is strictly better — no egress, deterministic, no first-run latency — but is a
larger change. The challenge should decide whether v1.5.2 ships `p/default` with vendoring deferred, and say
so explicitly in the CHANGELOG either way.

---

### Task 2 — S3: the reviewed tree must equal the executed tree (structural change R3)

**Files:** modify `scripts/difftool.py`, `scripts/floorsynth.py`, `skills/atlas/SKILL.md` (Step 1 and
Step 4+5); modify `tests/test_difftool.py`, `tests/test_floorsynth.py`.

**Two distinct defects, both reproduced.**

*(a) The scope-restricted diff is the only evidence channel.* `difftool.capture(baseline, scope_paths,
review_root)` feeds **every** lens, but the coder's real blast radius is `review_root`. A change outside
`scope_paths` — including deleting the very test that would catch the bug — is invisible to all six lenses
while `runcheck` still runs the whole tree. Verified: a real bug in `src/` plus the covering test deleted
from `tests/` (out of scope) → `✅ VERIFIED`.

The designed backstop cannot fire: `reqcoverage`'s scope-creep lens derives its changed paths from the same
already-restricted diff. It is **dead code by construction** — the positive control confirms the lens itself
works when fed an unrestricted diff.

*(b) `scope_paths = ["."]` drops every tracked modification.* `difftool._tracked_at` (`:57-59`) runs
`git cat-file -e <baseline>:<path>`, and git rejects the pathspec `.`:

```
fatal: path '.' exists on disk, but not in '09da04f…'    rc=128
```

Measured on a fixture with one corrupted tracked file and one new untracked file:

```
capture(scope=["."])   -> 146 bytes: ONLY the new file
empty_diff_defect      -> []          # no CRITICAL; the diff "looks real"
capture(scope=["src"]) -> 321 bytes: BOTH, including the corruption
```

`["."]` is the **documented headless CLARIFY default** (`skills/atlas/SKILL.md:225`), so this fires on
ordinary unattended runs, and one new file is enough to suppress the `empty-diff` CRITICAL.

- [ ] **Step 1 — failing test for (b).** In `tests/test_difftool.py`: a git fixture with a tracked file
      modified and an untracked file added; assert `capture(sha, ["."], cwd)` contains **both**. RED today.
- [ ] **Step 2 — fix `_tracked_at`.** Normalise the pathspec: `.` and `""` mean the whole tree, for which
      `git cat-file -e <sha>:` returns 0 while `<sha>:.` returns 128. Handle `./`-prefixed paths too.
      Do not change behaviour for any other pathspec — pin that with a differential over the existing tests.
- [ ] **Step 3 — failing test for (a).** In `tests/test_floorsynth.py`, pin a new pure function
      `out_of_scope_defects(full_diff: str, scope_paths: list[str]) -> list[dict]` returning one defect per
      file present in `full_diff` but outside `scope_paths`.
      **Contract, decided deliberately:** `severity: "HIGH"`, `category: "CORRECTNESS"`, one defect per path.
      HIGH rather than CRITICAL because the legitimate case exists; HIGH already blocks **and** fires V7.
      Exclude `.atlas/` from consideration. The `fix` string must be coder-actionable and must **not** be
      added to `ORCHESTRATOR_DEFECT_IDS`.
- [ ] **Step 4 — implement it**, pure, no I/O, matching `floorsynth`'s existing style.
- [ ] **Step 5 — add `difftool.capture_full(baseline_sha, cwd)`** — the same capture with no pathspec
      restriction. Test it against the same fixtures.
- [ ] **Step 6 — wire the SKILL.** Step 1 persists `diff.full.patch` alongside `diff.patch`. Step 4+5 adds
      one `script_defects += floorsynth.out_of_scope_defects(full_diff, scope_paths)` line.
      **Pass only the path list downstream, never the full bytes** — token cost must stay O(files), not
      O(bytes). `diff.full.patch` must never enter a critic packet.
- [ ] **Step 7 — the false-positive gate (this is the acceptance criterion, not a formality).** Build three
      honest fixtures and prove none of them goes RED: (i) a legitimate cross-cutting edit to a shared
      `conftest.py` outside `scope_paths` — this one *should* fire, and you must confirm the message tells
      the human why and that one refine pass resolves it; (ii) a run whose `scope_paths` is `["."]`, where
      nothing can be out of scope; (iii) an ATLAS-WEAVE node whose `review_root` is its own worktree —
      the full capture must be scoped to that worktree, or every sibling node's edits are flagged.
      **If (iii) fires, the wiring is wrong.** Fix it before proceeding.
- [ ] **Step 8 — mutation check, `make ci`, commit.**

---

### Task 3 — S4: validate a critic's judgment where it is produced (structural change R4, part 1)

**Files:** modify `skills/atlas/SKILL.md` (Step 3.4, around `:602`), `scripts/floorsynth.py`; modify
`tests/test_floorsynth.py`.

**The defect.** `verdict.merge` recomputes `verdict` from `defects[]` and **discards the critic's own
`verdict` field**; `dimensions` is written and — verified by grepping every consumer — read by nothing that
decides anything. `quality.enforce_critic_schema` is applied only to the *merged* shape, which `merge`
constructs to satisfy every rule by definition, so most of that validator is structurally unreachable.

Verified end-to-end over a green deterministic evidence set:

| critic shape | merged verdict | schema_errors | printed |
|---|---|---|---|
| 3× `verdict:"FAIL"`, `defects:[]` | `OK` | `[]` | **✅ VERIFIED** |
| 3× all six dimensions `"no"` | `OK` | `[]` | **✅ VERIFIED** |
| defects under a drifted key (`findings`) | `OK` | `[]` | **✅ VERIFIED** |
| duplicate `"defects"` JSON key | `OK` | `[]` | **✅ VERIFIED** |
| control: one real CRITICAL | `FAIL` | `[]` | ⚠️ UNVERIFIED |

`enforce_critic_schema` catches the first shape **outright** — it is simply never called on an individual
critic. This is an ordinary LLM failure mode: a critic that objects in prose, or files its objection under
the wrong key, is silently read as a clean lens.

- [ ] **Step 1 — failing tests.** Pin all four shapes end-to-end: each must end **UNVERIFIED**. Include the
      control (one real CRITICAL) so the suite cannot pass by blocking everything.
- [ ] **Step 2 — SKILL Step 3.4:** run `quality.enforce_critic_schema(<raw critic>)` on each returned JSON
      **before** `ctxstore.write_artifact`, and re-dispatch that critic **once** quoting the exact errors.
- [ ] **Step 3 — `floorsynth.dimension_dissent_defects(raw_critics) -> list[dict]`:** one blocking defect per
      critic that reports `dimensions[d] == "no"` or `verdict == "FAIL"` **without** a corresponding blocking
      defect. Category = that lens's own dimension (never `"SCHEMA"` — `quality.enforce_critic_schema:78-82`
      rejects any category outside `rubric.DIMENSIONS`, and the existing `critic-schema` defect only works
      because it is appended *after* validation). Add its id to `ORCHESTRATOR_DEFECT_IDS` and give its `fix`
      the `"ORCHESTRATOR ACTION — not a coder task:"` prefix the existing audit pins.
- [ ] **Step 4 — duplicate-key shape.** Decide and document: `json.loads` is last-key-wins, so this shape
      collapses into "critic said FAIL with empty defects" and Step 3 already closes it. Pin that it does.
- [ ] **Step 5 — mutation check, `make ci`, commit.**

---

### Task 4 — S5 + S10: artifact currency and stage order (structural change R2, part 1)

**Files:** modify `scripts/floorsynth.py`, `skills/atlas/SKILL.md` (Step 3.4, Step 4+5, REFINE); modify
`tests/test_floorsynth.py`.

**S5 — stale critic artifacts.** Critic artifact names are pass-invariant and REFINE re-enters
CODED→VERIFIED in the same run dir. `floorsynth.critics_missing_defects` (`:176`) tests **file existence,
not freshness**. Verified: on pass 2 the security critic returns non-JSON twice (the SKILL's own documented
degradation path, so no orchestrator misbehaviour is required), nothing is persisted, pass 1's clean
artifact is still on disk → `critics_loaded=3/3`, `critic-missing: []`, `gate OK`, `✅ VERIFIED` on code that
lens never saw. Asymmetric: a stale **red** artifact keeps the run red; only a stale **clean** one is a false
green.

**S10 — no stage-order invariant.** `ctxstore.advance` is a permissive recorder and
`verdict.missing_stages` is pure set membership, therefore order-blind. Verified: a ledger reading
`[…,'VERIFIED','REFINE','CODED','OUTPUT']` — the tree mutated *after* verification — yields
`missing_stages == []` and prints `✅` from the stale merged critic. The pure core to detect it **already
exists and is deliberately unwired**: `fsm.legal_transition(CODED → OUTPUT)` is `False`.

- [ ] **Step 1 — failing test, S5.** Reproduce the two-pass scenario against a real `ctxstore` run dir and
      assert the run ends UNVERIFIED. Also pin the asymmetry: a stale **red** artifact must still block
      (do not "fix" it into passing).
- [ ] **Step 2 — stamp the artifacts.** Step 3.4 writes each critic artifact with a `pass` field equal to
      `ctxstore.get_refine_passes(...)` at write time. Extend `critics_missing_defects` (or add a sibling)
      to require the stamp to match the current pass, synthesizing the same blocking defect shape when it
      does not. **Back-compat:** an artifact with no `pass` field must be treated as stale, not as pass 0.
- [ ] **Step 3 — failing test, S10.** Pin `floorsynth.stale_verdict_defects(log_records) -> list[dict]`:
      a blocking `DOES-IT-RUN` / CRITICAL defect when the last `CODED` ledger entry post-dates the last
      `VERIFIED` entry, or when any adjacent pair fails `fsm.legal_transition`.
- [ ] **Step 4 — implement it**, pure, folding over `ctxstore._iter_log_records`. **Non-raising** — it
      records a defect; it must not turn `advance` into a hard error (that would break resume-after-
      compaction, which legitimately jumps stages).
- [ ] **Step 5 — wire it into the OUTPUT block** so it is folded into the merged critic *before*
      `final_status` is computed.
- [ ] **Step 6 — regression guard.** Prove a legitimate REFINE run (`VERIFIED → REFINE → CODED → VERIFIED →
      OUTPUT`) still passes. This is the false-RED risk for this task.
- [ ] **Step 7 — mutation check, `make ci`, commit.**

---

### Task 5 — S9 + S18: `timeout_s` must actually bound the run

**Files:** modify `scripts/proccap.py` (`:342` and the `_launch_and_wait` docstring at `:307-309`),
`scripts/suiterun.py` (`:114`, `:140`); modify `tests/test_proccap.py`, `tests/test_suiterun.py`.

**The defect.** `proccap.py:342` drains with a bare `proc.communicate()` — **no timeout** — *after*
`_kill_process_group`. A descendant that called `setsid` is outside the group, keeps the inherited pipe
open, and the drain blocks on it. Measured: **45.1 s against a 3 s bound**; `sleep infinity` makes it
unbounded. With pipes closed instead, the process and its transient systemd scope both outlive the run.

The docstring's claim that "the group's pipe write-ends are then closed, so the post-kill drain returns
promptly" is **false** for any process that left the group.

**This fires on honest repos** — any build that daemonises: a dev server, a docker/containerd client,
`npm start &`, a fixture that leaves a broker running. No hostility required.

`suiterun` has the same family of defect from the other direction: `subprocess.run(shell=True, timeout=…)`
kills a single pid with no memory cap, so two *plain* background children survived (no `setsid` needed) —
the shape of `pytest-xdist`, `make -j`, `npm`. It does **not** hang, because CPython waits on the process
rather than the pipes; do not merge the two symptoms.

- [ ] **Step 1 — failing test.** A fixture whose command backgrounds a `setsid` descendant holding the
      inherited pipe; assert `runcheck.run(..., timeout_s=3)` returns within a small multiple of 3 s.
      Measure wall clock in the assertion. RED today (~45 s).
- [ ] **Step 2 — bound the drain.** Replace the bare `communicate()` with `communicate(timeout=<grace>)`
      inside a `try`, falling back to closing `proc.stdout`/`proc.stderr`, `proc.wait(timeout=…)`, and
      returning whatever was drained. **Use a 5–10 s grace, not 0** — a legitimately slow-flushing runner
      must not have its output truncated.
- [ ] **Step 3 — tear down the unit, not just the group.** On the cgroup backend, stop the transient scope
      (read `cgroup.procs` and SIGKILL every pid in it, or launch with `--unit=` and `systemctl stop`) so a
      `setsid` descendant cannot survive. Guard it so a host without systemd degrades to today's behaviour.
- [ ] **Step 4 — correct the docstring.** It currently asserts a property the code does not have.
- [ ] **Step 5 — route `suiterun` through `proccap._launch_and_wait`** so it inherits the process group,
      the group kill and the memory cap. Keep `target_env()` — that seam is correct and must not regress.
- [ ] **Step 6 — regression guard.** A normal build that exits cleanly must be byte-identical in `stdout`,
      `stderr`, `returncode` and `timed_out` before and after. The changed path is only reached on timeout,
      where the run is already RED; prove that.
- [ ] **Step 7 — mutation check, `make ci`, commit.**

---

### Task 6 — S14 + E3: stop shipping a constant as evidence, and fix the rubric contradiction

**Files:** modify `scripts/runcheck.py` (`:291`), `skills/atlas/SKILL.md:586`,
`agents/correctness-critic.md:61`, `references/rubric.md:193-194`.

**S14.** `runcheck.run` hard-codes `"revert_red": False`. Grep confirms no orchestrator path ever computes
it; the only other mentions are a docstring, rubric prose, and `run_negative_gate.py`'s printout. Yet
`skills/atlas/SKILL.md:586` hands `revert_red` to the CORRECTNESS critic **as evidence**, and
`agents/correctness-critic.md:61` instructs that critic to *"Cross-check `test_count` / `revert_red`: no
differential signal is suspicious"* — i.e. to reason about a constant.

Decide one of two, and say which in the CHANGELOG: **(a)** actually compute it (run the frozen `verify_cmd`
on the reverted tree and require RED — this is the only control that detects a recipe which always prints
green, and it also mitigates S19), or **(b)** remove it from the critic packet and the role file until it has
a producer. **(b) is the correct v1.5.2 scope**; (a) belongs in its own release with its own cost analysis
(it doubles build time).

**E3.** `references/rubric.md:193` narrows V7 to "any defect **a critic emits**". That contradicts the
shipped program (`skills/atlas/SKILL.md:692` filters on category with **no origin filter**), contradicts the
SKILL's own gloss at `:669-672` ("critic + `pathcheck`"), and would silently delete the reason
`floorsynth.empty_diff_defect` was deliberately given `category: CORRECTNESS`.
**Adjudicated: `:53-54` and `:98` are right; `:193` is wrong.** Amend `:193-194` to name the deterministic
floor explicitly (`pathcheck`, `sast`, `empty-diff`) and cite `skills/atlas/SKILL.md:692`.

- [ ] **Step 1** — pin that no critic packet field lacks a producer (a test enumerating the Step-3 packet
      fields against the modules that emit them).
- [ ] **Step 2** — apply (b); update the role file sentence in the same commit.
- [ ] **Step 3** — amend `references/rubric.md:193-194`; pin the amendment so it cannot silently re-narrow.
- [ ] **Step 4** — `make ci`, commit.

---

### v1.5.2 release checklist

- [ ] Whole-branch review on the most capable model, with an explicit instruction to hunt for a mutant of
      the branch's own new code that passes the suite while reopening a false green. **This has succeeded
      three releases running; budget for it.**
- [ ] Version truth 1.5.1 → 1.5.2 across `.kimi-plugin/plugin.json`, `README.md` (install pin), `AGENTS.md`
      (×3 including the tracked-doc count), `references/system-map.md`, `CHANGELOG.md`.
- [ ] `make ci` EXIT 0. Merge to `main`, push, `git tag -a v1.5.2`, `gh release create … --latest`.
- [ ] Confirm both CI lanes green, then **reinstall the plugin** (`/plugins install …`) — an old managed
      copy silently serves stale code; this has already caught the project once.

---

## 5. Release v1.5.3 — the adversarial surface

Larger and riskier than v1.5.2, because **the resume path this project depends on must keep working.**
Write its own plan document; the task specs below are the input to that plan, not a substitute for it.

**R1 — the run directory becomes plugin-owned and integrity-checked (closes S2, half of S1, half of S5).**
`ctxstore.init_run` writes `<run_dir>/.atlas-owner` carrying a per-**installation** nonce plus the plugin
version. Both resume discovery sites — `skills/atlas/SKILL.md:135` and `skills/atlas-resume/SKILL.md` step
3s — skip any run dir without a token this installation issued: a foreign ledger is **reported to the human
and ignored**, never adopted. Then wire the containment layer that already ships unused: replace every
`ctxstore.write_artifact` call site with `write_artifact_confined`, and call `valid_run_id` in
`init_run`/`advance`/`_run_dir`.

*Framing that matters:* implement it as **"resume only what we can prove we wrote"**, never as "refuse
anything that looks foreign" — the first is strictly narrower and cannot silently drop a legitimate run.
Per-installation (not per-process) so a compacted or crashed session in the same directory resumes normally.
Known risks to design for: a run resumed after a plugin upgrade (persist the nonce in `${KIMI_CODE_HOME}`
and version-tolerate it); a run dir legitimately copied between machines; and the ATLAS-WEAVE
`${SESSION}/tasks/<id>` sub-runs, which are created by a different dispatch and must be issued tokens by the
same authority (`resume.is_task_subrun` already special-cases them — verify both paths).
Also check `write_artifact_confined` refuses **any** symlinked component before switching the headless path
over: `.atlas/<run_id>/worktree` is a real `git worktree`. And note the two write hands' serialisation
**diverges** (sort_keys; `True`→`'true'`; `None`→`'null'`; tuple→JSON array; set→`TypeError`; 0600 vs 0644) —
they are not interchangeable.

**R2 — the verdict is recomputed at the point of printing (closes S1, completes S10).**
The printed status is `final_status(merged, budget_exhausted)` read from `merged_critic.json`;
`gate_results.json` is **write-only** (grep confirms). Verified: a `Makefile` whose `test:` target
backgrounds a `sleep 4` that rewrites the artifact turned five blocking defects — `runcheck`, `empty-diff`
and three `critic-missing` — into a printed `✅ VERIFIED`. **No attacker ledger and no symlink required:
`runcheck` executes the target's own build at VERIFIED, inside the writable root.**
Fix: OUTPUT re-reads `det_evidence.json` + `critic_*.json` at that instant, recomputes `verdict.gate`, and
requires agreement with `final_status`. Disagreement, a missing artifact, or an artifact post-dating the last
`CODED` ledger entry ⇒ **UNVERIFIED**. **Fail closed to a red label, never to a crash** — a crash writes no
OUTPUT ledger entry and leaves the run resumable, which is worse.

**R4 part 2 — fence the Step-3 critic packet (closes S8).** `SKILL.md:95-102` names the `runcheck` tails as
untrusted **by name**, and the REFINE→coder path fences exactly those bytes via
`safewrap.refine_feedback_block`. The Step-3 critic packet (`:586`) hands the same bytes to the CORRECTNESS
critic raw, and `agents/correctness-critic.md:35` scopes its own SAFE-2 rule to "the diff and any file you
open" — the tails are neither. Two verified payoffs: **suppression** (a compliant critic returns a clean
lens) and **escalation** — a critic-authored `fix` string reaches the `Write`/`Edit`-capable coder in
`coder_redispatch_packet`'s trusted `fix_instructions`, filtered only against five fixed ids:
`injected id 'C7' filtered? False`.
Fix: `safewrap` the packet; route every **critic-authored** `fix` through `wrap_untrusted` so only
`floorsynth`-synthesized fixes stay trusted; add the program-output clause from `agents/elite-coder.md:61-68`
verbatim to all three critic role files. Rewrite `tests/test_safe2_enumeration.py` from a substring pin into
a real `(channel, producer, consumer)` enumeration — today it is green while the critic path is bare.

**Also in v1.5.3:** `-S` alongside `PYTHONSAFEPATH=1` on the plugin's own invocations (closes the
`sitecustomize`/`usercustomize` auto-exec half of S6 — verified, and all 48 `scripts/*.py` import cleanly
under it; **do not** confuse with `-E`/`-I`, which the SKILL rightly forbids because they discard
`PYTHONPATH`). `init_run(fresh=…)` that forks the run id rather than silently no-opping (S11) — **audit the
five consumers that assume `run_id == ${KIMI_SESSION_ID}` first**, the `atlas/${KIMI_SESSION_ID}` worktree
branch name in particular. `-c core.hooksPath=/dev/null` on the worktree bootstrap (S12). `O_NOFOLLOW`
before the telemetry append, **keeping its absolute `exit 0` contract** (S13) — a refused write must be a
silent no-op, never a nonzero exit, or it breaks tool use in every session with the plugin installed.

**Explicitly deferred with a reason.** Full closure of S6 needs a plugin-integrity mechanism — a signed
manifest verified at run start, or a read-only install. That is a design problem, not a patch: the target's
build can overwrite `scripts/verdict.py` directly under both `PYTHONSAFEPATH=1` and `-S`. Do not pretend
`-S` closes it; the CHANGELOG must say what remains open.

---

## 6. Release v1.5.4 — supply chain and installer hygiene

**S15 — `hooks/guard-destructive.sh` false-DENIES ordinary commands.** Rule 2 (`:114-117`) is four
*independent* `grep -Eq` scans over the whole command string, so `rm` at command position, a recursive flag,
a force flag and a bare ` /` may each be satisfied by a **different part** of a compound command. Measured:
`rm -rf ./build && ls /`, `rm -rf build; df -h /`, `rm -rf target/ && echo done; mount | grep ' / '` and 4
more of 10 realistic commands are wrongly blocked — against the file's own header promise that
"ordinary commands (e.g. `rm -rf ./build`) are ALLOWED" and its stated rule that "a false global block is
not recoverable". Fix: extract the `rm` segment first (split on `;`/`&&`/`||`/newline, keep only segments
whose command position is `rm`) and apply the recursive/force/target tests **to that segment only**.
Measured true-positive coverage is 23/57 (40%) — either raise it (absolute paths, `\rm`, quoted targets,
`blkdiscard`/`sgdisk`/`parted`, `/dev/mapper/`, `/dev/dm-`) or state the number honestly in the header.

**S16 — `scripts/install.sh`.** Reports success and registers an `enabled` plugin after a partial
`git archive` (no `pipefail`, so only `tar`'s status is seen) — verified: a truncated tree with no
`hooks/` and no `scripts/` was registered as enabled. And it `cp`s `installed.json` to `.bak`
**unconditionally before parsing**, so the one run that needs recovery is the run that destroys the backup.
Fix: extract to a temp dir, validate `.kimi-plugin/plugin.json` + `scripts/` + `hooks/` + `skills/` exist,
then swap; parse before backing up; catch `AttributeError`/`TypeError` on malformed shapes.

**S17 — `skillextract --verify` blind spots.** Misses a stowaway dir *without* `SKILL.md`, a loose file at
`skills/` root, an extra file in a first-party dir (`skills/atlas/` — the highest-value plant location, and
it is explicitly excluded), a symlinked manifest file, and a mode change. Root cause:
`skillregistry.iter_skill_dirs` requires `(d/"SKILL.md").is_file()` and excludes `FIRST_PARTY_DIRS`.
Fix: sweep `root/"skills"` with `rglob("*")` against the union of recorded paths; reject symlinks outright;
record and check mode. **And add `--verify` to the `ci` target** — it is currently only in
`make skills-extract`, so the docs name a gate that no lane runs.

**The LOW set** (fix opportunistically, do not gate the release): `gate`/`final_status` pathcheck-severity
asymmetry (latent — but one constant edit in `pathcheck.py` makes it live, so pin the coupling);
OUTPUT renders advisory text before recording the verdict (move it after `advance`, wrap in `try/except`);
mode-only and rename-only diffs yield `changed_files == {}`; `valid_run_id` accepts refs
`git check-ref-format` rejects (`a..b`, `a.lock`, `...`, leading/trailing `.`) — or stop deriving the branch
name from `run_id` and use `--detach` as `uniontree` already does; `safewrap._sanitize_source` does not
neutralise fence prefixes in a dynamic `source` label (latent — all four call sites pass literals);
`lintlens` builds tool argv with no `--` separator, so a target-controlled filename beginning with `-`
silently kills the ruff job (`sast.py` gets this right); CI actions pinned to mutable tags with no
`permissions:` block.

---

## 7. After the program: Phase 3A

Token optimisation resumes **only** once the gate cannot be bypassed — a cheaper run is worthless if a
repository can make it green. The Phase 3A plan is written and hardened but **UNBUILT**:
`docs/superpowers/plans/2026-07-25-token-opt-p3a-driver-core-plan.md`, on branch `feature/token-opt-p3a`
(`8da9049`, 38 plan-challenge findings folded — read that commit body; its five CRITICALs *are* the plan's
content).

Two things must happen before building it: **rebase the branch onto the then-current `main`** (it is based
on the v1.5.0-era `main` and is now many commits behind), and **re-verify its 67 `skills/atlas/SKILL.md`
line citations**, which this security program will have shifted substantially. Skipping that means an
implementer edits the wrong lines.

Context for that phase: measured accounting (n=10 runs, Kimi's `usage.record`) shows the **root orchestrator
is 68–85%** of a run and the three judgment critics only 5–20%, so the founding "risk-gate the critics"
hypothesis is **refuted**. Do not re-propose it, nor lens-scoped REFINE, nor progressive disclosure of
hot-path SKILL sections.

---

## 8. Definition of done

- All 19 confirmed findings closed, or explicitly deferred **in the CHANGELOG** with the reason and what
  remains open. A security release that overstates what it fixed is itself a defect — that has already
  happened once on this project and cost a fix wave.
- Every fix carries a regression test that **fails without it**, and every pin is killed by a mutation you
  actually ran.
- No fix manufactures a RED on an honest repository. Prove it with fixtures, not with argument.
- The nine invariants hold, with 1, 2 and 3 strengthened. `scripts/verdict.py` never opened.
- `make ci` EXIT 0 at every task boundary; both CI lanes green at every release.
- `.superpowers/sdd/progress.md` records every task outcome, every deliberate deviation, and every Minor
  carried forward — it is the recovery map when context is lost.
