# kimi-atlas — verified, human-gated code for Kimi Code

> **Rough request in. Verified code out. Or an honest "not yet."**
>
> A many-agent orchestrator for Kimi Code that turns a loose coding request into implemented,
> reviewed, test-passing code — and never claims *done* unless a deterministic gate agrees.
> **No language model ever computes pass or fail.**

`Kimi Code plugin` · `v1.1.0 · MIT` · `115 skills built in`

---

## The problem it solves

AI coding tools are always confident. That's the problem — the same model that *writes* the code
also *grades* it, so "done" only means "the model feels good about it." kimi-atlas takes the grading
away from the model and hands it to math: the pass/fail decision is a pure function, not an opinion.

Every run ends in one of two honest verdicts:

- **✓ VERIFIED** — it passed every gate; it ships, on your say-so.
- **UNVERIFIED** — it couldn't be proven; you're told plainly, never guessed at.

---

## How one run works

A fixed state machine, not a freeform chat. Each stage has one job and the machine can't skip
ahead — so the process is inspectable and repeatable, not improvised.

| # | Stage | What happens |
|---|-------|--------------|
| 01 | **Intent** | Captures exactly what you asked and freezes it, so the goal can't drift mid-run. |
| 02 | **Ground** | A read-only scout maps the relevant parts of your repo before a line is touched. |
| 03 | **Code** | A coder agent writes the change in an **isolated worktree** — never your real files. |
| 04 | **Verify** | The 6-lens harness scores the result against the frozen intent. |
| 05 | **Gate** | You see the verdict and the diff. Nothing lands on your tree without your word. |

If a check fails, atlas **refines and re-verifies** — a bounded number of times — then stops and
reports honestly rather than pretending.

---

## An orchestra, not a soloist

This is the "many-agent" part, and it's the reason the verdict can be trusted. kimi-atlas is an
**orchestrator**: a root conductor that never writes code itself. It dispatches specialized
subagents — each in its own **fresh context**, each with one job — and collects what they return:

- a **scout** that surveys the repo, read-only, before anything is changed;
- a **coder** that implements the change in the isolated worktree;
- independent **critics** for correctness, code quality, and security — each judging in isolation,
  none seeing the others' verdicts;
- for split work, an **integration critic** that inspects the seams where parallel changes meet.

The conductor owns the state machine, hands each agent exactly the context it needs (nothing more),
feeds their results through the deterministic gates, and runs the human gate at the end. Because
every agent starts fresh and returns a **structured result**, nothing accumulates into one giant
drifting context.

Why it matters: **separation of powers.** The agent that *writes* the code is never the agent that
*judges* it, and the judges don't collude. That independence — not a bigger model — is what makes
the verdict worth trusting.

---

## The verdict: six falsifiable questions

Every change is judged on the same six lenses. Three are argued by independent AI critics; three are
settled by deterministic checks — the **floor** — that a model can't talk its way past.

| Lens | The question | Decided by |
|------|--------------|------------|
| **Does it run?** | The program parses, compiles, and executes — proven, not assumed. | deterministic floor |
| **Is it correct?** | The change does what the frozen intent asked — no more, no less. | AI critic |
| **Is it good code?** | Readable, non-duplicated, free of dead ends and lazy shortcuts. | AI critic |
| **Is it secure?** | Static analysis scans for real vulnerabilities before anything reaches you. | deterministic floor |
| **Is it tested?** | The tests exist, actually run, and actually assert something meaningful. | AI critic |
| **Does it cover the ask?** | Every requirement you stated maps to something the change delivers. | deterministic floor |

The step that merges these into a single **pass or fail is a pure function** — the same inputs always
produce the same verdict. That is the whole promise: verification is arithmetic, not an opinion the
model can be flattered into.

---

## Every run writes itself down

A run is not throwaway chat — it is recorded, on disk, as structured JSON under a per-run folder
(`.atlas/<run>/`). These files are not debris; they are what makes the guarantees possible.

| File | What it holds |
|------|---------------|
| `intent.txt` | The frozen, immutable goal — written once, never edited, so nothing drifts from what you asked. |
| `log.jsonl` | An **append-only ledger** of every stage, refine pass, and decision — never rewritten. |
| `hooks.jsonl` | An event log of the tools each agent used and the errors it hit. |
| `context-graph.json` | A live, queryable map of the run — the task hierarchy, tools, and errors — rebuilt from the ledger so it can never drift out of sync. |
| `plan.dag.json` | For split work: the file-disjoint plan — its nodes, dependencies, and budget. |
| `critic_*.json` | Each lens's verdict, persisted as evidence behind the pass/fail. |

**What all that detail buys you:**

- **Resumable** — if a run is killed, times out, or your session is compacted, it picks up *exactly*
  where it stopped (`/atlas-resume`). The ledger is the recovery map — no lost work, no restart.
- **Auditable** — you can see *why* any verdict happened. Every stage, tool call, and critic result
  is on the record; it is a paper trail, not a black box.
- **Deterministic** — the pure gates recompute the verdict *from these records*, so there is no
  hidden state. The same records always produce the same answer, and you can re-derive it yourself.
- **Safe** — the ledger is append-only and the progress counter is provable, so a run cannot silently
  rewrite its own history, fabricate a pass, or loop forever.

---

## What's inside — four capabilities

- **atlas** — the single-change core. One request, driven end-to-end through the pipeline above and
  its 6-lens gate. This is the engine everything else builds on.
- **ATLAS-WEAVE** — for larger changes. Splits the work into a file-disjoint plan, runs the pieces in
  parallel, and merges them through a combined-tree gate — falling back to a single atlas run when
  the work doesn't split.
- **115 skill packages** — a built-in library of official Kimi skills (spreadsheets, email, scraping,
  and more) that atlas selects automatically for your task, or that you can invoke on their own.
- **The agentic backbone** — run-state awareness: a live map of the run (a *ContextGraph*), an
  explicit state machine, and safe forward-only rollback confined to the isolated worktree — so long
  runs stay reliable and recoverable.

---

## Why it's different — guarantees, not vibes

| | | |
|---|---|---|
| **Pure gate** | The model never grades its own work | Pass/fail is a deterministic function. A model can propose a fix; it cannot vote itself a passing grade. |
| **Human-gated** | Nothing touches your tree without you | All work happens in an isolated worktree. You review the verdict and the diff, then keep, revert, or discard. No silent auto-apply. |
| **Self-proven** | Built and verified by its own harness | The plugin's own skills were implemented and checked by the same 6-lens gate it ships — which caught real defects before merge. Its full test suite is green on every commit. |
| **Deterministic** | Same inputs, same verdict — every time | The decision cores are pure, standard-library-only, and carry no hidden state. Reruns don't drift, and the reasoning behind a verdict is inspectable. |

---

## Get started

Inside Kimi Code — no clone, no build. It fetches the latest release, registers natively, and shows
the standard third-party trust prompt.

```text
/plugins install https://github.com/null0xxx/kimi-atlas
/plugins reload
```

Then start a run: `/atlas` · `/atlas-weave` · `/atlas-resume`.

`v1.1.0 · latest` · `MIT licensed` · `stdlib-only Python 3.12` · runs inside Kimi Code.

---

## Honest scope

kimi-atlas is for real implementation work you want verified — not throwaway snippets, and not a
standalone IDE. It lives inside Kimi Code. When it genuinely can't verify a change, it labels the
result `UNVERIFIED` instead of guessing. **That restraint is the feature.**

---

*See also: [`README.md`](../README.md) for the full technical documentation ·
[`CHANGELOG.md`](../CHANGELOG.md) for release history ·
[`references/rubric.md`](../references/rubric.md) for the six lenses and the exact PASS bar.*
