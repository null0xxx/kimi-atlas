# Runtime Token-Optimization — Phase 0–2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`)
> syntax for tracking.

**Goal:** Close three confirmed false-green defects in the shipped verification harness, resolve two
SKILL contradictions, and build the three pure cores the token-optimization driver will consume —
without changing a single token of what any critic sees.

**Architecture:** Spec →
[`docs/superpowers/specs/2026-07-24-runtime-token-optimization-design.md`](../specs/2026-07-24-runtime-token-optimization-design.md).
This plan covers **Phases 0, 1 and 2 only**. Phase 0 extracts the SKILL's Step-4/5 gate marshalling into
a pure module `scripts/floorsynth.py` and adds two new blocking syntheses. Phase 1 is SKILL prose only.
Phase 2 builds three pure cores that nothing calls yet. Phase 3 (`scripts/atlasrun.py`), Phase 4
(`scripts/packet.py`) and Phase 5 (M4′) get **their own plans** after Phase 3's hard measurement gate,
exactly as P1/P2/P3 each did.

**Tech Stack:** Python 3.12 stdlib only. `unittest`. No new dependencies, ever.

## Global Constraints

Copied verbatim from `AGENTS.md` — every task's requirements implicitly include these.

- **stdlib-only Python 3.12**, `from __future__ import annotations`, pure cores + thin I/O "hands",
  long module docstrings citing invariants, CLI = `main(argv=None) -> int` + `sys.exit(main())`,
  plugin root via `pathlib.Path(__file__).resolve().parents[1]` + sys.path shim.
- **Output idiom:** `sys.stdout.write` / `sys.stderr.write` in `skill*` modules — the atlas harness
  lints changed files for `print(` as a debug token.
- **Tests:** stdlib `unittest` only, `tests/test_<module>.py` per `scripts/<module>.py`, tempfile
  fixture trees, in-process `main()` via `redirect_stdout/stderr`, behavior AND failure-path assertions.
- **Doc gates:** new `.md` = lowercase kebab-case AND individually markdown-linked from
  `references/*.md` or `README.md`. If the tracked-doc count changes, update `AGENTS.md:122` —
  `tests/test_tracked_docs_count.py` enforces it.
- **Determinism:** generated artifacts sorted, stable-keyed, timestamp-free.
- **`make ci` must be EXIT 0 after every task.** Baseline at plan time: **1193 tests**, 5 skipped
  locally (ruby/gofmt absent).
- **FROZEN — do not open in this plan:** `scripts/verdict.py`. The pure gate is not touched.
- **Elite-model mandate:** every dispatched implementer and reviewer subagent runs on **opus**.

---

## File Structure

| File | Responsibility | Phase |
|---|---|---|
| `scripts/floorsynth.py` **(new)** | Pure synthesis of the deterministic floor's blocking defects + the two-phase merge/validate cycle. No I/O. | 0 |
| `tests/test_floorsynth.py` **(new)** | The nine-condition gate-agreement matrix; the empty-diff and missing-critic regressions. | 0 |
| `skills/atlas/SKILL.md` | Step 4+5 heredoc calls `floorsynth`; E1/E2 resolved; the registry read path deleted. | 0, 1 |
| `tests/test_skill_floor_contract.py` **(new)** | Text pins for the resolved contradictions + the deleted read path. | 1 |
| `scripts/rubric.py` | Gains the pure `lens_section` slicer alongside the existing constants. | 2 |
| `tests/test_rubric.py` | Golden-slice matrix over all six dimensions. | 2 |
| `scripts/contextgraph.py` | Gains pure `render_for_injection`. **Not wired** into `graph_lookup` in this plan. | 2 |
| `scripts/ctxstore.py` | Gains pure `valid_run_id` + the hardened `write_artifact_confined` hand. | 2 |

---

# PHASE 0 — the floor synthesiser

### Task 1: `floorsynth` — transcribe the existing marshalling, behaviour-identical

**Files:**
- Create: `scripts/floorsynth.py`
- Create: `tests/test_floorsynth.py`

**Interfaces:**
- Consumes: `scripts.verdict.merge`, `scripts.quality.enforce_critic_schema` (both unchanged).
- Produces: `script_defects_from(evidence: dict) -> list[dict]`,
  `synth_runcheck(rc: dict) -> list[dict]`, `synth_docs(docs_clean: bool) -> list[dict]`.

**Why this shape:** `skills/atlas/SKILL.md:601-631` reads three evidence keys with `ev["..."]`
(mandatory — a missing key raises today) and three with `ev.get(..., [])` (optional, for older evidence
files). A blanket `.get` would silently drop a whole floor lens; keeping the distinction and turning the
mandatory-key failure into a **blocking defect** is strictly safer than both today's crash and a silent
skip. `lintlens_advisory` is **deliberately never merged** — that is the P3 firewall
(`skills/atlas/SKILL.md:621-623`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_floorsynth.py
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
              "lintlens_advisory": []}
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
        ev = {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": []}
        self.assertEqual(floorsynth.script_defects_from(ev), [])

    def test_missing_mandatory_key_is_a_blocking_defect_not_a_crash(self):
        ev = {"reqcoverage_defects": [], "pathcheck_defects": []}   # lint_defects absent
        out = floorsynth.script_defects_from(ev)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], "evidence-incomplete")
        self.assertEqual(out[0]["severity"], "CRITICAL")
        self.assertIn("lint_defects", out[0]["fix"])


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

    def test_dirty_docs_synthesize_a_critical(self):
        out = floorsynth.synth_docs(False)
        self.assertEqual((out[0]["id"], out[0]["category"], out[0]["severity"]),
                         ("docs-naming", "CODE-QUALITY", "CRITICAL"))

    def test_clean_docs_synthesize_nothing(self):
        self.assertEqual(floorsynth.synth_docs(True), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_floorsynth -v`
Expected: `ModuleNotFoundError: No module named 'scripts.floorsynth'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/floorsynth.py
"""Pure synthesis of the deterministic floor's blocking defects (SKILL Step 4).

Every ``verdict.gate`` failure condition MUST also become a blocking defect inside
``merged_critic.json`` — otherwise ``should_refine``/``final_status`` (which read
ONLY the merged critic) disagree with ``gate``, and a run can ship a false
``VERIFIED`` while the fallible critics emit nothing. That marshalling lived as
inline heredoc text in ``skills/atlas/SKILL.md:601-641``, retyped by the model on
every run; a single dropped ``+=`` line silently deleted a whole floor lens with
nothing detecting it. Hoisting it here makes floor completeness a ``make ci``
invariant instead of a per-run transcription lottery.

INVARIANTS THIS MODULE PRESERVES
- ``scripts/verdict.py`` is FROZEN and is not modified: this module only ever
  ADDS entries to the ``script_defects`` list handed to the pure ``verdict.merge``.
- The P3 advisory firewall: ``lintlens_advisory`` is DELIBERATELY never merged and
  never reaches ``gate_results`` (``skills/atlas/SKILL.md:621-623``). Advisory lint
  can never block.
- No I/O, no subprocess, no clock: importing this module has zero side effects.
- Defect ``category`` is always one of ``rubric.DIMENSIONS`` for anything this
  module synthesises BEFORE validation, because ``quality.enforce_critic_schema``
  rejects any other category. The lone ``SCHEMA``-category defect is appended
  AFTER validation, exactly as the SKILL does, so it is never validated.
"""
from __future__ import annotations

from scripts import quality, verdict

# Evidence keys the SKILL reads with ``ev[...]`` — absence is a real fault.
MANDATORY_EVIDENCE_KEYS: tuple[str, ...] = (
    "lint_defects",
    "reqcoverage_defects",
    "pathcheck_defects",
)
# Evidence keys the SKILL reads with ``ev.get(..., [])`` — absence is legitimate
# for an evidence file written by an older plugin version.
OPTIONAL_EVIDENCE_KEYS: tuple[str, ...] = (
    "sast_defects",
    "astlens_defects",
    "syntaxlens_defects",
)


def script_defects_from(evidence: dict) -> list[dict]:
    """The deterministic lens defect-lists, in ``skills/atlas/SKILL.md:602-620`` order.

    ``lintlens_advisory`` is never included (the P3 firewall). A missing MANDATORY
    key yields one blocking ``evidence-incomplete`` defect rather than raising or —
    far worse — silently contributing nothing.
    """
    missing = [k for k in MANDATORY_EVIDENCE_KEYS if k not in (evidence or {})]
    if missing:
        return [{
            "id": "evidence-incomplete",
            "category": "DOES-IT-RUN",
            "severity": "CRITICAL",
            "location": "det_evidence.json",
            "fix": "re-run the deterministic lenses; absent evidence key(s): "
                   + ", ".join(sorted(missing)),
        }]
    out: list[dict] = []
    for key in MANDATORY_EVIDENCE_KEYS + OPTIONAL_EVIDENCE_KEYS:
        out += list(evidence.get(key) or [])
    return out


def synth_runcheck(rc: dict, verify_cmd: str = "") -> list[dict]:
    """Mirror ``gate``'s runcheck condition as a blocking defect (SKILL :624-627)."""
    from scripts import runcheck

    if runcheck.green(rc or {}):
        return []
    return [{
        "id": "runcheck",
        "category": "DOES-IT-RUN",
        "severity": "CRITICAL",
        "location": "verify_cmd (%s)" % (verify_cmd or ""),
        "fix": "make build+tests green: exit 0, test_count>0, new/changed tests collected",
    }]


def synth_docs(docs_clean: bool) -> list[dict]:
    """Mirror ``gate``'s ``docs_clean`` condition as a blocking defect (SKILL :628-631)."""
    if docs_clean:
        return []
    return [{
        "id": "docs-naming",
        "category": "CODE-QUALITY",
        "severity": "CRITICAL",
        "location": "changed .md docs",
        "fix": "fix artifact naming / inventory-drift so check_artifact_naming passes",
    }]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_floorsynth -v`
Expected: `OK` — 8 tests.

- [ ] **Step 5: Run the whole gate**

Run: `make ci`
Expected: `EXIT 0`, 1201 tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/floorsynth.py tests/test_floorsynth.py
git commit -F - <<'EOF'
feat(floorsynth): pure deterministic-floor synthesiser (transcribed, behaviour-identical)

script_defects_from / synth_runcheck / synth_docs lift the Step-4 marshalling out
of the SKILL heredoc, where a dropped `+=` line silently deleted a whole floor lens
with nothing detecting it. The P3 advisory firewall is preserved by construction:
lintlens_advisory is never merged. A missing MANDATORY evidence key becomes a
blocking `evidence-incomplete` defect instead of raising or silently contributing
nothing. verdict.py untouched.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 2: the two NEW blocking syntheses + the nine-condition gate-agreement matrix

**Files:**
- Modify: `scripts/floorsynth.py`
- Modify: `tests/test_floorsynth.py`

**Interfaces:**
- Produces: `empty_diff_defect(diff: str) -> list[dict]`,
  `critics_missing_defects(loaded_artifacts) -> list[dict]`,
  `CRITIC_ARTIFACTS: tuple[tuple[str, str], ...]`.

**Why the categories are what they are — do not change them without re-reading this.**
`quality.enforce_critic_schema` rejects any defect whose `category` is not one of
`rubric.DIMENSIONS` (`scripts/quality.py:78-82`). A `SCHEMA`-category defect added **before**
validation would therefore produce a schema error *about our own synthesised defect*. So:

* `empty-diff` → **`CORRECTNESS`**. Correct semantically, schema-clean, and it additionally fires the
  V7 rule (any CORRECTNESS/SECURITY defect at any severity forces one refine pass), so an empty diff
  drives a re-attempt rather than only a red label.
* `critic-missing:<lens>` → **that lens's own dimension**. A lens that produced no judgment is not a
  clean lens; using its own dimension makes `merged["dimensions"][<lens>] == "no"` — honest — and keeps
  the merged shape schema-valid.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_floorsynth.py, above `if __name__`
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


class TestGateAgreementMatrix(unittest.TestCase):
    """For EVERY deterministic failure condition, gate AND final_status must both
    say UNVERIFIED. This is the standing invariant that floor completeness used to
    lack."""

    GREEN_RC = {"ok": True, "test_count": 3, "new_tests_collected": True}
    ALL_LOADED = ("critic_correctness.json", "critic_code_quality.json", "critic_security.json")

    def _run(self, evidence, diff="--- a/x.py\n+++ b/x.py\n+1\n", loaded=None, docs_clean=True):
        loaded = self.ALL_LOADED if loaded is None else loaded
        sd = floorsynth.script_defects_from(evidence)
        sd += floorsynth.synth_runcheck(evidence.get("runcheck", {}), evidence.get("verify_cmd", ""))
        sd += floorsynth.synth_docs(docs_clean)
        sd += floorsynth.empty_diff_defect(diff)
        sd += floorsynth.critics_missing_defects(loaded)
        merged, schema_errors = floorsynth.merge_and_validate([], sd)
        gate_inputs = {"runcheck": evidence.get("runcheck", {}), "schema_errors": schema_errors,
                       "lint_defects": evidence.get("lint_defects", []),
                       "reqcoverage_defects": evidence.get("reqcoverage_defects", []),
                       "pathcheck_defects": evidence.get("pathcheck_defects", []),
                       "docs_clean": docs_clean}
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
            "empty-diff": dict(evidence=self._clean(), diff=""),
            "critic-missing": dict(evidence=self._clean(), loaded=("critic_security.json",)),
        }
        for name, kwargs in cases.items():
            with self.subTest(condition=name):
                self.assertEqual(self._run(**kwargs), ("UNVERIFIED", "UNVERIFIED"))

    def test_advisory_lint_never_blocks(self):
        adv = [{"lane": "auto", "tool": "ruff", "path": "a.py", "line": 3, "message": "E501"}]
        self.assertEqual(self._run(self._clean(lintlens_advisory=adv)), ("OK", "OK"))


class TestMergeAndValidate(unittest.TestCase):
    def test_malformed_critic_yields_schema_errors_and_a_blocking_merged_critic(self):
        bad = {"dimensions": {"CORRECTNESS": "maybe"}, "defects": [], "verdict": "OK"}
        merged, schema_errors = floorsynth.merge_and_validate([bad], [])
        self.assertTrue(schema_errors)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertTrue(any(d["id"] == "critic-schema" for d in merged["defects"]))

    def test_wellformed_critic_yields_no_schema_error_and_no_synthetic_defect(self):
        good = verdict.merge([], [])
        merged, schema_errors = floorsynth.merge_and_validate([good], [])
        self.assertEqual(schema_errors, [])
        self.assertEqual(merged["defects"], [])
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. python3 -m unittest tests.test_floorsynth -v`
Expected: `AttributeError: module 'scripts.floorsynth' has no attribute 'empty_diff_defect'`.

> **Note for the implementer:** the `empty-diff` arm of
> `test_every_failure_condition_blocks_both_gate_and_final_status` is the reproduction of the
> defect this whole phase exists for. Before writing the implementation, confirm by hand that
> `verdict.gate` returns `"OK"` for an empty diff today — that is the finding, not a test bug.

- [ ] **Step 3: Write the implementation**

```python
# append to scripts/floorsynth.py

# (artifact basename, the rubric dimension that artifact's critic owns).
# skills/atlas/SKILL.md:588 reads exactly these three, in this order.
CRITIC_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("critic_correctness.json", "CORRECTNESS"),
    ("critic_code_quality.json", "CODE-QUALITY"),
    ("critic_security.json", "SECURITY"),
)


def empty_diff_defect(diff: str) -> list[dict]:
    """A captured diff with no content is a BLOCKING CORRECTNESS defect.

    Without this, a run whose coder wrote nothing ships a false ``VERIFIED``:
    ``runsignal.count`` (``scripts/runsignal.py:474-502``) derives
    ``new_tests_collected`` purely from the runner's own output and never sees the
    diff, so an already-green suite satisfies ``runcheck.green``; and
    ``reqcoverage``'s "no diff token overlaps criterion" signal is MEDIUM/
    REQUIREMENTS-COVERAGE, which blocks neither ``gate`` (CRITICAL/HIGH only) nor
    the V7 refine rule (CORRECTNESS/SECURITY only). Category CORRECTNESS is chosen
    deliberately: it is schema-valid AND it fires V7, so an empty diff drives one
    re-attempt rather than only a red label.
    """
    if (diff or "").strip():
        return []
    return [{
        "id": "empty-diff",
        "category": "CORRECTNESS",
        "severity": "CRITICAL",
        "location": "diff.patch (captured from review_root)",
        "fix": "the coder produced no change under scope_paths in review_root — re-dispatch it, "
               "and confirm review_root points at the tree the coder actually wrote to",
    }]


def critics_missing_defects(loaded_artifacts) -> list[dict]:
    """One BLOCKING defect per judgment-critic artifact that failed to load.

    ``skills/atlas/SKILL.md:588-592`` substitutes ``{"dimensions": {}, "defects":
    [], "verdict": "OK"}`` on a read failure, and ``verdict.merge``
    (``scripts/verdict.py:95-98``) then SYNTHESISES all six dimensions as ``yes``.
    ``quality.enforce_critic_schema`` cannot see it, because it only ever validates
    the MERGED shape — so an undispatched or lost critic is indistinguishable from
    a clean lens.

    The category is the MISSING LENS'S OWN dimension, never ``"SCHEMA"``:
    ``enforce_critic_schema`` (``scripts/quality.py:78-82``) rejects any category
    outside ``rubric.DIMENSIONS``, so a ``SCHEMA``-category defect added before
    validation would raise a schema error about this very defect.
    """
    present = set(loaded_artifacts or ())
    out: list[dict] = []
    for name, dimension in CRITIC_ARTIFACTS:
        if name in present:
            continue
        out.append({
            "id": "critic-missing:%s" % dimension.lower(),
            "category": dimension,
            "severity": "CRITICAL",
            "location": ".atlas/<run_id>/%s" % name,
            "fix": "re-dispatch the %s critic and persist its JSON; a lens that produced no "
                   "judgment is never a clean lens" % dimension,
        })
    return out


def merge_and_validate(critics: list[dict], script_defects: list[dict]) -> tuple[dict, list[str]]:
    """The two-phase merge → validate → re-merge cycle (SKILL :633-641).

    Load-bearing: without the re-merge, ``gate`` returns UNVERIFIED (its
    ``schema_errors`` condition) while ``merged_critic.json`` — the artifact OUTPUT
    and ``bench`` actually read — still says OK. The synthesised ``critic-schema``
    defect keeps category ``"SCHEMA"`` and is appended AFTER validation, exactly as
    the SKILL does, so it is never itself validated.
    """
    defects = list(script_defects or [])
    merged = verdict.merge(critics, defects)
    schema_errors = quality.enforce_critic_schema(merged)
    if schema_errors:
        defects.append({
            "id": "critic-schema",
            "category": "SCHEMA",
            "severity": "CRITICAL",
            "location": "merged_critic.json",
            "fix": "critic JSON must satisfy enforce_critic_schema",
        })
        merged = verdict.merge(critics, defects)
    return merged, schema_errors
```

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_floorsynth -v`
Expected: `OK`.

- [ ] **Step 5: Prove the matrix is mutation-catching**

Temporarily delete the line `out += list(evidence.get(key) or [])`'s `sast_defects` entry by editing
`OPTIONAL_EVIDENCE_KEYS` to `("astlens_defects", "syntaxlens_defects")`, then run:

Run: `PYTHONPATH=. python3 -m unittest tests.test_floorsynth -v`
Expected: **FAIL** on `sast-HIGH`. **Revert the mutation** and re-run — expected `OK`.

- [ ] **Step 6: `make ci` + commit**

```bash
make ci   # expected EXIT 0
git add scripts/floorsynth.py tests/test_floorsynth.py
git commit -F - <<'EOF'
feat(floorsynth): close the empty-diff and missing-critic false-green holes

Two new blocking syntheses, both reproduced at HEAD before being fixed:

  empty-diff  — an empty captured diff plus an already-green suite yields
                verdict.gate == "OK" and final_status == "OK" today, because
                runsignal.count never sees the diff and reqcoverage's signal is
                MEDIUM/REQUIREMENTS-COVERAGE, which blocks neither the gate nor V7.
                A run whose coder wrote nothing shipped a false VERIFIED.
  critic-missing:<lens> — a critic artifact that fails to load is substituted with
                an empty OK critic, and verdict.merge then synthesises all six
                dimensions as "yes"; enforce_critic_schema only validates the MERGED
                shape, so an undispatched lens was indistinguishable from a clean one.

Categories are rubric dimensions, never "SCHEMA": enforce_critic_schema rejects any
category outside rubric.DIMENSIONS, so a SCHEMA-category defect added before
validation would raise a schema error about itself. empty-diff is CORRECTNESS so it
also fires V7 and drives one re-attempt; critic-missing uses the missing lens's own
dimension so merged["dimensions"][lens] is honestly "no".

Plus merge_and_validate, owning the two-phase re-merge whose loss would let gate()
say UNVERIFIED while merged_critic.json said OK, and a nine-condition matrix
asserting gate AND final_status agree, with a non-vacuous green control arm.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 3: rewire the SKILL's Step 4+5 heredoc to call `floorsynth`

**Files:**
- Modify: `skills/atlas/SKILL.md:581-651` (the Step 4+5 fenced block)
- Modify: `tests/test_lintlens_firewall.py` — **strengthen, never relax**

**Interfaces:**
- Consumes: everything from Tasks 1–2.
- Produces: no new Python symbols. The heredoc shrinks from ~5,000 B to ~1,300 B.

- [ ] **Step 1: Write the failing test** — pin the new contract before editing the SKILL

```python
# tests/test_skill_floor_contract.py  (new file)
"""The SKILL's Step 4+5 block must DELEGATE to floorsynth, not re-inline it."""
from __future__ import annotations

import pathlib
import re
import unittest

SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills" / "atlas" / "SKILL.md"


class TestStep45Delegates(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_imports_floorsynth(self):
        self.assertIn("from scripts import ctxstore, floorsynth, verdict", self.text)

    def test_calls_every_synthesiser(self):
        for call in ("floorsynth.script_defects_from(", "floorsynth.synth_runcheck(",
                     "floorsynth.synth_docs(", "floorsynth.empty_diff_defect(",
                     "floorsynth.critics_missing_defects(", "floorsynth.merge_and_validate("):
            with self.subTest(call=call):
                self.assertIn(call, self.text)

    def test_marshalling_is_not_re_inlined(self):
        """The `+=` ladder and the hand-rolled synth dicts must be GONE — leaving
        them would recreate the transcription lottery floorsynth exists to end."""
        for gone in ('script_defects += ev["lint_defects"]',
                     'script_defects += ev.get("sast_defects", [])',
                     '"fix": "make build+tests green'):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, self.text)

    def test_records_which_critics_loaded(self):
        self.assertIn("loaded_critics", self.text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_skill_floor_contract -v`
Expected: FAIL on `test_imports_floorsynth`.

- [ ] **Step 3: Replace the Step 4+5 fenced block**

Replace the whole `PYTHONPATH=... python3 - <<'PY' … PY` block at `skills/atlas/SKILL.md:581-651` with:

````markdown
```
PYTHONPATH="${KIMI_SKILL_DIR}/../.." python3 - <<'PY'
import json
from scripts import ctxstore, floorsynth, verdict
run = "${KIMI_SESSION_ID}"
ev = ctxstore.read_artifact(".atlas", run, "det_evidence.json")
diff = ctxstore.read_artifact(".atlas", run, "diff.patch")

# Load the three judgment critics. A missing artifact is NOT a clean lens:
# floorsynth.critics_missing_defects synthesizes a BLOCKING defect for each one
# that fails to load, so an undispatched critic can never read as "yes".
critics, loaded_critics = [], []
for name, _dim in floorsynth.CRITIC_ARTIFACTS:
    try:
        critics.append(ctxstore.read_artifact(".atlas", run, name))
        loaded_critics.append(name)
    except Exception:
        pass

# script_defects = every deterministic gate() failure condition, synthesized as a
# blocking merged defect so should_refine()/final_status() (which read ONLY the
# merged critic) stay in AGREEMENT with gate(). floorsynth owns this marshalling;
# it is unit-tested over all eleven conditions, and lintlens_advisory is
# DELIBERATELY excluded there (the P3 firewall) so advisory lint can never block.
script_defects = floorsynth.script_defects_from(ev)
script_defects += floorsynth.synth_runcheck(ev.get("runcheck", {}), ev.get("verify_cmd", ""))
script_defects += floorsynth.synth_docs(ev.get("docs_clean", True))
script_defects += floorsynth.empty_diff_defect(diff)
script_defects += floorsynth.critics_missing_defects(loaded_critics)

merged, schema_errors = floorsynth.merge_and_validate(critics, script_defects)

# gate() reads these EXACT keys (verdict.gate): runcheck, schema_errors, lint_defects,
# reqcoverage_defects, pathcheck_defects, docs_clean. This is the full PASS bar.
# lintlens_advisory is deliberately ABSENT — the pure gate stays blind to it.
gate_results = {"runcheck": ev["runcheck"], "schema_errors": schema_errors,
                "lint_defects": ev["lint_defects"], "reqcoverage_defects": ev["reqcoverage_defects"],
                "pathcheck_defects": ev["pathcheck_defects"], "docs_clean": ev["docs_clean"]}
status = verdict.gate(merged, gate_results)                 # PURE — "OK" | "UNVERIFIED"
ctxstore.write_artifact(".atlas", run, "merged_critic.json", merged)
ctxstore.write_artifact(".atlas", run, "gate_results.json", gate_results)
blocking = [d for d in merged["defects"] if d.get("severity") in ("CRITICAL", "HIGH")]
print(json.dumps({"provisional_status": status, "schema_errors": schema_errors,
                  "critics_loaded": "%d/3" % len(loaded_critics), "blocking": blocking}))
PY
```
````

- [ ] **Step 4: Strengthen the firewall pin**

`tests/test_lintlens_firewall.py`'s taint-scan asserts every `lintlens_advisory` line inside the
Step-4/5 merge heredoc is a comment. That still holds — the new block mentions it only in comments.
Add one behavioural arm proving the firewall through the real synthesiser:

```python
    def test_floorsynth_never_merges_advisory(self):
        from scripts import floorsynth
        adv = [{"lane": "auto", "tool": "ruff", "path": "a.py", "line": 1, "message": "E501"}]
        ev = {"lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
              "lintlens_advisory": adv}
        self.assertEqual(floorsynth.script_defects_from(ev), [])
```

- [ ] **Step 5: Verify the heredoc is syntactically valid Python**

```bash
PYTHONPATH=. python3 - <<'PY'
import ast, pathlib, re
t = pathlib.Path("skills/atlas/SKILL.md").read_text(encoding="utf-8")
blocks = re.findall(r"python3 - <<'PY'\n(.*?)\nPY\n", t, re.S)
for i, b in enumerate(blocks):
    ast.parse(b.replace("${KIMI_SESSION_ID}", "SID").replace("${KIMI_SKILL_DIR}", "SDIR"))
print("all %d heredocs parse OK" % len(blocks))
PY
```
Expected: `all N heredocs parse OK`.

- [ ] **Step 6: `make ci` + commit**

```bash
make ci   # expected EXIT 0
git add skills/atlas/SKILL.md tests/test_skill_floor_contract.py tests/test_lintlens_firewall.py
git commit -F - <<'EOF'
feat(atlas): Step 4+5 delegates the floor marshalling to floorsynth

The SKILL no longer re-types the gate marshalling on every run. The block shrinks
~5,000 B -> ~1,300 B and, more importantly, floor completeness becomes a make ci
invariant: dropping a lens is now a failing test rather than a silent false green.
The critic read loop records WHICH artifacts loaded and feeds
critics_missing_defects, so a lost critic is blocking instead of clean.

The P3 advisory firewall is preserved two ways: structurally (the taint-scan still
finds lintlens_advisory only in comments) and behaviourally (a new arm proves
floorsynth.script_defects_from drops a non-empty advisory).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

# PHASE 1 — SKILL text only, no new runtime code

### Task 4: resolve E1 and E2, delete the registry read path

**Files:**
- Modify: `skills/atlas/SKILL.md:292-295` (E1), `:690-693` (E2)
- Modify: `tests/test_skill_floor_contract.py`

**Interfaces:** none — prose only. No Python symbol changes.

- [ ] **Step 1: Write the failing pins**

```python
# append to tests/test_skill_floor_contract.py, above `if __name__`

class TestContradictionsResolved(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_e1_advisory_skills_do_not_go_to_critics(self):
        """E1: :292-295 said 'coder and every critic packet'; :557-558 said the critic
        packet is ONLY four items. Resolved toward isolation (F6 anti-anchoring)."""
        self.assertNotIn("and every critic packet", self.text)
        self.assertIn("CODED (elite-coder packet) only", self.text)

    def test_e2_refine_re_enters_coded_in_full(self):
        """E2: safewrap.coder_redispatch_packet returns NO skill body, NO graph and NO
        role body, so it was never 'equivalent' to re-entering CODED."""
        self.assertNotIn("equivalently", self.text)
        self.assertIn("re-enters CODED in full", self.text)

    def test_registry_read_path_is_gone(self):
        """An 80,597 B Read would be 1.4x the whole SKILL body, permanently resident."""
        self.assertNotIn("look\n    them up by name in `references/skill-registry.json`", self.text)
        self.assertNotIn("them up by name in `references/skill-registry.json`", self.text)
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. python3 -m unittest tests.test_skill_floor_contract -v`
Expected: FAIL on all three.

- [ ] **Step 3: Apply the E1 edit**

Replace `skills/atlas/SKILL.md:292-295`:

```markdown
  - **CODED + VERIFIED (coder and every critic packet):** the remaining top-3 results go
    in as *available reference skills* — names + `skills/<name>/` paths + `why` — advisory
    only, it never widens `scope_paths`. When a packet wants one-line descriptions, look
    them up by name in `references/skill-registry.json`.
```

with:

```markdown
  - **CODED (elite-coder packet) only:** the remaining top-3 results go in as
    *available reference skills* — names + `skills/<name>/` paths + `why` + the
    one-line `description` already carried in `.atlas/<run_id>/skills.json` —
    advisory only, it never widens `scope_paths`. They are **not** handed to any
    critic: the critic packet is exactly the four items enumerated at Step 3, and
    that isolation (F6) is what buys anti-anchoring. Never `Read`
    `references/skill-registry.json` into context — it is 80 KB, 1.4× this whole
    skill body, and it would stay resident for the rest of the run.
```

- [ ] **Step 4: Apply the E2 edit**

In `skills/atlas/SKILL.md:690-693`, replace:

```markdown
  wrapper as the Ph2 read path via `safewrap.refine_feedback_block(rc)` (equivalently, assemble the
  whole re-dispatch with `safewrap.coder_redispatch_packet(frozen_packet, fix_items, rc)`): the tails
```

with:

```markdown
  wrapper as the Ph2 read path via `safewrap.refine_feedback_block(rc)`. The re-dispatch
  **re-enters CODED in full** — the coder gets the role body, the ACTIVE skill and a freshly
  recomputed run-state graph again, exactly as on the first pass;
  `safewrap.coder_redispatch_packet(frozen_packet, fix_items, rc)` is the canonical assembler
  for that packet's **fix-feedback fields**, not a smaller substitute for the whole packet
  (it carries no skill body, no graph and no role body). The tails
```

- [ ] **Step 5: Run tests**

Run: `PYTHONPATH=. python3 -m unittest tests.test_skill_floor_contract -v`
Expected: `OK`.

- [ ] **Step 6: `make ci` + commit**

```bash
make ci   # expected EXIT 0
git add skills/atlas/SKILL.md tests/test_skill_floor_contract.py
git commit -F - <<'EOF'
fix(atlas): resolve the two SKILL contradictions; delete the registry read path

E1 — :292-295 sent the advisory top-3 skill list to "coder and every critic packet"
while :557-558 said the critic packet is ONLY {intent+criteria, diff, that critic's
lens, evidence slice}. Resolved toward :557-558: isolation is the anti-anchoring
mechanism (F6), and an advisory list cannot produce, suppress or re-severity a
defect, so removing it is deductively quality-neutral.

E2 — :692-693 offered safewrap.coder_redispatch_packet as "equivalent" to re-entering
CODED, but it returns only {intent, scope_paths, target, fix_instructions,
untrusted_failure_evidence} — no skill body, no graph, no role body. Resolved toward
the superset and documented for what the helper actually is.

M7 (half) — the instruction to look descriptions up in references/skill-registry.json
is deleted: an 80,597 B Read is 1.4x the whole SKILL body and stays resident for the
rest of the run. The driver will carry `description` in skills.json instead.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

# PHASE 2 — pure cores, nothing wired

### Task 5: `rubric.lens_section` — byte-exact per-lens slicing

**Files:**
- Modify: `scripts/rubric.py`
- Create: `tests/test_rubric.py`

**Interfaces:**
- Produces: `lens_section(md_text: str, dimension: str) -> str`.

**Grounding:** the six headings in `references/rubric.md` are at lines 37, 56, 71, 100, 116, 130 and use
an **EM DASH (U+2014)**, e.g. `## Lens 1 — CORRECTNESS  *(judgment lens; …)*`. The slice must terminate
at the next `^## ` — **not** `^## Lens` — or `REQUIREMENTS-COVERAGE` would swallow
`## Per-critic verdict` (:146) and the whole PASS bar (:153).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rubric.py
"""Golden-slice tests for the pure per-lens rubric slicer."""
from __future__ import annotations

import pathlib
import unittest

from scripts import rubric

RUBRIC = pathlib.Path(__file__).resolve().parents[1] / "references" / "rubric.md"


class TestLensSection(unittest.TestCase):
    def setUp(self):
        self.md = RUBRIC.read_text(encoding="utf-8")
        self.slices = {d: rubric.lens_section(self.md, d) for d in rubric.DIMENSIONS}

    def test_every_dimension_yields_a_non_empty_slice(self):
        for d, s in self.slices.items():
            with self.subTest(dimension=d):
                self.assertTrue(s.strip(), "empty slice for %s" % d)

    def test_slice_starts_with_its_own_heading(self):
        for d, s in self.slices.items():
            with self.subTest(dimension=d):
                self.assertRegex(s, r"\A## Lens \d+ — %s" % d)

    def test_slice_contains_no_other_lens_heading(self):
        for d, s in self.slices.items():
            for other in rubric.DIMENSIONS:
                if other == d:
                    continue
                with self.subTest(dimension=d, other=other):
                    self.assertNotIn("— %s" % other, s.split("\n", 1)[1])

    def test_slice_carries_no_gate_knowledge(self):
        """The :17-33 preamble states 'Only CRITICAL and HIGH are blocking … never flip
        final_status'. That is gate knowledge; a single-lens critic must not receive it."""
        for d, s in self.slices.items():
            for banned in ("verdict.gate", "_BLOCKING", "never flip", "final_status",
                           "The PASS bar"):
                with self.subTest(dimension=d, banned=banned):
                    self.assertNotIn(banned, s)

    def test_slices_are_pairwise_disjoint(self):
        for a in rubric.DIMENSIONS:
            for b in rubric.DIMENSIONS:
                if a >= b:
                    continue
                with self.subTest(a=a, b=b):
                    self.assertNotIn(self.slices[a], self.slices[b])
                    self.assertNotIn(self.slices[b], self.slices[a])

    def test_unknown_dimension_returns_empty(self):
        self.assertEqual(rubric.lens_section(self.md, "NOT-A-LENS"), "")

    def test_hyphen_instead_of_em_dash_does_not_match(self):
        """Guards the exact failure mode where every slice silently comes back empty."""
        self.assertEqual(rubric.lens_section("## Lens 1 - CORRECTNESS\nbody\n", "CORRECTNESS"), "")

    def test_terminator_is_any_h2_not_only_a_lens_h2(self):
        md = "## Lens 6 — REQUIREMENTS-COVERAGE\nbody\n\n## Per-critic verdict\nOTHER\n"
        got = rubric.lens_section(md, "REQUIREMENTS-COVERAGE")
        self.assertIn("body", got)
        self.assertNotIn("OTHER", got)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. python3 -m unittest tests.test_rubric -v`
Expected: `AttributeError: module 'scripts.rubric' has no attribute 'lens_section'`.

- [ ] **Step 3: Write the implementation**

```python
# append to scripts/rubric.py — and add `import re` + `from __future__` stays at top

# The per-lens heading form in ``references/rubric.md``: "## Lens <n> — <DIMENSION>",
# where the separator is an EM DASH (U+2014). A hyphen here would silently return an
# empty slice for every dimension, so the character is asserted by tests.
_LENS_HEADING = "## Lens %s — %s"


def lens_section(md_text: str, dimension: str) -> str:
    """Return the ``references/rubric.md`` section for ``dimension``, verbatim.

    The slice runs from that lens's ``## Lens <n> — <DIMENSION>`` heading up to the
    NEXT ``^## `` heading of any kind — never up to the next ``## Lens``, which
    would make the last lens swallow ``## Per-critic verdict`` and the whole PASS
    bar. An unknown dimension, or a heading whose separator is not an em dash,
    returns ``""``; the caller MUST treat an empty slice as a hard failure rather
    than dispatching a critic with no rubric.

    Pure: no I/O. The caller supplies the markdown text.
    """
    if dimension not in DIMENSIONS:
        return ""
    pattern = re.compile(
        r"^## Lens \d+ — %s\b.*?(?=^## |\Z)" % re.escape(dimension),
        re.M | re.S,
    )
    match = pattern.search(md_text or "")
    return match.group(0).rstrip("\n") if match else ""
```

> The `import re` goes at the top of `scripts/rubric.py`, immediately after
> `from __future__ import annotations`. The module docstring's claim "no imports beyond
> `__future__`" must be updated to "stdlib `re` only, no I/O".

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_rubric -v`
Expected: `OK`.

- [ ] **Step 5: Prove the terminator test bites**

Temporarily change `(?=^## |\Z)` to `(?=^## Lens |\Z)` and re-run.
Expected: **FAIL** on `test_slice_carries_no_gate_knowledge` and
`test_terminator_is_any_h2_not_only_a_lens_h2`. **Revert** and re-run — expected `OK`.

- [ ] **Step 6: `make ci` + commit**

```bash
make ci   # expected EXIT 0
git add scripts/rubric.py tests/test_rubric.py
git commit -F - <<'EOF'
feat(rubric): pure byte-exact per-lens slicer

skills/atlas/SKILL.md:557 specifies "that critic's single rubric lens from
references/rubric.md", and today the root LLM reads all 13,044 B and hand-slices it
on every VERIFIED pass — where it can truncate a bullet, drop the severity mapping
or paste the wrong lens with nothing detecting it. lens_section is byte-exact and
mechanises the F6 isolation for the first time.

The terminator is `^## `, not `^## Lens`: the latter makes REQUIREMENTS-COVERAGE
swallow Per-critic verdict and the whole PASS bar, i.e. hand a single-lens critic
the gate knowledge it must not have. The separator is an EM DASH; a hyphen returns
empty for every dimension, so both are pinned by mutation-caught tests.

Not wired into any dispatch path yet — Phase 4 consumes it.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 6: `contextgraph.render_for_injection` — bound the injection view only

**Files:**
- Modify: `scripts/contextgraph.py`
- Modify: `tests/test_contextgraph.py`

**Interfaces:**
- Produces: `render_for_injection(graph: dict, max_bytes: int = 24000, max_node_chars: int = 2000) -> dict`.
- **Not called by `graph_lookup` in this plan.** Wiring happens in Phase 5.

**Grounding + the three corrections:** measured law `bytes ≈ 1,019 + n·(227 + output_len)` with
`output_len ≤ 2000` clamped per node by `hooks/telemetry.sh:82,86`, and `n` unbounded.

1. `max_node_chars` **must be 2000** — exactly the telemetry clamp — so that below the budget the
   render is provably byte-identical to today.
2. **One binding dimension:** `max_bytes` is the budget; per-class windows derive from it. Binding drops
   **whole nodes** oldest-first within class quotas and re-serialises. Never string-slice: that emits
   invalid JSON inside the SAFE-2 fence.
3. **No node class gets unconditional retention.** `.atlas/<run>/hooks.jsonl` sits inside the interactive
   coder's writable root, so "keep all error nodes" would let a coder append synthetic errors and evict
   every legitimate `tool_call`, making the injected graph 100 % attacker-authored.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_contextgraph.py, above `if __name__`

class TestRenderForInjection(unittest.TestCase):
    def _graph(self, n_tool=0, n_err=0, body=""):
        nodes, edges, seq = [], [], 0
        for i in range(n_tool):
            nodes.append({"id": "t%d" % i, "kind": "tool_call", "seq": seq,
                          "tool": "Bash", "untrusted_output": body})
            seq += 1
        for i in range(n_err):
            nodes.append({"id": "e%d" % i, "kind": "error", "seq": seq,
                          "tool": "Bash", "untrusted_error": body})
            seq += 1
        for a, b in zip(nodes, nodes[1:]):
            edges.append({"from": a["id"], "to": b["id"], "rel": "then"})
        return {"nodes": nodes, "edges": edges, "run_id": "R", "schema": "context-graph/1"}

    def test_below_budget_is_byte_identical(self):
        g = self._graph(n_tool=20, body="x" * 100)
        self.assertEqual(json.dumps(contextgraph.render_for_injection(g), sort_keys=True),
                         json.dumps(g, sort_keys=True))

    def test_above_budget_respects_the_byte_budget(self):
        g = self._graph(n_tool=200, body="x" * 2000)
        out = contextgraph.render_for_injection(g, max_bytes=24000)
        self.assertLessEqual(len(json.dumps(out)), 24000)

    def test_binding_drops_whole_nodes_and_stays_valid_json(self):
        g = self._graph(n_tool=200, body="x" * 2000)
        out = contextgraph.render_for_injection(g, max_bytes=24000)
        json.loads(json.dumps(out))                       # never string-sliced
        self.assertLess(len(out["nodes"]), len(g["nodes"]))

    def test_errors_are_not_unconditionally_retained(self):
        """A coder that appends 500 synthetic errors must not evict every tool_call."""
        g = self._graph(n_tool=20, n_err=500, body="x" * 2000)
        out = contextgraph.render_for_injection(g, max_bytes=24000)
        kinds = [n["kind"] for n in out["nodes"]]
        self.assertIn("tool_call", kinds)
        self.assertIn("error", kinds)

    def test_retained_nodes_keep_ascending_original_seq(self):
        g = self._graph(n_tool=200, body="x" * 2000)
        out = contextgraph.render_for_injection(g, max_bytes=24000)
        seqs = [n["seq"] for n in out["nodes"]]
        self.assertEqual(seqs, sorted(seqs))
        self.assertEqual(len(seqs), len(set(seqs)))

    def test_dangling_edges_are_dropped(self):
        g = self._graph(n_tool=200, body="x" * 2000)
        out = contextgraph.render_for_injection(g, max_bytes=24000)
        ids = {n["id"] for n in out["nodes"]}
        for e in out["edges"]:
            self.assertIn(e["from"], ids)
            self.assertIn(e["to"], ids)

    def test_honesty_markers_report_what_was_dropped(self):
        g = self._graph(n_tool=200, body="x" * 2000)
        out = contextgraph.render_for_injection(g, max_bytes=24000)
        self.assertGreater(out["window"]["omitted_tool_calls"], 0)
        self.assertIn("omitted_errors", out["window"])

    def test_project_is_untouched_by_the_cap(self):
        """SCOPE: the cap is an INJECTION view. The on-disk projection, OUTPUT's
        completeness read and resume must all still see every node."""
        import inspect
        src = inspect.getsource(contextgraph.project)
        self.assertNotIn("render_for_injection", src)
        self.assertNotIn("render_for_injection", inspect.getsource(contextgraph.build))
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. python3 -m unittest tests.test_contextgraph -v`
Expected: `AttributeError: … has no attribute 'render_for_injection'`.

- [ ] **Step 3: Write the implementation**

```python
# append to scripts/contextgraph.py

# The injection view's default byte budget. The graph is a HINT and never a gate
# (skills/atlas/SKILL.md:351-363), so bounding it cannot change any verdict; the
# per-node clamp matches hooks/telemetry.sh:82,86 EXACTLY so that below the budget
# the render is byte-identical to the uncapped graph.
INJECTION_MAX_BYTES = 24_000
INJECTION_MAX_NODE_CHARS = 2_000
_EVENT_KINDS = ("tool_call", "error")


def render_for_injection(graph: dict, max_bytes: int = INJECTION_MAX_BYTES,
                         max_node_chars: int = INJECTION_MAX_NODE_CHARS) -> dict:
    """Return a byte-bounded VIEW of ``graph`` for packet injection.

    SCOPE: this is for the ``graph_lookup`` injection path ONLY. ``build``,
    ``project`` and ``load_or_rebuild`` — and therefore the on-disk
    ``context-graph.json``, OUTPUT's completeness read and resume — keep seeing
    every node, uncapped.

    ``bytes ≈ 1019 + n·(227 + output_len)`` with ``n`` unbounded today, so a
    telemetry-heavy run can inject a graph many times the size of the change under
    review. Binding drops WHOLE event nodes, newest-first retention within a
    per-kind quota, then re-serialises — never string-slicing, which would emit
    invalid JSON inside the SAFE-2 fence. Neither event kind gets unconditional
    retention: ``hooks.jsonl`` lives inside the interactive coder's writable root,
    so an "always keep errors" rule would let a coder evict every legitimate
    ``tool_call``. Retained nodes are emitted in ascending original ``seq`` so the
    module's monotonic-seq invariant holds and omissions show as gaps.
    """
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    if len(json.dumps(graph)) <= max_bytes:
        return graph

    kept: list[dict] = [n for n in nodes if n.get("kind") not in _EVENT_KINDS]
    by_kind = {k: [n for n in nodes if n.get("kind") == k] for k in _EVENT_KINDS}
    quotas = {k: 0 for k in _EVENT_KINDS}
    # Grow each kind's quota one node at a time, round-robin, until the budget binds.
    grew = True
    while grew:
        grew = False
        for kind in _EVENT_KINDS:
            if quotas[kind] >= len(by_kind[kind]):
                continue
            trial = dict(quotas, **{kind: quotas[kind] + 1})
            candidate = kept + [n for k in _EVENT_KINDS for n in by_kind[k][-trial[k]:]]
            candidate.sort(key=lambda n: n.get("seq", 0))
            ids = {n.get("id") for n in candidate}
            trial_graph = dict(graph)
            trial_graph["nodes"] = candidate
            trial_graph["edges"] = [e for e in edges
                                    if e.get("from") in ids and e.get("to") in ids]
            trial_graph["window"] = {"omitted_tool_calls": 0, "omitted_errors": 0,
                                     "truncated_event_bodies": 0, "max_bytes": max_bytes}
            if len(json.dumps(trial_graph)) <= max_bytes:
                quotas = trial
                grew = True

    retained = kept + [n for k in _EVENT_KINDS for n in by_kind[k][-quotas[k]:] if quotas[k]]
    retained.sort(key=lambda n: n.get("seq", 0))
    ids = {n.get("id") for n in retained}
    out = dict(graph)
    out["nodes"] = retained
    out["edges"] = [e for e in edges if e.get("from") in ids and e.get("to") in ids]
    out["window"] = {
        "omitted_tool_calls": len(by_kind["tool_call"]) - quotas["tool_call"],
        "omitted_errors": len(by_kind["error"]) - quotas["error"],
        "truncated_event_bodies": 0,
        "max_bytes": max_bytes,
    }
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_contextgraph -v`
Expected: `OK`.

- [ ] **Step 5: Prove the anti-eviction test bites**

Temporarily change `_EVENT_KINDS` to `("tool_call",)` and add `kept += by_kind_errors` so errors are
retained unconditionally; re-run.
Expected: **FAIL** on `test_errors_are_not_unconditionally_retained` or
`test_above_budget_respects_the_byte_budget`. **Revert** and re-run — expected `OK`.

- [ ] **Step 6: `make ci` + commit**

```bash
make ci   # expected EXIT 0
git add scripts/contextgraph.py tests/test_contextgraph.py
git commit -F - <<'EOF'
feat(contextgraph): pure byte-bounded injection view (not yet wired)

The injected graph has no cap of any kind today: measured
bytes ~= 1019 + n*(227 + output_len) with output_len <= 2000 clamped per node by
hooks/telemetry.sh but n unbounded — 200 events render 446,802 B, many times the
size of the change under review. The graph is explicitly a HINT and never a gate,
so bounding it cannot change any verdict.

max_node_chars is 2000, EXACTLY the telemetry clamp, so below the budget the render
is byte-identical (pinned). Binding drops WHOLE nodes and re-serialises — never
string-slices, which would emit invalid JSON inside the SAFE-2 fence. Neither event
kind is unconditionally retained: hooks.jsonl sits inside the interactive coder's
writable root, so an always-keep-errors rule would let a coder append synthetic
errors and evict every legitimate tool_call.

Scoped to the injection path: build/project/load_or_rebuild, the on-disk
context-graph.json, OUTPUT's completeness read and resume all stay uncapped, pinned
by a source-inspection test. Wiring lands in Phase 5.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 7: `ctxstore.valid_run_id` + the hardened confined write hand

**Files:**
- Modify: `scripts/ctxstore.py`
- Modify: `tests/test_ctxstore.py`

**Interfaces:**
- Produces: `valid_run_id(run_id: str) -> bool`,
  `write_artifact_confined(base: str, run_id: str, name: str, data) -> pathlib.Path`.

**Why:** `ctxstore.write_artifact` (`scripts/ctxstore.py:291-298`) is a bare `write_text` that follows
symlinks at every path component. Phase 5 writes attacker-influenceable blobs under
`.atlas/<run_id>/untrusted/`, and in interactive mode `review_root == "."` puts `.atlas/` **inside the
coder's own writable root**. `run_id` also flows into path joins and, in Phase 3, into
`git worktree add` argv.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_ctxstore.py, above `if __name__`

class TestValidRunId(unittest.TestCase):
    def test_accepts_realistic_session_ids(self):
        for ok in ("session_cf7b23ae-885a-4ef7-9ec9-97ac841d9737", "abc123", "A-b_9"):
            with self.subTest(run_id=ok):
                self.assertTrue(ctxstore.valid_run_id(ok))

    def test_rejects_traversal_separators_and_argv_injection(self):
        for bad in ("..", "../x", "a/b", "a\\b", "", "  ", "-x", "--upload-pack=evil",
                    "a b", "a\nb", "a\x00b", "x" * 129, None, 5):
            with self.subTest(run_id=bad):
                self.assertFalse(ctxstore.valid_run_id(bad))


class TestWriteArtifactConfined(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.base = os.path.join(self.tmp, ".atlas")
        ctxstore.init_run(self.base, "R", {"intent": "i", "success_criteria": [],
                                           "scope_paths": [], "verify_cmd": "",
                                           "baseline_sha": "", "debug_tokens": [],
                                           "test_glob": ""})

    def test_writes_and_reads_back(self):
        p = ctxstore.write_artifact_confined(self.base, "R", "untrusted/blob.txt", "hello")
        self.assertTrue(p.is_file())
        self.assertEqual(p.read_text(encoding="utf-8"), "hello")

    def test_refuses_traversal_out_of_the_run_dir(self):
        with self.assertRaises(ValueError):
            ctxstore.write_artifact_confined(self.base, "R", "../../escape.txt", "x")

    def test_refuses_a_symlinked_component(self):
        outside = os.path.join(self.tmp, "outside")
        os.makedirs(outside)
        link = os.path.join(self.base, "R", "untrusted")
        os.symlink(outside, link)
        with self.assertRaises(ValueError):
            ctxstore.write_artifact_confined(self.base, "R", "untrusted/blob.txt", "x")
        self.assertFalse(os.path.exists(os.path.join(outside, "blob.txt")))

    def test_refuses_an_invalid_run_id(self):
        with self.assertRaises(ValueError):
            ctxstore.write_artifact_confined(self.base, "../evil", "blob.txt", "x")
```

> The test module already imports `os`, `shutil`, `tempfile` and `ctxstore`; if any is absent, add it.

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. python3 -m unittest tests.test_ctxstore -v`
Expected: `AttributeError: … has no attribute 'valid_run_id'`.

- [ ] **Step 3: Write the implementation**

```python
# append to scripts/ctxstore.py  (needs `import re` and `import os` at the top)

# A run_id is a path component AND, from Phase 3, part of `git worktree add` argv.
# Restricting it to [A-Za-z0-9._-], banning a leading '-' (argv option injection)
# and banning a bare '.'/'..' makes both uses safe by construction.
_RUN_ID_RE = re.compile(r"\A(?!-)[A-Za-z0-9._-]{1,128}\Z")


def valid_run_id(run_id) -> bool:
    """True iff ``run_id`` is safe as a path component and as an argv token."""
    if not isinstance(run_id, str):
        return False
    if run_id in (".", ".."):
        return False
    return bool(_RUN_ID_RE.match(run_id))


def write_artifact_confined(base: str, run_id: str, name: str, data) -> pathlib.Path:
    """Write ``data`` under the run dir, refusing traversal and symlinked components.

    ``write_artifact`` is a bare ``write_text`` that follows symlinks at every
    component. Callers that persist ATTACKER-INFLUENCEABLE bytes must use this hand
    instead: in interactive mode ``review_root == "."``
    (``skills/atlas/SKILL.md:322``), so ``.atlas/`` sits inside the coder's own
    writable root and any component could be replaced with a symlink.

    Raises ``ValueError`` on an invalid ``run_id``, on a target that resolves
    outside the run dir, or on any symlinked component. Writes via
    ``O_NOFOLLOW|O_CREAT|O_EXCL`` + ``os.replace`` so the final placement is atomic.
    """
    if not valid_run_id(run_id):
        raise ValueError("unsafe run_id: %r" % (run_id,))
    run_dir = pathlib.Path(base, run_id).resolve()
    target = pathlib.Path(base, run_id, name)
    resolved = target.resolve()
    if not resolved.is_relative_to(run_dir):
        raise ValueError("artifact escapes the run dir: %r" % (name,))
    probe = resolved.parent
    while probe != run_dir and run_dir in probe.parents:
        if probe.is_symlink():
            raise ValueError("symlinked path component: %s" % probe)
        probe = probe.parent
    if resolved.parent.is_symlink() or resolved.is_symlink():
        raise ValueError("symlinked target: %s" % resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data, indent=2, sort_keys=True)
    tmp = resolved.parent / (resolved.name + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, resolved)
    return resolved
```

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_ctxstore -v`
Expected: `OK`.

- [ ] **Step 5: Prove the symlink test bites**

Temporarily replace the symlink walk with `pass` and re-run.
Expected: **FAIL** on `test_refuses_a_symlinked_component` — and the assertion that no file landed in
`outside/` is what proves it non-tautological. **Revert** and re-run — expected `OK`.

- [ ] **Step 6: `make ci` + commit**

```bash
make ci   # expected EXIT 0
git add scripts/ctxstore.py tests/test_ctxstore.py
git commit -F - <<'EOF'
feat(ctxstore): valid_run_id + a symlink-refusing confined write hand

write_artifact is a bare write_text that follows symlinks at every component. In
interactive mode review_root == "." (SKILL.md:322), so .atlas/ sits inside the
coder's own writable root — and Phase 5 will persist attacker-influenceable blobs
there. write_artifact_confined refuses traversal and any symlinked component, then
writes O_NOFOLLOW|O_CREAT|O_EXCL + os.replace.

valid_run_id restricts run_id to a safe path component that is also a safe argv
token: no separators, no leading '-' (Phase 3 passes it to `git worktree add`), no
NUL/newline/space, no bare '.'/'..'.

Both pure/thin and additive: write_artifact keeps its exact contract and every
existing caller is untouched.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
```

---

## After this plan

Phase 0–2 ship a **strictly stronger harness and three unused pure cores** — no token saving is
realised yet, by design, and none of the changes can alter what any critic sees.

**Next plans, each written only after its predecessor merges:**

| Plan | Contents | Gate |
|---|---|---|
| P3 | `scripts/atlasrun.py` — the stage driver (M1), the continuation envelope (M5), the memory guards (M12a), skills.json enrichment (M7 driver half), and the **ports of all seven existing SKILL substring pins to behavioural successors** | **the hard measurement gate: re-measure a leaptest-class run's `wire.jsonl` and publish the real `N`. If `N > 19`, re-scope Phases 4–5 before committing to them.** |
| P4 | `scripts/packet.py` (M2 B/C); `run_negative_gate.call_critic` re-pointed; `make preflight` | the four-leg negative-gate protocol |
| P5 | M4′ untrusted blobs by reference + the ledger-premise digest; wire `render_for_injection` into `graph_lookup` | trust-partition / fence-at-write / containment tests + a live dogfood in both modes |

**Not scheduled:** M11 (critic packets by reference), M10 (V7 scope narrowing), M6 Tier 1 — each needs
named evidence infrastructure that does not exist, and M10 additionally needs the **E3** adjudication
(`references/rubric.md` contradicts itself on V7: `:53-54`/`:98` vs `:193`).
