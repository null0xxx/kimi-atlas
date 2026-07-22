"""Unit tests for scripts/langfloor.py — the single run/floor language registry.

Task-2 acceptance bar (universal-floor P1, blueprint §2.1/§3/§4):
  * ``RUNNERS`` — the ordered marker→cmd probe list with precedence.
  * ``collectable_pytest`` — pytest's RECURSIVE discovery predicate (not only
    ``tests/``): any ``test_*.py``/``*_test.py`` anywhere, or a declared
    ``[tool.pytest.ini_options]``/``[tool:pytest]`` section.
  * ``resolve_runner_tag`` — map a frozen ``verify_cmd`` to an ordered set of
    runner tags: a direct token, or wrapper-expansion (Makefile ``test:`` recipe /
    ``package.json scripts.test``); unknown → ``()``. Fail-safe on missing files.
  * ``SYNTAX_ARGV`` / ``CONFIG_ALLOWLIST`` — declared, importable, tested.

Reading the Makefile / package.json is the ONLY I/O and must fail SAFELY
(missing/malformed → ``()``).
"""
import fnmatch
import tempfile
import unittest
from pathlib import Path

from scripts import langfloor


def _write(root: Path, relpath: str, text: str) -> None:
    """Materialize a file (creating parents) under ``root`` for a fixture repo."""
    dest = root / relpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


class TestRunnersRegistry(unittest.TestCase):
    """RUNNERS is the ONE ordered marker→cmd probe list with precedence."""

    def test_runners_is_ordered_by_precedence(self):
        precs = [entry["prec"] for entry in langfloor.RUNNERS]
        self.assertEqual(precs, sorted(precs))
        self.assertEqual(precs, list(range(len(langfloor.RUNNERS))))

    def test_every_entry_has_the_declared_schema(self):
        for entry in langfloor.RUNNERS:
            self.assertEqual(
                set(entry), {"marker", "cmd", "runner_tag", "prec"}
            )
            self.assertIsInstance(entry["marker"], tuple)
            self.assertTrue(entry["marker"])
            self.assertIsInstance(entry["cmd"], str)
            self.assertIsInstance(entry["runner_tag"], str)
            self.assertIsInstance(entry["prec"], int)

    def test_expected_marker_to_cmd_probes(self):
        by_cmd = {entry["cmd"]: entry for entry in langfloor.RUNNERS}
        self.assertIn("Makefile", by_cmd["make test"]["marker"])
        self.assertEqual(by_cmd["make test"]["prec"], 0)
        self.assertIn("package.json", by_cmd["npm test"]["marker"])
        self.assertEqual(by_cmd["npm test"]["prec"], 1)
        self.assertIn("Cargo.toml", by_cmd["cargo test"]["marker"])
        self.assertEqual(by_cmd["cargo test"]["prec"], 2)
        self.assertIn("go.mod", by_cmd["go test -json ./..."]["marker"])
        self.assertEqual(by_cmd["go test -json ./..."]["prec"], 3)
        gemfile = by_cmd["bundle exec rspec"]
        self.assertIn("Gemfile", gemfile["marker"])
        self.assertIn(".rspec", gemfile["marker"])
        self.assertEqual(gemfile["prec"], 4)

    def test_direct_runner_entries_agree_with_resolver(self):
        # For the direct-language entries the table's runner_tag must equal what
        # the resolver derives from the same cmd (single source of truth).
        for cmd in ("cargo test", "go test -json ./...", "bundle exec rspec"):
            entry = next(e for e in langfloor.RUNNERS if e["cmd"] == cmd)
            self.assertEqual(
                (entry["runner_tag"],), langfloor.resolve_runner_tag(cmd, ".")
            )


class TestCollectablePytest(unittest.TestCase):
    """Mirrors pytest's recursive rootdir discovery (blueprint §3, R7 COR)."""

    def test_recursive_test_file_outside_tests_dir(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "mytests/test_foo.py", "def test_x():\n    pass\n")
            self.assertTrue(langfloor.collectable_pytest(d))

    def test_trailing_underscore_test_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "pkg/deep/foo_test.py", "def test_y():\n    pass\n")
            self.assertTrue(langfloor.collectable_pytest(d))

    def test_source_only_repo_is_not_collectable(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "src/app.py", "print('hi')\n")
            self.assertFalse(langfloor.collectable_pytest(d))

    def test_pyproject_pytest_section_is_collectable(self):
        with tempfile.TemporaryDirectory() as d:
            _write(
                Path(d),
                "pyproject.toml",
                "[tool.pytest.ini_options]\naddopts = '-q'\n",
            )
            _write(Path(d), "src/app.py", "x = 1\n")
            self.assertTrue(langfloor.collectable_pytest(d))

    def test_setup_cfg_pytest_section_is_collectable(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "setup.cfg", "[tool:pytest]\naddopts = -q\n")
            self.assertTrue(langfloor.collectable_pytest(d))

    def test_empty_repo_is_not_collectable(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(langfloor.collectable_pytest(d))

    def test_stray_test_file_in_denylisted_dirs_is_not_collectable(self):
        # A dependency's own ``test_*.py`` vendored under ``.venv``/``node_modules``
        # (or copied into ``build``/``dist``/``__pycache__``) must NOT make a
        # non-Python repo resolve to pytest — those trees are pruned mid-walk.
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), ".venv/lib/python3.12/site-packages/x/test_dep.py",
                   "def test_x():\n    pass\n")
            _write(Path(d), "node_modules/pkg/test_bundled.py",
                   "def test_y():\n    pass\n")
            _write(Path(d), "build/lib/foo_test.py", "def test_z():\n    pass\n")
            _write(Path(d), "src/app.py", "print('hi')\n")
            self.assertFalse(langfloor.collectable_pytest(d))

    def test_genuine_test_file_beside_a_denylisted_dir_is_collectable(self):
        # Pruning must not over-reach: a real ``test_*.py`` in a normal package
        # still counts even when a ``.venv`` sits alongside it.
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), ".venv/lib/site.py", "x = 1\n")
            _write(Path(d), "tests/test_real.py", "def test_a():\n    pass\n")
            self.assertTrue(langfloor.collectable_pytest(d))


class TestResolveRunnerTagDirect(unittest.TestCase):
    """Direct runner tokens map to their canonical tag (cwd unused)."""

    def test_bare_pytest(self):
        self.assertEqual(langfloor.resolve_runner_tag("pytest", "."), ("pytest",))

    def test_python_m_pytest(self):
        self.assertEqual(
            langfloor.resolve_runner_tag("python -m pytest", "."), ("pytest",)
        )

    def test_python_m_unittest(self):
        self.assertEqual(
            langfloor.resolve_runner_tag("python3 -m unittest", "."), ("unittest",)
        )

    def test_go_test(self):
        # The discovered command carries `-json` (so a green `go test` emits the
        # `-json` events runsignal counts); the `\bgo\s+test\b` token still matches.
        self.assertEqual(
            langfloor.resolve_runner_tag("go test -json ./...", "."), ("go test",)
        )

    def test_cargo_test_does_not_leak_go_test(self):
        # 'cargo test' contains the substring 'go test'; word boundaries must
        # keep it from spuriously resolving to the go tag.
        self.assertEqual(
            langfloor.resolve_runner_tag("cargo test", "."), ("cargo test",)
        )

    def test_bundle_exec_rspec_wrapper_strip(self):
        self.assertEqual(
            langfloor.resolve_runner_tag("bundle exec rspec", "."), ("rspec",)
        )

    def test_poetry_run_pytest_wrapper_strip(self):
        self.assertEqual(
            langfloor.resolve_runner_tag("poetry run pytest", "."), ("pytest",)
        )

    def test_uv_run_pytest_wrapper_strip(self):
        self.assertEqual(
            langfloor.resolve_runner_tag("uv run pytest", "."), ("pytest",)
        )

    def test_jest_vitest_mocha_phpunit(self):
        self.assertEqual(langfloor.resolve_runner_tag("jest", "."), ("jest",))
        self.assertEqual(langfloor.resolve_runner_tag("vitest run", "."), ("vitest",))
        self.assertEqual(langfloor.resolve_runner_tag("mocha", "."), ("mocha",))
        self.assertEqual(langfloor.resolve_runner_tag("phpunit", "."), ("phpunit",))

    def test_pure_supported_polyglot_still_resolves(self):
        # COR-1 guard (no over-reach): an all-SUPPORTED polyglot — `go test` is a
        # known tag, not a residual `<word> test` — must still resolve to both.
        self.assertEqual(
            langfloor.resolve_runner_tag("pytest && go test -json ./...", "."),
            ("pytest", "go test"),
        )

    def test_supported_runner_beside_shell_script_arg_still_resolves(self):
        # `bash test.sh` is a shell SCRIPT, not a `<word> test` subcommand — the
        # residual detector must not trip on it and drop the real pytest tag.
        self.assertEqual(
            langfloor.resolve_runner_tag("pytest && bash test.sh", "."), ("pytest",)
        )

    def test_unsupported_runner_alone_is_empty(self):
        # A bare unsupported runner resolves to () just as an unknown token does.
        self.assertEqual(langfloor.resolve_runner_tag("./gradlew test", "."), ())

    def test_unknown_runner_is_empty(self):
        self.assertEqual(langfloor.resolve_runner_tag("tox", "."), ())

    def test_empty_cmd_is_empty(self):
        self.assertEqual(langfloor.resolve_runner_tag("", "."), ())
        self.assertEqual(langfloor.resolve_runner_tag("   ", "."), ())


class TestResolveRunnerTagWrapper(unittest.TestCase):
    """`make test` / `npm test` expand via the recipe / package.json (the only I/O)."""

    def test_make_test_recipe_unittest(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "Makefile", "test:\n\tpython3 -m unittest\n")
            self.assertEqual(
                langfloor.resolve_runner_tag("make test", d), ("unittest",)
            )

    def test_make_test_polyglot_recipe_is_ordered(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "Makefile", "test:\n\tpytest && go test ./...\n")
            self.assertEqual(
                langfloor.resolve_runner_tag("make test", d),
                ("pytest", "go test"),
            )

    def test_make_test_multiline_recipe_multiple_runners(self):
        with tempfile.TemporaryDirectory() as d:
            _write(
                Path(d),
                "Makefile",
                "test: deps\n\tpytest\n\tcargo test\n\nother:\n\techo hi\n",
            )
            self.assertEqual(
                langfloor.resolve_runner_tag("make test", d),
                ("pytest", "cargo test"),
            )

    def test_make_test_missing_makefile_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(langfloor.resolve_runner_tag("make test", d), ())

    def test_make_test_unrecognized_recipe_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "Makefile", "test:\n\ttox -e py312\n")
            self.assertEqual(langfloor.resolve_runner_tag("make test", d), ())

    def test_make_test_recipe_with_residual_gradle_is_unresolved(self):
        # COR-1 (cardinal sin): a recipe that runs `pytest` AND an uncountable
        # `./gradlew test` must NOT resolve to the recognized `('pytest',)` subset
        # — gradle's `|| true`-masked failure is invisible, so a green pytest would
        # fabricate a pass. The whole recipe is UNRESOLVED (() → UNVERIFIED).
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "Makefile", "test:\n\tpytest\n\t./gradlew test || true\n")
            self.assertEqual(langfloor.resolve_runner_tag("make test", d), ())

    def test_make_test_recipe_with_bare_gradle_is_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "Makefile", "test:\n\tpytest && gradle check\n")
            self.assertEqual(langfloor.resolve_runner_tag("make test", d), ())

    def test_make_test_recipe_with_dotnet_test_is_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "Makefile", "test:\n\tdotnet test\n")
            self.assertEqual(langfloor.resolve_runner_tag("make test", d), ())

    def test_npm_test_script_jest(self):
        with tempfile.TemporaryDirectory() as d:
            _write(
                Path(d),
                "package.json",
                '{"scripts": {"test": "jest --ci"}}\n',
            )
            self.assertEqual(langfloor.resolve_runner_tag("npm test", d), ("jest",))

    def test_npm_run_test_variant(self):
        with tempfile.TemporaryDirectory() as d:
            _write(
                Path(d),
                "package.json",
                '{"scripts": {"test": "vitest run"}}\n',
            )
            self.assertEqual(
                langfloor.resolve_runner_tag("npm run test", d), ("vitest",)
            )

    def test_npm_test_missing_package_json_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(langfloor.resolve_runner_tag("npm test", d), ())

    def test_npm_test_malformed_json_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "package.json", "{not valid json,,,")
            self.assertEqual(langfloor.resolve_runner_tag("npm test", d), ())

    def test_npm_test_no_test_script_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d), "package.json", '{"scripts": {"build": "tsc"}}\n')
            self.assertEqual(langfloor.resolve_runner_tag("npm test", d), ())


class TestSyntaxArgv(unittest.TestCase):
    """The ext→syntax-argv table (declared for P2; importable + non-exec here)."""

    def test_ruby_argv(self):
        self.assertEqual(langfloor.SYNTAX_ARGV[".rb"], ["ruby", "-cw"])

    def test_all_values_are_nonempty_argv_lists(self):
        self.assertTrue(langfloor.SYNTAX_ARGV)
        for ext, argv in langfloor.SYNTAX_ARGV.items():
            self.assertTrue(ext.startswith("."), ext)
            self.assertIsInstance(argv, list)
            self.assertTrue(argv)
            self.assertTrue(all(isinstance(tok, str) for tok in argv))

    def test_covers_the_documented_extensions(self):
        for ext in (".js", ".mjs", ".cjs", ".rb", ".php", ".go", ".sh"):
            self.assertIn(ext, langfloor.SYNTAX_ARGV)


class TestConfigAllowlist(unittest.TestCase):
    """The config allowlist of glob patterns (blueprint §9)."""

    def test_contains_the_named_config_files(self):
        for name in (
            "package.json",
            "tsconfig.json",
            "pyproject.toml",
            "Cargo.toml",
            "composer.json",
        ):
            self.assertIn(name, langfloor.CONFIG_ALLOWLIST)

    def test_lock_glob_present_and_matches_lockfiles(self):
        self.assertIn("*.lock", langfloor.CONFIG_ALLOWLIST)
        for lock in ("Cargo.lock", "poetry.lock", "yarn.lock"):
            self.assertTrue(
                any(fnmatch.fnmatch(lock, pat) for pat in langfloor.CONFIG_ALLOWLIST)
            )

    def test_is_a_frozenset(self):
        self.assertIsInstance(langfloor.CONFIG_ALLOWLIST, frozenset)


if __name__ == "__main__":
    unittest.main()
