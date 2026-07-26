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

import json

from scripts import quality, verdict
from scripts.rubric import BLOCKING as _BLOCKING_SEV, DIMENSIONS as _DIMENSIONS

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
# (SKILL.md:328) — so a fix telling the coder to "persist the critic JSON" would
# invite the LLM under review to author gate input. These ids are never coder tasks.
ORCHESTRATOR_DEFECT_IDS: frozenset[str] = frozenset(
    {"evidence-incomplete", "critic-schema", "stale-verdict"}
    | {"critic-missing:%s" % d.lower() for _n, d in CRITIC_ARTIFACTS}
    | {"dimension-dissent:%s" % d.lower() for _n, d in CRITIC_ARTIFACTS}
    | {"critic-stale:%s" % d.lower() for _n, d in CRITIC_ARTIFACTS}
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
    root (``skills/atlas/SKILL.md:313``, ``:328``), i.e. it is gate input the LLM under
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


# Legitimate tool residue a verification run regenerates OUTSIDE scope_paths on
# honest runs (challenge fold T2-F1): the coder runs the suite, pytest/py/coverage
# drop their caches next to the code, and without this set each file below fires a
# blocking defect the coder can only clear by deleting files runcheck then
# regenerates — a manufactured, never-resolvable RED. This set is DELIBERATELY
# BROADER than the invisibility class ``--exclude-standard`` already accepts, in
# two named ways: (1) it also hides TRACKED files under residue names (a checked-in
# ``build`` script, a JS project shipping ``dist/`` as source) — narrowing to
# untracked-only would manufacture a RED on honest runs whose build regenerates
# TRACKED generated files under residue names (committed codegen); and (2) the
# ``.coverage*`` prefix also hides unignored untracked names like
# ``lib/.coverage-evil.py``. The trade-off is conscious: a deceptive coder gains a
# small set of named hiding places (all of which runcheck still EXECUTES), in
# exchange for never manufacturing a RED on an honest repository — the governing
# rule of this program.
_RESIDUE_SEGMENTS: frozenset[str] = frozenset({
    ".atlas", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".venv", "venv", "node_modules", "dist", "build",
    "target", "htmlcov",
})


def _is_residue(path: str) -> bool:
    """True iff ``path`` is tool residue never worth an out-of-scope defect."""
    parts = path.split("/")
    if any(seg in _RESIDUE_SEGMENTS for seg in parts):
        return True
    if any(seg.endswith(".egg-info") for seg in parts):
        return True
    name = parts[-1]
    return name.endswith((".pyc", ".pyo")) or name.startswith(".coverage")


def _normalize_scopes(scope_paths) -> list[str] | None:
    """Scope specs normalized, or ``None`` when they mean the WHOLE tree.

    Whole-tree spellings are ``.``, ``""`` and ``./`` (after stripping leading
    ``./`` segments and trailing ``/``); for them nothing can be out of scope.
    Do NOT reuse ``reqcoverage._under_scope``: it matches NOTHING under
    ``["."]`` / ``["./src"]`` (verified), so it would flag every file under the
    documented headless default. An empty result is NOT whole-tree — no
    legitimate scope is empty, so empty fails closed (every path fires).
    """
    scopes: list[str] = []
    for raw in scope_paths or []:
        s = raw if isinstance(raw, str) else ""
        while s.startswith("./"):
            s = s[2:]
        s = s.rstrip("/")
        if s in ("", "."):
            return None
        scopes.append(s)
    return scopes


def out_of_scope_defects(full_paths, scope_paths) -> list[dict]:
    """One blocking HIGH CORRECTNESS defect per file changed OUTSIDE ``scope_paths``.

    The reviewed tree must equal the executed tree (S3(a)/R3): the scope-
    restricted ``diff.patch`` feeds every lens, but the coder's real blast radius
    is ``review_root`` — a change outside ``scope_paths`` (including deleting the
    very test that would catch the bug) was invisible to all six lenses while
    ``runcheck`` still ran the whole tree. ``full_paths`` is the machine-derived
    whole-tree change list (``difftool.change_paths`` — never parsed patch TEXT,
    which is content-spoofable and misses pure renames).

    HIGH rather than CRITICAL, deliberately: the legitimate case exists (a
    cross-cutting edit to a shared ``conftest.py``), and HIGH already blocks AND
    fires V7. This id is deliberately NOT in ``ORCHESTRATOR_DEFECT_IDS``: the
    in-loop resolution is the coder's (revert the out-of-scope part), so REFINE
    correctly hands the ``fix`` to the coder; the ``fix`` also names the other
    resolution — the HUMAN widening scope at the OUTPUT gate — because
    ``scope_paths`` is frozen and a legitimate edit correctly ends UNVERIFIED
    with the defect visible, never silently cleared. Wired ONLY when
    ``difftool.git_tree_has_baseline`` holds (fold T2-F2): on a non-git tree or
    an unresolvable baseline this fold contributes ``[]``, because a non-git
    capture renders every pre-existing file as new.

    ADJUDICATED honest-false-positive, named for the CHANGELOG: git cannot
    timestamp untracked files, so a file that is UNTRACKED AT BASELINE and
    outside ``scope_paths`` fires even though nobody changed it this run
    (whole-branch review, Important-2). That is the correct terminal state,
    not a defect: an unreviewed file inside the executed tree (a root
    ``conftest.py`` pytest auto-loads is the canonical shape) is precisely the
    S3 class, and the human gate resolves it — widen scope or remove the file
    deliberately. The ``fix`` therefore forbids deleting a pre-existing file:
    the in-loop hazard was a coder "reverting" a user's scratch file to go
    green. A snapshot-at-INIT exclusion was rejected: the snapshot would be
    gate input living in the same writable ``.atlas/`` (the T4-F8 class).

    **H2 (v1.5.2.1) — the ``fix`` may never order a revert of a file the coder
    did not write.** v1.5.2 opened with *"if you made that change, revert it"*
    and keyed its escape clause on *"untracked at baseline"* — a git state, not
    authorship. On an ordinary interactive run (``review_root="."``) the user's
    own pre-existing work fires this lens, and the TRACKED-and-dirty case
    (``docs/notes.md``) missed that clause entirely, so a coder writing the
    user's REAL tree was told to revert it. The template is now keyed on the one
    fact the coder actually holds — did *I* create or modify this file during
    this task — and every other path falls through to an unconditional
    do-not-touch. **This is an INTERIM.** ``out_of_scope_defects`` takes paths
    and scopes only; provenance is not machine-determinable here (``baseline_sha``
    does not capture a dirty worktree, and "untracked ⇒ human" is the very
    heuristic that produced this defect), so the partition is stated to the coder
    as prose and MUST NOT be approximated in code. Three HIGH defects still emit
    on an honest dirty tree and the run still ends UNVERIFIED; the content-hashed
    pre-coder snapshot that actually fixes that is a v1.5.3 item. What this
    change buys is bounded and exact: the user's files are no longer at risk.

    **H1 (v1.5.2.1): the path is TARGET-CONTROLLED and this ``fix`` is a TRUSTED
    coder instruction**, so every place it appears — ``id``, ``location`` and
    ``fix`` — is rendered with ``json.dumps``. A filename may hold anything but
    NUL and ``/``, git tracks it, and the target's own build can create it during
    VERIFIED: measured, a newline-bearing name reached
    ``safewrap.coder_redispatch_packet`` byte-raw as a ``fix_instructions`` entry
    for a ``Write``/``Edit``-capable coder, with no critic subverted.
    ``json.dumps`` and NOT ``safewrap._sanitize_source`` (challenge fold F9): the
    sanitizer leaves TAB/ESC/VT/FF/BS intact, mutilates a legal ``a>>>b.py`` into
    ``ab.py``, and COLLIDES ``a\\nb.py`` with ``a b.py`` onto one id — three
    separate ways to lose or misattribute a defect. ``json.dumps`` is
    control-character-free, injective (two paths can never share an id),
    reversible with ``json.loads``, leaves ``>>>`` intact, and escapes the
    bidi-override characters that would otherwise visually reorder the coder's
    instruction. It is already this program's discipline for text crossing a
    machine-read boundary (``skills/atlas/SKILL.md:738``). The normalized scopes
    are rendered the same way and for the same reason: they come from the frozen
    packet, which is built from the raw user request.

    **Scope of the "trusted ⟺ zero target-derived bytes" criterion (fold F8):**
    after this change it holds for *floorsynth's own* coder-facing ids, and only
    those. It is FALSE today for three other trusted (non-orchestrator) ids that
    also reach ``fix_instructions`` byte-raw: ``pathcheck``'s ``P*`` (the cited
    path), ``sast``'s ``rules.*`` (semgrep's message verbatim) and ``astlens``'s
    ``AST*``. Moving those into ``ORCHESTRATOR_DEFECT_IDS`` is explicitly
    FORBIDDEN here — it would delete the coder's only in-loop resolution for
    genuine CRITICAL findings and manufacture an UNRESOLVABLE red. Their remedy
    is a v1.5.3 design item, not a hotfix.
    """
    scopes = _normalize_scopes(scope_paths)
    if scopes is None:
        return []
    out: list[dict] = []
    for path in sorted(set(full_paths or [])):
        if not isinstance(path, str) or not path:
            continue
        if _is_residue(path):
            continue
        if any(path == s or path.startswith(s + "/") for s in scopes):
            continue
        # H1: the path is target-controlled and every field below is read by the
        # coder as a trusted instruction, so it is quoted, not interpolated raw.
        safe_path = json.dumps(path)
        safe_scopes = ", ".join(json.dumps(s) for s in scopes) if scopes else "<none>"
        out.append({
            "id": "out-of-scope:%s" % safe_path,
            "category": "CORRECTNESS",
            "severity": "HIGH",
            "location": safe_path,
            # H2: the revert branch is keyed on the CODER's own authorship during
            # this task; every other file falls through to an unconditional
            # do-not-touch. Never re-narrow the default to a git state.
            "fix": "the change to %s is outside the frozen scope_paths (%s); if YOU "
                   "created or modified that file during this task, revert your own "
                   "change; otherwise it pre-existed this run — LEAVE IT ENTIRELY "
                   "UNTOUCHED, and never touch a file you did not author; this "
                   "defect is then resolved by the human, who may widen scope at "
                   "the OUTPUT gate; do not edit scope_paths"
                   % (safe_path, safe_scopes),
        })
    return out


def dimension_dissent_defects(raw_critics) -> list[dict]:
    """One blocking HIGH per critic whose judgment never reached ``defects[]``.

    S4/R4: ``verdict.merge`` recomputes ``verdict`` from ``defects[]`` and
    DISCARDS the critic's own ``verdict`` field; ``dimensions`` was written and
    read by nothing that decides anything. A critic that objects in prose
    (``dimensions[d] == "no"`` or ``verdict == "FAIL"``) without filing a
    corresponding blocking defect was silently read as a clean lens — verified
    end-to-end: all six dimensions ``"no"`` with empty defects printed
    ``✅ VERIFIED``. "Corresponding" means SAME critic, SAME dimension,
    severity in BLOCKING: a same-critic HIGH in the dissented dimension
    suppresses synthesis (the merge already blocks); a MEDIUM, or a blocking
    defect in another dimension, does not.

    Input shape: ``{artifact_name: critic_dict}`` for the artifacts that loaded
    (the SKILL's ``loaded_map``). HIGH rather than CRITICAL, deliberately:
    CRITICAL is this project's idiom for hard deterministic failures, and a
    synthesized proxy for unarticulated judgment would overstate confidence —
    HIGH already blocks. One defect per critic, category = the FIRST dissented
    dimension in rubric order (cross-lens dissent keeps the dissented dimension,
    fail-closed). Orchestrator-facing: the fix re-
    dispatches the critic, so the ids live in ``ORCHESTRATOR_DEFECT_IDS``.

    **These ids do NOT fire V7**, and an earlier revision of this docstring
    wrongly said a CORRECTNESS/SECURITY-category dissent "also fires V7". The
    REFINE? block (``skills/atlas/SKILL.md``) drops every
    ``ORCHESTRATOR_DEFECT_IDS`` member *before* evaluating both ``should_refine``
    and the V7 clause, so a HIGH ``dimension-dissent:correctness`` yields
    ``should_refine=False`` and ``v7=False`` — correctly, since the coder cannot
    articulate another agent's judgment and would burn a pass to no effect. The
    blocking is not lost: ``verdict.gate`` / ``final_status`` read the FULL
    merged critic, so the HIGH still ends the run ``⚠️ UNVERIFIED``, and the
    dissent has its own pre-REFINE remediation (one critic re-dispatch).
    Malformed entries are skipped — the schema floor (Step 3.4) and
    ``critics_missing_defects`` own those shapes.
    """
    blocking = _BLOCKING_SEV
    out: list[dict] = []
    for name, dimension in CRITIC_ARTIFACTS:
        critic = (raw_critics or {}).get(name)
        if not isinstance(critic, dict):
            continue
        dims = critic.get("dimensions")
        dims = dims if isinstance(dims, dict) else {}
        defects = critic.get("defects")
        defects = defects if isinstance(defects, list) else []

        def _corresponds(dim: str) -> bool:
            return any(
                isinstance(d, dict) and d.get("category") == dim
                and d.get("severity") in blocking
                for d in defects
            )

        dissented = [d for d in _DIMENSIONS
                     if dims.get(d) == "no" and not _corresponds(d)]
        has_blocking = any(
            isinstance(d, dict) and d.get("severity") in blocking for d in defects
        )
        if critic.get("verdict") == "FAIL" and not has_blocking:
            dissented = dissented or [dimension]
        if not dissented:
            continue
        out.append({
            "id": "dimension-dissent:%s" % dimension.lower(),
            "category": dissented[0],
            "severity": "HIGH",
            "location": ".atlas/<run_id>/%s" % name,
            "fix": "ORCHESTRATOR ACTION — not a coder task: re-dispatch the %s critic "
                   "once: articulate the dissent (%s) as a blocking defect with "
                   "evidence, or change the dimension verdict to yes — a dissent "
                   "without a blocking defect must never merge as a clean lens"
                   % (dimension, ", ".join(dissented)),
        })
    return out


def critics_stale_defects(loaded_map, current_pass: int) -> list[dict]:
    """One blocking CRITICAL per critic artifact whose currency stamp is wrong.

    S5: critic artifact names are pass-invariant and REFINE re-enters
    CODED→VERIFIED in the same run dir, so existence was never freshness —
    a pass-1 CLEAN artifact read as a fresh lens on code that critic never
    saw (verified end-to-end at v1.5.1). Each artifact is stamped at write
    time with ``pass = ctxstore.get_refine_passes(...)`` (orchestrator
    metadata added AFTER ``enforce_critic_schema`` passes — CF-0 — never part
    of the validated object), and the stamp must equal the current pass.

    Back-compat: an artifact with NO ``pass`` field is stale — EXCEPT at
    ``current_pass == 0``, where it can only be from this run's first VERIFIED
    (a v1.5.1 artifact carried through an upgrade-resume, fold T4-F4). The
    check lives ONLY in the Step 4+5 fold, never at OUTPUT. Asymmetric by
    design: a stale RED artifact keeps the run red through its own defects;
    this floor exists for the stale CLEAN one. Orchestrator-facing: the fix
    re-dispatches the critic, never the coder.
    """
    out: list[dict] = []
    for name, dimension in CRITIC_ARTIFACTS:
        critic = (loaded_map or {}).get(name)
        if not isinstance(critic, dict):
            continue
        stamp = critic.get("pass", ...)
        fresh = (stamp == current_pass) if stamp is not ... else (current_pass == 0)
        if fresh:
            continue
        out.append({
            "id": "critic-stale:%s" % dimension.lower(),
            "category": dimension,
            "severity": "CRITICAL",
            "location": ".atlas/<run_id>/%s" % name,
            "fix": "ORCHESTRATOR ACTION — not a coder task: re-dispatch the %s critic "
                   "and persist its JSON for the current refine pass (%s); a lens "
                   "stamped for an earlier pass never reviewed this tree"
                   % (dimension, current_pass),
        })
    return out


# One reason string per INDEPENDENT ledger-shape failure ``stale_verdict_defects``
# detects. They are separate constants, and the emitted ``fix`` names ONLY the
# reasons that actually fired, because the three shapes have genuinely different
# diagnoses and genuinely different remedies (fold M-1). Handing an honest
# ROLLBACK-after-REFINE or a coder-timeout run "the tree may have mutated after
# verification" would be a fabricated accusation about work nobody did: neither
# shape mutates anything, and a wrong diagnosis on a correct RED is how an
# orchestrator gets talked into "fixing" the wrong thing.
_STALE_REASON_ORDERING = (
    "a CODED record post-dates the last VERIFIED, so the tree may have mutated "
    "after verification — re-run CODED → VERIFIED"
)
_STALE_REASON_ADJACENCY = (
    "the ledger contains a stage pair that is not a legal transition of this "
    "machine, so the recorded trajectory is not a path the run can have taken — "
    "reconstruct the transition that was skipped or mis-recorded"
)
_STALE_REASON_REFINE_UNRESOLVED = (
    "a REFINE record post-dates the last CODED, so the refine pass the gate "
    "forced never re-entered CODED and NO verification covers the tree as it now "
    "stands — re-enter CODED and re-run VERIFIED; if the coder could not be "
    "re-run at all (timeout, budget spent), this is the degraded could-not-verify "
    "path and the run must end ⚠️ UNVERIFIED with budget_exhausted = True"
)


def stale_verdict_defects(log_records) -> list[dict]:
    """One blocking DOES-IT-RUN/CRITICAL when the ledger's stage SHAPE is broken.

    S10: ``ctxstore.advance`` is a permissive recorder and
    ``verdict.missing_stages`` is set-membership — order-blind — so a ledger
    reading ``[..., VERIFIED, REFINE, CODED, OUTPUT]`` (the tree mutated AFTER
    verification) printed a stale ✅. THREE conditions, any one sufficient:
    (a) the last CODED record's APPEND-ORDER index exceeds the last
    VERIFIED record's; (b) any adjacent pair fails ``fsm.legal_transition``;
    (c) the last REFINE record's index exceeds the last CODED record's.
    Append-order index, NEVER a timestamp — the ledger clock is
    second-granular, so a fast honest run shares one ``ts`` across entries
    (fold T4-F2).

    (c) is H6 (v1.5.2.1), and it is deliberately a TRAILING-SHAPE test rather
    than the pairwise "the record after a REFINE is not CODED" it is tempting to
    write. This function is called by ``skills/atlas/SKILL.md``'s OUTPUT block
    **36 lines before** that block's own ``advance(..., "OUTPUT")``, so at the
    real evaluation point a run that crashed after ``advance(REFINE)`` presents a
    ledger ENDING at ``REFINE``, with no successor record at all — a pairwise
    condition has no pair to look at and can never fire, while an
    OUTPUT-terminated test fixture makes it look closed. The honest crash then
    resumed at OUTPUT (``STAGES`` order puts OUTPUT after REFINE), the forced
    refine never ran, and the run printed ✅ off a verdict the gate had already
    superseded. Corollary for anyone adding a fixture here: **truncate it where
    the SKILL evaluates it**, and never append an ``OUTPUT`` record unless the
    fixture also models the ``cancelled=True`` early return below.

    The sequence is normalized FIRST (fold T4-F1), because honest sequences
    contain shapes that are not machine transitions: ``stage == "ROLLBACK"``
    records are dropped (they are ledger markers, not transitions), adjacent
    duplicates are collapsed (``advance`` appends the log line before writing
    state.json, so a crash-resume re-records one stage — idempotent, benign),
    and a ledger whose final OUTPUT record carries ``cancelled=True`` is
    skipped outright (the sanctioned pre-CODE cancel). The S10 attack shape
    has no duplicates and still trips (a) and (b) after normalization.

    At most ONE defect is ever returned: the three conditions share one id, one
    location and one remedy sentence, and differ only in the reason text, which
    names exactly the conditions that fired. A ledger tripping two of them is one
    broken ledger, not two defects — and keeping the arity at one is what lets
    every ``len(...) == 1`` pin in the matrix stay a pin.

    NON-RAISING, deliberately: it records a defect; it does not turn
    ``advance`` into a hard error — resume-after-compaction legitimately
    re-enters stages and must keep working. Scoped to the single-change atlas
    machine: the weave root ledger uses outer stages (DECOMPOSED…) that are
    not fsm edges at all.
    """
    from scripts import fsm

    records = [r for r in (log_records or []) if isinstance(r, dict)]
    if records:
        last = records[-1]
        if last.get("stage") == "OUTPUT" and last.get("cancelled"):
            return []
    stages = [r.get("stage") for r in records]
    stages = [s for s in stages if isinstance(s, str) and s != "ROLLBACK"]
    deduped = [s for i, s in enumerate(stages) if i == 0 or s != stages[i - 1]]

    last_coded = max((i for i, s in enumerate(deduped) if s == "CODED"), default=-1)
    last_verified = max((i for i, s in enumerate(deduped) if s == "VERIFIED"), default=-1)
    last_refine = max((i for i, s in enumerate(deduped) if s == "REFINE"), default=-1)
    reasons: list[str] = []
    if last_coded >= 0 and last_verified >= 0 and last_coded > last_verified:
        reasons.append(_STALE_REASON_ORDERING)
    if any(not fsm.legal_transition(a, b) for a, b in zip(deduped, deduped[1:])):
        reasons.append(_STALE_REASON_ADJACENCY)
    # No ``last_refine >= 0`` guard is needed or wanted: the absent-REFINE
    # sentinel is -1 and ``last_coded`` is never below -1, so an empty or
    # pre-CODED ledger cannot satisfy this. A redundant conjunct here would be a
    # branch no mutation could kill.
    if last_refine > last_coded:
        reasons.append(_STALE_REASON_REFINE_UNRESOLVED)
    if not reasons:
        return []
    return [{
        "id": "stale-verdict",
        "category": "DOES-IT-RUN",
        "severity": "CRITICAL",
        "location": ".atlas/<run_id>/log.jsonl",
        "fix": "ORCHESTRATOR ACTION — not a coder task: " + "; also ".join(reasons)
               + ". Recompute the verdict from the repaired ledger before printing "
                 "any status.",
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
