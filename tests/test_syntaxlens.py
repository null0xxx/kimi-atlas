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
import json, os, shutil, signal, tempfile, unittest
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


class TestMaterializeExtDecision(unittest.TestCase):
    """Non-vacuous, node-INDEPENDENT proof the .js ESM/CJS ext decision is load-bearing
    in BOTH directions. Inverting `_materialize_ext` EITHER way flips an assertion RED.

    Why a unit test and not two end-to-end node arms: Node 22+ auto-detects ESM
    syntax inside a `.js` (top-level `import`/`export`/`await`/`import.meta` all parse
    clean as a bare `.js`), which would MASK the `type:module -> .mjs` direction end to
    end. Pinning the decision itself is the faithful both-directions guard; the
    end-to-end CJS arm below adds real teeth against the always-`.mjs` mutation."""

    def test_js_ext_decision_is_load_bearing_both_directions(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "src"))
            # No package.json type -> CJS default -> materialize as `.js`.
            # (Inverting to always-`.mjs` fails HERE.)
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".js")
            with open(os.path.join(root, "package.json"), "w") as f:
                f.write('{"type":"module"}')
            # type:module -> ESM -> materialize as `.mjs`.
            # (Inverting to always-`.js` fails HERE.)
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".mjs")
            # Explicit .mjs/.cjs keep their mode regardless of the nearest package type.
            self.assertEqual(syntaxlens._materialize_ext(".mjs", "src/app.js", root), ".mjs")
            self.assertEqual(syntaxlens._materialize_ext(".cjs", "src/app.js", root), ".cjs")


@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestEsmCjsMaterializationLive(unittest.TestCase):
    """End-to-end teeth for the ext decision on real node — the false-block guard for
    the one place `_nearest_package_type` is load-bearing."""

    def test_cjs_sloppy_only_js_stays_green(self):
        # `var x = 0777;` (legacy octal) is a SyntaxError under ESM/strict (.mjs) but
        # VALID in sloppy-mode CJS. With NO type:module it MUST materialize as `.js`
        # and stay GREEN. Inverting to always-`.mjs` makes node reject it -> RED. This
        # is exactly the mutation the finding called out ("always-.mjs keeps the suite
        # green"); with this arm it no longer does.
        with tempfile.TemporaryDirectory() as root:
            d = syntaxlens.check({"legacy.js": "var x = 0777;\n"}, cwd=root)
            self.assertFalse(_blocking(d), "sloppy-mode CJS .js must NOT be materialized as ESM")

    def test_esm_js_under_type_module_stays_green(self):
        # Valid-repo guard: a valid ESM `.js` under type:module must stay GREEN (the
        # floor must never false-block it). Node auto-detect makes this pass under
        # either ext, so the both-directions inversion proof lives in the unit test
        # above; this arm pins the end-to-end valid-repo contract.
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "package.json"), "w") as f:
                f.write('{"type":"module"}')
            os.makedirs(os.path.join(root, "src"))
            d = syntaxlens.check(
                {"src/app.js": "import path from 'node:path';\nexport const x = 1;\n"},
                cwd=root,
            )
            self.assertFalse(_blocking(d))


class TestUntrustedConfigRead(unittest.TestCase):
    """CRITICAL: `_read_package_type` reads package.json straight from the untrusted
    repo tree. It MUST be bounded and non-following so `check()` never hangs/raises."""

    def _check_within(self, changed, cwd, seconds=8):
        """Run syntaxlens.check under a hard SIGALRM deadline; fail (not hang) if slow."""
        def _on_alarm(signum, frame):
            raise TimeoutError("syntaxlens.check hung on an untrusted config read")
        old = signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(seconds)
        try:
            return syntaxlens.check(changed, cwd=cwd)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

    @unittest.skipUnless(os.path.exists("/dev/zero"), "/dev/zero unavailable")
    def test_package_json_symlinked_to_dev_zero_does_not_hang(self):
        # The exact DoS repro: a package.json symlinked to /dev/zero used to make the
        # unbounded fh.read() HANG check() forever (an infinite stream of zero bytes).
        # isfile() now rejects the char-device target up front, so ESM/CJS resolution
        # returns promptly (type absent -> CJS default) and nothing blocks.
        with tempfile.TemporaryDirectory() as root:
            os.symlink("/dev/zero", os.path.join(root, "package.json"))
            os.makedirs(os.path.join(root, "src"))
            d = self._check_within({"src/app.js": "const x=1;\n"}, root)
            self.assertEqual(_blocking(d), [])   # returned promptly, no hang, no raise

    @unittest.skipUnless(os.path.exists("/dev/zero"), "/dev/zero unavailable")
    def test_read_helper_rejects_dev_zero_symlink(self):
        # Direct proof the helper returns None (bounded) for the char-device target.
        with tempfile.TemporaryDirectory() as root:
            link = os.path.join(root, "package.json")
            os.symlink("/dev/zero", link)
            self.assertIsNone(syntaxlens._read_package_type(link))

    def test_oversize_package_json_is_treated_as_absent(self):
        # A huge REGULAR package.json (a MemoryError vector for an unbounded read) is
        # bounded to the byte cap; the truncated read is invalid JSON -> treated as
        # absent (None), never raised — even with a valid {"type":"module"} prefix.
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "package.json")
            with open(path, "w") as fh:
                fh.write('{"type":"module","pad":"' + "x" * (syntaxlens._CONFIG_MAX_BYTES + 16) + '"}')
            self.assertIsNone(syntaxlens._read_package_type(path))

    def test_valid_package_json_esm_resolution_still_works(self):
        # The bound/guard must NOT change a real, in-cap package.json: type resolves.
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "package.json")
            with open(path, "w") as fh:
                fh.write('{"type":"module"}')
            self.assertEqual(syntaxlens._read_package_type(path), "module")


class TestPackageTypeResolutionMatrix(unittest.TestCase):
    """Node-parity ESM/CJS resolution: the NEAREST ``package.json`` is authoritative
    and the walk NEVER inherits an ancestor's ``type``. Node-INDEPENDENT (unit calls
    to ``_nearest_package_type``/``_materialize_ext``); the live monorepo arm below
    proves the SAME rule end to end on real node. Inverting any single row goes RED."""

    def _mk(self, root, rel_dir, contents):
        """Make ``root/rel_dir`` and drop a ``package.json`` with ``contents`` (None = none)."""
        d = os.path.join(root, rel_dir) if rel_dir else root
        os.makedirs(d, exist_ok=True)
        if contents is not None:
            with open(os.path.join(d, "package.json"), "w") as f:
                f.write(contents)

    def test_a_no_package_json_anywhere_is_cjs(self):
        with tempfile.TemporaryDirectory() as root:
            self._mk(root, "src", None)   # a dir, but no package.json anywhere
            self.assertIsNone(syntaxlens._nearest_package_type("src/app.js", root))
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".js")

    def test_b_nearest_type_module_is_esm(self):
        with tempfile.TemporaryDirectory() as root:
            self._mk(root, "", '{"type":"module"}')
            self._mk(root, "src", None)
            self.assertEqual(syntaxlens._nearest_package_type("src/app.js", root), "module")
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".mjs")

    def test_c_nearest_type_commonjs_is_cjs(self):
        with tempfile.TemporaryDirectory() as root:
            self._mk(root, "", '{"type":"commonjs"}')
            self._mk(root, "src", None)
            self.assertEqual(syntaxlens._nearest_package_type("src/app.js", root), "commonjs")
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".js")

    def test_d_nearest_typeless_ancestor_module_is_cjs_THE_BUG(self):
        # The regression: root type:module, sub/ type-LESS. Node stops at sub's
        # package.json (CJS default) and NEVER inherits root's module. The old walk
        # climbed PAST the type-less file and wrongly returned "module" -> .mjs ->
        # false-block. Nearest-wins must return None (CJS) and materialize `.js`.
        with tempfile.TemporaryDirectory() as root:
            self._mk(root, "", '{"type":"module"}')
            self._mk(root, "sub", '{"name":"sub"}')   # present but type-less -> CJS, STOP
            self.assertIsNone(syntaxlens._nearest_package_type("sub/legacy.js", root))
            self.assertEqual(syntaxlens._materialize_ext(".js", "sub/legacy.js", root), ".js")

    def test_e_nearest_typeless_no_ancestor_is_cjs(self):
        with tempfile.TemporaryDirectory() as root:
            self._mk(root, "", '{"name":"root"}')   # type-less, no ancestor
            self._mk(root, "src", None)
            self.assertIsNone(syntaxlens._nearest_package_type("src/app.js", root))
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".js")

    def test_bom_prefixed_package_json_type_resolves_to_module(self):
        # MEDIUM (BOM divergence): a BOM'd {"type":"module"} must resolve to ESM via
        # the shared BOM-stripping helper, not be misread as type-absent (which would
        # degrade ESM -> CJS `.js` and latently false-block on node 18/20).
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "package.json")
            with open(path, "w") as f:
                f.write("﻿" + '{"type":"module"}')   # leading UTF-8 BOM
            self.assertEqual(syntaxlens._read_package_type(path), "module")
            os.makedirs(os.path.join(root, "src"))
            self.assertEqual(syntaxlens._materialize_ext(".js", "src/app.js", root), ".mjs")


@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestMonorepoTypelessCjsLive(unittest.TestCase):
    """End-to-end teeth for the CRITICAL fix on real node: a type-less sub-package
    holding sloppy-mode CJS must NOT be false-blocked by an ancestor's type:module."""

    def test_typeless_subpackage_sloppy_cjs_is_not_false_blocked(self):
        # The exact CRITICAL repro: root {"type":"module"}, sub/ {"name":"sub"}
        # (type-less -> CJS), sub/legacy.js = `var x = 0777;` — a legacy-octal literal
        # that is VALID sloppy CJS (`node --check` exits 0) but a SyntaxError as .mjs.
        # Nearest-wins materializes it `.js` and it stays GREEN.
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "package.json"), "w") as f:
                f.write('{"type":"module"}')
            os.makedirs(os.path.join(root, "sub"))
            with open(os.path.join(root, "sub", "package.json"), "w") as f:
                f.write('{"name":"sub"}')
            d = syntaxlens.check({"sub/legacy.js": "var x = 0777;\n"}, cwd=root)
            self.assertEqual(_blocking(d), [])


class TestMalformedInputGuards(unittest.TestCase):
    """`check()` never raises on a malformed changed_files map (contract is dict[str,str])."""

    def test_non_str_key_is_skipped_not_raised(self):
        # A non-str KEY must be skipped (symmetry with the non-str VALUE guard),
        # never raise a TypeError out of check() at os.path.basename; the valid
        # str-keyed entry still processes.
        d = syntaxlens.check({123: "x", "ok.js": "const x=1;\n"}, cwd=".")
        self.assertEqual(_blocking(d), [])   # did not raise; ok.js valid -> no block


if __name__ == "__main__":
    unittest.main()
