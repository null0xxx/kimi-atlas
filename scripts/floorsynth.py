"""Pure synthesis of the deterministic floor's blocking defects (SKILL Step 4).

Every ``verdict.gate`` failure condition MUST also become a blocking defect inside
``merged_critic.json`` — otherwise ``should_refine``/``final_status`` (which read
ONLY the merged critic) disagree with ``gate``, and a run can ship a false
``VERIFIED`` while the fallible critics emit nothing. That marshalling lived as
inline heredoc text in ``skills/atlas/SKILL.md:601-631``, retyped by the model on
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
- Every ``category`` this module synthesises BEFORE validation (``DOES-IT-RUN``,
  ``CODE-QUALITY``, ``CORRECTNESS``, ``SECURITY``) is a member of
  ``rubric.DIMENSIONS``, because ``quality.enforce_critic_schema`` rejects any
  other category — a defect this module invents with an off-rubric category would
  fail schema validation downstream instead of blocking the run. The lone
  ``"SCHEMA"`` category, inside ``merge_and_validate``, is appended AFTER
  validation (exactly as the SKILL does), so it is never itself validated.
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

    ``lintlens_advisory`` is never included (the P3 firewall). A MANDATORY key that
    is absent OR ``None`` yields one blocking ``evidence-incomplete`` defect rather
    than raising or — far worse — silently contributing nothing. The ``is None``
    test subsumes absence: a present-but-NULL key contributes nothing through
    ``ev.get(key) or []``, so a mere key-presence check would report complete
    evidence for a lens that never ran (fail-OPEN), where today's SKILL raises a
    ``TypeError`` and writes no ``merged_critic.json`` at all (fail-CLOSED).
    """
    ev = evidence or {}
    out: list[dict] = []
    for key in MANDATORY_EVIDENCE_KEYS + OPTIONAL_EVIDENCE_KEYS:
        out += list(ev.get(key) or [])
    missing = [k for k in MANDATORY_EVIDENCE_KEYS if ev.get(k) is None]
    if missing:
        # ACCUMULATE, never replace: a present CRITICAL must not be swallowed by the
        # report that a sibling key was absent or NULL.
        out.append({
            "id": "evidence-incomplete",
            "category": "DOES-IT-RUN",
            "severity": "CRITICAL",
            "location": "det_evidence.json",
            "fix": "ORCHESTRATOR ACTION — not a coder task: re-run the deterministic "
                   "lenses; absent or NULL evidence key(s): " + ", ".join(sorted(missing)),
        })
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


# (artifact basename, the rubric dimension that artifact's critic owns).
# skills/atlas/SKILL.md:588 reads exactly these three, in this order.
CRITIC_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("critic_correctness.json", "CORRECTNESS"),
    ("critic_code_quality.json", "CODE-QUALITY"),
    ("critic_security.json", "SECURITY"),
)

# Defect ids naming ORCHESTRATOR work. The REFINE loop hands CRITICAL/HIGH `fix`
# strings to the CODER as trusted instructions (skills/atlas/SKILL.md:687-690), and in
# interactive mode .atlas/ sits inside the coder's writable root (SKILL.md:322) — so a
# fix telling the coder to "persist the critic JSON" would invite the LLM under review
# to author gate input. These ids are never coder tasks.
ORCHESTRATOR_DEFECT_IDS: frozenset[str] = frozenset(
    {"evidence-incomplete", "critic-schema"}
    | {"critic-missing:%s" % d.lower() for _n, d in CRITIC_ARTIFACTS}
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

    This id is deliberately NOT in ``ORCHESTRATOR_DEFECT_IDS``: producing the change
    IS the coder's job, so REFINE correctly hands this ``fix`` to the coder as a
    trusted instruction. Because of that, the ``fix`` names ONLY coder work and never
    ``review_root`` — that value is the ``cwd`` for both ``difftool.capture`` and
    ``runcheck.run`` and, interactively, is persisted inside the coder's own writable
    root (``skills/atlas/SKILL.md:313``, ``:322``), i.e. it is gate input the LLM under
    review must never be told to inspect or adjust. The orchestrator-side possibility
    that ``review_root`` pointed at the wrong tree is carried by ``location`` instead,
    which OUTPUT shows to the human and REFINE never sends.
    """
    if (diff or "").strip():
        return []
    return [{
        "id": "empty-diff",
        "category": "CORRECTNESS",
        "severity": "CRITICAL",
        "location": "diff.patch (captured from review_root)",
        "fix": "no change was produced under scope_paths — implement the task by editing the "
               "files under scope_paths; an empty diff satisfies no acceptance criterion",
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
            "fix": "ORCHESTRATOR ACTION — not a coder task: re-dispatch the %s critic and "
                   "persist its JSON; a lens that produced no judgment is never a clean "
                   "lens" % dimension,
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
            "fix": "ORCHESTRATOR ACTION — not a coder task: critic JSON must satisfy "
                   "enforce_critic_schema",
        })
        merged = verdict.merge(critics, defects)
    return merged, schema_errors
