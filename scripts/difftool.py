"""Deterministic diff capture — the single diff source for every lens.

The verification harness must review exactly one, reproducible diff. This module
captures ``git diff <baseline_sha> -- <scope_paths>`` (working tree vs. the frozen
baseline commit) with all environment-dependent formatting disabled, so the same
repository state always yields byte-identical output. A missing or invalid
baseline is handled gracefully (empty diff) rather than raising, so a lens never
crashes on a fresh or non-git tree.
"""
from __future__ import annotations

import subprocess


def _build_diff_argv(baseline_sha: str, scope_paths: list[str]) -> list[str]:
    """Build the deterministic ``git diff`` argv (pure, unit-testable).

    ``--no-pager``/``--no-color``/``--no-ext-diff`` strip all interactive and
    environment-dependent formatting so output is reproducible. When
    ``baseline_sha`` is falsy the diff is taken against the working tree only
    (unstaged changes). ``scope_paths`` (when non-empty) are passed as a
    pathspec after ``--`` so only in-scope changes appear.
    """
    argv = ["git", "--no-pager", "diff", "--no-color", "--no-ext-diff"]
    if baseline_sha and baseline_sha.strip():
        argv.append(baseline_sha.strip())
    if scope_paths:
        argv.append("--")
        argv.extend(scope_paths)
    return argv


def capture(baseline_sha: str, scope_paths: list[str], cwd: str) -> str:
    """Return the deterministic diff text for one run's in-scope changes.

    Runs ``git diff <baseline_sha> -- <scope_paths>`` in ``cwd``. Returns the
    diff as a string, or an empty string if git is unavailable, ``cwd`` is not a
    repository, or ``baseline_sha`` does not resolve (git exits with 128) — the
    harness treats "no capturable diff" as an empty diff, never an exception.
    """
    argv = _build_diff_argv(baseline_sha, scope_paths)
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return ""
    # git diff exits 0 normally; a bad revision / non-repo exits 128.
    if proc.returncode not in (0, 1):
        return ""
    return proc.stdout
