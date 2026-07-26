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
import pathlib

from scripts.rubric import BLOCKING as _BLOCKING_SEV

_ROOT = pathlib.Path(__file__).resolve().parents[1]

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


def split_script_defects(evidence) -> tuple[list[dict], list[dict]]:
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

    produced = floorsynth.script_defects_from(evidence)
    own = [d for d in produced
           if isinstance(d, dict) and d.get("id") == "evidence-incomplete"]
    passthrough = [d for d in produced
                   if not (isinstance(d, dict) and d.get("id") == "evidence-incomplete")]
    return own, passthrough


def emit_evidence_incomplete(evidence) -> bool:
    """Did ``evidence-incomplete`` fire on this item? See :func:`split_script_defects`."""
    own, _passthrough = split_script_defects(evidence)
    return fired("evidence-incomplete", own)


def emit_critic_schema(critics, script_defects) -> bool:
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

    _merged, schema_errors = floorsynth.merge_and_validate(
        critics if isinstance(critics, list) else [],
        script_defects if isinstance(script_defects, list) else [],
    )
    return bool(schema_errors)


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
