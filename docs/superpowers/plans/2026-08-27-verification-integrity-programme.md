# Verification-integrity programme — what is half-working, and in what order to fix it

**Date:** 2026-08-27 · **HEAD:** `5bae3d4` · **Method:** four parallel read-only research sweeps over
the whole tree, every load-bearing claim re-measured by the orchestrator afterwards. Nothing in this
document is inferred; each item names the measurement that produced it.

## The finding that organises everything else

This project's gates do not fail. They **check a property adjacent to the one they protect**.

The archetype is already on the record: `hooks/init-env.sh` was dead on every Debian/Ubuntu host for
weeks — three variables the whole plugin depends on were never exported — while `make ci` stayed
green, because `check-shell` runs `sh -n`, a PARSE check, and the broken construct is syntactically
valid in dash and fails only at RUNTIME.

That was not an isolated miss. The sweep found the same shape across the gate surface, and two
instances are worse than the original:

    manifest with the init-env.sh SessionStart entry DELETED  ->  9/9 tests OK
    syntaxlens.py: `if result.get("signature_matched"):` -> `if False and ...`  ->  32 tests OK

The first reproduces the original outage exactly, with zero coverage. The second disables the entire
ruby/php/go/sh/bash syntax floor with one token.

## Class A — the verdict can be WRONG, and these fail toward GREEN

The one thing this project exists to prevent.

| id | what | measured |
|---|---|---|
| **A1 RS-FAB** | one bare tally line anywhere in captured output opens the gate, with no corroboration; a later line silently overwrites a genuine earlier count | `"3 passed in 12s"` → `(3, True)`; `"3 passed in 0.02s\n99 passed in 1s"` → `(99, True)` |
| **A2 SEC-2** | `difftool.change_paths` appends an untrusted `baseline_sha` with **no `--` terminator**, so a value starting with `-` is a git OPTION | `change_paths("--output=<p>", repo)` returned `['PWNED.txt']` **and created the file**. Every other diff site in that module has `--`; only this one does not. `schemas.json` constrains `baseline_sha` to `"str"` — no format. The only guard lives in ONE caller (`corpusbuild.frozen_tree_paths`), whose own docstring names SEC-2 |
| **A3 SYNTAX-FLOOR** | the matched-signature arm has no positive test on any host; `.php`/`.sh` have no broken-input test at all | `if False and …` → 32 tests OK. Zero occurrences of `signature_matched.*True` in all of `tests/` |
| **A4 SAST-FLOOR** | the only test proving `scan()` returns a defect is `skipTest`-guarded; the five armed fixtures under `tests/fixtures/` are consumed by **no test** | appending `"--exclude","*.py"` to argv keeps 41 tests green and silences the floor. `bad_security_sast/linecount.py` contains a real `shell=True` injection nothing ever scans |
| **A5 SAST-ENV** | `sast.scanner_env` strips two switches but passes `PYTHONUSERBASE`/`PYTHONHOME`/`LD_PRELOAD` to semgrep, whose stdout becomes a blocking SECURITY defect | measured, `scripts/sast.py:103,207` |

## Class B — honest work is turned RED

By this project's own standard, worse than the bug it prevents.

| id | what | measured |
|---|---|---|
| **B1 RS-QRED** | any `=+…=+` section header beats the `-q` tally; a run ≥60s or one using subtests is rejected by the grammar | green `-q` with one warning → `(0, False)`; `2 passed in 61.20s (0:01:01)` → `(0, False)`. 9 of 19 green captures in the recorded corpus |
| **B2 MAKE-CI** | `langfloor.resolve_runner_tag` special-cases exactly `make test`; this repo's own documented primary gate resolves to `()` and can never print ✅ | `resolve_runner_tag("make ci")` → `()`, while `AGENTS.md`/`README.md` both call it "THE gate" |
| **B3 DOCS-TRAP** | the run applies kimi-atlas's OWN doc-naming rules to any `.md` the coder changed in the TARGET repo | `CONTRIBUTING.md` → "filename must be all lowercase"; `docs/notes.md` → "generic filename not allowed". Only `README.md` is allowlisted |
| **B4 A3-SCOPE** | `floorsynth` tells the coder, in its trusted instructions, that the human may widen scope at the OUTPUT gate. `scope_paths` has one writer (`ctxstore.init_run`) and no such option exists | blocks A4/A5 of the open-defect surface |

**A1 and B1 are entangled and must not be bundled.** Two attempts have already been built and
destroyed by measurement. The 2026-08-26 pass established why: every signal surviving `-q` is
imitable, and every reliable signal is what `-q` removes. **The provenance lives in `runcheck.run`,
which holds `stdout`, `stderr` and `returncode` and then discards the split before calling `count()`.**
Any credible fix changes what `runcheck` hands over, not how the text is matched.

## Class C — the gates are structurally blind

| id | gate | what it actually checks |
|---|---|---|
| **C1** | hook registration | `init-env.sh` is asserted NOWHERE. Six mutations verified green, incl. deleting its registration and `s\|/hooks/\|/hook/\|` (all six registrations dead) |
| **C2** | `check-shell` | `sh -n` over 18 of 59 tracked `.sh`; **41 under `skills/` are checked by nothing** and are `#!/bin/bash`, so `sh -n` is the wrong instrument anyway. Prints OK having checked zero files in an empty dir |
| **C3** | `check-cc-migration` | passes on ZERO files — one 0xFF byte makes a file undecodable and it is skipped silently. Four further evasions measured green |
| **C4** | `check-strict` | `.md` filenames only, 63 of 435 files; `--strict` is byte-identical to `check`. `touch docs/SKILL.md` removes a whole tree from both doc gates |
| **C5** | `inventory-drift` | `.md`→`.md` only; live `agents/` and `probe/` are declared FUTURE_DIRS |
| **C6** | `predcov` | nothing — `-@… \|\| true`, report-only. It is a target, not a gate |
| **C7** | skips | 8 of 21 are unlaned. `test_lintlens_redteam.py:47` puts every assertion under `if resolved is not None:` and asserts **zero** on every CI box — invisible in the skip count |
| **C8** | not in CI at all | `negative-gate`, `bench-validate`, `skills-extract --verify`, `skill-registry` |

## Class D — evidence that does not exist

* **13 of 14 probes have no committed result.** All 14 self-clean in an `EXIT` trap, so running one
  leaves no repository trace. Exactly one `FINDING=` line exists in the whole tree.
* **The most load-bearing platform claim in the repo rests on an HTML comment.** "granting `Bash`
  alongside `Grep`/`Glob` leaves both silently UNAVAILABLE" — no script, no transcript, no reference
  doc — and two shipped role files had tools removed on that basis.
* **`.atlas/` is git-excluded**, so no run ledger is durable evidence, including the three that
  refute G39.
* **`H5` is live at HEAD** and hidden behind an `@unittest.skip` reading "DEFERRED to v1.5.3" —
  v1.5.3 and v1.5.3.1 have both shipped. A second request in a session silently reuses the first's
  frozen packet.

## Order of work, and why

1. **A2 SEC-2** — one `--` terminator plus a format constraint at the sink. Smallest, and it is a
   live arbitrary-file-write documented in the repo's own docstring as measured and never fixed.
2. **C1 hook registration** — a test that resolves each `hooks.json` command to a real file and
   executes it. Closes the archetype so the original outage cannot recur silently.
3. **A3 + A4 floor positives** — one tool-independent positive mirror each. The sweep names A3's as
   "the highest-value single missing test"; A4's is wiring the five orphaned fixtures into `make ci`.
4. **B2 MAKE-CI** — the repo cannot verify itself with its own documented gate. Small and unblocks
   honest use.
5. **A1 RS-FAB** — alone, at `runcheck.run`, never bundled with B1.
6. **B3 DOCS-TRAP** — scope the doc gate to the plugin's own tree.
7. **B1 RS-QRED** — after A1, using the recorded F1–F5 regressions as its specification.
8. **Class D** — run the 13 probes once and commit their `FINDING=` lines. Cheap, and it converts
   the largest open surface from assertion to evidence.

**Explicitly NOT on this list:** the reasoned deferrals (`Workflow` adoption, native
`isolation:worktree`, `KIMI_CODE_HOME`), and the four owner decisions that nothing but the user can
close — Phase 0 keep-or-revert, the `≥81` vs `≥94` test-file bar, the untracked `Skills/` zips, and
the 73 MB vendored binary.

## Addendum — the fourth sweep, and the finding that reframes Class C

### A6 — `verdict.coverage_partition`: the weave SKILL documents the wrong shape and it fires a CRITICAL

`scripts/verdict.py:166` takes `(node_criteria: list[list[str]], frozen_criteria: list[str])` and does
`for subset in node_criteria: covered.update(subset)`. `skills/atlas-weave/SKILL.md:187` instructs the
**union** of per-node subsets — a FLAT `list[str]`. Measured:

    NESTED (what every test passes)  -> []
    FLAT   (what the SKILL says)     -> [{'severity': 'CRITICAL', ... 'dropped: docs updated, tests pass'}]

Following the documented procedure, `update()` iterates each criterion's CHARACTERS, `covered` never
matches, and **every weave AGGREGATE emits a blocking CRITICAL on correctly-covered criteria.** The
correct shape is well tested; the documented one is tested nowhere. This belongs in Class B.

### C9 — the SKILL bodies are programs, and 9 of 13 blocks are only parsed

A mutation experiment injected one drift per repo copy and ran the full suite. **8 of 10 shipped
silently.** Undetected: a renamed artifact (`diff.patch` → `diff.patchXX`), a kwarg `runcheck.run`
does not accept, four renamed functions, a renamed CLI flag, a renamed plan file. Detected: only the
two injected into heredocs a test actually EXECUTES.

The rule is exact: **drift is caught if and only if it lives in one of the 4 of 13 heredocs that
`test_critic_shapes_e2e.py` runs.** Blocks 0–8 — the INIT guard, the packet freeze, CLARIFY validate,
scout persist, skillselect, plan persist, **Step-1 diff capture** and the **Step-2a deterministic-lens
block** — are `ast.parse`-d only. `atlas-weave` and `atlas-resume` have **zero** execution coverage.

Nothing verifies that a flag the prose names is accepted by the script it names, or that a symbol it
calls exists with that arity. `test_skill_floor_contract.py` is the strongest pin in the repo and
still derives argument fidelity from a hand-maintained table rather than `inspect.signature`.

Nine further documented-vs-code mismatches live in `atlas-weave` alone, including `${SESSION}` never
bound across 12 call sites, a `leases` argument with no producer, and five weave stage names absent
from `ctxstore.STAGES` — so `verdict.missing_stages` reports six missing stages on any weave ledger.

### What this changes about the order of work

C9 outranks most of Class C. A gate that cannot see a renamed function in the program it is gating is
not a weak gate; it is an absent one. The cheapest high-value step is a **name-and-arity resolver over
all 13 heredocs** — parse each `scripts.<mod>.<fn>` reference, import it, and check the call binds via
`inspect.signature().bind()`. Run against the current tree it reports zero mismatches, so it is a
tripwire, not a repair — and it would have caught A6 before it was written.
