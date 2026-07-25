"""Pure synthesis of the deterministic floor's blocking defects (SKILL Step 4).

Every ``verdict.gate`` failure condition MUST also become a blocking defect inside
``merged_critic.json`` — otherwise ``should_refine``/``final_status`` (which read
ONLY the merged critic) disagree with ``gate``, and a run can ship a false
``VERIFIED`` while the fallible critics emit nothing. That marshalling lived as
inline heredoc text in the SKILL's Step 4+5 block, retyped by the model on every
run; a single dropped ``+=`` line silently deleted a whole floor lens with
nothing detecting it. Hoisting it here — Step 4+5 now CALLS this module — makes
floor completeness a ``make ci`` invariant instead of a per-run transcription
lottery.

INVARIANTS THIS MODULE PRESERVES
- ``scripts/verdict.py`` is FROZEN and is not modified: this module only ever
  ADDS entries to the ``script_defects`` list handed to the pure ``verdict.merge``.
- The P3 advisory firewall: ``lintlens_advisory`` is DELIBERATELY never merged and
  never reaches ``gate_results`` (the SKILL Step 4+5 firewall comments). Advisory lint
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

# Mandatory evidence keys that ARE defect lists: collected AND absence-checked.
# The pre-floorsynth SKILL read these with ``ev[...]`` and died on absence.
MANDATORY_EVIDENCE_KEYS: tuple[str, ...] = (
    "lint_defects",
    "reqcoverage_defects",
    "pathcheck_defects",
)
# Mandatory evidence keys that are NOT defect lists. They are absence-checked but
# never collected: ``docs_clean`` is a bool whose safe default (``True``) would
# otherwise make a dropped line in the Step-2 evidence literal fail OPEN on the docs
# floor, where the pre-floorsynth SKILL died with a ``KeyError`` and wrote nothing.
# (An absent ``runcheck`` needs no entry here: ``synth_runcheck({})`` synthesises its
# CRITICAL, so that key already fails CLOSED.)
MANDATORY_FLAG_KEYS: tuple[str, ...] = ("docs_clean",)
# Evidence keys this module reads with ``ev.get(...) or []`` — absence is legitimate
# for an evidence file written by an older plugin version.
OPTIONAL_EVIDENCE_KEYS: tuple[str, ...] = (
    "sast_defects",
    "astlens_defects",
    "syntaxlens_defects",
)


def script_defects_from(evidence: dict) -> list[dict]:
    """The deterministic lens defect-lists, in the SKILL's Step 4+5 fold order.

    ``lintlens_advisory`` is never included (the P3 firewall). A key in
    ``MANDATORY_EVIDENCE_KEYS`` **or** ``MANDATORY_FLAG_KEYS`` that is absent OR
    ``None`` yields one blocking ``evidence-incomplete`` defect rather than raising
    or — far worse — silently contributing nothing. Only the former are COLLECTED;
    the flag keys are absence-checked here and consumed elsewhere (``docs_clean`` by
    ``synth_docs``), because they are not defect lists.

    The test is ``is None``, never falsiness, and that is load-bearing for both kinds.
    For a defect list it subsumes absence: a present-but-NULL key contributes nothing
    through ``ev.get(key) or []``, so a mere key-presence check would report complete
    evidence for a lens that never ran (fail-OPEN), where the pre-floorsynth SKILL
    raised a ``TypeError`` and wrote no ``merged_critic.json`` at all (fail-CLOSED).
    For ``docs_clean`` the SKILL reads ``ev.get("docs_clean", True)``, so an absent
    key would default the docs floor to CLEAN (fail-OPEN) where the old block died
    with a ``KeyError`` — while ``False`` is the legitimate DIRTY-docs value that a
    falsiness test would mislabel as missing evidence.
    """
    ev = evidence or {}
    out: list[dict] = []
    for key in MANDATORY_EVIDENCE_KEYS + OPTIONAL_EVIDENCE_KEYS:
        out += list(ev.get(key) or [])
    missing = [k for k in MANDATORY_EVIDENCE_KEYS + MANDATORY_FLAG_KEYS if ev.get(k) is None]
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
    """Mirror ``gate``'s runcheck condition as a blocking defect (SKILL Step 4+5)."""
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
    """Mirror ``gate``'s ``docs_clean`` condition as a blocking defect (SKILL Step 4+5)."""
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
# The SKILL's Step 4+5 critic read loop iterates exactly these, in this order.
CRITIC_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("critic_correctness.json", "CORRECTNESS"),
    ("critic_code_quality.json", "CODE-QUALITY"),
    ("critic_security.json", "SECURITY"),
)

# Defect ids naming ORCHESTRATOR work. The REFINE loop hands CRITICAL/HIGH `fix`
# strings to the CODER as trusted instructions (the SKILL's REFINE `True` branch),
# and in interactive mode .atlas/ sits inside the coder's writable root
# (SKILL.md:322) — so a fix telling the coder to "persist the critic JSON" would
# invite the LLM under review to author gate input. These ids are never coder tasks.
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

    The pre-floorsynth Step 4+5 substituted ``{"dimensions": {}, "defects": [],
    "verdict": "OK"}`` on a read failure; today's block appends nothing and records
    which artifacts loaded. Either way ``verdict.merge``
    (``scripts/verdict.py:95-98``) SYNTHESISES all six dimensions as ``yes`` for a
    critic that is not there, and ``quality.enforce_critic_schema`` cannot see it,
    because it only ever validates the MERGED shape — so without this function an
    undispatched or lost critic is indistinguishable from a clean lens.

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
    """The two-phase merge → validate → re-merge cycle (SKILL Step 4+5).

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
