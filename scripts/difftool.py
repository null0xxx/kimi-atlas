"""Deterministic diff capture — the single diff source for every lens.

The verification harness must review exactly one, reproducible diff of the
change under review. This module produces it deterministically and, crucially,
**shows brand-new files** — the most common coder output — which a plain
``git diff <baseline> -- <paths>`` omits entirely (untracked files never appear
in a tracked diff) and which, with an empty baseline in a non-git tree, git
would even mis-render as a bogus pairwise ``a/x -> b/y`` rename.

Strategy (per scope path, so multiple paths can never be compared against each
other):

* **git repo, tracked at the baseline** -> ``git diff <baseline> -- <path>``
  (real modification / deletion, restricted to scope).
* **git repo, untracked (new) in scope** -> discovered via
  ``git ls-files --others`` and rendered as a full new-file diff.
* **non-git tree** -> each in-scope file rendered as a full new-file diff via
  ``git diff --no-index /dev/null <file>`` (directories are walked).

All formatting is pinned (``--no-color``/``--no-ext-diff``/``--no-pager``) so the
same tree state always yields byte-identical output, and every failure mode
(no git, non-repo, unresolved baseline, missing file) degrades to "no diff",
never an exception. The working tree and index are never mutated.
"""
from __future__ import annotations

import os
import subprocess


def _run(argv: list[str], cwd: str) -> tuple[str, int]:
    """Run ``git <argv>`` in ``cwd``; return ``(stdout, returncode)``, never raising.

    ``--no-pager`` is prepended so output is never swallowed by a pager. On a
    missing git binary or OS error the return code is a sentinel (127) so callers
    uniformly treat it as "no diff".
    """
    try:
        proc = subprocess.run(
            ["git", "--no-pager", *argv],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return "", 127
    return proc.stdout, proc.returncode


def _is_git_repo(cwd: str) -> bool:
    """True iff ``cwd`` is inside a git working tree."""
    out, rc = _run(["rev-parse", "--is-inside-work-tree"], cwd)
    return rc == 0 and out.strip() == "true"


def _tracked_at(cwd: str, baseline: str, path: str) -> bool:
    """True iff ``path`` exists (as a blob or tree) in the ``baseline`` commit."""
    _, rc = _run(["cat-file", "-e", f"{baseline}:{path}"], cwd)
    return rc == 0


def _tracked_diff(cwd: str, baseline: str, path: str) -> str:
    """Diff a baseline-tracked ``path`` against the working tree (scope-restricted)."""
    out, rc = _run(["diff", "--no-color", "--no-ext-diff", baseline, "--", path], cwd)
    return out if rc in (0, 1) else ""


def _new_file_diff(cwd: str, rel_path: str) -> str:
    """Full new-file diff for a path that exists on disk (works in or out of a repo).

    ``git diff --no-index /dev/null <file>`` renders the entire file as added
    lines; it exits 1 when the files differ (i.e. there is content) and 0 when
    identical, so both are "real output".
    """
    out, rc = _run(
        ["diff", "--no-color", "--no-ext-diff", "--no-index", "/dev/null", rel_path], cwd
    )
    return out if rc in (0, 1) else ""


def _untracked_in_scope(cwd: str, scope_paths: list[str]) -> list[str]:
    """New (untracked, non-ignored) files within scope, per ``git ls-files --others``."""
    argv = ["ls-files", "--others", "--exclude-standard", "--", *scope_paths]
    out, rc = _run(argv, cwd)
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _walk_scope_files(cwd: str, scope_paths: list[str]) -> list[str]:
    """Existing files under ``scope_paths`` (files as-is, directories walked), cwd-relative."""
    files: list[str] = []
    for path in scope_paths:
        full = os.path.join(cwd, path)
        if os.path.isfile(full):
            files.append(path)
        elif os.path.isdir(full):
            for root, _dirs, names in os.walk(full):
                for name in sorted(names):
                    files.append(os.path.relpath(os.path.join(root, name), cwd))
    return files


def _join(parts: list[str]) -> str:
    """Concatenate non-empty diff fragments, each newline-terminated, in order."""
    out = []
    for text in parts:
        if text.strip():
            out.append(text if text.endswith("\n") else text + "\n")
    return "".join(out)


def capture(baseline_sha: str, scope_paths: list[str], cwd: str) -> str:
    """Return the deterministic diff text for one run's in-scope changes.

    Handles modified tracked files, brand-new (untracked) files, and non-git
    trees uniformly, and never mutates the working tree or index. Returns an
    empty string when there is nothing to show.
    """
    baseline = baseline_sha.strip() if baseline_sha else ""
    parts: list[str] = []

    if _is_git_repo(cwd):
        # 1. Tracked changes vs the baseline (scope-restricted). Passing multiple
        #    paths after `--` inside a repo is safe (no pairwise --no-index).
        if baseline:
            for path in scope_paths:
                if _tracked_at(cwd, baseline, path):
                    parts.append(_tracked_diff(cwd, baseline, path))
        else:
            # No baseline: fall back to working-tree-vs-index for tracked files.
            out, rc = _run(
                ["diff", "--no-color", "--no-ext-diff", "--", *scope_paths], cwd
            )
            if rc in (0, 1):
                parts.append(out)
        # 2. New (untracked) files in scope -> full new-file diffs (else invisible).
        for rel in _untracked_in_scope(cwd, scope_paths):
            parts.append(_new_file_diff(cwd, rel))
    else:
        # Non-git tree: render each in-scope file as a new-file diff. Never pass
        # two paths to one `git diff`, which would mis-render them as a rename.
        for rel in _walk_scope_files(cwd, scope_paths):
            parts.append(_new_file_diff(cwd, rel))

    return _join(parts)
