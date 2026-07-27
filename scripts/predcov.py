"""The Phase 1 predicate-coverage instrument — REPORT ONLY, it blocks nothing.

This module answers one question the roadmap committed to: *how many of
``scripts/floorsynth.py``'s blocking predicates actually fire when replayed
against real recorded runs of this plugin?* It is an instrument, not a gate. It
emits no defect, adds no key to ``gate_results``, is imported by nothing on the
review path, and has no non-zero return path. If it breaks it must report that
it broke and still exit 0 — a measuring device that can fail a build is a gate
wearing a lab coat.

THE COUNTING RULE (the denominator), stated before any number.
    N = the number of top-level ``def``s in ``scripts/floorsynth.py`` whose body
    contains at least one dict carrying BOTH an ``"id"`` key AND a ``"severity"``
    key whose CONSTANT value is a member of ``rubric.BLOCKING``.
One such function is one predicate, counted BEFORE per-lens and per-path
expansion. It is derived by an AST walk over the source TEXT — never by reading
names, never by importing ``floorsynth``, so no import-time side effect and no
monkeypatch can move the denominator. The rule is exhaustive rather than a
sample: ``scripts/floorsynth.py`` contains no executable ``raise`` and no
``assert``, so an authored blocking defect literal is the module's only way to
say NO.

WHY THE UNIT IS THE EMITTER AND NOT THE ID. There are 16 distinct ids at HEAD:
three predicates expand ×3 over ``floorsynth.CRITIC_ARTIFACTS`` and
``out-of-scope`` expands per path, unbounded. Scored over ids, ONE predicate
firing — three undispatched critics yielding ``critic-missing:correctness`` +
``:code-quality`` + ``:security`` — would satisfy a "3 or more fire" threshold by
itself. Over emitters, one predicate firing counts as one, and the committed
prediction can fail.

WHY THE UNIT IS A ``(func_name, id_stem)`` PAIR. Binding function names alone
lets ``"docs-naming"`` be renamed to ``"docs-clean"`` with the closed-world pin
still green while that report row silently reads 0 forever (CQ3). Binding stems
alone loses the map back to the emitter the adapters must call.

WHAT THIS INSTRUMENT CANNOT CONCLUDE — carried here so it travels with the
number, per plan §7:
  * It CANNOT produce a false-RED rate. The recorded arm is 3 independent tasks,
    one repository, one orchestrator, one model, one afternoon. Twelve items is
    not twelve observations.
  * It CANNOT speak for a predicate the corpus hands a CONSTANT input. Eight of
    the ten are fed one value on the recorded arm, and in every case it is the
    non-firing value; their silence is that constant handed back, not restraint.
    Those cells render ``— (constant)``, never ``0``.
  * It CANNOT generalise past Python micro-tasks: no ``.md``, no ``.rb``/
    ``.php``/``.go``/``.sh``, no scope narrower than the whole tree, and
    ``scripts/syntaxlens.py`` has no input anywhere in the corpus.
  * It CANNOT test the release-level growth thesis (n = 3 audited releases).
  * It CANNOT distinguish "predicate too wide" from "evidence plumbing too
    brittle" without the per-fire mechanism attribution.
  * It CANNOT see a FAIL-OPEN at all. Three of the eight recorded injections are
    silences, and no fire count can see a silence — so this metric sees at most
    3 of 8, and that ceiling is printed on the same line as the verdict.

THE FIRING RULE and its two bespoke adapters live in :func:`fired`,
:func:`emit_evidence_incomplete` and :func:`emit_critic_schema`. The naive rule
("the emitter returned a non-empty list") is measurably wrong on exactly those
two and INVERTS the experiment's answer; each carries its own note.

THE ADAPTERS ARE A REPLICA, and :data:`ADAPTER_ARGUMENTS` is what keeps them one.
The argument marshalling below is a THIRD hand-copy of the SKILL's Step 4+5 fold
(``skills/atlas/SKILL.md``), after the fold itself and
``tests/test_skill_floor_contract.py``. An unbound third copy is worse than a
duplicate: it produces a coverage number for a call the orchestrator never makes,
and every reader takes that for a measurement of the real fold. So the table
below is checked against the SKILL's own calls AND against this module's own
calls, by ``tests/test_predcov.py``, and a drift on either side is a red rather
than a different number. The adapters ALSO refuse rather than default (see
:class:`AdapterInputError`), which is the one place they deliberately do NOT
replicate the fold: the SKILL's ``.get`` defaults are correct fail-closed/
fail-open runtime behaviour and would be manufactured measurements here.
"""
from __future__ import annotations

import ast
import json
import pathlib

from scripts.rubric import BLOCKING as _BLOCKING_SEV

_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Where the per-emitter firing/silent controls live. DELIBERATELY outside
#: ``tests/corpus/``: a control that lived in the corpus would be replayed as a
#: corpus item, and the instrument would then be measuring inputs its own author
#: chose to make fire — the exact rigging this phase exists to expose.
CONTROLS_DIR: pathlib.Path = _ROOT / "tests" / "fixtures" / "predcov_controls"

#: The closed-world set of blocking-predicate id STEMS in ``scripts/floorsynth.py``,
#: in source order. This is the DECLARED half of the denominator pin; the derived
#: half is :func:`discover_emitters`, and ``tests/test_predcov.py`` asserts they
#: agree. Renaming an id in either place — and only there — turns that test red.
#: There is deliberately no ``EMITTER_FUNCS`` constant beside it: the function
#: names are derived, and a second hand-maintained list would be a second thing to
#: forget.
EMITTERS: tuple[str, ...] = (
    "evidence-incomplete",
    "runcheck",
    "docs-naming",
    "empty-diff",
    "out-of-scope",
    "dimension-dissent",
    "critic-stale",
    "stale-verdict",
    "critic-missing",
    "critic-schema",
)


class AdapterInputError(ValueError):
    """An adapter was handed an input it cannot judge, and refused to guess.

    THE RULE, and the whole of it: **an adapter never substitutes a value for an
    input it did not get.** It raises, so the item carries an error and the report
    prints ``ADAPTER DEGRADED`` instead of a number.

    The reason is measured, not theoretical (TA-C1). What a silent read failure
    hands these emitters — ``ev={}``, ``diff=""``, ``loaded=[]`` — is not neutral
    input. Through ``floorsynth`` itself an empty evidence dict manufactures a
    ``runcheck`` CRITICAL (``runcheck.green({})`` is False) *and* a ``docs-naming``
    silence (``ev.get("docs_clean", True)`` defaults CLEAN), on every item at once,
    in OPPOSITE directions: one inflates the numerator, the other reports a blind
    predicate as restraint. A degraded adapter of that kind fires 4 of 10 on every
    item and reads SUPPORTED; one that swallows its exceptions reads FALSIFIED.
    Neither is visible in a corpus replay, because eight of the ten emitters are
    fed a constant on the recorded arm.

    Refusal is NOT a rule about emptiness. ``critics_missing_defects([])`` and
    ``empty_diff_defect("")`` fire on genuinely empty inputs and those fires are
    real; what the adapters refuse is ABSENCE — ``None``, a wrong type, or a
    missing key whose ``.get`` default would silently become the answer.

    THE RESIDUAL, AND IT IS THE CALLER'S TO CLOSE. For three emitters the empty
    value and the read-failure value are the same bytes: ``{}`` for
    ``evidence-incomplete``, ``""`` for ``empty-diff``, ``[]`` for
    ``critic-missing``. An adapter cannot tell those apart — it is handed a value,
    not a file — so whoever builds the per-item inputs MUST raise on an artifact it
    could not read and must never fall back to an empty literal. Substituting one
    there re-opens TA-C1 underneath a guard that looks like it is closed.
    """


class ControlFailure(RuntimeError):
    """A control fixture is missing, malformed, or does not supply its adapter's inputs.

    Distinct from :class:`AdapterInputError`, which is about a CORPUS ITEM's inputs:
    this one says the instrument's own calibration is not on disk, and no coverage
    number should be believed until it is.
    """


class DiscoveryFailure(RuntimeError):
    """The source could not be counted UNAMBIGUOUSLY.

    Never raised for "nothing matched" — an empty result is a legitimate answer
    (``scripts/floorsynth.py`` did not exist at ``v1.4.0``). It is raised only
    where the walk can see that something blocking is there and cannot say what:
    a non-constant severity, a non-derivable id, an unknown-key spread, or a
    blocking literal outside any top-level ``def``. Every one of those would
    otherwise SHRINK N silently while the experiment was running, which is the
    one failure mode a denominator must not have.
    """


def _stem_of(defect_id) -> str:
    """The firing rule's stem: ``str(id)`` up to the first ``":"``.

    ``out-of-scope`` ids embed a ``json.dumps``-quoted path that may itself hold a
    colon, so the split is bounded to one — ``out-of-scope:"a:b.py"`` is one
    ``out-of-scope`` fire, not an ``out-of-scope:"a`` one.
    """
    return str(defect_id).split(":", 1)[0]


def fired(stem: str, defects) -> bool:
    """THE FIRING RULE, and the whole of it.

    An emitter FIRES on a corpus item iff, called with that item's real inputs, it
    yields at least one defect whose id STEM equals that emitter's own stem AND
    whose ``severity`` is a member of ``rubric.BLOCKING``.

    Returns a bool and never a count, deliberately. Three predicates expand ×3
    over ``floorsynth.CRITIC_ARTIFACTS`` and ``out-of-scope`` expands per path, so
    a caller summing defects would let ONE predicate — three undispatched critics
    — satisfy a "3 of 10" threshold by itself. That is the exact rigging the
    roadmap's prediction already had to be rewritten once to remove.

    The stem is a whole segment, never a prefix: ``out-of-scope-ish`` is a
    different predicate from ``out-of-scope``.

    Every field is defended, because corpus bytes are model-influenced (``.atlas/``
    was coder-writable during recording): a non-dict record, a null id, a missing
    severity and an UNHASHABLE severity (a JSON array deserialises to a ``list``,
    and ``[] in frozenset(...)`` raises ``TypeError``) are all inert, never fatal.
    An instrument that dies on one malformed record would report every later
    emitter on that item as silent.
    """
    for defect in defects or ():
        if not isinstance(defect, dict):
            continue
        if _stem_of(defect.get("id")) != stem:
            continue
        severity = defect.get("severity")
        if isinstance(severity, str) and severity in _BLOCKING_SEV:
            return True
    return False


def _require_dict(name: str, value) -> dict:
    """The value as a dict, or :class:`AdapterInputError`. See that class for the rule."""
    if not isinstance(value, dict):
        raise AdapterInputError(
            "%s: expected the recorded object, got %s — an adapter never substitutes "
            "a default for an input it did not get" % (name, type(value).__name__)
        )
    return value


def _require_list(name: str, value) -> list:
    """The value as a list, or :class:`AdapterInputError`."""
    if not isinstance(value, list):
        raise AdapterInputError(
            "%s: expected the recorded list, got %s — an adapter never substitutes "
            "a default for an input it did not get" % (name, type(value).__name__)
        )
    return value


def _require_str(name: str, value) -> str:
    """The value as a str, or :class:`AdapterInputError`.

    ``""`` PASSES: an empty captured diff is the real input ``empty-diff`` exists to
    judge. What is refused is the absence of a diff, which would fire it identically
    while meaning something entirely different.
    """
    if not isinstance(value, str):
        raise AdapterInputError(
            "%s: expected the recorded text, got %s — an absent diff and an EMPTY "
            "diff fire this emitter identically and mean opposite things"
            % (name, type(value).__name__)
        )
    return value


def _require_int(name: str, value) -> int:
    """The value as an int, or :class:`AdapterInputError`.

    ``bool`` is refused although it is an ``int`` subclass: ``critics_stale_defects``
    compares ``stamp == current_pass``, and ``False == 0`` would silently pass a
    truthiness bug off as pass 0 — the one pass number at which a critic carrying NO
    stamp is treated as fresh.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdapterInputError(
            "%s: expected the recorded pass number, got %s — an adapter never "
            "substitutes a default for an input it did not get"
            % (name, type(value).__name__)
        )
    return value


def _require_key(name: str, mapping: dict, key: str) -> None:
    """Refuse a mapping whose ``key`` is absent, naming what the default would have done.

    Only ever called for keys whose ``.get`` default in the SKILL's fold IS an
    answer: ``runcheck`` (absent ⇒ a manufactured CRITICAL) and ``docs_clean``
    (absent ⇒ a manufactured silence). ``verify_cmd`` deliberately has no such
    guard — it decorates ``location`` and cannot change whether anything fires.
    """
    if key not in mapping:
        raise AdapterInputError(
            "%s: the key %r is absent, and this emitter's default for it IS an "
            "answer — refused rather than reported" % (name, key)
        )


def split_script_defects(ev) -> tuple[list[dict], list[dict]]:
    """``(this emitter's own defects, the upstream pass-throughs)`` — adapter 1 of 2.

    ``floorsynth.script_defects_from`` is NOT a predicate that returns its own
    verdict: it first passes through the six upstream deterministic lens defect
    lists (``scripts/floorsynth.py``:80-81) and only then considers
    ``evidence-incomplete``. Measured on the twelve real ledgers, it returns a
    NON-EMPTY list on 8 of 12 items while ``evidence-incomplete`` fires on ZERO —
    the content is MEDIUM ``RC2``/``RC3``/``RC4`` reqcoverage pass-throughs, none
    of them blocking. Scored on ``len()``, this emitter alone contributes a fire on
    two thirds of the corpus and helps flip the reported verdict from FALSIFIED to
    SUPPORTED.

    The pass-throughs are kept, not discarded: they are reported in their own
    non-counting bucket, because "8 of 12 items carry a MEDIUM advisory" is a real
    fact about the corpus and hiding it would be its own kind of dishonesty.

    Honest note on what this adapter does and does not add: no upstream lens emits
    the id ``evidence-incomplete``, so on today's sources :func:`fired` alone would
    reach the same answer. The adapter exists for the SEPARATION — the bucket has
    to be a named output, not an implicit one — and to keep the count immune to a
    future lens that borrows the id.
    """
    from scripts import floorsynth

    produced = floorsynth.script_defects_from(ev)
    own = [d for d in produced
           if isinstance(d, dict) and d.get("id") == "evidence-incomplete"]
    passthrough = [d for d in produced
                   if not (isinstance(d, dict) and d.get("id") == "evidence-incomplete")]
    return own, passthrough


def emit_evidence_incomplete(evidence) -> bool:
    """Did ``evidence-incomplete`` fire on this item? See :func:`split_script_defects`.

    ``{}`` is a legitimate input and legitimately fires — an evidence file with no
    mandatory keys is exactly what this predicate is for. ``None`` is not an input at
    all and is refused, because the two are indistinguishable here and only one of
    them is a measurement.
    """
    return fired("evidence-incomplete", defects_evidence_incomplete(evidence))


def defects_evidence_incomplete(evidence) -> list[dict]:
    """This emitter's OWN defects for one item — the pass-throughs dropped."""
    ev = _require_dict("ev", evidence)
    own, _passthrough = split_script_defects(ev)
    return own


def all_script_defects(evidence) -> list[dict]:
    """``script_defects_from``'s whole output, in floorsynth's own order.

    Needed by the fold replay (:func:`recompute_delta`), which must reproduce what
    the orchestrator merged, pass-throughs included. Reassembled from
    :func:`split_script_defects` rather than by calling ``script_defects_from`` a
    second time, so the marshalling keeps exactly ONE call site per emitter — the
    property ``tests/test_predcov.py`` pins for every row of
    :data:`ADAPTER_ARGUMENTS`. Order is exact: ``evidence-incomplete`` is APPENDED
    last by that function, so ``passthrough + own`` is the original list.
    """
    own, passthrough = split_script_defects(_require_dict("ev", evidence))
    return passthrough + own


def merge_fold(raw_critics, raw_script_defects) -> tuple[dict, list[str]]:
    """The single ``merge_and_validate`` call site: ``(merged, schema_errors)``.

    Every consumer in this module goes through here — the ``critic-schema`` adapter,
    its dimension accessor and the R2 replay — because ``merge_and_validate`` is one
    of the two emitters whose ARGUMENTS are pinned against the SKILL fold, and a
    second call site would let one copy drift while the pinned one stayed honest.
    """
    from scripts import floorsynth

    critics = _require_list("critics", raw_critics)
    script_defects = _require_list("script_defects", raw_script_defects)
    return floorsynth.merge_and_validate(critics, script_defects)


def emit_critic_schema(raw_critics, raw_script_defects) -> bool:
    """Did ``critic-schema`` fire on this item? — adapter 2 of 2.

    ``floorsynth.merge_and_validate`` does not return a defect list at all. Its
    signature is ``(critics, script_defects) -> tuple[dict, list[str]]``, so
    ``bool(...)`` is True and ``len(...)`` is 2 UNCONDITIONALLY, on every item ever
    — measured, ``merge_and_validate([], [])`` returns a 2-tuple. Any rule reading
    the return value scores this emitter as firing on 12 of 12 honest items where
    it truly fires on none.

    It fires iff ``schema_errors`` is non-empty, and NOT iff the merged defect list
    contains a ``critic-schema`` id. Those differ by exactly one thing, and it is
    the thing that matters here: ``merged["defects"]`` carries the CRITICS' own
    defects verbatim, and the corpus's critic artifacts are model-influenced, so a
    critic forging ``id="critic-schema"`` would inflate this instrument's numerator
    with a fire ``floorsynth`` never emitted. ``schema_errors`` is computed by
    ``quality.enforce_critic_schema`` and cannot be authored by the reviewed target.
    """
    _merged, schema_errors = merge_fold(raw_critics, raw_script_defects)
    return bool(schema_errors)


# ---------------------------------------------------------------------------
# The other eight adapters. One per emitter, each a REPLICA of the SKILL's Step
# 4+5 call, and each importing ``floorsynth`` locally rather than at module scope,
# so that the discovery half of this module can never reach an imported object
# where it is required to read source TEXT.
#
# Each is split in two: a ``defects_*`` core that performs the ONE call and returns
# floorsynth's own list, and an ``emit_*`` hand that applies the firing rule to it.
# The split is not cosmetic — the R2 recompute row and the dimension accessors both
# need the LIST, and routing them through the same core is what keeps every emitter
# at exactly one call site, which is the CQ5 pin.
# ---------------------------------------------------------------------------


def defects_runcheck(evidence) -> list[dict]:
    """``synth_runcheck``'s defects for one item.

    The ``runcheck`` key is REQUIRED, not defaulted: ``runcheck.green({})`` is False,
    so the SKILL's own ``ev.get('runcheck', {})`` fail-CLOSED default — correct at
    runtime, where a missing runcheck must block — would report a manufactured
    CRITICAL as a measurement here. ``verify_cmd`` is left defaulted deliberately: it
    reaches ``location`` only and cannot change whether anything fires.
    """
    from scripts import floorsynth

    ev = _require_dict("ev", evidence)
    _require_key("ev", ev, "runcheck")
    return floorsynth.synth_runcheck(ev.get("runcheck", {}), ev.get("verify_cmd", ""))


def emit_runcheck(evidence) -> bool:
    """Did ``runcheck`` fire on this item?"""
    return fired("runcheck", defects_runcheck(evidence))


def defects_docs_naming(evidence) -> list[dict]:
    """``synth_docs``' defects for one item.

    The mirror image of :func:`defects_runcheck`: here the SKILL's default
    (``ev.get('docs_clean', True)``) fails OPEN, so an absent key would be reported
    as a CLEAN docs floor — a blinded predicate printed as restraint. Required.
    """
    from scripts import floorsynth

    ev = _require_dict("ev", evidence)
    _require_key("ev", ev, "docs_clean")
    return floorsynth.synth_docs(ev.get("docs_clean", True))


def emit_docs_naming(evidence) -> bool:
    """Did ``docs-naming`` fire on this item?"""
    return fired("docs-naming", defects_docs_naming(evidence))


def defects_empty_diff(diff_text) -> list[dict]:
    """``empty_diff_defect``'s defects for one item.

    ``""`` is a real input and really fires. ``None`` is refused: an item whose
    ``diff.patch`` could not be read would otherwise be indistinguishable from a
    coder that wrote nothing, and this instrument would be counting the read failure.
    """
    from scripts import floorsynth

    diff = _require_str("diff", diff_text)
    return floorsynth.empty_diff_defect(diff)


def emit_empty_diff(diff_text) -> bool:
    """Did ``empty-diff`` fire on this item?"""
    return fired("empty-diff", defects_empty_diff(diff_text))


def defects_out_of_scope(paths, state) -> list[dict]:
    """``out_of_scope_defects``' defects for one item.

    Two refusals, both measured against ``_normalize_scopes``. An ABSENT
    ``scope_paths`` cannot be defaulted at all. An EMPTY one is worse than absent:
    ``_normalize_scopes([])`` returns ``[]`` rather than ``None``, which fails CLOSED
    and emits one HIGH per changed path — an item whose state was half-read would
    post the largest fire count in the corpus.

    ``full_paths`` is the FROZEN whole-tree path list captured with the item
    (``tree.paths``). This adapter must never recompute it with a live
    ``difftool.change_paths``, which on a non-git tree returns ``[]`` and would
    record "measured, nothing outside scope" for an item nobody can reconstruct
    (CQ2); ``tests/test_predcov.py`` asserts that call is absent from this module.
    """
    from scripts import floorsynth

    full_paths = _require_list("full_paths", paths)
    st = _require_dict("st", state)
    _require_key("st", st, "scope_paths")
    scopes = st["scope_paths"]
    if not isinstance(scopes, list) or not scopes or not all(isinstance(s, str) for s in scopes):
        raise AdapterInputError(
            "st['scope_paths']: expected a non-empty list of path strings, got %r — "
            "an empty scope fails CLOSED and fires one HIGH per changed path" % (scopes,)
        )
    return floorsynth.out_of_scope_defects(full_paths, st["scope_paths"])


def emit_out_of_scope(paths, state) -> bool:
    """Did ``out-of-scope`` fire on this item?"""
    return fired("out-of-scope", defects_out_of_scope(paths, state))


def defects_dimension_dissent(critics_map) -> list[dict]:
    """``dimension_dissent_defects``' defects for one item.

    Takes the SKILL's ``loaded_map`` (``{artifact_name: critic_dict}``), never the
    list of artifact names: an empty map is silent, so the wrong shape here reports
    every item in the corpus as a clean lens.
    """
    from scripts import floorsynth

    loaded_map = _require_dict("loaded_map", critics_map)
    return floorsynth.dimension_dissent_defects(loaded_map)


def emit_dimension_dissent(critics_map) -> bool:
    """Did ``dimension-dissent`` fire on this item?"""
    return fired("dimension-dissent", defects_dimension_dissent(critics_map))


def defects_critic_stale(critics_map, pass_number) -> list[dict]:
    """``critics_stale_defects``' defects for one item.

    ``current_pass`` is required and must be a real int: it is the item's
    ``ctxstore.get_refine_passes`` value, and at 0 an UNSTAMPED critic counts as
    fresh (the v1.5.1 upgrade-resume carve-out), so a defaulted 0 would silence the
    one emitter with a measured honest-arm fire on this corpus.
    """
    from scripts import floorsynth

    loaded_map = _require_dict("loaded_map", critics_map)
    current_pass = _require_int("current_pass", pass_number)
    return floorsynth.critics_stale_defects(loaded_map, current_pass)


def emit_critic_stale(critics_map, pass_number) -> bool:
    """Did ``critic-stale`` fire on this item?"""
    return fired("critic-stale", defects_critic_stale(critics_map, pass_number))


def defects_stale_verdict(records) -> list[dict]:
    """``stale_verdict_defects``' defects for one item.

    The ledger handed in must be the EVAL-POINT one (``log.eval.jsonl``): the SKILL
    calls this 36 lines before the OUTPUT block's own ``advance(..., "OUTPUT")``, and
    a ledger carrying that trailing record cannot trip the H6 trailing-REFINE
    condition at all. Truncation is the corpus builder's job; this adapter only
    refuses a ledger that is not a list.
    """
    from scripts import floorsynth

    log_records = _require_list("log_records", records)
    return floorsynth.stale_verdict_defects(log_records)


def emit_stale_verdict(records) -> bool:
    """Did ``stale-verdict`` fire on this item?"""
    return fired("stale-verdict", defects_stale_verdict(records))


def defects_critic_missing(artifacts) -> list[dict]:
    """``critics_missing_defects``' defects for one item.

    ``[]`` is a real input and really fires — three undispatched critics is precisely
    what this predicate is for, and it is why the firing rule returns a bool: that
    ONE predicate expands to three ids and must still count once. ``None`` is
    refused; and the list must be the artifacts that LOADED, never the ones that
    exist on disk.
    """
    from scripts import floorsynth

    loaded_critics = _require_list("loaded_critics", artifacts)
    return floorsynth.critics_missing_defects(loaded_critics)


def emit_critic_missing(artifacts) -> bool:
    """Did ``critic-missing`` fire on this item?"""
    return fired("critic-missing", defects_critic_missing(artifacts))


#: floorsynth function name -> the ARGUMENT EXPRESSIONS this module hands it, as
#: source text. It is a claim with two halves and both are checked in
#: ``tests/test_predcov.py``: it must equal the SKILL's Step 4+5 fold (eight rows
#: from ``TestStep45FoldIsStructural.SYNTH_ARGUMENTS``, plus ``merge_and_validate``
#: and the OUTPUT block's ``stale_verdict_defects``, both re-derived from
#: ``skills/atlas/SKILL.md`` itself), and it must equal what the adapters above
#: really call. Neither check alone is enough: the first leaves the table free to
#: agree with the SKILL while the adapters do something else, and the second leaves
#: the pair free to drift away from the fold together.
ADAPTER_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "script_defects_from": ("ev",),
    "synth_runcheck": ("ev.get('runcheck', {})", "ev.get('verify_cmd', '')"),
    "synth_docs": ("ev.get('docs_clean', True)",),
    "empty_diff_defect": ("diff",),
    "critics_missing_defects": ("loaded_critics",),
    "out_of_scope_defects": ("full_paths", "st['scope_paths']"),
    "dimension_dissent_defects": ("loaded_map",),
    "critics_stale_defects": ("loaded_map", "current_pass"),
    "stale_verdict_defects": ("log_records",),
    "merge_and_validate": ("critics", "script_defects"),
}

#: stem -> (adapter, the control-fixture input names it takes, IN CALL ORDER).
#: The names are the SKILL fold's own variable names, so this table can be diffed
#: against ``skills/atlas/SKILL.md``'s Step 4+5 block by eye. Argument ORDER lives
#: here and nowhere else, because order is a measured hazard in this codebase:
#: ``difftool.git_tree_has_baseline(cwd, sha)`` and ``difftool.change_paths(sha,
#: cwd)`` take the same two strings in OPPOSITE positions and a swap degrades
#: silently to an empty result.
ADAPTERS: dict[str, tuple] = {
    "evidence-incomplete": (emit_evidence_incomplete, ("ev",)),
    "runcheck": (emit_runcheck, ("ev",)),
    "docs-naming": (emit_docs_naming, ("ev",)),
    "empty-diff": (emit_empty_diff, ("diff",)),
    "out-of-scope": (emit_out_of_scope, ("full_paths", "st")),
    "dimension-dissent": (emit_dimension_dissent, ("loaded_map",)),
    "critic-stale": (emit_critic_stale, ("loaded_map", "current_pass")),
    "stale-verdict": (emit_stale_verdict, ("log_records",)),
    "critic-missing": (emit_critic_missing, ("loaded_critics",)),
    "critic-schema": (emit_critic_schema, ("critics", "script_defects")),
}


def load_control(stem: str, controls_dir=None) -> dict:
    """The authored firing/silent control pair for one emitter.

    A missing or malformed fixture is a :class:`ControlFailure`, never a silent
    default: the controls are what separate "this predicate stayed silent" from
    "this adapter is dead", so an absent one must stop the claim, not shrink it.
    """
    root = pathlib.Path(controls_dir) if controls_dir is not None else CONTROLS_DIR
    path = root / ("%s.json" % stem)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ControlFailure("%s: no control fixture at %s (%s)" % (stem, path, exc)) from exc
    try:
        control = json.loads(text)
    except ValueError as exc:
        raise ControlFailure("%s: control fixture %s is not JSON (%s)"
                             % (stem, path, exc)) from exc
    if not isinstance(control, dict):
        raise ControlFailure("%s: control fixture %s is not an object" % (stem, path))
    absent = [k for k in ("emitter", "function", "branch_line", "branch_source",
                          "fires", "silent") if k not in control]
    if absent:
        raise ControlFailure("%s: control fixture %s lacks %s"
                             % (stem, path, ", ".join(absent)))
    return control


def probe_control(stem: str, arm: str, controls_dir=None) -> dict[str, bool]:
    """Run one emitter's control through its ADAPTER, reported under the FIXTURE's name.

    ``arm`` is ``"fires"`` or ``"silent"``. The return is a single-entry mapping
    keyed on the emitter the FIXTURE declares itself to be — not on the ``stem``
    argument and not on the filename. That is the only reason the return is a
    mapping at all: a fixture copy-pasted from another emitter, or filed under the
    wrong name, then answers under a key the caller never asked for and raises
    ``KeyError`` at the call site, rather than quietly passing an assertion about a
    predicate it never exercised.
    """
    if arm not in ("fires", "silent"):
        raise ControlFailure("%s: unknown control arm %r (expected 'fires' or 'silent')"
                             % (stem, arm))
    control = load_control(stem, controls_dir)
    declared = control["emitter"]
    if declared not in ADAPTERS:
        raise ControlFailure("%s: control declares emitter %r, which has no adapter"
                             % (stem, declared))
    adapter, names = ADAPTERS[declared]
    supplied = control[arm]
    if not isinstance(supplied, dict):
        raise ControlFailure("%s: the %r arm is not an object of named inputs" % (stem, arm))
    absent = [n for n in names if n not in supplied]
    if absent:
        raise ControlFailure("%s: the %r arm supplies no %s" % (stem, arm, ", ".join(absent)))
    return {declared: bool(adapter(*[supplied[n] for n in names]))}


def _dict_fields(node) -> tuple[dict[str, ast.AST], bool] | None:
    """``({literal key: value node}, unknown_keys)`` for a dict expression, else None.

    Handles both spellings a defect can be authored in: the ``{"id": ...}``
    literal and the ``dict(id=...)`` call (TA-H3). ``unknown_keys`` is True when
    the expression can carry keys the walk cannot see — ``**spread``, a computed
    key, or a positional ``dict(other, ...)`` merge — because in that case the
    absence of a ``"severity"`` key proves nothing.
    """
    if isinstance(node, ast.Dict):
        fields: dict[str, ast.AST] = {}
        unknown = False
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                fields[key.value] = value
            else:
                unknown = True
        return fields, unknown
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        fields = {}
        unknown = bool(node.args)
        for kw in node.keywords:
            if kw.arg is None:
                unknown = True
            else:
                fields[kw.arg] = kw.value
        return fields, unknown
    return None


def _string_prefix(node) -> tuple[str, bool] | None:
    """``(known leading text, is_complete)`` for a string expression, else None.

    ``is_complete`` is True only when the whole value is known statically. A
    ``%``-format or a ``+`` concatenation contributes its literal left operand and
    nothing more, which is exactly enough to recover a stem that ends in ``":"``.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        left = _string_prefix(node.left)
        return (left[0], False) if left is not None else None
    if isinstance(node, ast.JoinedStr):
        text = ""
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                text += part.value
            else:
                return text, False
        return text, True
    return None


def _static_stem(node) -> str | None:
    """The id stem of a defect literal, or None when it is not statically derivable.

    Derivable in exactly two cases: the id is a complete constant
    (``"stale-verdict"``), or its literal prefix already contains the ``":"`` that
    ends the stem (``"critic-stale:%s" % dimension``). ``"prefix%s" % x`` with no
    colon is NOT derivable — the runtime value could extend the stem itself — and
    the caller turns that into a :class:`DiscoveryFailure` rather than a guess.
    """
    got = _string_prefix(node)
    if got is None:
        return None
    text, complete = got
    head, sep, _rest = text.partition(":")
    return head if (sep or complete) else None


def _blocking_stems(node: ast.AST, where: str, source_label: str) -> list[str]:
    """Every blocking defect stem authored anywhere inside ``node``.

    Walks nested functions and comprehensions too: the counting rule asks what a
    top-level ``def``'s BODY contains, and a literal hidden one scope deeper is
    still that predicate's output.
    """
    stems: list[str] = []
    for sub in ast.walk(node):
        fields = _dict_fields(sub)
        if fields is None:
            continue
        mapping, unknown = fields
        if "id" not in mapping and "severity" not in mapping:
            continue
        line = getattr(sub, "lineno", "?")
        if unknown:
            raise DiscoveryFailure(
                "%s:%s (%s): a defect dict carries keys this walk cannot read "
                "(** spread, computed key, or dict(other, ...) merge); its severity "
                "cannot be established, so N is not countable from this source"
                % (source_label, line, where)
            )
        if "id" not in mapping or "severity" not in mapping:
            continue
        severity = mapping["severity"]
        if not (isinstance(severity, ast.Constant) and isinstance(severity.value, str)):
            raise DiscoveryFailure(
                "%s:%s (%s): id-bearing dict whose \"severity\" is not a constant. "
                "scripts/quality.py:171 already builds defects that way, and a "
                "floorsynth refactor to that idiom would silently shrink the "
                "denominator under a running experiment — so this is a failure, "
                "never a non-match" % (source_label, line, where)
            )
        if severity.value not in _BLOCKING_SEV:
            continue
        stem = _static_stem(mapping["id"])
        if stem is None:
            raise DiscoveryFailure(
                "%s:%s (%s): blocking defect whose \"id\" stem is not statically "
                "derivable; skipping it would shrink N and guessing it would file "
                "every fire under the wrong row" % (source_label, line, where)
            )
        stems.append(stem)
    return stems


def discover_emitters_from_text(
    source: str, source_label: str = "<text>"
) -> tuple[tuple[str, str], ...]:
    """The counting rule, applied to source TEXT. See :func:`discover_emitters`."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise DiscoveryFailure(
            "%s: cannot be parsed, so N cannot be derived: %s" % (source_label, exc)
        ) from exc
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for stem in _blocking_stems(node, node.name, source_label):
                pair = (node.name, stem)
                if pair not in seen:
                    seen.add(pair)
                    pairs.append(pair)
            continue
        # Not a top-level def. A blocking defect authored out here — a hoisted
        # template constant, or one inside a class — is invisible to the counting
        # rule, so N would drop by one with nothing to notice. Loud, not silent.
        outside = _blocking_stems(node, "<not a top-level def>", source_label)
        if outside:
            raise DiscoveryFailure(
                "%s:%s: blocking defect literal(s) %s authored outside any top-level "
                "def. The counting rule counts top-level defs, so this shape would "
                "shrink N silently" % (source_label, getattr(node, "lineno", "?"), outside)
            )
    return tuple(pairs)


def discover_emitters(source_path: str = "scripts/floorsynth.py") -> tuple[tuple[str, str], ...]:
    """AST-derive floorsynth's blocking emitters as (func_name, id_stem) pairs.

    An id-bearing dict whose "severity" is NOT a constant raises DiscoveryFailure rather
    than silently not matching: scripts/quality.py:_d() already uses that builder idiom,
    and a floorsynth refactor to it would silently shrink N under a running experiment.
    A missing source returns () -- git show v1.4.0:scripts/floorsynth.py exits non-zero
    because the file did not exist at that tag, and ABSENT is not the same as 0.

    A relative ``source_path`` resolves against the repository root, not the
    process cwd: the denominator must not depend on where the reader stood.

    RESIDUAL BLIND SPOT, stated rather than papered over: the walk sees only the
    source it is given. A defect built by a helper IMPORTED from another module
    (``from x import _d; return [_d("y", ..., "CRITICAL", ...)]``) carries no dict
    expression here at all, so it is neither counted nor reported — it is the one
    refactor that can still move N without saying so. The in-file version of that
    same refactor IS caught, because the builder's own body is walked.
    """
    path = pathlib.Path(source_path)
    if not path.is_absolute():
        path = _ROOT / path
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError):
        return ()
    return discover_emitters_from_text(text, source_label=str(path))


# ===========================================================================
# THE RECORD — rows{kind}, the corpus replay, and the runtime-observation rows.
#
# RC-05 is why ``rows`` is a mapping of ROW OBJECTS and not a mapping of stems
# to counts. Roadmap §4 names R1 (the ``.atlas-owner`` ownership nonce) and R2
# (recompute-at-print) as Phase 1 COVERAGE ROWS — re-scoped there from
# ``fix/security-audit-v153``, where both shipped as NEW BLOCKING PREDICATES,
# which is the exact generator this phase exists to measure. A schema keyed only
# on the ten emitter stems has nowhere to put them, and both candidate designs
# dropped them for that reason. Every row therefore carries a ``kind``, and only
# ``floorsynth-emitter`` rows are in the denominator.
# ===========================================================================

#: Row kinds. The denominator is defined over :data:`KIND_EMITTER` rows ONLY.
KIND_EMITTER = "floorsynth-emitter"
KIND_RUNTIME = "runtime-observation"

#: The arms the committed prediction is evaluated over (plan §5.1). Membership is
#: the item's DIRECTORY, so widening the numerator requires a visible file move.
COUNTING_ARMS: tuple[str, ...] = ("honest", "historical", "dirty")

#: Arms that exist and never count. ``interrupted`` is the non-vacuity control;
#: ``failopen`` is the §5.4 arm and is added by Task 9.
NON_COUNTING_ARMS: tuple[str, ...] = ("interrupted", "failopen")

#: Declared BEFORE the corpus was registered, per plan §5.2: emitters already
#: known to fire. They stay in the PRIMARY numerator (the roadmap's prediction is
#: evaluated verbatim) and are subtracted only in the labelled secondary.
PRIORS: tuple[str, ...] = ("out-of-scope", "critic-stale")

#: The roadmap's committed threshold, carried verbatim.
THRESHOLD: int = 3

#: The plan's VOID guard (§5.2): fewer than this many emitters supplied with two
#: or more distinct decision-variable values means the corpus CANNOT ANSWER.
VOID_BELOW_VARYING: int = 3

#: R1's proposed runtime home. Read as TEXT from the runtime module, never
#: imported: the row's whole content is whether that module issues a token today.
OWNERSHIP_TOKEN_NAME = ".atlas-owner"
OWNERSHIP_SOURCE = "scripts/ctxstore.py"


class CorpusInputError(RuntimeError):
    """A corpus item's recorded input could not be read, so it was NOT replayed.

    The counterpart of :class:`AdapterInputError`, and the closure of the residual
    that class names: an adapter is handed a VALUE and cannot tell an empty
    artifact from an unreadable one, so the responsibility for that distinction
    lives here, at the only place that touches files. A missing ``det_evidence.json``
    raises; it never becomes ``ev = {}``, which through ``floorsynth`` itself would
    manufacture a ``runcheck`` CRITICAL and a ``docs-naming`` silence on every item
    at once.
    """


def _read_text(path: pathlib.Path) -> str:
    """File text, or :class:`CorpusInputError`. Never an empty-string fallback."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CorpusInputError("%s: unreadable (%s)" % (path, exc)) from exc


def _read_json(path: pathlib.Path):
    """Parsed JSON, or :class:`CorpusInputError`. Never an empty-object fallback."""
    text = _read_text(path)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise CorpusInputError("%s: not JSON (%s)" % (path, exc)) from exc


def _read_jsonl(path: pathlib.Path) -> list[dict]:
    """Every parsable record of a ``.jsonl`` ledger, or :class:`CorpusInputError`.

    An unparsable LINE is an error, not a skipped record: a ledger the instrument
    silently shortened would change the stage shape ``stale_verdict_defects``
    judges, which is the one emitter whose whole input is that shape.
    """
    out: list[dict] = []
    for number, line in enumerate(_read_text(path).splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError as exc:
            raise CorpusInputError("%s:%d: not JSON (%s)" % (path, number, exc)) from exc
    return out


def _read_paths(path: pathlib.Path) -> list[str]:
    """A ``tree.paths`` file as a list of paths."""
    return [line for line in _read_text(path).splitlines() if line]


# ---------------------------------------------------------------------------
# Per-arm input construction. Each builder returns the SKILL's Step 4+5 NAMESPACE
# — the same variable names the fold uses — so ``ADAPTERS``' declared argument
# names index straight into it and the marshalling has exactly one spelling.
# ---------------------------------------------------------------------------


def run_item_inputs(item_dir: pathlib.Path, meta: dict) -> dict:
    """The Step 4+5 namespace rebuilt from one recorded-run item (arms A and B).

    ``full_paths`` is present ONLY when the item recorded ``tree.paths``. Its
    absence is the record that the whole-tree change list is unreconstructible
    (CQ2), and this builder must never substitute ``[]`` — that value is what a
    live ``difftool.change_paths`` returns on a non-git tree, and it renders as
    "measured, nothing outside scope".
    """
    from scripts import floorsynth

    critics: list[dict] = []
    loaded_critics: list[str] = []
    for name, _dim in floorsynth.CRITIC_ARTIFACTS:
        critics.append(_read_json(item_dir / name))
        loaded_critics.append(name)

    current_pass = meta.get("refine_passes")
    inputs = {
        "ev": _read_json(item_dir / "det_evidence.json"),
        "diff": _read_text(item_dir / "diff.patch"),
        "st": _read_json(item_dir / "state.json"),
        "critics": critics,
        "loaded_critics": loaded_critics,
        "loaded_map": dict(zip(loaded_critics, critics)),
        "log_records": _read_jsonl(item_dir / "log.eval.jsonl"),
    }
    if isinstance(current_pass, int) and not isinstance(current_pass, bool):
        inputs["current_pass"] = current_pass
    if (item_dir / "tree.paths").is_file():
        inputs["full_paths"] = _read_paths(item_dir / "tree.paths")
    return inputs


def historical_item_inputs(item_dir: pathlib.Path, meta: dict) -> dict:
    """The namespace one release interval supplies (arm C).

    Two emitters and no more. ``out-of-scope`` gets the tag range's real changed
    path list against a whole-tree scope — the second value of that decision
    variable, and one nobody authored. ``docs-naming`` gets a ``docs_clean``
    DERIVED by running the repo's own ``check_artifact_naming.check_file`` over the
    interval's changed ``.md`` files, unpacked as ``errs, _warns`` (H5: that call
    returns a 2-TUPLE, and reading it as a truth value would make ``docs_clean``
    False on every interval and fire ``docs-naming`` five times out of five).

    ``empty-diff`` is deliberately NOT supplied. The arm stores a ``--numstat``
    summary and the command that regenerates the patch, not ~1.2 MB of vendored
    release diff, so the emitter's own argument is not on disk; the cell is
    reported ``unmeasured``, never as a non-empty diff inferred from a byte count.
    """
    from scripts import check_artifact_naming as can

    changed_md = [p for p in meta.get("changed_md") or [] if isinstance(p, str)]
    docs_errors: list[str] = []
    for rel in changed_md:
        errs, _warns = can.check_file(_ROOT, rel)
        docs_errors += list(errs)
    return {
        "full_paths": _read_paths(item_dir / "tree.paths"),
        "st": {"scope_paths": list(meta.get("scope_paths") or [])},
        "ev": {"docs_clean": not docs_errors},
        "docs_checked": len(changed_md),
        "docs_errors": docs_errors,
    }


def dirty_item_inputs(item_dir: pathlib.Path, meta: dict) -> dict:
    """The namespace the documented dirty-tree shape supplies (arm D).

    One emitter. The expectation is NOT authored here or in the fixture: it is
    documented at ``CHANGELOG.md``:48-57 and cross-pinned by
    ``tests/test_v1521_regressions.py``, independently of this item.
    """
    return {
        "full_paths": _read_paths(item_dir / "tree.paths"),
        "st": {"scope_paths": list(meta.get("scope_paths") or [])},
    }


ARM_INPUT_BUILDERS = {
    "honest": run_item_inputs,
    "interrupted": run_item_inputs,
    "historical": historical_item_inputs,
    "dirty": dirty_item_inputs,
}

#: Which emitters each arm DECLARES it supplies real inputs for. Not decoration and
#: not an optimisation — it is a TA-C1 guard, and it was added because the corpus
#: manufactured a fire without it.
#:
#: The SKILL's fold reads three emitters out of ONE ``ev`` dict, so an arm that can
#: derive only ``docs_clean`` still presents a name called ``ev``. Measured: fed the
#: release-history arm's two-key evidence dict, ``script_defects_from`` reports every
#: mandatory lens key absent and ``evidence-incomplete`` FIRES on all four intervals
#: — four fires of a predicate nobody measured, in the numerator, from a dict this
#: module wrote. ``runcheck`` on the same dict raises instead, which is louder but
#: no more correct: the key is not lost, it was never part of this arm.
#:
#: The recorded-run arms declare all ten by construction, so nothing can be hidden
#: there. The derived arms declare only what their own source establishes, and
#: ``tests/test_predcov.py`` pins the hazard directly rather than trusting the list.
ARM_SUPPLIES: dict[str, tuple[str, ...]] = {
    "honest": EMITTERS,
    "interrupted": EMITTERS,
    # tree.paths against the interval's recorded scope; docs_clean re-derived by
    # running check_artifact_naming over the interval's own changed .md files.
    "historical": ("out-of-scope", "docs-naming"),
    # The documented dirty-tree path list against a narrow scope, and nothing else.
    "dirty": ("out-of-scope",),
}


# ---------------------------------------------------------------------------
# THE DECLARED DIMENSION ACCESSORS (the D1/TA-C2 fold).
#
# Design A's ``reachable`` column is DELETED, not repaired: it measured argument
# PRESENCE, so it printed "reachable 10 of 10" for eight emitters handed one
# constant value, converting the most important zero-supply row into apparent
# evidence of restraint. What replaces it is a declared accessor per emitter,
# returning that emitter's OWN DECISION VARIABLES as a hashable — plan §4's rule,
# spelled out. Two or more distinct values across the counting arms is VARYING;
# one is CONSTANT; none is BLIND.
#
# Stated because it bounds every conclusion: for several emitters the decision
# variable IS the branch outcome (``docs_clean``; ``schema_errors``; the count of
# out-of-scope paths). For those, "the corpus supplied two values" and "the corpus
# contains a firing input" are the same sentence, and VARYING must not be read as
# "the corpus exercised everything upstream of the branch" — only as "the corpus
# presented both sides of the branch this predicate actually tests".
# ---------------------------------------------------------------------------


def _dim_evidence_incomplete(inputs) -> tuple:
    """Which mandatory evidence keys are absent or NULL — the emitter's own test."""
    from scripts import floorsynth

    ev = inputs["ev"]
    keys = floorsynth.MANDATORY_EVIDENCE_KEYS + floorsynth.MANDATORY_FLAG_KEYS
    return tuple(sorted(k for k in keys if not isinstance(ev, dict) or ev.get(k) is None))


def _dim_runcheck(inputs) -> tuple:
    """``runcheck.green``'s three conjuncts, unreduced (plan §4's own triple)."""
    rc = inputs["ev"].get("runcheck")
    rc = rc if isinstance(rc, dict) else {}
    return (bool(rc.get("ok")), rc.get("test_count", 0) > 0,
            bool(rc.get("new_tests_collected")))


def _dim_docs_naming(inputs) -> tuple:
    """``synth_docs``' single flag. Its ONLY argument, so its only decision variable."""
    return (bool(inputs["ev"].get("docs_clean")),)


def _dim_empty_diff(inputs) -> tuple:
    """``(diff or "").strip()`` as a bool — the emitter's whole branch."""
    return (bool((inputs["diff"] or "").strip()),)


def _dim_out_of_scope(inputs) -> tuple:
    """How many changed paths fall outside scope.

    Deliberately NOT ``(whole_tree_scope, count)``, though that pair is the more
    informative one: establishing whole-tree-ness means calling
    ``floorsynth._normalize_scopes``, a PRIVATE function of a frozen module, and
    re-implementing its three whole-tree spellings here would be a fourth hand-copy
    of runtime logic. The item's recorded ``scope_paths`` is reported beside the row
    instead, as data rather than as a re-derivation.
    """
    return (len(defects_out_of_scope(inputs["full_paths"], inputs["st"])),)


def _dim_dimension_dissent(inputs) -> tuple:
    """Per critic: the dimensions marked ``no``, the verdict, and whether it blocks."""
    from scripts import floorsynth

    out = []
    for name, _dim in floorsynth.CRITIC_ARTIFACTS:
        critic = inputs["loaded_map"].get(name)
        if not isinstance(critic, dict):
            out.append((name, None, None, None))
            continue
        dims = critic.get("dimensions") if isinstance(critic.get("dimensions"), dict) else {}
        defects = critic.get("defects") if isinstance(critic.get("defects"), list) else []
        out.append((
            name,
            tuple(sorted(d for d, v in dims.items() if v == "no")),
            critic.get("verdict"),
            any(isinstance(d, dict) and d.get("severity") in _BLOCKING_SEV for d in defects),
        ))
    return tuple(out)


def _dim_critic_stale(inputs) -> tuple:
    """Each artifact's currency stamp against the run's current pass."""
    from scripts import floorsynth

    stamps = []
    for name, _dim in floorsynth.CRITIC_ARTIFACTS:
        critic = inputs["loaded_map"].get(name)
        stamps.append((name, critic.get("pass") if isinstance(critic, dict) else None))
    return (inputs["current_pass"], tuple(stamps))


def _dim_stale_verdict(inputs) -> tuple:
    """The ledger's normalized stage SEQUENCE — the only thing this emitter reads."""
    stages = [r.get("stage") for r in inputs["log_records"] if isinstance(r, dict)]
    stages = [s for s in stages if isinstance(s, str) and s != "ROLLBACK"]
    return tuple(s for i, s in enumerate(stages) if i == 0 or s != stages[i - 1])


def _dim_critic_missing(inputs) -> tuple:
    """Which of the three judgment artifacts loaded."""
    return tuple(sorted(inputs["loaded_critics"]))


def _dim_critic_schema(inputs) -> tuple:
    """``enforce_critic_schema``'s findings on the merged shape.

    The frankest of the accessors: ``merge_and_validate`` has no branch of its own
    to project onto, so its decision variable is the validator's own output. Plan
    §4 declares it the same way (``schema_errors = []``).
    """
    _merged, schema_errors = merge_fold(inputs["critics"], list(inputs["script_defects"]))
    return tuple(sorted(schema_errors))


#: stem -> the declared accessor. Closed against :data:`EMITTERS` by a test.
DIMENSIONS = {
    "evidence-incomplete": _dim_evidence_incomplete,
    "runcheck": _dim_runcheck,
    "docs-naming": _dim_docs_naming,
    "empty-diff": _dim_empty_diff,
    "out-of-scope": _dim_out_of_scope,
    "dimension-dissent": _dim_dimension_dissent,
    "critic-stale": _dim_critic_stale,
    "stale-verdict": _dim_stale_verdict,
    "critic-missing": _dim_critic_missing,
    "critic-schema": _dim_critic_schema,
}


def _hashable(value):
    """A stable, hashable, JSON-renderable form of a dimension value."""
    if isinstance(value, (list, tuple)):
        return tuple(_hashable(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _hashable(v)) for k, v in value.items()))
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def replay_item(inputs: dict, supplies=EMITTERS) -> dict:
    """Replay every emitter this item's arm supplies. See :data:`ARM_SUPPLIES`.

    Returns ``{stem: {"state", "fired", "dimension", "error"}}``. Three states and
    they mean three different things, which is the whole reason the report has a
    ``— (constant)`` rendering and a ``—`` rendering and never a bare ``0``:

      * ``measured``    — the emitter was called with this item's real inputs;
      * ``unmeasured``  — this arm supplies no argument for it (a release interval
        has no critic artifacts; a run item with no ``tree.paths`` has no
        whole-tree path list). NOT a silence;
      * ``error``       — the arguments were there and the adapter REFUSED them, or
        the emitter raised. Any error anywhere suppresses the verdict line and
        prints ``ADAPTER DEGRADED``; it is never a silence either.
    """
    local = dict(inputs)
    if "ev" in local:
        try:
            local["script_defects"] = all_script_defects(local["ev"])
        except Exception:                                   # pragma: no cover - defensive
            local["script_defects"] = []

    out: dict[str, dict] = {}
    for stem in EMITTERS:
        adapter, names = ADAPTERS[stem]
        if stem not in supplies:
            out[stem] = {"state": "unmeasured", "fired": None, "dimension": None,
                         "error": "", "reason": "this arm supplies no input for it"}
            continue
        missing = [n for n in names if n not in local]
        if missing:
            out[stem] = {"state": "unmeasured", "fired": None, "dimension": None,
                         "error": "", "reason": "no %s in this arm" % ", ".join(missing)}
            continue
        row = {"state": "measured", "fired": None, "dimension": None,
               "error": "", "reason": ""}
        try:
            row["fired"] = bool(adapter(*[local[n] for n in names]))
        except Exception as exc:
            row.update({"state": "error", "fired": None,
                        "error": "%s: %s" % (type(exc).__name__, exc)})
            out[stem] = row
            continue
        try:
            row["dimension"] = _hashable(DIMENSIONS[stem](local))
        except Exception as exc:
            row.update({"state": "error", "error": "dimension: %s: %s"
                                                   % (type(exc).__name__, exc)})
        out[stem] = row
    return out


def _blocking_ids(defects) -> list[str]:
    """The sorted ids of the blocking defects in a merged critic's defect list."""
    return sorted(str(d.get("id")) for d in defects or ()
                  if isinstance(d, dict) and d.get("severity") in _BLOCKING_SEV)


def recompute_delta(item_dir: pathlib.Path, inputs: dict) -> dict:
    """R2 — recompute-at-print, as a REPORT ROW. Blocks nothing.

    ``fix/security-audit-v153`` shipped this as a new blocking predicate: recompute
    the verdict at the moment of printing and refuse to print if it differs. The
    roadmap re-scoped it to a coverage row precisely because "a new blocking
    predicate over an unenumerated state space" is the generator this phase is
    measuring. So the delta is RECORDED and nothing is refused.

    It is also the RC-04 fold. ``after-t3-a``'s recorded ``merged_critic.json``
    says ``OK`` with zero blocking defects while the replay manufactures defects the
    machine never emitted; a corpus whose non-vacuity control was itself a replay
    artifact would certify nothing. Divergent items are excluded from every count.

    ``basis`` is honest about what the comparison rests on: ``complete`` only when
    every argument of the fold was on disk. An item with no ``tree.paths`` cannot
    reproduce the out-of-scope contribution, and its delta is reported ``partial``
    rather than being computed against a fabricated empty path list.
    """
    recorded = _read_json(item_dir / "merged_critic.json")
    if not isinstance(recorded, dict):
        raise CorpusInputError("%s: merged_critic.json is not an object" % item_dir)

    # The SKILL's Step 4+5 fold order, through this module's single call sites.
    script_defects = list(all_script_defects(inputs["ev"]))
    script_defects += defects_runcheck(inputs["ev"])
    script_defects += defects_docs_naming(inputs["ev"])
    script_defects += defects_empty_diff(inputs["diff"])
    script_defects += defects_critic_missing(inputs["loaded_critics"])
    basis_missing = [n for n in ("full_paths", "current_pass") if n not in inputs]
    if "current_pass" in inputs:
        script_defects += defects_critic_stale(inputs["loaded_map"], inputs["current_pass"])
    script_defects += defects_dimension_dissent(inputs["loaded_map"])
    if "full_paths" in inputs:
        script_defects += defects_out_of_scope(inputs["full_paths"], inputs["st"])
    basis = "partial:%s" % ",".join(basis_missing) if basis_missing else "complete"
    merged, schema_errors = merge_fold(inputs["critics"], script_defects)
    # The OUTPUT block folds this one AFTER the merge and writes it back.
    stale = defects_stale_verdict(inputs["log_records"])
    replayed_ids = sorted(set(_blocking_ids(merged.get("defects")))
                          | set(_blocking_ids(stale)))
    recorded_ids = _blocking_ids(recorded.get("defects"))
    added = sorted(set(replayed_ids) - set(recorded_ids))
    removed = sorted(set(recorded_ids) - set(replayed_ids))
    return {
        "basis": basis,
        "recorded_verdict": recorded.get("verdict"),
        "replayed_verdict": "FAIL" if (replayed_ids or stale) else merged.get("verdict"),
        "recorded_blocking_ids": recorded_ids,
        "replayed_blocking_ids": replayed_ids,
        "added_blocking_ids": added,
        "removed_blocking_ids": removed,
        "schema_errors": list(schema_errors),
        "divergent": bool(added or removed),
    }


def ownership_observation(items: list[dict], source_path=None) -> dict:
    """R1 — the ``.atlas-owner`` ownership nonce, as a REPORT ROW. Blocks nothing.

    Two independent halves, and neither is an opinion of this module's.

    RUNTIME: does ``scripts/ctxstore.py`` issue an ownership token at all? Read as
    TEXT from the runtime module this instrument may not modify. Measured at HEAD it
    does not — ``ctxstore.init_run`` writes no ``.atlas-owner`` — so the token is
    not merely absent from these runs, it does not exist. The row flips to
    ``implemented`` on the day R1 ships, without anyone editing this function.

    CORPUS: how many recorded items carry a token. Zero, necessarily, since none was
    ever issued.

    THE HONEST CAVEAT, and it is the whole meaning of the row: these runs PRE-DATE
    the proposal, so ``0 of 12 owned`` is a BASELINE, not R1's false-RED rate. What
    it does establish is the thing the re-scope was for: promoted to a blocking
    predicate today, R1 refuses every run in this corpus, and the corpus contains no
    honest run it would accept. That is a fact about the promotion, measured before
    it happens, which is exactly what a coverage row is for.

    ``source_path`` exists so the row has a POSITIVE control. Today both the row and
    any test of it read ``False``, so a hard-coded ``implemented=False`` is
    indistinguishable from a reading of the runtime — the vacuity this project has
    been bitten by five times. Pointed at a source that DOES issue a token, this
    function must report ``implemented=True``, and only a real read does that.
    """
    source = pathlib.Path(source_path) if source_path is not None else _ROOT / OWNERSHIP_SOURCE
    try:
        text = source.read_text(encoding="utf-8")
        readable = True
    except OSError:
        text, readable = "", False
    owned = sum(1 for it in items if it.get("ownership_token") not in (None, ""))
    replayable = [it for it in items if it.get("kind") == "recorded-run"]
    return {
        "kind": KIND_RUNTIME,
        "roadmap_id": "R1",
        "title": "ownership nonce (%s)" % OWNERSHIP_TOKEN_NAME,
        "blocks": False,
        "counts_toward_prediction": False,
        "source": "%s (text) + the recorded-run items' own directories" % OWNERSHIP_SOURCE,
        "runtime_source": str(source.relative_to(_ROOT)) if _ROOT in source.parents
                          else str(source),
        "runtime_source_readable": readable,
        "implemented": OWNERSHIP_TOKEN_NAME in text,
        "runs_examined": len(replayable),
        "runs_carrying_a_token": owned,
        "observation": (
            "%s issues no %s at HEAD, so every recorded run is unowned"
            % (OWNERSHIP_SOURCE, OWNERSHIP_TOKEN_NAME)
            if OWNERSHIP_TOKEN_NAME not in text else
            "%s issues %s; %d of %d recorded runs carry one"
            % (OWNERSHIP_SOURCE, OWNERSHIP_TOKEN_NAME, owned, len(replayable))
        ),
        "caveat": (
            "these runs pre-date the R1 proposal, so this is a BASELINE and not a "
            "false-RED rate; what it does establish is that R1 promoted to a "
            "blocking predicate today would refuse every item in this corpus"
        ),
    }


# ---------------------------------------------------------------------------
# THE FAIL-OPEN ARM (the C1 fold) — the side of the dial a fire count cannot see.
#
# The diagnosis is two-sided: too narrow and a predicate fails OPEN; too wide and
# it fires on honest input. A fire count measures one side. Of the eight injections
# the record counts, THREE are fail-opens — silences — so this metric can see at
# most 3 of 8, and that ceiling is printed on the verdict line. This arm records
# the other side: per documented fail-open, an input the predicate SHOULD have
# fired on, replayed against HEAD, with what actually happened.
#
# IT EVALUATES THROUGH THE SKILL'S MARSHALLING, NOT THROUGH THE ADAPTERS, and the
# distinction is the whole mechanism. The adapters REFUSE an absent key, correctly:
# for a corpus item an absent key is a read failure, and the SKILL's ``.get``
# default would report a blinded predicate as restraint. But a fail-open IS that
# default being taken — the v1.5.0 hole is exactly ``ev.get("docs_clean", True)``
# on evidence that never carried the key. Routed through the adapter it raises;
# routed through the SKILL's own expression it is observable. So the argument
# expressions are replayed from :data:`ADAPTER_ARGUMENTS`, which Task 7 binds to
# ``skills/atlas/SKILL.md`` itself — the defaults are the SKILL's, not this
# module's opinion of them.
# ---------------------------------------------------------------------------


def marshal_skill_argument(expr: str, namespace: dict):
    """Evaluate ONE Step 4+5 argument expression against a namespace. Never ``eval``.

    Exactly three shapes, because the fold contains exactly three: a bare name
    (``diff``), a subscript with a literal key (``st['scope_paths']``), and a
    ``.get`` with a literal key and a literal default (``ev.get('docs_clean',
    True)``). Anything else is a :class:`ControlFailure` rather than a skip: a
    skipped argument becomes a POSITIONAL SHIFT, and this codebase has already
    measured what that costs — ``git_tree_has_baseline(cwd, sha)`` and
    ``change_paths(sha, cwd)`` take the same two strings in opposite positions and
    a swap degrades silently to an empty result.
    """
    try:
        node = ast.parse(expr, mode="eval").body
    except SyntaxError as exc:
        raise ControlFailure("%r: not an expression (%s)" % (expr, exc)) from exc

    if isinstance(node, ast.Name):
        if node.id not in namespace:
            raise ControlFailure("%r: the namespace supplies no %s" % (expr, node.id))
        return namespace[node.id]

    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
        base = marshal_skill_argument(node.value.id, namespace)
        if not isinstance(base, dict) or node.slice.value not in base:
            raise ControlFailure("%r: %s has no key %r"
                                 % (expr, node.value.id, node.slice.value))
        return base[node.slice.value]

    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get" and isinstance(node.func.value, ast.Name)
            and not node.keywords and len(node.args) == 2
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)):
        base = marshal_skill_argument(node.func.value.id, namespace)
        if not isinstance(base, dict):
            raise ControlFailure("%r: %s is not a mapping" % (expr, node.func.value.id))
        try:
            default = ast.literal_eval(node.args[1])
        except ValueError as exc:
            raise ControlFailure("%r: the default is not a literal (%s)" % (expr, exc)) from exc
        return base.get(node.args[0].value, default)

    raise ControlFailure(
        "%r: not one of the three Step 4+5 argument shapes (name, name['key'], "
        "name.get('key', literal)) — refused rather than guessed, because a "
        "mis-marshalled argument is a positional shift, not a missing value" % expr
    )


def probe_failopen(function: str, stem: str, namespace: dict) -> dict:
    """Replay ONE emitter on an authored should-fire namespace. Report only.

    ``silent_at_head`` is the finding, and it is genuinely two-valued: a documented
    fail-open that HEAD now catches reports ``False``, which is the arm's own
    non-vacuity control — without at least one such case, an evaluator hard-coded to
    "still silent" would print the most flattering possible reading of this
    instrument's own subject matter and nothing in the corpus could contradict it.
    """
    from scripts import floorsynth

    if function not in ADAPTER_ARGUMENTS:
        raise ControlFailure("%s: no Step 4+5 marshalling is declared for %r"
                             % (stem, function))
    if not isinstance(namespace, dict):
        raise ControlFailure("%s: the namespace is not an object of named inputs" % stem)
    arguments = [marshal_skill_argument(expr, namespace)
                 for expr in ADAPTER_ARGUMENTS[function]]

    if function == "merge_and_validate":
        _merged, schema_errors = merge_fold(*arguments)
        return {"function": function, "emitter": stem, "arguments": arguments,
                "silent_at_head": not schema_errors, "defect_ids": [],
                "schema_errors": list(schema_errors)}

    produced = getattr(floorsynth, function)(*arguments)
    return {
        "function": function,
        "emitter": stem,
        "arguments": arguments,
        "silent_at_head": not fired(stem, produced),
        "defect_ids": sorted(str(d.get("id")) for d in produced or ()
                             if isinstance(d, dict)),
        "schema_errors": [],
    }


def evaluate_failopen_item(item_dir: pathlib.Path, meta: dict) -> dict:
    """One fail-open item: the named emitter's silence, and who else caught it.

    ``covered_by`` is the honest completion of the row and it changes the answer.
    Measured on the v1.5.0 ``docs_clean`` fail-open: ``synth_docs`` is STILL silent
    at HEAD — the ``True`` default is unchanged — but ``script_defects_from`` fires
    ``evidence-incomplete`` on the same evidence, because ``docs_clean`` was added
    to ``MANDATORY_FLAG_KEYS``. Reporting only the named emitter would print that
    hole as open when a different predicate closed it, which is precisely the
    "predicate too narrow" conclusion this arm exists to keep honest.
    """
    namespace = meta.get("namespace")
    probe = probe_failopen(meta["function"], meta["emitter"], namespace)
    functions = function_of_stem()
    covered_by = []
    for stem in EMITTERS:
        if stem == meta["emitter"] or stem not in functions:
            continue
        try:
            other = probe_failopen(functions[stem], stem, namespace)
        except ControlFailure:
            continue                      # this namespace cannot feed that emitter
        if not other["silent_at_head"]:
            covered_by.append(stem)
    return {
        "emitter": meta["emitter"],
        "function": meta["function"],
        "injection": meta.get("injection", ""),
        "should_fire_because": meta.get("should_fire_because", ""),
        "expectation_sources": list(meta.get("expectation_sources") or []),
        "silent_at_head": probe["silent_at_head"],
        "defect_ids": probe["defect_ids"],
        "schema_errors": probe["schema_errors"],
        "covered_by": sorted(covered_by),
        "status": ("STILL OPEN" if probe["silent_at_head"] and not covered_by
                   else "COVERED BY ANOTHER PREDICATE" if probe["silent_at_head"]
                   else "CLOSED SINCE"),
    }


def function_of_stem() -> dict[str, str]:
    """id stem -> the floorsynth function that emits it.

    DERIVED, and computed on call rather than at import. Derived because a
    hand-maintained second copy of the pairing is the CQ3 failure — rename the id
    and the copy stays green while the row reads 0 forever. On call because this
    module must import even when the denominator cannot be counted: a
    :class:`DiscoveryFailure` at import time would make the instrument unable to
    report that it broke, which is the one thing it must always be able to do.
    """
    try:
        return {stem: func for func, stem in discover_emitters()}
    except DiscoveryFailure:
        return {}


def _corpus_items(corpus_root: pathlib.Path) -> list[tuple[str, str, pathlib.Path]]:
    """``(arm, item_id, dir)`` for every item directory, in sorted order.

    Sorted at every level, and derived from the FILESYSTEM rather than from
    ``manifest.json``: arm membership is a directory (plan §5.1), so a manifest that
    disagreed with the tree could not quietly widen the counting arms.
    """
    found: list[tuple[str, str, pathlib.Path]] = []
    for arm in sorted(COUNTING_ARMS + NON_COUNTING_ARMS):
        arm_dir = corpus_root / arm
        if not arm_dir.is_dir():
            continue
        for item_dir in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
            found.append((arm, "%s/%s" % (arm, item_dir.name), item_dir))
    return found


def evaluate_corpus(corpus_root: str = "tests/corpus") -> dict:
    """Replay the whole corpus and return the RECORD. Report only; blocks nothing.

    The record's shape is the RC-05 fold: ``rows`` is keyed by row id and every row
    declares a ``kind``, so the ten ``floorsynth-emitter`` rows and the two
    ``runtime-observation`` rows (R1, R2) live in one table while only the former
    are the denominator. ``denominator.emitters`` is DERIVED by
    :func:`discover_emitters`, never listed by hand, so an eleventh predicate cannot
    join the table without joining the denominator.
    """
    root = pathlib.Path(corpus_root)
    if not root.is_absolute():
        root = _ROOT / root
    errors: list[str] = []

    try:
        pairs = discover_emitters()
        derived = sorted({stem for _f, stem in pairs})
        discovery_error = ""
    except DiscoveryFailure as exc:
        pairs, derived, discovery_error = (), sorted(EMITTERS), str(exc)
        errors.append("DISCOVERY FAILURE: %s" % exc)

    items: list[dict] = []
    for arm, item_id, item_dir in _corpus_items(root):
        item = {"id": item_id, "arm": arm, "dir": str(item_dir.relative_to(_ROOT))
                if _ROOT in item_dir.parents else str(item_dir)}
        try:
            meta = _read_json(item_dir / "item.json")
            if not isinstance(meta, dict):
                raise CorpusInputError("%s: item.json is not an object" % item_dir)
        except CorpusInputError as exc:
            item.update({"kind": "", "errors": [str(exc)], "emitters": {}, "counts": False})
            items.append(item)
            errors.append(str(exc))
            continue

        item["kind"] = meta.get("kind", "")
        item["label"] = meta.get("label", item_dir.name)
        item_errors: list[str] = []
        # R1's corpus half. No run ever wrote one; the file is looked for anyway,
        # so the day one is captured the row moves without a code change.
        token_file = item_dir / OWNERSHIP_TOKEN_NAME.lstrip(".")
        item["ownership_token"] = (token_file.read_text(encoding="utf-8").strip()
                                   if token_file.is_file() else None)

        if arm == "failopen":
            # §5.4. Evaluated through the SKILL's marshalling, reported as its own
            # block, and structurally unable to reach the emitter rows: it carries
            # no ``emitters`` mapping at all, so ``_emitter_rows`` never sees it.
            try:
                item["failopen"] = evaluate_failopen_item(item_dir, meta)
            except (ControlFailure, KeyError, TypeError) as exc:
                item_errors.append("failopen: %s: %s" % (type(exc).__name__, exc))
                errors.append("%s: %s" % (item_id, item_errors[-1]))
            item.update({"errors": item_errors, "emitters": {}, "counts": False,
                         "replay_divergent": False})
            items.append(item)
            continue

        builder = ARM_INPUT_BUILDERS.get(arm)
        if builder is None:
            item.update({"errors": ["no input builder for arm %r" % arm],
                         "emitters": {}, "counts": False})
            items.append(item)
            continue
        try:
            inputs = builder(item_dir, meta)
        except CorpusInputError as exc:
            item.update({"errors": [str(exc)], "emitters": {}, "counts": False})
            items.append(item)
            errors.append(str(exc))
            continue

        item["supplies"] = list(ARM_SUPPLIES.get(arm, ()))
        item["scope_paths"] = list(meta.get("scope_paths") or [])
        item["emitters"] = replay_item(inputs, ARM_SUPPLIES.get(arm, ()))
        item_errors += [r["error"] for r in item["emitters"].values() if r["error"]]

        if item["kind"] == "recorded-run":
            try:
                item["recompute"] = recompute_delta(item_dir, inputs)
            except Exception as exc:                        # pragma: no cover - defensive
                item_errors.append("recompute: %s: %s" % (type(exc).__name__, exc))
        item["errors"] = item_errors
        errors += ["%s: %s" % (item_id, e) for e in item_errors]
        item["replay_divergent"] = bool(item.get("recompute", {}).get("divergent"))
        item["counts"] = (arm in COUNTING_ARMS and not item["replay_divergent"]
                          and not item_errors)
        items.append(item)

    rows = _emitter_rows(items, derived, pairs)
    replayed = [it for it in items if "recompute" in it]
    rows["ownership-nonce"] = ownership_observation(items)
    rows["recompute-delta"] = {
        "kind": KIND_RUNTIME,
        "roadmap_id": "R2",
        "title": "recompute-at-print delta",
        "blocks": False,
        "counts_toward_prediction": False,
        "source": "each item's recorded merged_critic.json vs the replayed fold",
        "items_compared": len(replayed),
        "divergent_items": sorted(it["id"] for it in replayed
                                  if it["recompute"]["divergent"]),
        "partial_basis_items": sorted(it["id"] for it in replayed
                                      if it["recompute"]["basis"] != "complete"),
        "observation": ("%d of %d replayed items disagree with their recorded verdict"
                        % (sum(1 for it in replayed if it["recompute"]["divergent"]),
                           len(replayed))),
        "caveat": ("a divergence is not proof the run was wrong: the replay evaluates "
                   "the TERMINAL pass only, and the pass-1 evaluations that forced a "
                   "refine were overwritten in place"),
    }

    counts: dict[str, int] = {}
    for item in items:
        counts[item["arm"]] = counts.get(item["arm"], 0) + 1

    report = {
        "schema": "predcov-report/1",
        "report_only": True,
        "corpus": {
            "root": str(root.relative_to(_ROOT)) if _ROOT in root.parents else str(root),
            "items": len(items),
            "by_arm": dict(sorted(counts.items())),
            "counting_arms": list(COUNTING_ARMS),
            "provenance_warning": (
                ".atlas/ was coder-writable during recording; the recorded-run "
                "artifacts are model-influenced, not machine-attested"
            ),
        },
        "denominator": {
            "n": len(derived),
            "emitters": derived,
            "source": "scripts/floorsynth.py",
            "source_sha256": _source_sha256(),
            "rule": ("one top-level def emitting a dict with \"id\" + a CONSTANT "
                     "\"severity\" in rubric.BLOCKING"),
            "discovery_error": discovery_error,
        },
        "firing_rule": ("at least one defect whose id STEM is this emitter's own AND "
                        "whose severity is in rubric.BLOCKING; once per emitter per "
                        "item, never once per defect"),
        "rows": rows,
        "arms": _arm_blocks(items),
        "prediction": _prediction(rows, derived, bool(errors)),
        "items": items,
        "errors": sorted(errors),
        "degraded": bool(errors),
    }
    return report


def _source_sha256() -> str:
    """The sha256 of the floorsynth source the denominator was derived from.

    Provenance without a clock: the record must be byte-identical across two runs
    (TA-H2/CQ15 runs the CLI in two subprocesses and compares), so a timestamp is
    not available to say *which* floorsynth this is.
    """
    import hashlib

    try:
        data = (_ROOT / "scripts" / "floorsynth.py").read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()


#: What each arm is FOR, and whether it counts. Written down because "counts" is
#: the single most riggable property of this experiment: plan §5.1 makes arm
#: membership a DIRECTORY so that widening the numerator requires a visible file
#: move in a diff, and this table is the other half of that — the role is stated
#: next to the flag, so a silent change to either reads as a contradiction.
ARM_ROLES: dict[str, str] = {
    "honest": "recorded runs, rc=0 and a ledger ending at OUTPUT — the counting arm",
    "interrupted": "the non-vacuity control, and nothing else; never counts",
    "historical": "release intervals from this repo's own tags — real changed .md, "
                  "and a whole-tree scope nobody authored",
    "dirty": "the one shape the record documents as an honest false RED",
    "failopen": "§5.4: inputs a predicate SHOULD fire on. Reported alone; it does "
                "not move the primary denominator, because a fire count cannot "
                "see a silence and this arm is made of silences",
}


def _arm_blocks(items: list[dict]) -> dict:
    """Per-arm summary, with the fail-open arm's findings carried inside its own block."""
    blocks: dict[str, dict] = {}
    for arm in sorted(set(COUNTING_ARMS + NON_COUNTING_ARMS)):
        members = [it for it in items if it["arm"] == arm]
        if not members:
            continue
        block = {
            "items": len(members),
            "counts": arm in COUNTING_ARMS,
            "role": ARM_ROLES.get(arm, ""),
            "item_ids": sorted(it["id"] for it in members),
        }
        if arm == "failopen":
            findings = [it["failopen"] for it in members if it.get("failopen")]
            block["observations"] = sorted(findings, key=lambda f: f["emitter"])
            block["still_open"] = sorted(f["emitter"] for f in findings
                                         if f["status"] == "STILL OPEN")
            block["covered_elsewhere"] = sorted(
                f["emitter"] for f in findings
                if f["status"] == "COVERED BY ANOTHER PREDICATE")
            block["closed_since"] = sorted(f["emitter"] for f in findings
                                           if f["status"] == "CLOSED SINCE")
            block["emitters_with_no_documented_fail_open"] = sorted(
                set(EMITTERS) - {f["emitter"] for f in findings})
            block["caveat"] = (
                "an emitter with no item here has NO DOCUMENTED fail-open input; it "
                "is rendered '— (none documented)' and never as zero fail-opens. "
                "Authoring a should-fire input for the other emitters would be "
                "authoring the finding, which is the failure mode this phase exists "
                "to expose"
            )
        blocks[arm] = block
    return blocks


def _prediction(rows: dict, derived: list[str], degraded: bool) -> dict:
    """The roadmap's committed prediction, evaluated verbatim, with its guards.

    The prediction is NOT rewritten here. Design C replaced it with one authored by
    the party being tested, which would have been the third rewrite; the ledger's
    version is carried word for word and the priors are subtracted only in a
    labelled SECONDARY figure.

    Three things can stop a verdict being printed, and each is a different sentence:

      * ``ADAPTER DEGRADED`` — any item carried an error. A coverage number computed
        while part of the instrument was refusing its input is not a measurement,
        and TA-C1 measured what a degraded adapter reports: 4 of 10 in one failure
        mode and 0 of 10 in the other, i.e. SUPPORTED and FALSIFIED from the same
        bug.
      * ``VOID`` — fewer than three emitters were supplied two or more distinct
        decision-variable values, so the corpus cannot answer. VOID means the corpus
        cannot answer; it never means the diagnosis is wrong. It permits exactly ONE
        rebuild, and a second is VOID-EXHAUSTED.
      * otherwise the arithmetic, which can come out either way.
    """
    emitter_rows = {stem: rows[stem] for stem in EMITTERS if stem in rows}
    fired_stems = sorted(s for s, r in emitter_rows.items() if r["fire_count"])
    varying = sorted(s for s, r in emitter_rows.items() if r["supply"] >= 2)
    observed = len(fired_stems)
    if degraded:
        verdict = "ADAPTER DEGRADED — no verdict"
    elif len(varying) < VOID_BELOW_VARYING:
        verdict = "VOID"
    elif observed >= THRESHOLD:
        verdict = "SUPPORTED"
    else:
        verdict = "FALSIFIED"
    return {
        "statement": "at least 3 of the 10 predicates fire on the honest corpus",
        "source": "roadmap Phase 1, carried verbatim and evaluated verbatim",
        "denominator": len(derived),
        "threshold": THRESHOLD,
        "counting_arms": list(COUNTING_ARMS),
        "observed": observed,
        "fired": fired_stems,
        "varying_denominator": len(varying),
        "varying_emitters": varying,
        "void_below_varying": VOID_BELOW_VARYING,
        "verdict": verdict,
        "priors": list(PRIORS),
        "observed_excluding_priors": len([s for s in fired_stems if s not in PRIORS]),
        "ceiling": ("this metric can see at most 3 of the 8 recorded injections — 3 "
                    "are fail-opens (silences) and 2 are template-payload defects; "
                    "see the failopen arm"),
        "scope": ("3 independent tasks, 1 repository, 1 orchestrator, 1 model, 1 day; "
                  "twelve items is not twelve observations, and this cannot produce a "
                  "false-RED rate"),
    }


def _emitter_rows(items: list[dict], derived: list[str], pairs) -> dict:
    """One row per emitter, aggregated over the COUNTING arms only."""
    func_of = {stem: func for func, stem in pairs}
    rows: dict[str, dict] = {}
    for stem in EMITTERS:
        measured, fires, dims, errs, unmeasured = [], [], [], [], []
        for item in items:
            cell = (item.get("emitters") or {}).get(stem)
            if cell is None:
                continue
            if cell["state"] == "error":
                errs.append("%s: %s" % (item["id"], cell["error"]))
                continue
            if item["arm"] not in COUNTING_ARMS or not item["counts"]:
                continue
            if cell["state"] != "measured":
                unmeasured.append(item["id"])
                continue
            measured.append(item["id"])
            dims.append(json.dumps(cell["dimension"], sort_keys=True))
            if cell["fired"]:
                fires.append(item["id"])
        supply = len(set(dims))
        if not measured:
            state = "BLIND"
        elif supply < 2:
            state = "CONSTANT"
        elif fires:
            state = "SILENT+%d" % len(fires)
        else:
            state = "SILENT"
        rows[stem] = {
            "kind": KIND_EMITTER,
            "function": func_of.get(stem, ""),
            "in_denominator": stem in derived,
            "counting_arm_items": len(measured),
            "fires": sorted(fires),
            "fire_count": len(fires),
            "supply": supply,
            "distinct_dimension_values": sorted(set(dims)),
            "state": state,
            "unmeasured_items": sorted(unmeasured),
            "errors": sorted(errs),
            "prior": stem in PRIORS,
        }
    return rows
