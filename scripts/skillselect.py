"""Advisory skill selector — ranks the committed skill registry for a task intent.

Reads ``references/skill-registry.json`` (built by ``scripts/skillregistry.py``
from the bundled ``Skills/`` zips) and scores every skill against a free-text task
intent, so an agent can be handed the *right skill at the right time*. The ranking
is **advisory only** (V6): it is a string/token heuristic, emits no verdicts and
no defects, and can never gate a run — the atlas flow treats it as a hint injected
into the coder/critic packets.

Scoring (E2) is weighted and explainable: a token matched in the skill **name**
outweighs one matched in its **trigger signals** (E1, see ``extract_triggers``
in ``scripts/skillregistry.py``), which outweighs one matched in the
**description**; a small **category prior** applies when the intent literally
names a category ("finance", "marketing", …). Each matched token is counted once,
in its highest-weighted field. Ties break deterministically by skill name, and
every result carries ``matched_tokens`` plus a ``why`` string naming the fields
that fired, so a ranking can always be explained.

Manual overrides (``references/skill-overrides.json``, optional) steer the
ranking without rebuilding the registry:

- ``pin`` (list[str]) — force-include these skills at the top, in declared order.
- ``exclude`` (list[str]) — never return these skills; wins over ``pin``.
- ``boost`` (dict[str, float]) — multiply a skill's score by the given factor
  (``0`` zeroes the score: the skill drops out of the selection unless pinned).
- ``categories`` (list[str]) — whitelist: scored candidates are limited to these
  categories (pinned skills are explicit intent and bypass the filter).

The tokenizer is imported from ``scripts/reqcoverage.py`` (identifier-aware
sub-token splitting, the same stopword floor) so intent tokens and registry
tokens are computed the same way on both sides of the match.

:func:`select` is pure; :func:`load_registry` / :func:`load_overrides` and
:func:`main` are the thin I/O hand.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# When run directly as ``python3 scripts/skillselect.py`` the interpreter puts
# ``scripts/`` (not the repo root) on ``sys.path[0]``, so ``from scripts import ...``
# would fail. Put the plugin root on the path so the package imports resolve both when
# run directly and when imported as ``scripts.skillselect`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.reqcoverage import STOPWORDS, tokenize  # noqa: E402  (path shim precedes this)

# The registry/overrides live at <plugin-root>/references; this script lives at
# <plugin-root>/scripts/skillselect.py, so parents[1] is the plugin root
# (same resolution idiom as scripts/validate.py).
_DEFAULT_REGISTRY = _ROOT / "references" / "skill-registry.json"
_DEFAULT_OVERRIDES = _ROOT / "references" / "skill-overrides.json"

# Scoring weights (E2): name > triggers > description, plus a small category
# prior when the intent text literally names the category.
NAME_WEIGHT = 3.0
TRIGGER_WEIGHT = 2.0
DESCRIPTION_WEIGHT = 1.0
CATEGORY_PRIOR = 1.0


def _str_list(value) -> list[str]:
    """Coerce an overrides field to a list of strings ([] when malformed)."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _score_entry(entry: dict, intent_tokens: set[str]) -> dict:
    """Score one registry entry against the intent (E2 weighted, explainable).

    Each matched intent token is counted once, in its highest-weighted field:
    name first, then triggers, then description. The category prior fires only
    when a whole intent token names the entry's category ("refinance" does
    NOT name Finance — substring containment is not a match).
    """
    name_hits = intent_tokens & tokenize(entry.get("name", ""))
    trigger_hits = (intent_tokens - name_hits) & tokenize(" ".join(entry.get("triggers", [])))
    description_hits = (intent_tokens - name_hits - trigger_hits) & tokenize(
        entry.get("description", "")
    )
    score = (
        NAME_WEIGHT * len(name_hits)
        + TRIGGER_WEIGHT * len(trigger_hits)
        + DESCRIPTION_WEIGHT * len(description_hits)
    )
    why_parts: list[str] = []
    for field, hits in (
        ("name", name_hits),
        ("triggers", trigger_hits),
        ("description", description_hits),
    ):
        if hits:
            why_parts.append(f"{field}[{', '.join(sorted(hits))}]")
    category = entry.get("category", "")
    if category and category.lower() in intent_tokens:
        score += CATEGORY_PRIOR
        why_parts.append(f"category-prior[{category}]")
    matched = sorted(name_hits | trigger_hits | description_hits)
    return {
        "entry": entry,
        "score": score,
        "matched_tokens": matched,
        "why": "matched " + " + ".join(why_parts) if why_parts else "no token overlap",
    }


def select(
    intent_text: str,
    registry: dict,
    overrides: dict | None = None,
    top_n: int = 3,
) -> list[dict]:
    """Rank registry skills for ``intent_text`` (advisory only — V6).

    Args:
        intent_text: the free-text task intent.
        registry: a ``skill-registry`` document (``{"skills": [...]}``).
        overrides: optional ``skill-overrides`` document (pin/exclude/boost/
            categories); ``None`` — or any non-dict value — means no overrides.
            Malformed override fields are ignored (selection must never break
            a run).
        top_n: maximum number of results; ``<= 0`` returns ``[]``.

    Returns:
        At most ``top_n`` dicts ``{name, category, score, matched_tokens, why}``:
        pinned skills first in declared order, then the remaining candidates by
        descending score with a deterministic name tie-break. Only candidates
        with a positive score (or a pin) are returned, so an empty intent yields
        ``[]``. Duplicate archives (same category+name) are de-duplicated;
        same-name skills in different categories are distinct candidates that
        rank independently (pin/exclude/boost match on the bare name and apply
        to every entry carrying it).
    """
    if top_n <= 0:
        return []
    overrides = overrides if isinstance(overrides, dict) else {}
    # A skill pinned twice is force-included once, in declared order.
    pinned = list(dict.fromkeys(_str_list(overrides.get("pin"))))
    excluded = set(_str_list(overrides.get("exclude")))
    raw_boost = overrides.get("boost")
    boost = raw_boost if isinstance(raw_boost, dict) else {}
    categories = set(_str_list(overrides.get("categories")))

    intent_tokens = tokenize(intent_text) - STOPWORDS

    skills = registry.get("skills") if isinstance(registry, dict) else None
    entries = skills if isinstance(skills, list) else []

    # De-duplicate by (category, name): identically-named duplicate archives
    # classify identically; the first (sorted) occurrence wins.
    seen: set[tuple[str, str]] = set()
    candidates: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = (entry.get("category", ""), entry.get("name", ""))
        if key in seen or key[1] in excluded:
            continue
        seen.add(key)
        candidates.append(entry)

    # Keyed by (category, name): same-name skills in different categories are
    # distinct candidates and rank independently; a boost matches on the bare
    # name and applies to every entry carrying it.
    scored: dict[tuple[str, str], dict] = {}
    for entry in candidates:
        result = _score_entry(entry, intent_tokens)
        name = entry.get("name", "")
        factor = boost.get(name)
        if isinstance(factor, (int, float)) and not isinstance(factor, bool) and factor >= 0:
            if factor != 1:
                result["score"] *= factor
                result["why"] += f" + boost[x{factor}]"
        scored[(entry.get("category", ""), name)] = result

    def _public(result: dict, pinned_note: bool = False) -> dict:
        why = result["why"]
        if pinned_note:
            why = "pinned (manual override)" + ("" if why == "no token overlap" else "; " + why)
        return {
            "name": result["entry"].get("name", ""),
            "category": result["entry"].get("category", ""),
            "score": round(result["score"], 4),
            "matched_tokens": result["matched_tokens"],
            "why": why,
        }

    results: list[dict] = []
    for name in pinned:  # force-include at the top, in declared order
        if name in excluded:
            continue
        for key, result in scored.items():  # a pin matches every entry with that name
            if key[1] == name:
                results.append(_public(result, pinned_note=True))
                if len(results) >= top_n:
                    return results

    pin_set = set(pinned)
    ranked = sorted(
        (r for key, r in scored.items() if key[1] not in pin_set and r["score"] > 0),
        key=lambda r: (-r["score"], r["entry"].get("name", "")),
    )
    if categories:  # whitelist applies to scored candidates, never to pins
        ranked = [r for r in ranked if r["entry"].get("category", "") in categories]
    for result in ranked:
        if len(results) >= top_n:
            break
        results.append(_public(result))
    return results


def load_registry(path: pathlib.Path | None = None) -> dict:
    """Load a registry document (default: the committed one); raises on failure."""
    registry_path = path or _DEFAULT_REGISTRY
    return json.loads(registry_path.read_text(encoding="utf-8"))


def load_overrides(path: pathlib.Path | None = None) -> dict | None:
    """Load an overrides document; ``None`` when the file is absent (tolerated)."""
    overrides_path = path or _DEFAULT_OVERRIDES
    if not overrides_path.is_file():
        return None
    return json.loads(overrides_path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    """CLI: rank skills for an intent; write the ranked JSON list to stdout."""
    parser = argparse.ArgumentParser(
        description="Rank bundled skills for a task intent (advisory — V6)."
    )
    parser.add_argument("intent", help="Free-text task intent to match skills against.")
    parser.add_argument(
        "--registry",
        type=pathlib.Path,
        default=None,
        help="Registry path (default: <plugin-root>/references/skill-registry.json).",
    )
    parser.add_argument(
        "--overrides",
        type=pathlib.Path,
        default=None,
        help="Overrides path (default: <plugin-root>/references/skill-overrides.json; "
        "absent file is tolerated).",
    )
    parser.add_argument("--top-n", type=int, default=3, help="Max results (default: 3).")
    args = parser.parse_args(argv)

    try:
        registry = load_registry(args.registry)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"skillselect: cannot load registry: {exc}\n")
        return 1
    try:
        overrides = load_overrides(args.overrides)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"skillselect: cannot parse overrides: {exc}\n")
        return 1

    ranked = select(args.intent, registry, overrides, top_n=args.top_n)
    sys.stdout.write(json.dumps(ranked, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
