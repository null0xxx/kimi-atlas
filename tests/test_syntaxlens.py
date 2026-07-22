"""Acceptance tests for :mod:`scripts.syntaxlens` — the sole ``nativefloor`` consumer.

Host-independent throughout. The config-parse policy (strict-format map, byte
bound, the four CRITICAL false-block regressions, and the guarded
``RecursionError``/``MemoryError`` arm) is proven in-process — no subprocess. The
source-dispatch rule (which exts are NEVER dispatched) is proven with NO tool:
an un-dispatched ext never reaches a subprocess.

JS (``.js``/``.mjs``/``.cjs``) is deliberately NOT syntax-checked. ``node --check``
cannot distinguish valid JSX/Flow — which ship pervasively INSIDE ordinary ``.js``
files (Create React App, most React repos, Flow-typed source) — from invalid JS,
so checking it would FALSE-BLOCK valid React/Flow repos (a valid
``const B = () => <button/>;`` in a ``.js`` makes ``node --check`` exit non-zero).
JS is verified via the run-signal floor (test-running) instead. JS therefore has
no ``SYNTAX_ARGV`` entry and is never dispatched — proven below with no node.
"""
import json
import unittest
from unittest import mock

from scripts import syntaxlens


def _blocking(defects):  # HIGH/CRITICAL count as blocking
    return [d for d in defects if d["severity"] in ("HIGH", "CRITICAL")]


class TestConfigParse(unittest.TestCase):
    def test_invalid_strict_json_config_blocks(self):
        d = syntaxlens.check({"package.json": "{ not json"}, cwd=".")
        self.assertTrue(_blocking(d)); self.assertEqual(d[0]["category"], "DOES-IT-RUN")

    def test_invalid_toml_lock_blocks(self):
        # poetry.lock IS TOML and IS in _STRICT_CONFIG -> a broken one blocks.
        self.assertTrue(_blocking(syntaxlens.check({"poetry.lock": "= = = broken"}, cwd=".")))

    # --- the four CRITICAL false-block regressions the plan-challenge caught: all must NOT block ---
    def test_tsconfig_jsonc_is_NOT_blocked(self):
        # tsc --init emits JSONC: // comments + trailing commas. strict json.loads would reject it,
        # but tsconfig.json is NOT in _STRICT_CONFIG -> advisory at most, NEVER blocking.
        tsconfig = '{\n  // editor hints\n  "compilerOptions": { "strict": true, },\n}\n'
        self.assertFalse(_blocking(syntaxlens.check({"tsconfig.json": tsconfig}, cwd=".")))

    def test_yarn_lock_opaque_is_NOT_blocked(self):
        self.assertFalse(_blocking(syntaxlens.check({"yarn.lock": "# yarn lockfile v1\nfoo@1:\n  version 1\n"}, cwd=".")))

    def test_gemfile_lock_opaque_is_NOT_blocked(self):
        self.assertFalse(_blocking(syntaxlens.check({"Gemfile.lock": "GEM\n  specs:\n    rake (13.0)\n"}, cwd=".")))

    def test_arbitrary_data_json_is_NOT_blocked(self):
        self.assertFalse(_blocking(syntaxlens.check({"fixtures/sample.json": "{ not json"}, cwd=".")))

    def test_valid_config_no_defect(self):
        self.assertEqual(syntaxlens.check({"package.json": json.dumps({"name": "x"})}, cwd="."), [])

    def test_bom_prefixed_valid_package_json_is_NOT_blocked(self):
        # A leading UTF-8 BOM (﻿) is stripped/accepted by npm and node's loader.
        # A valid package.json carrying one must NOT false-block (strip before json.loads).
        bom_config = "﻿" + json.dumps({"name": "x"})
        self.assertEqual(syntaxlens.check({"package.json": bom_config}, cwd="."), [])

    def test_bom_prefixed_valid_toml_BLOCKS_deliberate_json_vs_toml_asymmetry(self):
        # The JSON-vs-TOML BOM decision, pinned as an EXPLICIT, GUARDED asymmetry.
        #   * JSON: npm/node STRIP a leading BOM and accept the file, so a BOM'd valid
        #     package.json must NOT false-block -> _loads_json_bom strips it (asserted above).
        #   * TOML: cargo and tomllib REJECT a BOM'd document (cargo issue #2031: a BOM'd
        #     Cargo.toml "could not parse input as TOML"; tomllib raises TOMLDecodeError),
        #     so the build genuinely cannot read it -> BLOCKING is correct, NOT a false-block.
        # _config_defect deliberately does NOT strip the BOM on the TOML branch, so a
        # BOM-prefixed valid pyproject.toml surfaces a HIGH DOES-IT-RUN defect. This test
        # pins that intended decision so the asymmetry can't silently flip either way.
        valid_toml = "[tool.poetry]\nname = \"x\"\n"
        # Control: the SAME TOML WITHOUT a BOM is valid and must NOT block.
        self.assertEqual(syntaxlens.check({"pyproject.toml": valid_toml}, cwd="."), [])
        # With a leading BOM it BLOCKS (matches cargo/tomllib; the build can't parse it).
        d = syntaxlens.check({"pyproject.toml": "﻿" + valid_toml}, cwd=".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")
        self.assertEqual(d[0]["severity"], "HIGH")

    def test_same_named_broken_configs_report_distinct_locations(self):
        # Two same-named broken configs in different dirs must yield two defects with
        # distinct real-path locations (not the bare basename). Ids are now per-file
        # UNIQUE (SYN<n>-config-<basename>, minted after sorting) so they no longer
        # collide into one — each still carries the descriptive config-<basename> tail.
        d = syntaxlens.check({"vendor/package.json": "{ not json",
                              "a/package.json": "{ not json"}, cwd=".")
        blocking = _blocking(d)
        self.assertEqual(len(blocking), 2)
        self.assertEqual({b["location"] for b in blocking}, {"vendor/package.json", "a/package.json"})
        self.assertEqual(len({b["id"] for b in blocking}), 2)   # per-file-unique, not collided
        for b in blocking:
            self.assertRegex(b["id"], r"^SYN\d+-config-package\.json$")

    def test_oversize_config_is_not_parsed(self):
        self.assertFalse(_blocking(syntaxlens.check({"package.json": "{" + "0" * 2_000_000}, cwd=".")))

    def test_recursionerror_deep_json_is_graceful_defect_not_raise(self):
        # MEDIUM (TA): the RecursionError/MemoryError arm of _config_defect's guard
        # must turn a pathological-but-under-cap config into a GRACEFUL HIGH
        # DOES-IT-RUN defect, NOT a raise that aborts the VERIFIED lens. Deeply-nested
        # JSON arrays exceed json.loads's recursion limit (a RecursionError, NOT a
        # ValueError); dropping RecursionError from the guard would let it propagate
        # and turn a graceful defect into a lens-aborting raise. ~200 KB stays under
        # _CONFIG_MAX_BYTES so it is actually parsed (not skipped as oversize).
        deep = "[" * 100000 + "]" * 100000
        self.assertLess(len(deep.encode("utf-8")), syntaxlens._CONFIG_MAX_BYTES)
        d = syntaxlens.check({"package.json": deep}, cwd=".")   # must NOT raise
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")
        self.assertEqual(d[0]["severity"], "HIGH")

    def test_memoryerror_parse_is_graceful_defect_not_raise(self):
        # The MemoryError arm of _config_defect's `except (ValueError, RecursionError,
        # MemoryError)` guard (docstring claims all three) is otherwise untested — only
        # ValueError + RecursionError have proofs, so narrowing the guard to drop
        # MemoryError would ship green. A MemoryError from the underlying parse (a
        # genuinely possible outcome on a pathological under-cap config) must degrade to
        # a GRACEFUL HIGH DOES-IT-RUN defect, NOT propagate and abort the VERIFIED lens.
        # Patch the shared JSON entry point to raise it; check() must NOT raise.
        with mock.patch.object(syntaxlens, "_loads_json_bom", side_effect=MemoryError("boom")):
            d = syntaxlens.check({"package.json": '{"name": "x"}'}, cwd=".")   # must NOT raise
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")
        self.assertEqual(d[0]["severity"], "HIGH")


class TestSourceDispatch(unittest.TestCase):
    """Which exts are dispatched to a parse checker — proven with NO tool (an
    un-dispatched ext never reaches a subprocess, so this is host-independent)."""

    def test_jsx_ts_tsx_never_dispatched(self):
        for name, src in (("c.jsx", "<App/>;"), ("a.ts", "let x: number ="), ("b.tsx", "<X/>")):
            self.assertEqual(syntaxlens.check({name: src}, cwd="."), [], name)

    def test_valid_react_jsx_in_js_is_not_blocked(self):
        # THE headline guarantee: a VALID React component living in a `.js` file
        # (JSX inside .js is pervasive — CRA, most React repos) must NOT be blocked.
        # `node --check` would exit non-zero on the `<button>` token and false-block
        # a valid repo; the fix drops JS from the syntax floor entirely, so `.js` is
        # never dispatched and never a defect. cwd is irrelevant (JS is not dispatched).
        src = "const Button = () => <button>Click</button>;\nexport default Button;\n"
        self.assertEqual(syntaxlens.check({"src/Button.js": src}, cwd="."), [])

    def test_js_mjs_cjs_are_never_dispatched(self):
        # None of .js/.mjs/.cjs has a SYNTAX_ARGV entry, so none is dispatched — even
        # content that `node --check` WOULD reject (Flow types, JSX) never blocks.
        for name, src in (
            ("app.js", "const x: number = 1;\n"),     # Flow annotation — invalid JS, valid Flow
            ("mod.mjs", "export const y = () => <X/>;\n"),
            ("legacy.cjs", "const z = () => <Y/>;\n"),
        ):
            self.assertEqual(syntaxlens.check({name: src}, cwd="."), [], name)


class TestMalformedInputGuards(unittest.TestCase):
    """`check()` never raises on a malformed changed_files map (contract is dict[str,str])."""

    def test_non_str_key_is_skipped_not_raised(self):
        # A non-str KEY must be skipped (symmetry with the non-str VALUE guard),
        # never raise a TypeError out of check() at os.path.basename; the valid
        # str-keyed entry still processes (a `.js` is simply not dispatched -> []).
        d = syntaxlens.check({123: "x", "ok.js": "const x=1;\n"}, cwd=".")
        self.assertEqual(_blocking(d), [])   # did not raise; ok.js not dispatched -> no block


if __name__ == "__main__":
    unittest.main()
