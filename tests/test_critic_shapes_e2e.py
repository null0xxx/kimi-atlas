# tests/test_critic_shapes_e2e.py
"""End-to-end pins for S4 (Task 3 Step 1): the four critic shapes that printed
``✅ VERIFIED`` over a green deterministic evidence set at v1.5.1 must each end
UNVERIFIED now — driven through the REAL Step-3.4 validate-and-persist block and
the REAL Step-4+5 merge/gate block, both extracted verbatim from the SKILL text.

The two controls are the vacuity guards: one real CRITICAL must still block (the
suite cannot pass by ignoring defects), and three clean critics must stay OK
(the suite cannot pass by blocking everything).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "atlas" / "SKILL.md"


def _heredoc_bodies(text):
    """Same extractor as tests/test_skill_floor_contract.py (kept standalone)."""
    bodies, cur = [], None
    for line in text.splitlines():
        if cur is None:
            if line.rstrip().endswith("<<'PY'"):
                cur = []
        elif line.strip() == "PY":
            bodies.append(textwrap.dedent("\n".join(cur)))
            cur = None
        else:
            cur.append(line)
    return bodies


_BODIES = _heredoc_bodies(SKILL.read_text(encoding="utf-8"))


def _one(pred, what):
    matches = [b for b in _BODIES if pred(b)]
    if len(matches) != 1:
        raise AssertionError(
            "expected exactly one %s heredoc in the SKILL, found %d — the block "
            "this suite executes has been removed or duplicated" % (what, len(matches)))
    return matches[0]


_VALIDATE_BLOCK = _one(
    lambda b: "enforce_critic_schema" in b and "object_pairs_hook" in b,
    "Step-3.4 validate-and-persist")
_STEP45_BLOCK = _one(
    lambda b: "floorsynth.merge_and_validate(" in b, "Step-4+5 merge/gate")
_REFINE_BLOCK = _one(
    lambda b: "verdict.should_refine(" in b, "REFINE? decision")
_OUTPUT_BLOCK = _one(
    lambda b: "verdict.final_status(" in b, "OUTPUT final-status")

_ARTIFACTS = ("critic_correctness.json", "critic_code_quality.json",
              "critic_security.json")


def _critic(dim_no=(), verdict="OK", defects=()):
    dims = {d: "yes" for d in (
        "CORRECTNESS", "CODE-QUALITY", "SECURITY", "DOES-IT-RUN",
        "REQUIREMENTS-COVERAGE", "TEST-ADEQUACY")}
    for d in dim_no:
        dims[d] = "no"
    return {"dimensions": dims, "defects": list(defects), "verdict": verdict}


_CLEAN = _critic()
_CRITICAL = _critic(verdict="FAIL", defects=[{
    "id": "C1", "category": "SECURITY", "severity": "CRITICAL",
    "location": "a.py:1", "fix": "f"}])

# The four S4 shapes (spec evidence table): each printed VERIFIED at v1.5.1.
_SHAPE_VERDICT_FAIL = json.dumps(_critic(verdict="FAIL"))
_SHAPE_DIMS_NO = json.dumps(_critic(dim_no=(
    "CORRECTNESS", "CODE-QUALITY", "SECURITY", "DOES-IT-RUN",
    "REQUIREMENTS-COVERAGE", "TEST-ADEQUACY")))
_SHAPE_DRIFTED_KEY = json.dumps({
    "dimensions": _CLEAN["dimensions"],
    "findings": [{"id": "C1", "category": "SECURITY", "severity": "CRITICAL",
                  "location": "a.py:1", "fix": "f"}],
    "verdict": "OK"})
_SHAPE_DUP_KEY_OK = ('{"dimensions": %s, "defects": [{"id": "C1", "category": '
                     '"SECURITY", "severity": "CRITICAL", "location": "a.py:1", '
                     '"fix": "f"}], "defects": [], "verdict": "OK"}'
                     % json.dumps(_CLEAN["dimensions"]))
_SHAPE_DUP_KEY_FAIL = ('{"dimensions": %s, "defects": [], "defects": [{"id": '
                       '"C1", "category": "SECURITY", "severity": "CRITICAL", '
                       '"location": "a.py:1", "fix": "f"}], "verdict": "FAIL"}'
                       % json.dumps(_CLEAN["dimensions"]))


class _RunDirMixin:
    def _make_run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        env = dict(os.environ, PYTHONPATH=str(REPO), PYTHONSAFEPATH="1")
        init = (
            "from scripts import ctxstore\n"
            "ctxstore.init_run('.atlas', 'RUN', {'intent': 't', "
            "'success_criteria': ['c'], 'scope_paths': ['src'], "
            "'baseline_sha': '', 'verify_cmd': 'true'})\n"
            "ctxstore.write_artifact('.atlas', 'RUN', 'diff.patch', 'non-empty')\n"
            "ctxstore.write_artifact('.atlas', 'RUN', 'review_root', '.')\n"
            "ctxstore.write_artifact('.atlas', 'RUN', 'det_evidence.json', {\n"
            " 'runcheck': {'ok': True, 'test_count': 5, 'new_tests_collected': True},\n"
            " 'lint_defects': [], 'reqcoverage_defects': [], "
            " 'pathcheck_defects': [], 'docs_clean': True})\n"
        )
        proc = subprocess.run([sys.executable, "-c", init], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return root, env

    def _persist(self, root, env, name, raw):
        """Drive the real Step-3.4 block the way the SKILL now mandates.

        C1 (v1.5.2.1): the critic's text is no longer interpolated into the
        block's source — it is written verbatim to a scratch file by the native
        ``Write`` tool and reaches the block as ``sys.argv[1]``. This driver
        mirrors that exactly: bytes to disk, path in argv, nothing substituted
        into the Python. The block CONSUMES the scratch file, so each call gets
        a fresh one.
        """
        body = _VALIDATE_BLOCK.replace("$ATLAS_SESSION_ID", "RUN")
        body = body.replace('NAME = "critic_correctness.json"', 'NAME = "%s"' % name)
        self.assertNotIn("<the critic's returned JSON text>", body,
                         "the Step-3.4 block still interpolates model text (C1)")
        src = pathlib.Path(root) / ("%s.raw.json" % name)
        src.write_text(raw, encoding="utf-8")
        return subprocess.run([sys.executable, "-c", body, str(src)],
                              cwd=root, env=env, capture_output=True, text=True)

    def _gate(self, root, env):
        body = _STEP45_BLOCK.replace("$ATLAS_SESSION_ID", "RUN")
        proc = subprocess.run([sys.executable, "-c", body], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        return json.loads(last)

    def _advance(self, root, env, stage):
        init = ("from scripts import ctxstore\n"
                "ctxstore.advance('.atlas', 'RUN', '%s')\n" % stage)
        proc = subprocess.run([sys.executable, "-c", init], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def _output(self, root, env):
        body = _OUTPUT_BLOCK.replace("$ATLAS_SESSION_ID", "RUN")
        proc = subprocess.run([sys.executable, "-c", body], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        return json.loads(last)

    def _persist_clean(self, root, env):
        for name in _ARTIFACTS:
            proc = self._persist(root, env, name, json.dumps(_CLEAN))
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def _run_shape(self, raw):
        root, env = self._make_run()
        persists = [self._persist(root, env, name, raw) for name in _ARTIFACTS]
        return root, persists, self._gate(root, env)


class TestS4ShapesEndToEnd(_RunDirMixin, unittest.TestCase):
    """Each shape ends UNVERIFIED; the mechanism (not-persist vs dissent) is
    pinned per shape so the suite cannot go red for the wrong reason."""

    def test_verdict_fail_with_empty_defects_is_rejected_not_persisted(self):
        root, persists, out = self._run_shape(_SHAPE_VERDICT_FAIL)
        for name, proc in zip(_ARTIFACTS, persists):
            self.assertEqual(proc.returncode, 2, name)
            self.assertIn("CRITIC_SCHEMA_ERRORS", proc.stdout)
            self.assertFalse((root / ".atlas" / "RUN" / name).exists())
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        self.assertEqual(out["critics_loaded"], "0/3")
        ids = [d["id"] for d in out["blocking"]]
        self.assertIn("critic-missing:security", ids)

    def test_all_dimensions_no_persists_and_dissent_blocks(self):
        root, persists, out = self._run_shape(_SHAPE_DIMS_NO)
        for proc in persists:
            self.assertEqual(proc.returncode, 0, proc.stdout)  # schema-clean shape
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        self.assertEqual(out["critics_loaded"], "3/3")
        ids = [d["id"] for d in out["blocking"]]
        self.assertIn("dimension-dissent:correctness", ids)
        self.assertIn("dimension-dissent:security", ids)

    def test_drifted_key_is_rejected_not_persisted(self):
        root, persists, out = self._run_shape(_SHAPE_DRIFTED_KEY)
        for name, proc in zip(_ARTIFACTS, persists):
            self.assertEqual(proc.returncode, 2, name)
            self.assertIn("CRITIC_SCHEMA_ERRORS", proc.stdout)
            self.assertFalse((root / ".atlas" / "RUN" / name).exists())
        self.assertEqual(out["provisional_status"], "UNVERIFIED")

    def test_duplicate_defects_key_ok_variant_is_rejected(self):
        root, persists, out = self._run_shape(_SHAPE_DUP_KEY_OK)
        for proc in persists:
            self.assertEqual(proc.returncode, 2)
            self.assertIn("CRITIC_INVALID", proc.stdout)
            self.assertIn("duplicate", proc.stdout)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")

    def test_duplicate_defects_key_fail_variant_is_rejected(self):
        root, persists, out = self._run_shape(_SHAPE_DUP_KEY_FAIL)
        for proc in persists:
            self.assertEqual(proc.returncode, 2)
            self.assertIn("CRITIC_INVALID", proc.stdout)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")


class TestRefineSkipsOrchestratorDefects(_RunDirMixin, unittest.TestCase):
    """I1: the REFINE? decision must not burn coder passes on defects the coder
    cannot act on. Orchestrator-facing ids are filtered from BOTH should_refine
    AND the V7 clause; final_status still reads the FULL merged critic, so the
    terminal label can never go green on this filter."""

    def _refine(self, root, env, defects, refine_advances=0):
        init = (
            "from scripts import ctxstore\n"
            "ctxstore.write_artifact('.atlas', 'RUN', 'merged_critic.json', {\n"
            " 'dimensions': {}, 'verdict': 'FAIL', 'defects': %s})\n"
            % json.dumps(defects)
        )
        for _i in range(refine_advances):
            init += "ctxstore.advance('.atlas', 'RUN', 'REFINE')\n"
        proc = subprocess.run([sys.executable, "-c", init], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        body = _REFINE_BLOCK.replace("$ATLAS_SESSION_ID", "RUN")
        proc = subprocess.run([sys.executable, "-c", body], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def test_orchestrator_only_defects_do_not_refine(self):
        root, env = self._make_run()
        out = self._refine(root, env, [
            {"id": "dimension-dissent:correctness", "category": "CORRECTNESS",
             "severity": "HIGH", "location": "l", "fix": "f"},
            {"id": "critic-missing:security", "category": "SECURITY",
             "severity": "CRITICAL", "location": "l", "fix": "f"},
        ])
        self.assertEqual(out, "REFINE=False PASSES=0")

    def test_orchestrator_correctness_defect_does_not_fire_v7(self):
        # THE I1 pin: dimension-dissent:correctness carries category
        # CORRECTNESS — an unfiltered V7 clause would force a coder pass on it.
        root, env = self._make_run()
        out = self._refine(root, env, [
            {"id": "dimension-dissent:correctness", "category": "CORRECTNESS",
             "severity": "HIGH", "location": "l", "fix": "f"},
        ])
        self.assertEqual(out, "REFINE=False PASSES=0")

    def test_coder_facing_blocking_defect_still_refines(self):
        root, env = self._make_run()
        out = self._refine(root, env, [
            {"id": "C7", "category": "CORRECTNESS", "severity": "HIGH",
             "location": "l", "fix": "f"},
        ])
        self.assertEqual(out, "REFINE=True PASSES=0")

    def test_coder_facing_medium_correctness_still_fires_v7(self):
        root, env = self._make_run()
        out = self._refine(root, env, [
            {"id": "C9", "category": "CORRECTNESS", "severity": "MEDIUM",
             "location": "l", "fix": "f"},
        ])
        self.assertEqual(out, "REFINE=True PASSES=0")

    def test_pass_cap_still_holds(self):
        root, env = self._make_run()
        out = self._refine(root, env, [
            {"id": "C7", "category": "CORRECTNESS", "severity": "HIGH",
             "location": "l", "fix": "f"},
        ], refine_advances=2)
        self.assertEqual(out, "REFINE=False PASSES=2")


class TestLoadedMapAttributionE2E(_RunDirMixin, unittest.TestCase):
    """Whole-branch Important-1: loaded_map pairs artifact NAMES with their
    objects; a swap (zip order) survives the whole suite when fixtures are
    symmetric, then attributes staleness/dissent to the WRONG lens — the
    remediation re-dispatches a healthy critic and the genuinely stale one is
    never re-stamped: an unhealable RED. These fixtures are deliberately
    ASYMMETRIC so a pairing swap cannot hide."""

    def test_exactly_the_stale_lens_is_named(self):
        root, env = self._make_run()
        self._persist_clean(root, env)                     # all stamped pass=0
        self._advance(root, env, "REFINE")                  # passes -> 1
        # Only correctness and code-quality are re-dispatched (stamped pass=1);
        # security's re-dispatch "fails to persist" (the documented degradation
        # path) — its pass-0 artifact is now the ONLY stale one.
        for name in ("critic_correctness.json", "critic_code_quality.json"):
            proc = self._persist(root, env, name, json.dumps(_CLEAN))
            self.assertEqual(proc.returncode, 0, proc.stdout)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        ids = [d["id"] for d in out["blocking"] if d["id"].startswith("critic-stale:")]
        self.assertEqual(ids, ["critic-stale:security"])

    def test_exactly_the_dissenting_lens_is_named(self):
        root, env = self._make_run()
        raws = [json.dumps(_CLEAN), json.dumps(_CLEAN),
                json.dumps(_critic(dim_no=("SECURITY",)))]
        for name, raw in zip(_ARTIFACTS, raws):
            self.assertEqual(self._persist(root, env, name, raw).returncode, 0)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        ids = [d["id"] for d in out["blocking"]
               if d["id"].startswith("dimension-dissent:")]
        self.assertEqual(ids, ["dimension-dissent:security"])


class TestCriticArtifactCurrencyE2E(_RunDirMixin, unittest.TestCase):
    """S5 (Task 4 Step 1): the spec's two-pass scenario against a real ctxstore
    run dir — pass-1 CLEAN artifacts must NOT read as fresh lenses on pass 2."""

    def test_stale_clean_artifacts_block_on_pass_two(self):
        root, env = self._make_run()
        self._persist_clean(root, env)          # stamped pass=0 by the real block
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "OK")   # pass 0: fresh
        self._advance(root, env, "REFINE")                   # passes -> 1
        out = self._gate(root, env)                          # critics never re-saw this tree
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        ids = {d["id"] for d in out["blocking"]}
        self.assertEqual(ids & {"critic-stale:correctness",
                                "critic-stale:code-quality",
                                "critic-stale:security"},
                         {"critic-stale:correctness", "critic-stale:code-quality",
                          "critic-stale:security"})

    def test_stale_red_artifact_still_blocks(self):
        # The asymmetry pin: a stale RED artifact keeps the run red — never
        # "fixed" into passing by the currency check.
        root, env = self._make_run()
        raws = [json.dumps(_CRITICAL), json.dumps(_CLEAN), json.dumps(_CLEAN)]
        for name, raw in zip(_ARTIFACTS, raws):
            self.assertEqual(self._persist(root, env, name, raw).returncode, 0)
        self._advance(root, env, "REFINE")
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")

    def test_fresh_stamps_after_refine_are_accepted(self):
        # The fix must not over-fire: re-dispatched critics are stamped with
        # the new pass and the run goes green again.
        root, env = self._make_run()
        self._persist_clean(root, env)
        self._advance(root, env, "REFINE")
        self._persist_clean(root, env)          # stamped pass=1 now
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "OK")

    def test_unstamped_artifacts_at_pass_zero_are_accepted(self):
        # Upgrade-resume (fold T4-F4): a v1.5.1-era artifact carries no stamp;
        # at pass 0 it can only be from this run's first VERIFIED — accepted.
        root, env = self._make_run()
        init = "from scripts import ctxstore\n"
        for name, dim in zip(_ARTIFACTS, ("CORRECTNESS", "CODE-QUALITY", "SECURITY")):
            init += ("ctxstore.write_artifact('.atlas', 'RUN', '%s', %s)\n"
                     % (name, json.dumps(_CLEAN)))
        proc = subprocess.run([sys.executable, "-c", init], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "OK")


class TestStageOrderE2E(_RunDirMixin, unittest.TestCase):
    """S10: a tree mutated AFTER verification turns OUTPUT red — folded into
    merged_critic.json BEFORE final_status, and written back so the residual
    list can show it. A clean ledger stays green (the regression guard)."""

    def _green_merged(self, root, env):
        self._persist_clean(root, env)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "OK")
        for stage in ("INTENT_CAPTURED", "TRIAGED", "GROUNDED", "CODED", "VERIFIED"):
            self._advance(root, env, stage)

    def test_coded_after_verified_turns_output_red(self):
        root, env = self._make_run()
        self._green_merged(root, env)
        self._advance(root, env, "CODED")   # the tree mutated AFTER verification
        out = self._output(root, env)
        self.assertEqual(out["status"], "UNVERIFIED")
        merged = json.loads((root / ".atlas" / "RUN" / "merged_critic.json").read_text())
        self.assertIn("stale-verdict", [d["id"] for d in merged["defects"]])
        self.assertEqual(merged["verdict"], "FAIL")

    def test_a_crash_after_refine_turns_output_red(self):
        # H6 (review MINOR-6): the ledger ENDS at REFINE when this block runs —
        # the forced refine never re-entered CODED, so nothing verified the tree
        # as it now stands. The unit pins assert the fold; this is the only place
        # the real OUTPUT heredoc executes, so it is the only place that shows
        # the printed status.
        root, env = self._make_run()
        self._green_merged(root, env)
        self._advance(root, env, "REFINE")
        out = self._output(root, env)
        self.assertEqual(out["status"], "UNVERIFIED")
        merged = json.loads((root / ".atlas" / "RUN" / "merged_critic.json").read_text())
        self.assertIn("stale-verdict", [d["id"] for d in merged["defects"]])
        self.assertEqual(merged["verdict"], "FAIL")

    def test_clean_ledger_stays_green_at_output(self):
        root, env = self._make_run()
        self._green_merged(root, env)
        out = self._output(root, env)
        self.assertEqual(out["status"], "OK")

    def test_honest_refine_ledger_stays_green_at_output(self):
        # The S10 regression guard (plan Step 6): VERIFIED → REFINE → CODED →
        # VERIFIED → OUTPUT is the legitimate loop and must NOT fire.
        root, env = self._make_run()
        self._persist_clean(root, env)
        self._gate(root, env)
        for stage in ("INTENT_CAPTURED", "TRIAGED", "GROUNDED", "CODED", "VERIFIED"):
            self._advance(root, env, stage)
        self._advance(root, env, "REFINE")
        self._persist_clean(root, env)      # pass-1 critics for the second VERIFIED
        self._gate(root, env)
        for stage in ("CODED", "VERIFIED"):
            self._advance(root, env, stage)
        out = self._output(root, env)
        self.assertEqual(out["status"], "OK")


class TestS4Controls(_RunDirMixin, unittest.TestCase):
    def test_control_one_real_critical_still_blocks(self):
        root, env = self._make_run()
        raws = [json.dumps(_CRITICAL), json.dumps(_CLEAN), json.dumps(_CLEAN)]
        for name, raw in zip(_ARTIFACTS, raws):
            proc = self._persist(root, env, name, raw)
            self.assertEqual(proc.returncode, 0, proc.stdout)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        self.assertIn("C1", [d["id"] for d in out["blocking"]])

    def test_control_three_clean_critics_stay_ok(self):
        root, env = self._make_run()
        for name in _ARTIFACTS:
            proc = self._persist(root, env, name, json.dumps(_CLEAN))
            self.assertEqual(proc.returncode, 0, proc.stdout)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "OK")
        self.assertEqual(out["blocking"], [])


class TestReservedIdsEndToEnd(_RunDirMixin, unittest.TestCase):
    """H4 (v1.5.2.1): a critic claiming an ORCHESTRATOR id deletes its own
    CRITICAL from the refine loop, because those ids are fenced OUT of the coder
    re-dispatch (``TestRefineSkipsOrchestratorDefects`` above pins that fence).

    So the raw-critic gate reserves exactly ``ORCHESTRATOR_DEFECT_IDS`` — driven
    here through the REAL Step-3.4 block, not through ``quality`` directly, so
    the pin covers the SKILL's wiring and not only the pure core.

    The second half is the fail-open direction and it is the more important one:
    reserving ``runcheck``/``docs-naming``/``empty-diff``/``out-of-scope:*`` was
    the release's *fourth* manufactured RED, avoided. The correctness critic is
    handed ``runcheck`` evidence BY NAME, so ``{"id": "runcheck"}`` is a
    plausible HONEST emission; rejecting it would burn the one sanctioned
    re-dispatch and can land at ``critic-missing:<lens>`` on a green tree.
    """

    def _with_id(self, defect_id):
        return json.dumps(_critic(dim_no=("SECURITY",), verdict="FAIL", defects=[{
            "id": defect_id, "category": "SECURITY", "severity": "CRITICAL",
            "location": "a.py:1", "fix": "f"}]))

    def test_an_orchestrator_id_is_rejected_and_never_persisted(self):
        from scripts import floorsynth
        for did in sorted(floorsynth.ORCHESTRATOR_DEFECT_IDS):
            with self.subTest(id=did):
                root, env = self._make_run()
                name = "critic_security.json"
                proc = self._persist(root, env, name, self._with_id(did))
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("CRITIC_SCHEMA_ERRORS", proc.stdout)
                self.assertIn(did, proc.stdout)
                self.assertFalse((root / ".atlas" / "RUN" / name).exists())

    def test_the_run_ends_unverified_when_a_critic_forges_an_orchestrator_id(self):
        root, env = self._make_run()
        for name in ("critic_correctness.json", "critic_code_quality.json"):
            self.assertEqual(
                self._persist(root, env, name, json.dumps(_CLEAN)).returncode, 0)
        proc = self._persist(root, env, "critic_security.json",
                             self._with_id("stale-verdict"))
        self.assertEqual(proc.returncode, 2, proc.stdout)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "UNVERIFIED")
        self.assertEqual(out["critics_loaded"], "2/3")
        self.assertIn("critic-missing:security", [d["id"] for d in out["blocking"]])

    def test_FAIL_OPEN_a_floor_id_outside_the_orchestrator_set_still_persists(self):
        """The honest direction. These ids are coder-actionable, a critic's
        ``fix`` is already trusted by design, and forging one is byte-identical
        to an honest ``C1`` — so reserving them buys nothing and costs a lens."""
        for did in ("runcheck", "docs-naming", "empty-diff",
                    'out-of-scope:"lib/x.py"', "C1", "S3", "Q7"):
            with self.subTest(id=did):
                root, env = self._make_run()
                name = "critic_security.json"
                proc = self._persist(root, env, name, self._with_id(did))
                self.assertEqual(proc.returncode, 0, proc.stdout)
                self.assertIn("PERSISTED", proc.stdout)
                self.assertTrue((root / ".atlas" / "RUN" / name).exists())

    def test_FAIL_OPEN_three_clean_critics_are_unaffected_by_the_reservation(self):
        """The blast-radius control: adding the reservation must not disturb a
        run in which nobody claimed anything."""
        root, env = self._make_run()
        self._persist_clean(root, env)
        out = self._gate(root, env)
        self.assertEqual(out["provisional_status"], "OK")
        self.assertEqual(out["blocking"], [])


class TestStep34PassesTheOrchestratorNamespace(unittest.TestCase):
    """The wiring itself, pinned by AST rather than by substring: the Step-3.4
    call must pass ``reserved_ids=floorsynth.ORCHESTRATOR_DEFECT_IDS``. A pin
    that only asserted the call HAPPENS would survive deleting the keyword."""

    def _tree(self):
        import ast
        return ast.parse(_VALIDATE_BLOCK.replace("$ATLAS_SESSION_ID", "SID"))

    def test_the_call_passes_reserved_ids_by_keyword(self):
        import ast
        calls = [n for n in ast.walk(self._tree())
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "enforce_critic_schema"]
        self.assertEqual(len(calls), 1)
        kw = {k.arg: k.value for k in calls[0].keywords}
        self.assertIn("reserved_ids", kw, "the reservation was dropped from Step 3.4")
        self.assertEqual(ast.unparse(kw["reserved_ids"]),
                         "floorsynth.ORCHESTRATOR_DEFECT_IDS")
        self.assertEqual(len(calls[0].args), 1, "the critic is still the sole positional")

    def test_the_block_imports_floorsynth(self):
        import ast
        names = set()
        for n in ast.walk(self._tree()):
            if isinstance(n, ast.ImportFrom):
                names |= {a.name for a in n.names}
        self.assertIn("floorsynth", names)

    def test_the_reserved_set_excludes_every_coder_actionable_floor_id(self):
        """The fourth-manufactured-RED guard, at the wiring level: whatever the
        orchestrator set grows to, it must never swallow a coder-actionable id."""
        from scripts import floorsynth
        for did in ("runcheck", "docs-naming", "empty-diff"):
            self.assertNotIn(did, floorsynth.ORCHESTRATOR_DEFECT_IDS)
        self.assertFalse(
            [d for d in floorsynth.out_of_scope_defects(["lib/x.py"], ["src"])
             if d["id"] in floorsynth.ORCHESTRATOR_DEFECT_IDS])


class TestCriticRoleFilesInstructTheIdFormat(unittest.TestCase):
    """The reservation is only safe if the id format is actually INSTRUCTED —
    before v1.5.2.1 no role file said anything about ``id`` (``C1``/``Q1``/``S1``
    appear only inside a JSON example, and ``references/schemas.json``'s
    ``critic`` shape constrains no ``id``). Fold F7 made this a precondition.
    """

    ROLES = {"correctness-critic.md": "C", "code-quality-critic.md": "Q",
             "security-critic.md": "S", "integration-critic.md": "S"}

    def _text(self, name):
        return (REPO / "agents" / name).read_text(encoding="utf-8")

    def test_each_role_file_instructs_its_own_id_prefix(self):
        for name, letter in self.ROLES.items():
            with self.subTest(role=name):
                flat = " ".join(self._text(name).split())
                self.assertIn("`id`", flat, "%s never mentions the id field" % name)
                self.assertIn("`%s1`" % letter, flat,
                              "%s does not instruct its own id prefix" % name)

    def test_each_role_file_forbids_the_orchestrator_namespace(self):
        for name in self.ROLES:
            with self.subTest(role=name):
                flat = " ".join(self._text(name).split())
                for token in ("evidence-incomplete", "critic-schema", "stale-verdict",
                              "critic-missing:", "critic-stale:", "dimension-dissent:"):
                    self.assertIn(token, flat,
                                  "%s does not name %s as reserved" % (name, token))
                self.assertIn("Never claim an id the orchestrator synthesizes", flat)

    def test_the_instruction_covers_every_reserved_id(self):
        """Non-vacuity: the prose must name every family the code reserves, so
        the two cannot drift. Iterating the constant here is the CHECK, not the
        pin — the pin is the literal token list above."""
        from scripts import floorsynth
        for name in self.ROLES:
            flat = " ".join(self._text(name).split())
            for did in sorted(floorsynth.ORCHESTRATOR_DEFECT_IDS):
                family = did.split(":", 1)[0] + ":" if ":" in did else did
                with self.subTest(role=name, id=did):
                    self.assertIn(family, flat)

    def test_no_instructed_id_collides_with_a_reserved_one(self):
        """Fold Step 4 — the collision check, over the real role files: every id
        a critic is told to emit, and every id its worked example uses, must be
        outside the reserved set."""
        from scripts import floorsynth
        for name, letter in self.ROLES.items():
            for n in range(1, 40):
                with self.subTest(role=name, id="%s%d" % (letter, n)):
                    self.assertNotIn("%s%d" % (letter, n),
                                     floorsynth.ORCHESTRATOR_DEFECT_IDS)
            for block in self._text(name).split("```json")[1:]:
                obj = json.loads(block.split("```", 1)[0])
                for d in obj.get("defects", []):
                    with self.subTest(role=name, example=d["id"]):
                        self.assertNotIn(d["id"], floorsynth.ORCHESTRATOR_DEFECT_IDS)


if __name__ == "__main__":
    unittest.main()
