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
        body = _VALIDATE_BLOCK.replace("${KIMI_SESSION_ID}", "RUN")
        body = body.replace('NAME = "critic_correctness.json"', 'NAME = "%s"' % name)
        body = body.replace("r'''<the critic's returned JSON text>'''", "r'''" + raw + "'''")
        return subprocess.run([sys.executable, "-c", body], cwd=root, env=env,
                              capture_output=True, text=True)

    def _gate(self, root, env):
        body = _STEP45_BLOCK.replace("${KIMI_SESSION_ID}", "RUN")
        proc = subprocess.run([sys.executable, "-c", body], cwd=root, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        return json.loads(last)

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
        body = _REFINE_BLOCK.replace("${KIMI_SESSION_ID}", "RUN")
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


if __name__ == "__main__":
    unittest.main()
