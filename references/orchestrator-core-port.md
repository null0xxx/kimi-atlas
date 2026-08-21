# Orchestrator core port — decision record (Stage 03)

Named as a Stage 03 deliverable in
[`docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`](../docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md)
("the decision record Stage 4 reads rather than re-deriving these facts"), but never created during
Stage 03 itself. Written 2026-08-21 to close that gap
(`references/full-blueprint-audit-2026-08-21.md`, item G9), with every fact below independently
re-derived from the current tree rather than copied from the blueprint's own prose.

## 1. The `PYTHONPATH=$CLAUDE_PLUGIN_ROOT PYTHONSAFEPATH=1` invocation convention

Confirmed, session-wide: the Claude Code **SessionStart** hook (`hooks/init-env.sh`) exports both
`PYTHONPATH` (extended with `$CLAUDE_PLUGIN_ROOT`) and `PYTHONSAFEPATH=1` once, before this skill
ever runs, for the rest of the session — see `tests/test_syspath_isolation.py`'s
`TestSessionWideIsolationReplacesThePerInvocationPrefix` class. The literal env var names are
`CLAUDE_PLUGIN_ROOT` (Claude Code's own plugin-root variable) and `PYTHONSAFEPATH` (CPython 3.11+;
strips the untrusted target repo's cwd from `sys.path` so it cannot shadow atlas's own modules,
including the FROZEN `verdict.py` gate).

### Which of the 12 backbone modules actually depend on this convention

Stage 03's own "Files affected" list plus the file G10 (this same audit round) established was the
unnamed 12th ("`runcheck.py` also changed") gives 12 backbone modules: `fsm.py`, `verdict.py`,
`budget.py`, `leaseclock.py`, `plandag.py`, `scheduler.py`, `resume.py`, `ctxevents.py`,
`ctxstore.py`, `contextgraph.py`, `rollback_driver.py`, `runcheck.py`.

Checked directly (`rg -n "sys.path|parents\[" scripts/<module>.py` for each), not assumed:

- **9 modules import bare `from scripts import <mod>` with no shim of their own** — they are
  unconditionally dependent on the SessionStart-hook convention above: `fsm.py`, `verdict.py`,
  `budget.py`, `leaseclock.py`, `plandag.py`, `scheduler.py`, `resume.py`, `ctxstore.py`,
  `runcheck.py`.
- **3 modules carry their own self-shim** — `_ROOT = pathlib.Path(__file__).resolve().parents[1]`
  then `sys.path.insert(0, str(_ROOT))` before their own `from scripts import ...` — and so work
  standalone even if run directly, without `PYTHONPATH` set at all: `contextgraph.py`,
  `rollback_driver.py`, **and `ctxevents.py`**.

**Correction against this same session's own working assumption going in:** the task that produced
this document expected only `contextgraph.py`/`rollback_driver.py` to self-shim (an "8
non-self-shimming" split). Direct inspection found `ctxevents.py` carries the identical shim
(`scripts/ctxevents.py:18-20`) — it was missed by that recollection. The accurate, re-derived split
is **9 non-self-shimming / 3 self-shimming**, not 8/2. This note exists so a future reader trusts
the grep above, not either party's memory of it — exactly the standard this whole audit round
applied to the blueprint itself.

## 2. `run_id` source: self-generated vs. session-sourced

**Decided: session-sourced, `$ATLAS_SESSION_ID`.** Not the blueprint's originally-specified
self-generated `$ATLAS_RUN_ID` (UUID4 per run). Source of truth for *why* this is a decided fact and
not merely an as-shipped default: the blueprint's own "Divergence: run_id source" section
(§ near line 500 as of this writing) now carries a dated record —

> **2026-08-21 — dated decision record.** This exact question — keep the already-implemented,
> session-sourced `$ATLAS_SESSION_ID`, or switch to this blueprint's originally-specified
> self-generated `$ATLAS_RUN_ID` (UUID4 per run) — was put to the user explicitly, via a structured
> yes/no question, during the 2026-08-21 session that produced the full-blueprint audit. The user
> explicitly chose to keep `$ATLAS_SESSION_ID`.

This is added there (and cited here, not restated as a second independent claim) specifically
because audit item C5 found the *prior* framing ("kept... by explicit user decision") had no
traceable primary source in the repository — the exchange lived only in that session's live
conversation. This document and the blueprint's own Divergence section are now that record.
Mechanically: `hooks/init-env.sh` persists Claude Code's own SessionStart `session_id` field as
`$ATLAS_SESSION_ID`; `contextgraph.graph_lookup(".atlas", "$ATLAS_SESSION_ID")` and every
`ctxstore.advance(...)` call site key off it the same way `$KIMI_SESSION_ID` did pre-migration —
same collision shape (H5), deliberately not re-opened by this decision (see
`tests/test_v1521_regressions.py`'s H5 skip, left byte-identical by this same audit round).

## 3. `runcheck.py`'s Bash-sandboxing memory-cap probe — still open

Stage 03's own action items included: "Probe `runcheck.py`'s memory-cap backend resolution under
Claude Code's optional Bash sandboxing, on and off — no code change needed either way." This was
**never attempted** (blueprint audit item G12, out of scope for this pass per the task that produced
this document — it is one of the live-probe items explicitly deferred to a later phase, alongside
G3/G11/G14/G15/G20/G40/G37/G39). Flagged here rather than silently omitted: no probe script, no
reference doc, no test, and no commit message addresses it as of 2026-08-21. `runcheck.py`'s
memory-cap backend selection (`systemd-run --user --scope` MemoryMax RSS cap, preferred over the
legacy `ulimit -v`) remains unverified specifically under Claude Code's Bash sandboxing, on either
setting.
