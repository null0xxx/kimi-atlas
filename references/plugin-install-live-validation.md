# Live validation — installing kimi-atlas from GitHub into Claude Code

Closes the one live-measurement claim in this repository that had no committed evidence behind it.
`AGENTS.md:17-30` has asserted since 2026-08-24 that the marketplace install works; the 2026-08-21
audit's section-G re-derivation flagged it as **the only such claim with no
`references/*live-validation.md` file**, while `README.md` simultaneously stated that a persistent
marketplace-install path "does **not** exist yet". This settles it by measurement.

**Date:** 2026-08-27 · **CLI:** Claude Code 2.1.246 · **Repo HEAD at measurement:** `314fa9b`

## Why it could not have worked before today

`.claude-plugin/marketplace.json` was committed in `df6430e` but **that commit sat unpushed**. Until
this session's push, the manifest did not exist on GitHub, so `claude plugin marketplace add
null0xxx/kimi-atlas` could not have succeeded for anyone. The local install that did work was
registered as `Source: Directory (/home/utruta/kimi-atlas)` — a clone path, not the repository.

## Method — isolated, so the live environment was never mutated

The developer machine already had `kimi-atlas` registered from a local directory. Rather than
disturb it, every command below ran under a throwaway `CLAUDE_CONFIG_DIR`. Isolation was verified
first, read-only: the isolated config reported `No marketplaces configured` while the real one still
listed `kimi-atlas`. Nothing outside the temporary directory was written, and it was removed
afterwards.

## Result — both steps succeeded from a clean config

    $ claude plugin marketplace add null0xxx/kimi-atlas
    SSH not configured, cloning via HTTPS: https://github.com/null0xxx/kimi-atlas.git
    Refreshing marketplace cache (timeout: 120s)…
    Clone complete, validating marketplace…
    ✔ Successfully added marketplace: kimi-atlas (declared in user settings)     rc=0

    $ claude plugin marketplace list
      ❯ kimi-atlas
        Source: GitHub (null0xxx/kimi-atlas)          <-- NOT a local directory

    $ claude plugin install kimi-atlas@kimi-atlas
    ✔ Successfully installed plugin: kimi-atlas@kimi-atlas (scope: user)         rc=0

    $ claude plugin list
      ❯ kimi-atlas@kimi-atlas    Version: 1.5.3.1    Scope: user    Status: ✔ enabled

## What was installed

`claude plugin details kimi-atlas` reports **Skills (118) · Agents (7) · Hooks (5) · MCP servers (0)
· LSP servers (0)**, hooks marked *harness-only — no model context cost*.

Verified against the repository at the same HEAD:

| | installed copy | repo |
|---|---|---|
| top-level `skills/*/SKILL.md` | 118 | 118 |
| `agents/*.md` | 7 | 7 |
| `hooks/*.sh` | 4 | 4 |
| `plugin.json` version | 1.5.3.1 | 1.5.3.1 |
| `hooks/init-env.sh` | **byte-identical to repo HEAD** | — |

That last row matters: the freshly-pushed hook hardening is what a new user actually receives.

**Reconciling 118 against 155.** A recursive `find skills -name SKILL.md` returns 155. The CLI counts
118 because that is the number of top-level packages (`skills/*/SKILL.md`); the remaining 37 are
nested inside packages. Both numbers are correct for what they count, and the same 118/155 split
holds in the repo.

## One number that did NOT reproduce

`AGENTS.md:25` claims **~16.6k always-on tokens per session**. This run measured **~11,713**. The
claim was recorded against CLI 2.1.241 and this measurement is on 2.1.246, so token accounting may
simply have changed between them. Recorded as a discrepancy to reconcile, **not** as a refutation —
nothing here establishes which number was right for which build.

## What this does and does not establish

**Established:** a user with no prior setup can add this repository as a marketplace from GitHub and
install the plugin, and what lands matches the repository at that HEAD.

**Not established:** that `skills/` auto-discovery lists or auto-triggers the 115 vendored packages
the way it does the three first-party orchestrator skills (the open `G20` question); that the
install works on a non-Linux host; or the always-on token figure above.

**Consequence for the blueprint.** `docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`
§14 lists "a persistent marketplace-install path" among its **explicit non-requirements**. That
exclusion is why the acceptance criteria never measured the thing most people would call the point of
the migration. The path now demonstrably works; whether §14 should be amended to require it is a
decision for the blueprint's owner, recorded here rather than taken.
