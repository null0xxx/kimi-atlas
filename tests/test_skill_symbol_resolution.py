"""VIP-C0: the drift tripwire — every ``scripts.<mod>.<fn>(…)`` the SKILL bodies
call must resolve to a real symbol whose signature the call actually binds.

The SKILL bodies are programs (plan §1, mechanism **M2**: *"executable prose bound
to nothing"*). Of the 13 heredocs in ``skills/atlas/SKILL.md`` only 4 are executed by
``tests/test_critic_shapes_e2e.py``; the other 9 — including the INIT guard, the
packet freeze, the Step-1 diff capture and the Step-2a deterministic-lens block — are
``ast.parse``-d and nothing more. ``skills/atlas-weave/SKILL.md`` and
``skills/atlas-resume/SKILL.md`` have no executed block at all. **8 of 10 drifts
injected into those bodies shipped silently, and the rule was exact for that sample:
drift is caught if and only if it lives in one of the 4 executed heredocs.**

This module closes the NAME and ARITY half of that hole for every block in all three
files. It reports ZERO mismatches against this tree — it is a **tripwire, not a
repair**, and its entire value is what it catches next.

Why the existing pin is not enough: ``tests/test_skill_floor_contract.py:229,254``
compares call TEXT by string equality. That catches a renamed symbol in the prose,
but a call that stays textually identical while the function it names gains a
required parameter is still green today.

WHAT THIS CANNOT SEE — the limits are part of the contract
----------------------------------------------------------
``inspect.signature().bind()`` checks NAME and ARITY. It does not check:

* **Element types.** MEASURED, and pinned in
  ``tests/test_vip_measurements.py``: ``verdict.coverage_partition(FLAT, frozen)``
  and ``coverage_partition(NESTED, frozen)`` BOTH bind successfully, so this
  resolver would **not** have caught VIP-A6. An earlier draft of the plan claimed
  it would; that claim was false and was struck. Do not reintroduce it.
* **Values.** A call that passes ``".atlas"`` where the run needs another base, or
  the wrong stage name, binds perfectly.
* **Behaviour, ordering, or control flow.** Whether the block does the right thing
  with the value it gets is out of reach; that is what the executed-heredoc E2E
  suites are for.
* **Anything it cannot statically attribute to a known module.** Specifically:
  a prose span that does not parse as a Python expression (4 exist in
  ``atlas-weave`` — they carry ``<count>``/``<n>``/``<union of …>`` placeholders);
  a heredoc call whose receiver is not a name bound by ``from scripts import X`` /
  ``import scripts.X`` in that same block; a call reached through a variable,
  alias or ``getattr``; and a bare ``mod.symbol`` mention with no call parentheses
  (``resume.is_task_subrun``, ``scheduler.lease_valid``, ``uniontree.cleanup`` and
  ``bestofn.fanout_n`` are named in prose that way and are therefore unchecked).
* **Elided argument lists.** A documentation call written ``ctxstore.advance(...)``
  states no arity, so it is checked for NAME ONLY. Six such calls exist.
* **CLI flags.** A ``python3 -m scripts.<mod> --flag`` invocation names no Python
  symbol; whether that flag is accepted is not tested here.

COVERAGE AT THIS HEAD (measured, not asserted)
----------------------------------------------
=============================  =========  =============  ============
file                            heredocs   calls checked   mismatches
=============================  =========  =============  ============
``skills/atlas/SKILL.md``             13            122            0
``skills/atlas-weave/SKILL.md``        0             25            0
``skills/atlas-resume/SKILL.md``       0              2            0
=============================  =========  =============  ============

The two prose-only files ship no heredoc at all, which is why they had no
execution coverage to lose. Of the 122 calls in ``atlas``, 6 are the ``f(...)``
elisions above (name-checked only); 4 spans in ``atlas-weave`` carry ``<count>``/
``<n>``/``<union of …>`` placeholders and do not parse, so they are skipped.

The value is measured, not assumed: four drifts were injected and the
pre-existing 2011-test suite was run over each **without** this module.
``ctxstore.init_run`` renamed in the parse-only packet-freeze heredoc, a bad
``leaseclock.stamp`` keyword in weave prose, and ``resume.select_graph_run``
renamed in resume prose ALL shipped green; only the ``syntaxlens.check`` rename
was caught, by the dedicated string pin at
``tests/test_syntaxlens_wiring.py``. This module turns all four red.

An extraction that silently found nothing would pass vacuously, so
``TestCoverageIsNotVacuous`` pins per-file floors on the number of blocks and of
resolved calls.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pathlib
import re
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Every SKILL body kimi-atlas ships as an executable program.
SKILL_FILES = (
    REPO / "skills" / "atlas" / "SKILL.md",
    REPO / "skills" / "atlas-weave" / "SKILL.md",
    REPO / "skills" / "atlas-resume" / "SKILL.md",
)

# The importable surface the SKILL bodies address. Derived from the tree, never
# listed by hand, so a new script joins the resolver's vocabulary automatically.
SCRIPT_MODULES = frozenset(
    p.stem for p in (REPO / "scripts").glob("*.py") if p.stem != "__init__")

# A markdown inline-code span: a run of N backticks, content, the same run again.
_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)

# ``<module>.<attr>(`` inside such a span. The module filter below rejects every
# receiver that is not a real ``scripts/`` module.
_CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*\(")

# A placeholder passed positionally to make a bind check meaningful without
# evaluating anything from the SKILL text. Never called, never inspected.
_ARG = object()


class _Block:
    """One attributable region of a SKILL file: a heredoc body, or the prose."""

    def __init__(self, path, label, line):
        self.path = path
        self.label = label
        self.line = line

    def where(self):
        return "%s:%d [%s]" % (self.path.relative_to(REPO), self.line, self.label)


class _CallSite:
    def __init__(self, block, line, text, module, symbol, node):
        self.block = block
        self.line = line
        self.text = text
        self.module = module
        self.symbol = symbol
        self.node = node

    def where(self):
        return "%s:%d [%s] %s" % (
            self.block.path.relative_to(REPO), self.line, self.block.label, self.text)


def heredoc_blocks(path, text):
    """Every ``python3 - <<'PY' … PY`` body in ``text``, with its opening line.

    Same extractor shape as ``tests/test_critic_shapes_e2e.py`` and
    ``tests/test_skill_floor_contract.py`` (deliberately duplicated rather than
    imported — each of those keeps its own standalone copy), extended to carry the
    source line so a finding can name the block it came from.
    """
    blocks, body, start = [], None, 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if body is None:
            if line.rstrip().endswith("<<'PY'"):
                body, start = [], lineno
        elif line.strip() == "PY":
            blocks.append((_Block(path, "heredoc@%d" % start, start),
                           textwrap.dedent("\n".join(body))))
            body = None
        else:
            body.append(line)
    return blocks


def _strip_heredoc_bodies(text):
    """``text`` with every heredoc BODY blanked, its opener/line numbering kept.

    Heredoc bodies are resolved as Python; blanking them here stops the prose
    scanner from double-reporting the same call from inside a fenced block.
    """
    out, inside = [], False
    for line in text.splitlines():
        if inside:
            out.append("")
            if line.strip() == "PY":
                inside = False
        else:
            out.append(line)
            if line.rstrip().endswith("<<'PY'"):
                inside = True
    return "\n".join(out)


def _module_aliases(tree):
    """Map the names a heredoc binds to ``scripts/`` modules → the module name.

    Only ``from scripts import X`` / ``from scripts import X as Y`` /
    ``import scripts.X [as Y]`` are traced. A receiver bound any other way is
    deliberately not attributed (see the module docstring's limits).
    """
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "scripts":
            for alias in node.names:
                if alias.name in SCRIPT_MODULES:
                    aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) == 2 and parts[0] == "scripts" and parts[1] in SCRIPT_MODULES:
                    aliases[alias.asname or parts[1]] = parts[1]
    return aliases


def heredoc_call_sites(path, text):
    """Every attributable ``<scripts module>.<symbol>(…)`` call in the heredocs."""
    sites = []
    for block, body in heredoc_blocks(path, text):
        tree = ast.parse(body)
        aliases = _module_aliases(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)):
                continue
            module = aliases.get(node.func.value.id)
            if module is None:
                continue
            sites.append(_CallSite(
                block, block.line + node.lineno, _short(ast.unparse(node)),
                module, node.func.attr, node))
    return sites


def _short(text, limit=110):
    """One-line, length-capped call text for a failure message."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit - 1] + "…"


def _balanced_call_text(span, open_paren):
    """The full ``…(…)`` slice of ``span`` starting at its call's ``(``, or None."""
    depth = 0
    for i in range(open_paren, len(span)):
        if span[i] == "(":
            depth += 1
        elif span[i] == ")":
            depth -= 1
            if depth == 0:
                return span[:i + 1]
    return None


def prose_call_sites(path, text):
    """Every ``<scripts module>.<symbol>(…)`` call written in inline-code prose.

    ``atlas-weave`` and ``atlas-resume`` ship no heredoc at all — their executable
    prose is entirely of this form (``scheduler.plan_wave(dag, free_mb=avail)``),
    and the SKILL text itself declares the convention: *"every script call in this
    file runs as ``python3 -c "from scripts import <mod>; …"``"*. A span that does
    not parse as a Python expression is skipped, not guessed at.
    """
    stripped = _strip_heredoc_bodies(text)
    sites = []
    for span_match in _SPAN_RE.finditer(stripped):
        span = span_match.group(2)
        base_line = stripped.count("\n", 0, span_match.start(2)) + 1
        for call_match in _CALL_RE.finditer(span):
            module, symbol = call_match.group(1), call_match.group(2)
            if module not in SCRIPT_MODULES:
                continue
            text_to_paren = _balanced_call_text(span[call_match.start():],
                                                call_match.end() - 1 - call_match.start())
            if text_to_paren is None:
                continue
            flattened = " ".join(text_to_paren.split())
            try:
                node = ast.parse(flattened, mode="eval").body
            except SyntaxError:
                continue
            if not isinstance(node, ast.Call):
                continue
            line = base_line + span.count("\n", 0, call_match.start())
            sites.append(_CallSite(_Block(path, "prose", line), line, _short(flattened),
                                   module, symbol, node))
    return sites


def _is_elided(call):
    """True when the call writes a literal ``...`` — documentation for "and so on".

    Such a call asserts a NAME, not an arity, so the arity half of the check is
    skipped rather than guessed. This is a property of the notation, not an
    exemption for any particular call site.
    """
    for arg in call.args:
        if isinstance(arg, ast.Constant) and arg.value is Ellipsis:
            return True
    for kw in call.keywords:
        if isinstance(kw.value, ast.Constant) and kw.value.value is Ellipsis:
            return True
    return False


def resolve(site):
    """Return a human-readable mismatch for ``site``, or ``None`` when it resolves.

    Three arms, each of which must be able to fail: a module that will not import,
    a symbol the module does not export, and a call the symbol's signature refuses
    to bind.
    """
    try:
        module = importlib.import_module("scripts." + site.module)
    except Exception as exc:
        return "module scripts.%s does not import: %r" % (site.module, exc)
    target = getattr(module, site.symbol, None)
    if target is None:
        return "scripts.%s has no attribute %r" % (site.module, site.symbol)
    if not callable(target):
        return "scripts.%s.%s is not callable (%s)" % (
            site.module, site.symbol, type(target).__name__)
    if _is_elided(site.node):
        return None
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):                # pragma: no cover - tripwire arm
        return None
    starred = any(isinstance(a, ast.Starred) for a in site.node.args)
    double_starred = any(kw.arg is None for kw in site.node.keywords)
    positional = [_ARG for a in site.node.args if not isinstance(a, ast.Starred)]
    keywords = {kw.arg: _ARG for kw in site.node.keywords if kw.arg is not None}
    # An unpacking call (``f(*a)`` / ``f(**d)``) hides how many arguments arrive,
    # so only the arguments that ARE visible are checked — bind_partial still
    # rejects an unknown keyword and an over-long positional list, but cannot
    # report a missing required one.
    binder = signature.bind_partial if (starred or double_starred) else signature.bind
    try:
        binder(*positional, **keywords)
    except TypeError as exc:
        return "does not bind: %s — signature is %s%s" % (exc, site.symbol, signature)
    return None


def call_sites(path):
    text = path.read_text(encoding="utf-8")
    return heredoc_call_sites(path, text) + prose_call_sites(path, text)


class TestEverySkillCallResolves(unittest.TestCase):
    """The tripwire itself: zero mismatches, across all three SKILL files."""

    def test_every_call_site_resolves_and_binds(self):
        """Name + arity for every attributable call in every block of all 3 files.

        A missing module, a missing symbol, a non-callable target or a bind
        failure is a test failure naming the file, the block and the call.
        """
        mismatches = []
        for path in SKILL_FILES:
            for site in call_sites(path):
                problem = resolve(site)
                if problem is not None:
                    mismatches.append("%s — %s" % (site.where(), problem))
        self.assertEqual(
            mismatches, [],
            "SKILL prose names %d call(s) that no longer resolve against scripts/:"
            "\n  %s" % (len(mismatches), "\n  ".join(mismatches)))

    def test_each_file_is_checked_independently(self):
        """Per-file arm, so one clean file cannot hide another's drift."""
        for path in SKILL_FILES:
            with self.subTest(skill=str(path.relative_to(REPO))):
                bad = [s.where() for s in call_sites(path) if resolve(s) is not None]
                self.assertEqual(bad, [])


class TestCoverageIsNotVacuous(unittest.TestCase):
    """A resolver that quietly resolved nothing would pass. These floors stop that.

    Floors, not exact counts: a SKILL body that grows a block or a call must not
    turn this red, but one that loses its executable prose — or an extractor that
    silently stops matching — must.
    """

    def test_the_atlas_skill_still_carries_its_thirteen_heredocs(self):
        path = SKILL_FILES[0]
        blocks = heredoc_blocks(path, path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(
            len(blocks), 13,
            "atlas/SKILL.md is documented (plan §1) as carrying 13 heredocs; "
            "the extractor found %d" % len(blocks))

    def test_every_heredoc_body_parses(self):
        """The precondition for attribution: an unparseable block resolves nothing."""
        for path in SKILL_FILES:
            for block, body in heredoc_blocks(path, path.read_text(encoding="utf-8")):
                with self.subTest(block=block.where()):
                    ast.parse(body)

    def test_each_skill_file_contributes_call_sites(self):
        """Floors per file. ``atlas-weave``/``atlas-resume`` are prose-only.

        Their whole executable surface is inline-code calls, which is exactly the
        surface that had ZERO execution coverage before this module.
        """
        floors = {"skills/atlas/SKILL.md": 100,
                  "skills/atlas-weave/SKILL.md": 20,
                  "skills/atlas-resume/SKILL.md": 2}
        for path in SKILL_FILES:
            key = str(path.relative_to(REPO))
            with self.subTest(skill=key):
                self.assertGreaterEqual(len(call_sites(path)), floors[key])

    def test_the_prose_only_skills_are_covered_by_prose_extraction(self):
        """Guards the mechanism, not just the total: these two have no heredoc."""
        for path in SKILL_FILES[1:]:
            with self.subTest(skill=str(path.relative_to(REPO))):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(heredoc_call_sites(path, text), [])
                self.assertNotEqual(prose_call_sites(path, text), [])


class TestTheResolverCanFail(unittest.TestCase):
    """Armed controls. Each arm of ``resolve`` is driven to RED on a synthetic
    block, so a mismatch that never fires cannot be mistaken for a clean tree.

    Note the polarity the plan warns about (§2): these controls prove the
    FALSE-PASS direction — that the resolver *can* say no — not merely that it
    tolerates good input.
    """

    def _site(self, source, module, symbol):
        block = _Block(SKILL_FILES[0], "synthetic", 0)
        node = ast.parse(source, mode="eval").body
        return _CallSite(block, 0, source, module, symbol, node)

    def test_a_renamed_symbol_is_reported(self):
        site = self._site("ctxstore.init_runX(a, b, c)", "ctxstore", "init_runX")
        self.assertIn("has no attribute", resolve(site))

    def test_a_missing_module_is_reported(self):
        site = self._site("nosuchmod.f(a)", "nosuchmod", "f")
        self.assertIn("does not import", resolve(site))

    def test_a_non_callable_target_is_reported(self):
        site = self._site("langfloor.SYNTAX_ARGV(a)", "langfloor", "SYNTAX_ARGV")
        self.assertIn("not callable", resolve(site))

    def test_too_few_positional_arguments_is_reported(self):
        """The arm the string-equality pin at test_skill_floor_contract.py:229 misses."""
        site = self._site("ctxstore.init_run(base)", "ctxstore", "init_run")
        self.assertIn("does not bind", resolve(site))

    def test_too_many_positional_arguments_is_reported(self):
        site = self._site("verdict.coverage_partition(a, b, c)", "verdict",
                          "coverage_partition")
        self.assertIn("does not bind", resolve(site))

    def test_an_unknown_keyword_argument_is_reported(self):
        site = self._site("verdict.coverage_partition(a, b, nope=1)", "verdict",
                          "coverage_partition")
        self.assertIn("does not bind", resolve(site))

    def test_an_unknown_keyword_is_reported_even_through_unpacking(self):
        """``bind_partial`` still refuses a name the signature does not accept."""
        site = self._site("verdict.coverage_partition(*a, nope=1)", "verdict",
                          "coverage_partition")
        self.assertIn("does not bind", resolve(site))

    def test_a_correct_call_is_not_reported(self):
        """The vacuity control: the resolver must not reject a good call."""
        site = self._site("verdict.coverage_partition(a, b)", "verdict",
                          "coverage_partition")
        self.assertIsNone(resolve(site))

    def test_an_elided_call_is_checked_for_name_only(self):
        """``f(...)`` asserts a name, so a bad name still fires and arity does not."""
        self.assertIsNone(resolve(self._site("ctxstore.advance(...)", "ctxstore",
                                             "advance")))
        self.assertIn("has no attribute",
                      resolve(self._site("ctxstore.advanceX(...)", "ctxstore",
                                         "advanceX")))

    def test_element_type_drift_is_invisible_to_this_resolver(self):
        """VIP-A6, measured: the resolver's own blind spot, pinned as a fixture.

        Both shapes bind. ``tests/test_vip_measurements.py`` holds the behavioural
        half. This is stated in the module docstring and asserted here so the
        struck claim cannot quietly return.
        """
        flat = self._site("verdict.coverage_partition(['a', 'b'], f)", "verdict",
                          "coverage_partition")
        nested = self._site("verdict.coverage_partition([['a', 'b']], f)", "verdict",
                            "coverage_partition")
        self.assertIsNone(resolve(flat))
        self.assertIsNone(resolve(nested))


class TestExtractionEdges(unittest.TestCase):
    """Failure/edge paths of the two extractors, on synthetic text."""

    PATH = SKILL_FILES[0]

    def test_an_unterminated_heredoc_yields_no_block(self):
        text = "python3 - <<'PY'\nfrom scripts import verdict\n"
        self.assertEqual(heredoc_blocks(self.PATH, text), [])

    def test_an_empty_document_yields_nothing(self):
        self.assertEqual(heredoc_blocks(self.PATH, ""), [])
        self.assertEqual(prose_call_sites(self.PATH, ""), [])

    def test_a_receiver_that_is_not_an_imported_module_is_not_attributed(self):
        """``verdict`` here is a local variable, not ``scripts.verdict``."""
        text = "python3 - <<'PY'\nverdict = object()\nverdict.gate(1)\nPY\n"
        self.assertEqual(heredoc_call_sites(self.PATH, text), [])

    def test_an_aliased_from_import_is_attributed(self):
        text = ("python3 - <<'PY'\nfrom scripts import verdict as v\n"
                "v.coverage_partition([['a']], ['a'])\nPY\n")
        self.assertEqual(
            [(s.module, s.symbol) for s in heredoc_call_sites(self.PATH, text)],
            [("verdict", "coverage_partition")])

    def test_an_aliased_dotted_import_is_attributed(self):
        text = ("python3 - <<'PY'\nimport scripts.verdict as v\n"
                "v.coverage_partition([['a']], ['a'])\nPY\n")
        self.assertEqual(
            [(s.module, s.symbol) for s in heredoc_call_sites(self.PATH, text)],
            [("verdict", "coverage_partition")])

    def test_a_fully_qualified_receiver_is_not_attributed(self):
        """``scripts.verdict.f(…)`` has an Attribute receiver, not a Name.

        Unattributed rather than guessed — one of the docstring's stated limits,
        pinned so the gap stays visible instead of being assumed closed.
        """
        text = ("python3 - <<'PY'\nimport scripts.verdict\n"
                "scripts.verdict.coverage_partition([['a']], ['a'])\nPY\n")
        self.assertEqual(heredoc_call_sites(self.PATH, text), [])

    def test_an_unparseable_prose_span_is_skipped_not_guessed(self):
        text = '`ctxstore.advance(".atlas","${SESSION}","SCHEDULE", wave=<n>)`\n'
        self.assertEqual(prose_call_sites(self.PATH, text), [])

    def test_an_unbalanced_prose_call_is_skipped(self):
        self.assertEqual(
            prose_call_sites(self.PATH, "`verdict.coverage_partition(a, b`\n"), [])

    def test_a_heredoc_body_is_not_rescanned_as_prose(self):
        """No double-reporting: the body is blanked before the prose scan."""
        text = ("python3 - <<'PY'\nfrom scripts import verdict\n"
                "`verdict.coverage_partition([['a']], ['a'])`\nPY\n")
        self.assertEqual(prose_call_sites(self.PATH, text), [])

    def test_a_non_scripts_receiver_in_prose_is_ignored(self):
        text = "`json.dumps(x)` and `os.path.join(a, b)`\n"
        self.assertEqual(prose_call_sites(self.PATH, text), [])

    def test_prose_line_numbers_point_at_the_call(self):
        text = "intro\n\n- `verdict.coverage_partition(a, b)` closes it\n"
        sites = prose_call_sites(self.PATH, text)
        self.assertEqual([s.line for s in sites], [3])
        self.assertIn("SKILL.md:3", sites[0].where())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
