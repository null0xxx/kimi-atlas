# Skill registry & selection — right skill at the right time

The 117 skill archives under `Skills/<Category>/*.zip` are the **source of truth**. Two
scripts make them addressable at runtime: `scripts/skillregistry.py` distils every zip into
the compact, committed registry [`references/skill-registry.json`](skill-registry.json), and
`scripts/skillselect.py` ranks that registry against a task intent. The ranking is **advisory
only** (V6) — a token heuristic that emits no verdicts and no defects and can never gate a
run; the atlas flow injects it into the coder/critic packets as a hint.

## Registry schema

`scripts/skillregistry.py` reads each archive fully in memory (zips are **never extracted** into the
tracked tree) and hand-parses the top-level `key: value` frontmatter of its `SKILL.md` —
stdlib-only, treating the content as untrusted data (SAFE-2). The document validates against
the `skill-registry` / `skill-entry` schemas in [`references/schemas.json`](schemas.json):

```
{ "version": 1, "skill_count": 117, "skills": [ <entry>, … ] }

entry = { name, category,          # category = the zip's parent directory
          description,             # frontmatter description ("" when absent)
          triggers,                # E1: explicit intent signals (see below)
          zip }                    # archive filename (disambiguates duplicates)
```

Entries are sorted by `(category, name, zip)` with a stable key order and no timestamps, so
rebuilding over an unchanged tree is a no-op diff. Two duplicate archive pairs exist
(`market-research-brief`, `okr-strategist`); both are registered (the count check is
`registry == zips == 117`) and the selector de-duplicates them at match time.

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
`{name, category, score, matched_tokens, why}` — `matched_tokens` lists exactly which intent
tokens fired and `why` names the fields they fired in (e.g.
`"matched name[pdf] + triggers[convert]"`), so any ranking can be explained. Only candidates
with a positive score (or a pin) are returned; an empty intent returns `[]`, and duplicate
`category+name` archives collapse to one candidate.

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
make skill-registry        # or: python3 scripts/skillregistry.py
```

The builder prints an audit (E4) — per-category counts, any parse failures, and the
`registry-count == zip-count` check — and exits non-zero on a mismatch or a failed zip; the
file is written ONLY when the registry is schema-valid AND the audit is clean, so a partial
or failed registry is never committed. `tests/test_skillregistry.py` re-validates the
committed registry against the schemas in CI (E3).
