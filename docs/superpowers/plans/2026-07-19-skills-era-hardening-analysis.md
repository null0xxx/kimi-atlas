# Skills-era hardening — residual-defect analysis & implementation plan (2026-07-19)

**Status:** analysis complete; implementation scheduled as one follow-up atlas run (Section D).
**Tree:** every claim below re-verified today against the live tree at `456b6d3`.

## Executive summary

- Two verified atlas runs (run-1/run-2) merged their critic ledgers into 7 residual LOW defects (D1–D7) across the skills-era scripts and tests; each now has a verified root cause, a minimal fix, and a named regression test (Section A).
- The TOP-1 skill-injection mechanics is fully wired in `skills/atlas/SKILL.md` and this run is its first production exercise — the happy path worked once; the degrade paths are unproven until the dogfood assertions in Section B.3 exist.
- Open audit items are dispositioned: coverage stays behavior-pinned (stdlib-only is deliberate), `skills/repo-audit/scripts/hotfiles.sh` has a reproduced exit-141 SIGPIPE bug with an upstream-able fix, the vendored "secrets" are documentation examples, and the three pending user decisions get explicit recommendations (Section C).
- All fixes are small and near-file-disjoint; Section D orders D1→D7 with files touched, regression tests, and risk notes, packaged as a single atlas run with verify_cmd `make ci`.
- No production-code behavior changes are required beyond D1–D5; D6–D7 are test-only hygiene.

## A. Residual LOW defects (D1–D7)

| ID | Location | Defect | Minimal fix |
|----|----------|--------|-------------|
| D1 | `scripts/skillregistry.py:343-346` | Non-atomic registry write | sibling tmp + `os.replace()` |
| D2 | `scripts/skillregistry.py:148` | Magic literal `2` | `_MIN_SIGNAL_LEN = 2` constant |
| D3 | `scripts/skillselect.py:227-232` | `load_overrides` annotation overstates the contract | coerce at the boundary |
| D4 | `scripts/skillextract.py:116-128` | `'.'` member name passes `_is_safe_entry` | reject empty-parts names |
| D5 | `scripts/skillextract.py:356-358` vs `scripts/skillregistry.py:264-266` | `audit()` failures slot differs across siblings | failures last in both |
| D6 | `tests/test_check_artifact_naming.py:241-254` | Duplicated test scaffold | shared `_TempTreeCase`-style base |
| D7 | `tests/test_skillregistry.py:366` | Dead `out_name` parameter | drop it, inline the literal |

### D1 — non-atomic registry write

**Location:** `scripts/skillregistry.py:343-346` — `main()` writes the registry via a direct `args.out.write_text(json.dumps(registry, ...) + "\n")`.

**Root cause.** No tmp+rename: a kill or OOM mid-`write_text` leaves a torn `references/skill-registry.json` on disk.

**Why LOW.** The blast radius is bounded on every side: the audit gate at `scripts/skillregistry.py:340-341` already guarantees a *failed* audit never writes at all; a torn file fails loudly on the next `json.loads`; the E3 test (`tests/test_skillregistry.py:441`) re-validates the committed registry against the schemas in CI; and the artifact is regenerable on demand via `make skill-registry` (`Makefile:28-29`). No silent corruption is possible — only an obvious one.

**Minimal fix.** Write to a sibling temporary file, then `os.replace()` it onto `args.out` — mirroring `write_artifact_atomic` at `scripts/ctxstore.py:193-209` (the `os.replace` lands at `scripts/ctxstore.py:209`).

**Regression test** (`tests/test_skillregistry.py::TestMain`): (a) success path — after a happy-path run the out directory contains no tmp residue and the file parses; (b) failure path — patch `os.replace` to raise `OSError` and assert the target path keeps its prior bytes (pre-seed it) or never appears.

### D2 — magic literal `2`

**Location:** `scripts/skillregistry.py:148`, inside `extract_triggers` (`scripts/skillregistry.py:126`) — `if len(piece) >= 2 and piece not in signals:`.

**Root cause.** The minimum signal length is an inline literal. The sibling tokenizer names its own floor: `_MIN_TOKEN_LEN = 3` at `scripts/reqcoverage.py:42`, applied at `scripts/reqcoverage.py:59`.

**Why LOW.** Pure readability/consistency debt; the behavior is correct and pinned by `tests/test_skillregistry.py::TestExtractTriggers` (`tests/test_skillregistry.py:96`).

**Minimal fix.** Add module constant `_MIN_SIGNAL_LEN = 2` and use it in the predicate.

**Regression test:** extend `TestExtractTriggers` with the boundary pair — a 1-character signal is dropped, a 2-character signal is kept.

### D3 — overstated `load_overrides` annotation

**Location:** `scripts/skillselect.py:227-232` — declared `-> dict | None`, but the body returns raw `json.loads(...)` output, so a JSON document of ANY type (list, string, number) passes through annotated as `dict`.

**Root cause.** The parse result is returned uninspected; the only type guard lives downstream in `select()` at `scripts/skillselect.py:144` (`overrides if isinstance(overrides, dict) else {}`).

**Why LOW.** Behavior is safe today precisely because `select()` coerces; the defect is a lie in the contract, hazardous only to a future caller that trusts the annotation.

**Minimal fix.** Coerce at the boundary: `doc = json.loads(...)`; `return doc if isinstance(doc, dict) else None`. This keeps the honest `dict | None` contract and matches the existing "absent → None" semantics (the absent-file branch at `scripts/skillselect.py:230-231`). Widening the annotation instead is rejected: it would push the isinstance duty onto every future caller.

**Regression test** (`tests/test_skillselect.py::TestBoundaries`, `tests/test_skillselect.py:232` — the absent-file case at line 255 is the sibling): an overrides file containing a JSON array returns `None`; a JSON object returns the dict.

### D4 — `'.'` member name accepted

**Location:** `scripts/skillextract.py:116-128` `_is_safe_entry`.

**Root cause.** `PurePosixPath('.')` has empty `parts` and is not absolute (verified in the interpreter today: `parts == ()`), so the name clears both checks at `scripts/skillextract.py:125-128`. The enforcement twin `_confined_target` (`scripts/skillextract.py:210-222`) accepts it too and resolves the member onto the package directory itself; `write_bytes` then raises `IsADirectoryError` mid-extract. Reproduced in-memory today against the live module: `_is_safe_entry('.')` → `True`, target == package dir, `write_bytes` → `IsADirectoryError`.

**Why LOW.** It is a loud crash, not a traversal — confinement is never breached, and hostile archives only arrive via operator-supplied zips. Still, it escapes the module's own contract: a hostile name is supposed to be a recorded *plan failure* before anything is written (`tests/test_skillextract.py:153-175` pin the preflight rejection; `tests/test_skillextract.py:186-195` pin "a hostile name is a plan FAILURE … and nothing is extracted"). The `'.'` member instead aborts the whole run with an unhandled exception, potentially after earlier members of the same package were already written — a half-extracted package.

**Minimal fix.** Reject empty-parts names in `_is_safe_entry`: `if not pure.parts: return False`.

**Regression test:** add the unit case beside `tests/test_skillextract.py:177-180` (`_is_safe_entry(".")` is `False`) and a plan-level case beside `tests/test_skillextract.py:190-195` (a zip whose member is `.` is a recorded plan failure keyed on the skill name, never a crash).

### D5 — sibling `audit()` argument-order mismatch

**Locations:** `scripts/skillextract.py:356-358` `audit(plans, failures, manifest)` (failures 2nd) vs `scripts/skillregistry.py:264-266` `audit(entries, manifest_skill_count, failures)` (failures 3rd).

**Root cause.** Two siblings evolved one audit-line contract — per-category counts, one line per failure, the reconciliation check, the trailing `AUDIT ok` / `AUDIT MISMATCH` verdict line — with the `failures` parameter in different slots.

**Why LOW.** Every live call site is positionally correct today (`scripts/skillextract.py:459`, `scripts/skillextract.py:475`, `scripts/skillregistry.py:337`). The hazard is purely future: a cross-module copy-paste would slot failures into the wrong position and compile clean.

**Minimal fix.** Put `failures` last in both: change the extractor's signature to `audit(plans, manifest, failures)` and update its two call sites plus the positional test calls in `tests/test_skillextract.py::TestAudit` (`tests/test_skillextract.py:386`; calls at lines 395, 407, 414).

**Regression test:** the existing `TestAudit` assertions pin the emitted lines unchanged; the reorder is behavior-neutral, so the green suite *is* the regression proof.

### D6 — duplicated test scaffold

**Location:** `tests/test_check_artifact_naming.py` — `TestSkillPackageExemption` (class at line 241) re-defines `setUp`/`tearDown`/`_touch` (lines 244-254) verbatim vs `TestMainEndToEnd` (lines 151-156 and 164-167).

**Root cause.** The exemption class was added by copy-paste after the end-to-end class.

**Why LOW.** Test-only duplication; zero production impact; the risk is the two copies drifting.

**Minimal fix.** Hoist a small shared base class in the file — the `_TempTreeCase` idiom at `tests/test_skillpkgs.py:17-36`. Hoist only `setUp`/`tearDown`/`_touch`: the two `_run` helpers genuinely differ (`tests/test_check_artifact_naming.py:158-162` takes `*extra_args`; `:256-260` does not).

**Regression test:** none new — both classes' tests must stay green unchanged, which is the proof the hoist was behavior-neutral.

### D7 — dead parameter

**Location:** `tests/test_skillregistry.py:366` — `def _args(self, root, mapping, out_name="registry.json"):`.

**Root cause.** The `out_name` parameter anticipates a caller that never materialized: all four call sites (lines 379, 397, 412, 423) pass only `(root, mapping)`.

**Why LOW.** Dead flexibility in a test helper; no behavior involved.

**Minimal fix.** Drop the parameter and inline the `"registry.json"` literal at line 370.

**Regression test:** none new — suite green is sufficient.

## B. TOP-1 skill-injection mechanics — wired vs production-proven

### B.1 What is wired (verified against the tree)

- **Selection + persistence (GROUNDED):** `skills/atlas/SKILL.md:248-267` ranks the committed registry (`references/skill-registry.json`) against the frozen intent and persists the selection as `.atlas/<run_id>/skills.json`; any exception degrades to `[]` and never blocks the machine (`skills/atlas/SKILL.md:262-263`). Every result carries the on-disk package `path` via `_public` at `scripts/skillselect.py:184-195` (line 191).
- **Injection policy:** `skills/atlas/SKILL.md:268-284` — the TOP-1 result's `skills/<name>/SKILL.md` body is read from disk and injected into the CODED packet as the ACTIVE skill under SAFE-2 untrusted-content framing (lines 271-277); the remaining top-3 go in as advisory references only (lines 278-281); an absent/unreadable package file degrades to no-ACTIVE-skill without blocking. User steering via `references/skill-overrides.json` is documented at lines 282-284.
- **CODED dispatch:** `skills/atlas/SKILL.md:334-336` reads the persisted `.atlas/<run_id>/skills.json` back (absent → `[]`) and applies the policy — TOP-1 body ACTIVE, rest advisory, never widening `scope_paths`.

### B.2 What is production-proven

Until this run: **nothing.** This run (run 3 of its session) is the mechanics' first live exercise, and it validates the happy path end-to-end exactly once:

1. `.atlas/<run_id>/skills.json` was persisted at GROUNDED with three entries — TOP-1 `repo-audit` (score 12.0), `incident-review-guide` (9.0), `process-doc` (8.0) — each carrying `name`, `category`, `path`, `matched_tokens`, and a human-readable `why` (e.g. `"matched name[audit, repo] + triggers[analysis, what] + description[secrets] + category-prior[Engineering]"`).
2. The CODED packet for this very document contained the complete TOP-1 body (`skills/repo-audit/SKILL.md`) inside explicit SAFE-2 markers, with the skill's on-disk payload paths under `skills/repo-audit/` named, plus the 2nd/3rd skills as advisory references with paths and scores.
3. The framing held: the injected body informed Section C.2's analysis without altering the frozen intent, success criteria, or scope — SAFE-2 as designed.

One happy-path datapoint says nothing about the degrade paths (absent registry, unreadable TOP-1 package) or about selection correctness under adversarial input. That is what the dogfood must close.

### B.3 Dogfood validation approach (follow-up)

Deterministic assertions, in the spirit of `scripts/run_negative_gate.py` and its `tests/fixtures/` matrix (good → OK, each `bad_*` → UNVERIFIED), with `scripts/dogfood_weave.py` as the model for a scripted harness:

| # | Assertion | How |
|---|-----------|-----|
| 1 | **Persistence** — after GROUNDED, `.atlas/<run_id>/skills.json` exists, parses, and every entry carries `name`/`category`/`path`/`why` with `path` resolving under `skills/` | harness inspects the run ledger |
| 2 | **Injection** — the CODED packet contains the TOP-1 `skills/<name>/SKILL.md` body verbatim inside the SAFE-2 markers, and names the on-disk payload dir | packet capture diff |
| 3 | **Advisory-only** — 2nd/3rd results appear as names + paths + `why`, bodies absent | packet capture diff |
| 4 | **Degrade: absent registry** — in a sandbox run with the registry file renamed away, `.atlas/<run_id>/skills.json` == `[]` and the machine continues to the human gate (selection never blocks) | scripted sandbox run |
| 5 | **Degrade: unreadable TOP-1 package** — a registry entry whose `path` has no readable SKILL.md yields an advisory list with no ACTIVE skill | fixture registry + packet capture |
| 6 | **Negative-gate fixture for selection** — a malformed-JSON registry fixture degrades the run instead of crashing it; an `exclude`-beats-`pin` fixture proves override semantics end-to-end (unit-level semantics already pinned in `tests/test_skillselect.py::TestOverrides`, `tests/test_skillselect.py:151`) | extend the negative-gate fixture matrix |

## C. Open audit items

### C.1 Coverage measurement — coverage.py absent

`import coverage` raises `ModuleNotFoundError` (re-verified today). This is deliberate: the project is stdlib-only and says so (`README.md:196`), which is what keeps the E3/E4 committed-artifact tests zip-free and runnable anywhere.

- **Option (a):** accept the behavior-pinned suite design. The atlas harness mechanically enforces collected tests plus failure-path assertions, and every script carries a `tests/test_<module>.py` by convention (`README.md:196`).
- **Option (b):** introduce a dev-only virtualenv with coverage.py — nothing committed — behind a `make coverage` target that skips cleanly when the module is absent.

**Recommendation: (a) now, (b) only on demand.** A coverage percentage adds a number but no gate, and a committed dev-dependency would erode the constraint that makes CI trivially reproducible. If a future refactor wave wants heat-maps, adopt (b) strictly uncommitted.

### C.2 `hotfiles.sh` — silent exit 141

**Root cause (reproduced today on this repo):** `skills/repo-audit/scripts/hotfiles.sh:2` sets `set -euo pipefail`, and the pipeline at `skills/repo-audit/scripts/hotfiles.sh:64` ends in `head -n "$TOP_N"`. `head` exits after N lines and closes the pipe; the upstream `sort -rn` dies of SIGPIPE (128+13 = 141); `pipefail` makes the command substitution's status 141; `set -e` aborts the script at the assignment — before any output. Running `bash skills/repo-audit/scripts/hotfiles.sh --top 5` here yields empty stdout and EXIT=141; even the empty-result branch (lines 66-69) is never reached. The failure triggers whenever the pre-limit stream exceeds one pipe buffer — i.e. on any real repository.

**Fix proposal (upstream-able):** consume before trimming — drop `| head -n "$TOP_N"` from the line-64 substitution so no writer outlives its reader, and apply the limit in the emission loop (lines 76-88) instead. A documented git-native fallback for the same data: `git log --numstat --pretty=format: | awk 'NF==3 {c[$3]++} END {for (f in c) print c[f], f}' | sort -rn | head` — verified on this repo today (top row: `tests/test_scheduler.py`, 13 commits).

**Constraint:** the skill is vendored third-party content whose bytes are manifest-anchored — a local patch makes `tests/test_skillextract.py::TestCommittedManifest` fail (the drift alarm working as designed). Prefer upstreaming; re-anchor the manifest only if a local patch is ever taken.

### C.3 Vendored doc-example "secrets"

Scanners flag three locations, all verified today as expected third-party documentation examples, not leaks:

- `skills/code-vuln-audit/SKILL.md:108` and `:132` — AWS's canonical documentation example key `AKIAIOSFODNN7EXAMPLE`, carried as a detection *sample*;
- `skills/code-vuln-audit/SKILL.md:62` — a `-----BEGIN PRIVATE KEY-----` pattern-sample table row;
- `skills/gitlab-cli-skills/glab-auth/references/commands.md:37` and `:165` — `glpat-xxx` / `glpat-xxxxxxxxxxxxxxxxxxxx` placeholders in usage examples.

A fresh run of `skills/repo-audit/scripts/secret-scan.sh --branch main --severity high` today confirms the classification: every HIGH hit is one of the locations above, all introduced by the vendoring commit `115fee7`; no first-party secret appears in history.

**Policy recommendation:** leave the vendored bytes as-is (the manifest anchors them; editing would trip `TestCommittedManifest`). If a scanner gate is ever added to CI, allowlist these two files rather than editing third-party content.

### C.4 Pending user decisions

- **Untracked 41 MB `Skills/` zips (117 archives).** `README.md:215` documents them as a one-time import source, intentionally not committed. Options: keep-local / delete / gitignore. **Recommendation:** add `Skills/` to `.gitignore` now — zero-risk, silences `git status` noise, and keeps the byte-identical import source for disaster recovery. Deletion is safe later: `references/skills-manifest.json` anchors the extracted tree, and `tests/test_skillextract.py::TestCommittedManifest` re-proves it in CI.
- **73.4 MiB binary `skills/xlsx/scripts/Xlsx` (77,001,601 bytes).** Exceeds GitHub's 50 MB push warning (hard limit 100 MB). Options: keep vs Git LFS. **Recommendation: keep.** The warning is cosmetic and the hard limit is not hit; LFS migrates history (rewriting commits) and, worse, an LFS pointer file would break the manifest re-hash in `tests/test_skillextract.py::TestCommittedManifest` on any checkout without LFS smudge — including CI. Revisit only if the file grows toward 100 MB.
- **`shell=True` at `scripts/suiterun.py:88` (call site `scripts/suiterun.py:86-92`).** Confirmed by design: the command is an operator-supplied verify_cmd from internal callers, and any subprocess/timeout failure degrades to `{}` (`scripts/suiterun.py:93-94`). **Recommendation:** accept and document it as a named trusted boundary — a comment at the call site plus a line in `references/architecture.md` (the comment is a code change, scheduled in Section D). SAST-style heuristics will always flag this line; naming the boundary is the durable answer.

## D. Ordered implementation plan (follow-up run)

One recommended atlas run bundling D1–D7 — all small, near-file-disjoint — with verify_cmd `make ci`. Order follows the D1→D7 ledger; the risky steps are D1 and D4 (audit-gated writer / security-hardened extractor), so the hostile-input matrix (tests/test_skillextract.py:153-195) must stay green throughout.

| Step | Files touched | Fix | Regression test | Risk note |
|------|---------------|-----|-----------------|-----------|
| D1 | `scripts/skillregistry.py`, `tests/test_skillregistry.py` | tmp sibling + `os.replace()` per `scripts/ctxstore.py:193-209` | `TestMain`: no tmp residue; patched-`os.replace` failure preserves prior bytes | Touches the audit-gated writer; keep "failed audit never writes" (`scripts/skillregistry.py:340-341`) intact |
| D2 | `scripts/skillregistry.py`, `tests/test_skillregistry.py` | `_MIN_SIGNAL_LEN = 2` constant | `TestExtractTriggers` boundary pair (1-char dropped, 2-char kept) | None — rename-only semantics |
| D3 | `scripts/skillselect.py`, `tests/test_skillselect.py` | coerce `json.loads` result to `dict | None` at the boundary | `TestBoundaries`: JSON array → `None`; object → dict | Callers already tolerate non-dict (`scripts/skillselect.py:144`) |
| D4 | `scripts/skillextract.py`, `tests/test_skillextract.py` | `if not pure.parts: return False` in `_is_safe_entry` | unit case (`'.'` → unsafe) + plan-level recorded-failure case | Security-hardened extractor: the hostile-name matrix (`tests/test_skillextract.py:153-195`) must stay green; confirm no legitimate archive relies on `'.'` |
| D5 | `scripts/skillextract.py`, `tests/test_skillextract.py` | `audit(plans, manifest, failures)` — failures last in both siblings | existing `TestAudit` assertions unchanged | Update both call sites (`scripts/skillextract.py:459`, `:475`) and the positional test calls together — a partial reorder compiles clean and inverts output |
| D6 | `tests/test_check_artifact_naming.py` | shared `_TempTreeCase`-style base (`tests/test_skillpkgs.py:17-36` idiom) | existing tests green unchanged | Hoist only setUp/tearDown/`_touch`; the two `_run` helpers differ |
| D7 | `tests/test_skillregistry.py` | drop `out_name`, inline the literal | suite green | Test-only |

**C-items actionable in the same or a later run:**

- **hotfiles.sh (C.2):** no repo change — draft the upstream issue/patch (consume-before-trim). Local patching is blocked by the manifest anchor.
- **`Skills/` gitignore (C.4):** one-line `.gitignore` edit, gated on the user's decision.
- **suiterun trusted boundary (C.4):** one comment at `scripts/suiterun.py:86-92` plus a line in `references/architecture.md`; file-disjoint from D1–D7, safe to bundle.
- **Dogfood (B.3):** a separate run — it builds harness/assertions, not defect fixes; bundle assertions 1–3 first (happy-path evidence), then the degrade/negative fixtures 4–6.

---

*Related index entry: linked from `references/skill-registry.md` (inventory-drift gate). Defect ledger sources: run-1/run-2 merged critic ledgers under `.atlas/<run_id>/`.*
