# AGENTS.md — kimi-atlas project memory

Read this first in any session touching this repo. It is the durable, fact-checked map of
what exists, how to verify it, and what is still open. For depth, follow the links to
[`references/`](references/) — especially [`references/architecture.md`](references/architecture.md),
[`references/atlas-weave.md`](references/atlas-weave.md), [`references/rubric.md`](references/rubric.md),
[`references/skill-registry.md`](references/skill-registry.md), and the plan docs under
[`docs/superpowers/plans/`](docs/superpowers/plans/).

## What this is

**kimi-atlas** — a many-agent, quality-calibrated orchestrator plugin for Kimi Code with **115
vendored official skill packages** built in. Public repo: <https://github.com/null0xxx/kimi-atlas>
(v1.3.0, MIT). Install: `/plugins install https://github.com/null0xxx/kimi-atlas` (managed copy at
`~/.kimi-code/plugins/managed/kimi-atlas`); from source: `./scripts/install.sh`
(installs to `~/.kimi-code/plugins/kimi-atlas`).

Four layers, all first-party:

- **atlas** (`skills/atlas/SKILL.md`) — single-change core: deterministic
  `INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT`
  state machine; 6-lens verification harness (deterministic `runcheck`/`lint`/`reqcoverage`/
  `pathcheck`/`astlens` floor + 3 isolated adversarial critics); **no LLM ever computes pass/fail**
  (`verdict.merge`/`gate` are pure). Never auto-applies; human gates only.
- **ATLAS-WEAVE** (`skills/atlas-weave/SKILL.md`) — multi-agent meta-machine: file-disjoint
  plan-DAG, ≤3 concurrent inner atlas runs, combined-tree differential integration.
- **The agentic backbone (Graph + Loop + Verification)** — wraps the pure core, never replaces it
  (merged `da90f6c`, 6-lens-hardened `27→0`): **ContextGraph** (`scripts/contextgraph.py`) — pure
  read-time projection over the ledger + `hooks.jsonl`, injected as SAFE-2 DATA into the CODED coder
  packet (recomputed each REFINE; a hint, never a gate); **`scripts/ctxevents.py`** records
  tool_call/error events to `hooks.jsonl` (never `log.jsonl`); **`scripts/fsm.py`** — `legal_transition`
  derived from `ctxstore.STAGES` + one declared `REFINE→CODED` edge; **`scripts/rollback_driver.py`** —
  two-phase forward-only rollback (pure `sanctioned_rollback` + monkeypatchable git seam, worktree-only,
  append-only ledger); **`scripts/safewrap.py`** — the single canonical SAFE-2 wrapper; **`scripts/astlens.py`**
  — `ast` syntax/lint lens folded into VERIFIED; **`scripts/rubric.py`**/**`scripts/frontmatter.py`** —
  single-source rubric vocab / shared BOM+CRLF frontmatter primitive.
- **The skill system** — 115 vendored skill packages + registry/selector (below).

## Commands (the daily five)

```bash
make ci               # THE gate: strict naming + unit tests + inventory-drift + shell syntax
make test             # the full unit-test suite (python3 -m unittest discover -s tests -v)
make skill-registry   # rebuild references/skill-registry.json from the extracted skills/ tree
make skills-extract   # re-extract vendored packages + --verify against the sha256 manifest
make negative-gate    # red-team fixtures: good→OK, each bad_*→UNVERIFIED
```

`make ci` mirrors `.github/workflows/check.yml` (Python 3.12). Everything must stay green.

## Non-negotiable conventions (any edit must match)

- **Python:** stdlib-only 3.12, `from __future__ import annotations`, pure cores + thin I/O
  "hands", long module docstrings citing invariants, CLI = `main(argv=None) -> int` +
  `sys.exit(main())`, plugin root via `pathlib.Path(__file__).resolve().parents[1]` + sys.path shim.
- **Output idiom:** `sys.stdout.write` / `sys.stderr.write` in the `skill*` modules — the atlas
  harness lints changed files for `print(` as a debug token (repo's older CLIs use `print()`).
- **Tests:** stdlib `unittest` only, `tests/test_<module>.py` per `scripts/<module>.py`,
  tempfile fixture trees, in-process `main()` via `redirect_stdout/stderr`, behavior AND
  failure-path assertions; `TestMainRealRepo`/`TestCommitted*` classes pin the real tree.
- **Doc gates:** new `.md` = lowercase kebab-case (exempt basenames: `README.md`, `SKILL.md`,
  `LICENSE`, `Makefile`, `PLAN.md`, `AGENTS.md`) AND individually markdown-linked from
  `references/*.md` or `README.md` (a directory link does not count). A `skills/` dir containing
  `SKILL.md` is a self-contained vendored package — exempt via `scripts/skillpkgs.walk_markdown`.
- **Backticked path citations** in changed text must exist on disk (harness `pathcheck` scans
  `-`/`+`/context diff lines); use the `.atlas/<run_id>/…` placeholder form for run artifacts.
- **Determinism:** generated artifacts are sorted, stable-keyed, timestamp-free; writers follow
  validate→audit→write and never persist partial state.

## The skill system (v2, manifest-anchored)

- `skills/<name>/` — 115 vendored official packages (712 files, byte-identical to their source
  zips; 2 duplicate zips coalesced 117→115) + 3 first-party orchestrator skills. Platform-
  registered via `.kimi-plugin/plugin.json` (`"skills": "./skills/"`).
- `references/skills-manifest.json` — sha256 anchor for every vendored file;
  `python3 scripts/skillextract.py --verify` + `TestCommittedManifest` re-prove it zip-free in CI.
- `references/skill-registry.json` — v2 registry (115 entries `{name, category, description,
  triggers, path}`), built from the tree by `scripts/skillregistry.py` (audit-gated).
- `scripts/skillselect.py` — weighted explainable ranking (name 3.0 > triggers 2.0 >
  description 1.0 + word-boundary category prior); advisory only (V6). User overrides:
  `references/skill-overrides.json` (`pin`/`exclude`/`boost`/`categories`).
- Atlas wiring: GROUNDED persists the top-3 to `.atlas/<run_id>/skills.json` (with `path`); the
  TOP-1 skill's full `SKILL.md` body is injected into the elite-coder packet as the ACTIVE skill
  (SAFE-2 untrusted framing); remaining top-3 advisory. Production-proven in run-3 (dogfood).
- The 41MB `Skills/` zips are the local import archive — gitignored, NOT in the repo.

## Atlas-run workflow (how work happens here)

- A change = one uninterrupted atlas run by the root orchestrator (this assistant) following
  `skills/atlas/SKILL.md` exactly; durable state lives in `.atlas/<run_id>/` (gitignored) —
  resume reads the newest non-terminal ledger, never memory.
- Subagent dispatch: role file under `agents/<role>.md` → strip frontmatter → prepend body →
  `Agent(subagent_type=...)` (context-scout→explore, elite-coder→coder, critics→plan).
  Read-only subagents RETURN JSON; the root persists via `ctxstore`.
- Scripts run via `PYTHONPATH=<plugin-root> python3 -c "from scripts import <mod>"`.
- Refine loop: any CRITICAL/HIGH defect, or any CORRECTNESS/SECURITY defect at any severity,
  forces a pass; hard cap `MAX_PASSES=2`.
- Agentic backbone wiring: at CODED the SAFE-2-wrapped `contextgraph.graph_lookup(".atlas",
  "${KIMI_SESSION_ID}")` is injected into the elite-coder packet as architectural-state DATA
  (recomputed on every REFINE; a hint, never a gate). `fsm.legal_transition` is a test + negative-gate
  invariant — `advance()` stays a permissive recorder. Rollback: a headless hard-fail calls
  `rollback_driver.run_rollback` (worktree-only, gated by `sanctioned_rollback`); interactive runs
  surface the residual for human revert/keep/discard at OUTPUT. Events → `hooks.jsonl` (via
  `hooks/telemetry.sh` + `scripts/ctxevents.py`), never `log.jsonl`.

## Open items (as of v1.3.0)

- **D1–D7 fix run** — ordered + risk-assessed in
  [`docs/superpowers/plans/2026-07-19-skills-era-hardening-analysis.md`](docs/superpowers/plans/2026-07-19-skills-era-hardening-analysis.md):
  atomic registry write, `_MIN_SIGNAL_LEN`, `load_overrides` boundary, `_is_safe_entry` `.`
  rejection, sibling `audit()` arg order, test scaffold hoist, dead test param.
- **Pending decisions:** coverage.py (stdlib-only by design vs dev-only venv), `hotfiles.sh`
  SIGPIPE exit-141 upstream fix (vendored script — patch upstream, NOT locally: the manifest
  anchors vendored bytes), 73MB `skills/xlsx/scripts/Xlsx` (kept; LFS would break the manifest
  re-hash), `scripts/suiterun.py:88` `shell=True` (named trusted boundary — operator-supplied
  verify_cmd only, degrades to `{}`).
- **Never do:** edit vendored `skills/<name>/` content directly (re-extract instead); commit
  `.atlas/` or `Skills/`; weaken the doc gates for first-party docs.

## Status

unit-test suite green (`make test`) · `make ci` clean · 29 tracked docs, no inventory drift · v1.3.0 released (P2 syntax floor merged: `nativefloor`/`syntaxlens` Lens 5c — Ruby/PHP/Go/shell syntax + JSON/TOML config; JS syntax-check dropped)
(tag + GitHub Release) · registry v2 (115 skills) · TOP-1 injection production-proven · **agentic
backbone shipped & merged (`da90f6c`, pushed to origin): ContextGraph live at CODED, explicit
`fsm`/two-phase rollback, `astlens` lens; 6-lens-hardened `27→0`; graphify audit F1–F11 all fixed;
deep whole-system 6-lens (`51f652f`) fixed atlas-weave apply-failures + 4 more, adversary-verified.**
Design + build record: `docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md`,
`docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md`; whole-system map:
`references/system-map.md`. Remaining opportunities (not defects): deeper ContextGraph consumption
(critic packets, orchestrator `ctxevents`), the real `rollback_driver` git seam is monkeypatch-tested.
