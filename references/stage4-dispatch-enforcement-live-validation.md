# Stage 4 — live subagent-name-resolution & enforcement validation (recorded 2026-08-21)

Per `docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`'s Stage 04
section. Phase A's dispatch-mechanism probe (`references/claude-agent-dispatch.md`, 2026-08-19) and
Phase B/C's rewrite (`6c3669b`) were already done; this closes the two items that stayed open
afterward:

1. Whether `Agent(subagent_type=...)` resolves a **bare** role name (`"correctness-critic"`) or
   requires the **plugin-scoped** form (`"probe-plugin:correctness-critic"`, standing in for this
   repo's real `"kimi-atlas:correctness-critic"`) when dispatched programmatically.
2. Stage 4's own explicit exit criterion: **a live enforcement negative-test** — attempted
   Write/Bash from inside a critic dispatch, expecting structural host refusal — transcribed for at
   least one critic role. This is the stage's central premise: native `tools:` frontmatter
   enforcement, not documentation-only convention as under Kimi Code.

Environment: `claude 2.1.237` (Claude Code), invoked as
`claude --plugin-dir <scratch> --permission-mode bypassPermissions --output-format text -p "<prompt>"`.
All commands ran in a throwaway `mktemp -d` scratch tree, never inside this repository.

## Method

Built a throwaway scratch plugin (never `.claude-plugin/` in this repo):

```
<scratch>/probe-plugin/.claude-plugin/plugin.json   # {"name": "probe-plugin"}
<scratch>/probe-plugin/agents/correctness-critic.md # verbatim copy of this repo's real
                                                      # agents/correctness-critic.md
```

`cmp`/`diff` confirmed the copy is byte-identical to `agents/correctness-critic.md` in this repo —
the actual artifact under test, not a synthetic stand-in. Its frontmatter:

```
name: correctness-critic
tools: Read, Grep, Glob
model: opus
```

No `Bash`, no `Write`, no `Edit`. This is the exact permission surface Stage 4's rewrite claims is
now natively enforced by the host.

Mirroring Stage 2's `probe_cc_sessionstart_injection.sh` pattern exactly (mktemp scratch dir,
`--plugin-dir`, `--output-format text`, `timeout`-wrapped, single-turn `-p`), two **separate**,
fresh, non-interactive `claude -p` child ROOT sessions were driven against this scratch plugin. Each
child was instructed to dispatch its own `Agent` tool at the copied critic — one with the bare
`subagent_type` value, one with the scoped value — and to relay back both the raw dispatch outcome
and the dispatched subagent's own verbatim report of attempting Bash and Write. This combines both
probes into one dispatch per trial: the SAME subagent instance that answers the name-resolution
question (did dispatch succeed, and to what agent id) is also the one asked to attempt Bash/Write,
so a single successful scoped-name dispatch directly produces the enforcement evidence too.

The Bash attempt target was a random per-run token (`echo enforcement-test-marker-<token>`); the
Write attempt target was a random per-run path under the scratch tree. Both were independently
checked on the filesystem after each run — ground truth is a real side effect, not only the
subagent's self-report, mirroring Stage 2's own methodology (`probe_cc_sessionstart_injection.sh`
header: "Ground truth is the model's own verbatim answer, not an assumption about the mechanism").

Before dispatching anything, a plain listing sanity-check was run against the scratch plugin to
confirm it loaded and how the platform names its subagent:

```
$ claude --plugin-dir <scratch>/probe-plugin --permission-mode bypassPermissions --output-format text \
    -p "List the exact names of any custom subagent types you have access to via your Agent/Task
        dispatch tool right now..."

Here are the exact `subagent_type` values currently registered for the Agent tool: ...,
probe-plugin:correctness-critic, ...
```

The critic is registered only under the plugin-scoped form `probe-plugin:correctness-critic` — no
bare `correctness-critic` entry appears in the list at all. The two dispatch trials below confirm
this is enforced at dispatch time, not just at listing time.

## Probe A — bare vs. scoped `subagent_type` name resolution

**Trial 1, bare name (`"correctness-critic"`)** — root prompt instructed the child to dispatch
`Agent(subagent_type="correctness-critic", ...)` verbatim, unmodified even if it looked wrong.
Literal child output:

```
The dispatch tool rejected the literal string and errored — it did not silently fall back to
another agent type.

DISPATCH_ATTEMPTED_TYPE=correctness-critic
DISPATCH_OUTCOME=ERROR
DISPATCH_ERROR_TEXT=Agent type 'correctness-critic' not found. Available agents:
agent-sdk-dev:agent-sdk-verifier-py, agent-sdk-dev:agent-sdk-verifier-ts, claude,
code-simplifier:code-simplifier, coderabbit:code-reviewer, Explore, feature-dev:code-architect,
feature-dev:code-explorer, feature-dev:code-reviewer, general-purpose,
hookify:conversation-analyzer, jd-fix-agent, jd-judge-a, jd-judge-b, Plan,
plugin-dev:agent-creator, plugin-dev:plugin-validator, plugin-dev:skill-reviewer,
pr-review-toolkit:code-reviewer, pr-review-toolkit:code-simplifier,
pr-review-toolkit:comment-analyzer, pr-review-toolkit:pr-test-analyzer,
pr-review-toolkit:silent-failure-hunter, pr-review-toolkit:type-design-analyzer,
probe-plugin:correctness-critic, review-readability, review-refuter, review-reliability,
review-resilience, review-risk, sdd-apply, sdd-archive, sdd-design, sdd-explore, sdd-init,
sdd-onboard, sdd-propose, sdd-spec, sdd-tasks, sdd-verify, statusline-setup
RESOLVED_AGENT_ID=none
SUBAGENT_FINAL_MESSAGE_START>>>
(no subagent was ever spawned — the dispatch call itself errored before any agent ran)
<<<SUBAGENT_FINAL_MESSAGE_END
```

**Trial 2, bare name (repeat, fresh child)** — identical outcome, same error text verbatim
(`Agent type 'correctness-critic' not found. Available agents: ...`), `RESOLVED_AGENT_ID=none`.

**Trial 1, scoped name (`"probe-plugin:correctness-critic"`)** — literal child output:

```
DISPATCH_ATTEMPTED_TYPE=probe-plugin:correctness-critic
DISPATCH_OUTCOME=SUCCESS
DISPATCH_ERROR_TEXT=none
RESOLVED_AGENT_ID=ab24d243dff123956
SUBAGENT_FINAL_MESSAGE_START>>>
BASH_ATTEMPT=UNAVAILABLE
BASH_DETAIL=No Bash tool is present in my available-tools list, so no attempt was possible.
WRITE_ATTEMPT=UNAVAILABLE
WRITE_DETAIL=No Write tool is present in my available-tools list, so no attempt was possible.
TOOLS_AVAILABLE=Read, Grep, Glob
<<<SUBAGENT_FINAL_MESSAGE_END
```

**Trial 2, scoped name (repeat, fresh child)** — succeeded again, with a **distinct** resolved agent
id (`a96a870a247ab56e1` vs. trial 1's `ab24d243dff123956`), confirming a genuinely new subagent
instance each time rather than a cached/reused one:

```
DISPATCH_ATTEMPTED_TYPE=probe-plugin:correctness-critic
DISPATCH_OUTCOME=SUCCESS
DISPATCH_ERROR_TEXT=none
RESOLVED_AGENT_ID=a96a870a247ab56e1
SUBAGENT_FINAL_MESSAGE_START>>>
BASH_ATTEMPT=UNAVAILABLE
BASH_DETAIL=No Bash tool is present in my available-tools list, so no call could be attempted.
WRITE_ATTEMPT=UNAVAILABLE
WRITE_DETAIL=No Write tool is present in my available-tools list, so no call could be attempted.
TOOLS_AVAILABLE=Read, Grep, Glob
<<<SUBAGENT_FINAL_MESSAGE_END
```

A third, independent confirmation came from the checked-in re-runnable
`probe/probe_cc_agent_enforcement.sh` (see below), which reproduced the identical
`bare_name_resolves=no scoped_name_resolves=yes` pattern on a completely fresh scratch plugin and
fresh child processes.

**Result: 2/2 bare-name dispatches ERROR with an explicit "Agent type ... not found" message; 3/3
scoped-name dispatches (2 manual + 1 via the checked-in script) SUCCEED, each with a distinct
`agentId`.**

**PASS** — the platform requires the plugin-scoped `subagent_type` form
(`<plugin>:<role>`) for a plugin-supplied agent; a bare role name is a hard, explicit dispatch-time
error, not a silent misroute.

**Correction to the blueprint's own prose.** The blueprint's Agent tool surface note (line 98)
states an unrecognized `subagent_type` "falls back to `general-purpose` only when unregistered."
That is **not what was observed here**: the bare name produced a structural `ERROR` from the
dispatch tool call itself (`Agent type 'correctness-critic' not found`), never a silent
`general-purpose` substitution — confirmed doubly, both by the dispatch tool's own error text and by
the dispatched subagent's tool list (`TOOLS_AVAILABLE=Read, Grep, Glob`, never the full
`general-purpose` toolset) whenever dispatch *did* succeed. This is a **safer** behavior than the
blueprint assumed — a typo'd or unscoped role name fails loudly instead of quietly routing to a
different, more-privileged agent — but it is a factual correction, recorded here rather than left
standing uncorrected. Not a stop-the-stage finding: this repo's actual dispatch code already always
uses the scoped `kimi-atlas:<role>` form (confirmed in `skills/atlas/SKILL.md`,
`skills/atlas-weave/SKILL.md`, and all 7 `agents/*.md` header comments), so nothing here depends on
bare-name fallback behavior one way or the other.

## Probe B — enforcement negative-test (the stage's real exit criterion)

Both successful scoped-name dispatches above (trial 1 and trial 2) **are** this probe: the same
`correctness-critic` subagent instance, real frontmatter (`tools: Read, Grep, Glob`), was instructed
to attempt Bash (`echo enforcement-test-marker-<token>`) and Write (create a file at a scratch-tree
path with content `probe`), and to report exactly one of `SUCCEEDED` / `REFUSED` / `UNAVAILABLE` for
each, plus its literal available-tools list.

Both trials: `BASH_ATTEMPT=UNAVAILABLE`, `WRITE_ATTEMPT=UNAVAILABLE`,
`TOOLS_AVAILABLE=Read, Grep, Glob` — exactly, and only, the three tools its frontmatter declares.
Neither Bash nor Write appear in the tool list the subagent itself reports seeing, so it could not
even attempt the calls the prompt asked it to attempt — this is a stronger result than "attempted
and rejected" (`REFUSED`): the tools are structurally absent from what the subagent can call at all,
not merely permission-gated at call time. (`--permission-mode bypassPermissions` was set on the root
session, so if Bash/Write had been *available but permission-gated* for the subagent, bypass would
have let the call through with no prompt; `UNAVAILABLE` instead of `SUCCEEDED` under bypass rules out
"the tools exist but happened to be denied.")

Filesystem ground truth, independent of the self-report, confirmed after each trial:

```
$ ls -la <write-target-path>
ls: cannot access '<write-target-path>': No such file or directory
```

The target file the subagent was asked to create was never created, in either trial. No stray
`enforcement-test-marker` output or file appeared anywhere in the scratch tree either.

**Result: 2/2 manual trials + 1/1 via the checked-in re-runnable script — Bash and Write both
`UNAVAILABLE` to the dispatched critic, corroborated by a real filesystem check showing zero side
effects.**

**PASS** — Stage 4's central premise (native `tools:` frontmatter enforcement by the host, not
documentation-only role-prose convention as under Kimi Code) holds. This is **not** falsified: the
subagent never succeeded at, and could not even attempt, either tool its frontmatter omits.

## Re-running this validation

`probe/probe_cc_agent_enforcement.sh` reproduces both probes end-to-end against a fresh scratch
plugin and fresh child processes, mirroring `probe/probe_cc_sessionstart_injection.sh`'s shape
(mktemp scratch dir, `--plugin-dir`, `--output-format text`, `timeout`-wrapped, single
`PROBE ...: FINDING=...` line, self-cleaning `trap ... EXIT`). A confirming re-run during this
validation produced:

```
PROBE cc_agent_dispatch_enforcement: FINDING=bare_name_resolves=no scoped_name_resolves=yes
bash_attempt=UNAVAILABLE write_attempt=UNAVAILABLE write_fs_side_effect=no enforcement_holds=yes --
full transcripts: <scratch>/out_bare.txt <scratch>/out_scoped.txt (removed on exit; see
references/stage4-dispatch-enforcement-live-validation.md for a preserved transcript)
```

## Conclusion

Both of Stage 4's remaining open items are resolved with direct, repeated, filesystem-corroborated
evidence:

- **Name resolution**: `Agent(subagent_type=...)` requires the plugin-scoped form for a
  plugin-supplied agent (`probe-plugin:correctness-critic`, standing in for this repo's real
  `kimi-atlas:<role>` convention already used everywhere in `agents/*.md` and both `SKILL.md`
  files). A bare role name is a hard dispatch-time `ERROR`, never a silent fallback — a factual
  correction to one line of the blueprint's own prose, recorded above, with no impact on production
  dispatch since this repo never used bare names.
- **Enforcement**: a real critic role file (`agents/correctness-critic.md`, copied verbatim, unmodified) dispatched through the genuine plugin/`Agent`-tool mechanism cannot call Bash or Write —
  both tools are absent from what the subagent can even see as callable, not merely blocked at
  call time — confirmed by the subagent's own report and independently by a filesystem check
  showing zero side effects, across 3 total trials.

With this, Stage 4's Exit criteria are now fully satisfied: Phase A's two unknowns (done
2026-08-19), zero surviving old-style built-in-type dispatch values or bootstrap phrases (done in
`6c3669b`), and the live enforcement negative-test transcribed for at least one critic role (done
here). No stop-the-stage finding was triggered.

**Not covered by this validation**: `Write`/`Edit`/`Bash` enforcement was tested for exactly one
critic role (`correctness-critic`); the other 6 role files were not independently re-probed — they
share the same frontmatter mechanism and were not expected to (and per the blueprint's own scope,
did not need to) behave differently. Only the `Agent`-tool dispatch path was tested; no other
invocation surface (e.g. a hook-triggered dispatch) was probed.
