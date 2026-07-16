"""Union git-apply-on-worktree — the ATLAS-WEAVE INTEGRATE hand (I/O boundary).

This is a "hand", not a pure core: it actually creates an isolated git worktree at
the baseline sha, `git apply`s the union of node diffs onto it in list order, and
captures the combined diff. It is the THIRD disjointness net (per §5) behind the
planner's declared `scope_paths` and `integrate.actual_conflicts` — a real `git
apply` will reject a hidden same-file overlap that slipped both earlier gates.

Fail-safe discipline (mirrors the pure cores' degrade-toward-BLOCK rule): every
subprocess/git failure degrades toward failure, NEVER a false green. A failed
`worktree add` yields `worktree=None` with every change recorded as `failed`; a
change whose `git apply` exits non-zero is recorded in `failed` (never silently
counted as applied). Uses `subprocess` with `git -C <path>` — NO reliance on the
process cwd (agent threads reset cwd between calls).
"""
from __future__ import annotations

import os
import subprocess


def _run(cwd, args, stdin=None):
    """Run `git -C cwd <args>`; return (returncode, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, ValueError) as exc:  # git missing, bad args, encoding, etc.
        return 1, "", str(exc)


def _worktree_path(repo_cwd: str, session: str) -> str:
    return os.path.join(repo_cwd, ".atlas", session, "union-worktree")


def apply_union(baseline_sha: str, changes: list, repo_cwd: str, session: str) -> dict:
    """Apply the union of node diffs onto an isolated worktree at `baseline_sha`.

    ``changes`` = ``[{"id", "diff"}]``. Creates a **detached** worktree at
    ``baseline_sha`` (``git worktree add --detach`` — NO branch ref, so nothing is left
    in ``.git/refs`` and a second run with the same ``session`` cannot collide with a
    leftover branch; the union tree only needs to apply+diff+test, never to commit)
    under ``.atlas/{session}/union-worktree``, then ``git apply``s each change's diff in
    list order. A change whose apply exits non-zero is recorded in ``failed`` as
    ``{"id", "reason"}`` (the hidden-overlap net); ``applied`` lists the ids that
    applied clean.

    Returns ``{"worktree", "applied", "failed", "combined_diff"}``. All git failures
    degrade safe: a failed ``worktree add`` yields ``worktree=None`` with every change
    ``failed`` and an empty ``combined_diff``.
    """
    changes = list(changes or [])
    path = _worktree_path(repo_cwd, session)

    # Ensure the parent dir exists; git worktree add creates the leaf itself.
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        pass

    rc, _out, err = _run(
        repo_cwd, ["worktree", "add", "--detach", path, baseline_sha]
    )
    if rc != 0:
        reason = (err or "worktree add failed").strip()
        return {
            "worktree": None,
            "applied": [],
            "failed": [
                {"id": ch.get("id"), "reason": reason} for ch in changes
            ],
            "combined_diff": "",
        }

    applied: list = []
    failed: list = []
    for ch in changes:
        cid = ch.get("id")
        diff = ch.get("diff", "") or ""
        rc, _o, err = _run(path, ["apply", "--whitespace=nowarn", "-"], stdin=diff)
        if rc == 0:
            applied.append(cid)
        else:
            failed.append({"id": cid, "reason": (err or "git apply failed").strip()})

    # Stage everything (so newly-created files show up in the combined diff), then
    # diff the worktree against the baseline sha. A diff failure degrades to "".
    _run(path, ["add", "-A"])
    rc, out, _err = _run(path, ["diff", baseline_sha])
    combined_diff = out if rc == 0 else ""

    return {
        "worktree": path,
        "applied": applied,
        "failed": failed,
        "combined_diff": combined_diff,
    }


def cleanup(worktree, repo_cwd: str, session: str) -> None:
    """Remove the union worktree + prune stale registrations. Never raises.

    A detached worktree leaves no branch ref, so removing it (``git worktree remove
    --force``) plus a ``prune`` returns the repo to its exact prior state — the union
    machinery is fully idempotent across re-runs with the same ``session``.
    """
    if not worktree:
        return
    _run(repo_cwd, ["worktree", "remove", "--force", worktree])
    _run(repo_cwd, ["worktree", "prune"])
