"""Pins for the four v1.5.2.1 documentation fictions — claims that described
behaviour the code does not have.

A fiction in this repo is not a cosmetic problem. ``references/rubric.md`` is
handed to the judgment critics verbatim (``rubric.lens_section``) and
``skills/atlas/SKILL.md`` is a PROGRAM an LLM executes, so a sentence describing
a safety net that does not exist is read as an instruction to rely on it. Each
class below therefore pins the *behaviour* first and the corrected prose second,
so the pair cannot drift apart again:

1. ``TestNoSecurityGrepInQuality`` — rubric.md's Lens 3 header and body claimed
   ``quality.py`` kept "a static grep for known secret/eval/unsafe-shell
   patterns" behind semgrep. ``scripts/quality.py`` contains no such code and
   never did: ``lint_deliverable`` emits CODE-QUALITY and TEST-ADEQUACY only.
2. (V7's "no origin filter" fiction is pinned in ``tests/test_rubric.py``, next
   to the rest of the V7 prose guards.)
3. ``TestDegradationLadderHasNoFabricatedCriticFallback`` — the ladder told the
   orchestrator to "fall back to the deterministic-only critic (rebuild
   critic.json from runcheck/pathcheck), then continue" after a malformed critic.
   The shipped Step 3.4 does the opposite: never persist, let
   ``critic-missing:<lens>`` CRITICAL fire, degrade to UNVERIFIED.
4. ``TestCiLanesAreNotUnderstated`` — ``sast-floor.yml``'s header asserted the
   local build shell has no semgrep (false on the box this was written on, where
   semgrep 1.169.0 resolves and ``TestScanRealSemgrep`` runs rather than skips),
   and AGENTS.md implied ``make ci`` covers CI when it covers one lane of three.

Nothing here touches a target repository, so no assertion in this file can
manufacture a RED on an honest review — these guard the plugin's own tree only.
"""
from __future__ import annotations

import pathlib
import re
import unittest

from scripts import floorsynth, quality

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    # utf-8-sig, not utf-8, by the project's standing ruling on this class
    # (`scripts/syntaxlens.py`'s `_loads_json_bom`): a BOM-prefixed doc must never
    # turn a prose pin into a RED on an otherwise honest tree.
    # HONEST SCOPE: measured, this is defensive only — prepending a real BOM to
    # every file read here leaves all of these assertions green even under plain
    # utf-8, because none of them anchors at offset 0. It is here so that a future
    # pin which DOES anchor at the start of a file inherits the safe default.
    return (_ROOT / rel).read_text(encoding="utf-8-sig")


class TestNoSecurityGrepInQuality(unittest.TestCase):
    """`quality.lint_deliverable` emits no SECURITY defect, and the docs agree."""

    # A source file dense with exactly the patterns the fictional grep claimed to
    # find. If any grep is ever added, the behavioural test below starts failing
    # and forces the rubric to be updated in the same change.
    _HOSTILE = (
        'AWS_SECRET_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
        'password = "hunter2"\n'
        'eval(user_supplied)\n'
        'exec(request.body)\n'
        'subprocess.run(cmd, shell=True)\n'
        'os.system("rm -rf " + path)\n'
        'open("../../../../etc/passwd")\n'
        'cursor.execute("SELECT * FROM t WHERE u=" + name)\n'
        'child_process.exec(req.query.q)\n'
        'private_key = "-----BEGIN RSA PRIVATE KEY-----"\n'
    )

    def test_lint_deliverable_emits_no_security_defect(self):
        defects = quality.lint_deliverable(
            {"app.py": self._HOSTILE},
            {"tests/test_app.py": "def test_x():\n    assert True\n"},
            {"debug_tokens": ["TODO", "FIXME", "XXX", "print("], "test_glob": "tests/*.py"},
        )
        self.assertEqual(
            [d for d in defects if d.get("category") == "SECURITY"], [],
            "quality.lint_deliverable emitted a SECURITY defect; rubric.md's Lens 3 "
            "section must be updated in the same change to describe the new floor",
        )

    def test_the_hostile_fixture_is_not_vacuous(self):
        """The fixture must reach the scanner at all — otherwise the test above
        proves nothing. One configured debug token IS found in it, so the input
        is demonstrably scanned end to end."""
        defects = quality.lint_deliverable(
            {"app.py": self._HOSTILE + "    # TODO: fix\n"},
            {"tests/test_app.py": "assert True\n"},
            {"debug_tokens": ["TODO"], "test_glob": "tests/*.py"},
        )
        self.assertTrue(defects, "the fixture never reached lint_deliverable")
        self.assertEqual({d["category"] for d in defects}, {"CODE-QUALITY"})

    def test_only_two_categories_are_reachable(self):
        """Across the whole input space the module exercises, the emitted
        categories are exactly CODE-QUALITY and TEST-ADEQUACY."""
        seen = set()
        for changed, tests in (
            ({"a.py": "TODO\nprint(x)\n"}, {"t.py": "x"}),   # debug tokens
            ({"a.py": "clean\n"}, {}),                        # missing tests
            ({"a.py": self._HOSTILE}, {"t.py": "x"}),         # security patterns
        ):
            for d in quality.lint_deliverable(
                changed, tests, {"debug_tokens": ["TODO", "print("], "test_glob": "t*.py"}
            ):
                seen.add(d["category"])
        self.assertEqual(seen, {"CODE-QUALITY", "TEST-ADEQUACY"})

    def test_no_grep_machinery_in_the_module(self):
        """No regex/`in`-scan over a hard-coded security pattern list exists."""
        src = _read("scripts/quality.py")
        code = "\n".join(
            line for line in src.splitlines()
            if not line.lstrip().startswith("#")
        )
        for token in ("import re", "re.compile", "re.search", "_SECRET", "_UNSAFE"):
            self.assertNotIn(
                token, code,
                f"scripts/quality.py grew {token!r} — if a SECURITY grep landed, "
                f"references/rubric.md Lens 3 must say so",
            )

    def test_rubric_lens3_does_not_claim_a_quality_grep(self):
        text = _read("references/rubric.md")
        lens3 = text.split("## Lens 3 — SECURITY", 1)[1].split("\n## ", 1)[0]
        for phrase in ("static grep", "quality.py` static", "nor the grep"):
            self.assertNotIn(
                phrase, lens3,
                f"rubric.md Lens 3 again claims a quality.py security grep "
                f"({phrase!r}); scripts/quality.py has none",
            )
        self.assertIn("no deterministic floor at all", lens3,
                      "Lens 3 must state the honest semgrep-absent degraded shape")

    def test_quality_docstring_does_not_claim_lens_3(self):
        doc = quality.__doc__ or ""
        self.assertNotIn("3 (SECURITY)", doc)
        self.assertIn("NO SECURITY defect", doc)


class TestDegradationLadderHasNoFabricatedCriticFallback(unittest.TestCase):
    """A malformed critic must land at `critic-missing:<lens>`, never at a
    synthesized stand-in artifact."""

    def _ladder(self) -> str:
        text = _read("skills/atlas/SKILL.md")
        return text.split("## Degradation ladder", 1)[1].split("\n## ", 1)[0]

    def _critic_bullet(self) -> str:
        """Just the malformed-critic rung, so the phrase pins cannot be tripped
        by an unrelated bullet legitimately using the same words."""
        bullets = re.split(r"\n(?=- \*\*)", self._ladder())
        matches = [b for b in bullets if b.lstrip().startswith("- **Critic output")]
        self.assertEqual(len(matches), 1,
                         "the malformed-critic rung was renamed or removed")
        return matches[0]

    def test_a_missing_critic_is_a_blocking_critical(self):
        """The behaviour the ladder must describe, driven through the real core."""
        defects = floorsynth.critics_missing_defects({})
        self.assertEqual(len(defects), 3, "one per critic artifact")
        for d in defects:
            self.assertEqual(d["severity"], "CRITICAL")
            self.assertIn(d["id"], floorsynth.ORCHESTRATOR_DEFECT_IDS)
        # A loaded lens does not fire; the floor is not indiscriminate.
        one = floorsynth.critics_missing_defects({"critic_security.json": {"defects": []}})
        self.assertEqual(len(one), 2)
        self.assertNotIn("critic-missing:security", [d["id"] for d in one])

    def test_the_ladder_offers_no_fabricated_substitute(self):
        bullet = self._critic_bullet()
        for phrase in ("deterministic-only critic",
                       "rebuild `critic.json`",
                       "then continue"):
            self.assertNotIn(
                phrase, bullet,
                f"the degradation ladder again offers {phrase!r} for a malformed "
                f"critic; Step 3.4 forbids persisting a rejected judgment and the "
                f"run must degrade to UNVERIFIED via critic-missing:<lens>",
            )

    def test_the_ladder_names_the_real_landing(self):
        bullet = self._critic_bullet()
        for phrase in ("never persist", "critic-missing:<lens>", "CRITICAL", "UNVERIFIED"):
            self.assertIn(phrase, bullet,
                          f"the malformed-critic rung no longer names {phrase!r}")

    def test_the_bullet_slicer_is_not_vacuous(self):
        """The slicer must really isolate one rung — a pin that silently matched
        the empty string would assert nothing."""
        bullet = self._critic_bullet()
        self.assertIn("Critic output", bullet)
        self.assertNotIn("Coder timeout", bullet)
        self.assertNotIn("Scout returns", bullet)


class TestCiLanesAreNotUnderstated(unittest.TestCase):
    """`make ci` covers one of three lanes; no doc may assert a box's toolchain."""

    def _workflow_stems(self) -> set[str]:
        return {p.stem for p in (_ROOT / ".github" / "workflows").glob("*.yml")}

    def test_every_workflow_lane_is_named_in_agents_md(self):
        agents = _read("AGENTS.md")
        stems = self._workflow_stems()
        self.assertGreaterEqual(len(stems), 3, "workflow discovery found nothing")
        for stem in stems:
            self.assertIn(
                f"{stem}.yml", agents,
                f"CI lane {stem}.yml is not named in AGENTS.md — a contributor "
                f"reading 'make ci mirrors CI' would ship a red lane",
            )

    def test_agents_md_does_not_equate_make_ci_with_ci(self):
        agents = _read("AGENTS.md")
        self.assertNotIn(
            "`make ci` mirrors `.github/workflows/check.yml` (Python 3.12). "
            "Everything must stay green.",
            agents,
            "AGENTS.md again presents make ci as the whole of CI",
        )
        # Whitespace-normalized: the sentence is line-wrapped in the doc.
        self.assertIn("necessary, not sufficient", " ".join(agents.split()))

    def test_makefile_does_not_claim_to_mirror_github_actions(self):
        mk = _read("Makefile")
        self.assertNotIn(
            "mirrors GitHub Actions", mk,
            "the ci target again claims to mirror all of GitHub Actions; it "
            "mirrors check.yml only",
        )

    def test_no_lane_asserts_a_local_toolchain_fact(self):
        """Neither toolchain lane may state which binaries a dev box has.

        Both headers used to. Measured on the build shell this was written on:
        semgrep 1.169.0, node and php all resolved while ruby and gofmt did not,
        so `sast-floor.yml`'s "the local build shell ... ha[s] no semgrep" and
        `native-floor.yml`'s "no node/ruby/php/go" were both false. The lanes'
        real guarantee never depended on that claim — it is the hard assert.
        """
        for lane, banned in ((".github/workflows/sast-floor.yml", "have no semgrep"),
                             (".github/workflows/native-floor.yml", "have no node")):
            wf = _read(lane)
            header = "\n".join(l for l in wf.splitlines() if l.startswith("#"))
            self.assertNotIn(
                banned, header,
                f"{lane} again asserts a dev box's toolchain ({banned!r}) — not a "
                f"fact a workflow file can make, and one that was measurably false",
            )
            self.assertIn("skipUnless", header,
                          f"{lane} no longer says why the lane exists")
        wf = _read(".github/workflows/sast-floor.yml")
        for step in ("pip install semgrep==", "sast.semgrep_path()"):
            self.assertIn(step, wf, f"the sast lane lost {step!r}")

    def test_the_lane_still_hard_asserts_rather_than_skips(self):
        wf = _read(".github/workflows/sast-floor.yml")
        self.assertRegex(wf, r"sys\.exit\(0 if sast\.semgrep_path\(\) else 1\)")
        self.assertRegex(wf, re.compile(r"^\s+run: \|?\s*$.*tests\.test_sast",
                                        re.M | re.S))


if __name__ == "__main__":
    unittest.main()
