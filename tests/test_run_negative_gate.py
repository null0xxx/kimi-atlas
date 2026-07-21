"""Unit tests for scripts.run_negative_gate — the red-team negative-gate driver.

The driver's two impure seams — ``invoke_kimi`` (shells to Kimi) and ``sast_scan``
(shells to semgrep via ``scripts.sast.scan``) — are monkeypatched throughout, so this
whole suite, including the end-to-end ``process_fixture`` / ``main`` paths, runs with
**neither Kimi nor semgrep** and is safe under ``make ci``. Fixtures are synthesized in
throwaway temp dirs; ``tests/fixtures/`` is never touched.

Coverage:

* pure helpers — fixture discovery, frontmatter strip, lens mapping, prompt build,
  evidence summary, JSON extraction, deterministic-blocker detection (now including a
  blocking SAST finding), diff→file split, the SAST-fixture marker, and the
  verdict-comparison (`evaluate_outcome`) for every branch;
* the ``sast_scan`` wrapper — delegates to ``scripts.sast.scan`` and fails open to []
  on any raise;
* the full pipeline — `process_fixture` with real deterministic lenses (a trivial
  passing unittest fixture), a mocked critic, and a mocked SAST floor, proving good→OK,
  a blocking bad→UNVERIFIED-on-the-right-lens, a rubber-stamp bad→FAIL, a wrong-lens
  bad→FAIL, a deterministically-red bad→FAIL before Kimi is ever called, a
  **deterministic-sast fixture blocked by the floor with NO critic dispatched**, that
  same fixture **failing when the floor is empty**, and **bad_security failing if its
  vuln is no longer semgrep-clean**;
* `main` — exit 0 when all match (including a SAST-floor fixture in the matrix),
  non-zero on a rubber stamp, non-zero on no fixtures.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from scripts import run_negative_gate as rng


# ---------------------------------------------------------------------------
# Fixture synthesis helpers (never touch tests/fixtures/)
# ---------------------------------------------------------------------------
_MOD_PY = "def add(a, b):\n    return a + b\n"
_TEST_PY = (
    "import unittest\n"
    "from mod import add\n\n\n"
    "class AddTests(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(add(2, 3), 5)\n"
)


def _write_fixture(
    parent: pathlib.Path,
    name: str,
    *,
    intent: str,
    expected_verdict: str,
    expected_lens: str | None,
    verify_cmd: str = "python3 -m unittest test_mod",
    scope_paths: list[str] | None = None,
    mod_py: str = _MOD_PY,
    extra_manifest: dict | None = None,
) -> pathlib.Path:
    """Create a deterministically-green fixture dir and return its path.

    ``extra_manifest`` merges extra keys into ``fixture.json`` (e.g.
    ``{"expected_blocker": "deterministic-sast"}``) so a SAST-floor fixture can be
    synthesized without a bespoke writer.
    """
    fx = parent / name
    fx.mkdir(parents=True)
    (fx / "mod.py").write_text(mod_py, encoding="utf-8")
    (fx / "test_mod.py").write_text(_TEST_PY, encoding="utf-8")
    manifest = {
        "intent": intent,
        "success_criteria": ["add returns the sum of its two arguments"],
        "verify_cmd": verify_cmd,
        "scope_paths": scope_paths if scope_paths is not None else ["mod.py", "test_mod.py"],
        "expected_verdict": expected_verdict,
        "expected_lens": expected_lens,
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    (fx / "fixture.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return fx


def _write_sast_fixture(parent: pathlib.Path, name: str = "bad_security_sast") -> pathlib.Path:
    """Create a deterministically-green fixture marked as a SAST-floor proof.

    Its code is a trivial passing add() (semgrep is mocked in this suite, so the file
    content need not actually trip a rule), but its ``scope_paths`` are distinctively
    named (``shellcmd.py``) so a keyed fake ``sast_scan`` can return a blocking finding
    for THIS fixture and ``[]`` for the mod.py judgment fixtures in the same matrix.
    """
    fx = parent / name
    fx.mkdir(parents=True)
    (fx / "shellcmd.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (fx / "test_shellcmd.py").write_text(
        "import unittest\n"
        "from shellcmd import add\n\n\n"
        "class ShellcmdTests(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n",
        encoding="utf-8",
    )
    manifest = {
        "intent": "run a shell command",
        "success_criteria": ["add returns the sum of its two arguments"],
        "verify_cmd": "python3 -m unittest test_shellcmd",
        "scope_paths": ["shellcmd.py", "test_shellcmd.py"],
        "expected_verdict": "UNVERIFIED",
        "expected_lens": "SECURITY",
        "expected_blocker": "deterministic-sast",
    }
    (fx / "fixture.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return fx


def _sast_hit(location: str = "mod.py:2", severity: str = "HIGH") -> list[dict]:
    """A canonical blocking SECURITY defect as scripts.sast.scan would emit it."""
    return [
        {
            "id": "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
            "category": "SECURITY",
            "severity": severity,
            "location": location,
            "fix": "Found subprocess with shell=True; use shell=False instead.",
        }
    ]


def _marker_sast(scope_paths, work_dir, *, timeout_s: int = 0) -> list[dict]:
    """A fake sast_scan: a blocking SECURITY hit iff a scope path names ``shellcmd``.

    Lets one fake drive a mixed matrix — the SAST-floor fixture (``shellcmd.py``) is
    flagged; the mod.py judgment fixtures come back clean.
    """
    if any("shellcmd" in p for p in (scope_paths or [])):
        return _sast_hit("shellcmd.py:5")
    return []


def _ok_critic_json() -> str:
    """kimi stdout for a clean critic (wrapped in prose + a fence to test extraction)."""
    obj = {"dimensions": {"CORRECTNESS": "yes"}, "defects": [], "verdict": "OK"}
    return "Here is my review.\n```json\n" + json.dumps(obj) + "\n```\nDone."


def _blocking_critic_json(category: str, severity: str = "HIGH") -> str:
    """kimi stdout for a critic that blocks on ``category`` at ``severity``."""
    defect = {
        "id": "D1",
        "category": category,
        "severity": severity,
        "location": "mod.py:2",
        "fix": "fix the defect",
    }
    obj = {"dimensions": {category: "no"}, "defects": [defect], "verdict": "FAIL"}
    return "Reasoning...\n" + json.dumps(obj)


def _marker_kimi(prompt: str, timeout_s: int = 0) -> str:
    """A fake invoke_kimi that keys its critic off an intent marker in the prompt.

    ``INJECT_BLOCK_<LENS>`` in the packet intent -> a blocking defect on that lens;
    otherwise a clean OK critic. Lets a single fake drive a whole matrix run.
    """
    if "INJECT_BLOCK_CORRECTNESS" in prompt:
        return _blocking_critic_json("CORRECTNESS", "HIGH")
    if "INJECT_BLOCK_SECURITY" in prompt:
        return _blocking_critic_json("SECURITY", "CRITICAL")
    if "INJECT_BLOCK_CODE-QUALITY" in prompt:
        return _blocking_critic_json("CODE-QUALITY", "HIGH")
    return _ok_critic_json()


_AGENTS_DIR = rng._ROOT / "agents"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class ExtractLastJsonTests(unittest.TestCase):
    def test_plain_object(self) -> None:
        self.assertEqual(rng.extract_last_json('{"a": 1}'), {"a": 1})

    def test_fenced_with_surrounding_prose(self) -> None:
        text = 'thinking\n```json\n{"verdict": "OK"}\n```\ndone'
        self.assertEqual(rng.extract_last_json(text), {"verdict": "OK"})

    def test_returns_last_of_several(self) -> None:
        text = '{"n": 1} noise {"n": 2} tail {"n": 3}'
        self.assertEqual(rng.extract_last_json(text), {"n": 3})

    def test_nested_braces(self) -> None:
        obj = {"dimensions": {"CORRECTNESS": "no"}, "defects": [{"id": "x"}]}
        self.assertEqual(rng.extract_last_json("pre " + json.dumps(obj)), obj)

    def test_braces_inside_string_literal_ignored(self) -> None:
        # A "}" inside a JSON string must not close the object early.
        text = 'x {"fix": "use } carefully"} y'
        self.assertEqual(rng.extract_last_json(text), {"fix": "use } carefully"})

    def test_escaped_quote_in_string(self) -> None:
        text = r'{"fix": "say \"hi\" now"}'
        self.assertEqual(rng.extract_last_json(text), {"fix": 'say "hi" now'})

    def test_last_valid_when_trailing_is_broken(self) -> None:
        text = '{"good": 1} then {broken'
        self.assertEqual(rng.extract_last_json(text), {"good": 1})

    def test_no_json_raises(self) -> None:
        with self.assertRaises(ValueError):
            rng.extract_last_json("no json here at all")


class StripFrontmatterTests(unittest.TestCase):
    def test_strips_leading_block(self) -> None:
        text = "---\nname: c\ntools: Read\n---\n# Body\ncontent\n"
        self.assertEqual(rng.strip_frontmatter(text), "# Body\ncontent\n")

    def test_no_frontmatter_returned_unchanged(self) -> None:
        text = "# Body only\nno fence\n"
        self.assertEqual(rng.strip_frontmatter(text), text)

    def test_unterminated_frontmatter_returned_unchanged(self) -> None:
        text = "---\nname: c\nno closing fence\n"
        self.assertEqual(rng.strip_frontmatter(text), text)

    def test_bom_prefix_handled(self) -> None:
        text = "﻿---\nname: c\n---\nBody\n"
        self.assertEqual(rng.strip_frontmatter(text), "Body\n")


class LensMappingTests(unittest.TestCase):
    def test_all_three_map(self) -> None:
        self.assertEqual(rng.lens_to_critic_name("CORRECTNESS"), "correctness-critic")
        self.assertEqual(rng.lens_to_critic_name("CODE-QUALITY"), "code-quality-critic")
        self.assertEqual(rng.lens_to_critic_name("SECURITY"), "security-critic")

    def test_unknown_lens_raises(self) -> None:
        with self.assertRaises(ValueError):
            rng.lens_to_critic_name("NONSENSE")

    def test_all_critic_role_files_exist(self) -> None:
        for lens in rng.JUDGMENT_LENSES:
            path = _AGENTS_DIR / (rng.lens_to_critic_name(lens) + ".md")
            self.assertTrue(path.is_file(), f"missing critic role file: {path}")


class LensesToExerciseTests(unittest.TestCase):
    def test_good_exercises_all_three(self) -> None:
        self.assertEqual(
            rng.lenses_to_exercise({"expected_lens": None}), list(rng.JUDGMENT_LENSES)
        )

    def test_bad_exercises_only_expected(self) -> None:
        self.assertEqual(
            rng.lenses_to_exercise({"expected_lens": "SECURITY"}), ["SECURITY"]
        )


class IsBadFixtureTests(unittest.TestCase):
    def test_unverified_is_bad(self) -> None:
        self.assertTrue(rng.is_bad_fixture({"expected_verdict": "UNVERIFIED"}))

    def test_ok_is_good(self) -> None:
        self.assertFalse(rng.is_bad_fixture({"expected_verdict": "OK"}))


class IsSastFixtureTests(unittest.TestCase):
    def test_marker_true(self) -> None:
        self.assertTrue(
            rng.is_sast_fixture(
                {"expected_verdict": "UNVERIFIED", "expected_blocker": "deterministic-sast"}
            )
        )

    def test_absent_marker_false(self) -> None:
        self.assertFalse(rng.is_sast_fixture({"expected_verdict": "UNVERIFIED"}))

    def test_other_marker_false(self) -> None:
        self.assertFalse(rng.is_sast_fixture({"expected_blocker": "judgment-critic"}))


class SastScanWrapperTests(unittest.TestCase):
    def test_delegates_to_scripts_sast_scan(self) -> None:
        sentinel = _sast_hit("a.py:1")
        with mock.patch.object(rng.sast, "scan", return_value=sentinel) as m:
            got = rng.sast_scan(["a.py", "test_a.py"], "/work", timeout_s=42)
        self.assertEqual(got, sentinel)
        m.assert_called_once_with(["a.py", "test_a.py"], "/work", timeout_s=42)

    def test_fails_open_on_raise(self) -> None:
        # sast.scan is contractually fail-open, but the wrapper double-guards so an
        # unexpected raise can never crash the gate.
        with mock.patch.object(rng.sast, "scan", side_effect=RuntimeError("boom")):
            self.assertEqual(rng.sast_scan(["a.py"], "/work"), [])


class BuildPromptTests(unittest.TestCase):
    def test_prompt_contains_all_sections(self) -> None:
        manifest = {"intent": "do X", "success_criteria": ["crit one", "crit two"]}
        prompt = rng.build_critic_prompt("ROLE BODY", manifest, "DIFFTEXT", "EVIDENCE")
        self.assertIn("ROLE BODY", prompt)
        self.assertIn("## PACKET", prompt)
        self.assertIn("Intent: do X", prompt)
        self.assertIn("crit one", prompt)
        self.assertIn("crit two", prompt)
        self.assertIn("## DIFF", prompt)
        self.assertIn("DIFFTEXT", prompt)
        self.assertIn("## DETERMINISTIC EVIDENCE", prompt)
        self.assertIn("EVIDENCE", prompt)
        self.assertTrue(prompt.rstrip().endswith("Return ONLY the critic JSON."))

    def test_no_criteria_renders_placeholder(self) -> None:
        prompt = rng.build_critic_prompt("R", {"intent": "x", "success_criteria": []}, "d", "e")
        self.assertIn("(none provided)", prompt)


class SummarizeEvidenceTests(unittest.TestCase):
    def _det(self) -> dict:
        return {
            "runcheck": {
                "ok": True,
                "returncode": 0,
                "test_count": 3,
                "new_tests_collected": True,
                "revert_red": False,
            },
            "runcheck_green": True,
            "lint_defects": [],
            "reqcoverage_defects": [],
        }

    def test_correctness_includes_advisory_lines(self) -> None:
        text = rng.summarize_evidence(self._det(), "CORRECTNESS")
        self.assertIn("TEST-ADEQUACY", text)
        self.assertIn("REQUIREMENTS-COVERAGE", text)
        self.assertIn("runcheck_green=True", text)

    def test_security_states_empty_grep_floor(self) -> None:
        text = rng.summarize_evidence(self._det(), "SECURITY")
        self.assertIn("NONE", text)

    def test_code_quality_reports_lint(self) -> None:
        text = rng.summarize_evidence(self._det(), "CODE-QUALITY")
        self.assertIn("lint_deliverable", text)


class DiscoverFixturesTests(unittest.TestCase):
    def test_good_first_then_bad_sorted_and_ignores_non_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in ("bad_security", "good", "bad_correctness"):
                d = root / name
                d.mkdir()
                (d / "fixture.json").write_text("{}", encoding="utf-8")
            (root / "not_a_fixture").mkdir()  # no fixture.json -> ignored
            (root / "loose.txt").write_text("x", encoding="utf-8")
            names = [p.name for p in rng.discover_fixtures(root)]
            self.assertEqual(names, ["good", "bad_correctness", "bad_security"])

    def test_missing_root_returns_empty(self) -> None:
        self.assertEqual(rng.discover_fixtures("/no/such/dir/at/all"), [])


class DeterministicBlockersTests(unittest.TestCase):
    def _green(self) -> dict:
        return {
            "runcheck_green": True,
            "runcheck": {"ok": True, "test_count": 2, "new_tests_collected": True, "returncode": 0},
            "lint_defects": [],
            "reqcoverage_defects": [],
            "pathcheck_defects": [],
            "sast_defects": [],
            "docs_clean": True,
        }

    def test_all_green_no_blockers(self) -> None:
        self.assertEqual(rng.deterministic_blockers(self._green()), [])

    def test_red_runcheck_blocks(self) -> None:
        det = self._green()
        det["runcheck_green"] = False
        det["runcheck"] = {"ok": False, "test_count": 0, "new_tests_collected": False, "returncode": 1}
        problems = rng.deterministic_blockers(det)
        self.assertEqual(len(problems), 1)
        self.assertIn("runcheck not green", problems[0])

    def test_blocking_pathcheck_defect_blocks(self) -> None:
        det = self._green()
        det["pathcheck_defects"] = [
            {"category": "CORRECTNESS", "severity": "CRITICAL", "location": "ghost.py"}
        ]
        problems = rng.deterministic_blockers(det)
        self.assertTrue(any("pathcheck_defects" in p for p in problems))

    def test_medium_lint_is_not_a_blocker(self) -> None:
        det = self._green()
        det["lint_defects"] = [
            {"category": "CODE-QUALITY", "severity": "MEDIUM", "location": "mod.py:1"}
        ]
        self.assertEqual(rng.deterministic_blockers(det), [])

    def test_blocking_sast_defect_blocks(self) -> None:
        # A blocking SAST finding on a judgment fixture means the SAST floor (not the
        # critic) would fire — the fixture no longer isolates the SECURITY judgment lens.
        det = self._green()
        det["sast_defects"] = _sast_hit("linecount.py:15")
        problems = rng.deterministic_blockers(det)
        self.assertTrue(any("sast_defects" in p and "SECURITY" in p for p in problems))

    def test_medium_sast_is_not_a_blocker(self) -> None:
        det = self._green()
        det["sast_defects"] = [
            {"category": "SECURITY", "severity": "MEDIUM", "location": "x.py:1"}
        ]
        self.assertEqual(rng.deterministic_blockers(det), [])

    def test_dirty_docs_blocks(self) -> None:
        det = self._green()
        det["docs_clean"] = False
        self.assertTrue(any("docs" in p for p in rng.deterministic_blockers(det)))


class SplitChangedFilesTests(unittest.TestCase):
    def test_classifies_test_vs_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            (root / "test_mod.py").write_text("y = 2\n", encoding="utf-8")
            diff = "+++ mod.py\n+++ test_mod.py\n+++ /dev/null\n"
            changed, tests = rng.split_changed_files(diff, root, "test_*.py")
            self.assertEqual(sorted(changed), ["mod.py"])
            self.assertEqual(sorted(tests), ["test_mod.py"])

    def test_absent_paths_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            diff = "+++ ghost.py\n"
            changed, tests = rng.split_changed_files(diff, tmp, "test_*.py")
            self.assertEqual(changed, {})
            self.assertEqual(tests, {})


class EvaluateOutcomeTests(unittest.TestCase):
    def _merged(self, defects: list[dict]) -> dict:
        return {"dimensions": {}, "defects": defects, "verdict": "OK"}

    def _defect(self, category: str, severity: str = "HIGH") -> dict:
        return {"id": "d", "category": category, "severity": severity, "location": "m.py:1", "fix": "f"}

    def test_good_clean_passes(self) -> None:
        m = {"expected_verdict": "OK", "expected_lens": None}
        o = rng.evaluate_outcome("good", m, "OK", self._merged([]), [])
        self.assertTrue(o.passed)
        self.assertFalse(o.rubber_stamp)

    def test_good_with_blocking_fails(self) -> None:
        m = {"expected_verdict": "OK", "expected_lens": None}
        o = rng.evaluate_outcome("good", m, "UNVERIFIED", self._merged([self._defect("CORRECTNESS")]), [])
        self.assertFalse(o.passed)

    def test_bad_blocked_on_expected_lens_passes(self) -> None:
        m = {"expected_verdict": "UNVERIFIED", "expected_lens": "CORRECTNESS"}
        o = rng.evaluate_outcome(
            "bad_correctness", m, "UNVERIFIED", self._merged([self._defect("CORRECTNESS")]), []
        )
        self.assertTrue(o.passed)
        self.assertIn("blocked by CORRECTNESS", o.message)

    def test_bad_blocked_on_wrong_lens_fails(self) -> None:
        m = {"expected_verdict": "UNVERIFIED", "expected_lens": "SECURITY"}
        o = rng.evaluate_outcome(
            "bad_security", m, "UNVERIFIED", self._merged([self._defect("CORRECTNESS")]), []
        )
        self.assertFalse(o.passed)
        self.assertFalse(o.rubber_stamp)
        self.assertIn("expected a blocking defect on SECURITY", o.message)

    def test_bad_returning_ok_is_rubber_stamp(self) -> None:
        m = {"expected_verdict": "UNVERIFIED", "expected_lens": "CORRECTNESS"}
        o = rng.evaluate_outcome("bad_correctness", m, "OK", self._merged([]), [])
        self.assertFalse(o.passed)
        self.assertTrue(o.rubber_stamp)
        self.assertIn("RUBBER STAMP", o.message)

    def test_bad_with_deterministic_blocker_fails_before_lens_check(self) -> None:
        m = {"expected_verdict": "UNVERIFIED", "expected_lens": "CORRECTNESS"}
        o = rng.evaluate_outcome("bad_correctness", m, None, self._merged([]), ["runcheck not green (...)"])
        self.assertFalse(o.passed)
        self.assertFalse(o.rubber_stamp)
        self.assertIn("deterministic gate fired", o.message)


# ---------------------------------------------------------------------------
# End-to-end pipeline (real deterministic lenses, mocked Kimi)
# ---------------------------------------------------------------------------
class ProcessFixtureTests(unittest.TestCase):
    def _run(self, fx: pathlib.Path, *, sast_defects=()) -> rng.Outcome:
        """Run process_fixture with the SAST floor mocked (default: no findings).

        Callers wrap this in their own ``invoke_kimi`` patch; both seams are therefore
        mocked, so the pipeline runs with neither Kimi nor semgrep.
        """
        with mock.patch.object(rng, "sast_scan", return_value=list(sast_defects)):
            return rng.process_fixture(fx, _AGENTS_DIR, mem_limit_mb=0, runcheck_timeout_s=60)

    def test_good_all_clean_yields_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "good",
                intent="add returns the sum", expected_verdict="OK", expected_lens=None,
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi) as m:
                out = self._run(fx)
            self.assertTrue(out.passed, out.message)
            self.assertEqual(out.status, "OK")
            self.assertEqual(m.call_count, 3)  # all three judgment lenses exercised

    def test_bad_correctness_blocks_on_correctness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_correctness",
                intent="add INJECT_BLOCK_CORRECTNESS", expected_verdict="UNVERIFIED",
                expected_lens="CORRECTNESS",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi) as m:
                out = self._run(fx)
            self.assertTrue(out.passed, out.message)
            self.assertEqual(out.status, "UNVERIFIED")
            self.assertEqual(m.call_count, 1)  # only the expected_lens critic runs
            self.assertIn("CORRECTNESS", out.fired_lenses)

    def test_bad_security_blocks_on_security(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_security",
                intent="add INJECT_BLOCK_SECURITY", expected_verdict="UNVERIFIED",
                expected_lens="SECURITY",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi):
                out = self._run(fx)
            self.assertTrue(out.passed, out.message)
            self.assertEqual(out.status, "UNVERIFIED")
            self.assertIn("SECURITY", out.fired_lenses)

    def test_rubber_stamp_bad_returning_ok_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_correctness",
                intent="add (critic will rubber-stamp this)", expected_verdict="UNVERIFIED",
                expected_lens="CORRECTNESS",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi):
                out = self._run(fx)
            self.assertFalse(out.passed)
            self.assertTrue(out.rubber_stamp)
            self.assertEqual(out.status, "OK")

    def test_bad_blocked_on_wrong_lens_fails(self) -> None:
        # A security fixture whose (mocked) security critic reports a CORRECTNESS
        # defect: the intended eye did not fire -> FAIL, not a rubber stamp.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_security",
                intent="add INJECT_BLOCK_CORRECTNESS", expected_verdict="UNVERIFIED",
                expected_lens="SECURITY",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi):
                out = self._run(fx)
            self.assertFalse(out.passed)
            self.assertFalse(out.rubber_stamp)
            self.assertIn("expected a blocking defect on SECURITY", out.message)

    def test_deterministically_red_bad_fails_without_calling_kimi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_correctness",
                intent="add INJECT_BLOCK_CORRECTNESS", expected_verdict="UNVERIFIED",
                expected_lens="CORRECTNESS",
                verify_cmd="python3 -m unittest test_does_not_exist",  # -> runcheck RED
            )
            guard = mock.Mock(side_effect=AssertionError("kimi must not be called"))
            with mock.patch.object(rng, "invoke_kimi", guard):
                out = self._run(fx)
            self.assertFalse(out.passed)
            self.assertFalse(out.rubber_stamp)
            self.assertIn("deterministic gate fired", out.message)
            guard.assert_not_called()

    # -- SAST floor (deterministic-sast) fixtures --------------------------------
    def test_deterministic_sast_fixture_blocked_by_floor(self) -> None:
        # The SAST floor blocks a mechanically detectable vuln with NO judgment critic.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_security_sast",
                intent="run a shell command", expected_verdict="UNVERIFIED",
                expected_lens="SECURITY",
                extra_manifest={"expected_blocker": "deterministic-sast"},
            )
            guard = mock.Mock(
                side_effect=AssertionError("kimi must not be called for a SAST-floor fixture")
            )
            with mock.patch.object(rng, "invoke_kimi", guard):
                out = self._run(fx, sast_defects=_sast_hit("mod.py:2"))
            self.assertTrue(out.passed, out.message)
            self.assertEqual(out.status, "UNVERIFIED")
            self.assertIn("SECURITY", out.fired_lenses)
            self.assertIn("SAST floor", out.message)
            guard.assert_not_called()

    def test_deterministic_sast_fixture_fails_when_floor_empty(self) -> None:
        # If sast.scan finds nothing (semgrep absent, or the vuln left the ruleset),
        # the floor cannot prove the block -> FAIL, still without dispatching Kimi.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_security_sast",
                intent="run a shell command", expected_verdict="UNVERIFIED",
                expected_lens="SECURITY",
                extra_manifest={"expected_blocker": "deterministic-sast"},
            )
            guard = mock.Mock(side_effect=AssertionError("kimi must not be called"))
            with mock.patch.object(rng, "invoke_kimi", guard):
                out = self._run(fx, sast_defects=[])
            self.assertFalse(out.passed)
            self.assertIn("SAST floor did not block", out.message)
            guard.assert_not_called()

    def test_bad_security_not_sast_clean_fails_before_kimi(self) -> None:
        # bad_security is a SECURITY *critic* proof: its seeded vuln MUST stay
        # semgrep-clean. If the floor fires on it, the fixture no longer isolates the
        # judgment lens -> FAIL before any Kimi dispatch (a signal to reseed a subtler
        # vuln). This is the "assert bad_security is semgrep-clean" guard.
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_security",
                intent="add INJECT_BLOCK_SECURITY", expected_verdict="UNVERIFIED",
                expected_lens="SECURITY",
            )
            guard = mock.Mock(
                side_effect=AssertionError("kimi must not run once the floor already fired")
            )
            with mock.patch.object(rng, "invoke_kimi", guard):
                out = self._run(fx, sast_defects=_sast_hit("mod.py:2"))
            self.assertFalse(out.passed)
            self.assertFalse(out.rubber_stamp)
            self.assertIn("deterministic gate fired", out.message)
            self.assertIn("SECURITY", out.message)
            guard.assert_not_called()

    def test_bad_security_sast_clean_still_exercises_critic(self) -> None:
        # The normal bad_security path: SAST clean, so the SECURITY *critic* is what
        # must block (mirrors make negative-gate on the reseeded fixture).
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "bad_security",
                intent="add INJECT_BLOCK_SECURITY", expected_verdict="UNVERIFIED",
                expected_lens="SECURITY",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi) as m:
                out = self._run(fx, sast_defects=[])
            self.assertTrue(out.passed, out.message)
            self.assertEqual(out.status, "UNVERIFIED")
            self.assertIn("SECURITY", out.fired_lenses)
            self.assertEqual(m.call_count, 1)  # the SECURITY critic did the blocking

    def test_good_fixture_tripping_sast_floor_fails(self) -> None:
        # A good fixture whose SAST floor unexpectedly fires is correctly blocked and
        # fails as "unexpectedly blocked" (the floor feeds the merged SECURITY dim).
        with tempfile.TemporaryDirectory() as tmp:
            fx = _write_fixture(
                pathlib.Path(tmp), "good",
                intent="add returns the sum", expected_verdict="OK", expected_lens=None,
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi):
                out = self._run(fx, sast_defects=_sast_hit("mod.py:2"))
            self.assertFalse(out.passed)
            self.assertEqual(out.status, "UNVERIFIED")
            self.assertIn("SECURITY", out.fired_lenses)


# ---------------------------------------------------------------------------
# CLI (main)
# ---------------------------------------------------------------------------
class MainTests(unittest.TestCase):
    def _main_captured(self, argv) -> tuple[str, int]:
        """Run rng.main under captured stdout+stderr; return (captured_text, rc).

        main() prints progress + a PASS/FAIL report to stdout and the deliberately
        alarming ``RUBBER STAMP …`` / ``no fixtures found …`` lines to stderr. Capturing
        both keeps a *green* suite quiet (F10) — assertions read the returned rc / buffer
        instead of letting the module write to the real console.
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rng.main(argv)
        return out.getvalue() + err.getvalue(), rc

    def test_main_output_is_captured_not_leaked(self) -> None:
        # F10 guard: main()'s deliberately-alarming report lines (``RUBBER STAMP …``,
        # ``no fixtures found …``) must land in OUR buffer, never the real console.
        # The empty fixtures-root uses a self-cleaning TemporaryDirectory so this guard
        # test does not itself re-introduce the F9 /tmp-dir leak it exists to police.
        with tempfile.TemporaryDirectory() as tmp:
            buf, rc = self._main_captured(
                ["--fixtures-root", tmp, "--agents-dir", str(_AGENTS_DIR)]
            )
        self.assertNotEqual(rc, 0)
        self.assertIn("no fixtures found", buf)  # the noisy line is in OUR buffer

    def test_no_fixtures_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, rc = self._main_captured(["--fixtures-root", tmp, "--agents-dir", str(_AGENTS_DIR)])
            self.assertNotEqual(rc, 0)

    def test_full_matrix_all_pass_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _write_fixture(root, "good", intent="add sum", expected_verdict="OK", expected_lens=None)
            _write_fixture(
                root, "bad_correctness", intent="add INJECT_BLOCK_CORRECTNESS",
                expected_verdict="UNVERIFIED", expected_lens="CORRECTNESS",
            )
            _write_fixture(
                root, "bad_security", intent="add INJECT_BLOCK_SECURITY",
                expected_verdict="UNVERIFIED", expected_lens="SECURITY",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi), \
                    mock.patch.object(rng, "sast_scan", side_effect=_marker_sast):
                _, rc = self._main_captured([
                    "--fixtures-root", str(root), "--agents-dir", str(_AGENTS_DIR),
                    "--mem-limit-mb", "0", "--runcheck-timeout", "60",
                ])
            self.assertEqual(rc, 0)

    def test_matrix_with_sast_floor_fixture_all_pass_exits_zero(self) -> None:
        # A mixed matrix: a judgment SECURITY fixture (must stay SAST-clean, blocked by
        # the critic) AND a deterministic-sast fixture (blocked by the floor, no critic).
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _write_fixture(root, "good", intent="add sum", expected_verdict="OK", expected_lens=None)
            _write_fixture(
                root, "bad_security", intent="add INJECT_BLOCK_SECURITY",
                expected_verdict="UNVERIFIED", expected_lens="SECURITY",
            )
            _write_sast_fixture(root, "bad_security_sast")
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi), \
                    mock.patch.object(rng, "sast_scan", side_effect=_marker_sast):
                _, rc = self._main_captured([
                    "--fixtures-root", str(root), "--agents-dir", str(_AGENTS_DIR),
                    "--mem-limit-mb", "0", "--runcheck-timeout", "60",
                ])
            self.assertEqual(rc, 0)

    def test_rubber_stamp_in_matrix_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _write_fixture(root, "good", intent="add sum", expected_verdict="OK", expected_lens=None)
            # No marker in intent -> the single critic rubber-stamps this bad fixture.
            _write_fixture(
                root, "bad_correctness", intent="add (no defect surfaced)",
                expected_verdict="UNVERIFIED", expected_lens="CORRECTNESS",
            )
            with mock.patch.object(rng, "invoke_kimi", side_effect=_marker_kimi), \
                    mock.patch.object(rng, "sast_scan", side_effect=_marker_sast):
                _, rc = self._main_captured([
                    "--fixtures-root", str(root), "--agents-dir", str(_AGENTS_DIR),
                    "--mem-limit-mb", "0", "--runcheck-timeout", "60",
                ])
            self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
