"""scripts/install.sh must keep one rolling backup, not unbounded timestamped
snapshots (F11).

Two layers of coverage:

1. Static-source guards (fast, environment-independent): the installer no longer
   mints a `.bak.$(date ...)` timestamp and instead writes a single rolling
   `"$INSTALLED.bak"` at both the install and uninstall sites.

2. A real end-to-end behavioral drive: run the actual installer twice against a
   throwaway ``KIMI_CODE_HOME`` tempdir (never the user's real ``~/.kimi-code``)
   and assert that after TWO installs there is exactly ONE ``installed.json.bak``
   holding the PREVIOUS ``installed.json`` content -- not a pile of timestamped
   files.
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_INSTALL = _ROOT / "scripts" / "install.sh"


class TestInstallBackupSource(unittest.TestCase):
    """Static-source guards straight from the F11 brief."""

    def setUp(self):
        self.text = _INSTALL.read_text(encoding="utf-8")

    def test_no_timestamped_backup(self):
        self.assertNotIn(".bak.$(date", self.text)

    def test_uses_single_rolling_backup(self):
        # Both the install and uninstall paths back up to the same rolling file.
        self.assertEqual(self.text.count('"$INSTALLED.bak"'), 2)


@unittest.skipUnless(
    shutil.which("git") and shutil.which("python3") and shutil.which("tar"),
    "requires git, python3, and tar to drive the installer end-to-end",
)
class TestInstallBackupBehavior(unittest.TestCase):
    """Drive the real installer twice and prove the rolling-backup behavior."""

    def _run_install(self, kimi_home):
        env = dict(os.environ, KIMI_CODE_HOME=str(kimi_home))
        # Force a deterministic, non-interactive git identity is not needed here
        # (install only *reads* HEAD via `git archive`), but keep the env clean.
        proc = subprocess.run(
            ["sh", str(_INSTALL)],
            env=env,
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"installer failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        return proc

    def test_two_installs_keep_one_rolling_backup_of_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            kimi_home = pathlib.Path(tmp) / "kimi-code"
            plugins = kimi_home / "plugins"
            plugins.mkdir(parents=True)

            # Fake Kimi install so install.sh's `-x bin/kimi` gate passes.
            bin_dir = kimi_home / "bin"
            bin_dir.mkdir()
            kimi_bin = bin_dir / "kimi"
            kimi_bin.write_text("#!/bin/sh\nexit 0\n")
            kimi_bin.chmod(0o755)

            installed = plugins / "installed.json"
            rolling_bak = plugins / "installed.json.bak"

            # Seed a pre-existing registry so the first install has something to
            # back up, and tag it so we can recognize it later.
            installed.write_text(
                json.dumps({"version": 1, "plugins": [], "_seed": "initial"}) + "\n"
            )

            # --- install #1 -------------------------------------------------
            self._run_install(kimi_home)
            self.assertTrue(rolling_bak.exists(), "first install should create the backup")
            self.assertEqual(
                json.loads(rolling_bak.read_text()).get("_seed"),
                "initial",
                "backup after install #1 must hold the seeded (previous) content",
            )

            # Tag the live registry so we can prove the backup rolls to *this*
            # (previous) content after the second install.
            live = json.loads(installed.read_text())
            live["_marker"] = "before-second-install"
            installed.write_text(json.dumps(live, indent=2) + "\n")

            # --- install #2 -------------------------------------------------
            self._run_install(kimi_home)

            # Exactly ONE backup file, named `installed.json.bak` -- no
            # accumulation of timestamped `installed.json.bak.<ts>` snapshots.
            baks = sorted(p.name for p in plugins.glob("installed.json.bak*"))
            self.assertEqual(
                baks,
                ["installed.json.bak"],
                msg=f"expected a single rolling backup, found: {baks}",
            )

            # The rolling backup holds the PREVIOUS registry (the marked one),
            # proving it was overwritten in place rather than left stale.
            backup = json.loads(rolling_bak.read_text())
            self.assertEqual(backup.get("_marker"), "before-second-install")


if __name__ == "__main__":
    unittest.main()
