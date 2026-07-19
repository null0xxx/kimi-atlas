# Skill registry & selection — right skill at the right time

The extracted `skills/` tree — 115 vendored official skill packages under `skills/<name>/`,
anchored by the committed sha256 manifest [`references/skills-manifest.json`](skills-manifest.json) —
is the **source of truth**. The 117 archives under `Skills/<Category>/*.zip` were the one-time
import source: `scripts/skillextract.py` unpacked them byte-identically (modes normalized:
`0o755` for `*.sh`, `0o644` otherwise) and wrote the manifest; it plays no role at runtime.
Two scripts make the tree addressable: `scripts/skillregistry.py` distils every package into
the compact, committed registry [`references/skill-registry.json`](skill-registry.json), and
`scripts/skillselect.py` ranks that registry against a task intent. The ranking is **advisory
only** (V6) — a token heuristic that emits no verdicts and no defects and can never gate a
run; the atlas flow injects it into the coder/critic packets as a hint.

**Coalesce policy.** The zips were grouped by frontmatter `name`; a same-name group had to be
**byte-identical** (same member names, same bytes) to extract at all. Two duplicate pairs
coalesced (`market-research-brief`, `okr-strategist`), so 117 zips became 115 unique packages
(a same-name group that ever differs in bytes is an audit FAILURE, never a silent pick).

## Registry schema

`scripts/skillregistry.py` reads each package's `SKILL.md` from disk and hand-parses the
top-level `key: value` frontmatter — stdlib-only, treating the content as untrusted data
(SAFE-2). A package's `category` comes from the committed manifest (a skill dir the manifest
does not record is an audit failure). The document validates against the `skill-registry` /
`skill-entry` schemas in [`references/schemas.json`](schemas.json):

```
{ "version": 2, "skill_count": 115, "skills": [ <entry>, … ] }

entry = { name, category,          # category = the package's manifest category
          description,             # frontmatter description ("" when absent)
          triggers,                # E1: explicit intent signals (see below)
          path }                   # on-disk package dir, "skills/<name>/"
```

Entries are sorted by `(category, name)` with a stable key order and no timestamps, so
rebuilding over an unchanged tree is a no-op diff.

**Trigger extraction (E1).** Descriptions phrase their intent signals as "Triggered when
users ask for X, Y …", "Trigger on requests to …", "Use when the user mentions …". The
builder lifts that fragment, splits its enumeration, strips filler prefixes and quoting, and
stores the deduplicated signal list as `triggers`. A description without trigger phrasing
yields `[]`; selection then falls back to name/description matching.

## Selection algorithm (E2)

`skillselect.select(intent_text, registry, overrides=None, top_n=3)` tokenizes both sides
with the `reqcoverage` tokenizer (identifier-aware sub-tokens, stopword floor) and scores
each skill by weighted token overlap — every matched token counted once, in its
highest-weighted field:

| field             | weight | meaning                                        |
|-------------------|--------|------------------------------------------------|
| `name`            | 3.0    | intent token appears in the skill name         |
| `triggers`        | 2.0    | intent token appears in an E1 trigger signal   |
| `description`     | 1.0    | intent token appears elsewhere in the text     |
| category prior    | +1.0   | the intent literally names the category        |

Ties break deterministically by skill name. Each result is
`{name, category, path, score, matched_tokens, why}` — `path` is the on-disk package dir
(`skills/<name>/`), `matched_tokens` lists exactly which intent tokens fired and `why` names
the fields they fired in (e.g. `"matched name[pdf] + triggers[convert]"`), so any ranking can
be explained. Only candidates with a positive score (or a pin) are returned; an empty intent
returns `[]`, and duplicate `category+name` packages collapse to one candidate.

## Manual overrides

The user steers selection by editing [`references/skill-overrides.json`](skill-overrides.json)
(validated against the `skill-overrides` schema). The file is optional — its absence means no
overrides — and malformed fields are ignored (selection must never break a run):

- **`pin`** (list) — force-include these skills at the top, in declared order.
- **`exclude`** (list) — never return these skills; wins over `pin`.
- **`boost`** (dict name→factor) — multiply the skill's score by the factor.
- **`categories`** (list) — whitelist: scored candidates are limited to these categories.
  Pinned skills are explicit intent and bypass the filter.

## Rebuild

```bash
make skill-registry                        # or: python3 scripts/skillregistry.py
python3 scripts/skillextract.py --verify   # prove the tree still matches the manifest
```

The registry builder prints an audit (E4) — per-category counts, any failures, and the
`registry-count == manifest-skill-count` check — and exits non-zero on a mismatch or a failed
package; the file is written ONLY when the registry is schema-valid AND the audit is clean, so
a partial or failed registry is never committed. `tests/test_skillregistry.py` re-validates
the committed registry against the schemas in CI (E3), and
`tests/test_skillextract.py::TestCommittedManifest` re-hashes the whole extracted tree against
the manifest — zip-free, so it runs anywhere the repo is checked out.

## Related

- [2026-07-19 — skills-era hardening analysis](../docs/superpowers/plans/2026-07-19-skills-era-hardening-analysis.md):
  the 7 residual LOW defects (D1–D7) across the registry/selector/extractor, the TOP-1
  injection dogfood approach, and the ordered fix plan.
