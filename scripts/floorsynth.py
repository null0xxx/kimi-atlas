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
- Every ``category`` this module synthesises (``DOES-IT-RUN``, ``CODE-QUALITY``) is
  a member of ``rubric.DIMENSIONS``, because ``quality.enforce_critic_schema``
  rejects any other category — a defect this module invents with an off-rubric
  category would fail schema validation downstream instead of blocking the run.
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
    ev = evidence or {}
    out: list[dict] = []
    for key in MANDATORY_EVIDENCE_KEYS + OPTIONAL_EVIDENCE_KEYS:
        out += list(ev.get(key) or [])
    missing = [k for k in MANDATORY_EVIDENCE_KEYS if k not in ev]
    if missing:
        # ACCUMULATE, never replace: a present CRITICAL must not be swallowed by the
        # report that a sibling key was absent.
        out.append({
            "id": "evidence-incomplete",
            "category": "DOES-IT-RUN",
            "severity": "CRITICAL",
            "location": "det_evidence.json",
            "fix": "ORCHESTRATOR ACTION — not a coder task: re-run the deterministic "
                   "lenses; absent evidence key(s): " + ", ".join(sorted(missing)),
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
