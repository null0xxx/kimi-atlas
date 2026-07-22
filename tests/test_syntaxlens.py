"""Acceptance tests for :mod:`scripts.syntaxlens` — the sole ``nativefloor`` consumer.

Two tiers:

* **Host-independent** (``TestConfigParse``, ``TestNodeDispatch``) — the config
  parse policy (strict-format map, byte bound, the four CRITICAL false-block
  regressions) and the "jsx/ts/tsx are never dispatched" rule are proven with NO
  subprocess: config parsing is in-process, and un-dispatched exts never reach a
  tool. These run on every host.
* **Live-tool** (``TestNodeEsmLive``, ``skipUnless(node)``) — the ESM/CJS
  materialized-extension proof and the broken/clean ``.js`` proofs exercise the
  real ``node --check`` end to end. They skip cleanly when node is absent.
"""
import json, os, shutil, tempfile, unittest
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

    def test_same_named_broken_configs_report_distinct_locations(self):
        # Two same-named broken configs in different dirs must yield two defects with
        # distinct real-path locations (not the bare basename); id stays config-<basename>.
        d = syntaxlens.check({"vendor/package.json": "{ not json",
                              "a/package.json": "{ not json"}, cwd=".")
        blocking = _blocking(d)
        self.assertEqual(len(blocking), 2)
        self.assertEqual({b["location"] for b in blocking}, {"vendor/package.json", "a/package.json"})
        self.assertEqual({b["id"] for b in blocking}, {"config-package.json"})

    def test_oversize_config_is_not_parsed(self):
        self.assertFalse(_blocking(syntaxlens.check({"package.json": "{" + "0" * 2_000_000}, cwd=".")))

class TestNodeDispatch(unittest.TestCase):
    def test_jsx_ts_tsx_never_dispatched(self):
        for name, src in (("c.jsx", "<App/>;"), ("a.ts", "let x: number ="), ("b.tsx", "<X/>")):
            self.assertEqual(syntaxlens.check({name: src}, cwd="."), [], name)

@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestNodeEsmLive(unittest.TestCase):
    def test_esm_js_in_type_module_is_not_false_blocked(self):
        # A valid ESM `.js` (top-level import) under a "type":"module" package must be materialized as
        # .mjs and parse clean -> NO block. (Under CJS materialization node would SyntaxError on import.)
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "package.json"), "w") as f:
                f.write('{"type":"module"}')
            os.makedirs(os.path.join(root, "src"))
            d = syntaxlens.check({"src/app.js": "import path from 'node:path';\nexport const x = 1;\n"}, cwd=root)
            self.assertFalse(_blocking(d))

    def test_broken_js_blocks(self):
        self.assertTrue(_blocking(syntaxlens.check({"broken.js": "function ( {"}, cwd=".")))

    def test_valid_cjs_js_clean(self):
        self.assertEqual(syntaxlens.check({"ok.js": "const x = 1;\n"}, cwd="."), [])


if __name__ == "__main__":
    unittest.main()
