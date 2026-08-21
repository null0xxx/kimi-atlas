"""C1 — model-, user- and repo-supplied text must never become Python source.

``skills/atlas/SKILL.md`` is not documentation, it is a PROGRAM an LLM executes.
v1.5.2 shipped three blocks that interpolated foreign text straight into a Python
source literal:

- Step 3.4 ``RAW = r'''<the critic's returned JSON text>'''`` — a critic's message,
- ``json.loads('''<returned JSON>''')`` — the scout digest, which carries
  ``untrusted_excerpts`` copied **verbatim out of the target repo**,
- the INIT packet freeze ``"intent": \"\"\"<full request>\"\"\"`` — the user's raw request.

A body containing the closing quote closes the literal and everything after it
**executes** — before ``json.loads`` and before ``quality.enforce_critic_schema``,
so the whole v1.5.2 validation layer is *bypassed, not defeated*. Pointed the
honest way it is a false RED: a critic quoting a ``'''`` docstring (which
``agents/*-critic.md`` tell critics to do) breaks the block on a **green** tree.

This module pins the *defect class*, not the three known instances. ``tests/
test_v1521_regressions.py`` carries the narrow reproduction; the pins here are
deliberately wider, because a pin narrower than the class is exactly how C1
shipped in the first place:

- **no Python-executable region of the SKILL may contain a quoted placeholder** —
  the hard pin, zero tolerance;
- **every quoted placeholder anywhere in the SKILL must be explicitly waived**
  with a reason (``WAIVED`` below), and a waiver that no longer matches any line
  is itself a failure, so the table cannot rot into a rubber stamp;
- **each of the four rewritten blocks must READ A FILE** — pinned as "reads a
  path from ``argv``", never as "does not use ``r'''``". An implementer told to
  "fix it the same way" could add an ``r`` prefix to the digest block: that fixes
  the ``\\n``-mangling and leaves the break-out wide open.

The fail-open direction is probed by execution: a BOM, invalid UTF-8, a missing
scratch file, and an honest critic quoting ``'''``/``\"\"\"``/``EOF``/``PY``.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"

if str(_ROOT) not in sys.path:  # pragma: no cover - import shim
    sys.path.insert(0, str(_ROOT))

from scripts import rubric  # noqa: E402

# A quoted string literal whose body carries an <angle-bracket placeholder> —
# i.e. "the model substitutes text here". Covers ''' and \"\"\" as well as the
# single-character quotes, because the CRITICAL sink used a RAW triple-quote.
_QUOTED_PLACEHOLDER = re.compile(
    r"""(?P<q>'''|\"\"\"|'|")(?:(?!(?P=q)).)*?<[^>\n]*>(?:(?!(?P=q)).)*?(?P=q)"""
)


def _fences(lines):
    """Yield ``(open_lineno, close_lineno, info)`` for every fenced block."""
    out, open_i, info = [], None, None
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith("```"):
            continue
        if open_i is None:
            open_i, info = i, stripped[3:].strip()
        else:
            out.append((open_i, i, info))
            open_i, info = None, None
    return out


def heredoc_bodies(text):
    """The project's shared extractor: every ``<<'PY'`` … ``PY`` body, dedented.

    This is what the orchestrator actually executes — the shell wrapper line and
    the markdown indentation are not part of it. Kept byte-compatible with
    ``tests/test_skill_floor_contract.py`` and ``tests/test_critic_shapes_e2e.py``
    so all three drive the same text.
    """
    bodies, cur = [], None
    for line in text.splitlines():
        if cur is None:
            if line.rstrip().endswith("<<'PY'"):
                cur = []
        elif line.strip() == "PY":
            bodies.append(textwrap.dedent("\n".join(cur)))
            cur = None
        else:
            cur.append(line)
    return bodies


def python_regions(text):
    """Return ``[(lineno, line)]`` for every PYTHON-EXECUTABLE line of the SKILL.

    Two shapes carry executable Python in this program: a ```` ```python ````
    fence, and the body of a ``python3 - … <<'PY'`` heredoc inside a bare fence.
    The heredoc's own wrapper line is shell, not Python, and is excluded — it is
    where ``PYTHONPATH="…"`` lives, which would otherwise swamp the signal.
    """
    lines = text.splitlines()
    out = []
    for start, end, info in _fences(lines):
        body = [(start + 1 + k, ln) for k, ln in enumerate(lines[start:end - 1])]
        heredoc = [k for k, (_, ln) in enumerate(body) if "<<'PY'" in ln]
        if heredoc:
            first = heredoc[0]
            closes = [k for k, (_, ln) in enumerate(body) if ln.strip() == "PY"]
            last = closes[0] if closes else len(body)
            out.extend(body[first + 1:last])
        elif info in ("python", "py"):
            out.extend(body)
    return out


# Every quoted placeholder that is NOT a foreign-text sink, with the reason it
# is safe. Keyed by the exact stripped source line so the table survives line
# drift; an entry matching nothing is a failure (see the round-trip test).
WAIVED = {
    'argument-hint: "<rough coding request> [verify_cmd: <cmd>] [success: <criteria>] '
    '[scope: <paths>] | ping"':
        "YAML frontmatter shown to the user as the slash-command's argument hint. "
        "Never executed, never parsed as Python.",
    'python3 -c "from scripts import <mod>; ..."':
        "The script-call convention template. <mod> is a plugin module name chosen by "
        "the SKILL author; no model-, user- or repo-supplied text can reach it.",
    '`ctxstore.advance(".atlas","$ATLAS_SESSION_ID","CLARIFY", '
    'updates={"clarify_resolution":"<what was asked/assumed>"})`.':
        "A one-line summary the ORCHESTRATOR composes itself, not verbatim foreign "
        "text. CLARIFY is bookkeeping, not a gate: a broken quote is an immediately "
        "visible error, never a forged green.",
    '- `ctxstore.advance(".atlas","$ATLAS_SESSION_ID","TRIAGED", archetype="<class>")`.':
        "One of four author-enumerated archetype words (bugfix/feature/refactor/test).",
    '> `ctxstore.write_artifact(".atlas","$ATLAS_SESSION_ID","review_root", "<root>")`.':
        "A path the orchestrator itself selects — '.', '.atlas/<run_id>/worktree', or a "
        "sandbox it created. Not target- or model-supplied.",
    '**`review_root = "<that sandbox dir>"`**; unattended coder runs are permitted '
    "**only** against":
        "Prose describing the value, not an executable line.",
    '- `ctxstore.advance(".atlas","$ATLAS_SESSION_ID","CODED", agent="elite-coder", '
    'status="<coder STATUS>")`.':
        "The coder's enumerated status token.",
    '- `ctxstore.advance(".atlas","$ATLAS_SESSION_ID","VERIFIED", '
    'verdict="<provisional_status>")`.':
        "One of the enumerated verdict words computed by the FROZEN pure gate.",
    '`ctxstore.advance(".atlas","$ATLAS_SESSION_ID","VERIFIED", '
    'verdict="<provisional_status>", updates={"checkpoints": '
    'dict(ctxstore.get_state(".atlas","$ATLAS_SESSION_ID").get("checkpoints") '
    'or {}, VERIFIED="<sha>")})`':
        "The passing-VERIFIED checkpoint riding the VERIFIED transition's own advance "
        "(H3/H-1). <provisional_status> is an enumerated verdict word from the FROZEN "
        "pure gate and <sha> is a hex git ref the orchestrator just created — both "
        "machine-generated, neither foreign text.",
    '`ctxstore.advance(".atlas","$ATLAS_SESSION_ID","REFINE", '
    'updates={"checkpoints": '
    'dict(ctxstore.get_state(".atlas","$ATLAS_SESSION_ID").get("checkpoints") '
    'or {}, CODED="<sha>")})`':
        "The pre-re-dispatch CODED checkpoint riding the REFINE transition's own "
        "advance (H3/H-1: it may not ride CODED's, which fires before any lens runs). "
        "<sha> is a hex git ref the orchestrator just created — machine-generated, "
        "never foreign text.",
    '(`ctxstore.advance(..., timeout_agent="<id>")` or `write_artifact`), then '
    "**degrade by":
        "An agent id from the fixed role set under `agents/`.",
    '`Agent(subagent_type="kimi-atlas:<role>", prompt=<task packet ONLY>)` — no role reference and':
        "The by-name dispatch template (Stage 4): <role> is one of the fixed role "
        "names under `agents/`, chosen by the SKILL author, never model- or "
        "repo-supplied text. Prose, not an executed line.",
    'judgment lenses** run as isolated `Agent(subagent_type="kimi-atlas:<lens>-critic")` critics (1 CORRECTNESS, 2':
        "The by-name dispatch template (Stage 4): <lens> is one of the three fixed "
        "critic lenses (correctness/code-quality/security), author-enumerated. "
        "Prose, not an executed line.",
    '`Agent(subagent_type="kimi-atlas:<lens>-critic", …)` (a critic must be read-only ⇒ its own':
        "Same by-name dispatch template as above, restated at the critic-wave "
        "dispatch site. <lens> is author-enumerated, never foreign text.",
    '3. Call `Agent(subagent_type="kimi-atlas:<lens>-critic", prompt=<packet ONLY>)`':
        "Same by-name dispatch template, restated at the literal Agent() call site. "
        "<lens> is author-enumerated, never foreign text.",
}


class TestNoForeignTextReachesPythonSource(unittest.TestCase):
    """The hard pin and its enumerate-and-waive widening."""

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")

    def test_no_python_region_carries_a_quoted_placeholder(self):
        """ZERO tolerance inside anything the orchestrator actually executes."""
        offenders = [
            "SKILL.md:%d: %s" % (n, ln.strip())
            for n, ln in python_regions(self.text)
            if _QUOTED_PLACEHOLDER.search(ln)
        ]
        self.assertEqual(offenders, [], "foreign text interpolated into Python source: %s" % offenders)

    def test_the_python_region_scanner_is_not_vacuous(self):
        """Control. A scanner that finds nothing would make the pin above free.

        Pins that the four rewritten blocks really are inside the scanned region.
        """
        found = "\n".join(ln for _, ln in python_regions(self.text))
        self.assertIn("ctxstore.init_run", found)
        self.assertIn("quality.enforce_critic_schema", found)
        self.assertIn('"context.json"', found)
        self.assertIn('"plan.md"', found)
        self.assertGreater(len(python_regions(self.text)), 100)

    def test_every_quoted_placeholder_anywhere_is_enumerated_and_waived(self):
        """The widened pin: the whole SKILL, not just the executable regions."""
        unwaived = []
        for n, line in enumerate(self.text.splitlines(), 1):
            if not _QUOTED_PLACEHOLDER.search(line):
                continue
            if line.strip() not in WAIVED:
                unwaived.append("SKILL.md:%d: %s" % (n, line.strip()))
        self.assertEqual(unwaived, [],
                         "a quoted placeholder with no recorded waiver: %s" % unwaived)

    def test_no_waiver_has_gone_stale(self):
        """A waiver matching nothing is a rubber stamp — delete it, don't keep it."""
        present = {ln.strip() for ln in self.text.splitlines()}
        stale = sorted(k for k in WAIVED if k not in present)
        self.assertEqual(stale, [], "stale waiver(s) — the line no longer exists: %s" % stale)

    def test_every_waiver_states_a_reason(self):
        for key, reason in WAIVED.items():
            with self.subTest(site=key[:60]):
                self.assertGreater(len(reason.strip()), 30, "waiver without a real reason")


class TestEverySinkReadsAFile(unittest.TestCase):
    """FOLD (challenge F4): pin that each block READS A FILE.

    ``:252`` was ``'''…'''`` — **non-raw** — so Python interpreted the digest's
    ``\\n`` escapes before ``json.loads`` ever saw them, and
    ``untrusted_excerpts`` always carry ``\\n``: a 100%-reproducible honest false
    RED. An implementer told "fix it the same way as Step 3.4" might add an ``r``
    prefix, which repairs the mangling and leaves the break-out wide open. So the
    pin is the positive property (path in ``argv``), never the negative one.

    Every assertion below is made on the block's **AST**, never on its text. A
    text pin here is vacuous in a way this suite has been bitten by before:
    mutating the call to ``encoding="utf-8"`` leaves the word ``utf-8-sig`` in
    the explanatory comment directly above it, so ``assertIn("utf-8-sig", block)``
    survives the mutation. Measured: it did. The AST cannot see comments.
    """

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        self.bodies = heredoc_bodies(self.text)

    def _tree(self, needle):
        """The parsed AST of the single EXECUTED block containing ``needle``."""
        blocks = [b for b in self.bodies if needle in b]
        self.assertEqual(len(blocks), 1,
                         "expected exactly one executed block containing %r, found %d"
                         % (needle, len(blocks)))
        return ast.parse(blocks[0].replace("$ATLAS_SESSION_ID", "SID")), blocks[0]

    @staticmethod
    def _read_calls(tree):
        return [n for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "read_text"]

    @staticmethod
    def _argv_index_nodes(tree):
        return [n for n in ast.walk(tree)
                if isinstance(n, ast.Subscript)
                and isinstance(n.value, ast.Attribute) and n.value.attr == "argv"]

    def _assert_reads_from_argv(self, needle, want_bom_tolerant=True):
        tree, _src = self._tree(needle)
        reads = self._read_calls(tree)
        self.assertTrue(reads, "%s: the block does not READ A FILE at all" % needle)
        self.assertTrue(self._argv_index_nodes(tree),
                        "%s: nothing is indexed out of sys.argv -- the text is still "
                        "coming from somewhere other than a path argument" % needle)
        if want_bom_tolerant:
            encodings = {kw.value.value for r in reads for kw in r.keywords
                         if kw.arg == "encoding" and isinstance(kw.value, ast.Constant)}
            self.assertEqual(encodings, {"utf-8-sig"},
                             "%s: read_text(encoding=...) is %s, so a BOM-prefixed body "
                             "manufactures a RED on a green tree" % (needle, sorted(encodings)))

    def test_the_critic_persistence_block_reads_its_text_from_argv(self):
        self._assert_reads_from_argv("quality.enforce_critic_schema")

    def test_the_grounding_digest_block_reads_its_text_from_argv(self):
        self._assert_reads_from_argv('write_artifact(".atlas", "$ATLAS_SESSION_ID", "context.json"')

    def test_the_init_packet_block_reads_its_text_from_argv(self):
        self._assert_reads_from_argv("ctxstore.init_run")

    def test_the_plan_preview_block_reads_its_text_from_argv(self):
        self._assert_reads_from_argv('"plan.md"')

    def test_no_sink_block_binds_its_text_from_a_source_literal(self):
        """The negative half, structurally: in each rewritten block the value that
        reaches ``json.loads``/``write_artifact`` must come from a ``read_text``
        call, never from a ``Constant``. Catches the fold-F4 trap (adding an ``r``
        prefix to ``'''<returned JSON>'''`` fixes the escape-mangling and leaves the
        break-out wide open) without ever mentioning ``r'''``.
        """
        for needle in ("quality.enforce_critic_schema",
                       'write_artifact(".atlas", "$ATLAS_SESSION_ID", "context.json"',
                       "ctxstore.init_run", '"plan.md"'):
            with self.subTest(block=needle):
                tree, _src = self._tree(needle)

                def _is_placeholder(node):
                    return (isinstance(node, ast.Constant) and isinstance(node.value, str)
                            and "<" in node.value and ">" in node.value)

                # (i) a placeholder handed DIRECTLY to a sink call, and
                # (ii) a placeholder bound to a name first (the shipped C1 shape
                #      was ``RAW = r'''<...>'''`` then ``json.loads(RAW)``, which a
                #      call-arguments-only scan cannot see -- measured: it did not).
                bad = [ast.dump(n) for n in ast.walk(tree)
                       if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                           and n.func.attr in ("loads", "write_artifact", "init_run")
                           and any(_is_placeholder(a) for a in n.args))
                       or (isinstance(n, ast.Assign) and _is_placeholder(n.value))
                       or (isinstance(n, ast.Dict)
                           and any(_is_placeholder(v) for v in n.values))]
                self.assertEqual(bad, [], "a placeholder literal still reaches a sink")

    def test_the_read_is_inside_the_try(self):
        """FOLD (challenge F5): a decode failure must land on the documented
        ``CRITIC_INVALID:`` line, not escape as a bare traceback."""
        tree, _src = self._tree("quality.enforce_critic_schema")
        tries = [n for n in ast.walk(tree) if isinstance(n, ast.Try)]
        self.assertTrue(tries, "no try: guards the read")
        guarded = [t for t in tries
                   if any(self._read_calls(stmt) for stmt in t.body)]
        self.assertTrue(guarded,
                        "read_text() sits outside every try -- a decode failure on a "
                        "BOM-less non-UTF-8 body escapes as a bare traceback")
        caught = set()
        for handler in guarded[0].handlers:
            names = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
            caught |= {n.id for n in names if isinstance(n, ast.Name)}
        self.assertIn("OSError", caught,
                      "an IO failure (the scratch file absent, i.e. a skipped Write) "
                      "escapes the handler")
        self.assertIn("ValueError", caught,
                      "a decode/JSON failure escapes the handler (UnicodeDecodeError "
                      "and JSONDecodeError are both ValueErrors)")

    def test_the_write_side_is_the_native_write_tool_and_heredocs_are_forbidden(self):
        """FOLD (challenge F1): the plan gave only the read side, and the natural
        filling is circular. A *quoted shell heredoc* as the writer is itself
        breakable — a critic body containing a line reading ``EOF`` gave rc=0, a
        PWNED marker AND a truncated file; a Python heredoc writer is worse.
        """
        self.assertIn("`Write` the critic's final message verbatim", self.text)
        self.assertIn("cat <<'EOF'", self.text,
                      "the SKILL must name the forbidden writer explicitly")
        forbid = self.text[self.text.index("Step 3.4 — persist ONE critic"):]
        forbid = forbid[:forbid.index("Step 4 + 5")]
        self.assertIn("only** sanctioned writer", forbid)
        self.assertNotIn("tempfile.mkstemp", self.text,
                         "mkstemp cannot run before the text exists (fold F6)")


class TestFailOpenProbes(unittest.TestCase):
    """Drive the SHIPPED Step-3.4 block and probe the honest directions.

    The governing rule of this release: *a fix that manufactures a RED on an
    honest repository is worse than the bug it closes.* Three of v1.5.2's seven
    defects were that failure, so every input an honest run can produce is
    probed here by execution.
    """

    @classmethod
    def setUpClass(cls):
        text = _SKILL.read_text(encoding="utf-8")
        blocks = [b for b in heredoc_bodies(text)
                  if "enforce_critic_schema" in b and "object_pairs_hook" in b]
        assert len(blocks) == 1, (
            "expected exactly one Step-3.4 validate-and-persist block, found %d"
            % len(blocks))
        cls.block = blocks[0]

    def _run(self, payload_bytes, write_payload=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = pathlib.Path(tmp.name)
        run_dir = d / ".atlas" / "$ATLAS_SESSION_ID"
        run_dir.mkdir(parents=True)
        src = d / "critic.raw.json"
        if write_payload:
            src.write_bytes(payload_bytes)
        env = dict(os.environ, PYTHONPATH=str(_ROOT), PYTHONSAFEPATH="1")
        proc = subprocess.run([sys.executable, "-c", self.block, str(src)],
                              cwd=str(d), capture_output=True, text=True,
                              timeout=60, env=env)
        return proc, d, run_dir

    @staticmethod
    def _critic(message):
        return json.dumps({
            "dimensions": {dim: "yes" for dim in rubric.DIMENSIONS},
            "defects": [{"id": "C1", "severity": "LOW", "category": "CORRECTNESS",
                         "location": "m.py:3", "message": message, "fix": "close it"}],
            "verdict": "OK",
        }).encode("utf-8")

    def test_a_critic_quoting_every_sentinel_still_persists(self):
        """The single most important fail-open probe.

        ``'''`` and ``\"\"\"`` broke the source literal; a bare ``EOF`` line broke
        the shell-heredoc writer the fold rejected; a bare ``PY`` line breaks the
        heredoc that carries the block itself. An honest critic reviewing this very
        repository emits all four.
        """
        message = "docstring ''' and \"\"\" here\nEOF\nPY\n' \" \\ %s ${X} `cmd`"
        proc, _d, run_dir = self._run(self._critic(message))
        self.assertEqual(proc.returncode, 0,
                         "an honest critic quoting the sentinels was rejected: %s"
                         % (proc.stdout + proc.stderr))
        got = json.loads((run_dir / "critic_correctness.json").read_text(encoding="utf-8"))
        self.assertEqual(got["defects"][0]["message"], message,
                         "the message did not survive the round trip byte-for-byte")

    def test_an_executing_payload_does_not_execute(self):
        """The C1 reproduction, driven through the shipped block."""
        payload = (b"{}''' \nimport pathlib; pathlib.Path('RCE_MARKER').write_text('x')\n"
                   b"RAW = '''{}")
        proc, d, run_dir = self._run(payload)
        self.assertNotEqual(proc.returncode, 0, "an injection payload was accepted")
        self.assertFalse((d / "RCE_MARKER").exists(), "the payload EXECUTED")
        self.assertFalse((run_dir / "critic_correctness.json").exists(),
                         "an invalid critic was persisted")
        self.assertIn("CRITIC_INVALID:", proc.stdout)

    def test_invalid_utf8_lands_on_the_documented_line(self):
        """FOLD (challenge F5): invalid UTF-8 must not escape as a bare traceback."""
        proc, _d, run_dir = self._run(b'{"verdict": "OK", "x": "\xff\xfe"}')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CRITIC_INVALID:", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertFalse((run_dir / "critic_correctness.json").exists())

    def test_a_missing_scratch_file_is_a_rejection_not_a_crash(self):
        """A skipped or failed `Write` must fail CLOSED, on the documented line."""
        proc, _d, run_dir = self._run(b"", write_payload=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CRITIC_INVALID:", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertFalse((run_dir / "critic_correctness.json").exists())

    def test_a_bom_prefixed_body_persists(self):
        proc, _d, run_dir = self._run(b"\xef\xbb\xbf" + self._critic("plain"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((run_dir / "critic_correctness.json").is_file())

    def test_crlf_and_a_trailing_newline_persist(self):
        raw = self._critic("windows line endings").replace(b"\n", b"\r\n") + b"\r\n"
        proc, _d, run_dir = self._run(raw)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((run_dir / "critic_correctness.json").is_file())

    def test_a_duplicate_key_is_still_rejected(self):
        """The S4 dup-key rejection must survive the rewrite."""
        proc, _d, run_dir = self._run(b'{"verdict": "OK", "verdict": "FAIL"}')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("duplicate key", proc.stdout)
        self.assertFalse((run_dir / "critic_correctness.json").exists())

    def test_a_schema_violation_is_still_rejected(self):
        """`enforce_critic_schema` must still run — the S4 layer is not bypassed."""
        proc, _d, run_dir = self._run(b'{"dimensions": {}, "defects": [], "verdict": "OK"}')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CRITIC_SCHEMA_ERRORS:", proc.stdout)
        self.assertFalse((run_dir / "critic_correctness.json").exists())

    def test_the_scratch_file_is_consumed(self):
        """A stale scratch file must never be re-read as a fresh lens."""
        proc, d, _run_dir = self._run(self._critic("fine"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((d / "critic.raw.json").exists(),
                         "the scratch file survived and can be re-read next pass")

    def test_the_pass_stamp_survives(self):
        """S5: the artifact must still carry the refine-pass stamp."""
        proc, _d, run_dir = self._run(self._critic("fine"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        got = json.loads((run_dir / "critic_correctness.json").read_text(encoding="utf-8"))
        self.assertEqual(got.get("pass"), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
