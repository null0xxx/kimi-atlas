#!/usr/bin/env python3
"""mutpolarity — the standing mutation-POLARITY harness (VIP-C0b, plan §2).

WHY THIS EXISTS. ``docs/superpowers/plans/2026-08-27-verification-integrity-programme.md``
§2 states the mechanism exactly: **controls are written against the failure the
author FEARS.** This project fears false-BLOCKS and says so repeatedly, so every
false-block control exists and the false-PASS control is systematically the
missing one. The proof is on disk: ``tests/test_syntaxlens_redteam.py:153-169`` is
a deliberate, host-independent, named-mutation control — and the mutation that
escaped was the OPPOSITE POLARITY from the one it was armed against
(``scripts/syntaxlens.py``: ``if result.get("signature_matched"):`` ->
``if False and result.get("signature_matched"):`` leaves the module's own tests
green while the whole ruby/php/go/sh/bash syntax floor goes silent).

"One armed control per gate" is therefore NOT the remedy — it moves the problem,
because nothing then verifies the control is non-vacuous. This module is the
remedy: for every defect-emitting site of every covered gate it injects THREE
mutations and requires that module's own tests to turn RED.

* ``force-fire``   — the gate fires unconditionally (a false BLOCK). This repo
  already fears these, so its controls are expected to be dense here.
* ``force-silent`` — the gate never fires (a false PASS). This is the polarity the
  §2 mechanism predicts is missing, and it is the one that matters.
* ``delete-emit``  — the emit statement is removed; the floor produces nothing at
  all.

A SURVIVOR IS THE FINDING, NOT A HARNESS FAILURE. A survivor means that gate has
no control for that polarity at that site. There is deliberately **no
expected-survivor allowlist**: an allowlist would rebuild the exact blindness this
harness exists to remove, so the run stays RED until a control is written. Exit
codes: 0 = every mutation caught, 1 = at least one survivor (the finding),
2 = the harness itself is broken or vacuous (no sites, a red baseline, a module
below its site floor).

SAFETY IS BY CONSTRUCTION, NOT BY ``finally``. This harness rewrites gate source
in order to test it, and a crash between "mutate" and "restore" would leave a
mutated gate in the working tree — precisely the invisible failure the whole
programme is about. So the real source is NEVER opened for writing: every mutant
is materialised in a throwaway sandbox under the system temp dir, and
:func:`_assert_outside_repo` re-checks every single write target against the repo
root before the bytes are written. SIGKILL the run at any instant and
``git status --porcelain`` is unchanged, because no write to the repo was ever
issued in the first place.

SIDE LANE (plan §3). This is ``make mutation-polarity``; it is deliberately NOT in
``make ci``. The pure analyser is covered by ``tests/test_mutation_polarity.py``
(which ``make ci`` does run, in milliseconds); only the subprocess sweep — one
child interpreter per distinct mutant — lives out here. Stdlib only; no runtime
dependency is added to the blocking lane.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORCE_FIRE = "force-fire"
FORCE_SILENT = "force-silent"
DELETE_EMIT = "delete-emit"
POLARITIES: tuple[str, ...] = (FORCE_FIRE, FORCE_SILENT, DELETE_EMIT)

# Covered gates: every module in the deterministic floor that can emit a defect
# (or a schema error the gate blocks on). MIN_SITES is the NON-VACUITY FLOOR
# (criterion 6): finding fewer sites than this in a module is a harness FAILURE,
# never a quiet pass. The numbers are measured at the build HEAD; a legitimate
# refactor that removes a site must lower them deliberately, in a diff a reviewer
# can see.
MIN_SITES: dict[str, int] = {
    "astlens": 6,
    "floorsynth": 14,
    "langfloor": 1,
    "lintlens": 4,
    "nativefloor": 2,
    "pathcheck": 1,
    "quality": 15,
    "reqcoverage": 3,
    "sast": 2,
    "syntaxlens": 4,
}
COVERED_MODULES: tuple[str, ...] = tuple(sorted(MIN_SITES))

# Gates in the pipeline that are NOT covered, each with the reason. These are
# DECISIONS, not omissions, and ``_excluded_module_report`` RE-MEASURES the claim
# on every run: an excluded module that grows an emit site turns the sweep RED
# instead of staying quietly outside the harness. That re-measurement is what
# moved ``langfloor``/``lintlens``/``nativefloor`` INTO the covered set — they
# carry no severity literal, but each has a decision accumulator whose silencing
# is a false-PASS lever (``nativefloor.run``'s ``results.append`` is the escaped
# syntaxlens mutation one layer down), so "no severity" was the wrong test.
EXCLUDED_MODULES: dict[str, str] = {
    "runcheck": "orchestrates the runner and delegates every judgement (runsignal "
                "tallies, langfloor resolution); it emits an UNVERIFIED status dict, "
                "not a finding into an accumulator, so it has no emit statement to "
                "mutate — measured: 0 sites.",
    "runsignal": "pure output parser — returns (count, green) tallies with no finding "
                 "accumulator; its polarity question is GRAMMAR coverage (plan "
                 "VIP-A1/VIP-B1), which a corpus answers and a mutation cannot — "
                 "measured: 0 sites.",
}

# Repo-relative trees the sandbox needs. ``scripts`` is what gets mutated; the
# rest is what the gates' own tests read (``agents/*.md`` critic prose,
# ``skills/atlas/SKILL.md`` for the wiring tests). Nothing here is ever written
# back — the copy is the only thing this module opens for writing, and an
# incomplete list is caught loudly by the baseline gate, never silently.
SANDBOX_PATHS: tuple[str, ...] = ("scripts", "tests", "agents", "skills/atlas")

# A test run is bounded: a mutant that hangs must not hang the sweep.
RUN_TIMEOUT_S = 300

_RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)


# --------------------------------------------------------------------------
# Pure analysis
# --------------------------------------------------------------------------
def _is_severity_dict(node: ast.AST) -> bool:
    """True iff ``node`` is a dict LITERAL carrying a constant ``"severity"`` key."""
    return isinstance(node, ast.Dict) and any(
        isinstance(key, ast.Constant) and key.value == "severity" for key in node.keys
    )


def _own_nodes(fn: ast.AST):
    """Yield the nodes of ``fn`` excluding those owned by a nested function/class.

    A nested def has its own returns and its own accumulators; attributing them to
    the enclosing function would mint sites that do not exist.
    """
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _defect_factories(tree: ast.Module) -> frozenset[str]:
    """Names of the module's defect CONSTRUCTORS (e.g. ``_d``).

    A factory is a function whose every ``return`` returns a severity-dict literal:
    it BUILDS a defect but decides nothing, so it is not itself an emission site —
    mutating it would just delete every defect in the module at once and tell us
    nothing about which control is missing. Its CALLERS are the sites.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        returns = [n for n in _own_nodes(node) if isinstance(n, ast.Return)]
        if returns and all(r.value is not None and _is_severity_dict(r.value) for r in returns):
            names.add(node.name)
    return frozenset(names)


def _is_defect_expr(node: ast.AST, producers: frozenset[str]) -> bool:
    """True iff ``node`` builds a defect: a severity-dict, or a call to a producer."""
    for sub in ast.walk(node):
        if _is_severity_dict(sub):
            return True
        if isinstance(sub, ast.Call):
            func = sub.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else None)
            if name in producers:
                return True
    return False


def _accumulators(fn: ast.AST) -> set[str]:
    """Local list names that are initialised empty AND decide the function's outcome.

    "Decides the outcome" means the list is either RETURNED (``defects``,
    ``quality.validate_critic``'s ``errs``, ``reqcoverage._changed_paths``'s
    ``paths``) or TESTED for emptiness (``syntaxlens``'s ``source_jobs``,
    ``floorsynth.stale_verdict_defects``'s ``reasons``). Both shapes are decision
    channels: silencing an append to either makes the gate see less and pass more,
    which is exactly the false-PASS polarity §2 says is unguarded. A list that is
    neither returned nor tested is scratch state and is correctly not an emit
    target.
    """
    empty_lists: set[str] = set()
    for node in _own_nodes(fn):
        target, value = None, None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and isinstance(value, ast.List) and not value.elts:
            empty_lists.add(target.id)
    decisive: set[str] = {
        node.value.id for node in _own_nodes(fn)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
    }
    for node in _own_nodes(fn):
        test = getattr(node, "test", None) if isinstance(
            node, (ast.If, ast.While, ast.IfExp, ast.Assert)) else None
        if test is None:
            continue
        decisive.update(sub.id for sub in ast.walk(test) if isinstance(sub, ast.Name))
    return empty_lists & decisive


def _appended_name(stmt: ast.stmt) -> str | None:
    """Return the target name if ``stmt`` is ``<name>.append/extend(...)``."""
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return None
    func = stmt.value.func
    if not isinstance(func, ast.Attribute) or func.attr not in ("append", "extend"):
        return None
    return func.value.id if isinstance(func.value, ast.Name) else None


def _index_blocks(tree: ast.Module) -> dict[int, tuple[ast.AST, str, list, int]]:
    """Map ``id(stmt)`` -> ``(owner, field, block, index)`` for every statement.

    This is the parent pointer the guard search needs; ``ast`` does not keep one.
    """
    index: dict[int, tuple[ast.AST, str, list, int]] = {}
    stack: list[ast.AST] = [tree]
    while stack:
        owner = stack.pop()
        for field, value in ast.iter_fields(owner):
            if not isinstance(value, list):
                continue
            for position, item in enumerate(value):
                if isinstance(item, ast.stmt):
                    index[id(item)] = (owner, field, value, position)
                if isinstance(item, ast.AST):
                    stack.append(item)
        for _field, value in ast.iter_fields(owner):
            if isinstance(value, ast.AST):
                stack.append(value)
    return index


def _is_bail_guard(stmt: ast.stmt) -> bool:
    """True iff ``stmt`` is an ``if`` whose body ENDS in return/continue/break/raise.

    This is the EARLY-RETURN idiom, and it is the dominant guard shape in this
    codebase (``if (diff or "").strip(): return []``, ``if m in known: continue``).
    Its polarity is INVERTED relative to a wrapping ``if``: taking the bail is what
    silences the emit below it. The body may carry work before the transfer —
    ``nativefloor.run``'s budget bail appends a skip record and *then* continues —
    so the test is on the LAST statement, not on a one-statement body.
    """
    return (
        isinstance(stmt, ast.If)
        and not stmt.orelse
        and bool(stmt.body)
        and isinstance(stmt.body[-1], (ast.Return, ast.Continue, ast.Break, ast.Raise))
    )


def _guard_context(stmt: ast.stmt, index: dict) -> str:
    """Name the construct an unguarded emit actually sits in, for the hole report.

    A hole must be NAMED, not counted: "inside an except handler" and "unconditional
    in a loop body" are different holes with different remedies.
    """
    node: ast.AST = stmt
    while id(node) in index:
        owner, field, _block, _position = index[id(node)]
        if isinstance(owner, ast.ExceptHandler):
            return "inside an except handler — the trigger is a raised exception, not a condition"
        if isinstance(owner, (ast.For, ast.AsyncFor, ast.While)):
            return "unconditional in a loop body"
        if isinstance(owner, ast.Try) and field == "body":
            return "unconditional inside a try body"
        if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return "unconditional in the function body"
        node = owner
    return "unconditional at module level"


def _hole_reason(stmt: ast.stmt, index: dict, polarity: str) -> str:
    """The exact, polarity-aware reason a conditional mutation cannot be injected."""
    context = _guard_context(stmt, index)
    if polarity == FORCE_SILENT:
        return ("no condition guards this emit (%s), so silencing it is the SAME edit as "
                "delete-emit — that row carries this site's verdict" % context)
    return ("no condition guards this emit (%s); forcing it would mean forcing the "
            "surrounding construct to occur, which no rewrite of a guard can do" % context)


def _resolve_guard(stmt: ast.stmt, index: dict) -> tuple[ast.expr, str] | None:
    """Find the innermost control decision that determines whether ``stmt`` runs.

    Returns ``(test_expression, sense)`` where sense is ``"direct"`` (the emit is in
    the guard's body: ``True or`` fires it) or ``"inverted"`` (an early-return bail
    guard, or an ``else`` branch: ``False and`` fires it). ``None`` means no guard
    is mechanically reachable from the source — reported as a HOLE IN THE HARNESS,
    never skipped.
    """
    node: ast.AST = stmt
    while id(node) in index:
        owner, field, block, position = index[id(node)]
        for previous in reversed(block[:position]):
            if _is_bail_guard(previous):
                return previous.test, "inverted"
        if isinstance(owner, ast.If) and field == "body":
            return owner.test, "direct"
        if isinstance(owner, ast.If) and field == "orelse":
            return owner.test, "inverted"
        if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module, ast.ClassDef)):
            return None
        node = owner
    return None


def find_sites(source: str, module: str = "<module>") -> list[dict]:
    """Return every defect-emitting site in ``source``, in source order (PURE).

    A SITE is a statement that puts a finding into the gate's output: an
    ``append``/``extend`` into a decision accumulator (see :func:`_accumulators`),
    an ``append``/``extend`` of a defect expression into ANY local list (which
    catches ``floorsynth.merge_and_validate``, whose list is seeded from its
    argument rather than from ``[]``), or a ``return`` of a defect expression from
    a function that is not a pure factory. Producers are closed to a fixpoint so a
    wrapper (``_config_defect`` -> ``_d``) counts its caller too.

    Each site dict carries ``line``/``end_line``, ``kind`` (``append`` | ``return``),
    ``source`` (the emit statement's own text), and either ``guard_line``/
    ``guard_source``/``guard_sense`` or ``guard_context`` — the named construct the
    unguarded emit sits in, from which the hole reason is built.

    Raises:
        SyntaxError: if ``source`` does not parse. A gate whose source is not
            parseable cannot be mutated, and pretending otherwise would report a
            clean sweep over nothing.
    """
    tree = ast.parse(source)
    index = _index_blocks(tree)
    producers = set(_defect_factories(tree))

    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    # Fixpoint: a function that emits a defect is itself a producer, so a caller
    # appending its result (``defects.append(defect)``) is an emit site too.
    for _pass in range(len(functions) + 1):
        grown = False
        for fn in functions:
            if fn.name in producers:
                continue
            emits = any(
                _appended_name(stmt) is not None
                and _is_defect_expr(stmt, frozenset(producers))
                for stmt in _own_nodes(fn) if isinstance(stmt, ast.stmt)
            ) or any(
                isinstance(stmt, ast.Return) and stmt.value is not None
                and _is_defect_expr(stmt.value, frozenset(producers))
                for stmt in _own_nodes(fn)
            )
            if emits:
                producers.add(fn.name)
                grown = True
        if not grown:
            break

    frozen = frozenset(producers)
    factories = _defect_factories(tree)
    sites: list[dict] = []
    for fn in functions:
        if fn.name in factories:
            continue
        names = _accumulators(fn)
        for stmt in _own_nodes(fn):
            if not isinstance(stmt, ast.stmt):
                continue
            kind: str | None = None
            appended = _appended_name(stmt)
            if appended is not None and (appended in names or _is_defect_expr(stmt, frozen)):
                kind = "append"
            elif (isinstance(stmt, ast.Return) and stmt.value is not None
                    and _is_defect_expr(stmt.value, frozen)):
                kind = "return"
            if kind is None:
                continue
            site = {
                "module": module,
                "function": fn.name,
                "line": stmt.lineno,
                "end_line": stmt.end_lineno or stmt.lineno,
                "kind": kind,
                "source": _segment(source, stmt),
            }
            guard = _resolve_guard(stmt, index)
            if guard is None:
                site["guard_context"] = _guard_context(stmt, index)
            else:
                test, sense = guard
                site["guard_line"] = test.lineno
                site["guard_sense"] = sense
                site["guard_source"] = _segment(source, test)
            sites.append(site)
    sites.sort(key=lambda s: (s["line"], s["end_line"]))
    return sites


# --------------------------------------------------------------------------
# Pure mutation
# --------------------------------------------------------------------------
def _char_col(line: str, byte_col: int) -> int:
    """Convert an ``ast`` UTF-8 byte column into a character index into ``line``."""
    return len(line.encode("utf-8")[:byte_col].decode("utf-8", errors="ignore"))


def _segment(source: str, node: ast.AST) -> str:
    """Return the exact source text of ``node`` (byte-column safe)."""
    lines = source.splitlines(keepends=True)
    first, last = node.lineno - 1, (node.end_lineno or node.lineno) - 1
    start = _char_col(lines[first], node.col_offset)
    end = _char_col(lines[last], node.end_col_offset or 0)
    if first == last:
        return lines[first][start:end]
    return lines[first][start:] + "".join(lines[first + 1:last]) + lines[last][:end]


def _splice(source: str, node: ast.AST, replacement: str) -> str:
    """Replace ``node``'s exact source span with ``replacement`` (byte-column safe)."""
    lines = source.splitlines(keepends=True)
    first, last = node.lineno - 1, (node.end_lineno or node.lineno) - 1
    start = _char_col(lines[first], node.col_offset)
    end = _char_col(lines[last], node.end_col_offset or 0)
    return (
        "".join(lines[:first])
        + lines[first][:start] + replacement + lines[last][end:]
        + "".join(lines[last + 1:])
    )


def _empty_return(node: ast.Return) -> str:
    """The 'no defect' return this function's own convention uses.

    ``return []`` for a list-returning emitter (``floorsynth.empty_diff_defect``),
    ``return None`` for a single-defect emitter (``astlens.check_syntax``). Using
    the module's own empty value keeps ``delete-emit`` a SILENCING mutation rather
    than a crash the caller would notice for the wrong reason.
    """
    return "return []" if isinstance(node.value, ast.List) else "return None"


def mutate(source: str, site: dict, polarity: str) -> dict:
    """Return the mutant source for ``site`` under ``polarity`` (PURE).

    Returns a dict with ``ok`` plus either ``source``/``injection`` (the exact text
    injected, so the report can quote it) or ``reason`` — the named reason this
    polarity cannot be injected mechanically at this site. A refusal is a HOLE IN
    THE HARNESS and is reported as such (criterion 9); it is never a silent skip.

    Raises:
        ValueError: on an unknown polarity — a typo must fail loudly rather than
            quietly mutate nothing and report a clean sweep.
    """
    if polarity not in POLARITIES:
        raise ValueError("unknown polarity %r (expected one of %s)" % (polarity, list(POLARITIES)))
    tree = ast.parse(source)
    index = _index_blocks(tree)
    stmt = _statement_at(tree, site)
    if stmt is None:
        return {"ok": False, "reason": "the site's statement is no longer at line %d — the "
                                       "source moved under the plan" % site["line"]}

    if polarity == DELETE_EMIT:
        replacement = _empty_return(stmt) if isinstance(stmt, ast.Return) else "pass"
        mutant = _splice(source, stmt, replacement)
        injection = replacement
    else:
        guard = _resolve_guard(stmt, index)
        if guard is None:
            return {"ok": False, "reason": _hole_reason(stmt, index, polarity)}
        test, sense = guard
        fire = polarity == FORCE_FIRE
        prefix = "True or " if (fire == (sense == "direct")) else "False and "
        injection = "%s(%s)" % (prefix, _segment(source, test))
        mutant = _splice(source, test, injection)

    try:
        compile(mutant, "<mutant>", "exec")
    except (SyntaxError, ValueError) as exc:
        return {"ok": False, "reason": "the rewrite does not compile (%s: %s) — this site's "
                                       "syntax is out of the harness's reach" % (type(exc).__name__, exc)}
    return {"ok": True, "source": mutant, "injection": injection}


def _statement_at(tree: ast.Module, site: dict) -> ast.stmt | None:
    """Re-find the site's statement in a freshly parsed ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and node.lineno == site["line"] and \
                (node.end_lineno or node.lineno) == site["end_line"]:
            if site["kind"] == "return" and isinstance(node, ast.Return):
                return node
            if site["kind"] == "append" and isinstance(node, ast.Expr):
                return node
    return None


def plan(module: str, source: str) -> list[dict]:
    """Return every (site x polarity) mutation for ``module`` (PURE, deterministic)."""
    mutations: list[dict] = []
    for site in find_sites(source, module):
        for polarity in POLARITIES:
            result = mutate(source, site, polarity)
            mutations.append({
                "module": module,
                "site": site,
                "polarity": polarity,
                "ok": result["ok"],
                "injection": result.get("injection", ""),
                "reason": result.get("reason", ""),
                "source": result.get("source", ""),
            })
    return mutations


# --------------------------------------------------------------------------
# Sandbox — the safety boundary
# --------------------------------------------------------------------------
def _assert_outside_repo(path: str) -> str:
    """Raise unless ``path`` is strictly outside the repository tree.

    Called immediately before EVERY write this module performs. The design already
    makes a repo write impossible (nothing ever composes a path from ``REPO_ROOT``
    for writing); this is the second lock, so a future edit that reintroduces one
    dies here instead of in someone's working tree.
    """
    real = os.path.realpath(path)
    root = os.path.realpath(REPO_ROOT)
    if real == root or real.startswith(root + os.sep):
        raise RuntimeError(
            "REFUSED: mutpolarity never writes inside the repository (%s is under %s). "
            "Mutants live in a throwaway sandbox so a crash cannot leave a mutated gate "
            "in the working tree." % (real, root))
    return real


def make_sandbox() -> str:
    """Copy :data:`SANDBOX_PATHS` into a fresh temp dir and return its path.

    The copy — not the repo — is what gets mutated and imported. ``__pycache__`` is
    excluded and the children run with ``-B``/``PYTHONDONTWRITEBYTECODE`` so a
    same-size, same-second mutant can never be served a stale ``.pyc``.
    """
    sandbox = tempfile.mkdtemp(prefix="mutpolarity-")
    _assert_outside_repo(sandbox)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for name in SANDBOX_PATHS:
        target = _assert_outside_repo(os.path.join(sandbox, name))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(os.path.join(REPO_ROOT, name), target, ignore=ignore)
    return sandbox


def _write_module(sandbox: str, module: str, source: str) -> None:
    """Write ``source`` as ``<sandbox>/scripts/<module>.py`` (never the real file)."""
    target = _assert_outside_repo(os.path.join(sandbox, "scripts", "%s.py" % module))
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(source)


def _discard_sandbox(sandbox: str) -> None:
    """Remove a sandbox this process created, or leave it alone.

    Deliberately narrow after the two working-tree accidents this programme is
    named for: the path must be outside the repo, under the system temp dir, and
    carry this module's own prefix. Anything else is left untouched.
    """
    real = _assert_outside_repo(sandbox)
    parent = os.path.realpath(tempfile.gettempdir())
    if os.path.dirname(real) == parent and os.path.basename(real).startswith("mutpolarity-"):
        shutil.rmtree(real, ignore_errors=True)


def run_tests(sandbox: str, module: str, timeout_s: int = RUN_TIMEOUT_S) -> dict:
    """Run ``module``'s own tests inside ``sandbox``; return rc, test count, tail.

    "Its own tests" is ``tests/test_<module>*.py`` — the same scope the §2 evidence
    used ("32 tests OK"). ``PYTHONPATH`` is pinned to the sandbox so an inherited
    value can never let a child import the REAL gate and report a mutant caught
    that was never loaded.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = sandbox
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    argv = [sys.executable, "-B", "-m", "unittest", "discover",
            "-s", "tests", "-p", "test_%s*.py" % module]
    try:
        proc = subprocess.run(argv, cwd=sandbox, env=env, capture_output=True,
                              text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"rc": None, "tests": 0, "tail": "timed out after %ds" % timeout_s}
    output = (proc.stdout or "") + (proc.stderr or "")
    match = _RAN_RE.search(output)
    return {
        "rc": proc.returncode,
        "tests": int(match.group(1)) if match else 0,
        "tail": output[-400:],
    }


# --------------------------------------------------------------------------
# The sweep
# --------------------------------------------------------------------------
def _read_module(module: str) -> str:
    with open(os.path.join(REPO_ROOT, "scripts", "%s.py" % module), encoding="utf-8") as handle:
        return handle.read()


def _excluded_module_report() -> list[dict]:
    """Re-measure the exclusions: an excluded module must still have ZERO sites.

    The exclusion list is a decision, and a decision that is never re-checked rots.
    If ``runcheck`` or ``runsignal`` grows an emit, this turns the sweep RED rather
    than letting the module stay quietly outside the harness — which is exactly how
    ``lintlens``/``langfloor``/``nativefloor`` were moved into the covered set.
    """
    rows: list[dict] = []
    for module, reason in sorted(EXCLUDED_MODULES.items()):
        try:
            sites = find_sites(_read_module(module), module)
        except (OSError, SyntaxError) as exc:
            rows.append({"module": module, "reason": reason, "sites": -1,
                         "error": "%s: %s" % (type(exc).__name__, exc)})
            continue
        rows.append({"module": module, "reason": reason, "sites": len(sites), "error": ""})
    return rows


def sweep(modules: tuple[str, ...] = COVERED_MODULES, timeout_s: int = RUN_TIMEOUT_S) -> dict:
    """Mutate every site of every covered gate and report which mutations survive.

    Identical mutant sources are executed once and the result shared (two sites
    behind one guard produce the same bytes); the report still lists every
    (site, polarity) row, so the matrix is complete.
    """
    started = time.time()
    sandbox = make_sandbox()
    report: dict = {
        "sandbox": sandbox,
        "modules": [],
        "excluded": _excluded_module_report(),
        "errors": [],
        "rows": [],
        "holes": [],
    }
    try:
        for module in modules:
            pristine = _read_module(module)
            baseline = run_tests(sandbox, module, timeout_s)
            mutations = plan(module, pristine)
            sites = find_sites(pristine, module)
            floor = MIN_SITES.get(module, 1)
            entry = {
                "module": module,
                "sites": len(sites),
                "floor": floor,
                "baseline_rc": baseline["rc"],
                "baseline_tests": baseline["tests"],
            }
            report["modules"].append(entry)
            if len(sites) < floor:
                report["errors"].append(
                    "%s: found %d emit site(s), below the non-vacuity floor of %d — the "
                    "analyser has lost sight of this gate, which is a harness failure, "
                    "not a clean sweep" % (module, len(sites), floor))
                continue
            if baseline["rc"] != 0 or baseline["tests"] <= 0:
                report["errors"].append(
                    "%s: baseline is not green in the sandbox (rc=%s, %d test(s)) — every "
                    "mutant would look 'caught' for the wrong reason. Tail: %s"
                    % (module, baseline["rc"], baseline["tests"], baseline["tail"].strip()))
                continue

            cache: dict[str, dict] = {}
            for mutation in mutations:
                site = mutation["site"]
                row = {
                    "module": module,
                    "function": site["function"],
                    "line": site["line"],
                    "guard_line": site.get("guard_line", 0),
                    "polarity": mutation["polarity"],
                    "injection": mutation["injection"],
                }
                if not mutation["ok"]:
                    row["result"] = "HOLE"
                    row["detail"] = mutation["reason"]
                    report["holes"].append(row)
                    report["rows"].append(row)
                    continue
                cached = cache.get(mutation["source"])
                if cached is None:
                    _write_module(sandbox, module, mutation["source"])
                    cached = run_tests(sandbox, module, timeout_s)
                    cache[mutation["source"]] = cached
                row["result"] = "caught" if cached["rc"] not in (0, None) else "SURVIVED"
                if cached["rc"] is None:
                    row["result"] = "HOLE"
                    row["detail"] = "the mutant's test run timed out; no verdict"
                    report["holes"].append(row)
                elif cached["tests"] <= 0:
                    row["result"] = "HOLE"
                    row["detail"] = "the mutant run collected 0 tests; no verdict"
                    report["holes"].append(row)
                else:
                    row["detail"] = "%d test(s), rc=%s" % (cached["tests"], cached["rc"])
                report["rows"].append(row)
            # Restore the pristine copy so the next module's baseline is honest.
            _write_module(sandbox, module, pristine)
    finally:
        _discard_sandbox(sandbox)

    report["survivors"] = [r for r in report["rows"] if r["result"] == "SURVIVED"]
    report["caught"] = [r for r in report["rows"] if r["result"] == "caught"]
    report["seconds"] = round(time.time() - started, 2)
    return report


def render(report: dict) -> str:
    """Render the survivor matrix — the finding — followed by the holes and totals."""
    lines: list[str] = ["SURVIVOR MATRIX — module x site x polarity"]
    lines.append("%-12s %-26s %-6s %-6s %-13s %s"
                 % ("module", "function", "emit", "guard", "polarity", "result"))
    for row in report["rows"]:
        lines.append("%-12s %-26s L%-5d %-6s %-13s %s"
                     % (row["module"], row["function"][:26], row["line"],
                        ("L%d" % row["guard_line"]) if row["guard_line"] else "-",
                        row["polarity"], row["result"]))

    survivors = report.get("survivors", [])
    lines.append("")
    if survivors:
        lines.append("SURVIVORS (%d) — each one is a gate with no control for that polarity:"
                     % len(survivors))
        for row in survivors:
            guard = (" guard L%d" % row["guard_line"]) if row["guard_line"] else ""
            lines.append("  %-13s scripts/%s.py:%d%s (%s)  injected: %s"
                         % (row["polarity"], row["module"], row["line"], guard,
                            row["function"], row["injection"] or "-"))
    else:
        lines.append("SURVIVORS: none.")

    holes = report.get("holes", [])
    lines.append("")
    if holes:
        lines.append("HOLES IN THE HARNESS (%d) — sites this harness cannot reach, named "
                     "rather than skipped:" % len(holes))
        for row in holes:
            lines.append("  %-13s scripts/%s.py:%d (%s) — %s"
                         % (row["polarity"], row["module"], row["line"], row["function"],
                            row.get("detail", "")))
    else:
        lines.append("HOLES IN THE HARNESS: none.")

    lines.append("")
    lines.append("COVERED (%d module(s)):" % len(report["modules"]))
    for entry in report["modules"]:
        lines.append("  %-12s %2d site(s) (floor %d), baseline %d test(s) rc=%s"
                     % (entry["module"], entry["sites"], entry["floor"],
                        entry["baseline_tests"], entry["baseline_rc"]))
    lines.append("NOT COVERED (%d module(s)) — decided, and re-measured every run:"
                 % len(report["excluded"]))
    for entry in report["excluded"]:
        lines.append("  %-12s %d emit site(s): %s"
                     % (entry["module"], entry["sites"], entry["reason"]))

    for message in report.get("errors", []):
        lines.append("! HARNESS ERROR: %s" % message)

    lines.append("")
    lines.append("TOTALS: %d mutation(s), %d caught, %d SURVIVED, %d hole(s), %.2fs wall-clock"
                 % (len(report["rows"]), len(report.get("caught", [])), len(survivors),
                    len(holes), report.get("seconds", 0.0)))
    return "\n".join(lines) + "\n"


def exit_code(report: dict) -> int:
    """0 = every mutation caught; 1 = a survivor (the finding); 2 = harness broken."""
    if report.get("errors"):
        return 2
    if not report.get("rows"):
        return 2
    for entry in report["excluded"]:
        if entry["sites"] != 0:
            return 2
    if report.get("survivors"):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI for the side lane. Never writes anything inside the repository."""
    parser = argparse.ArgumentParser(
        description="Mutation-POLARITY harness: force-fire / force-silent / delete-emit "
                    "at every defect-emitting site of every covered gate.")
    parser.add_argument("--module", action="append", default=[],
                        help="Limit the sweep to this covered module (repeatable).")
    parser.add_argument("--list-sites", action="store_true",
                        help="List the emit sites and exit — pure analysis, no subprocess.")
    parser.add_argument("--json", action="store_true",
                        help="Emit the machine-readable report instead of the matrix.")
    parser.add_argument("--timeout", type=int, default=RUN_TIMEOUT_S,
                        help="Per-test-run timeout in seconds (default: %(default)s).")
    args = parser.parse_args(argv)

    modules = tuple(args.module) or COVERED_MODULES
    unknown = [m for m in modules if m not in MIN_SITES]
    if unknown:
        print("mutpolarity: not a covered module: %s (covered: %s)"
              % (", ".join(unknown), ", ".join(COVERED_MODULES)), file=sys.stderr)
        return 2

    if args.list_sites:
        payload = {m: find_sites(_read_module(m), m) for m in modules}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for module, sites in payload.items():
                print("%s: %d site(s), floor %d" % (module, len(sites), MIN_SITES[module]))
                for site in sites:
                    print("  L%-5d %-8s %-24s guard=%s"
                          % (site["line"], site["kind"], site["function"],
                             ("L%d %s" % (site["guard_line"], site["guard_sense"]))
                             if "guard_line" in site else "NONE"))
        return 0

    report = sweep(modules, timeout_s=args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report), end="")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
