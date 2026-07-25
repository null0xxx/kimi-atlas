"""Behaviour tests for the pure deterministic-floor synthesiser."""
from __future__ import annotations

import unittest

from scripts import floorsynth


def _defect(category="CODE-QUALITY", severity="HIGH", did="X1"):
    return {"id": did, "category": category, "severity": severity,
            "location": "a.py:1", "fix": "fix it"}


class TestScriptDefectsFrom(unittest.TestCase):
    def _full_evidence(self, **over):
        ev = {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
              "sast_defects": [], "astlens_defects": [], "syntaxlens_defects": [],
              "lintlens_advisory": [], "docs_clean": True}
        ev.update(over)
        return ev

    def test_collects_all_six_lists_in_skill_order(self):
        ev = self._full_evidence(
            lint_defects=[_defect(did="L")], reqcoverage_defects=[_defect(did="R")],
            pathcheck_defects=[_defect(did="P")], sast_defects=[_defect(did="S")],
            astlens_defects=[_defect(did="A")], syntaxlens_defects=[_defect(did="Y")])
        got = [d["id"] for d in floorsynth.script_defects_from(ev)]
        self.assertEqual(got, ["L", "R", "P", "S", "A", "Y"])

    def test_lintlens_advisory_is_never_merged(self):
        adv = {"lane": "auto", "tool": "ruff", "path": "a.py", "line": 3, "message": "E501"}
        ev = self._full_evidence(lintlens_advisory=[adv])
        self.assertEqual(floorsynth.script_defects_from(ev), [])

    def test_optional_keys_may_be_absent(self):
        # docs_clean=True also proves the flag key is absence-checked but NEVER
        # collected: ``list(True)`` would raise if it joined the collection loop.
        ev = {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
              "docs_clean": True}
        self.assertEqual(floorsynth.script_defects_from(ev), [])

    def test_missing_mandatory_key_is_a_blocking_defect_not_a_crash(self):
        # lint_defects absent, everything else present.
        ev = {"reqcoverage_defects": [], "pathcheck_defects": [], "docs_clean": True}
        out = floorsynth.script_defects_from(ev)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], "evidence-incomplete")
        self.assertEqual(out[0]["category"], "DOES-IT-RUN")
        self.assertEqual(out[0]["severity"], "CRITICAL")
        self.assertIn("lint_defects", out[0]["fix"])
        # The synthesized category must be a rubric dimension, or the merged critic
        # fails schema validation downstream instead of blocking the run.
        from scripts import quality, verdict
        self.assertEqual(quality.enforce_critic_schema(verdict.merge([], out)), [])

    def test_mandatory_key_set_is_pinned_literally(self):
        # Spelled out, because the per-key test below reads the tuple from the module:
        # demoting a key to the HEAD of OPTIONAL preserves collection order, so it
        # would shrink that loop instead of failing it. Only a literal catches it.
        self.assertEqual(floorsynth.MANDATORY_EVIDENCE_KEYS,
                         ("lint_defects", "reqcoverage_defects", "pathcheck_defects"))

    def test_flag_key_set_is_pinned_literally(self):
        # Spelled out for the same reason as the tuple above. These keys are NOT
        # defect lists: they are absence-checked only, so they can never join
        # MANDATORY_EVIDENCE_KEYS (the collection loop would do ``list(True)``).
        self.assertEqual(floorsynth.MANDATORY_FLAG_KEYS, ("docs_clean",))

    def test_each_mandatory_key_is_individually_required(self):
        for key in floorsynth.MANDATORY_EVIDENCE_KEYS:
            ev = {k: [] for k in floorsynth.MANDATORY_EVIDENCE_KEYS if k != key}
            ev["docs_clean"] = True
            out = floorsynth.script_defects_from(ev)
            self.assertEqual([d["id"] for d in out], ["evidence-incomplete"], key)
            self.assertIn(key, out[0]["fix"])

    def test_absent_docs_clean_is_incomplete_not_clean_docs(self):
        # The unique fail-OPEN key. The SKILL reads ``ev.get("docs_clean", True)``, so
        # a line dropped from the Step-2 evidence literal would default the docs floor
        # to CLEAN — the exact dropped-line failure floorsynth exists to kill, and the
        # one place the old block was STRICTLY more blocking (it died with KeyError and
        # wrote no merged_critic.json). ``runcheck`` needs no such check: an absent one
        # makes ``synth_runcheck({})`` synthesise its CRITICAL, i.e. it fails CLOSED.
        out = floorsynth.script_defects_from(
            {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": []})
        self.assertEqual([d["id"] for d in out], ["evidence-incomplete"])
        self.assertEqual(out[0]["category"], "DOES-IT-RUN")
        self.assertEqual(out[0]["severity"], "CRITICAL")
        self.assertIn("docs_clean", out[0]["fix"])

    def test_null_docs_clean_is_incomplete(self):
        out = floorsynth.script_defects_from(
            {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
             "docs_clean": None})
        self.assertEqual([d["id"] for d in out], ["evidence-incomplete"])
        self.assertIn("docs_clean", out[0]["fix"])

    def test_false_docs_clean_is_a_legitimate_value_not_an_absence(self):
        # False IS the dirty-docs signal, carried by synth_docs — not missing evidence.
        # A falsiness check (``if not ev.get(k)``) here would report it missing and
        # relabel a real docs-naming failure as an orchestrator re-run instruction.
        out = floorsynth.script_defects_from(
            {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
             "docs_clean": False})
        self.assertEqual(out, [])
        self.assertEqual([d["id"] for d in floorsynth.synth_docs(False)], ["docs-naming"])

    def test_present_but_null_mandatory_key_is_incomplete_not_silently_empty(self):
        # A present-but-NULL key is not evidence: ``ev.get(key) or []`` contributes
        # nothing, so a mere key-PRESENCE check would report complete evidence for a
        # lens that never ran. Today's SKILL does ``ev["lint_defects"]`` -> ``+= None``
        # -> TypeError -> the heredoc dies and no merged_critic.json is written, i.e.
        # fail-CLOSED; a silent empty contribution here would be fail-OPEN.
        out = floorsynth.script_defects_from(
            {"lint_defects": None, "reqcoverage_defects": [], "pathcheck_defects": [],
             "docs_clean": True})
        self.assertEqual([d["id"] for d in out], ["evidence-incomplete"])
        self.assertEqual(out[0]["category"], "DOES-IT-RUN")
        self.assertIn("lint_defects", out[0]["fix"])

    def test_incomplete_evidence_never_swallows_a_present_defect(self):
        from scripts import verdict
        sec = {"id": "S1", "category": "SECURITY", "severity": "CRITICAL",
               "location": "a.py:1", "fix": "patch"}
        out = floorsynth.script_defects_from(
            {"reqcoverage_defects": [], "pathcheck_defects": [], "sast_defects": [sec],
             "docs_clean": True})
        self.assertIn(sec, out)
        self.assertEqual(verdict.merge([], out)["dimensions"]["SECURITY"], "no")


class TestSynthesizedGateMirrors(unittest.TestCase):
    def test_red_runcheck_synthesizes_a_critical(self):
        rc = {"ok": False, "test_count": 0, "new_tests_collected": False}
        out = floorsynth.synth_runcheck(rc, verify_cmd="make test")
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["id"], out[0]["category"], out[0]["severity"]),
                         ("runcheck", "DOES-IT-RUN", "CRITICAL"))
        self.assertIn("make test", out[0]["location"])

    def test_green_runcheck_synthesizes_nothing(self):
        rc = {"ok": True, "test_count": 3, "new_tests_collected": True}
        self.assertEqual(floorsynth.synth_runcheck(rc, verify_cmd="make test"), [])

    def test_partially_green_runcheck_still_synthesizes_a_critical(self):
        rc = {"ok": True, "test_count": 0, "new_tests_collected": False}
        self.assertEqual(len(floorsynth.synth_runcheck(rc, verify_cmd="make test")), 1)

    def test_dirty_docs_synthesize_a_critical(self):
        out = floorsynth.synth_docs(False)
        self.assertEqual((out[0]["id"], out[0]["category"], out[0]["severity"]),
                         ("docs-naming", "CODE-QUALITY", "CRITICAL"))

    def test_clean_docs_synthesize_nothing(self):
        self.assertEqual(floorsynth.synth_docs(True), [])


from scripts import quality, verdict


class TestEmptyDiff(unittest.TestCase):
    def test_empty_diff_is_a_blocking_correctness_defect(self):
        out = floorsynth.empty_diff_defect("")
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["id"], out[0]["category"], out[0]["severity"]),
                         ("empty-diff", "CORRECTNESS", "CRITICAL"))

    def test_whitespace_only_diff_is_still_empty(self):
        self.assertEqual(len(floorsynth.empty_diff_defect("  \n\t\n")), 1)

    def test_real_diff_synthesizes_nothing(self):
        self.assertEqual(floorsynth.empty_diff_defect("--- a/x.py\n+++ b/x.py\n+1\n"), [])


def _every_synthesized_defect():
    """Every defect this module can emit, gathered by CALLING it (never by reading a
    constant), so a test over this corpus cannot shrink when a `fix` string changes."""
    out = list(floorsynth.script_defects_from({}))                     # evidence-incomplete
    out += floorsynth.synth_runcheck(
        {"ok": False, "test_count": 0, "new_tests_collected": False}, "make test")
    out += floorsynth.synth_docs(False)
    out += floorsynth.empty_diff_defect("")
    out += floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])
    out += floorsynth.critics_missing_defects([])
    bad = {"dimensions": {}, "verdict": "OK",
           "defects": [{"id": "x", "category": "NOPE", "severity": "MEDIUM",
                        "location": "a.py:1", "fix": "f"}]}
    merged, _errs = floorsynth.merge_and_validate([bad], [])           # critic-schema
    out += [d for d in merged["defects"] if d["id"] == "critic-schema"]
    return out


class TestFixStringAudience(unittest.TestCase):
    """A `fix` this module writes is either shown to a human (orchestrator ids) or handed
    to the CODER as a trusted instruction (skills/atlas/SKILL.md:677-680). The two
    audiences admit different content, so the split has to be enforced, not assumed."""

    ALL_IDS = {"evidence-incomplete", "runcheck", "docs-naming", "empty-diff",
               "out-of-scope:lib/x.py",
               "critic-missing:correctness", "critic-missing:code-quality",
               "critic-missing:security", "critic-schema"}

    def test_the_audited_corpus_covers_every_synthesis(self):
        """Non-vacuity: if a new synthesis is added and not gathered above, the two
        audits below would silently skip it."""
        self.assertEqual({d["id"] for d in _every_synthesized_defect()}, self.ALL_IDS)

    def test_no_coder_facing_fix_names_review_root(self):
        # review_root is the `cwd` for BOTH difftool.capture and runcheck.run, and
        # interactively it is persisted inside the coder's own writable root
        # (SKILL.md:313, :328) — it is gate input. A `fix` routed to the coder must
        # never tell the LLM under review to inspect or adjust it. Asserted literally
        # first, so the loop cannot be emptied by moving empty-diff into the frozenset.
        self.assertNotIn("empty-diff", floorsynth.ORCHESTRATOR_DEFECT_IDS)
        audited = 0
        for d in _every_synthesized_defect():
            if d["id"] in floorsynth.ORCHESTRATOR_DEFECT_IDS:
                continue
            audited += 1
            self.assertNotIn("review_root", d["fix"], d["id"])
        self.assertEqual(audited, 4)   # empty-diff, out-of-scope:*, runcheck, docs-naming

    def test_every_orchestrator_fix_is_labelled_as_such(self):
        seen = set()
        for d in _every_synthesized_defect():
            if d["id"] not in floorsynth.ORCHESTRATOR_DEFECT_IDS:
                continue
            seen.add(d["id"])
            self.assertTrue(d["fix"].startswith("ORCHESTRATOR ACTION"), d["id"])
        self.assertEqual(seen, set(floorsynth.ORCHESTRATOR_DEFECT_IDS))


class TestCriticsMissing(unittest.TestCase):
    def test_all_three_present_synthesizes_nothing(self):
        self.assertEqual(floorsynth.critics_missing_defects(
            [n for n, _ in floorsynth.CRITIC_ARTIFACTS]), [])

    def test_missing_critic_uses_its_own_dimension_not_SCHEMA(self):
        out = floorsynth.critics_missing_defects(["critic_correctness.json"])
        cats = sorted(d["category"] for d in out)
        self.assertEqual(cats, ["CODE-QUALITY", "SECURITY"])
        self.assertNotIn("SCHEMA", cats)

    def test_missing_critic_defect_is_schema_valid_and_flips_its_dimension(self):
        out = floorsynth.critics_missing_defects([])
        merged = verdict.merge([], out)
        self.assertEqual(quality.enforce_critic_schema(merged), [])
        self.assertEqual(merged["dimensions"]["SECURITY"], "no")
        self.assertEqual(merged["verdict"], "FAIL")

    def test_orchestrator_ids_cover_every_non_coder_actionable_synthesis(self):
        ids = {d["id"] for d in floorsynth.critics_missing_defects([])}
        ids |= {d["id"] for d in floorsynth.script_defects_from({})}
        self.assertTrue(ids <= floorsynth.ORCHESTRATOR_DEFECT_IDS, ids)
        for d in floorsynth.critics_missing_defects([]):
            self.assertTrue(d["fix"].startswith("ORCHESTRATOR ACTION"))


class TestOutOfScopeDefects(unittest.TestCase):
    """S3(a)/R3: one blocking HIGH CORRECTNESS defect per file changed OUTSIDE
    scope_paths — the reviewed tree must equal the executed tree. HIGH rather
    than CRITICAL because the legitimate case exists (a cross-cutting edit);
    HIGH already blocks AND fires V7. The fix is coder-actionable (NOT an
    orchestrator id): revert the out-of-scope change, or the human widens scope
    at the OUTPUT gate. Wired ONLY on a git tree with a resolvable baseline
    (difftool.git_tree_has_baseline) — elsewhere the fold contributes []."""

    def test_out_of_scope_file_fires_once_per_path(self):
        out = floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])
        self.assertEqual(len(out), 1)
        d = out[0]
        self.assertEqual((d["id"], d["category"], d["severity"]),
                         ("out-of-scope:lib/x.py", "CORRECTNESS", "HIGH"))
        self.assertEqual(d["location"], "lib/x.py")

    def test_in_scope_paths_stay_silent(self):
        self.assertEqual(
            floorsynth.out_of_scope_defects(["src/a.py", "src/sub/b.py"], ["src"]), [])

    def test_whole_tree_scopes_never_fire(self):
        for scope in (["."], [""], ["./"]):
            with self.subTest(scope=scope):
                self.assertEqual(
                    floorsynth.out_of_scope_defects(["lib/x.py", "a.py"], scope), [])

    def test_scope_spelling_equivalence(self):
        for scope in (["src"], ["src/"], ["./src"]):
            with self.subTest(scope=scope):
                self.assertEqual(floorsynth.out_of_scope_defects(["src/a.py"], scope), [])
                self.assertEqual(len(floorsynth.out_of_scope_defects(["lib/a.py"], scope)), 1)

    def test_prefix_boundary_is_not_a_match(self):
        self.assertEqual(len(floorsynth.out_of_scope_defects(["src2/x.py"], ["src"])), 1)

    def test_file_scope_matches_itself_only(self):
        self.assertEqual(floorsynth.out_of_scope_defects(["src/a.py"], ["src/a.py"]), [])
        self.assertEqual(len(floorsynth.out_of_scope_defects(["src/b.py"], ["src/a.py"])), 1)

    def test_tool_residue_is_not_a_defect(self):
        # The false-positive gate (challenge fold T2-F1): a verification run
        # legitimately regenerates these outside scope_paths on HONEST runs.
        residue = [".atlas/run-1/state.json", ".coverage", ".coverage.xml",
                   ".pytest_cache/v/cache/lastfailed", "lib/__pycache__/m.pyc",
                   "lib/old.pyo", "htmlcov/index.html", ".mypy_cache/x", ".ruff_cache/x",
                   ".tox/x", ".nox/x", ".venv/lib/python", "venv/lib/python",
                   "node_modules/pkg/index.js", "dist/bundle.js", "build/out.o",
                   "target/debug/main", "foo.egg-info/PKG-INFO"]
        self.assertEqual(floorsynth.out_of_scope_defects(residue, ["src"]), [])
        # Control: a real out-of-scope change still fires — the residue list
        # cannot be emptied into swallowing everything.
        self.assertEqual(len(floorsynth.out_of_scope_defects(["lib/real.py"], ["src"])), 1)

    def test_deterministic_sorted_output(self):
        a = floorsynth.out_of_scope_defects(["z/b.py", "a/c.py", "m/d.py"], ["src"])
        b = floorsynth.out_of_scope_defects(["m/d.py", "z/b.py", "a/c.py"], ["src"])
        self.assertEqual(a, b)
        self.assertEqual([d["location"] for d in a], ["a/c.py", "m/d.py", "z/b.py"])

    def test_empty_inputs(self):
        self.assertEqual(floorsynth.out_of_scope_defects([], ["src"]), [])
        self.assertEqual(floorsynth.out_of_scope_defects(None, ["src"]), [])

    def test_empty_scope_fails_closed(self):
        # No legitimate scope is empty — an absent scope can never mean whole-tree.
        self.assertEqual(len(floorsynth.out_of_scope_defects(["a.py"], [])), 1)
        self.assertEqual(len(floorsynth.out_of_scope_defects(["a.py"], None)), 1)

    def test_fix_is_coder_actionable_and_names_the_two_resolutions(self):
        d = floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])[0]
        self.assertIn("lib/x.py", d["fix"])
        self.assertIn("revert", d["fix"].lower())
        self.assertIn("scope", d["fix"])
        # The second resolution is the HUMAN widening scope at the gate — never
        # the coder editing the frozen scope_paths (SKILL.md:309).
        self.assertIn("human", d["fix"].lower())

    def test_id_is_coder_facing_not_orchestrator(self):
        d = floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])[0]
        self.assertNotIn(d["id"], floorsynth.ORCHESTRATOR_DEFECT_IDS)

    def test_high_blocks_merge_and_drives_refine(self):
        ds = floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])
        merged = verdict.merge([], ds)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(merged["dimensions"]["CORRECTNESS"], "no")
        self.assertTrue(verdict.should_refine(merged, 0))
        # ... and a legitimate edit the coder must not revert ends UNVERIFIED at
        # the human gate (fold T2-F6), never silently cleared.
        self.assertEqual(verdict.final_status(merged, False), "UNVERIFIED")

    def test_defect_shape_is_canonical(self):
        d = floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])[0]
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})


class TestGateAgreementMatrix(unittest.TestCase):
    """For EVERY deterministic failure condition, gate AND final_status must both
    say UNVERIFIED. This is the standing invariant that floor completeness used to
    lack."""

    GREEN_RC = {"ok": True, "test_count": 3, "new_tests_collected": True}
    ALL_LOADED = ("critic_correctness.json", "critic_code_quality.json", "critic_security.json")

    def _run(self, evidence, diff="--- a/x.py\n+++ b/x.py\n+1\n", loaded=None, docs_clean=True,
             critics=(), drop_docs_clean=False):
        loaded = self.ALL_LOADED if loaded is None else loaded
        # The SKILL reads docs_clean out of the SAME det_evidence.json, so mirror that:
        # one source, read everywhere through ev.get("docs_clean", True).
        ev = dict(evidence)
        ev["docs_clean"] = docs_clean
        if drop_docs_clean:                 # simulate the dropped Step-2 literal line
            ev.pop("docs_clean")
        sd = floorsynth.script_defects_from(ev)
        sd += floorsynth.synth_runcheck(ev.get("runcheck", {}), ev.get("verify_cmd", ""))
        sd += floorsynth.synth_docs(ev.get("docs_clean", True))
        sd += floorsynth.empty_diff_defect(diff)
        sd += floorsynth.critics_missing_defects(loaded)
        merged, schema_errors = floorsynth.merge_and_validate(list(critics), sd)
        gate_inputs = {"runcheck": ev.get("runcheck", {}), "schema_errors": schema_errors,
                       "lint_defects": ev.get("lint_defects", []),
                       "reqcoverage_defects": ev.get("reqcoverage_defects", []),
                       "pathcheck_defects": ev.get("pathcheck_defects", []),
                       "docs_clean": ev.get("docs_clean", True)}
        return verdict.gate(merged, gate_inputs), verdict.final_status(merged, False)

    def _clean(self, **over):
        ev = {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
              "sast_defects": [], "astlens_defects": [], "syntaxlens_defects": [],
              "runcheck": dict(self.GREEN_RC), "verify_cmd": "make test"}
        ev.update(over)
        return ev

    def test_control_arm_is_genuinely_green(self):
        """Non-vacuity: if this ever fails UNVERIFIED, every arm below is vacuous."""
        self.assertEqual(self._run(self._clean()), ("OK", "OK"))

    def test_every_failure_condition_blocks_both_gate_and_final_status(self):
        cases = {
            "runcheck-red": dict(evidence=self._clean(
                runcheck={"ok": False, "test_count": 0, "new_tests_collected": False})),
            "lint-HIGH": dict(evidence=self._clean(lint_defects=[_defect("CODE-QUALITY", "HIGH")])),
            "reqcov-HIGH": dict(evidence=self._clean(
                reqcoverage_defects=[_defect("REQUIREMENTS-COVERAGE", "HIGH")])),
            "pathcheck": dict(evidence=self._clean(
                pathcheck_defects=[_defect("CORRECTNESS", "CRITICAL")])),
            "sast-HIGH": dict(evidence=self._clean(sast_defects=[_defect("SECURITY", "HIGH")])),
            "astlens-HIGH": dict(evidence=self._clean(astlens_defects=[_defect("DOES-IT-RUN", "HIGH")])),
            "syntaxlens-HIGH": dict(evidence=self._clean(
                syntaxlens_defects=[_defect("DOES-IT-RUN", "HIGH")])),
            "evidence-incomplete": dict(evidence={"reqcoverage_defects": [], "pathcheck_defects": [],
                                                  "runcheck": dict(self.GREEN_RC)}),
            "docs-dirty": dict(evidence=self._clean(), docs_clean=False),
            # A docs_clean line dropped from the Step-2 evidence literal must BLOCK,
            # not inherit the ev.get(..., True) default the SKILL reads it with.
            "docs_clean-absent": dict(evidence=self._clean(), drop_docs_clean=True),
            "empty-diff": dict(evidence=self._clean(), diff=""),
            "critic-missing": dict(evidence=self._clean(), loaded=("critic_security.json",)),
            "schema-errors": dict(evidence=self._clean(), critics=[
                {"dimensions": {}, "verdict": "OK",
                 "defects": [{"id": "x", "category": "NOPE", "severity": "MEDIUM",
                              "location": "a.py:1", "fix": "f"}]}]),
        }
        for name, kwargs in cases.items():
            with self.subTest(condition=name):
                self.assertEqual(self._run(**kwargs), ("UNVERIFIED", "UNVERIFIED"))

    def test_advisory_lint_never_blocks(self):
        adv = [{"lane": "auto", "tool": "ruff", "path": "a.py", "line": 3, "message": "E501"}]
        self.assertEqual(self._run(self._clean(lintlens_advisory=adv)), ("OK", "OK"))


class TestMergeAndValidate(unittest.TestCase):
    def test_malformed_critic_yields_schema_errors_and_a_blocking_merged_critic(self):
        # A malformed DEFECT, not a malformed dimensions map: merge copies defects
        # verbatim but REBUILDS dimensions, so only a defect survives to validation.
        # Severity MEDIUM keeps the malformed critic's own defect non-blocking, so
        # nothing asserted below is attributable to the bad input.
        bad = {"dimensions": {}, "verdict": "OK",
               "defects": [{"id": "x", "category": "NOPE", "severity": "MEDIUM",
                            "location": "a.py:1", "fix": "f"}]}
        # A real deterministic-floor defect rides along, because the re-merge is the
        # ONLY thing keeping it in merged_critic.json: re-merging over a fresh
        # [critic-schema] list would drop every floor defect (SECURITY flips back to
        # "yes") while gate/final_status still blocked on critic-schema — so REFINE's
        # fix list and OUTPUT's blocking list would silently lose the real findings.
        sast = {"id": "S1", "category": "SECURITY", "severity": "CRITICAL",
                "location": "a.py:1", "fix": "patch"}
        merged, schema_errors = floorsynth.merge_and_validate([bad], [sast])
        self.assertTrue(schema_errors)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertTrue(any(d["id"] == "critic-schema" for d in merged["defects"]))
        self.assertIn("S1", [d["id"] for d in merged["defects"]])
        self.assertEqual(merged["dimensions"]["SECURITY"], "no")

    def test_a_bad_dimension_value_is_invisible_to_merged_validation(self):
        """Documented limit, not a bug: merge rebuilds dimensions from rubric.DIMENSIONS,
        so only a malformed DEFECT can ever populate schema_errors. This is exactly why
        critics_missing_defects has to exist."""
        merged, errs = floorsynth.merge_and_validate(
            [{"dimensions": {"CORRECTNESS": "maybe"}, "defects": [], "verdict": "OK"}], [])
        self.assertEqual(errs, [])

    def test_wellformed_critic_yields_no_schema_error_and_no_synthetic_defect(self):
        good = verdict.merge([], [])
        merged, schema_errors = floorsynth.merge_and_validate([good], [])
        self.assertEqual(schema_errors, [])
        self.assertEqual(merged["defects"], [])


if __name__ == "__main__":
    unittest.main()
