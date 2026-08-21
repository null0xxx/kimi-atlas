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
