"""Behavioral test for the `make check-shell` gate (F1): it must FAIL on a
syntax-broken shell script, and it must cover scripts/*.sh."""
import os
import pathlib
import subprocess
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MAKEFILE = _ROOT / "Makefile"


def _check_shell_command() -> str:
    """Return the real `check-shell` recipe as a runnable /bin/sh command line."""
    lines = _MAKEFILE.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("check-shell:"):
            recipe = lines[i + 1]
            break
    else:  # pragma: no cover
        raise AssertionError("no check-shell target in Makefile")
    recipe = recipe.lstrip("\t")
    if recipe.startswith("@"):
        recipe = recipe[1:]
    return recipe.replace("$$", "$")  # make-escaped $$ -> shell $


class TestCheckShellGate(unittest.TestCase):
    def setUp(self):
        self.cmd = _check_shell_command()

    def _run_in(self, tmp: str) -> int:
        return subprocess.run(
            ["sh", "-c", self.cmd], cwd=tmp, capture_output=True
        ).returncode

    def test_broken_script_makes_gate_fail(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "scripts"))
            with open(os.path.join(tmp, "scripts", "bad.sh"), "w") as f:
                f.write("if [\n")  # unterminated test -> sh -n exit 2
            self.assertNotEqual(self._run_in(tmp), 0)

    def test_valid_scripts_pass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "scripts"))
            with open(os.path.join(tmp, "scripts", "good.sh"), "w") as f:
                f.write("echo ok\n")
            self.assertEqual(self._run_in(tmp), 0)

    def test_recipe_covers_scripts_glob(self):
        self.assertIn("scripts/*.sh", self.cmd)
        self.assertNotIn("|| true", self.cmd)


if __name__ == "__main__":
    unittest.main()
