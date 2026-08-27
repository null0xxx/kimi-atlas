# Verification-integrity programme (v2)

**Date:** 2026-08-27 · **HEAD:** `272ed10` · **Status:** challenged, rewritten, not yet executed.

**v1 was challenged by two independent lenses and returned FAIL — 22 defects, 1 CRITICAL, 10 HIGH.**
This is the rewrite. What the challenge killed is recorded in §7 rather than quietly dropped, because
v1's top-priority remedy was **inert**, and a reader who only sees v2 would not know that.

## 1. Two organising findings, not one

v1 claimed a single pattern — "gates check a property ADJACENT to the one they protect". The challenge
showed that is three mechanisms wearing one name, and that the merged story produced an ordering with
a narrative justification rather than a mechanical one. The real cut:

| # | mechanism | IDs |
|---|---|---|
| **M1** | **Proxy-property gates** — the gate measures something near the property it protects. `sh -n` parses where the failure is at runtime; `runsignal` matches text where the question is whether a suite ran; the doc gate applies naming rules as a proxy for doc quality. | VIP-C2, VIP-B1, VIP-A1, VIP-B3 |
| **M2** | **Executable prose bound to nothing** — the SKILL bodies are programs, and 9 of 13 heredocs are only `ast.parse`-d. Nothing checks that a symbol they name exists, with that arity, or that a flag they pass is accepted. **8 of 10 injected drifts shipped silently.** | VIP-C9, VIP-A6, VIP-B4 |
| **M3** | **Absent gates and ordinary bugs** — not adjacent measurement at all: a gate that does not exist (hook registration, the orphaned fixtures), or a plain defect in non-gate code (an argv terminator, env passthrough). | VIP-A2, VIP-A3, VIP-A4, VIP-A5, VIP-C1, VIP-C3..C8 |

**The one-sentence takeaway, corrected:** *gates measure adjacent properties, and executable prose is
bound to nothing.* A reader who takes away only the first half never writes the drift tripwire — which
is the highest-value item in this document.

## 2. Root cause, sharpened by the challenge

v1 proposed: the test is written by the same pass, against the same mental model, as the code —
therefore every gate needs an armed control.

**That is half right and its remedy does not follow.** This repo already HAS armed controls;
`tests/test_syntaxlens_redteam.py:153-169` is a deliberate, host-independent, named-mutation control.
The mutation that escaped was the **opposite polarity** (`if False and` — a false-PASS) from the one it
was armed against (`if True or` — a false-BLOCK).

**The mechanism is: controls are written against the failure the author FEARS.** This project fears
false-blocks — it says so in its own documents, repeatedly, and correctly. So every false-block control
exists and the false-pass control is systematically the missing one.

"An armed control per gate" therefore just moves the problem: nothing then verifies the control is
non-vacuous. The remedy is a **standing mutation-polarity harness** — per gate, inject `if True or`,
`if False and`, and a deletion, and fail if any survives. v1 ran that experiment once by hand and
scheduled nothing to keep it running.

## 3. Constraints and non-goals

Four items run straight at constraints v1 never named:

* **Stdlib-only is deliberate** (`skills-era-hardening-analysis:145-150`). No item may add a runtime
  dependency to the blocking lane.
* **A toolchain-dependent floor made mandatory fails CLOSED on every machine without the toolchain**
  (`open-defect-surface:64`). VIP-A3, VIP-A4, VIP-C2 and VIP-C7 all touch this line. **Every one goes
  in a hard-asserting SIDE LANE, never in `make ci`.**
* **`make ci` must stay runnable on a bare host.** Wall-clock and toolchain cost are budgeted, not
  assumed.
* **Non-goal:** raising coverage as a number. Every item here is about whether a gate can SEE a
  defect, not how much code a test touches.

## 4. The register

Each row: what · evidence as `input -> observed output` · **the mutation that must turn the suite RED
once fixed** · how the fix could itself be worse. Provenance is `measured` (I ran it), `derived` (read
from code), or `cross-ref`.

### Class GREEN — the verdict can be wrong toward PASS

| id | what | evidence | killing mutation | fix-risk |
|---|---|---|---|---|
| **VIP-A1** | `runsignal.count` accepts one bare tally line anywhere in output, with no corroboration; a later line overwrites an earlier one | measured: `"3 passed in 12s"` -> `(3, True)`; `"3 passed in 0.02s\n99 passed in 1s"` -> `(99, True)` | revert the corroboration requirement -> the two inputs above must FAIL | **tightening.** Ship it AFTER VIP-B1 or the interval between is strictly more false-RED — the recorded casefold→lower shape |
| **VIP-A2** | option injection via `baseline_sha` — arbitrary file write | measured: `change_paths("--output=<p>", repo)` -> `['PWNED.txt']` **and created the file** | restore the unvalidated baseline -> the probe file must appear | see §7 — v1's fix was inert |
| **VIP-A3** | `syntaxlens.check` has a mocked NEGATIVE-arm control and no positive mirror | measured: `if False and result.get("signature_matched"):` -> 32 tests OK | `if False and` -> the new positive test must fail | none; a mocked mirror adds no dependency |
| **VIP-A4** | the only test proving `sast.scan` returns a defect is `skipTest`-guarded; the five armed fixtures under `tests/fixtures/` are consumed by no test | measured: appending `"--exclude","*.py"` -> 41 tests green, floor silent | the `--exclude` mutation must turn the side lane RED | **arming `bad_security_sast/linecount.py` puts a real `shell=True` injection into every run.** Do VIP-A5 FIRST or do not arm it |
| **VIP-A5** | `sast.scanner_env` passes `PYTHONUSERBASE`/`PYTHONHOME`/`LD_PRELOAD` to semgrep, whose stdout becomes a blocking SECURITY defect | derived, `scripts/sast.py:103,207` — **not yet reproduced; reproduce before building** | restore the passthrough -> a planted `usercustomize.py` must execute | none |
| **VIP-D4** | H5 — a second request in a session silently reuses the first's frozen packet. **Misfiled in v1 as "missing evidence"; it is fail-toward-green.** Hidden behind `@unittest.skip` reading "DEFERRED to v1.5.3" after v1.5.3 and v1.5.3.1 shipped | cross-ref `tests/test_v1521_regressions.py:685` | un-skip -> must fail (note: the test calls `init_run(..., fresh=True)`, a parameter that does not exist) | the `fresh=` seam was refuted by the s3v2 challenge — do not reinstate it |

### Class RED — honest work is turned red

| id | what | evidence | killing mutation | fix-risk |
|---|---|---|---|---|
| **VIP-B1** | any `=+…=+` section header beats the `-q` tally; a run ≥60s or using subtests is rejected by the grammar | measured: green `-q` with one warning -> `(0, False)`; `2 passed in 61.20s (0:01:01)` -> `(0, False)` | revert the grammar -> both must return `(0, False)` | **two attempts already built and destroyed by measurement.** The five recorded regressions F1–F5 are its specification |
| **VIP-B3** | the run applies kimi-atlas's OWN doc-naming rules to `.md` files in the TARGET repo | measured: `CONTRIBUTING.md` -> "filename must be all lowercase" | restore the unscoped gate -> the target-repo fixture must go red | **v1's fix — "scope it to the plugin's own tree" — REMOVES the only doc lens over target `.md`.** That is a coverage regression. Replace with a target-derived rule set, or price the removal |

### Class BLIND — the gate cannot see the defect

| id | what | evidence | killing mutation | fix-risk |
|---|---|---|---|---|
| **VIP-C0** | **the drift tripwire does not exist.** 9 of 13 SKILL heredocs are parse-only; nothing checks that a named symbol exists with that arity | measured: 8 of 10 injected drifts shipped silently; the rule is exact for that sample — drift is caught iff it lives in one of the 4 heredocs `test_critic_shapes_e2e.py` executes | rename any symbol in a parse-only block -> must fail | reports zero mismatches today, so it is a pure tripwire |
| **VIP-C0b** | **no standing mutation-polarity harness** (§2) | measured, by the 10-drift experiment | remove any gate's body -> the harness must fail | wall-clock cost; run it in a side lane |
| **VIP-C1** | hook registration is asserted nowhere | measured: delete the `init-env.sh` SessionStart entry -> 9/9 tests OK | that deletion must go red | **v1 said "execute each command" — that makes the gate an execution primitive driven by a manifest.** Resolve + `bash -n` + a hermetic sandboxed exec with an explicit env |
| **VIP-C2** | `check-shell` covers 18 of 59 tracked `.sh`; 41 under `skills/` are `#!/bin/bash` so `sh -n` is the wrong instrument; passes having checked zero files | measured | empty the glob -> must fail | shell identity is host-dependent; single-host measurement cannot settle it |
| **VIP-C3** | `check-cc-migration` passes on ZERO files — one 0xFF byte makes a file undecodable and it is skipped | measured: same file + one 0xFF -> "0 tracked file(s)", exit 0 | the 0xFF fixture must go red | none |
| **VIP-C4** | `check-strict` is byte-identical to `check`; doc gates see 63 of 435 `.md` | measured | — | none |
| **VIP-C5** | `inventory-drift` declares live `agents/` and `probe/` as FUTURE_DIRS | derived | — | none |
| **VIP-C6** | `predcov` is `-@… \|\| true` — a target, not a gate. `AGENTS.md`/`README.md` call `make ci` seven gates | measured | — | none — **documentation only** |
| **VIP-C7** | 8 of 21 skips are unlaned; `test_lintlens_redteam.py:47` asserts ZERO on every CI box | measured | — | installing linters into the blocking lane violates §3 |
| **VIP-C8** | `negative-gate`, `bench-validate`, `skills-extract --verify`, `skill-registry` are in no CI lane | measured | — | cost; side lane only |

### Class BOUND — prose that names code nothing binds it to (M2)

| id | what | evidence | killing mutation | fix-risk |
|---|---|---|---|---|
| **VIP-C9** | the SKILL bodies are programs; only 4 of 13 blocks are executed by any test | measured, 10-mutation sample | see VIP-C0 | — |
| **VIP-A6** | `coverage_partition` iterates a `str`'s CHARACTERS when handed a flat list. **v1 overstated this:** `SKILL.md:187` says "union of per-node subsets", which is AMBIGUOUS English in an LLM-executed block — so the failure is probabilistic per run, not deterministic, and the primary path (`planstage.py:68`) builds the correct nested list | measured: flat -> blocking CRITICAL; nested -> `[]` | pass a flat list -> the new type guard must reject it | **a prose edit in a parse-only block is unverifiable by construction.** The durable fix is a type guard INSIDE `coverage_partition` |
| **VIP-B4** | `floorsynth`'s trusted `fix` text says the human "may widen scope at the OUTPUT gate". **v1 misclassified this as false-RED; the challenge showed it turns zero honest work red** — the docstring's intent is "widen scope and re-run" | cross-ref `floorsynth.py:249-254` | — | **downgraded to a wording nit.** Do not build a scope-widening control on this evidence |

### Class EVIDENCE — actions, not defects

| id | what | disposition |
|---|---|---|
| **VIP-D1** | 13 of 14 probes have no committed result; all self-clean in an `EXIT` trap | scheduled, step 8 |
| **VIP-D2** | the claim that granting `Bash` alongside `Grep`/`Glob` disables the latter rests on an HTML comment — and two shipped role files had tools removed on it | **falsification task**, output: `references/agent-tools-live-validation.md` |
| **VIP-D3** | `.atlas/` is git-excluded, so no run ledger is durable evidence | **owner decision** — see §6 |

## 5. Order of work

**Every ID above appears exactly once below.** v1 left 11 of 19 with no disposition.

| step | id | why here |
|---|---|---|
| **0** | VIP-C0 | the tripwire. Three of v1's first five items were precisely the edits it exists to catch: step 5 changed `runcheck.run`'s handoff (a drift class measured as invisible), step 1 changed `change_paths`'s argv (called inside parse-only heredocs), step 3 changed syntaxlens/sast (named in the parse-only Step-2a block) |
| **0b** | VIP-C0b | the polarity harness (§2). Without it, every fix below can ship its own invisible inverse |
| 1 | VIP-A2 | live arbitrary-file-write. **Re-scoped — see §7** |
| 2 | VIP-B1 | **loosen BEFORE tightening.** v1 had A1 at 5 and B1 at 7, leaving an interval strictly more false-RED |
| 3 | VIP-A1 | the tightening, at `runcheck.run`, never bundled with B1 |
| 4 | VIP-C1 | closes the archetype |
| 5 | VIP-A5 → VIP-A4 → VIP-A3 | **A5 first**: A4 arms a real injection fixture and A5 is the env hole that fixture would exercise |
| 6 | VIP-A6 | type guard inside `coverage_partition`, not a prose edit |
| 7 | VIP-D4 | H5, re-classified into Class GREEN |
| 8 | VIP-D1, VIP-D2 | evidence: run the probes, falsify or confirm the tools claim |
| 9 | VIP-C3, VIP-C2, VIP-C7, VIP-C8 | gate scope, all side-lane per §3 |
| 10 | VIP-B3 | needs a target-derived rule set designed first |
| **doc-only** | VIP-C4, VIP-C5, VIP-C6, VIP-B4, VIP-C9 | corrections, no code |

## 6. Owner decisions — with a recommendation, as the local standard requires

| # | decision | recommendation |
|---|---|---|
| 1 | test-file bar: `≥81` (blueprint:410) vs `≥94` (:454); the tree is 88 | **adopt ≥81 and delete ≥94.** 88 passes it, the higher bar was never derived from anything, and a count is the wrong instrument — `tests/test_doc_testcount.py` already argues this |
| 2 | "3 pauses, 1 turn": no run ledgers a pause event | **retire the bar.** It is unverifiable from disk by construction; replace with a ledgered gate event if the property still matters |
| 3 | `.atlas/` git-excluded (VIP-D3) | **keep excluded, and stop citing ledgers as evidence.** Anything that must be durable gets a `references/*.md` |
| 4 | Phase 0 keep-or-revert (measured **+4.0%**, predicted −14.3%) | **revert.** The measurement refuted the premise |

## 7. What the challenge killed — recorded, not dropped

**v1's #1 action was INERT, and its scoping claim was false in the way that mattered.** v1 said: add
one `--` terminator; "every other diff site has `--`; only this one does not." Measured:

    current shape (no --)                            -> file created
    v1's fix: '--' appended AFTER the baseline        -> file created      <-- inert
    the other sites (baseline BEFORE their '--')      -> file created      <-- also vulnerable
    --end-of-options BEFORE the baseline              -> rc=128, blocked

**git parses options anywhere before `--`.** The other sites are not protected by their `--` either,
because the untrusted baseline still precedes it. The bug is at three sites, not one.

**Corrected VIP-A2:** validate `baseline_sha` against `^[0-9a-fA-F]{7,40}$` at every entry point (the
guard `corpusbuild.py:311` already uses), insert `--end-of-options` before the baseline, tighten
`schemas.json` (which today constrains it to `"str"` with no format), and fix all three sites
together. **Check first whether any live caller passes a ref like `HEAD~1`** — a strict sha pattern
would break it, and that would be a false-RED introduced by a security fix.

**v1 reproduced its own indictment.** It validated the fix by asking whether a `--` was PRESENT, not
whether it STOPPED the injection — a proxy-property check, in the remedy for a document about
proxy-property checks.

**Other corrections carried in above:** VIP-A3's evidence was a grep artifact (`assertTrue(res["signature_matched"])`
occurs four times; the regex missed it because `True` precedes the identifier) — the real hole is
consumer-side. VIP-A6 was overstated. VIP-B4 was misclassified. VIP-D4 was misfiled. `make ci`
resolving to `()` was **removed from Class RED entirely**: `()` means UNVERIFIED, which `langfloor.py:9-12`
documents as the intended fail-closed degrade — it is not a red, the fix is not small (`ci:` has no
recipe body, so widening the regex is a no-op and a real fix needs a Makefile prerequisite walker),
and it is now folded into VIP-C6 as documentation.

## 8. What no sweep could see

Four static read-only sweeps over one tree on one host cannot observe:

* **live multi-agent behaviour** — a subagent returning a schema-valid but fabricated critic, a
  dispatch that silently never happened, prompt truncation, the orchestrator skipping a step;
* **cost and latency** — zero measurements, while step 4 and step 5 both add work to the gate;
* **concurrency** — two sessions over one `.atlas/`, the lease clock, VIP-D4;
* **a second machine or a non-Linux host** — the archetype outage was host-specific (dash on
  Debian/Ubuntu), and VIP-C2 is by nature unmeasurable from one host;
* **the orchestrating model itself** — this document is self-attested by the same orchestrator that
  ran the sweeps.

## 9. Reproducibility — the debt this document still carries

Every `measured` cell above is a pure-function call, and **none is committed as a fixture.** Until
they are, this plan asks a builder to accept exactly the class of assertion its own Class EVIDENCE
exists to reject. **First commit of step 0: land all of them as regression fixtures under `tests/`,
re-taken at the build HEAD.**
