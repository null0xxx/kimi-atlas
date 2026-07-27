# H2 — the dirty-tree RED. Implementation plan (v1.5.3)

**Status:** ready to build. **Branch base:** `feat/phase0-packet-by-reference` @ `8d2a1bc`.
**Headline, stated before anything else:** this plan **NARROWS H2. It does not close it.** See
§8. The v1.5.2.1 entry overclaimed once; §8 is written so that cannot happen twice.

Every number in this document was computed by the author on 2026-07-27 against this working
tree. Each claim is tagged **MEASURED** (I ran it), **INHERITED** (I read it, did not re-derive)
or **MODELLED** (reasoning, not measurement). The working repo was left clean —
`git status --porcelain` empty, `git count-objects` 2343 before and after, no worktrees, no
objects added.

---

## 1. Global Constraints (verbatim, from the brief)

These are reproduced word for word. Violating any makes the design **wrong, not merely
imperfect**.

> 1. `scripts/verdict.py` is FROZEN (blob 57062e71, byte-identical across 5 releases). Never opened.
> 2. NO NEW BLOCKING PREDICATE and no new gate condition. Measured: every release that added a
>    blocking predicate injected a defect. The fix must REMOVE or NARROW a blocking condition,
>    or add only non-blocking coverage.
> 3. It must not create a false GREEN. Unreviewed executed surface must still reach the human.
> 4. No gate input may live where the reviewed model can write it (the T4-F8 class — this is
>    why the obvious snapshot was rejected).
> 5. `make ci` EXIT 0. Baseline: 1682 tests, 39 tracked docs.
> 6. Backticked path citations must exist on disk (`scripts/pathcheck.py` catches phantoms and
>    `make ci` does NOT run it on docs).
> 7. NO VACUOUS TESTS. A test deriving its expectation from what it pins is a defect; this
>    project has been bitten 5 times, including by a rigged falsification criterion.

And the governing rule, which outranks closing any defect:

> **A fix that manufactures a RED on an honest repository is worse than the bug it closes.**

**Baseline re-derived, not inherited.** MEASURED: `python3 -m unittest discover -s tests` →
`Ran 1682 tests in 57.129s` / `OK (skipped=7)`. `inventory_drift.scan_tree('.')` → **39** tracked
docs. `git --version` → 2.43.0. `id -u` → 0.

**Constraint 4 is honoured in a bounded, stated form, not claimed as closed.** MEASURED: `id -u`
is 0, the `coder` built-in carries `Bash`/`Write`/`Edit`, and its confinement to `review_root`
is prose in `skills/atlas/SKILL.md` and `agents/elite-coder.md` — there is no filesystem
sandbox on this host. **There is no location the coder cannot write.** Any plan phrased as
"a location the coder cannot write" is unbuildable here. What this plan delivers instead is
stated exactly in §7: tamper-**evident**, with every degradation pinned to *today's* behaviour,
and with the one surviving tamper-**silent** case printed to the human by name.

---

## 2. Adjudication — which design, and why

### 2.1 Chosen: **Design 1 — `presnap` as an INPUT FILTER on the existing predicate**, with grafts

`out_of_scope_defects` gains one optional third parameter. The only added statement filters
`full_paths`; the body below it is byte-identical. The input changes from
`diff(baseline_commit → post_coder_tree)` to `diff(pre_coder_tree → post_coder_tree)`, which is
the difference between the question the predicate is *asked* and the question it *answers*.

Four decisive reasons, each measured rather than argued:

**(a) It is the only design that survives the three structural pins with a data-only edit.**
MEASURED — I extracted the real Step 4+5 heredoc from `skills/atlas/SKILL.md`, applied this
plan's exact fold text, and replayed the real pin logic from
`tests/test_skill_floor_contract.py`:

```
FOLDS OK, set==8: True
all before merge: True
full_paths Name-assigns: 1   value is IfExp: True
out_of_scope args: ('full_paths', "st['scope_paths']", 'prov')   kwargs: []
```

`_folds()` passes (it only inspects assignments whose *value* is a `floorsynth.*` call, so
`prov = presnap.provenance(...)` is invisible to it);
`test_full_paths_is_gated_on_a_git_tree_with_resolvable_baseline` passes unchanged (the pinned
`IfExp` is not touched); `test_every_synthesiser_is_called_on_the_evidence_not_on_a_constant`
needs one 2-tuple → 3-tuple edit. Design 2's fold turns two of those three RED; Design 4's
rewrites the pinned argument into a comprehension `predcov.marshal_skill_argument` refuses.

**(b) Its blocking-side change is exercisable with pure data.** `provenance` is a plain dict, so
the whole demote / keep / degrade matrix runs with no git and no filesystem. MEASURED: only
three test modules in this repo are git-gated, and the `Makefile` header already records that
`make ci` can pass vacuously when a gated binary is absent. Design 3 and Design 4 put their
entire non-vacuous core behind real git.

**(c) It is the only design whose worst case still reaches the human.** MEASURED end to end
(§7): a fully forged snapshot demotes a coder-authored **evil.py**, but that path is still
**printed by name** as a coverage row. Design 4's forged pointer additionally empties its
`git diff <pre> <post>` coverage half, so the deception becomes fully silent.

**(d) It reuses an already-live location.** INHERITED from `PLAN.md` OD-3 and
`skills/atlas/SKILL.md`: `${KIMI_CODE_HOME:-$HOME/.kimi-code}/atlas-runs/wd_<sha256[:12]>/` is
the sanctioned non-git persistence base. MEASURED: `/root/.kimi-code/atlas-runs/wd_5eec50382347`
already exists on this host with real run ledgers in it. "Run state outside the target while the
coder writes the target" is exercised behaviour, not a hypothesis.

### 2.2 Grafts taken from the runners-up

| Graft | From | Why it is taken |
|---|---|---|
| **Capture at the TOP OF CODED**, immediately before `Agent(subagent_type="coder", …)` — *not* at the pre-CODE gate | Design 4 | Design 1 sited capture at the pre-CODE gate, which in interactive mode *is* the `AskUserQuestion` pause. A human deliberating there for minutes is a human plausibly saving a file. Any such file is absent from the snapshot → non-demotable → a blocking HIGH on a file no coder touched: **H2's exact shape, re-created by the fix, with the window maximised.** Design 4 sited it correctly and said why. Taken verbatim. |
| **Tri-state coverage rendering** — "not measured" is a distinct rendering from "zero" | Design 2 | Conflating "I looked and found none" with "I could not look" is the classic false green, and today's `git_tree_has_baseline` guard silently produces exactly that conflation. This is the one part of Design 2 that is strictly *stronger* than today. |
| **The one-snapshot two-arm acceptance test** (honest arm and adversarial arm off the *same* capture) | Design 4 | A test that snapshots after the coder runs derives its expectation from what it pins. One snapshot, two coder behaviours, is the non-vacuous construction. |
| **Explicit `outside_review_root` containment guard** | Designs 1 and 2 both measured it; kept | MEASURED with the live default home: the snapshot base resolves **inside** `review_root` for `/root` and for `/root/.kimi-code` (both `outside=False`), and outside for `/var/www/kimi-sub/kimi-atlas` and `/root/.kimi-code/plugins/managed/kimi-atlas`. This repo dogfoods against installed plugin copies, so the pathological root is reachable. Without the guard the design silently degrades into the rejected `.atlas/` snapshot. |

### 2.3 Rejected, with reasons

**Design 2 (two-arm routing on a stored pre-CODE bit) — REJECTED outright, not amended.**
Its central mechanism removes S3(a) for the entire population H2 lives in: on *any* dirty tree
the bit reads `dirty` and the blocking arm is off for everything, including a coder that deletes
the guarding test — and that needs no adversary. It also breaks `_folds()` and is caught in a
closed-world pincer between `predcov.discover_emitters` (which cannot see a router that authors
no blocking literal) and `test_adapter_arguments_match_the_skill_fold`. Two CRITICALs, one of
them the design rather than a bug in it.

**Design 3 (dirt-routed isolation) — REJECTED.** MEASURED: `git worktree add` checks out only
tracked files at the baseline, so every untracked or gitignored build input (`.env`, generated
config, submodule contents) is absent — and `_is_residue('.env')` is **False**. A suite that
passes in the user's tree fails in the worktree, and that failure lands in `runcheck`, the lens
`verdict.gate` trusts most, as a CRITICAL the coder structurally cannot fix. That is the
governing rule violated in a *less legible* place. It also executes target-controlled
`post-checkout` hooks before the human's Approve/Cancel, and it does not close H2 anyway (the
run's own build output still fires inside the clean worktree).

**Design 4's storage mechanism (git tree in a private object store) — REJECTED on three
measurements**, though its *location* reasoning agrees with Design 1's and its capture-timing
graft is taken:
- MEASURED: `timeout 5 git hash-object -- <fifo>` returns **rc=124** — it HANGS. A tracked path
  replaced by a FIFO *is* in `change_paths` (MEASURED), so `unchanged_paths` would never return
  and the run would never reach OUTPUT — worse than the RED being fixed. By contrast
  `presnap.hash_at` on the same FIFO returns `(None, 'nonregular')` in **0.000 s** (MEASURED).
- MEASURED: `git ls-tree` stores a symlink as `120000 blob 27b7fc27…` (the *target text*), while
  `git hash-object -- linky` returns `626799f0…` — byte-identical to `git hash-object docs/x.md`,
  i.e. **dereferenced**. A pre-existing symlink could therefore never be demoted; H2 would stay
  open for every repo with one.
- `git add -A` executes target-configured clean filters on *untracked* files, which today's
  `git diff` never touches. That widens an existing target-code-execution channel and writes to
  the user's `.git` on lfs repos.

**The TEST lens's `st['provenance']` subscript — REJECTED, with reason.** The proposal was to
make the third argument a subscript so `marshal_skill_argument` refuses when a corpus item omits
it. Two objections. First, `st` is `ctxstore.get_state(".atlas", run)` — i.e. **state.json**,
which lives inside the coder's writable root in the `review_root="."` lane. Putting the
provenance there is *precisely* the T4-F8 shape this plan exists to avoid, and it would make the
gate input coder-writable in exactly the mode that needs the fix. Second, the premise is wrong:
MEASURED by reading `marshal_skill_argument`, a **bare name also refuses** —
`if node.id not in namespace: raise ControlFailure("%r: the namespace supplies no %s")`. So
`prov` gets the refusal semantics the finding wanted, without moving a gate input into `.atlas/`.
The instrument-honesty half of that finding is folded separately as Task 7.

**A keyed MAC over the snapshot — REJECTED as unbuildable here.** An HMAC needs a key; the key
must live somewhere the coder cannot read; MEASURED, no such place exists at uid 0 with a
`Bash`-capable reviewed agent. The field is therefore named `entries_checksum`, not `digest`,
and its docstring says what it does and does not do.

---

## 3. What is built

### 3.1 New module — **scripts/presnap.py** (to be created)

Stdlib only. **No `subprocess`.** No function raises. ~200 lines, most of it docstring.

```python
SCHEMA = "atlas.presnap/1"
MAX_ENTRIES     = 4096
MAX_FILE_BYTES  = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024

def snapshot_dir(review_root: str, run_id: str) -> pathlib.Path
def outside_review_root(review_root: str, run_id: str) -> bool
def hash_at(root: str, rel: str) -> tuple[str | None, str]     # (sha256hex|None, kind)
def capture(review_root, run_id, baseline_sha, change_paths, is_residue) -> dict
def load(review_root, run_id, baseline_sha) -> tuple[dict | None, str]
def provenance(review_root, run_id, baseline_sha, full_paths) -> dict
```

**Location:**
`${KIMI_CODE_HOME:-$HOME/.kimi-code}/atlas-runs/wd_<sha256(realpath(review_root))[:12]>/<run_id>/pre_coder.snapshot.json`,
directory created `0o700`, file `0o600`, written to a `.tmp` sibling then `os.replace`.

**Record shape** (canonical JSON, `sort_keys=True`, `separators=(",",":")`):

```json
{"schema":"atlas.presnap/1","run_id":"<run_id>","baseline_sha":"<sha>",
 "review_root_real":"<abs realpath>","truncated":false,
 "entries":{"<review_root-relative path>":{"h":"<sha256hex>|null","k":"<kind>"}},
 "entries_checksum":"<sha256 of the canonical json of entries>"}
```

The key set is exactly `difftool.change_paths(baseline, review_root)` at capture time, minus
`floorsynth._is_residue`. Paths equal to the baseline need no entry — the baseline commit already
covers them, and their absence from `entries` means they can only ever **block**.

**`hash_at` kinds and the hashing discipline** (this is where three CRITICAL/HIGH findings land):

| kind | how it is reached | demotable? |
|---|---|---|
| `file` | `S_ISREG`, `sha256(b"F\0" + (b"x" if mode & 0o111 else b"-") + b"\0" + content)` | yes, on exact hash match |
| `symlink` | `S_ISLNK`, `sha256(b"L\0" + os.readlink(...))` — **never dereferenced** | yes, on exact hash match |
| `absent` | `os.lstat` raises `OSError` | yes, **only** when still `absent` at VERIFIED |
| `nonregular` | FIFO / socket / device — `h` is `None` | no |
| `oversize` | `st_size > MAX_FILE_BYTES` — `h` is `None` | no |
| `unreadable` | open/read fails — `h` is `None` | no |

The **executable bit is inside the hash** (`b"x"` / `b"-"`). MEASURED: a pure `chmod +x` on a
tracked out-of-scope file *is* returned by `difftool.change_paths` (fixture: **deploy.sh** appears
after `chmod 644 → 755` with no content change), so a content-only hash would demote it and ship
a green. With the mode folded in, it still blocks (§7).

The sequence is `os.lstat` → branch on type → `os.open(O_RDONLY|O_NOFOLLOW|O_NONBLOCK)` →
`fstat` → re-check `S_ISREG`. This is why the FIFO case costs 0.000 s instead of hanging.

**`load` refuses** — returning `(None, reason)` — on: `unsafe_location`, `symlinked_snapshot`,
`absent`, `unreadable`, `malformed`, `schema_mismatch`, `run_id_mismatch`, `baseline_mismatch`,
`review_root_mismatch`, `malformed_entries`, `checksum_mismatch`. Every refusal yields
`pre_existing = []`, which makes the filter the identity function, which is today's behaviour.

**`provenance` does two passes.** Pass 1, over `full_paths`: demote `p` iff
`entries[p]` exists **and** (`k` is `absent` and `p` is still absent now) **or**
(`entries[p].h` is non-null and `hash_at(...) == entries[p].h`). Everything else — no entry, null
hash, differing hash, unreadable now — falls through to **blocking**, per path. Pass 2, over
`entries` not in `full_paths`: classify as `pre-existing-deleted` /
`pre-existing-replaced-nonregular` / `pre-existing-reverted-or-now-invisible`. Pass-2 results are
**coverage only, never blocking** — promoting them would add a blocking condition, which
constraint 2 forbids.

### 3.2 `scripts/floorsynth.py` — four lines and one docstring paragraph

```python
def out_of_scope_defects(full_paths, scope_paths, provenance=None) -> list[dict]:
    ...
    pre = (provenance or {}).get("pre_existing") if (provenance or {}).get("status") == "ok" else None
    if isinstance(pre, (list, tuple, set, frozenset, dict)):
        pre = frozenset(x for x in pre if isinstance(x, str))
        if pre:
            full_paths = [p for p in (full_paths or []) if p not in pre]
    # ... EXISTING BODY UNCHANGED FROM HERE DOWN (line 318 onward today) ...
```

The `isinstance` coercion is load-bearing, not defensive tidiness — see Task 5 for the measured
substring-demotion failure it closes.

`_is_residue`, `_normalize_scopes`, the H1 `json.dumps` hardening and the H2 `fix` template are
inherited **untouched**. `scripts/verdict.py` is never opened.

### 3.3 `skills/atlas/SKILL.md` — three edits

1. **CODED, immediately before the coder dispatch** (a new `<<'PY'` block): compute
   `change_paths` and call `presnap.capture`. Print `PRESNAP=<status>:<n_entries>`.
2. **Step 4+5 fold** (today at `skills/atlas/SKILL.md`:841–843): two new lines and a third
   argument. The pinned `full_paths` `IfExp` is **not** touched.
3. **OUTPUT STOP block**: one non-blocking coverage line.

### 3.4 What is deliberately NOT built

- No new blocking predicate, no new `gate_results` key, no new stage, no new pause.
- The three newly-visible shapes (`deleted`, `reverted`, `replaced-nonregular`) ship as coverage.
- The S3(a) rename-into-scope miss is **not** touched. Promoting it would add a blocking
  condition. It stays on the roadmap.

---

## 4. The findings ledger — every CRITICAL and HIGH, and what changed

This repo records folds; it does not absorb them. Twenty-eight CRITICAL/HIGH findings were
raised across five lenses. Every one is listed. Findings against Designs 2, 3 and 4 are folded as
**design-selection evidence** where the design is rejected, and as **mechanism changes** where the
finding also bites the chosen design.

### 4.1 CRITICALs

| # | Lens · Design | Finding | Disposition |
|---|---|---|---|
| C1 | CORRECTNESS · D2 | One stray file flips the bit and disables blocking for the whole run; measured `gate=OK` on a tree where the coder deleted the guarding test | **FOLDED — design rejected.** No per-run switch is built. Discrimination is per-path and content-keyed. |
| C2 | CORRECTNESS · D1 | Content-only hashing demotes a coder-authored **mode-only** change; measured `chmod 0755` takes the gate UNVERIFIED → OK | **FOLDED — mechanism changed.** The executable bit is domain-separated **into** the hash (§3.1). VERIFIED in §7: **deploy.sh** still blocks on the adversarial arm. |
| C3 | CORRECTNESS · D2 | The bit is sited before the headless worktree exists, so the blocking arm is off for the 8/12 lane too | **FOLDED — design rejected.** Also generalised into a placement rule for the chosen design: capture runs at the top of CODED, *after* `review_root` is persisted and after any worktree exists. |
| C4 | CORRECTNESS / SECURITY / DOES-IT-RUN · D3 | Routing to a worktree manufactures a `runcheck` RED (untracked `.env` absent; submodule `vendor/` empty), unfixable by the coder, no escape hatch in the auto lane | **FOLDED — design rejected.** Independently corroborated: MEASURED `_is_residue('.env')` is **False**. |
| C5 | SECURITY · D3 | `git worktree add` executes the target's `post-checkout` hook as uid 0, **before** the human's Approve/Cancel | **FOLDED — design rejected.** The chosen design adds **no** new git subcommand against the target: `presnap` is pure stdlib with no `subprocess`. |
| C6 | CORRECTNESS · D4 | Replica-fidelity becomes unsatisfiable: the inline comprehension is not one of the three shapes `marshal_skill_argument` accepts, so `probe_failopen` becomes unbuildable for this predicate forever | **FOLDED — mechanism changed.** The narrowing is a **named argument** (`prov`), not a call-site comprehension. MEASURED: the fold's args unparse to `('full_paths', "st['scope_paths']", 'prov')` — all three marshallable. |
| C7 | CORRECTNESS · D4 | The proposed fold passes bare `scope_paths`, which is not bound in that heredoc → `NameError` on every run | **FOLDED — process change.** Task 9 requires the candidate fold text to be run through `ast.parse` + the bound-name walk + all three pins *before* the SKILL is edited. The chosen fold uses `st["scope_paths"]`, unchanged. |
| C8 | SECURITY · D4 | Pointer forgery is a **silent** false green: the forged `pre` also empties the `git diff <pre> <post>` coverage half, so nothing reaches the human | **FOLDED — design rejected**, and the property is made an explicit requirement of the chosen design: a demoted path is **always** printed. VERIFIED in §7 (`FULL-FORGERY … PRINTED-as-coverage: True`). |
| C9 | SECURITY · D4 | No containment guard on the store location; the store holds **file content** (`.env` is not residue) at rest outside the repo with no retention policy | **FOLDED — mechanism.** `outside_review_root` is mandatory (Task 1), and `presnap` stores **sha256 + path names only**, never file bytes. Dir `0o700`, file `0o600`. |
| C10 | CODE-QUALITY · D2 | `_folds()` must be weakened globally to accept a tuple destination, disarming the "discarded synthesis" fence for all eight synthesisers | **FOLDED — design rejected.** MEASURED: the chosen fold keeps `script_defects += floorsynth.<fn>(...)` as the sole fold shape and `_folds()` passes with all 8 members. |
| C11 | CODE-QUALITY · D2 | Closed-world pincer: `discover_emitters` cannot see a router that authors no blocking literal, but `SYNTH_ARGUMENTS` must name the function the fold calls | **FOLDED — design rejected.** The chosen design keeps one function name across `discover_emitters`, `ADAPTER_ARGUMENTS` and `SYNTH_ARGUMENTS`. |
| C12 | TEST-ADEQUACY · D4 | `capture`/`unchanged_paths` take no `run_id`/`baseline_sha`, so the H5 guard has no unit-testable home | **FOLDED — mechanism.** `load(review_root, run_id, baseline_sha)` takes exactly the three fields the check needs; one refusal test per bound field (Task 3). |
| C13 | TEST-ADEQUACY · D3 | The exact-predictor claim can only be tested on a fixture rigged so it cannot fail | **FOLDED — design rejected.** |
| C14 | DOES-IT-RUN · D4 | `git hash-object` **hangs** on a FIFO (measured rc=124); no `subprocess` in `scripts/difftool.py` has a timeout | **FOLDED — design rejected, and the safe construction adopted.** RE-MEASURED by me: rc=124 at a 5 s timeout; `presnap.hash_at` on the identical FIFO returns `(None,'nonregular')` in 0.000 s. `presnap` uses **no `subprocess` at all**. |
| C15 | DOES-IT-RUN · D2 | The proposed fold breaks the `full_paths` gate pin, `_folds()` and `test_calls_every_synthesiser` at once | **FOLDED — design rejected.** |

### 4.2 HIGHs

| # | Lens · Design | Finding | Disposition |
|---|---|---|---|
| H-a | CORRECTNESS · **all four** | None closes the honest RED produced by the verification run's own build output; 21 of 31 probed names are not residue | **FOLDED — scope honesty.** RE-MEASURED: **coverage.xml**, `build.log`, **junit-results.xml**, **pytest-report.json**, **coverage.json**, **package-lock.json**, `Cargo.lock`, `go.sum`, `.env` all `_is_residue = False`. §8 states this as **residual R1**, the CHANGELOG says **narrowed, not closed**, and Task 11 ships a test that **pins the limitation**. |
| H-b | CORRECTNESS · D1 + D4 | A user who **deleted** a tracked file before the run still gets a blocking HIGH: `h` is null → "falls through to blocking" | **FOLDED — mechanism changed.** RE-MEASURED: `rm docs/old.md` → `change_paths` returns `['deploy.sh','docs/old.md','docs/x.md','notes.txt']` → 4 blocking HIGH today. `hash_at` now returns kind `absent`, and `provenance` demotes on `absent → absent`. VERIFIED in §7: **docs/old.md** demoted on the honest arm. |
| H-c | CORRECTNESS · D4 | `git hash-object` dereferences symlinks, so pre-existing symlinks can never be demoted | **FOLDED — design rejected; construction adopted.** RE-MEASURED (§2.3). `presnap` hashes `b"L\0" + os.readlink(...)`. VERIFIED in §7: a *repointed* symlink still blocks; an untouched one demotes. |
| H-d | CORRECTNESS · D2 | `read_pre_code_state` validates `baseline_sha`/`review_root` but not `scope_paths`, so the gate's own *Adjust scope* option re-manufactures H2 | **FOLDED — design rejected.** The chosen design is scope-independent: content identity does not depend on `scope_paths`. |
| H-e | CORRECTNESS · D3 | Every preflight blocker routes back to `"."`, i.e. back to H2; `SUBMODULES_PRESENT` alone excludes a large class of repos | **FOLDED — design rejected.** |
| H-f | CORRECTNESS/TEST · D1, D2, D4 | Once the machine channel is removed, constraint 3 rests on model-emitted prose — and `diff.full.patch` is the measured precedent for a "the human will see it" channel nobody reads | **FOLDED — mechanism + test.** RE-MEASURED: `diff.full.patch` appears **once** in `skills/atlas/SKILL.md` (the write at :554) and in no read. Task 10 adds an OUTPUT-block **read** pin (not a write pin) and names `.atlas/<run_id>/diff.full.patch` in the STOP block, giving that dark artifact its first reader. Stated in §8 as residual R6: this is a static pin on an instruction, not a runtime guarantee. |
| H-g | SECURITY · D1 | The demotion test is content-only, so a mode-only coder change is silently demoted | **Same as C2 — FOLDED.** |
| H-h | SECURITY · D1 | Capture at the pre-CODE gate opens a manufactured-RED window equal to the human's think time | **FOLDED — graft from Design 4.** Capture moves to the top of CODED, immediately before `Agent(subagent_type="coder", …)`. Task 8. |
| H-i | SECURITY · D4 | The **second** `capture()` runs `git add -A` after the coder and after the build, executing target clean filters on untracked files | **FOLDED — design rejected.** The chosen design takes **one** snapshot per run and shells out to nothing. |
| H-j | SECURITY/CQ · D3, D4 (and D1's rendering) | Target-controlled path bytes reach the orchestrator on the verdict turn, unquoted; the artifact rendered at OUTPUT lives in coder-writable `.atlas/` | **FOLDED — mechanism changed.** RE-READ, and this is a shipped invariant I must not cross: the existing predicate-coverage line at `skills/atlas/SKILL.md`:1090–1097 states it "reads **NO file** … interpolates nothing … anything read here would enter the orchestrator's context on the very turn it prints the verdict, which is exactly the class of defect this floor exists to close." **So the OUTPUT coverage line prints only an integer count plus two FIXED literal artifact paths.** The path *names* live in **provenance.json** and `diff.full.patch`, one click away, and are never interpolated on the green turn. Task 10. |
| H-k | SECURITY · D2 | S3(a) is disabled for everything on any dirty tree, including plainly hostile changes | **FOLDED — design rejected.** VERIFIED in §7: the chosen design keeps 4 genuine touches blocking. |
| H-l | CODE-QUALITY · D1 | A four-line insert invalidates **six** `tests/fixtures/predcov_controls/*.json` `branch_line` citations at once | **FOLDED — task added.** RE-MEASURED: the six fixtures citing floorsynth lines ≥ 327 are `out-of-scope`(327), `dimension-dissent`(407), `critic-stale`(454), `stale-verdict`(568), `critic-missing`(602), `critic-schema`(628). The four below (`evidence-incomplete` 83, `runcheck` 101, `docs-naming` 114, `empty-diff` 169) are unaffected. Task 6 regenerates all six **programmatically** by unique `branch_source` match, in the same commit as the floorsynth edit. |
| H-m | CODE-QUALITY · D1 | The demotion line does an unguarded `in` on an untyped value; a **string** there demotes by substring | **FOLDED — mechanism changed.** The `isinstance` + `frozenset` coercion in §3.2. Task 5 ships the three-type unit test. |
| H-n | CODE-QUALITY · D1 | Capture placement is internally contradictory (pre-CODE gate is the *early* point) | **Same as H-h — FOLDED.** |
| H-o | CODE-QUALITY · D2 | Breaks the T2-F2 `full_paths` gate pin (tuple target → zero Name-assigns) | **FOLDED — design rejected.** MEASURED: the chosen fold keeps exactly 1 Name-assign whose value is the pinned `IfExp`. |
| H-p | CODE-QUALITY · D3 | Does not close H2: build output outside the 14-entry residue frozenset fires inside the clean worktree | **FOLDED — design rejected**, and folded into §8 residual R1 for the chosen design too. |
| H-q | CODE-QUALITY · D3 | Converts a legible false RED into an illegible one through `runcheck` | **Same as C4 — FOLDED, design rejected.** |
| H-r | TEST-ADEQUACY · D1 | **The headline evidence claim is vacuous.** `blocking_new ⊆ blocking_today` is satisfied by a mutant that returns `[]` on any provenance | **FOLDED — acceptance bar rewritten.** RE-MEASURED by me: I applied mutant **M1** (`if provenance: return []`) to a copy of `scripts/floorsynth.py` and ran the 26-row matrix plus `TestH2OrdinaryDirtyTreeIsNotBlocked` → **`Ran 29 tests … OK`**. The subset property is **struck from the acceptance bar** and demoted to a labelled refactor fence carrying the comment *"this cannot fail; it is not evidence."* The killing test is the adversarial arm (§9). |
| H-s | TEST-ADEQUACY · all three arg-adding designs | The argument-fidelity pin degrades to "is it a name"; predcov would bind a fabricated `prov=None` and the published `out-of-scope 1/15` row silently changes meaning | **PARTIALLY FOLDED, and the proposed remedy REJECTED with reason (§2.3).** The instrument-honesty half is folded as Task 7: `dirty_item_inputs` gains an explicit `"prov": None` sentinel, `defects_out_of_scope` gains the third parameter, and the row in `references/predcov.json` is **relabelled** to state that it measures the **un-demoted** predicate. Shipping the mechanism without the relabel is the instrument-lies failure and is forbidden here. |
| H-t | TEST-ADEQUACY · D2 | The union invariant is vacuous — `printed` is unobservable to a pure function | **FOLDED — design rejected.** |
| H-u | TEST-ADEQUACY · D2 | `tree_change_state` has no fault-injection seam, so a partial git read reported as `observed=True` cannot be tested | **FOLDED — design rejected.** `scripts/difftool.py` is not modified by this plan. |
| H-v | SECURITY · D1 | A forged snapshot yields a silent 0-blocking demotion; the checksum authenticates nothing and the containment guard closes only misconfiguration | **ACCEPTED AS A STATED RESIDUAL, not fixed.** §8 residual R3. The field is named `entries_checksum`; the docstring says it detects corruption and careless edits and authenticates nothing. The bound is measured, not asserted (§7): the forged path is still printed, and MEASURED control — rewriting `scope_paths` in `.atlas/<run_id>/state.json` to `["."]` already takes this predicate from 3 blocking to 0 today, with no snapshot involved. This is a third tenant of an occupied room and the *only* one that is content-addressed at all. It is **not** a closure of T4-F8. |
| H-w | DOES-IT-RUN · D1 + D4 | Adding the module to the existing import line turns `make ci` RED (`test_imports_floorsynth` asserts an exact substring) | **FOLDED — task instruction.** Task 8 requires `from scripts import presnap` on a **separate line**; `skills/atlas/SKILL.md`:790 stays byte-identical. |
| H-x | DOES-IT-RUN · D4 | The specified fold does not run and silently rewrites both pinned argument expressions | **Same as C7 — FOLDED.** |
| H-y | DOES-IT-RUN · D3 | `auto` mode has no source of truth: `grep -i "permission mode"` over `skills/atlas/SKILL.md` returns zero | **FOLDED — design rejected; item recorded, not built.** §8 residual R7. Naming the third lane is worth shipping on its own merits and is out of scope here. |
| H-z | DOES-IT-RUN · D3 | Routing an interactive run into a worktree silently repeals the interactive auto-reset prohibition (`rollback_driver.sanctioned_rollback` is keyed on **path**, the SKILL rule on **mode**) | **FOLDED — design rejected.** Worth recording independently: it is a live mode/path keying mismatch that any future isolation work must fix first. |

### 4.3 MEDIUM/LOW findings folded anyway (cheap, and two are correctness)

- **`make ci` heredoc count.** `tests/test_skill_floor_contract.py` asserts `len(bodies) == 13`.
  The CODED capture block makes it 14. **Task 8 bumps it and extends the comment.** Without this
  every design fails `make ci`.
- **FIFO mislabel (Design 1's self-declared W5).** A pre-existing file replaced by a FIFO must
  classify as `pre-existing-replaced-nonregular`, not `reverted`. Folded into §3.1 and Task 4 —
  a mislabelled coverage row is a mislabelled piece of the only evidence the human gets.
- **Docstring supersession.** `out_of_scope_defects`' docstring currently says provenance
  "MUST NOT be approximated in code". Task 12 supersedes it **explicitly**, stating that the ban
  was on the `untracked ⇒ human` heuristic and that this is a **content measurement**, not that
  heuristic. Leaving it would be the `tests/test_doc_fictions.py` class in reverse.
- **Tracked-doc count.** MEASURED 39 today; this plan document is the 40th tracked doc. Task 12
  links it from the roadmap ledger and updates `AGENTS.md` in the same commit, or `make ci`
  (`inventory-drift`) goes red.
- **S3(a) rename-into-scope (LOW).** Left open by all four designs. Not touched here; promoting
  it would add a blocking condition. §8 residual R5.

---

## 5. Task-by-task build (TDD)

Every task: write the test, watch it fail for the stated reason, write the code, watch it pass.
Commands are exact and run from `/var/www/kimi-sub/kimi-atlas`.

Shorthand used below:
`PP='PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.'`

---

### Task 1 — presnap: location + containment guard

**Create** tests/test_presnap.py (to be created) with:

```python
import os, pathlib, unittest
from scripts import presnap


class TestSnapshotLocation(unittest.TestCase):
    def test_key_is_the_realpath_of_review_root(self):
        d1 = presnap.snapshot_dir(".", "s1")
        d2 = presnap.snapshot_dir(os.getcwd(), "s1")
        self.assertEqual(d1, d2)
        self.assertTrue(d1.name == "s1")
        self.assertTrue(d1.parent.name.startswith("wd_"))
        self.assertEqual(len(d1.parent.name), len("wd_") + 12)

    def test_honours_KIMI_CODE_HOME(self):
        os.environ["KIMI_CODE_HOME"] = "/tmp/atlas-presnap-probe"
        try:
            self.assertTrue(str(presnap.snapshot_dir(".", "s1"))
                            .startswith("/tmp/atlas-presnap-probe/atlas-runs/wd_"))
        finally:
            os.environ.pop("KIMI_CODE_HOME", None)


class TestContainmentGuard(unittest.TestCase):
    """Reviewing one's own Kimi home is not hypothetical: this repo dogfoods
    against installed plugin copies. Without this guard the design silently
    degrades into the rejected `.atlas/` snapshot -- the T4-F8 class."""

    def test_refuses_when_the_store_resolves_inside_review_root(self):
        home = os.environ.get("KIMI_CODE_HOME") or os.path.join(
            os.path.expanduser("~"), ".kimi-code")
        self.assertFalse(presnap.outside_review_root(home, "s1"))
        self.assertFalse(presnap.outside_review_root(
            str(pathlib.Path(home).parent), "s1"))

    def test_allows_an_ordinary_target(self):
        self.assertTrue(presnap.outside_review_root(os.getcwd(), "s1"))

    def test_never_raises_on_a_nonsense_root(self):
        self.assertIsInstance(presnap.outside_review_root("\0bad", "s1"), bool)
```

**Run — expect FAIL:**
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m unittest tests.test_presnap -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.presnap'`.

**Implement** `snapshot_dir`, `outside_review_root` in scripts/presnap.py per §3.1.
`outside_review_root` returns `False` on any exception (fail toward today's behaviour).

**Run — expect PASS:** `Ran 5 tests … OK`.

**Independent evidence this guard is not theoretical** (run it, record the output in the commit
message):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c "
from scripts import presnap
for rr in ['/var/www/kimi-sub/kimi-atlas','/root','/root/.kimi-code','/root/.kimi-code/plugins/managed/kimi-atlas']:
    print('%-48s outside=%s' % (rr, presnap.outside_review_root(rr,'s1')))"
```
Expected (MEASURED today):
```
/var/www/kimi-sub/kimi-atlas                     outside=True
/root                                            outside=False
/root/.kimi-code                                 outside=False
/root/.kimi-code/plugins/managed/kimi-atlas      outside=True
```

---

### Task 2 — presnap: `hash_at`, all six kinds

**Append** to tests/test_presnap.py:

```python
import hashlib, os, stat, tempfile, time, unittest
from scripts import presnap


class TestHashAt(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def test_regular_file(self):
        p = os.path.join(self.d, "a.txt")
        open(p, "w").write("hello")
        h, k = presnap.hash_at(self.d, "a.txt")
        self.assertEqual(k, "file")
        self.assertEqual(h, hashlib.sha256(b"F\0-\0hello").hexdigest())

    def test_the_executable_bit_is_INSIDE_the_hash(self):
        """C2: a pure `chmod +x` on an out-of-scope tracked file IS returned by
        difftool.change_paths (measured). A content-only hash would demote a
        coder-authored mode change and ship a green."""
        p = os.path.join(self.d, "run.sh")
        open(p, "w").write("#!/bin/sh\n")
        os.chmod(p, 0o644)
        before, _ = presnap.hash_at(self.d, "run.sh")
        os.chmod(p, 0o755)
        after, _ = presnap.hash_at(self.d, "run.sh")
        self.assertNotEqual(before, after)

    def test_symlink_is_hashed_on_its_TARGET_TEXT_never_dereferenced(self):
        """H-c: `git hash-object` dereferences (measured: a symlink and its
        target return the same sha). We must not."""
        open(os.path.join(self.d, "real.txt"), "w").write("payload")
        os.symlink("real.txt", os.path.join(self.d, "link"))
        hl, kl = presnap.hash_at(self.d, "link")
        hr, kr = presnap.hash_at(self.d, "real.txt")
        self.assertEqual(kl, "symlink")
        self.assertEqual(kr, "file")
        self.assertNotEqual(hl, hr)
        self.assertEqual(hl, hashlib.sha256(b"L\0real.txt").hexdigest())

    def test_repointing_a_symlink_changes_the_hash(self):
        os.symlink("/etc/hostname", os.path.join(self.d, "l2"))
        h1, _ = presnap.hash_at(self.d, "l2")
        os.unlink(os.path.join(self.d, "l2"))
        os.symlink("/etc/passwd", os.path.join(self.d, "l2"))
        h2, _ = presnap.hash_at(self.d, "l2")
        self.assertNotEqual(h1, h2)

    def test_fifo_is_nonregular_and_does_NOT_block(self):
        """C14: `git hash-object -- <fifo>` HANGS (measured rc=124 at a 5s
        timeout). A tracked path replaced by a FIFO IS in change_paths, so a
        hang here means the run never reaches OUTPUT -- worse than the RED."""
        os.mkfifo(os.path.join(self.d, "pipe"))
        t0 = time.time()
        h, k = presnap.hash_at(self.d, "pipe")
        self.assertLess(time.time() - t0, 1.0)
        self.assertIsNone(h)
        self.assertEqual(k, "nonregular")

    def test_absent_is_its_own_kind(self):
        """H-b: a user who DELETED a tracked file before the run is an ordinary
        dirty tree and must not keep a blocking HIGH."""
        self.assertEqual(presnap.hash_at(self.d, "nope.txt"), (None, "absent"))

    def test_oversize_is_not_hashed(self):
        p = os.path.join(self.d, "big.bin")
        with open(p, "wb") as f:
            f.truncate(presnap.MAX_FILE_BYTES + 1)
        h, k = presnap.hash_at(self.d, "big.bin")
        self.assertIsNone(h)
        self.assertEqual(k, "oversize")

    def test_never_raises_on_a_hostile_name(self):
        for bad in ("../escape", "a\nb", "\0"):
            self.assertIsInstance(presnap.hash_at(self.d, bad), tuple)
```

**Run — expect FAIL** (`AttributeError: module 'scripts.presnap' has no attribute 'hash_at'`),
then implement per §3.1, then **expect PASS:** `Ran 13 tests … OK`.

---

### Task 3 — presnap: `capture` and `load`, and every refusal

**Append** to tests/test_presnap.py a `TestCaptureAndLoad` class covering:

- `capture` returns `{"status": "captured", "n_entries": N, "truncated": False}`; the file exists
  at `snapshot_dir(...)/pre_coder.snapshot.json`; dir mode `0o700`, file mode `0o600`.
- residue is filtered at capture time — pass `floorsynth._is_residue`; assert **__pycache__/x.pyc**
  and **node_modules/a.js** are absent from `entries`.
- **idempotence**: a second `capture` returns `{"status": "reused"}` and does **not** rewrite the
  file (compare `st_mtime_ns` before/after). This is the machine detector for
  *"never re-taken on a REFINE pass"* — without it, pass 1's own out-of-scope output launders
  itself into `pre_existing` on pass 2, which is a **silent** false green.
- `capture` on a `review_root` whose store resolves inside it returns
  `{"status": "unsafe_location"}` and writes nothing.
- **one refusal test per bound field** (C12): mutate `schema`, `run_id`, `baseline_sha`,
  `review_root_real`, `entries_checksum` in turn; assert `load` returns
  `(None, "<field>_mismatch")` in each case. Each test is killed by deleting that field's
  comparison.
- `load` on an absent file → `(None, "absent")`; on truncated JSON → `(None, "unreadable")`; on a
  **symlinked** snapshot file → `(None, "symlinked_snapshot")`.
- `MAX_ENTRIES` overflow sets `truncated: True` and the record still loads.

**Run — expect FAIL, implement, expect PASS.**

---

### Task 4 — presnap: `provenance`, the partition

**Append** `TestProvenance` covering, with expectations derived from the constructed filesystem
state (never from the classifier's own output):

| case | expectation |
|---|---|
| unchanged since capture (file, symlink) | in `pre_existing` |
| content changed | **not** in `pre_existing` |
| mode changed, content identical | **not** in `pre_existing` |
| captured `absent`, still absent | in `pre_existing` |
| captured `absent`, now present | **not** in `pre_existing` |
| captured `file`, now a FIFO | **not** in `pre_existing`; in `vanished` iff dropped from `full_paths`, kind `pre-existing-replaced-nonregular` |
| in `entries`, absent from `full_paths`, now gone | `vanished`, kind `pre-existing-deleted` |
| `load` refuses (any reason) | `{"status": "<reason>", "pre_existing": [], "vanished": []}` |
| no entry at all for a path in `full_paths` | **not** in `pre_existing` |

Plus: `provenance` never raises for any of `None`, `[]`, `[123]`, `["\0"]` as `full_paths`.

**Run — expect FAIL, implement, expect PASS.**

---

### Task 5 — floorsynth: the optional third parameter

**Append** to `tests/test_floorsynth.py`, inside `TestOutOfScopeDefects`, a paired block modelled
on `test_tool_residue_is_not_a_defect` — the one existing row that already pairs a filter
assertion with an explicit control:

```python
    def test_provenance_demotes_only_the_named_paths(self):
        prov = {"status": "ok", "pre_existing": ["notes.txt", "data.csv"]}
        got = floorsynth.out_of_scope_defects(
            ["notes.txt", "data.csv", "evil.py", "scripts/a.py"], ["scripts"], prov)
        # Control: the filter must NOT be emptiable into swallowing everything.
        self.assertEqual([d["id"] for d in got], ['out-of-scope:"evil.py"'])

    def test_provenance_absent_or_not_ok_is_byte_for_byte_today(self):
        args = (["notes.txt", "data.csv", "docs/x.md", "scripts/a.py"], ["scripts"])
        today = floorsynth.out_of_scope_defects(*args)
        for prov in (None, {}, {"status": "absent", "pre_existing": ["notes.txt"]},
                     {"status": "checksum_mismatch", "pre_existing": ["notes.txt"]}):
            with self.subTest(prov=prov):
                self.assertEqual(floorsynth.out_of_scope_defects(*args, prov), today)

    def test_a_non_collection_pre_existing_can_never_demote_by_SUBSTRING(self):
        """H-m: `p not in pre` against a STRING demotes by substring. Measured:
        with pre='NOTES.md data/download.csv' both user files vanish, and so
        would any path that is a substring of it. A string is not a set."""
        args = (["notes.txt", "data.csv", "evil.py"], ["scripts"])
        today = floorsynth.out_of_scope_defects(*args)
        for bad in ("notes.txt data.csv", 7, object(), {"notes.txt": 1}.keys()):
            with self.subTest(bad=bad):
                self.assertEqual(
                    floorsynth.out_of_scope_defects(*args, {"status": "ok",
                                                            "pre_existing": bad}),
                    today)
```

Note the fourth case is a `dict_keys`, which **is** a legitimate collection — the coercion
accepts `dict` and rejects `str`/`int`/arbitrary objects; adjust the expectation if the
implementation admits views. The load-bearing assertion is the `str` case.

**Run — expect FAIL:** `TypeError: out_of_scope_defects() takes 2 positional arguments but 3
were given`.

**Implement** §3.2 in `scripts/floorsynth.py` (signature at line 236; the filter goes immediately
above `scopes = _normalize_scopes(scope_paths)`, today line 318).

**Update** `tests/test_skill_floor_contract.py`: `SYNTH_ARGUMENTS["out_of_scope_defects"]`
becomes `("full_paths", "st['scope_paths']", "prov")`.

**Run — expect PASS**, and separately confirm the 26-row matrix is untouched:
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_floorsynth.TestOutOfScopeDefects \
  tests.test_floorsynth.TestOutOfScopeFixDefaultsToDoNotTouch \
  tests.test_floorsynth.TestOutOfScopeTargetBytesAreQuoted \
  tests.test_v1521_regressions.TestH2OrdinaryDirtyTreeIsNotBlocked
```
Expected: `Ran 32 tests … OK` (29 today + the 3 new). **All three
`TestH2OrdinaryDirtyTreeIsNotBlocked` assertions pass unmodified.**

**Do not** cite that as evidence the blocking surface held. MEASURED (H-r): mutant M1
(`if provenance: return []`) passes all 29 of today's rows. The evidence is §9.

---

### Task 6 — regenerate the six `predcov_controls` `branch_line` citations

The floorsynth insert shifts every emitter defined below it. MEASURED, the six affected fixtures
and their current values:

| fixture | current `branch_line` |
|---|---|
| `tests/fixtures/predcov_controls/out-of-scope.json` | 327 |
| `tests/fixtures/predcov_controls/dimension-dissent.json` | 407 |
| `tests/fixtures/predcov_controls/critic-stale.json` | 454 |
| `tests/fixtures/predcov_controls/stale-verdict.json` | 568 |
| `tests/fixtures/predcov_controls/critic-missing.json` | 602 |
| `tests/fixtures/predcov_controls/critic-schema.json` | 628 |

Unaffected (below the insert): `evidence-incomplete`(83), `runcheck`(101), `docs-naming`(114),
`empty-diff`(169).

**Regenerate programmatically, never by hand** — `branch_source` is unique inside each emitter's
span, which is exactly what `test_control_provenance_lines_are_inside_their_emitter` enforces:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
import ast, json, pathlib
src = pathlib.Path("scripts/floorsynth.py").read_text().splitlines()
for p in sorted(pathlib.Path("tests/fixtures/predcov_controls").glob("*.json")):
    d = json.loads(p.read_text())
    want = d["branch_source"]
    hits = [i + 1 for i, ln in enumerate(src) if ln.strip() == want.strip()]
    assert len(hits) == 1, (p.name, want, hits)
    if d["branch_line"] != hits[0]:
        print("%-26s %4d -> %4d" % (p.name, d["branch_line"], hits[0]))
        d["branch_line"] = hits[0]
        p.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
PY
```

**Run — expect PASS:**
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

**Commit Tasks 5 and 6 together.** No intermediate state may carry stale citations — a citation
landing on the wrong branch is a control that silently exercises a different predicate and then
proves nothing.

---

### Task 7 — `scripts/predcov.py`: the cascade, and the relabel that keeps the instrument honest

Four call sites and one input builder must move together (MEASURED locations):
`ADAPTER_ARGUMENTS` (the `"out-of-scope"` row at `scripts/predcov.py`:631),
`defects_out_of_scope` (:485), its two internal callers (:1149, :1325), and
`dirty_item_inputs` (:1046).

1. `ADAPTER_ARGUMENTS["out-of-scope"]` → `(emit_out_of_scope, ("full_paths", "st", "prov"))`.
2. `defects_out_of_scope(paths, state, prov)` → `floorsynth.out_of_scope_defects(full_paths,
   st["scope_paths"], prov)`; both internal callers pass `inputs["prov"]`.
3. `dirty_item_inputs` returns an explicit `"prov": None` **with a comment stating why**: the
   corpus replays a frozen `tree.paths` with no snapshot, so this arm measures the **un-demoted**
   worst case.
4. **Relabel the record.** In `references/predcov.json` and in the report text, the
   `out-of-scope` row is renamed to state the arm it measures
   (`out-of-scope (pre-provenance)`), and a one-line note is added: *"this row replays the frozen
   `tree.paths` with no pre-coder snapshot, so it reports the predicate BEFORE provenance
   narrowing; the shipped fold narrows it."* Regenerate with `make predcov-write`, never with
   `make ci`.

**Why this is mandatory, not tidiness:** without it, `references/predcov.json` keeps saying
`out-of-scope 1/15` while describing behaviour the orchestrator no longer has, and Phase 2's
go/no-go decision is made from that number. `scripts/predcov.py`'s own docstring names this
failure: *"An unbound third copy … produces a coverage number for a call the orchestrator never
makes, and every reader takes that for a measurement of the real fold."*

**Run — expect PASS:**
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov 2>&1 | tail -3
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m scripts.predcov | grep out-of-scope
```
Expected: the row prints and is labelled `(pre-provenance)`.

---

### Task 8 — SKILL: the CODED capture block

**Edit `skills/atlas/SKILL.md`.** Insert immediately **before** the
`- **Dispatch \`elite-coder\`**` bullet (today line 450), i.e. after the memory guard and after
`review_root` has been persisted and any headless worktree created:

````
- **Pre-coder snapshot (H2).** Take it **HERE**, immediately before the coder is dispatched —
  never at the pre-CODE gate, whose `AskUserQuestion` is an unbounded human pause, and every file
  a human saves during it would otherwise become a blocking HIGH on a file no coder touched. It is
  taken **once per run**: a REFINE re-dispatch returns `reused`, so pass 1's own out-of-scope work
  can never launder itself into "pre-existing". Failure is silent and lands on today's behaviour.
  ```
  PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.." python3 - <<'PY'
  from scripts import ctxstore, difftool, floorsynth, presnap
  run = "${KIMI_SESSION_ID}"
  st = ctxstore.get_state(".atlas", run)
  review_root = (ctxstore.read_artifact(".atlas", run, "review_root") or ".").strip() or "."
  baseline = (st.get("baseline_sha") or "").strip()
  paths = difftool.change_paths(baseline, review_root) \
      if difftool.git_tree_has_baseline(review_root, baseline) else []
  res = presnap.capture(review_root, run, baseline, paths, floorsynth._is_residue)
  print("PRESNAP=%s:%s" % (res.get("status"), res.get("n_entries", 0)))
  PY
  ```
  Any status other than `captured`/`reused` means the run will end UNVERIFIED on any pre-existing
  out-of-scope file, exactly as it does today. Note it and continue — this is **not** a gate.
````

**Also in this task:**

- `from scripts import presnap` goes on **its own line** in the Step 4+5 block (Task 9).
  `skills/atlas/SKILL.md`:790 (`from scripts import ctxstore, difftool, floorsynth, verdict`)
  must stay **byte-identical** — `test_imports_floorsynth` asserts that exact substring (H-w).
- Bump `tests/test_skill_floor_contract.py`'s `self.assertEqual(len(bodies), 13)` to `14` and
  extend the adjacent comment: *"14 with the CODED pre-coder-snapshot block (H2)."*

**Run — expect PASS:**
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_floor_contract 2>&1 | tail -3
```

---

### Task 9 — SKILL: the Step 4+5 fold

**Before editing**, run the candidate text through the pins (this is the process fold for C7):

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
import ast, pathlib, sys
sys.path.insert(0, "tests")
from tests.test_skill_floor_contract import _heredoc_bodies, _floorsynth_calls
src = [b for b in _heredoc_bodies(pathlib.Path("skills/atlas/SKILL.md").read_text())
       if "floorsynth.merge_and_validate(" in b][0]
t = ast.parse(src.replace("${KIMI_SESSION_ID}", "SID"))
bound = sorted({n.id for n in ast.walk(t) if isinstance(n, ast.Name)
                and isinstance(n.ctx, ast.Store)})
print("BOUND NAMES:", bound)
assigns = [n for n in ast.walk(t) if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "full_paths"]
print("full_paths Name-assigns:", len(assigns), "IfExp:", isinstance(assigns[0].value, ast.IfExp))
print("oos args:", tuple(ast.unparse(a) for a in
                         _floorsynth_calls(t, "out_of_scope_defects")[0].args))
PY
```
`scope_paths` must **not** appear in `BOUND NAMES` — the block reads `st["scope_paths"]`.
After the edit, `oos args` must print `('full_paths', "st['scope_paths']", 'prov')`.

**Edit** `skills/atlas/SKILL.md`:841–843. Replace:

```python
full_paths = difftool.change_paths(baseline, review_root) \
    if difftool.git_tree_has_baseline(review_root, baseline) else []
script_defects += floorsynth.out_of_scope_defects(full_paths, st["scope_paths"])
```

with:

```python
full_paths = difftool.change_paths(baseline, review_root) \
    if difftool.git_tree_has_baseline(review_root, baseline) else []
# H2: narrow the INPUT, never add a verdict. `prov` demotes only paths whose
# CONTENT AND MODE are byte-identical to the pre-coder snapshot taken at CODED.
# Every degradation (absent/corrupt/stale/tampered snapshot) yields
# pre_existing == [], which makes this the identity function -- i.e. today's RED.
prov = presnap.provenance(review_root, run, baseline, full_paths)
try:                       # diagnostic ONLY -- never read by a predicate or a gate
    ctxstore.write_artifact_confined(".atlas", run, "provenance.json", prov)
except Exception:
    pass                   # a planted symlink must not kill the gate block
script_defects += floorsynth.out_of_scope_defects(full_paths, st["scope_paths"], prov)
```

and add `from scripts import presnap` on its own line beneath line 790.

The `try/except` is not decoration: `write_artifact_confined` **raises** on a symlinked
component, and in the `review_root="."` lane `.atlas/` is inside the coder's writable root — an
unwrapped raise would let a planted symlink kill the entire gate block, which is a manufactured
total failure, strictly worse than a RED.

**Run — expect PASS:**
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_skill_floor_contract tests.test_predcov 2>&1 | tail -3
```

---

### Task 10 — SKILL: the OUTPUT coverage line, and its READ pin

**Edit** the STOP block list in `skills/atlas/SKILL.md` (today at :1056+), inserting between the
residual-defect bullet and the diff-location bullet:

````
  - **Unreviewed executed surface (informational, NEVER a gate).** From the Step 4+5 stdout you
    already hold `n_pre_existing`, `n_vanished` and `provenance_status`. Print ONE line, deriving
    it from those integers **only**:
    - status `ok` and `n_pre_existing + n_vanished == 0` → omit the line.
    - status `ok` and the count is non-zero → `unreviewed executed surface: N file(s) changed in
      the executed tree were NOT reviewed by any lens (pre-existing before this run). Names and
      content hashes: .atlas/<run_id>/provenance.json ; whole-tree diff:
      .atlas/<run_id>/diff.full.patch`
    - any other status → `unreviewed executed surface: not measured (<status>)` — **never `0`**.
      "I could not look" is not "I looked and found none", and printing `0` for the first is the
      classic false green.
    Like the predicate-coverage line below it, this line **reads NO file**, interpolates **no
    path from the reviewed tree**, computes **no** pass/fail and adds **NO** key to
    `gate_results`. The only substituted values are integers and a fixed status word you already
    hold. A filename is target-controlled bytes, and this is the turn on which the verdict is
    printed.
````

**Add the READ pin** to `tests/test_skill_floor_contract.py` (H-f: pin the read, not the write —
`diff.full.patch` is this repo's measured precedent for a write pinned by two tests and read by
nobody):

```python
class TestOutputSurfacesTheUnreviewedResidual(unittest.TestCase):
    """H2/constraint 3. `diff.full.patch` is written every run (SKILL.md:554)
    and read by NOTHING -- two contract tests pin that write, none pins a read.
    The residual channel must not repeat that. This is a static pin on an
    INSTRUCTION, not a runtime guarantee; it cannot prove the model emits it."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        i = self.text.index("Present the labelled STOP block")
        self.block = self.text[i:i + 6000]

    def test_the_stop_block_names_the_provenance_artifact(self):
        self.assertIn("provenance.json", self.block)

    def test_the_stop_block_gives_diff_full_patch_its_first_reader(self):
        self.assertIn("diff.full.patch", self.block)

    def test_not_measured_is_a_distinct_rendering_from_zero(self):
        self.assertIn("not measured", self.block)

    def test_the_line_does_not_interpolate_a_reviewed_tree_path(self):
        """SAFE-2 / the shipped invariant at SKILL.md:1090-1097: nothing read
        from the target may enter the orchestrator's context on the verdict
        turn. Only integers and a fixed status word are substituted."""
        i = self.block.index("Unreviewed executed surface")
        line = self.block[i:i + 1400]
        self.assertIn("reads NO file", line)
        for banned in ("pre_existing[", "for p in", "json.dumps(p"):
            self.assertNotIn(banned, line)
```

Also extend the Step 4+5 block's final `print(json.dumps({...}))` with
`"provenance_status": prov.get("status")`, `"n_pre_existing": len(prov.get("pre_existing") or [])`
and `"n_vanished": len(prov.get("vanished") or [])`, so the three integers exist on the turn the
STOP block is composed.

**Run — expect PASS:** `Ran … OK`.

---

### Task 11 — the acceptance matrix (real git, real `floorsynth`, real `verdict.gate`)

**Create** tests/test_h2_dirty_tree.py (to be created), `skipUnless(shutil.which("git"))`.
**One fixture, ONE snapshot, two coder behaviours.** Expectations come from
`CHANGELOG.md`:48–63 (the documented H2 shape) and from the coder script, never from the fixture
setup or from the classifier.

Fixture (`_build()`), committed at a baseline: **src/calc.py**, **docs/x.md**, **docs/old.md**,
**deploy.sh** (mode 0644), **docs/real.md** + symlink `linky`, **tests/test_calc.py**. Then the
**user's own pre-existing dirt**: create **notes.txt**, create **data/download.csv**, edit
**docs/x.md**, `rm docs/old.md`. `scope_paths = ["src"]`.

Then `presnap.capture(...)` **once**.

**Arm A — honest** (the coder edits **src/calc.py** and nothing else):
```python
self.assertEqual(len(today), 4)          # today: 4 blocking HIGH
self.assertEqual(verdict.gate(m_today, GREEN), "UNVERIFIED")
self.assertEqual(len(new), 0)            # narrowed: 0 blocking
self.assertEqual(verdict.gate(m_new, GREEN), "OK")
self.assertEqual(sorted(prov["pre_existing"]),
                 ["data/download.csv", "docs/old.md", "docs/x.md", "notes.txt"])
```

**Arm B — adversarial, SAME snapshot** (five genuine coder touches: create **evil.py**; append to
the user's already-dirty **docs/x.md**; `chmod +x deploy.sh`; `rm notes.txt`; repoint `linky` to
`/etc/passwd`):
```python
self.assertEqual(sorted(d["id"] for d in new), [
    'out-of-scope:"deploy.sh"',   # C2  mode-only change
    'out-of-scope:"docs/x.md"',   # append to a user's dirty file
    'out-of-scope:"evil.py"',     # new out-of-scope file
    'out-of-scope:"linky"',       # H-c repointed symlink
])
self.assertEqual(verdict.gate(m_new, GREEN), "UNVERIFIED")
self.assertIn({"path": "notes.txt", "kind": "pre-existing-deleted"}, prov["vanished"])
```

**Arm C — degradation table.** For each of `tampered-no-checksum`, `truncated`, `absent`,
`stale-baseline`, `unsafe_location`: assert the new blocking **id set is equal to today's**.

**Arm D — the known residual, pinned as a NEGATIVE test** (constraint 7: pin the limitation, not
the hope):
```python
def test_a_FULLY_FORGED_snapshot_demotes_BUT_the_path_is_still_printed(self):
    """R3, stated rather than hidden. Content-addressing protects the payload,
    not which pointer is read; no key store exists at uid 0. The bound is that
    the deception is VISIBLE, not absent."""
    ...  # add evil.py to entries with its real hash, recompute entries_checksum
    self.assertNotIn('out-of-scope:"evil.py"', {d["id"] for d in new})
    self.assertIn("evil.py", prov["pre_existing"])   # printed by name

def test_the_runs_OWN_BUILD_OUTPUT_still_fires(self):
    """R1. coverage.xml is created by runcheck AFTER the snapshot, so it has
    no entry and is not demotable. H2 is NARROWED, not closed."""
    self.assertFalse(floorsynth._is_residue("coverage.xml"))
    ...
    self.assertIn('out-of-scope:"coverage.xml"', {d["id"] for d in new})

def test_mode_B_isolated_worktree_is_a_STRICT_NO_OP(self):
    """8 of 12 real runs. The worktree is clean at the baseline, so the snapshot
    has 0 entries and the blocking set is byte-identical to today's."""
    self.assertEqual(cap["n_entries"], 0)
    self.assertEqual(today_ids, new_ids)
    self.assertIn('out-of-scope:"oops.py"', new_ids)
```

**Arm E — the labelled refactor fence** (H-r), carrying its own honesty comment:
```python
def test_blocking_new_is_a_subset_of_blocking_today(self):
    """REFACTOR FENCE, NOT EVIDENCE. This property is satisfied by a mutant that
    returns [] on any provenance -- measured: `if provenance: return []` passes
    all 29 of today's out-of-scope rows. The killing test is Arm B."""
```

**Run — expect PASS.**

---

### Task 12 — docs, and the count

1. **`scripts/floorsynth.py` docstring.** Supersede the H2 paragraph explicitly:
   *"SUPERSEDED in v1.5.3. The ban above was on the `untracked ⇒ human` HEURISTIC, which is a
   git state and not authorship. It was never a ban on MEASUREMENT. `provenance` is a content-
   and-mode identity check against a snapshot taken before the coder was dispatched; a path is
   demoted only when its bytes and its mode are unchanged since then. Every failure of that
   measurement yields the un-narrowed input, i.e. the behaviour documented above."* Keep the rest
   of the H2 narrative intact — it is the record of why.
2. **`CHANGELOG.md`.** H2 moves from INTERIM to **NARROWED**, with §8's residual list reproduced
   verbatim. The words *closed* and *fixed* must not appear next to H2.
3. **`docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md`.** Update the H2 row in
   §2b, and **link this plan document** from the ledger — otherwise `inventory-drift` reports
   `missing_from_index` and `make ci` goes red.
4. **`AGENTS.md`:149.** `39 tracked docs` → `40 tracked docs`, and replace the H2 interim
   sentence with the narrowed statement.
5. **Phantom check** (`make ci` does **not** run `pathcheck` on docs):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c "
import pathlib,subprocess
from scripts import pathcheck
t=subprocess.run(['git','ls-files'],capture_output=True,text=True).stdout.split()
for f in ['CHANGELOG.md','AGENTS.md','docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md',
          'docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md']:
    d=pathcheck.cross_check(pathlib.Path(f).read_text(),{'tracked':t},'.')
    print(f, len(d), [x['location'] for x in d])"
```
Expected: `0 []` for every file. Any new module must exist on disk **before** any tracked doc
backticks it; until then it is written in bold with *(to be created)*, which is the convention
the roadmap already uses.

**Final gate:**
```
make ci ; echo "EXIT=$?"
```
Expected: `EXIT=0`, with the test count at **1682 + N** where N is the tasks' new tests
(≈ 55–70), and **39 + 1 = 40** tracked docs with no inventory drift.

---

## 6. Ordering, and why

Tasks 1–4 build **scripts/presnap.py** (to be created) **wired to nothing**. A pure additive
module with no call site can regress nothing, so the whole first half is risk-free and separately
revertible.

Tasks 5 + 6 land together as one commit — the floorsynth edit and the six control-fixture
regenerations must not be separable.

Task 7 lands before the SKILL edits, so `references/predcov.json` never describes a fold that
already shipped differently.

Tasks 8–10 are the only hazardous edits. Each is a separate commit. Task 9 in particular carries
the pin-verification command *before* the edit, because this repo's own record (`synth_docs(True)`)
is of an argument pin passing while the argument was wrong.

Task 11 is written **before** Task 12: the acceptance evidence must exist before the CHANGELOG
describes it.

---

## 7. Evidence — measured today, end to end

All of the following were executed by the author on 2026-07-27 with a prototype of
**scripts/presnap.py** and the **real** `scripts/difftool.py`, `scripts/floorsynth.py` and
`scripts/verdict.py`. `scripts/verdict.py` was **called**, never opened.

**H2 reproduced verbatim from the brief:**
```
floorsynth.out_of_scope_defects(['notes.txt','data.csv','docs/x.md','scripts/a.py'], ['scripts'])
-> 3  ['out-of-scope:"data.csv"', 'out-of-scope:"docs/x.md"', 'out-of-scope:"notes.txt"']
```

**Arm A — honest dirty tree, coder touched only src/calc.py:**
```
HONEST change_paths: ['data/download.csv','docs/old.md','docs/x.md','notes.txt','src/calc.py']
HONEST today blocking: 4   gate(today) -> UNVERIFIED
HONEST new   blocking: 0   gate(new)   -> OK
HONEST coverage pre_existing: ['data/download.csv','docs/old.md','docs/x.md','notes.txt']
```
Note **docs/old.md** — the **deleted** file (H-b) — demoted correctly.

**Arm B — adversarial, SAME snapshot, five genuine coder touches:**
```
ADV today blocking: 6  [data/download.csv, deploy.sh, docs/old.md, docs/x.md, evil.py, linky]
ADV new   blocking: 4  [deploy.sh, docs/x.md, evil.py, linky]
ADV coverage vanished: [{'path':'notes.txt','kind':'pre-existing-deleted'}]
gate(new) -> UNVERIFIED       SUBSET new<=today: True
```
**deploy.sh** is the **mode-only** change (C2). `linky` is the **repointed symlink** (H-c).
**notes.txt** is the coder deleting a user's untracked file — **invisible today** (it leaves
`change_paths` entirely), now surfaced as coverage.

**Degradation table — every row equals today's blocking set exactly:**
```
tampered-no-checksum   status=checksum_mismatch   blocking=6   ==today: True
truncated              status=unreadable          blocking=6   ==today: True
absent                 status=absent              blocking=6   ==today: True
stale-baseline (H5)    status=baseline_mismatch   blocking=6   ==today: True
FULL-FORGERY           status=ok                  blocking=3   evil demoted: True   PRINTED-as-coverage: True
```

**Mode B (isolated worktree, 8 of 12 real runs) — strict no-op:**
```
MODE-B pre-coder change_paths: []
MODE-B capture: {'status':'captured','n_entries':0,'truncated':False}
MODE-B today: ['out-of-scope:"oops.py"']
MODE-B new  : ['out-of-scope:"oops.py"']
MODE-B IDENTICAL (strict no-op): True
```

**Cost, on this repo (1096 tracked files, 96 MB `.git`), hashing every tracked file as if all
were dirty:**
```
capture   : wall=0.433s   maxRSS=19328kB   n_entries=1096
provenance: wall=0.056s
git count-objects: 2343 before -> 2343 after     git status --porcelain: 0 lines
```
Zero git objects, zero index touches, zero `.gitignore` edits. On a clean tree
`change_paths == []`, so the snapshot has 0 entries and costs ~1 ms.

**The FIFO and symlink measurements that rejected Design 4:**
```
timeout 5 git hash-object -- fifo1                 -> rc=124  (HANG)
presnap.hash_at('.', 'docs/real.md')  [a FIFO]     -> (None,'nonregular')  elapsed=0.000s
git ls-tree HEAD linky      -> 120000 blob 27b7fc274cb951f03d4a2b4013aeba19cb720ad8
git hash-object -- linky    -> 626799f0f85326a8c1fc522db584e86cdfccd51f   (== docs/x.md)
```

**The vacuity measurement (H-r):** mutant M1 (`if provenance: return []`) applied to a copy of
`scripts/floorsynth.py` → `Ran 29 tests … OK` across `TestOutOfScopeDefects`,
`TestOutOfScopeFixDefaultsToDoNotTouch`, `TestOutOfScopeTargetBytesAreQuoted` and
`TestH2OrdinaryDirtyTreeIsNotBlocked`. The copy was deleted; the repo is clean.

**The structural-pin simulation (§2.1(a))** — reproduced verbatim in Task 9's pre-edit command.

---

## 8. Does this CLOSE H2? — **NO. It NARROWS it.**

The v1.5.2.1 entry overclaimed once and had to be corrected. This section exists so that cannot
happen twice. **The CHANGELOG must say "narrowed", and must reproduce this list.**

### What is closed

The **pre-existing-user-dirt summand**: files that existed, in whatever state, before the coder
was dispatched, and whose **content and mode** are unchanged since. MEASURED: 4 blocking HIGH →
0, and `verdict.gate` UNVERIFIED → OK, on the documented `CHANGELOG.md`:48–57 shape.

### What it additionally buys (not asked for, worth recording)

Three shapes that are **false GREENs in shipped v1.5.2.1** become visible as coverage, because
`change_paths` is baseline-vs-now and a file that returns to baseline or leaves the tree simply
stops appearing: a coder reverting a user's dirty tracked file; a coder deleting a user's
untracked file (MEASURED in Arm B); a pre-existing file replaced by a non-regular file. They are
**printed, never promoted to blocking** — promoting them would add a blocking condition.

### What REMAINS OPEN — six residuals, each measured

**R1 — the verification run's own build output still fires.** `runcheck` executes at
`skills/atlas/SKILL.md`:602; `change_paths` runs at :841. Everything `verify_cmd` writes into
`review_root` is therefore in `full_paths` and **post-snapshot**, so it has no entry and is not
demotable. MEASURED, `_is_residue` is **False** for **coverage.xml**, `build.log`,
**junit-results.xml**, **pytest-report.json**, **coverage.json**, **package-lock.json**, `Cargo.lock`,
`go.sum` and `.env`. This population fires **even on a perfectly clean tree**, so it is a
strictly larger honest-RED source than H2 itself. Task 11 pins it as a negative test. The remedy
is the roadmap's Phase 2 (`scripts/blocking.py::BLOCKING_CHECKS`), which removes the blocking
condition rather than narrowing its input.

**R2 — concurrent human edits.** A file the user saves in another window *during* the run is
absent from the snapshot → not demotable → blocks. The capture-at-CODED placement shrinks the
window to near zero, but the window is real and sits in exactly the interactive lane.

**R3 — a fully forged snapshot demotes.** MEASURED (§7). Content-addressing protects the payload,
not which pointer is read, and no key store exists at uid 0 with a `Bash`-capable coder. Bounded
by two things and no more: the demoted path is still **printed by name**, and the same coder can
already reach a stronger result more cheaply today — MEASURED, rewriting `scope_paths` in
`.atlas/<run_id>/state.json` to `["."]` takes this predicate from 3 blocking to 0 with no
snapshot involved. **T4-F8 is not closed.** This is a third tenant of an already-occupied room,
and it is the only one of the three that is content-addressed at all.

**R4 — the caps.** `MAX_FILE_BYTES` 32 MiB, `MAX_TOTAL_BYTES` 256 MiB, `MAX_ENTRIES` 4096.
Exceeding any of them makes the affected paths non-demotable — today's RED, per path, never a
cliff. A repo with a large uncommitted dataset keeps the false RED on that file.

**R5 — S3(a), the rename-into-scope miss.** Untouched. `git`'s default rename detection collapses
the pair, so today's predicate emits **0 defects** when the guarding test is `git mv`'d into
scope. The `--no-renames` pre-vs-post diff would surface it, but promoting it to blocking would
add a blocking condition. Stays on the roadmap.

**R6 — the residual reaches the human through a model-emitted string.** Task 10's contract test
pins that the **instruction** is present in `skills/atlas/SKILL.md`; nothing at runtime forces
the orchestrator to emit it. This is strictly weaker than a machine gate, and this repo has
already shipped a "the human will see it" channel that nobody reads (`diff.full.patch`, written
at :554, read by nothing). Calling it equivalent would be dishonest.

**R7 — the auto-permission lane is still unnamed.** `skills/atlas/SKILL.md`:423–443 offers a
binary Interactive/Headless branch; MEASURED, `grep -c -i "permission mode"` over that file
returns **0**, and all four `review_root="."` runs in the dogfood corpus reached that state by
model adjudication (one transcript shows the same orchestrator reasoning to a worktree and then
reversing). H2's reachable surface is therefore non-deterministic and **no snapshot fixes that**.
Naming the third lane is cheaper than this whole plan and is worth shipping independently.

### And the frequency question, stated honestly

The 12-run dogfood corpus contains **zero** exposures of H2's trigger condition, so it can bound
the real-world rate in **neither** direction. `scripts/predcov.py` reports `out-of-scope 1/15`,
and MEASURED the single fire is the hand-built `tests/corpus/dirty/changelog-50-57` fixture, not
a recorded run. This work is justified by **severity** — a green `runcheck` and a clean critic set
converted to UNVERIFIED, both refine passes burned, unbounded arity — and by the three false
GREENs it closes. Anyone claiming "H2 is common" or "H2 is rare" from this repo's data is
claiming more than the data supports.

### The competing cheaper option, named rather than buried

The roadmap's Phase 2 already specifies demoting `out-of-scope` from blocking to coverage
wholesale via `scripts/blocking.py::BLOCKING_CHECKS`. That closes H2 **and R1** for a fraction of
this effort, by removing a blocking condition rather than narrowing its input, and it needs no
new state anywhere. What it gives up is the true-positive signal this plan keeps — MEASURED, the
four genuine out-of-scope touches in Arm B. If the project decides that signal is not worth
~200 lines plus three pinned-argument edits, **wholesale demotion is the defensible choice and
this plan should be abandoned rather than built alongside it.** That is a judgment call for the
human, and it should be made against Phase 1's corpus measurement, not against this plan's
elegance.

---

## 9. The falsifiable acceptance test

Two executions. Both must be run on the same fixture and the same snapshot. Neither derives its
expectation from the code under test.

### 9.1 What proves the fix works (the honest arm)

**Execution:** build a git repo with a baseline commit; create the user's own pre-existing dirt —
untracked **notes.txt**, untracked **data/download.csv**, a modification to tracked **docs/x.md**, and
a deletion of tracked **docs/old.md**; set `scope_paths = ["src"]`; take the snapshot; have the
coder edit **only** **src/calc.py**; run the real Step 4+5 fold.

**PASS iff** the blocking count is **0**, `verdict.gate(merged, GREEN)` returns `"OK"`, and all
four user paths appear in `provenance["pre_existing"]`.

**FALSIFIED if** any blocking defect remains, or the gate returns `"UNVERIFIED"`. The expected
values come from `CHANGELOG.md`:48–57 — the CHANGELOG's own description of the defect — not from
the fixture and not from the new code.

**MEASURED today: 4 → 0, UNVERIFIED → OK.**

### 9.2 What would prove the fix itself manufactures a RED

**Execution:** on the same fixture, with the snapshot **valid**, assert that the new blocking id
set is a subset of today's on every arm of the degradation table (`tampered`, `truncated`,
`absent`, `stale-baseline`, `unsafe_location`) **and** on the isolated-worktree lane.

**The fix manufactures a RED if** any arm produces a blocking id that today's
`out_of_scope_defects(full_paths, scope_paths)` does not produce, or if the isolated-worktree
lane's blocking set differs from today's in any way, or if `presnap.capture` /
`presnap.provenance` raises, hangs (the FIFO case: >1 s) or returns non-`bool`/non-`dict`.

**MEASURED today: every degradation row equals today's blocking set exactly; Mode B is a strict
no-op; the FIFO returns in 0.000 s.**

### 9.3 What proves the fix has NOT been hollowed out (the killing test)

The subset property in 9.2 is **satisfied by a mutant that returns `[]` on any provenance** —
MEASURED, `if provenance: return []` passes all 29 of today's out-of-scope rows. It is a refactor
fence, not evidence, and Task 11 labels it as such.

The killing test is the **adversarial arm**, which must be run off the **same** snapshot as 9.1:

**PASS iff** exactly these four still block —
`out-of-scope:"deploy.sh"` (mode-only change), `out-of-scope:"docs/x.md"` (append to the user's
dirty file), `out-of-scope:"evil.py"` (new out-of-scope file), `out-of-scope:"linky"` (repointed
symlink) — and `verdict.gate` returns `"UNVERIFIED"`.

**FALSIFIED if** any of the four is demoted. Each kills a specific hollowing: **deploy.sh** kills
"the mode was dropped from the hash"; `linky` kills "symlinks are dereferenced"; **evil.py** kills
M1; **docs/x.md** kills "the demotion is keyed on the path rather than the content".

**MEASURED today: exactly those four, gate UNVERIFIED.**

### 9.4 The `make ci` bar

```
make ci ; echo "EXIT=$?"
```
`EXIT=0`, with **1682 + N** tests (N ≈ 55–70) and **40** tracked docs, no inventory drift, and
`references/predcov.json`'s `out-of-scope` row relabelled `(pre-provenance)`.

---

## 10. One-paragraph summary for the CHANGELOG

> **H2 (NARROWED, not closed) — the dirty-tree RED.** A pre-coder content-and-mode snapshot,
> taken once at CODED immediately before the coder is dispatched and stored outside the reviewed
> tree, now narrows the input to `out_of_scope_defects`: a path is demoted only when its bytes and
> its mode are byte-identical to what was there before the coder ran. Measured on the shape this
> CHANGELOG documented: four blocking HIGH and `⚠️ UNVERIFIED` become zero and `✅ VERIFIED`, with
> all four user files printed as unreviewed executed surface. No new blocking predicate, no new
> gate key, `scripts/verdict.py` untouched; every degradation of the snapshot — absent, truncated,
> tampered, stale, or an unsafe location — yields exactly today's blocking set. The isolated
> worktree lane is a strict no-op. Three false GREENs shipped in v1.5.2.1 become visible as
> coverage: a coder reverting a user's dirty file, deleting a user's untracked file, or replacing
> one with a non-regular file. **Still open, and stated rather than overclaimed:** the run's own
> build output (**coverage.xml**, `build.log`, `Cargo.lock`, `.env` — none of them residue) is
> written after the snapshot and still fires, on clean trees too; a human editing files during
> the run still fires; a coder that forges the snapshot and recomputes its checksum can demote —
> the path is still printed, and no key store exists at uid 0, so **T4-F8 is not closed**; the
> size caps keep today's RED on large uncommitted payloads; S3(a)'s rename-into-scope miss is
> untouched; and the residual reaches the human through a model-emitted line, which a contract
> test pins as an instruction but cannot guarantee at runtime.
