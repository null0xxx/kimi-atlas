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

THE ADAPTERS ARE A REPLICA. The argument marshalling below is a third hand-copy
of the SKILL's Step 4+5 fold (``skills/atlas/SKILL.md``), after the fold itself
and ``tests/test_skill_floor_contract.py``. Plan Task 7 is the test that binds
this copy to that one; until it lands the duplication is UNBOUND, and a drift
between the SKILL's call and this module's would show up as a coverage number
for a call the orchestrator never makes.
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
    ev = _require_dict("ev", evidence)
    own, _passthrough = split_script_defects(ev)
    return fired("evidence-incomplete", own)


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
    from scripts import floorsynth

    critics = _require_list("critics", raw_critics)
    script_defects = _require_list("script_defects", raw_script_defects)
    _merged, schema_errors = floorsynth.merge_and_validate(critics, script_defects)
    return bool(schema_errors)


# ---------------------------------------------------------------------------
# The other eight adapters. One per emitter, each a REPLICA of the SKILL's Step
# 4+5 call, and each importing ``floorsynth`` locally rather than at module scope,
# so that the discovery half of this module can never reach an imported object
# where it is required to read source TEXT.
# ---------------------------------------------------------------------------


def emit_runcheck(evidence) -> bool:
    """Did ``runcheck`` fire on this item?

    The ``runcheck`` key is REQUIRED, not defaulted: ``runcheck.green({})`` is False,
    so the SKILL's own ``ev.get('runcheck', {})`` fail-CLOSED default — correct at
    runtime, where a missing runcheck must block — would report a manufactured
    CRITICAL as a measurement here. ``verify_cmd`` is left defaulted deliberately: it
    reaches ``location`` only and cannot change whether anything fires.
    """
    from scripts import floorsynth

    ev = _require_dict("ev", evidence)
    _require_key("ev", ev, "runcheck")
    return fired("runcheck", floorsynth.synth_runcheck(ev.get("runcheck", {}),
                                                       ev.get("verify_cmd", "")))


def emit_docs_naming(evidence) -> bool:
    """Did ``docs-naming`` fire on this item?

    The mirror image of :func:`emit_runcheck`: here the SKILL's default
    (``ev.get('docs_clean', True)``) fails OPEN, so an absent key would be reported
    as a CLEAN docs floor — a blinded predicate printed as restraint. Required.
    """
    from scripts import floorsynth

    ev = _require_dict("ev", evidence)
    _require_key("ev", ev, "docs_clean")
    return fired("docs-naming", floorsynth.synth_docs(ev.get("docs_clean", True)))


def emit_empty_diff(diff_text) -> bool:
    """Did ``empty-diff`` fire on this item?

    ``""`` is a real input and really fires. ``None`` is refused: an item whose
    ``diff.patch`` could not be read would otherwise be indistinguishable from a
    coder that wrote nothing, and this instrument would be counting the read failure.
    """
    from scripts import floorsynth

    diff = _require_str("diff", diff_text)
    return fired("empty-diff", floorsynth.empty_diff_defect(diff))


def emit_out_of_scope(paths, state) -> bool:
    """Did ``out-of-scope`` fire on this item?

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
    return fired("out-of-scope", floorsynth.out_of_scope_defects(full_paths, st["scope_paths"]))


def emit_dimension_dissent(critics_map) -> bool:
    """Did ``dimension-dissent`` fire on this item?

    Takes the SKILL's ``loaded_map`` (``{artifact_name: critic_dict}``), never the
    list of artifact names: an empty map is silent, so the wrong shape here reports
    every item in the corpus as a clean lens.
    """
    from scripts import floorsynth

    loaded_map = _require_dict("loaded_map", critics_map)
    return fired("dimension-dissent", floorsynth.dimension_dissent_defects(loaded_map))


def emit_critic_stale(critics_map, pass_number) -> bool:
    """Did ``critic-stale`` fire on this item?

    ``current_pass`` is required and must be a real int: it is the item's
    ``ctxstore.get_refine_passes`` value, and at 0 an UNSTAMPED critic counts as
    fresh (the v1.5.1 upgrade-resume carve-out), so a defaulted 0 would silence the
    one emitter with a measured honest-arm fire on this corpus.
    """
    from scripts import floorsynth

    loaded_map = _require_dict("loaded_map", critics_map)
    current_pass = _require_int("current_pass", pass_number)
    return fired("critic-stale", floorsynth.critics_stale_defects(loaded_map, current_pass))


def emit_stale_verdict(records) -> bool:
    """Did ``stale-verdict`` fire on this item?

    The ledger handed in must be the EVAL-POINT one (``log.eval.jsonl``): the SKILL
    calls this 36 lines before the OUTPUT block's own ``advance(..., "OUTPUT")``, and
    a ledger carrying that trailing record cannot trip the H6 trailing-REFINE
    condition at all. Truncation is the corpus builder's job; this adapter only
    refuses a ledger that is not a list.
    """
    from scripts import floorsynth

    log_records = _require_list("log_records", records)
    return fired("stale-verdict", floorsynth.stale_verdict_defects(log_records))


def emit_critic_missing(artifacts) -> bool:
    """Did ``critic-missing`` fire on this item?

    ``[]`` is a real input and really fires — three undispatched critics is precisely
    what this predicate is for, and it is why the firing rule returns a bool: that
    ONE predicate expands to three ids and must still count once. ``None`` is
    refused; and the list must be the artifacts that LOADED, never the ones that
    exist on disk.
    """
    from scripts import floorsynth

    loaded_critics = _require_list("loaded_critics", artifacts)
    return fired("critic-missing", floorsynth.critics_missing_defects(loaded_critics))


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
