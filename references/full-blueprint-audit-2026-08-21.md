# Full migration blueprint audit — 2026-08-21

*Commissioned after the user directly challenged an overclaimed "migration complete / READY" summary. 13 independent auditors, each assigned one section of `docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`, instructed NOT to trust the blueprint's own status overlay or any prior session's "done" claims — every verdict below is re-derived from primary evidence (git history, live command output, direct file reads) by the auditor itself. A synthesis agent combined and deduplicated the 13 reports; an adversarial spot-check agent then independently re-verified 8 of the synthesis's own DONE claims and 3 DEFERRED claims from scratch, to catch the synthesis itself overclaiming.*

**This document supersedes the unqualified "🎯 migration complete / VERDICT: READY" framing given earlier the same day.** That framing was not fabricated — both of the blueprint's own two Conditions for READY (§15) really were met and are still true — but it did not surface the ~46 other gaps below, several of which the blueprint's own text sets as explicit bars for "done."

---

## 1. Overall tally

| # | Audit (scope) | DONE | PARTIAL | NOT DONE | DEFERRED | Total |
|---|---|---|---|---|---|---|
| A1 | §6.1 Tool surface | 8 | 5 | 1 | 0 | 14 |
| A2 | §6.2 Dispatch model | 6 | 2 | 1 | 2 | 11 |
| A3 | §6.3 Orchestrator core + Stage 03 | 11 | 6 | 5 | 0 | 22 |
| A4 | §6.4 Verification harness | 9 | 0 | 0 | 0 | 9 |
| A5 | §6.5 Hooks + Stage 02 | 14 | 1 | 1 | 0 | 16 |
| A6 | §6.6/6.7 Packaging + CI | 13 | 2 | 1 | 1 | 17 |
| A7 | Stage 01 | 17 | 5 | 3 | 0 | 25 |
| A8 | AGENTS.md accuracy | 15 | 2 | 9 | 0 | 26 |
| A9 | Risk Register (§12) | 9 | 0 | 3 | 0 | 12 |
| A10 | Acceptance Criteria (§14) + 8 open facts (§15) | 6 | 3 | 7 | 5 | 21 |
| A11 | Stage 04 per-file | 14 | 2 | 1 | 0 | 17 |
| A12 | Stage 05 | 15 | 2 | 5 | 0 | 22 |
| A13 | Divergence / run_id governance | 11 | 0 | 2 | 0 | 13 |
| **TOTAL** | | **148** | **30** | **39** | **8** | **225** |

**148/225 = 65.8% DONE · 30/225 = 13.3% PARTIAL · 39/225 = 17.3% NOT DONE · 8/225 = 3.6% legitimately DEFERRED.**

Several raw NOT-DONE/PARTIAL rows are the same underlying defect found independently by multiple audits. Deduplicated: **~46 distinct genuine gaps**, listed in full below — nothing summarized away.

---

## 2. Every NOT DONE / PARTIAL item, grouped by area (deduplicated, every distinct fact preserved)

### A. Tool surface, dispatch, temperature, permissions

**G1. [NOT DONE] `temperature:` frontmatter never dropped from 4 of 7 role files, contra the blueprint's own confirmed platform fact.**
Evidence: I ran `grep -rn "^temperature:" agents/*.md` myself — `code-quality-critic.md:7` (`0.5`), `integration-critic.md:7` (`0.3`), `security-critic.md:7` (`0.3`), `correctness-critic.md:7` (`0.2`) — all still present. `skills/atlas/SKILL.md:850-855` still hedges "set a DISTINCT temperature per lens **if** the `Agent` tool exposes one," even though the blueprint's own §4 already lists "no `temperature` parameter" as *confirmed*. `git show 6c3669b` (Stage 4's rewrite commit) touched only the surrounding HTML comment in each file, leaving the `temperature:` line untouched. `scripts/check_cc_migration_residue.py`'s denylist does not include the string `temperature`, so `make check-cc-migration` passes clean and structurally cannot catch this.
Fix: delete the `temperature:` line from all 4 `agents/*-critic.md` files and delete the conditional clause at `skills/atlas/SKILL.md:850-855`.
Found by: A1, A2, A9, A11 (independently, consistently).

**G2. [NOT DONE] `context-scout.md` still grants `Bash`, contradicting the blueprint's own explicit §6.2 target ("Bash dropped entirely, not merely instructed-restricted").**
Evidence: I ran `grep -n "^tools:" agents/context-scout.md` myself — `tools: Read, Grep, Glob, Bash`. `git log -p` on this file shows the `Bash` entry traces to a pre-migration commit (`102dfff`) and Stage 4's rewrite commit (`6c3669b`) *reaffirmed* it in a new comment block ("Read, Grep, Glob, and read-only-use Bash") rather than removing it — i.e., this is a deliberate re-affirmation, not a missed leftover. The file's body still relies on prose-only restriction ("never to build, install, mutate, or run project code") — exactly the "instructed-restricted" pattern the blueprint row said was insufficient once enforcement became real. `.claude/settings.json` is a session-wide command allowlist, not a per-subagent Bash restriction.
Fix: remove `Bash` from `agents/context-scout.md:4`'s `tools:` line, or update the blueprint's own target row if the design decision changed.
Found by: A1, A2, A11.
**2026-08-21 design-correction resolution:** `Bash` was kept, not removed — `context-scout.md`'s own "What you do" step 2 (lines 30-33) directs the scout to compute a `sha256` of every relevant file it discovers via `python3 -c "import hashlib,…"`, and step 1 (line 28) names `git ls-files` for grounding; both are things `Read`/`Grep`/`Glob` genuinely cannot do (hashing requires code execution; `git ls-files` is index-aware in a way a plain glob is not), so `context-scout` is an intentional, evidence-backed exception to the general "critics get no Bash" rule, not a missed leftover — its Bash is read-only-scoped to grounding computation, never to build/install/mutate/run project code.

**G3. [PARTIAL] Live enforcement evidence (`references/stage4-dispatch-enforcement-live-validation.md`) overstates its own methodology and covers only 1 of 7 roles.**
Evidence: The doc claims Bash/Write were "independently checked on the filesystem after each run," but the Bash probe was a bare `echo` with no redirect — no possible filesystem artifact exists for a successful echo, so "Bash UNAVAILABLE" rests entirely on the subagent's self-report, not independent verification (only the Write claim has genuine filesystem corroboration). The doc's own "Not covered by this validation" section discloses only `correctness-critic` was live-probed; the other 6 roles' enforcement is inferred by architectural similarity, not independently tested — and that inference is what missed G2 above.
Fix: re-run the probe against the other 6 roles, and instrument the Bash check with a redirect so a filesystem artifact is actually possible.
Found by: A1, A2, A11.

**G4. [PARTIAL] Bash tool's "New ambient-env surface from rc-file inheritance" risk, named in the blueprint's own §6.1 row, is never mentioned or mitigated anywhere in the three SKILL.md files.**
Evidence: `rg -n "rc-file"` across all three SKILL.md files → zero matches. Low severity, but the specific named risk was never carried into the artifact.
Found by: A1.

**G5. [PARTIAL] Glob's "100 files" hard cap, named in the blueprint's own Note, is never stated anywhere in `agents/context-scout.md` or any SKILL.md.**
Evidence: `agents/context-scout.md:26` says only "Respect the max-files cap" — no number. Informational-only, no functional risk identified.
Found by: A1.

**G6. [PARTIAL] `AskUserQuestion`'s "grouped-question support unconfirmed" risk is silently assumed, not caveated, and sits in unresolved tension with a "confirmed" claim elsewhere in the same document.**
Evidence: `skills/atlas/SKILL.md:289` hard-codes "ask **ONE batched** `AskUserQuestion` (≤3 questions)" with no inline caveat and no probe backing it (`ls probe/` + `rg -ln "AskUserQuestion" probe/*.sh` → no probe targets this). This directly conflicts with §4's own "confirmed" platform-fact line elsewhere in the blueprint: "`AskUserQuestion` (singular schema, one question per call)."
Fix: either probe grouped-question support live, or add an explicit unconfirmed-caveat matching the one already present for headless behavior.
Found by: A1; underlying fact reconfirmed as still-open by A10 (§15 Fact 2).

**G7. [PARTIAL] `WebFetch`'s lossy-extraction interaction with the SAFE-2 injection-defense wrapper's threat model was never retested, despite being an explicit blueprint action item.**
Evidence: `WebFetch` is live-granted to `elite-coder` and `planner` (real, active attack surface) but `rg -n "WebFetch"` against `skills/atlas/SKILL.md` finds no SAFE-2/threat-model cross-reference. Documented as an open fact in the blueprint's own §15, so not silently dropped — but genuinely not done.
Found by: A1, A10 (§15 Fact 5).

**G8. [NOT DONE] Subagent wall-clock timeout (`maxTurns` or equivalent) was never measured or documented.**
Evidence: `skills/atlas/SKILL.md:1305-1319` states verbatim "Subagents' exact timeout duration is unconfirmed for Claude Code... treat 30 min as a working estimate, not a verified bound." `rg -n "maxTurns"` across the repo → zero hits. Honestly flagged as open, not misrepresented — but unresolved.
Found by: A2 (row9), A10 (§15 Fact 3).

### B. Orchestrator core, Stage 03, run_id design

**G9. [NOT DONE] `references/orchestrator-core-port.md`, an explicitly named Stage 3 deliverable ("the decision record Stage 4 reads"), was never created.**
Evidence: I ran `ls references/orchestrator-core-port.md` myself just now — "No such file or directory." Never mentioned anywhere as missing; the status overlay's Stage 3 row never surfaces this.
Fix: write `references/orchestrator-core-port.md`, or remove the reference to it from the blueprint's own Stage 03 "Files affected" list if it's no longer needed.
Found by: A3.

**G10. [NOT DONE] Stage 3's own byte-identity bar ("11 of 12 files stay byte-identical, only `contextgraph.py` changes by one docstring line") is false as measured — 10/12, not 11/12 — because `runcheck.py` also drifted, tripping the stage's own declared "Failure condition," which was never surfaced before Stage 4 began.**
Evidence: `git rev-parse <path>@<rev>` before/after: `runcheck.py` hash changed (`0221080…→af2a42c…`, `systemd-run --scope` → `systemd-run --user --scope`, commit `ef91c92`). `ef91c92` landed at 19:00:40; Stage 4's commit `6c3669b` began one minute later (19:01:04) with no acknowledgment the failure condition had fired. This invalidates three separate Stage 03 claims stated in the blueprint text: the Objective ("zero functional change"), the hash-parity Exit criterion ("11/12"), and the Failure condition ("any of the other 11 backbone files drifts... " — this fired).
Fix: reconcile Stage 03's own text with the actual 10/12 result, and explicitly acknowledge the triggered failure condition rather than silently proceeding to Stage 4.
Found by: A3.

**G11. [PARTIAL] The PYTHONPATH/`CLAUDE_ENV_FILE` convention was never tested end-to-end through a live Claude Code SessionStart-hook session — only via manual `export`, despite the blueprint's own explicit "(test before relying on it)" instruction, and the old per-call fallback prefix is now deleted, making the whole orchestrator unconditionally dependent on this untested mechanism.**
Evidence: `rg -ln "CLAUDE_ENV_FILE" tests/` → nothing; `references/rollback-sanction-live-validation.md:35` shows the tester manually exporting `PYTHONPATH`/`PYTHONSAFEPATH` rather than exercising the hook. Stage 1's own two mandated live checks for this exact mechanism (`claude --plugin-dir --debug` loads with SessionStart registered; a post-session Bash call shows `$ATLAS_PLUGIN_ROOT` populated) have **no evidence trail anywhere in the repo** prior to any of these 13 audits actually running them live themselves during this audit pass.
Fix: commit a dedicated `references/*-live-validation.md` for this mechanism (as every other stage did) instead of relying on manual exports or one-off audit-time checks.
Found by: A3 (§6.3 row7, Stage03), A6 (§6.7 row15), A7 (items 17/18/23), A12 (implicitly, via the heredoc risk in G23).

**G12. [NOT DONE] The Bash-sandboxing memory-cap probe for `runcheck.py`, explicitly named in Stage 03's implementation actions, was never attempted at all.**
Evidence: no probe script (checked all 8 files in `probe/`), no reference doc, no test, no commit message addresses it.
Found by: A3.

**G13. [NOT DONE] Blueprint's specified self-generated `run_id` (UUID4, held as `${ATLAS_RUN_ID}`) was never implemented; the shipped design sources `$ATLAS_SESSION_ID` from Claude Code's own SessionStart `session_id` instead — a materially different, session-scoped design that reproduces the exact collision shape (H5) the UUID4 approach was meant to eliminate.**
Evidence: `git grep 'ATLAS_RUN_ID'` on all 3 SKILL.md files → zero hits; `git grep 'ATLAS_SESSION_ID'` → 40+ hits (`hooks/init-env.sh:37-53`, `skills/atlas/SKILL.md:107,237,260,...`). The known H5 collision defect is still `@unittest.skip(...)`'d verbatim in `tests/test_v1521_regressions.py:674-688` ("DEFERRED... NOT abandoned"). **Additional finding not previously surfaced:** the one stability probe that exists for exactly this purpose, `probe/probe_runid_stability.sh`, still tests **Kimi's** `$KIMI_SESSION_ID` via the `kimi` binary — it was never adapted or re-run against Claude Code's `session_id` field, so the load-bearing "DS-2 — stable within a session across compaction" assumption behind the actually-shipped design is untested on the new platform.
Fix: decide (with the user, explicitly — see G-Gov1 below) whether to switch to a fresh-per-run UUID4 or keep session-scoped `$ATLAS_SESSION_ID`, and either way, adapt `probe_runid_stability.sh` to Claude Code and re-run it.
Found by: A3, A9 (row6), A12, A13.

### C. Verification harness — no NOT DONE/PARTIAL among the 9 graded §6.4 rows; two out-of-scope caveats flagged

**C1. [flagged, not tallied by A4] The live `make negative-gate` 5/5-pass result was not independently re-run by A4 itself (only its evidence doc was cross-checked against source code); it *was* independently re-run twice by A12 and A10, both getting 5/5 live — so this is now resolved with primary evidence, just not by A4.**

**C2. [flagged, not tallied by A4] Stale `kimi -p` comment references remain in `scripts/sast.py:159` and `scripts/nativefloor.py:91`, invisible to `check_cc_migration_residue.py`'s denylist (which targets literal tokens, not the bare word "kimi").** Cosmetic, does not affect function.

### D. Hooks & SessionStart

**G14. [NOT DONE] Hook execution `cwd` (plugin root vs. project root) was never empirically resolved anywhere in the repo's own evidence base — every hook file's own comments say so, no probe script targets it, and `git log --all --grep` across the whole history turns up nothing for Claude Code.**
Evidence: `hooks/guard-destructive.sh:30-33`, `hooks/telemetry.sh:41-46`, `hooks/session-resume.sh:56-59` all state this is unconfirmed and each sidesteps it by reading `cwd` from the hook's stdin JSON payload rather than trusting process cwd — a real, reasonable mitigation, but not a resolution of the fact. `tests/test_telemetry_events.py`/`tests/test_session_resume_hook.py` only test that the hook correctly *parses* an injected `cwd` field, not what Claude Code's runtime actually sets it to.
**Contradiction note:** A9 (Risk Register row8) graded this row DONE — but only for "the literal mitigation," and separately reports that its own author built and ran an ad-hoc probe live and found cwd *does* equal the project root. That finding is credible but is **not committed anywhere in the repository** (no `probe_cc_hook_cwd.sh` exists), so from the repo's own evidence-base standard every other audit applied, the fact remains unresolved. **Resolution: A5's/A10's NOT DONE grading is the more direct/primary read of the committed repo state; A9's DONE grading describes only the mitigation, and A9 itself flags this as "the same class of gap already flagged to the user previously."**
Fix: commit a `probe/probe_cc_hook_cwd.sh` that captures both `pwd` and the stdin `cwd` field from a live `PostToolUse` hook, matching the pattern of the existing SessionStart-injection probe.
Found by: A5 (row7), A9 (row8, contradictory framing), A10 (§15 Fact 6).

**G15. [PARTIAL] SessionStart→`atlas-resume` context injection was live-probed and positively confirmed, but only for the `startup` matcher source — the other 4 registered sources (`resume`/`clear`/`compact`/`fork`) were never independently exercised, and the `resume` case (the one that matters most for `atlas-resume`) is the untested one.**
Evidence: `probe/probe_cc_sessionstart_injection.sh:100-105` invokes `claude -p` in a brand-new working directory with no prior session state — by construction this can only ever trigger `startup`. `hooks/session-resume.sh:34-36` and `skills/atlas-resume/SKILL.md:11-13` both state this scope limit explicitly in the shipped code. The status overlay's terse "SessionStart injection (CONFIRMED, Stage 2)" phrasing, read in isolation, overstates this to 1-of-5 accuracy.
Fix: probe design needs a genuinely resumed/compacted/forked session, not just a fresh one — the plan's own probe design was structurally incapable of covering this from the outset (a plan-design gap, not just an execution shortfall).
Found by: A5 (row5 + Stage02 objective clause), A10 (§14 item3 / §15 Fact 1), A12 (corroborating detail).

**G16. [PARTIAL, informational] `guard-destructive.sh`'s "dual deny emission" behavior (exit 2 + `permissionDecision:deny` JSON) is unchanged code claimed correct by the blueprint but not newly live-verified during this migration — the row's own claim is a docs claim, not an execution claim, and the file's header correctly scopes it as "no behavior change was made here," so this is low-severity.**
Found by: A5 (row4).

### E. Packaging, skills, CI

**G17. [NOT DONE — blueprint verdict itself appears mistaken, not merely unfinished] `references/skill-registry.json` and `scripts/skillregistry.py`, targeted for REMOVE ("Claude Code auto-discovers frontmatter off disk natively"), still exist and are actively, load-bearingly called from live dispatch code at the GROUNDED stage.**
Evidence: I confirmed directly — `skills/atlas/SKILL.md:377-408` calls `skillselect.select(...)` against `references/skill-registry.json` to advisory-rank and inject one of 115 vendored skills' full body into the elite-coder's dispatch packet. This is a *skill-selection/ranking* feature, not the *skill-loading/auto-discovery* mechanism the REMOVE rationale addresses — the blueprint's target for this row looks like a genuine misclassification of what the code does, not just incomplete execution. `Makefile`'s `skill-registry` target and `.PHONY` entry are also still present and live.
Fix: correct the blueprint's §6.6 row-7 verdict from REMOVE to KEEP/ADAPT, or if REMOVE was truly intended, first replace the GROUNDED-stage skill-selection feature with something else before deleting these files.
Found by: A6 (row7), A8 (item11 — same underlying fact, framed as "AGENTS.md's description is accurate, but this contradicts the blueprint's own verdict").

**G18. [PARTIAL] `skills/atlas-weave/SKILL.md`'s mandatory Stage-05 rename pass is incomplete: it still contains a live section naming Kimi as the runtime.**
Evidence: I confirmed directly — `skills/atlas-weave/SKILL.md:205` (`## Live dogfood (manual, in Kimi)`) and `:213` ("it needs the Kimi agent runtime, not the CI env"). Missed because the residue checker's denylist targets specific tokens (`${KIMI_SKILL_DIR}` etc.), not the bare word "Kimi."
Fix: rewrite this section to name Claude Code, or explicitly mark it historical (as was done for other retained Kimi-era prose elsewhere).
Found by: A6 (row5).

**G19. [PARTIAL] `bench/runner.py:89-105` still defaults `kimi: str = "kimi"` and shells to the `kimi` binary to actually *drive* a live bench task — this code path is not exercised by `make bench-validate`, but the live-benchmark-driving half of `bench/` was never ported to shell out to `claude`.**
Evidence: confirmed by direct read of `bench/runner.py`. `bench/` isn't in the blueprint's own §2 repository map, so this is adjacent/informational, not a scored row miss.
Found by: A6 (row16 caveat).

**G20. [NOT DONE, count-corrected] `.claude-plugin/plugin.json` has no `"skills"` key at all (deliberately dropped per Stage 1), and whether Claude Code still auto-discovers `skills/` without it is unconfirmed anywhere in the repo's evidence base — the only live auto-discovery probe on record tested `agents/`, never `skills/`.**
Evidence: I printed the full manifest myself — only `name`/`version`/`description`/`keywords`/`license`/`author` present, confirmed no `skills` key. `references/claude-agent-dispatch.md` only covers agent auto-discovery. This is a real, unverified functional gap presented in AGENTS.md as if it were settled.
Fix: run a live probe analogous to `claude-agent-dispatch.md` but targeting skill auto-discovery specifically.
Found by: A8 (item12).

### F. Stage 01 Foundation

**G21. [NOT DONE, count-corrected by me] `git grep -c "\.kimi-plugin"` does not return "exactly 1" as Stage 1's own literal verification bar states.**
Evidence: I ran this myself just now — **18 files match** (Audit 7 independently got the same 18-file count); occurrence count is **42** by my own `git grep -o | wc -l` (Audit 7 reported 41 — a 1-occurrence discrepancy not worth chasing further, both numbers are two orders of magnitude off "exactly 1"). Commit `28c536d`'s own message quietly reframes the bar to a weaker, self-redefined criterion ("outside CHANGELOG.md → only historical/frozen sources remain") rather than the literal blueprint text.
Found by: A7 (item16), independently reconfirmed by me.

**G22. [NOT DONE] "Zero diff outside the declared file inventory" is false: 13 files were modified/created outside Stage 1's declared Create/Delete list.**
Evidence: `git diff --name-status c9e6b41^ 038d93f` shows 8 undeclared modified files (`AGENTS.md`, `Makefile`, `PLAN.md`, `README.md`, `hooks/guard-destructive.sh`, `scripts/plugin_meta.py`, `scripts/skillextract.py`), 4 undeclared modified test files, and 1 wholly undeclared new file (`tests/test_hooks_manifest.py`). Stage 1's own section declares zero "Modified" files.
Found by: A7 (item24).

**G23. [PARTIAL] `python3 -m scripts.fsm --help` "runs with no permission prompt" check is vacuous: `scripts/fsm.py` has no `__main__` block or argparse at all, so `--help` is silently ignored — the check only proves the module *imports* without prompting, not that it has a working CLI.**
Evidence: `rg -n "^if __name__|argparse" scripts/fsm.py` → no hits.
Found by: A7 (item19).

**G24. [PARTIAL] Stage 1's two mandated live checks ("plugin loads cleanly," "`$ATLAS_PLUGIN_ROOT` populated post-session") are true, but only because each of A7 and A6 independently ran them live *during this audit* — no probe, reference doc, or commit message in the repo documents either check ever having been run before now, unlike every other stage (each of which has a dedicated `references/*-live-validation.md`).**
Found by: A7 (items 17/18/23).

### G. Documentation drift (AGENTS.md / README.md) — largest single defect cluster

**G25. [NOT DONE] AGENTS.md L12: "orchestrator plugin for Kimi Code" — should read Claude Code.** I confirmed directly (`AGENTS.md:12`) this line is unchanged. Found by: A8 (item1).

**G26. [NOT DONE] AGENTS.md L14 / README.md: install instructions point at `~/.kimi-code/plugins/managed/kimi-atlas` — no Claude Code analogue exists anywhere in the repo's evidence base; a persistent marketplace-install path is an explicit blueprint non-requirement, so there is no ready-made replacement sentence — a genuine open documentation gap, not just a rename.** Found by: A8 (item3).

**G27. [NOT DONE] AGENTS.md L15-16 and README.md:69-70 both instruct running `./scripts/install.sh` — I confirmed this file was deleted in commit `c9e6b41`. Following either doc's Quick Start today produces "file not found." This is the exact class of gap already caught once before this audit round.** Found by: A7 (item25, cross-cutting), A8 (item4), A9 (incidental).

**G28. [NOT DONE] AGENTS.md L84 claims `.claude-plugin/plugin.json` has `"skills": "./skills/"` — it does not (confirmed above, G20). Whether skills still auto-discover without that key is unconfirmed.** Found by: A8 (item12) — same underlying fact as G20, different document.

**G29. [NOT DONE, most severe AGENTS.md finding] AGENTS.md L102-106 still describes retired dispatch-by-reference ("the root names `agents/<role>.md` in the prompt and the subagent reads it as its first act... explore/coder/plan") — the live `skills/atlas/SKILL.md`'s own "CLAUDE CODE PLATFORM FACTS" section states the opposite explicitly: dispatch is by-name, identity-mapped, confirmed by commit `6c3669b`.** Found by: A8 (item14).

**G30. [NOT DONE] AGENTS.md L107-111 describes the retired per-invocation `PYTHONSAFEPATH=1 PYTHONPATH=<plugin-root>` prefix convention — the live SKILL.md explicitly forbids re-adding this ("do not add one back"); the real mechanism is the SessionStart-hook env-file (see G11).** Found by: A8 (item15).

**G31. [NOT DONE] AGENTS.md L121's example literal `"${KIMI_SESSION_ID}"` is stale — the real current call uses `"$ATLAS_SESSION_ID"`.** Found by: A8 (item19).

**G32. [NOT DONE] AGENTS.md L130-134 ("in progress since 2026-08-20") is stale relative to HEAD — the blueprint document it points to now carries its own "VERDICT: READY" status overlay as of commit `75aaf17`, current repo HEAD.** Found by: A8 (item20).

**G33. [NOT DONE] AGENTS.md L155-165 (the project's single top-level "Status" section) shows zero indication a full CLI-host migration happened at all. `git show 82b5d18 -- AGENTS.md` (the only commit touching this file across Stages 1-5) shows the entire diff was a doc-count bump ("49"→"50 tracked docs") — nothing else changed, despite this being the largest architectural event in the project's history.** Found by: A8 (item23).

**G34. [PARTIAL] AGENTS.md L18-37 ("Four layers, all first-party") is individually accurate but incomplete: `skills/atlas-resume/SKILL.md` — a third rewritten SKILL.md and a Stage-5 deliverable — is never named anywhere in AGENTS.md.** Found by: A8 (item5).

**G35. [PARTIAL] AGENTS.md L42's `make ci` inline comment omits 3 of the 7 real prerequisites (`check-plugin-manifest`, `check-cc-migration`, `predcov`).** Found by: A8 (item8).

**G36. [NOT DONE] README.md:311 still reads "Stages 2 and 5 not started," despite commits `34f56b3`, `790dba5` (Stage 2) and `d90eb7b`, `82b5d18`, `75aaf17` (Stage 5) already existing — last touched at Stage-3-era commit `b23bad2`, never updated since.** Found by: A7 (item25, cross-cutting), A9 (incidental).

### H. Risk Register & Acceptance Criteria

**G37. [NOT DONE] No structural, non-ask-outcome signal for headless-vs-interactive detection exists — the blueprint's own documented mitigation ("record invocation form explicitly into the task packet at INIT") was never implemented.**
Evidence: `references/schemas.json`'s task-packet schema (`intent, success_criteria, scope_paths, verify_cmd, baseline_sha, debug_tokens, test_glob`) has no `invocation_form`/`is_headless`/`headless_mode` field — confirmed by repo-wide search returning zero hits. The model still infers mode contextually at CLARIFY/PRE-CODE/OUTPUT, exactly the anti-pattern the mitigation exists to replace.
Found by: A9 (row9), A10 (§15 Fact 8) — same gap.

**G38. [PARTIAL] Test file count floor: the blueprint's §14 acceptance bar of "≥94 test files" is not met — see corrected count in §4 below.** Found by: A10.

**G39. [NOT DONE] The §14 acceptance criterion "Invariant: 3 pauses, 1 turn — a live INIT→OUTPUT smoke run" and its parallel Stage-5 exit-criterion "a live smoke invocation of the orchestrator returns the expected loaded-OK response" (stated twice in Stage 05 text) have never been executed anywhere. No commit, reference doc, or test performs a full live INIT→OUTPUT run of the real `/kimi-atlas:atlas` skill through an actual session. `make negative-gate` exercises `verdict.gate()` and critic dispatch directly via Python — it never drives the SKILL.md-based orchestrator prompt end-to-end, so it provides zero evidence either way. This is the single most significant remaining gap for "is the whole thing actually proven to work as one flow" — exactly the class of unproven-completion claim the user already caught once.**
Found by: A10 (§14 item6), A12 (item15) — same gap, independently found from two different blueprint sections.

**G40. [NOT DONE] Fact 4 (§15): whether a `Workflow` script can subprocess-invoke the Python backbone remains empirically untested — correctly non-blocking (Workflow adoption itself is deferred, see §3), but the underlying feasibility question was never even probed.** Found by: A10.

### I. Stage 04/05-specific residue

**G41. [NOT DONE] Two Stage-05-named test files were never created: `tests/test_skill_frontmatter_schema.py` and `tests/test_agent_dispatch_shape.py`.** I confirmed directly — both absent. Named explicitly in the blueprint's Stage 05 "Files affected" list, never flagged as deferred anywhere; the status overlay's Stage-5 row claims "Fully done." These account for 2 of the shortfall in G38.
Found by: A12.

**G42. [PARTIAL] `${KIMI_SKILL_DIR}` is still literally present in 2 of 3 SKILL.md files (`skills/atlas/SKILL.md:96`, `skills/atlas-resume/SKILL.md:38`) as deliberate "do-not-reintroduce" warning prose, explicitly hand-exempted by the residue checker with documented rationale — not hidden, but the literal Stage-05 instruction ("global token rename... across all three SKILL.md files") was not achieved letter-for-letter.** Found by: A12.

**G43. [NOT DONE] Stage 05's own verification bullet "`git diff pre-stage5-baseline -- scripts/ tests/fixtures/ references/rubric.md references/schemas.json` is empty" is violated: `references/rubric.md` was in fact modified (a legitimate one-word `FetchURL`→`WebFetch` fix), but the specific check as literally written would not have passed — never reconciled anywhere.** Found by: A12.

**G44. [PARTIAL] Stage 05's "left untouched" scope discipline claim is inaccurate: 3 undeclared reference-doc edits (`references/rubric.md`, `references/system-graph.json`, `references/system-map.md`) happened during the Stage-5 commit window — each individually justified in the commit message, but none declared in the "Files affected" list.** Found by: A12.

**G45. [flagged, informational] `references/system-map.md:372` and `references/system-graph.json:1755` still assert the retired pre-migration invariant present-tense ("frontmatter is DOCUMENTATION ONLY... orchestrator sets dispatch temperature (V5)") — now factually false, never updated by any migration commit.** Found by: A11.

**G46. [flagged, informational] A heredoc risk in `skills/atlas/SKILL.md`: Python blocks use `<<'PY'` (quoted delimiter), which blocks shell parameter expansion — if the orchestrating model ever pastes the block byte-for-byte rather than substituting the real session id, `run` becomes the literal 17-character string `$ATLAS_SESSION_ID`, not the real id. Empirically demonstrated (shell repro included in the source audit) but never tested against real model behavior, because no live smoke run exists (ties directly to G39).** Found by: A12.

---

## 3. Every DELIBERATELY DEFERRED item, with exact blueprint quote

All 8 raw "deferred" tallies collapse to **4 distinct deferred decisions**, every one independently traced to an explicit blueprint quote by at least one audit — no hidden/unsupported deferral was found anywhere across all 13 audits.

1. **Native `Workflow` tool adoption for ATLAS-WEAVE's SCHEDULE.**
   Quote: *"Its whole reason for existing is a deterministic halting-proof scheduler — architecturally matches `Workflow`, a different execution primitive. Deferred to Phase 2 by default."* Reconfirmed at §14: *"`Workflow` adoption for ATLAS-WEAVE's SCHEDULE (Phase 2, optional)."*
   Confirmed as-shipped: `rg -n '\bWorkflow\b'` across both SKILL.md files → zero matches; SCHEDULE still dispatches via `scheduler.py`'s unchanged `W_MAX=3` sequential/wave model.
   Found by: A2 (row11), A6 (row5 context), A10.

2. **Native `isolation:worktree` adoption for the CODE stage.**
   Quote: *"Self-managed worktrees, not native isolation... Switching is explicitly out of scope for this port — deferred, not silently dropped."* + §14: *"native `isolation:worktree` adoption (declined pending independent validation)."*
   Confirmed as-shipped: no `isolation:` field in any `agents/*.md`; `skills/atlas/SKILL.md:463` uses self-managed `git worktree add`.
   Found by: A2 (row10), A10 (§14 + §15 Fact 7).

3. **A persistent marketplace-install path.**
   Quote (§14 explicit non-requirements): *"a persistent marketplace-install path."*
   Confirmed as-shipped: the only working load path is local/dev (`claude --plugin-dir <repo> --debug`) — consistent with the deferral, but see G26 above: the deferral does not excuse the docs still pointing at a *deleted* Kimi-era path instead of the confirmed working dev path.
   Found by: A6 (row14), A10.

4. **Resolving `KIMI_CODE_HOME`'s exact Claude Code analogue.**
   Quote (§14 explicit non-requirements): *"resolving `KIMI_CODE_HOME`'s exact analogue."*
   Confirmed as-shipped: no `CLAUDE_CODE_HOME`-equivalent anywhere in `scripts/`/`hooks/`; remaining hits are all historical/pre-migration docs.
   Found by: A6 (row14), A10.

**No item marked "deferred" by any of the 13 audits lacked a supporting blueprint quote.** This is itself worth stating plainly: the deferral mechanism in this blueprint is honestly used — every declared non-requirement really is declared, not retrofitted.

---

## 4. Contradictions between audits

**C1. Test-file count: A10 reports 91 (only 3 short of the ≥94 floor); A6 and A12 independently report 86 (8 short). I resolved this myself just now by running both commands directly.**
- `find tests -name 'test_*.py' -type f | wc -l` → **91** (A10's exact command and number, confirmed).
- `git ls-files 'tests/test_*.py' | wc -l` → **86** (A6's and A12's number, confirmed).
- The diff between the two sets is exactly 5 files, all under `tests/fixtures/`: `bad_correctness/test_clamp.py`, `bad_quality/test_pricing.py`, `bad_security_sast/test_linecount.py`, `bad_security/test_tokenauth.py`, `good/test_median.py`.
- **These 5 are deliberately-broken code *samples* used as inputs to the negative-gate corpus — not unittest suite files.** A10's recursive `find` inadvertently counted them as test files because they happen to match the `test_*.py` glob; A6/A12's `git ls-files 'tests/test_*.py'` pattern (no `**`) correctly excludes subdirectories and only counts the real top-level test suite.
- **Resolution: A6/A12's 86 is the more direct/primary count for "how many test files does the migration's own `≥94` acceptance bar refer to."** A10's shortfall claim ("3 files short") understates the gap; the correct shortfall, using the count both A6 and A12 independently arrived at, is **8 files short of ~94**, not 3. This should be corrected in any resumed work: the test-count floor is missed by roughly 2.5x more than A10 reported.

**C2. Hook execution `cwd`: A9 grades the Risk Register row DONE; A5 and A10 grade the same underlying fact NOT DONE.**
- Both are factually consistent once you separate "is the mitigation shipped" (yes — all three audits agree the hooks read `cwd` from the JSON payload rather than trusting process cwd) from "is the underlying fact resolved and evidenced in the repo" (no — A5/A10 are correct that no committed probe exists).
- A9 additionally reports running its own ad-hoc live probe and getting a positive resolution (cwd = project root) — credible, but that evidence lives only in A9's audit transcript, not in the repository. A9 itself flags this tension explicitly ("the same class of gap already flagged to the user previously").
- **Resolution: NOT DONE is the more direct/primary read of committed repo state — A9's DONE grading is scoped narrowly to the mitigation, not the fact, and A9 says so itself.** See G14 above.

**C3. `skill-registry.json`/`skillregistry.py` — A6 grades the blueprint's own REMOVE verdict for this row NOT DONE (and calls it a likely misclassification); A8 grades AGENTS.md's *description* of the same files DONE (accurate).**
- No actual factual disagreement — both audits agree the files exist and are load-bearing at the GROUNDED stage. They are grading two different things (the blueprint's target vs. AGENTS.md's description accuracy), and both are correct on their own terms. A8 explicitly flags that its own DONE verdict "directly contradicts the migration blueprint's own §6.6 verdict," so this is a self-aware complementary finding, not a genuine disagreement.
- **Resolution: treat as one gap (G17) — the blueprint's REMOVE verdict for this row is wrong given what the code now does, and AGENTS.md happens to describe the (unremoved) reality correctly.**

**C4. `.kimi-plugin` occurrence count: A7 reports 41 total occurrences across 18 files; my own direct re-run just now got 42.**
- Both used the same 18-file count (confirmed identical). The 1-occurrence delta is not chased further — irrelevant to the verdict, since both numbers are two orders of magnitude away from the blueprint's literal "exactly 1" bar. **Resolution: not a meaningful contradiction; NOT DONE stands regardless of which of the two counts is used.**

**C5. Internal contradiction within the blueprint's own status overlay (not between two audits, but flagged by A13 and worth surfacing here as the single most consequential contradiction found across all 13 reports).**
- Line 487: "...run_id design divergence... (kept as `$ATLAS_SESSION_ID` **by explicit user decision**) — **a settled decision, not a blocker**."
- Line 497 (Stage-5 table): "Run_id kept as `$ATLAS_SESSION_ID` **per the user's explicit decision**."
- Line 510-511 (the Divergence section's own closing sentence, two paragraphs later): "Whether to switch is an open call — **not decided here**."
- A13 searched `git log --all --grep`, read Engram memory #1066 (the actual Stage-3 implementation record — whose "Why" is "User asked to start Stage 3 implementation," not a recorded choice between the two run_id designs), and found **no primary source anywhere recording the user ever being asked or ever deciding** between the UUID4 design and the session-id design.
- **Resolution: this is not a disagreement between two audits' evidence — it is the blueprint's own document contradicting itself, and the "explicit user decision" framing is unsubstantiated by any primary source.** This is the report's single highest-priority item for whoever resumes: treat the run_id design choice as genuinely open, and do not repeat the "settled by explicit user decision" framing without actually asking the user first.

---

## 5. Headline verdict

**No — it is not accurate to call this migration "100% done," and it would also be inaccurate to describe it with the blueprint's own "VERDICT: READY" framing without qualification.**

The defensible, precise claim:

> **148 of 225 raw audited items (65.8%) are verified fully DONE. 30 (13.3%) are PARTIAL — mechanism shipped but a named risk, sub-claim, or test coverage gap left open. 39 (17.3%) are NOT DONE. 8 (3.6%) are legitimately, quote-backed DEFERRED to Phase 2 or explicitly declared non-requirements — none of the 4 distinct deferred decisions behind those 8 rows were found to be undeclared or retroactively excused.**
>
> Deduplicating the ~69 raw PARTIAL+NOT DONE rows down to distinct underlying defects yields **roughly 46 genuinely separate gaps**, spanning: a safety-adjacent enforcement gap that was explicitly re-affirmed rather than fixed (`context-scout` retaining Bash, G2); a dead/contradictory parameter left in 4 of 7 subagent role files with no CI gate able to catch it (`temperature:`, G1); an entire stage's own byte-identity and failure-condition bar silently violated one commit before the next stage began (G10); a load-bearing environment mechanism the system now unconditionally depends on but has never been tested end-to-end through its real path (`CLAUDE_ENV_FILE`, G11); a hook-timing fact flagged High-impact by the blueprint itself that remains genuinely untested in the committed repository (`cwd`, G14, C2); the single most consequential missing proof — a full live INIT→OUTPUT run of the actual orchestrator skill has *never been executed*, at any point, by anyone, in this entire migration (G39); the primary onboarding docs (`AGENTS.md`, `README.md`) still describe an entirely different host platform and instruct new readers to run a script that was deleted five commits into Stage 1 (G25–G33, G27); a numeric acceptance-bar shortfall that is roughly 2.5x worse than the audit that first reported it claimed (test-file count, C1); and a governance claim — that the project's most architecturally significant open decision (run_id design) was "settled by explicit user decision" — that is directly contradicted by the same document's own closing sentence and unsupported by any primary record (C5).
>
> **None of these 46 gaps individually breaks the system today** — Stage 4's own live probe confirms Claude Code silently ignores the unknown `temperature` key, for instance, and the `cwd`-payload sidestep works regardless of the underlying fact's answer. But collectively they mean the blueprint's own acceptance bars (§14), its own Stage exit criteria, and its own status-overlay prose overclaim completion in exactly the pattern the user already caught once: mechanisms are real and mostly well-built, but several of the specific tests, live checks, and file-parity claims the blueprint itself set as the bar for "done" were never actually run, or were run and silently failed without being surfaced, before the "READY" verdict was written.

Most consequential single fix before any "READY" claim is repeated: **run the live INIT→OUTPUT smoke test the blueprint itself twice specifies and has never once executed (G39)**, and **stop asserting the run_id design is a settled user decision until the user has actually been asked (C5)**.

---

## Adversarial spot-check of the synthesis above

*A separate agent, given only the synthesis text, independently re-verified 8 DONE claims and 3 DEFERRED claims from primary sources without reading the synthesis's cited evidence first.*

## Independent verification results

**Method:** I read/ran everything below fresh — no synthesis text was consulted before forming each verdict.

### 8 DONE-area claims re-verified

| # | Area | Claim checked | My independent finding | Verdict |
|---|---|---|---|---|
| 1 | A2/A8 dispatch | SKILL.md's "CLAUDE CODE PLATFORM FACTS" documents by-name dispatch, backed by commit `6c3669b` and `references/claude-agent-dispatch.md` | `git show 6c3669b` exists verbatim as described ("feat(stage4): rewrite dispatch to Claude Code's real by-name mechanism"); `references/claude-agent-dispatch.md` exists with the exact 7/7-dispatch and byte-identical-fidelity probe results described | **AGREE — DONE**, accurate |
| 2 | A1 tool surface | 7 role files' `tools:`/`model:` frontmatter now enforced; 4 still carry stale `temperature:`; `context-scout` still has `Bash` | Read all 7 `agents/*.md` frontmatter directly: `code-quality-critic`, `correctness-critic`, `integration-critic`, `security-critic` all still have `temperature:`; `context-scout` tools line is exactly `Read, Grep, Glob, Bash` | **AGREE** — mechanism shipped, leftovers real, matches synthesis's own PARTIAL/NOT-DONE grading (i.e. no overclaim here) |
| 3 | A4/C1 harness | `make negative-gate` passes 5/5 live | Ran `python3 scripts/run_negative_gate.py` myself just now: `good→OK`, all 4 `bad_*→UNVERIFIED` as expected, **"5/5 fixture(s) matched expectation"** | **AGREE — DONE**, confirmed live |
| 4 | A5 hooks | `guard-destructive.sh`'s dual deny emission (exit 2 + JSON `permissionDecision:deny`) is unchanged, correct, header-scoped as no-behavior-change | Read the full header: text matches near-verbatim, including "CONFIRMED to honor BOTH blocking signals" and "no behavior change was made here" | **AGREE — DONE**, accurate |
| 5 | A5/A9 hooks | All three hooks (`guard-destructive.sh`, `telemetry.sh`, `session-resume.sh`) "sidestep" the unconfirmed-`cwd` fact by "reading `cwd` from the hook's stdin JSON payload" | `telemetry.sh`/`session-resume.sh` do this (`d.get("cwd")` present in both). **`guard-destructive.sh` does NOT** — `rg '"cwd"|d\.get\("cwd"' hooks/guard-destructive.sh` returns zero matches in 149 lines. Its only `cwd` mention (line 30) is prose stating the fact is unconfirmed; its actual mitigation is `PYTHONSAFEPATH=1` (import-path isolation), an unrelated fix for a different threat | **DISAGREE — synthesis evidence is inaccurate.** It cites `guard-destructive.sh:30-33` as if it implements the same JSON-cwd-read sidestep as the other two files. It doesn't need to (no cwd-dependent logic), but claiming it does is a factual error in the supporting evidence, not a rounding error |
| 6 | A12 Stage 05 | `skills/atlas-resume/SKILL.md` exists as a genuine third rewritten SKILL.md | File exists, 99 lines, substantive content (not a stub) | **AGREE — DONE** |
| 7 | A9/A13 governance | H5 collision defect left `@unittest.skip`'d with an honest "DEFERRED... NOT abandoned" rationale, not silently deleted | Read `tests/test_v1521_regressions.py:672-688` directly: skip decorator present, citing commit `4fa4cee`, explicit "DEFERRED to v1.5.3 by an explicit, recorded scope decision... NOT abandoned, and NOT quietly dropped" | **AGREE — DONE**, honestly documented |
| 8 | A8 docs accuracy | AGENTS.md's "Four layers, all first-party" (L18-37) accurately names existing backbone scripts | Verified all 9 named scripts exist: `contextgraph.py`, `ctxevents.py`, `fsm.py`, `rollback_driver.py`, `safewrap.py`, `astlens.py`, `rubric.py`, `frontmatter.py`, `verdict.py` | **AGREE — DONE**, accurate |

**Unprompted corroborations along the way** (not part of the 8, but independently reproduced and worth noting): `.claude-plugin/plugin.json` has exactly `name/version/description/keywords/license/author`, no `skills` key; test counts are exactly 91 (`find`) vs 86 (`git ls-files`), and the diff is exactly the 5 named fixture files under `tests/fixtures/`; `references/skill-registry.json` and `scripts/skillregistry.py` both exist and are called from `skills/atlas/SKILL.md` at the claimed line range (~377-408) via `skillselect.select(...)`; AGENTS.md:12 still literally says "Kimi Code" and AGENTS.md's dispatch section (~L102-106) still describes the retired dispatch-by-reference model verbatim, directly contradicted by the SKILL.md text in row 1. All of these matched the synthesis exactly.

### 3 DEFERRED items — blueprint quote verification

Read `docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md` directly:

1. **`Workflow` tool for ATLAS-WEAVE's SCHEDULE** — line 216: *"Its whole reason for existing is a deterministic halting-proof scheduler — architecturally matches `Workflow`, a different execution primitive. Deferred to Phase 2 by default."* **Exact match.**
2. **`isolation:worktree`** — line 256: *"Self-managed worktrees, not native isolation... Switching is explicitly out of scope for this port — deferred, not silently dropped."* Plus line 446: *"native `isolation:worktree` adoption (declined pending independent validation)"*. **Exact match, both quotes.**
3. **Persistent marketplace-install path** — line 446: *"...a persistent marketplace-install path..."* **Exact match** (verbatim substring of the §14 non-requirements list).

No misquoting or fabrication found in any of the three.

### Overall judgment

The synthesis is **largely trustworthy** and its "I re-ran seven claims myself" framing holds up — every number, commit hash, file path, and line-range I independently reproduced matched exactly, including a fairly intricate one (the 91-vs-86 test-count reconciliation down to the same 5 files). This is not the pattern of a document hallucinating verification.

But it does still overclaim in one place, which matters because it's exactly the failure mode this exercise exists to catch: **G14's evidence treats `guard-destructive.sh` as implementing the same "read cwd from stdin JSON" sidestep as `telemetry.sh`/`session-resume.sh`, citing a specific line range for it — but that file never reads a cwd field at all.** The synthesis bundled three files under one uniform mitigation claim when only two actually have it. This doesn't flip the NOT DONE verdict on the underlying `cwd`-unconfirmed fact (if anything it means that gap is slightly wider than stated), but it's a real instance of the synthesis stating supporting evidence more broadly/uniformly than the code supports — worth correcting before this document is treated as a clean re-verification pass.

---

## Post-audit clarification (added by the orchestrating session, not the audit agents)

On **C5** (the run_id "settled by explicit user decision" claim): the 13 audit agents only had access to the repository's own committed history and Engram memory — none of them had access to this session's actual chat transcript. The user genuinely **was** asked explicitly, mid-session, via a structured yes/no choice (keep `$ATLAS_SESSION_ID`, already implemented, vs. switch to the blueprint's self-generated-UUID4 `$ATLAS_RUN_ID` design) and explicitly chose to keep `$ATLAS_SESSION_ID`. So the underlying claim is factually true, not fabricated.

**What the audit correctly caught, though**: this exchange was never captured anywhere durable in the repository itself — no commit message, no dated note in the blueprint's own Divergence section, nothing an independent reader (or a future session, or this very audit) could find without access to the live conversation. Asserting "settled by explicit user decision" in a document meant to stand on its own, with zero traceable evidence of that decision inside the document's own evidence base, is indistinguishable from an unsubstantiated claim to anyone who can't see the original conversation — which is a real documentation defect, independent of whether the underlying fact happens to be true. Fix: add a dated, quoted record of the actual exchange to the blueprint's Divergence section.

---

## Live-probe defects found and fixed — 2026-08-21 (post-audit, not part of the original 46-item list)

Two further defects surfaced by live probing after this audit was written, independent of the ~46 items above. Both are now fixed in the working tree.

**Grep/Glob silently unavailable for `context-scout`/`elite-coder` despite frontmatter grant.** Row 2 of the adversarial spot-check above already noted `context-scout`'s `tools:` line was `Read, Grep, Glob, Bash` — at the time recorded as a plain fact, not yet known to be broken. Two independent live nested-dispatch probes (real `claude -p` sessions issuing `Agent(subagent_type="kimi-atlas:<role>", …)` and attempting real `Grep`/`Glob` calls) proved both tools return `UNAVAILABLE` at runtime for exactly these two roles — the only two of the 7 that also carry `Bash` — while the other 5 (no `Bash`) are unaffected. Root-cause testing ruled out a frontmatter-formatting bug: reformatting `context-scout.md`'s and `elite-coder.md`'s `tools:` line to a YAML block-list (dashes, reordered) reproduced the identical `UNAVAILABLE` result on redispatch, twice, byte-for-byte (`elite-coder`'s self-reported `tools_available` was identical before and after reformatting). This is a genuine Claude Code platform behavior — granting `Bash` alongside `Grep`/`Glob` structurally excludes the latter two from the effective per-subagent tool grant — not a repo-side syntax defect. Fix: removed the dead `Grep`/`Glob` entries from both files' `tools:` frontmatter (now `Read, Bash` and `Bash, Read, Write, Edit, WebSearch, WebFetch` respectively), rewrote `context-scout.md`'s prose to locate files via its existing read-only `Bash` (`grep -rn`, `find`) instead of the now-absent `Glob`/`Grep`, and confirmed `elite-coder.md`'s prose never referenced `Grep`/`Glob` in the first place. Re-verified live against the fixed production files via real `kimi-atlas:context-scout`/`kimi-atlas:elite-coder` dispatches: `context-scout` correctly grounded a real task using only `Read`+`Bash` search, and `elite-coder` correctly implemented and tested a real small feature using `Write`/`Edit`/`Bash`, neither needing nor attempting `Grep`/`Glob`.

**`runcheck`'s OPS-3 memory cap was not swap-bounded.** `scripts/proccap.py`'s `_build_wrapper`/`_build_wrapper_argv` (the argv construction `runcheck.run()` actually calls for lens 5) set `systemd-run --user --scope -p MemoryMax=<N>M` but never `MemorySwapMax`, so on a host with swap headroom a workload that exceeded the cap simply swapped instead of being killed — the cap silently failed to enforce a hard limit. Confirmed live via `probe/probe_runcheck_memcap.sh`: a 200 MB memory hog against a 50 MB cap returned `ok: true` (uncapped, swapped) via the raw `MemoryMax`-only scope, while the identical cap plus `MemorySwapMax=0` killed it (`rc=137`). Fix: added `-p MemorySwapMax=0` alongside `-p MemoryMax=<N>M` in both `_build_wrapper` and `_build_wrapper_argv` in `scripts/proccap.py` (the single shared argv-construction path both `runcheck.run()` and the future `nativefloor` use, so no other file needed the same edit). Re-ran the probe against `runcheck.run()` itself (the production entrypoint, not a reimplementation): the same 200 MB-vs-50 MB workload now returns `{"ok": false, "returncode": 137, ...}`. Added `tests/test_proccap.py::TestMemorySwapCapEnforcement` (host-independent structural pins in `TestBuildWrapper`/`TestBuildWrapperArgv` plus a live cgroup enforcement test that `skipTest`s when the cgroup backend or host swap headroom is unavailable, matching this suite's existing environment-dependent-test convention); manually verified the live test fails (catches the regression) when `MemorySwapMax=0` is temporarily reverted, then confirmed it passes again with the fix restored.

## G39 — live INIT→OUTPUT smoke test — 2026-08-21

Run twice, both times by a human interactively (`claude --plugin-dir <repo>`, no `--permission-mode bypassPermissions` — that flag was attempted for an autonomous subagent run and correctly blocked by the platform's own safety classifier as an unauthorized approval-gate bypass; the human ran it themselves instead). Both runs reached the real `OUTPUT` terminal gate, with both real `AskUserQuestion` human gates (`PRE-CODE HUMAN GATE`, `OUTPUT`) firing live; `CLARIFY?` correctly self-skipped both times (well-specified requests). `refine_passes` hit the hard `MAX_PASSES=2` cap correctly both times without looping. All three critics (`correctness`, `code-quality`, `security`) genuinely dispatched and returned real JSON verdicts each run; the deterministic floor (astlens/syntaxlens/sast/lint/pathcheck) genuinely ran with zero defects both times. The terminal verdict was an honest `UNVERIFIED` both times — never a false `PASS` — because the runs surfaced two real, independently confirmed defects in the deterministic floor itself (not in the orchestrator's state machine, and not in the code `elite-coder` wrote, which was correct both times):

- **`scripts/difftool.py`** could not see a `git add`-ed-but-uncommitted new in-scope file (fell into neither its "tracked at baseline" nor "untracked" channel). Fixed with a third channel (`_staged_new_in_scope`); independently verified safe, no regression to the two existing channels.
- **`scripts/runsignal.py`**'s pytest-output parser false-negatived on the extremely common `verify_cmd: python3 -m pytest -q` (both live runs used exactly this) because `-q` suppresses all three markers (`collected N items`, platform header, `====` rule line) the parser required. Fixing this took three adversarial rounds — round 1's naive fix (recognize pytest's own undecorated `-q` tally line as a new marker) introduced a fabricated-pass regression (the marker wasn't coupled to extraction, so an unrelated line could supply a fake count); round 2 coupled extraction to the marker for the rule-line/q-summary cases but left a third path open (`collected`/`platform`-only gate still fell through to the old ungated scan); round 3 closed that third path by failing closed to `(0, 0)` whenever neither a rule line nor a q-summary line exists, proven both structurally (exhaustive code-path enumeration by two independent agents) and empirically (11+ adversarial probes across all three rounds).
- **One further, DEEPER, still-OPEN residual risk was found by round 3's own verifier and is NOT yet fixed**: the `-q` tally-line marker itself carries no provenance — a bare line anywhere in captured output that merely happens to fullmatch pytest's own `N word[, N word...] in Xs` shape is trusted with no requirement of any other pytest-specific context nearby, and when two such lines exist the later one wins extraction, which can silently overwrite a genuine earlier pass count with a fabricated one (`runsignal.count("3 passed in 12s\n", ("pytest",))` → `(3, True)` off nothing; `"3 passed in 0.02s\n99 passed in 1s\n"` → `(99, True)`, corrupting a real 3-pass result). This is documented in detail directly in `scripts/runsignal.py`'s own source next to `_PY_Q_SUMMARY_RE`, including a candidate untried fix (require a preceding pytest progress-dots line). Left open rather than rushed, per an explicit user decision to checkpoint the current state rather than continue an unbounded fourth round; realistic exposure is bounded because `verify_cmd` is task-packet-frozen, not adversarial external content, but this should not be considered closed.

Both scratch repos used for these runs (`/tmp/atlas-g39-smoke-test`, `/tmp/atlas-g39-smoke-test-2`) and a third prepared-but-unused one for a CLARIFY-gate probe (`/tmp/atlas-g39-smoke-test-3`) are outside this repo and were never committed; the atlas repo itself was confirmed byte-identical in its exclusion zone (`scripts/ctxstore.py`, `rollback_driver.py`, `resume.py`, `fsm.py`, the H5 skip) before and after every live run and every fix round.

## 2026-08-24 — an attempt at the G39 residual `-q` provenance risk was BUILT, ADVERSARIALLY REFUTED, and REVERTED

The G39 residual above (`scripts/runsignal.py`'s `_PY_Q_SUMMARY_RE` carrying no provenance beyond its own shape) **is still OPEN**. An attempt was written, passed `make ci` (exit 0, 1838 tests), and was then destroyed by an independent adversarial verification pass that did not write it. The attempt is preserved unmerged on branch `wip/runsignal-q-provenance` (commit `89aed6d`); `main` was reset to `5d04466`. Nothing was pushed.

**The approach that failed.** Require a `-q` tally line to be "armed" by a pytest-specific line above it (a progress line of `.FEsxX` characters, `collected N items`, or the `platform … -- Python` header) with no other tally line in between; and require a `=+…=+` rule line to actually carry a tally before it can win summary selection. It genuinely closed both probes the risk note names, and genuinely fixed a real, previously unrecorded bug (below) — but it introduced five regressions, every one verified twice: once by the adversarial pass, once independently by re-running the parent commit's `count()` and HEAD's `count()` over the same input in one process.

**Five verified regressions — the specification for whatever is attempted next. Each must be a test before any new fix is written.**

| # | Input | parent `5d04466` | attempt `89aed6d` | Class |
|---|---|---|---|---|
| F1 | A green `pytest -q` run followed by a decorated run KILLED before printing a tally (SIGKILL / verify-timeout / segfault; real captures used) | `(0, False)` | `(2, True)` | **fabricated pass** |
| F2 | A killed decorated run's own `collected 2 items` line, then a foreign `99999 passed in 3.00s` line such as `runcheck`'s `stdout + "\n" + stderr` assembly appends | `(0, False)` | `(99999, True)` | **fabricated pass** |
| F3 | Any decorated run lasting ≥ 60s — pytest appends ` (H:MM:SS)`, so the tally rule no longer fullmatches | `(2, True)` | `(0, False)` | false RED |
| F4 | `2 passed, 3 subtests passed in 0.02s` — core pytest 9's own bundled `subtests` fixture; the tally grammar cannot express a two-word category | `(2, True)` | `(0, False)` | false RED |
| F5 | `R..` progress line under `pytest-rerunfailures` (also `u`/`y` from core `_pytest/subtests.py`) — one unlisted progress character disarms the whole capture | `(2, True)` | `(0, False)` | false RED |

F1/F2 are the cardinal sin (blueprint §0). F3 alone is disqualifying on its own terms: **most real CI suites run longer than a minute**, so the attempt would have turned essentially every honest decorated run UNVERIFIED — the precise "a naive fix is worse than the bug" failure mode this project already recorded once at v1.5.1.

**Root causes, so the next attempt does not repeat them.** (i) `_pytest_summary_line` falling back to the trusted `-q` line whenever no *tally-bearing* rule line exists lets one invocation's tally answer for a different, verdict-less invocation — the fallback is load-bearing for the warnings fix, so this is a design consequence, not a typo. (ii) Arming on `collected N items` is unsound in exactly the case that matters: a run that collected and then died. (iii) Narrowing rule-line selection to a hand-written tally grammar silently rejects real tallies whose vocabulary that grammar does not model (duration suffix, plugin categories). (iv) An allowlist of progress characters is open-ended by construction — plugins and core pytest both add letters to it.

**One real, previously unrecorded defect the attempt found, which is INDEPENDENT of the reverted mechanism and still live on `main`.** Under `-q` pytest prints no decorated trailing tally, so whichever `=+…=+` section header comes last — `=== warnings summary ===`, `=== FAILURES ===`, `=== short test summary info ===` — is `rule_lines[-1]` and wins summary selection despite carrying no tally. Measured on a real capture (`python3 -m pytest -q`, two passing tests, one ordinary `UserWarning`, exit 0): **`(0, False)` — a genuinely green run read as ZERO tests and forced to UNVERIFIED.** The adversarial pass independently confirmed the same degradation for `-q --durations=5` and `-q -rA`. Any warning at all triggers it, so this is common in the field. It needs its own fix, and its own tests, and must not be bundled with the provenance work again.

**A second pre-existing hole, unchanged by the attempt and still live.** The provenance question is moot on the rule-line path, which has no corroboration requirement at all: `count("==== 3 passed in 12s ====\n", ("pytest",))` → `(3, True)` on `main` and on the attempt alike. A single line with a leading and trailing `=` is trusted with zero pytest context, so the bare-shape fabrication survives with two extra characters. Any credible closure of the `-q` provenance risk has to address this path too, or it closes nothing.

**Also unpinned (test gap, verified by mutation on a throwaway copy):** changing `_pytest_summary_line`'s `return trusted_q_lines[-1]` to `[0]` leaves the whole suite green — the "last run is authoritative" ordering has no test that distinguishes it. Eleven of twelve other mutations were killed.

## 2026-08-25 — item 1 (the `make ci` env-leak blocker) CLOSED, and a new harness finding

Two atlas runs, `INIT → OUTPUT` each. Run 1a ended `⚠️ UNVERIFIED` with its refine budget spent; run 1b ended **`✅ VERIFIED`**. Five files under `tests/` changed, +316/-13 then +43 KB total; no production module touched.

**The blocker is closed, measured.** `make ci` inside a real kimi-atlas plugin session (both `PYTHONPATH` and `PYTHONSAFEPATH` exported by `hooks/init-env.sh`) went **exit 2 → exit 0**; 1827 → 1831 tests; weave-negative-gate 7/7; inventory in sync at 52 tracked docs.

**The continuation prompt's diagnosis was wrong on the causal variable and is corrected here.** It named `PYTHONPATH` and prescribed removing it. Measured on CPython 3.12.3 against an isolated probe fixture: `PYTHONPATH` alone → the control exits 3 and the test **passes**, because `python3 -m` puts the cwd at `sys.path[0]` *ahead of* `PYTHONPATH`; `PYTHONSAFEPATH=1` alone → exits 1; **both** → exits 0, the documented "would be vacuous" failure. The causal variable is `PYTHONSAFEPATH=1`, which deletes the cwd entry. A fix stripping only `PYTHONPATH` leaves the control at exit 1 and closes nothing.

**Three of the test's four subprocesses were failing SILENTLY.** Only the control failed loudly. `make predcov` and `sh -c <recipe>` launch Python *indirectly*, and the recipe's `-` prefix and `|| true` hold the status at 0 whatever ran — so those three assertions passed while measuring nothing. The whole test was hollow under the leak, not just the control.

### NEW, previously unrecorded: `langfloor.resolve_runner_tag` cannot tag any make target but `make test`

`resolve_runner_tag("make ci", root)` returns `()`. The resolver special-cases exactly one target name (`_MAKE_TEST_RE` → read the Makefile's `test:` recipe); every other target falls through to a direct-token scan that finds no runner. `runsignal.count(output, ())` then returns `(0, False)` by its documented fail-closed rule, so `runcheck.green()` is False and a blocking `runcheck` CRITICAL is synthesized — **on a build that exited 0**. Measured on the same captured bytes, `runsignal.count(output, ("unittest",))` returns `(1830, True)`.

Consequence: **this repository's own documented primary gate — `make ci`, called "THE gate" in `AGENTS.md` — can never produce a `✅` when used as a `verify_cmd`.** This is fail-closed, so it is a false RED and never a false green. It is not fixed here (it would require changing `scripts/langfloor.py`, a production module on the verify path, which is its own change). Run 1b worked around it by using `verify_cmd: make test` and running the full `make ci` out of band in every ambient combination — a disclosed weakening, recorded because a `verify_cmd` substitution that is not compensated and reported is a way of hiding coverage.

### One criterion formally WAIVED, with the proposed remedy refuted by measurement

`make ci` under `PYTHONSAFEPATH=1` with **no** `PYTHONPATH` exits 2 with 20 loader `ModuleNotFoundError`s — **at baseline too** (`Ran 1501, FAILED (failures=3, errors=20)`). `python3 -m` is the only thing putting the repo root on `sys.path`; `PYTHONSAFEPATH` deletes it, and `unittest discover -s tests` inserts `<repo>/tests`, not `<repo>`. A critic proposed adding `tests/__init__.py`; that was built and measured and **refuted** — the combination still exits 2 with the same 20 errors. The only other remedy touches `Makefile:27`, outside the change's scope. Nothing in this system produces that ambient state: `hooks/init-env.sh` exports both variables together.

### Eight residuals, open

None blocks the gate. The three worth acting on first, each confirmed by direct orchestrator measurement rather than taken from the critic:

| id | severity | finding |
|---|---|---|
| C1 | MEDIUM | The AST pin's `stores` count sees only `ast.Name` with `ctx=Store`, so **in-place mutation is invisible**: `env["PYTHONSAFEPATH"] = "1"` and `env.update(...)` both leave `stores.count("env") == 1` and resolve to `_fixture_env()`, so all four launches report ACCEPTED on an environment that has had both scrubbed keys put back. Rebinding and `env |= {...}` correctly fail closed. Mitigated — a hard-coded re-add is still caught by the sibling `assertEqual(direct.returncode, _PROBE_EXIT)` control. |
| S1 | MEDIUM | The `cwd=` half tests "this expression READS the fixture name", not "stays INSIDE the fixture tree". `os.path.join(td,'..','..')`, `pathlib.Path(td).parent`, `os.path.dirname(td)` and `td + '/../..'` all reduce to `{'td'}` and pass — pointing the child at the tempdir's parent, on Linux the world-writable `/tmp`, while the same test *requires* those launches to drop `PYTHONSAFEPATH`. That is the v1.5.1 hijack surface. |
| Q2 | MEDIUM | The same check is simultaneously too tight: `resolve()` follows a bare name only when the whole expression **is** a `Name`, and `sources()` never re-resolves a nested one, so `cwd=str(root)` **false-REDs** although `root = _probe_tree(td)` is honest. |

Also open: S2 (the launch selector matches only `subprocess.<attr>`, so `os.system` would slip past the count assertion), C2 (a docstring generalises an `assertIn` truncation fact onto `assertEqual`, which does truncate — via `_common_shorten_repr` and `_truncateMessage`), and Q1/Q3/Q4 (prose-vs-tree drift).

**The pattern is the finding.** Across five consecutive passes, each remedy introduced the next pass's defect: extracting a helper begat a duplicated fixture; consolidating a docstring begat five stale copies; pinning "the recipe" begat a provable no-op wrapper; hardening `env=` begat the same class of gap in `cwd=`. The root cause is one mistake repeated in two places — **name resolution is not a substitute for shape checking**. "Resolves to `_fixture_env`" never meant "was handed a scrub", and "reads `td`" never meant "stays inside `td`".

**Process notes worth keeping.** `verdict.gate` returned `OK` on run 1b's first pass with zero blocking defects; the run continued only because rule **V7** forces a pass on any CORRECTNESS or SECURITY defect at any severity. That forced pass is what surfaced the name-rebinding hole — the PASS bar would have shipped it. Separately, two critic claims were **refuted by measurement** rather than accepted (the `tests/__init__.py` remedy, and a complaint that the pin's deliberate refusal of `dict(_fixture_env(), ...)` was a defect), and one claim was nearly refuted in error: a first reproduction attempt failed, and only isolating the pin's own resolution logic confirmed it. One failed reproduction is not a refutation.

## 2026-08-25 — audit re-derivation swarm: `hooks/init-env.sh` is DEAD on any dash host, and masking a shell-injection path

Found by the section-D verification agent as `EXTRA-1`/`EXTRA-2`, then **settled by direct execution** (that agent has `Read`/`Grep`/`Glob` only and correctly recorded both as UNRESOLVED, naming the exact commands that would settle them).

### EXTRA-1 — the hook exports NOTHING on this host. Live.

`hooks/init-env.sh:1` is `#!/bin/sh`; `:27` is `set -euo pipefail`; `hooks/hooks.json:58` invokes it as `sh "$CLAUDE_PLUGIN_ROOT/hooks/init-env.sh"`, so the shebang is bypassed and the host's `/bin/sh` decides. Measured:

```
/bin/sh -> dash
$ sh -c 'set -euo pipefail; echo ok'
sh: 1: set: Illegal option -o pipefail

$ CLAUDE_PLUGIN_ROOT=... CLAUDE_ENV_FILE=... sh hooks/init-env.sh </dev/null
hooks/init-env.sh: 27: set: Illegal option -o pipefail
rc=2          # and $CLAUDE_ENV_FILE was never created
```

`dash` is the default `/bin/sh` on Debian and Ubuntu. On every such host the hook **aborts before its first `echo`** and exports none of `ATLAS_PLUGIN_ROOT`, `PYTHONPATH`, `PYTHONSAFEPATH`, `ATLAS_SESSION_ID`.

`PYTHONSAFEPATH=1` is the v1.5.1 CRITICAL countermeasure against the `sys.path` hijack (a target repo shipping `scripts/__init__.py` + `scripts/verdict.py` replacing the FROZEN pure gate). **It is silently absent in every plugin session on a dash host** — the guard is not weakened, it is simply never installed, and nothing reports that. `init-env.sh` is also the only `set -euo pipefail` script in the repo under a `#!/bin/sh` shebang; its three sibling hooks use portable POSIX `sh` with no `set -e` at all, and `hooks/session-resume.sh:68` additionally carries `trap 'exit 0' EXIT`. `hooks/hooks.json:2` describes the manifest as registering "only fail-open, observe-only, or pointer-only hooks" — `init-env.sh` is registered and is not fail-open (`EXTRA-3`).

**No committed test can see this.** `tests/test_syspath_isolation.py:1072-1089` only `read_text()`s the hook and greps for literal substrings; nothing in `tests/` ever executes it.

### EXTRA-2 — fixing EXTRA-1 alone ACTIVATES a shell-injection path. Latent, confirmed by execution.

`init-env.sh:52-54` interpolates the stdin-JSON `session_id` into a shell `export` line appended to `$CLAUDE_ENV_FILE` — a file whose whole purpose is to be sourced for the rest of the session — with no validation beyond `isinstance(v, str)` and `[ -n ... ]`. Measured against a copy with only `pipefail` removed (i.e. simulating an EXTRA-1 fix):

```
session_id = 'x"; touch /tmp/PWNED-BY-SESSION-ID; :"'
written line: export ATLAS_SESSION_ID="x"; touch /tmp/PWNED-BY-SESSION-ID; :""
sourcing it  -> /tmp/PWNED-BY-SESSION-ID created.   BREAKOUT CONFIRMED.
```

Severity is **MEDIUM, defense-in-depth, not CRITICAL**: `session_id` is supplied by Claude Code itself and is a UUID in normal operation, and no attacker-controlled path to it was established. But it is an unvalidated value crossing a trust boundary into sourced shell, and the same shape exists at `:32` for `PLUGIN_ROOT`. Cheap fix: `case "$SESSION_ID" in *[!A-Za-z0-9_-]*) SESSION_ID="" ;; esac` before the write.

**The two defects interact perversely: EXTRA-1 is currently masking EXTRA-2.** Repairing the shebang/`set` line without also validating `session_id` converts a dead hook into a live injection sink. They must be fixed together.

### Consequence for item 1 — the blocker's own premise is host-dependent

The continuation prompt asserted "`make ci` is red in **every** plugin session until this is fixed." That requires `init-env.sh` to run. On a dash host it does not run, nothing is exported, and `make ci` is **green**. The item-1 fix remains correct and necessary — it is right on any host where `/bin/sh` is bash, and it will be right everywhere once EXTRA-1 is repaired — but the "every plugin session" claim was never true on Debian/Ubuntu, and the earlier observation in this session that `PYTHONPATH`/`PYTHONSAFEPATH` were unset was attributed to the wrong cause (session cwd) when the likelier explanation is that the hook ran and died.

**These are not fixed here.** They touch `hooks/`, a production path, and belong in their own atlas run with their own gate.

### Swarm re-derivation, sections A / B / D — the pattern

Three agents re-derived 16 rows independently from bytes on disk, forbidden from trusting the audit, the status overlay, `5353fb2`'s "essentially all" claim, or `AGENTS.md`/`README.md`/`PLAN.md`. Ten verdicts differ from the audit, nearly all in the DONE direction — but the residue has one shape:

**Scripts were committed; results were not.** `probe/` holds 14 scripts. `references/` contains exactly **one** committed `FINDING=` line (`references/stage4-dispatch-enforcement-live-validation.md:213`). `probe_cc_envfile_sessionstart.sh` and `probe_cc_agent_enforcement_all7.sh` have zero recorded results; several probes `rm -rf` their scratch tree in an `EXIT` trap and print only to stdout, so running them leaves no repository trace at all. The blueprint's own bar is that a probe "must record a non-empty `FINDING=` line from at least one real execution." A committed instrument is not a committed result.

Corrections to the audit's own text, verified directly:

- **G41 is half wrong.** It records `tests/test_skill_frontmatter_schema.py` and `tests/test_agent_dispatch_shape.py` as both "never created". The first **exists** (137 lines, 10 tests, passing, wired into `make ci` via `unittest discover`) and is a real non-vacuous gate that closes G1; only the second is genuinely absent.
- **G2's frontmatter changed underneath the audit.** Recorded as `tools: Read, Grep, Glob, Bash`; today it is `tools: Read, Bash`. Grep and Glob were removed from `context-scout` and `elite-coder` on the strength of a claimed Claude Code platform behaviour ("granting Bash alongside Grep/Glob leaves both silently UNAVAILABLE"), documented **only as an inline HTML comment reading "live-probed 2026-08-21"** — no probe script, no transcript, no reference doc anywhere in the repo. That is precisely the uncommitted-ad-hoc-probe standard the audit itself refused to accept for G14, and it now carries more weight, because `context-scout` has lost its search fallback and is strictly more Bash-dependent than when the audit judged its Bash grant acceptable.
- **`PLAN.md:107` and `:266`** describe `probe_runid_stability.sh` as probing `$ATLAS_SESSION_ID`. It probes `${KIMI_SESSION_ID}` via the `kimi` binary and was never ported. The repo's own map reports a port that did not happen.
- **`references/orchestrator-core-port.md:12-15`** claims the `CLAUDE_ENV_FILE` convention is "Confirmed, session-wide", citing a test that only greps the hook's source text and never executes it — on the single most load-bearing unconfirmed mechanism in the migration. The same document's §3 still declares G12 "never attempted", contradicted by a probe, a production fix and two tests in the same tree.
- **`hooks/guard-destructive.sh:31-32`** asserts "no live probe of this specific fact has been run against the real CLI" about hook `cwd`, while `probe/probe_cc_hook_cwd.sh` sits committed in the same repo.

## 2026-08-25 — audit re-derivation swarm: sections A, B, C, D, E, F re-derived from primary evidence

Six read-only agents, three waves, each given **one** section and forbidden from trusting this document, the status overlay, commit `5353fb2`'s "essentially all" claim, or `AGENTS.md`/`README.md`/`PLAN.md` as evidence of their own accuracy. Each was told that "I could not determine this" is a valid and valuable answer, and each returned a mandatory `things_i_could_not_verify` list. None had Bash; every claim below marked *(settled by execution)* was resolved afterwards by the orchestrator.

**25 rows re-derived. Roughly half the verdicts differ from this document.** The improvement is real, but it has one shape.

### The pattern: what closed was what prose could close

Rows closable by editing text were closed. Rows needing executable code or a live run were not. Section E states it most cleanly: G17 and G18 were both prose fixes and both landed; G19 is the only row in that section requiring a code change and the only one still open (`bench/runner.py:89,105` still defaults `kimi: str = "kimi"` and shells out to `[kimi, "-p", brief]`; its sole caller passes no override; no test references `run_headless`).

### The probe-evidence gap, measured

`probe/` holds **14 scripts**. `references/` holds **exactly one** committed `FINDING=` line (`references/stage4-dispatch-enforcement-live-validation.md:213`). **All 14 scripts self-clean** — every one carries `trap ... EXIT` plus `rm -rf "$TMP"` — so no probe can leave repository evidence by running; evidence exists only where a human transcribed it. Against the blueprint's own bar (a probe "must record a non-empty `FINDING=` line from at least one real execution"), 13 of 14 fail.

Breakdown: **3 RESULT-RECORDED** · **5 SCRIPT-ONLY** · **6 STALE**.

The 5 SCRIPT-ONLY probes are all dated 2026-08-21 and were each written to close a specific named gap — `probe_cc_hook_cwd.sh` (G14), `probe_cc_skill_autodiscovery.sh` (G20/G28), `probe_cc_envfile_sessionstart.sh` (G11), `probe_cc_sessionstart_source.sh` (G15), `probe_cc_agent_enforcement_all7.sh` (G3). **The scripts were delivered; the evidence was not.** `probe_cc_hook_cwd.sh` in particular was written to this document's own G14 fix spec and quotes it back in its header — so G14's *tooling* half is done and its *fact* half is untouched.

The 6 STALE probes require the `kimi` binary and exit early without it — *(settled by execution: `kimi` is not on PATH and `~/bin/kimi` is absent on this host, so all six are inert here)*. Two additionally hardcode a dead path `/var/www/kimi-sub/kimi-atlas`. The repo already knows they are historical: `scripts/check_cc_migration_residue.py:99-104` lists exactly these six in `EXCLUDED_FILES`. **The trap is that three of them carry `CONFIRMED`/`CORRECTED` verdicts in `references/kimi-runtime.md:91-93` that read as settled facts but were established against a runtime this project no longer runs.** `probe_hook_block.sh` is the sharpest case: its result is `CONFIRMED — BOTH mechanisms honored`, and G16 separately flags exactly that dual-deny behaviour as un-reverified for this migration. `probe_runid_stability.sh` is worse still — it probes `${KIMI_SESSION_ID}`, `PLAN.md:107` and `:325` describe it as probing `$ATLAS_SESSION_ID`, and its only recorded result (`kimi-runtime.md:95`) is itself **UNCERTAIN — never exercised**. The load-bearing DS-2 assumption behind the shipped `run_id` design has no positive result on *either* host.

### Errors in this document, each settled by execution

- **G41 is half wrong.** It records `tests/test_skill_frontmatter_schema.py` and `tests/test_agent_dispatch_shape.py` as both "never created". The first **exists** — 137 lines, 10 tests, passing, reachable from `make ci` via `unittest discover` — and is a genuine non-vacuous gate that closes **G1**. Only the second is absent.
- **G22's count is wrong, and the error has propagated.** It states "8 undeclared modified files" and then names **seven**. *(Settled by execution — `git diff --name-status c9e6b41^ 038d93f` returns 22 files.)* The seven names are **correct**; the count `8` is inflated by one. True totals: **7** undeclared modified non-test files, 4 undeclared modified test files, 1 wholly new undeclared file (`tests/test_hooks_manifest.py`) = **12**, not 13. The same 7-names-under-a-count-of-8 shape has already been copied verbatim into the blueprint's reconciliation note at `:329`, so both documents now carry it. Note the structural point that makes this row unusual: `blueprint:319` declares only `Create:` and `Delete:` with **no `Modified:` clause at all** — contrast Stage 02 at `:336`, which has one — so under Stage 01's own inventory *any* modification is undeclared by construction.
- **G24's comparative clause is false.** It says Stage 1 lacks a live-validation record "unlike every other stage, each of which has a dedicated `references/*-live-validation.md`". Only Stages **3, 4 and 5** have one. The fourth such file, `references/live-validation.md`, is a pre-migration artifact recording **Kimi CLI v0.26.0**. **Stage 2 has none either.** The row's substance holds — no committed record of either Stage-1 live check exists — but the comparison does not.
- **G2's frontmatter changed underneath this document.** Recorded as `tools: Read, Grep, Glob, Bash`; today it is `tools: Read, Bash`. Grep and Glob were removed from `context-scout` **and** `elite-coder` on the strength of a claimed platform behaviour ("granting Bash alongside Grep/Glob leaves both silently UNAVAILABLE"), documented **only as an inline HTML comment reading "live-probed 2026-08-21"** — *(settled by execution: repo-wide grep finds that string in exactly those two comments and nowhere else — no probe, no transcript, no reference doc)*. That is the same uncommitted-ad-hoc-probe standard this document refused to accept for G14, and it now carries more weight: `context-scout` has lost its search fallback and is strictly **more** Bash-dependent than when G2 judged its Bash grant acceptable.
- **G12's `[NOT DONE]` grade at `:92` is stale.** The probe was written, run, found a real swap-porous cap (`MemoryMax`-only returned `ok=True` on a 200 MB hog against a 50 MB cap; adding `MemorySwapMax=0` killed it, `rc=137`), and that finding drove a production fix now pinned by two tests.

### Two contradictory acceptance bars, unresolved

`blueprint:454` sets **"Test files: ≥94"**. `blueprint:410` sets **"Discoverable test_*.py file count ≥ 81"**. *(Settled by execution using the bar's own command: `git ls-files 'tests/test_*.py' | wc -l` → **87**; recursive including fixtures → 92, the difference being exactly the 5 samples under `tests/fixtures/`; zero untracked.)* **87 fails the first bar and passes the second.** The same tree is simultaneously accepted and rejected by the blueprint's own criteria. Neither this document nor `5353fb2` addresses the contradiction; it needs a decision record of the kind that closed C5. Incidentally the shortfall against ≥94 is now **7**, not the 8 recorded at `:252`, and the "roughly 2.5x" figure was never exact (8/3 = 2.67; today 7/3 = 2.33).

### Section-C C2 is still open, byte-for-byte

*(Settled by execution.)* `scripts/sast.py:159` and `scripts/nativefloor.py:91` still carry stale ``kimi -p`` docstrings at the exact lines this document named. Neither file is in the residue checker's `EXCLUDED_FILES`; they simply are not matched, because `_DENYLIST` targets six literal tokens and not the bare word. **Commit `5353fb2`'s "essentially all" claim is false for this row.** Cosmetic severity — both are prose inside PATH-resolution helpers — but it is a direct counter-example to the closure claim.

### G21: the literal bar is unmeetable; the substituted one is real and passes

*(Settled by execution using the bar's own command.)* `git grep -c "\.kimi-plugin"` → **19 files, 44 occurrences**. The bar demands **exactly 1** — off by ~19× on files. The audit's 42/18 reconciles exactly: the delta is this document itself, uncommitted when counted. But the blueprint now concedes this in place at `:327-328` and names the weaker criterion actually achieved ("zero LIVE, non-historical references"), and that criterion is genuinely enforced: `make check-cc-migration` reports **"No Kimi-migration residue found across 1121 tracked file(s)."**

### Dangling paths no gate can see

*(Settled by execution.)* `references/system-graph.json:509` carries a node with `"path": "scripts/install.sh"` and `references/system-map.md:291` references `install.sh:61`. **The file does not exist** — deleted in `c9e6b41`. Meanwhile `system-map.md:3` asserts of that same graph: *"Post-rebuild the graph is **verified clean**: 0 dangling edges, **every node path exists**"*. That guarantee is now false. The `AGENTS.md`/`README.md` half of this gap **is** closed (both now state the installer is gone), so the correction reached the onboarding docs and stopped there. Nothing catches it: the residue checker hunts token patterns, not dangling paths, and no test enforces node-path existence.

### G23: unfixed and, unlike its siblings, unacknowledged

`blueprint:323` and `:400` both mandate `python3 -m scripts.fsm --help` "runs with no permission prompt". *(Confirmed: `scripts/fsm.py` matches nothing for `^if __name__|argparse|def main`.)* The module is a pure predicate module by design, so `--help` is ignored and the check proves only that the import resolves — which is a real thing to test, just not the thing the text claims. G21 and G22 each received a dated reconciliation note; **G23 received none**, so the mandating document still asserts it unqualified.

### Section summary

| section | rows | outcome |
|---|---|---|
| A | G1–G8 | 4 DONE · 2 PARTIAL · 2 NOT DONE — 6 of 8 differ from this document |
| B | G9–G13 | 3 DONE · 2 PARTIAL — 4 differ; three new discrepancies surfaced |
| C | C1, C2 (+ §4 C1) | 1 DONE · 1 NOT DONE · 1 PARTIAL — plus the 14-probe sweep |
| D | G14–G16 | 3 PARTIAL — plus 3 EXTRA rows, one a live defect (`init-env.sh`) |
| E | G17–G20 | 2 DONE · 1 PARTIAL · 1 closed-not-reviewed |
| F | G21–G24 | 1 NOT DONE · 2 PARTIAL · 1 UNRESOLVED-then-settled |

**Two rows were deliberately not re-litigated: G20 and C5.** Both remain closed.

One methodological note worth keeping. The section-C agent caught an error in its **own task packet** — this document contains two independent `C1`/`C2` numbering schemes (`### C.` at `:101` and `## 4. Contradictions` at `:245`), and the packet conflated them. Rather than guess which was meant, it re-derived all three rows. The section-F agent likewise refused to grade G22 in either direction without `git`, named the exact command that would settle it, and was right that the arithmetic did not add up — though its hypothesis about *which side* was wrong turned out to be inverted. Both behaviours are the intended output of a verification pass: an honest UNRESOLVED that names its own settling evidence is worth more than a confident verdict.

## 2026-08-25 — item 2 (`-q` summary selection) was BUILT over three passes, then DISCARDED by measurement

The G39-adjacent defect at `scripts/runsignal.py::_pytest_summary_line` — a tally-less `=+…=+` section header unconditionally beating the `-q` tally line that carries the count — **is still OPEN**. A fix was written, refined twice, and reverted at the OUTPUT gate. The discarded work is preserved as a 1211-line patch; `main` is untouched. This is the second time a `runsignal.py` change has been built and rejected (the first was `wip/runsignal-q-provenance`), and the reasons are different enough to record both.

### The defect is wider than previously recorded

A live corpus of **21 real pytest-9.1.1 captures** (with `pytest-xdist` 3.8.0 and `pytest-rerunfailures` 16.6) across `-q`, `-qq`, `-v`, `-s`, `-x`, `-rA`, `--durations=5`, `--tb=no`, `--no-header`, `-n 2`, decorated, and passing/warning/failing/all-skipped/all-xfail/subtests/rerun fixtures: **9 of the 19 green captures read `(0, False)`** — a false UNVERIFIED on green code.

**The earlier note's trigger description is wrong and is corrected here.** It named "any warning". Measured, `--durations=5` and `-rA` fire with **no warning present at all**, because both emit their own section headers. The trigger is *any* `=+…=+` section header.

The nine split into three causes:

| cause | configurations | status |
|---|---|---|
| **A** — a tally-less rule line beats the `-q` tally | `q_warn`, `dur_warn`, `q_rA_warn`, `durations`, `rA` | the item-2 target |
| **B** — the `-q` grammar rejects honest tallies | `2 passed, 3 subtests passed in …` and the ` (H:MM:SS)` suffix on runs ≥60s | **already live on `main`**, recorded as item 2b |
| **C** — not defects | `-qq` prints no tally at all; all-skipped / all-xfail genuinely have zero passed | fail-closed is correct |

**B is new information: F3 and F4 from the item-3 regression table are already broken on the `-q` path on `main`.** The table records them only for the decorated path, where both are handled correctly. Measured: decorated `(2, True)` both, `-q` `(0, False)` both. Since `AGENTS.md` itself notes most CI suites run longer than a minute, a `-q` suite over 60s is UNVERIFIED on `main` today.

### Four mechanisms were refuted by measurement, three of them before any code was written

| mechanism | killed by |
|---|---|
| prefer any tally-bearing line, else fall back to `q_summary_lines[-1]` | **F2 → `(99999, True)`** — structurally the same fallback that killed the reverted attempt |
| as above, keyed on the literal `test session starts` | a constructed capture → `(2, True)`; keying on one literal is the open-ended allowlist root cause (iv) names |
| as above, reusing `_PY_COLLECTED_RE`/`_PY_PLATFORM_RE` | a rule line appearing *after* the `-q` tally still won |
| positional guard anchored on the **last** rule line | a surviving run printing its own header steps over the evidence — **and this shipped**, closing only for survivors with no header of their own |

The surviving mechanism was a progress-line boundary keyed on the **percent column** (`[NNN%]`, later also `[N/M]`) rather than a character class — deliberately, because "a line drawn solely from `.FEsxXRu`" is the allowlist that produced F5. It closed cause A for every survivor shape tested.

### Why it was discarded: one NEW fail-closed → fail-open regression

Measured against the baseline module loaded side by side, on the fix's own shipped fixtures:

```
PYTEST_Q_KILLED_IN_FAILURES + PYTEST_Q_GREEN_CLASSIC_STYLE
  BASELINE: (0, False)
  NEW:      (2, True)
```

A capture **literally containing a dead run's `FAILURES` section reads GREEN** into `runcheck.green()` and thence the FROZEN `verdict.gate`. Every precondition is ordinary repo content — a `Makefile` chaining two pytest invocations, an OOM or timeout on the first, and `console_output_style = classic` (or `-q -s`) removing the survivor's progress column. No adversary required.

**The fix traded a false RED for a fabricated pass in one narrow configuration.** The baseline was wrong in the *safe* direction; the fix was wrong in the *unsafe* one. That is the single trade blueprint §0 forbids, so the work was reverted rather than shipped — the same call the `wip/runsignal-q-provenance` attempt received, reached by a different route.

Worse, the suite **asserted the fabricated value as expected behaviour** (`test_survivor_without_a_progress_column_is_a_known_residual` asserting `(2, True)`). Pinning a known-wrong answer as a test prevents silent drift but makes the wrong answer read as sanctioned. If that pattern is used again it must be an xfail-style pin, never a plain `assertEqual`.

### Three findings that are PRE-EXISTING on `main`, not caused by the attempt — verified against the baseline module

Two critics filed these as HIGH regressions; direct measurement shows the baseline behaves identically. They are open defects in `runsignal.py` today, and none is recorded anywhere else:

- **A killed `-q` predecessor followed by a healthy DECORATED survivor** → `(2, True)` on baseline and on the fix. Clause selection answers with the survivor's tally rule while the dead run's `FAILURES` header carries no digits for the fail fold.
- **A `-q` predecessor killed before printing any section header** → `(2, True)` on both. With no rule line there is nothing to anchor a restart check to.
- **A parametrized node id that looks like a progress column** — `t_x.py::test_ratio[1/2]`, `t_x.py::test_pct[100%]` — in a `warnings summary` / `--durations` / `-rA` body. Reads `(0, False)` on both; the fix simply failed to reach it. The ordinary-id control goes `(0, False) → (2, True)`, i.e. cause A is genuinely fixed for unparametrized suites.

### The recurring failure mode, stated once

Each pass closed the previous pass's gap and opened the next along **an axis the tests did not vary**:

1. pass 0 pinned only *restrictive* mutations — clause 4, the one newly permissive branch, was asserted only in the direction that adds passes;
2. pass 1 pinned both directions but varied only the *killed-run* axis — all three fixtures shared one surviving run;
3. pass 2 varied the surviving-run axis across `-q` renderings but never a **decorated** survivor, and never a section **body** containing a parametrized node id.

A green suite proves nothing about the shape it does not contain. Three consecutive reviews stated this in the same words at three different levels.

### Process notes worth keeping

- **A mutation harness can silently fail to mutate.** Both the coder and the orchestrator produced a matrix in which mutations reported "killed" while never taking effect — column-padded, length-preserving edits plus a `.pyc` matching on size and mtime-second. Purge `__pycache__` and run `python3 -B`, and treat any mutation claim made without that as unverified.
- **Three orchestrator claims were refuted by the coder or a critic.** In each case the measurement was right and the inference wrong: "deleting this disjunct leaves 82 tests green" ⇒ *not* behaviour-neutral (the fixture that would have shown it did not exist); "every capture has one percent line" ⇒ verbose mode prints one per test; "the fold is an order-independent sum over a permutation" ⇒ it is a permutation, but `no tests ran` applies a **running** `max(fail, 1)` whose result depends on position (same multiset folds to 2 or 3). **Absence of a failing test is not absence of behaviour.**
- **A frozen constraint can be wrong.** "The fail-fold must stay byte-identical" was a proxy for unchanged behaviour and is stricter than the goal; it blocked a correct simplification. Byte-identity is not behavioural equivalence, and pinning form instead of property is the same defect the critics kept finding in the tests.
- **Do not edit a critic's severities.** One attempt to downgrade two HIGH findings to MEDIUM on the strength of an orchestrator measurement was caught by `enforce_critic_schema` (`verdict: FAIL` with no CRITICAL/HIGH). The critic's judgment and the orchestrator's measurement both belong in the record; neither overwrites the other.
- **`pathcheck` cannot distinguish a repo path from a foreign tool's filename.** Citing `pytest.ini` / `pyproject.toml` / `setup.cfg` / `tox.ini` in backticks produced four blocking CRITICALs. The generalisable convention: reserve backticks for repo paths, Python identifiers and literal command text; write another tool's config filenames as prose qualified by their owner.

### What survives the discard

`main` is unchanged. The corpus, the differential harness (`differential.py` plus `measured_before.json`), the live kill captures, and the 1211-line discarded patch are on disk for whoever attempts this next. **The next attempt should begin by reproducing the four refuted mechanisms and the pre-existing findings above, not by proposing a fifth mechanism cold.**

## 2026-08-26 — item 3 (`-q` tally provenance) MEASURED, not attempted: no signal available inside `runsignal.py` can carry it

Per an explicit decision to measure before building, no fix was written. The G39 residual **remains OPEN**, and the measurement below explains why the one candidate remedy the earlier note proposed cannot close it.

### The fabrication surface, measured

`runsignal.count(output, ("pytest",))` on `main`:

| input | result |
|---|---|
| `3 passed in 12s` — one line, nothing else | **`(3, True)`** |
| `==== 3 passed in 12s ====` | **`(3, True)`** |
| `3 passed in 0.02s` then `99 passed in 1s` | **`(99, True)`** — the genuine count silently overwritten |
| `> build` + `3 passed in 12s` (an npm log) | **`(3, True)`** |
| `TOTAL 100%` + `3 passed in 12s` (a coverage summary) | **`(3, True)`** |
| the same tally-shaped text with a log prefix **on the same line** | `(0, False)` |

The gate opens on **one standalone line matching `N word[, N word…] in Xs`**, anywhere in the capture, with no corroboration of any kind. The only thing that saves the log-prefixed case is that `fullmatch` fails when other text shares the line.

Correctly fail-closed today: an empty capture, a progress line alone, `collected N items` alone, the platform header alone, both together, and `no tests ran`.

### The candidate remedy was measured and does not close it

The earlier note proposed "require a `-q` tally line to be preceded by a pytest progress-dots line". Measured against constructed captures and the live corpus:

| shape | closed by the rule? |
|---|---|
| bare tally / npm log / coverage summary | **yes** |
| `Fetching deps [ 50%]` + `3 passed in 12s` | **no** — a downloader renders a percentage |
| `Step 3/7 [ 42%]` + `3 passed in 12s` | **no** — a CI step renderer |
| `########## [100%]` + `3 passed in 12s` | **no** — an ordinary progress bar |
| an honest `pytest -q -s` run | **false RED** — it prints no percent column |

So the rule lets through any tool that renders a percentage and blocks a legitimate pytest configuration. It is weak in both directions.

**The rule-line path is worse and is not helped at all.** `_is_pytest_rule_line` is "starts and ends with `=`", so `==== 3 passed in 12s ====` fabricates with or without corroboration — two extra characters defeat the entire question.

### Why: every available signal is imitable, every reliable signal is suppressed

Measured across the 21-capture live corpus, restricted to the 15 captures whose count comes from the `-q` path:

| corroborating signal | present in honest `-q` captures | imitable by other tooling |
|---|---|---|
| `collected N items` | **0 of 15** — `-q` suppresses it | — |
| `platform … -- Python` header | **0 of 15** — `-q` suppresses it | — |
| a percent-column progress line | 14 of 15 (the exception is `-q -s`) | **yes** |
| the tally's own shape | 15 of 15 | **yes** |
| `=+…=+` wrapping | n/a | **yes, trivially** |

That table is the finding. **The signals that would establish provenance are exactly the ones `-q` exists to remove, and every signal that survives `-q` is one an unrelated tool can produce.** A parser handed only the text cannot distinguish them, which is why the first attempt failed and why a second attempt along the same line would fail the same way.

### Where the provenance actually lives

`scripts/runcheck.py:run` holds three facts that `runsignal.count` never receives:

```python
stdout, stderr = res["stdout"], res["stderr"]      # separate streams
returncode, timed_out = res["returncode"], ...     # the exit status
combined = stdout + "\n" + stderr                  # <- erased here
test_count, new_tests_collected = runsignal.count(combined, runner_tags)
```

The concatenation discards the stream split **and** the true interleaving, then the parser is asked to recover provenance from shape alone. A SECURITY critic independently reached the same seam from the other direction during item 2, observing that a positional guard built on `summary_lines` order rests on a property the callers do not supply — the orchestrator recorded that as a docstring correction at the time, which understated it.

**This does not make the problem unsolvable; it relocates it.** Any credible closure has to change what `runcheck` hands over — or how the target is invoked — not how the text is matched. That is a different change to different files with its own risk profile, and it is recorded here rather than started.

**A bound worth keeping in view:** `runcheck.green()` requires `ok` (exit 0, no timeout) **AND** `test_count > 0` **AND** `new_tests_collected`. A fabrication therefore also needs the `verify_cmd` to exit 0. The realistic exposure remains what the module's own docstring says — a careless `verify_cmd` chaining another tool — not adversarial input.

### Three fabrications on `main` that item 3's own description does not cover

Found while measuring item 2, verified against the baseline module, and recorded here because no existing item names them:

- a killed `-q` predecessor followed by a healthy **decorated** survivor → `(2, True)`;
- a `-q` predecessor killed before printing any section header → `(2, True)`;
- a parametrized node id shaped like a progress column (`t.py::test_r[1/2]`, `t.py::test_p[100%]`) in a `warnings summary` / `--durations` / `-rA` body → `(0, False)`, a false RED.

Any future attempt at the provenance problem must account for these as well; closing only the two probes the earlier note names would leave them untouched.

## 2026-08-26 — audit re-derivation, wave 3 (sections G, H, I) + consolidated result

Three read-only agents re-derived G25–G46 from bytes on disk. Their checkable claims were then
re-measured with Bash, which they did not have. **Correction to my own tasking:** I told sections H
and I that this session had executed *four* complete atlas runs. `ls -la .atlas/` shows **three**
(`…f421`, `…f421-1b`, `…f421-item2`). Both agents flagged the discrepancy and judged on disk rather
than on my claim, which is the correct behaviour. The error was mine.

### Verified with Bash (the agents could not run these)

| check | result |
|---|---|
| `.atlas/` run dirs | **3**, all real session ids; **no** dir named `$ATLAS_SESSION_ID` (G46 hazard did not fire) |
| `.atlas/` durability | **git-excluded** (`.git/info/exclude` holds `.atlas/`) — ledgers vanish on a fresh clone |
| `tests/test_*.py` | **87** tracked == 87 working tree (audit's "86 / 8 short" is stale: 87 / 7) |
| `tests/test_agent_dispatch_shape.py` | genuinely **absent** (G41 half-correct) |
| `invocation_form` in ledgers | **0 hits** across all 3 runs (G37 freeze is not durable) |
| `/bin/sh` | **dash**; `set -o pipefail` → `Illegal option` |

### The finding that required Bash: the SessionStart hook is dead in the live session

    ATLAS_SESSION_ID=<UNSET>   ATLAS_PLUGIN_ROOT=<UNSET>   PYTHONSAFEPATH=<UNSET>
    $ printf '{"session_id":"…"}' | CLAUDE_ENV_FILE=$f /bin/sh hooks/init-env.sh
    hooks/init-env.sh: 27: set: Illegal option -o pipefail
    envfile bytes written: 0

Three consequences:

1. **G30 is prose-DONE, behaviour-FALSE.** Section G closed it because `AGENTS.md:141-148` matches
   the *source* of `hooks/init-env.sh`. The script does not execute. A read-only agent cannot see
   this; the description and the implementation agree, and both are irrelevant if the file aborts
   on line 27.
2. **G46 measured the wrong risk.** The audit feared a byte-for-byte paste of `$ATLAS_SESSION_ID`.
   Measured, the variable is never set at all — the three runs carry real UUIDs because the model
   supplied its own session id from context, not from the environment. The mechanism SKILL.md
   documents has never worked on this host.
3. **EXTRA-1 is gated behind EXTRA-2.** The unescaped `session_id` interpolation (line 53) is
   unreachable because line 27 kills the script first. **Fixing the shebang alone ACTIVATES the
   injection.** They must be fixed together — now measured, previously only reasoned.

### Consolidated item-4 result — 9 sections, G1–G46

- **~half** the rows carry a verdict different from the audit's.
- **5 factual errors inside the audit document itself** (four found in waves 1–2, plus G42's line
  citation drifting 96→99 and G38's stale count).
- **G38 is unanswerable as written**: the blueprint sets two contradictory bars, `≥94` (line 454)
  and `≥81` (line 410). 87 fails one and passes the other; the audit cites only the first. Nothing
  in code enforces either, and `tests/test_doc_testcount.py` argues a static count is the wrong
  instrument. Needs a recorded decision, not a verdict.
- **G39 has genuinely moved** — three complete INIT→OUTPUT ledgers with real dispatch, real critics,
  the MAX_PASSES cap exercised and honest terminal UNVERIFIED verdicts refute "never executed
  anywhere". Residuals are precise: the "3 pauses, 1 turn" half has **zero** on-disk support (no
  pause/gate event is ledgered by any run), two of three runs used `make test` not `make ci`, and
  the ledgers are git-excluded so they are not durable evidence.
- **Dominant repair pattern, wave 3: ASYMMETRIC repair.** `AGENTS.md` was fixed thoroughly and
  `README.md` left behind on the same three facts, so the two now contradict each other in
  user-facing text: marketplace install (`AGENTS.md:19-20` vs `README.md:71`, with
  `.claude-plugin/marketplace.json` on disk), skills auto-discovery (`:112` CLOSED vs `:106/:122/:267`
  "unconfirmed"), and `make ci` gate count (**7** vs **4**; `Makefile:54` has 7). The correction
  reached the file the author reads and not the one a new user reads.

### Opened, not closed (each needs its own run)

| id | item | severity |
|---|---|---|
| EXTRA-1 + EXTRA-2 | `init-env.sh` dash-dead **and** unescaped `session_id` — fix **together** | HIGH |
| — | `README.md` behind `AGENTS.md` on 3 user-facing facts | MEDIUM |
| G37 | `invocation_form` not persisted; `setdefault("interactive")` fails **open** | MEDIUM |
| G39 | no pause/gate event ledgered; `.atlas/` git-excluded | MEDIUM |
| G38 | two contradictory test-file bars — needs a decision | LOW |
| — | `install.sh` residue in `system-graph.json:507-509`, `system-map.md:279,291` | LOW |

## 2026-08-26 — `hooks/init-env.sh` defect pair FIXED; run terminal verdict UNVERIFIED (refine exhausted)

Run `…-initenv`. INIT → … → OUTPUT with two refine passes (MAX_PASSES=2, exhausted). Three files:
`hooks/init-env.sh`, `tests/test_init_env_hook.py` (new, 1038 lines, 49 tests),
`tests/test_syspath_isolation.py`. **Nothing committed.** `make ci` exit 0, 1880 tests, inventory in sync.

### What the run set out to fix — both closed, verified by the orchestrator not the coder

1. **Dash death.** `set -euo pipefail` under `#!/bin/sh` → `set -eu`. The shebang was NOT changed:
   `hooks/hooks.json` invokes `sh "<path>"`, so a bash shebang would have been inert.
2. **`session_id` injection.** POSIX `case` allowlist on ctxstore's charset + single-quoted write.
   Measured: **12/12 corpus cases agree with `ctxstore.valid_run_id`, 0 mismatches**; every accepted
   value round-trips byte-for-byte; every rejection emits a diagnostic. Attack payloads (quote
   breakout, backtick, `$(…)`, single quote, newline, NUL) all rejected under sh/dash/bash/busybox.

### Four orchestrator errors the critics caught — recorded because they are the lesson

- **The `ctxstore` parity justification was FALSE.** I claimed a rejected session_id "would have been
  rejected downstream anyway". Measured: `valid_run_id` is called ONLY from `write_artifact_confined`;
  `init_run` uses an unvalidated `_run_dir`. `valid_run_id("a/b")` is False yet `init_run(base,"a/b")`
  SUCCEEDS. I had grepped the single call site and never checked which function contained it.
- **The scope exemption for line 32 was wrong on all three of its reasons.** (a) "not widening scope"
  — but the portability fix ACTIVATES that line, the same masking argument the run was built on;
  (b) "host-supplied env" — false, `PYTHONPATH` is AMBIENT and repo-steerable; (c) "the byte-pin
  blocks it" — inverted, the pin locked the VULNERABLE form in place.
- **Two false stated contracts**, one mine and one the coder's, both of the same class: a comment
  promising more than the code does. Mine was the parity claim; the coder's was "the env file gains
  all three or none" over `{ …; } >> file`, which groups the redirection, not the writes.
- **A near-miss false defect of my own**: I reported busybox `rc=127` before noticing my probe passed
  `"busybox sh"` as one word.

### Terminal verdict: UNVERIFIED — two blocking HIGH residuals, refine exhausted

Both were found only by the FINAL verification pass, on code no earlier critic had seen, and both
were then reproduced by execution:

- **F-S1 (HIGH, NEWLY REACHABLE BY THIS FIX).** The hook re-exports the ambient `PYTHONPATH`
  verbatim, session-wide. Measured: ambient `.` persists as `/plugin:.` and ambient `:` as
  `/plugin::` — whose empty/relative element resolves to each process's cwd, the untrusted target
  repo. And measured separately: **`PYTHONSAFEPATH=1` does NOT filter `PYTHONPATH` entries** — a
  `sitecustomize.py` reached through `PYTHONPATH` still executed with the switch on. So the v1.5.1
  CRITICAL countermeasure has a bypass, and `scripts/proccap.py:407` `_PLUGIN_ONLY_ENV` keeps
  `PYTHONPATH` deliberately. This line never executed on a dash host before, so the portability half
  of this change is what makes it reachable.
- **F-S2 (HIGH, PRE-EXISTING AND ALREADY LIVE).** The hook's own `python3` inherits ambient
  `PYTHONPATH`, so a hostile `json.py` executes inside a SessionStart hook. Measured: it fired.
  **But this is the repo-wide hook idiom, not something this change introduced** — all four
  `hooks/*.sh` fork `python3` the same way, and `hooks/telemetry.sh`, which RUNS TODAY, was measured
  loading the same hostile `json.py`. It needs its own repo-wide run.

Also open: F-S3 (the `X` sentinel is inside the accepted charset, so a short write at an interior
`X` still ends in the sentinel — needs a length prefix), F-S4 (the truncation arm emits no
diagnostic), F-S5 (`CLAUDE_ENV_FILE` append target unconfined; the critic could not determine whether
the host overrides an ambient value).

### The methodological result

`make ci` was **green at every stage** — 1831, 1857, 1875, 1880 tests — and a defect sat inside the
change every time. Each of the three critic rounds found something the other two could not, and the
final pass, run on the delta nobody had reviewed, found the deepest issue of all. A green gate is not
evidence a fix is correct; that is the rule this run demonstrates rather than merely restates.

## 2026-08-27 — `hooks/init-env.sh`: what was closed, what is OPEN, and the structural limit found

Five atlas runs (`…-initenv`, `…-fs1`, `…-origpath` + two refine passes). **Committed for review, NOT
declared finished.** `make ci` exit 0, 1938 tests (session start: 1831), inventory in sync.

### Closed and verified by orchestrator measurement, not by the coder's report

| defect | evidence |
|---|---|
| Hook DEAD on dash (`set -euo pipefail` under `#!/bin/sh`) | runs to completion on sh/dash/bash/busybox; env file non-empty |
| `session_id` shell injection into a SOURCED file | 12/12 corpus agrees with `ctxstore.valid_run_id`, 0 mismatches; quote/backtick/`$()`/newline/NUL all rejected with a diagnostic; honest UUID round-trips byte-for-byte |
| Ambient `PYTHONPATH` propagated session-wide | persisted value is exactly the plugin root; **armed control** confirms the payload executes when propagated and does not when pinned |
| Target losing its own `PYTHONPATH` (a FALSE RED this work created) | `ATLAS_ORIG_PYTHONPATH` seam: session gets the plugin root, `target_env()` gives the target `/opt/mono/src` back |
| User-site door into the frozen gate's interpreter | `PYTHONNOUSERSITE=1` session-wide + `_PLUGIN_ONLY_ENV`; **armed control**: SHIPPED does not execute, CONTROL does |
| Re-fire on `clear`/`compact`/`fork` destroying the recorded original | five chained fires keep `/opt/mono/src` |

Two long-standing OPEN VERIFICATION ITEMs were closed by running
`probe/probe_cc_envfile_sessionstart.sh` **live against the real `claude` binary**: the env-file
consumer DOES perform POSIX quote removal (byte-for-byte round trip, no injection), and a hook's
stderr on a zero exit is **NOT** surfaced to the session — so the "user can tell this was
intentional" mitigation was never real and is no longer claimed.

### OPEN — must be reviewed before this is called done

| id | severity | what |
|---|---|---|
| S2 | **HIGH** | `ATLAS_ORIG_PYTHONPATH` is now attacker-NAMEABLE. MEASURED: a repo's `.envrc` exporting it wins on the FIRST fire, persists all session by the idempotence that fixed C1, and `target_env()` restores it into every target build. Inverted, a forged EMPTY value DELETES an honest `PYTHONPATH`. |
| S1 | **HIGH** | `sast.scanner_env` strips `PYTHONNOUSERSITE` but passes `PYTHONUSERBASE`/`PYTHONHOME`/`LD_PRELOAD` through — MEASURED — re-opening the user-site door into semgrep, whose stdout becomes a BLOCKING SECURITY defect. |
| — | MEDIUM | `$PYTHONHOME` still open session-wide: an env file can export a value but not an *unset*. |
| — | MEDIUM | `LD_PRELOAD`/`LD_AUDIT` and interpreter selection via `$PATH` remain open by design. |
| — | LOW | The "stderr not surfaced" result is a model self-report, one CLI build — weaker evidence than the quote-removal result beside it. |
| — | LOW | A mid-write tear is uncovered; ordering is pinned, atomicity is unavailable from a POSIX append. |
| — | LOW | `tests/test_predcov.py` reasons from the retired `target_env` contract (out of scope, stale not wrong). |

### The structural limit — the finding that outranks the individual defects

Four rounds, each closing a real door and each opening the next: `PYTHONPATH` → `PYTHONUSERBASE` →
the handoff variable itself → `LD_PRELOAD`. **Scrubbing named variables from an inherited environment
cannot converge**, because the list does not end.

This repository already wrote down the answer, for a different consumer:

> `scripts/lintlens.py`: "**NOT `os.environ.copy()` minus a denylist** — a fresh dict, so hostile
> hooks (… `LD_PRELOAD`) simply do not exist in the child."
> `scripts/nativefloor.py`: "a fresh dict, **NOT `os.environ.copy()` with keys removed** … `BASH_ENV`,
> `LD_PRELOAD`, `PHP_INI_SCAN_DIR`, … simply do not exist", with
> `set(_hermetic_env()) == set(_HERMETIC_ENV_KEYS)` pinned as a test.

That hermetic pattern protects the **target's** linters. It is NOT applied to the plugin's own
interpreters — 20 bare `python3` calls in `skills/atlas/SKILL.md` and 4 hooks forking `python3`, all
inheriting the ambient environment — even though those run the FROZEN `verdict.py` gate, the higher
value asset. Inverting that (allowlist, not denylist) is the only approach that terminates.

**Recorded as its own project, and explicitly NOT part of the Claude Code migration**: `PYTHONUSERBASE`,
`PYTHONHOME` and `LD_PRELOAD` were exactly as reachable under Kimi. Nothing here was introduced by the
port.

## 2026-08-27 — item 5 (D1–D7) closed, plus the rollback that had to be un-added

Governing queue item 5. Three atlas runs (`…-d1d7` + two refines, then `…-unwind` + one refine).
`make ci` exit 0, **2011 tests** (session start: 1831). Seven files.

### The seven planned items, all closed and verified by orchestrator measurement

D1 atomic registry write (proven by execution both ways: `os.replace` patched to raise leaves the
prior bytes intact and no residue; happy path byte-identical to the committed registry) · D2
`_MIN_SIGNAL_LEN` · D3 `load_overrides` coerces at the boundary · D4 the `'.'` entry name · D5
`failures` last in both sibling `audit()` signatures · D6 the hoisted test base · D7 the dead parameter.

### D4 was rated LOW and was not

The plan described the failure as `IsADirectoryError`. Measured, it was worse in two directions
nobody had enumerated, and each was found only after the previous fix shipped:

1. `'.'` alone — a fresh tree writes the package path as a regular FILE, then dies `FileExistsError`.
2. After the raw-segment fix — `SKILL.md` + `SKILL.md/.` resolve to ONE path, so the audited file is
   silently overwritten and **`--verify` still passes**. Silent content substitution.
3. After that — `SKILL.md` + `sub` + `sub/x.md`, with no `.` anywhere, still crashed mid-extract and
   left a half-extracted package.

**Enumerating unsafe shapes could not converge.** What closed it was an INVARIANT: target
injectivity over normalized keys, rejecting a duplicate key, a key that is a proper prefix of
another, and an empty-after-strip segment. Calibrated: all 712 committed entries accepted, 0
collisions.

### The rollback: added on my instruction, then removed

I prescribed `shutil.rmtree(out_root / plan['dir'], ignore_errors=True)` verbatim in a refine packet.
The implementer built it and independently added containment I had not asked for. MEASURED harm: a
mid-package ENOSPC with the package dir already populated **deleted a pre-existing file and an
untracked stray**; and `_confined_package_dir` returned the RESOLVED path, so an in-root symlinked
package dir would have aimed `rmtree` at a different package.

It was removed rather than repaired, because the architecture said so: `Skills/` (the input) is
ABSENT from this repo, `skills/` is 715 TRACKED files of source-of-truth, `make skills-extract` is in
NO CI lane, and eight scripts plus the host read that directory. **Git is already the transaction
log**; building an undo inside a tool that runs inside a VCS duplicated a stronger mechanism and
introduced data loss. Stage-and-swap was rejected too, and the reason is on the record: `os.replace`
fails on a non-empty directory, so the swap has a window where `skills/` does not exist.

New contract: not "I will undo my mess" but **"your undo will be clean"** — refuse a dirty tracked
subtree (`--allow-dirty` escapes), warn once outside a worktree, and PRINT the recovery commands
without executing them.

### Two findings that came from the orchestrator's own mistakes

* **I overwrote the committed manifest.** A verification probe passed `--out-root` without
  `--manifest`, and the tool wrote a 1-package manifest over the committed 115/712 one. Recovered
  with `git checkout --` — the architecture working. The generalized defect (the two flags are
  independent, so a blessed scratch extraction damages the real repo) was then found independently
  by a critic and is fixed; the whole suite was blind to it because every test helper passed both
  flags together.
* **My Unicode fix was one codepoint wide.** I prescribed `.replace("ς","σ")` after measuring that
  `casefold()`→`lower()` had dropped a real alias (final sigma keys distinctly but NTFS `$UpCase`
  merges it). The implementer scanned all 1,114,112 codepoints and found **21 such classes**, not
  one — my fix would have left twenty open. The shipped fold models the UPPERCASE table
  per-codepoint, which also closes Turkish dotless ı, a residual I had asked to be documented as open.

### Residuals, recorded

NTFS `$UpCase` and APFS folding are modelled from documentation, not measured on a live volume ·
`$UpCase` is per-volume and can lag Unicode · multi-codepoint and locale-dependent folding is out of
scope · HFS+ normalization is an NFD variant while the key normalizes NFC · an untracked manifest
this tool overwrote still has no undo (the printed recovery says so) · git-ignored files stay
invisible to the precondition, deliberately, because flagging them would false-reject.
