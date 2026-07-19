"""Unit tests for scripts/skillselect.py (advisory skill selector — V6).

Fixtures are synthetic registry documents built inline — the tests never depend
on the real Skills/ tree or the committed registry. Covers the E2 weighted
ranking, matched_tokens explainability, every override semantic (pin / exclude /
boost / categories), and the CLI failure paths.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from scripts import skillselect


def _entry(name, category, description, triggers=None):
    return {
        "name": name,
        "category": category,
        "description": description,
        "triggers": triggers or [],
        "zip": name + ".zip",
    }


def _registry(*entries):
    return {"version": 1, "skill_count": len(entries), "skills": list(entries)}


REGISTRY = _registry(
    _entry("pdf-toolkit", "Productivity", "Merge and split PDF files.",
           ["merge pdf", "split pdf"]),
    _entry("doc-converter", "Productivity", "Convert documents, including pdf conversion."),
    _entry("finance-report", "Finance", "Build dashboards for portfolios.",
           ["portfolio dashboard"]),
    _entry("ops-console", "Engineering", "Operations dashboard for on-call views."),
    _entry("chart-image", "Engineering", "Render charts as images.", ["render chart"]),
)


def _names(results):
    return [r["name"] for r in results]


class TestWeightedRanking(unittest.TestCase):
    def test_name_match_outranks_description_match(self):
        results = skillselect.select("pdf", REGISTRY)
        # "pdf" hits the NAME of pdf-toolkit (3.0) but only the DESCRIPTION of
        # doc-converter (1.0) — name weight must win.
        self.assertEqual(_names(results), ["pdf-toolkit", "doc-converter"])
        self.assertEqual(results[0]["score"], 3.0)
        self.assertEqual(results[1]["score"], 1.0)

    def test_trigger_match_outranks_description_match(self):
        results = skillselect.select("dashboard", REGISTRY)
        # "dashboard" hits TRIGGERS of finance-report (2.0) vs only the
        # DESCRIPTION of ops-console (1.0).
        self.assertEqual(_names(results), ["finance-report", "ops-console"])
        self.assertEqual(results[0]["score"], 2.0)
        self.assertEqual(results[1]["score"], 1.0)

    def test_category_prior_applies_when_intent_names_category(self):
        results = skillselect.select("finance numbers", REGISTRY)
        top = results[0]
        self.assertEqual(top["name"], "finance-report")
        # name hit on "finance" (3.0) + category prior (1.0).
        self.assertEqual(top["score"], 4.0)
        self.assertIn("category-prior[Finance]", top["why"])

    def test_category_prior_requires_a_whole_word(self):
        # "refinance" merely CONTAINS "finance" as a substring — the intent
        # never names the Finance category, so no category-prior may fire.
        results = skillselect.select("refinance my mortgage", REGISTRY, top_n=10)
        self.assertNotIn("finance-report", _names(results))
        for result in results:
            self.assertNotIn("category-prior", result["why"])

    def test_matched_token_counted_once_in_highest_field(self):
        # "pdf" is in both the name and the triggers of pdf-toolkit; it must be
        # scored in the name field only (3.0, not 3.0 + 2.0).
        results = skillselect.select("pdf", REGISTRY)
        self.assertEqual(results[0]["score"], 3.0)
        self.assertEqual(results[0]["matched_tokens"], ["pdf"])
        self.assertIn("name[pdf]", results[0]["why"])
        self.assertNotIn("triggers[pdf]", results[0]["why"])

    def test_deterministic_tie_break_by_name(self):
        registry = _registry(
            _entry("chart-zebra", "Engineering", "Charts.", []),
            _entry("chart-alpha", "Engineering", "Charts.", []),
        )
        results = skillselect.select("chart", registry, top_n=2)
        self.assertEqual(_names(results), ["chart-alpha", "chart-zebra"])
        self.assertEqual(results[0]["score"], results[1]["score"])

    def test_zero_score_candidates_are_dropped(self):
        results = skillselect.select("pdf", REGISTRY, top_n=10)
        self.assertEqual(_names(results), ["pdf-toolkit", "doc-converter"])

    def test_duplicate_archives_collapse_to_one_candidate(self):
        registry = _registry(
            _entry("dup", "Alpha", "Unique foobar signal."),
            _entry("dup", "Alpha", "Unique foobar signal."),
        )
        results = skillselect.select("foobar", registry, top_n=5)
        self.assertEqual(_names(results), ["dup"])

    def test_same_name_skills_in_two_categories_rank_independently(self):
        # De-dup is by (category, name): two DIFFERENT skills sharing a name
        # across categories must both survive scoring and rank independently.
        registry = _registry(
            _entry("dup", "Alpha", "Has foobar in text.", ["foobar signal"]),
            _entry("dup", "Beta", "Mentions foobar."),
        )
        results = skillselect.select("foobar", registry, top_n=5)
        self.assertEqual([r["category"] for r in results], ["Alpha", "Beta"])
        self.assertEqual(results[0]["score"], 2.0)  # trigger hit
        self.assertEqual(results[1]["score"], 1.0)  # description hit

    def test_malformed_entries_are_skipped(self):
        registry = {"version": 1, "skill_count": 2, "skills": ["not-a-dict", None]}
        self.assertEqual(skillselect.select("anything", registry), [])


class TestExplainability(unittest.TestCase):
    def test_matched_tokens_and_why(self):
        results = skillselect.select("merge files", REGISTRY, top_n=1)
        top = results[0]
        self.assertEqual(top["name"], "pdf-toolkit")
        # "merge" fires in the triggers, "files" in the description — both reported.
        self.assertEqual(top["matched_tokens"], ["files", "merge"])
        self.assertEqual(top["why"], "matched triggers[merge] + description[files]")


class TestOverrides(unittest.TestCase):
    def test_pin_forces_order_at_top(self):
        overrides = {"pin": ["doc-converter", "finance-report"]}
        results = skillselect.select("pdf", REGISTRY, overrides)
        # Pinned first in declared order, even though pdf-toolkit scores highest.
        self.assertEqual(_names(results)[:2], ["doc-converter", "finance-report"])
        self.assertTrue(results[0]["why"].startswith("pinned (manual override)"))
        self.assertIn("pdf-toolkit", _names(results))

    def test_pin_fills_top_n_first(self):
        overrides = {"pin": ["doc-converter", "finance-report", "ops-console"]}
        results = skillselect.select("pdf", REGISTRY, overrides, top_n=2)
        self.assertEqual(_names(results), ["doc-converter", "finance-report"])

    def test_unknown_pin_ignored(self):
        overrides = {"pin": ["ghost-skill"]}
        results = skillselect.select("pdf", REGISTRY, overrides)
        self.assertNotIn("ghost-skill", _names(results))
        self.assertEqual(_names(results)[0], "pdf-toolkit")

    def test_duplicate_pins_force_include_once(self):
        # The same skill pinned twice is force-included once, in declared order.
        results = skillselect.select(
            "pdf", REGISTRY, {"pin": ["doc-converter", "doc-converter"]}, top_n=5
        )
        self.assertEqual(_names(results).count("doc-converter"), 1)
        self.assertEqual(_names(results)[0], "doc-converter")

    def test_pin_matches_every_entry_with_that_name(self):
        # A pin matches on the bare name: same-name skills in two categories
        # are all force-included.
        registry = _registry(
            _entry("dup", "Alpha", "Alpha text."),
            _entry("dup", "Beta", "Beta text."),
        )
        results = skillselect.select("", registry, {"pin": ["dup"]}, top_n=5)
        self.assertEqual([r["category"] for r in results], ["Alpha", "Beta"])

    def test_exclude_drops_top_scorer(self):
        results = skillselect.select("pdf", REGISTRY, {"exclude": ["pdf-toolkit"]})
        self.assertEqual(_names(results), ["doc-converter"])

    def test_exclude_wins_over_pin(self):
        overrides = {"pin": ["pdf-toolkit"], "exclude": ["pdf-toolkit"]}
        results = skillselect.select("pdf", REGISTRY, overrides)
        self.assertNotIn("pdf-toolkit", _names(results))

    def test_boost_multiplier_lifts_score(self):
        results = skillselect.select("pdf", REGISTRY, {"boost": {"doc-converter": 5}})
        # doc-converter 1.0 * 5 = 5.0 beats pdf-toolkit's 3.0.
        self.assertEqual(_names(results), ["doc-converter", "pdf-toolkit"])
        self.assertEqual(results[0]["score"], 5.0)
        self.assertIn("boost[x5]", results[0]["why"])

    def test_boost_factor_zero_drops_unpinned_skill(self):
        # A 0 factor zeroes the score: the skill drops out of an un-pinned
        # selection (only positive scores are returned) — unless it is pinned.
        results = skillselect.select("pdf", REGISTRY, {"boost": {"pdf-toolkit": 0}})
        self.assertEqual(_names(results), ["doc-converter"])
        results = skillselect.select(
            "pdf", REGISTRY, {"boost": {"pdf-toolkit": 0}, "pin": ["pdf-toolkit"]}
        )
        self.assertEqual(_names(results)[0], "pdf-toolkit")
        self.assertEqual(results[0]["score"], 0.0)
        self.assertIn("boost[x0]", results[0]["why"])

    def test_categories_whitelist_filters_scored_candidates(self):
        results = skillselect.select("pdf", REGISTRY, {"categories": ["Finance"]}, top_n=10)
        self.assertEqual(results, [])  # no Finance skill matches "pdf"

    def test_pinned_skill_bypasses_categories_filter(self):
        overrides = {"pin": ["doc-converter"], "categories": ["Finance"]}
        results = skillselect.select("pdf", REGISTRY, overrides)
        self.assertEqual(_names(results), ["doc-converter"])

    def test_malformed_override_fields_are_ignored(self):
        overrides = {"pin": "pdf-toolkit", "exclude": "pdf-toolkit", "boost": [1], "categories": "Finance"}
        results = skillselect.select("pdf", REGISTRY, overrides)
        self.assertEqual(_names(results), ["pdf-toolkit", "doc-converter"])


class TestBoundaries(unittest.TestCase):
    def test_empty_intent_returns_nothing(self):
        self.assertEqual(skillselect.select("", REGISTRY), [])

    def test_empty_intent_still_returns_pins(self):
        results = skillselect.select("", REGISTRY, {"pin": ["ops-console"]})
        self.assertEqual(_names(results), ["ops-console"])
        self.assertEqual(results[0]["matched_tokens"], [])

    def test_stopword_only_intent_returns_nothing(self):
        self.assertEqual(skillselect.select("the and with", REGISTRY), [])

    def test_top_n_zero_and_negative(self):
        self.assertEqual(skillselect.select("pdf", REGISTRY, top_n=0), [])
        self.assertEqual(skillselect.select("pdf", REGISTRY, top_n=-2), [])

    def test_top_n_above_candidate_count_returns_all(self):
        results = skillselect.select("pdf", REGISTRY, top_n=99)
        self.assertEqual(_names(results), ["pdf-toolkit", "doc-converter"])

    def test_absent_overrides_file_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / "no-such-overrides.json"
            self.assertIsNone(skillselect.load_overrides(missing))
        results = skillselect.select("pdf", REGISTRY, None)
        self.assertEqual(_names(results)[0], "pdf-toolkit")


class TestCli(unittest.TestCase):
    def _write_registry(self, tmp):
        path = pathlib.Path(tmp) / "registry.json"
        path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        return path

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = skillselect.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_cli_writes_ranked_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._write_registry(tmp)
            rc, stdout, _ = self._run(["pdf", "--registry", str(registry), "--top-n", "1"])
        self.assertEqual(rc, 0)
        ranked = json.loads(stdout)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["name"], "pdf-toolkit")
        self.assertEqual(
            sorted(ranked[0]), ["category", "matched_tokens", "name", "score", "why"]
        )

    def test_cli_honors_overrides_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._write_registry(tmp)
            overrides = pathlib.Path(tmp) / "overrides.json"
            overrides.write_text(json.dumps({"exclude": ["pdf-toolkit"]}), encoding="utf-8")
            rc, stdout, _ = self._run(
                ["pdf", "--registry", str(registry), "--overrides", str(overrides)]
            )
        self.assertEqual(rc, 0)
        self.assertNotIn("pdf-toolkit", _names(json.loads(stdout)))

    # ---- failure paths: unreadable registry / malformed overrides ----
    def test_cli_missing_registry_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / "absent.json"
            rc, _, stderr = self._run(["pdf", "--registry", str(missing)])
        self.assertEqual(rc, 1)
        self.assertIn("cannot load registry", stderr)

    def test_cli_malformed_registry_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            rc, _, stderr = self._run(["pdf", "--registry", str(bad)])
        self.assertEqual(rc, 1)
        self.assertIn("cannot load registry", stderr)

    def test_cli_malformed_overrides_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._write_registry(tmp)
            bad = pathlib.Path(tmp) / "overrides.json"
            bad.write_text("[1, 2", encoding="utf-8")
            rc, _, stderr = self._run(
                ["pdf", "--registry", str(registry), "--overrides", str(bad)]
            )
        self.assertEqual(rc, 1)
        self.assertIn("cannot parse overrides", stderr)

    def test_cli_absent_overrides_file_runs_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._write_registry(tmp)
            missing = pathlib.Path(tmp) / "absent-overrides.json"
            rc, stdout, _ = self._run(
                ["pdf", "--registry", str(registry), "--overrides", str(missing)]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout)[0]["name"], "pdf-toolkit")

    def test_cli_non_dict_overrides_document_is_ignored(self):
        # TA-1: a valid-JSON-but-non-dict overrides document is no overrides.
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._write_registry(tmp)
            overrides = pathlib.Path(tmp) / "overrides.json"
            overrides.write_text("[]", encoding="utf-8")
            rc, stdout, _ = self._run(
                ["pdf", "--registry", str(registry), "--overrides", str(overrides)]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout)[0]["name"], "pdf-toolkit")


if __name__ == "__main__":
    unittest.main()
