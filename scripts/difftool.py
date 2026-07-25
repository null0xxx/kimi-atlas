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

Pathspec contract (v1.5.2): ``.``, ``""`` and ``./`` — and any spec reducing to
them after stripping one leading ``./`` and trailing ``/`` — mean THE WHOLE
TREE and are normalized away before reaching git: ``cat-file`` rejects
``<rev>:.`` ("path '.' exists on disk, but not in ...") and ``diff`` /
``ls-files`` are BOTH fatal on the empty-string pathspec, so an un-normalized
whole-tree scope silently hid every tracked modification (and, for ``""``,
even the new files). Concrete paths are probed as ``<rev>:./<path>``, which
resolves CWD-relative — a deliberate change from ``<rev>:<path>``, which
resolves ROOT-relative and silently lost every tracked modification when a run
was launched from a monorepo subdirectory.

Two companion entry points serve the integration layer:

* :func:`capture_full` — the whole-tree evidence capture (``capture`` with a
  whole-tree scope), named so call sites read as intent.
* :func:`change_paths` — the machine-derived list of changed paths. Consumers
  must NEVER parse patch TEXT for paths: patch text is content-spoofable (a
  file whose added content contains a line like ``++ b/evil.py`` fools
  ``+++``-regex extraction, and a pure rename emits no ``+++`` lines at all).
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


def _normalize_pathspec(path: str) -> str:
    """Reduce a scope pathspec: strip ONE leading ``./`` and any trailing ``/``."""
    stripped = path[2:] if path.startswith("./") else path
    return stripped.rstrip("/")


def _is_whole_tree(path: str) -> bool:
    """True iff ``path`` names the whole tree: ``.``, ``""``, ``./`` or an equivalent."""
    return _normalize_pathspec(path) in ("", ".")


def _concrete_pathspecs(scope_paths: list[str]) -> list[str]:
    """Normalized scope paths with whole-tree specs dropped (those mean "no
    restriction" and must become the ABSENCE of a ``--`` pathspec, since git
    rejects ``""`` and ``cat-file`` rejects ``.``)."""
    return [p for p in (_normalize_pathspec(path) for path in scope_paths)
            if p not in ("", ".")]


def _tracked_at(cwd: str, baseline: str, path: str) -> bool:
    """True iff ``path`` exists (as a blob or tree) in the ``baseline`` commit.

    A whole-tree ``path`` probes ``<baseline>:`` — ``<baseline>:.`` is fatal
    ("path '.' exists on disk, but not in ..."). A concrete path probes
    ``<baseline>:./<path>``, which resolves CWD-relative from BOTH the repo
    root and any subdirectory; the old ``<baseline>:<path>`` form resolves
    ROOT-relative, so a run launched from a monorepo subdirectory silently
    lost every tracked modification. That is a deliberate behavior change.
    """
    if _is_whole_tree(path):
        _, rc = _run(["cat-file", "-e", f"{baseline}:"], cwd)
    else:
        _, rc = _run(
            ["cat-file", "-e", f"{baseline}:./{_normalize_pathspec(path)}"], cwd
        )
    return rc == 0


def _tracked_diff(cwd: str, baseline: str, path: str) -> str:
    """Diff a baseline-tracked ``path`` against the working tree (scope-restricted).

    A whole-tree ``path`` diffs via ``-- .``: the empty-string pathspec is fatal
    ("please use . instead"), and a bare no-pathspec ``git diff`` is REPO-wide
    even from a subdirectory — which would leak sibling-tree changes into a
    subdir ``review_root`` while the untracked channel and ``change_paths``
    (``--relative``) stay cwd-scoped. ``-- .`` is byte-identical to no pathspec
    from the repo root and cwd-scoped from a subdirectory, so every channel
    agrees on the same review_root-relative tree.
    """
    if _is_whole_tree(path):
        argv = ["diff", "--no-color", "--no-ext-diff", baseline, "--", "."]
    else:
        argv = ["diff", "--no-color", "--no-ext-diff", baseline, "--", path]
    out, rc = _run(argv, cwd)
    return out if rc in (0, 1) else ""


def _new_file_diff(cwd: str, rel_path: str) -> str:
    """Full new-file diff for a path that exists on disk (works in or out of a repo).

    ``git diff --no-index /dev/null <file>`` renders the entire file as added
    lines; it exits 1 when the files differ (i.e. there is content) and 0 when
    identical, so both are "real output". ``--`` precedes the path so a file
    named like a flag (``-foo.py``) is not parsed as an option — without it git
    exits 129 and the file is silently dropped from the evidence channel.
    """
    out, rc = _run(
        ["diff", "--no-color", "--no-ext-diff", "--no-index", "/dev/null", "--", rel_path],
        cwd,
    )
    return out if rc in (0, 1) else ""


def _untracked_in_scope(cwd: str, scope_paths: list[str]) -> list[str]:
    """New (untracked, non-ignored) files within scope, per ``git ls-files --others``.

    Whole-tree specs are dropped from the list; if nothing remains the command
    runs with NO ``--`` pathspec (an empty-string pathspec is fatal).
    """
    concrete = _concrete_pathspecs(scope_paths)
    argv = ["ls-files", "--others", "--exclude-standard"]
    if concrete:
        argv += ["--", *concrete]
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
            # Whole-tree specs become ``-- .`` (the empty-string pathspec is
            # fatal, and a bare no-pathspec diff is repo-wide from a subdir —
            # see _tracked_diff), keeping every channel review_root-relative.
            concrete = _concrete_pathspecs(scope_paths)
            argv = ["diff", "--no-color", "--no-ext-diff"]
            if concrete:
                argv += ["--", *concrete]
            else:
                argv += ["--", "."]
            out, rc = _run(argv, cwd)
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


def capture_full(baseline_sha: str, cwd: str) -> str:
    """Whole-tree evidence capture: every tracked change vs the baseline plus
    every new (untracked) file — exactly ``capture(baseline_sha, ["."], cwd)``.

    A thin wrapper so call sites that want the whole tree read as intent
    instead of passing a magic scope string.
    """
    return capture(baseline_sha, ["."], cwd)


def change_paths(baseline_sha: str, cwd: str) -> list[str]:
    """Machine-derived list of paths changed vs the baseline, review_root-relative.

    The path-list companion to :func:`capture_full`: ``git diff --name-only -z
    --relative <baseline>`` (tracked changes; an empty baseline falls back to
    worktree-vs-index, mirroring :func:`capture`'s no-baseline branch) UNION
    ``git ls-files --others --exclude-standard -z`` (new files), deduplicated
    and sorted deterministically. Both channels are NUL-separated so filenames
    containing newlines parse correctly, and ``--relative`` keeps the diff
    channel CWD-relative like ``ls-files`` — so both lists are
    review_root-relative. A rename yields one entry, the new path.

    Consumers must NEVER parse patch TEXT for paths instead: patch text is
    content-spoofable (a file whose added content contains a line like
    ``++ b/evil.py`` fools ``+++``-regex extraction) and a pure rename emits no
    ``+++`` lines at all.

    Pure of side effects; never raises — a non-git tree or any git failure
    degrades to ``[]`` (same discipline as :func:`_run`).
    """
    if not _is_git_repo(cwd):
        return []
    baseline = baseline_sha.strip() if baseline_sha else ""
    paths: set[str] = set()
    argv = ["diff", "--name-only", "-z", "--relative"]
    if baseline:
        argv.append(baseline)
    out, rc = _run(argv, cwd)
    if rc in (0, 1):
        paths.update(field for field in out.split("\0") if field)
    out, rc = _run(["ls-files", "--others", "--exclude-standard", "-z"], cwd)
    if rc == 0:
        paths.update(field for field in out.split("\0") if field)
    return sorted(paths)
