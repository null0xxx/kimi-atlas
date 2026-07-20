"""Two-phase, forward-only rollback driver — the impure git seam under ctxstore's pure ledger.

``ctxstore`` stays pure-persistence (no subprocess); the actual ``git reset --hard`` lives
HERE, behind a monkeypatchable seam (mirroring ``sast.scan`` / ``difftool._run``). The driver
orchestrates the blueprint's two-phase, idempotent, forward-only rollback:

    ctxstore.rollback_to(..., "rollback_intent")   # record target BEFORE touching the tree
    _git_reset(target_sha, cwd)                     # idempotent hard reset (the seam)
    ctxstore.rollback_to(..., "rollback_complete")  # record success AFTER

A crash between steps leaves a ``rollback_intent`` with no ``rollback_complete``; ``resume``
re-derives that from the ledger (``ctxstore.pending_rollback``) and REDOES the reset —
resetting to an already-reset SHA is a no-op, so it is safe to repeat.

Guard: the mechanism is HEADLESS-WORKTREE-ONLY and refuses unless
``sanctioned_rollback(target, git_common_dir, git_dir, env_token)`` holds — the reset target
must resolve inside an isolated ``.atlas/<run_id>/worktree`` (a real linked worktree ⇒
``git_common_dir != git_dir``) AND a caller-set sanction env token must be present. Interactive
real-tree rollback NEVER auto-resets: the residual is surfaced to the human at the OUTPUT gate
(SKILL prose). The driver refuses (non-zero) whenever the predicate is False.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

# Plugin root on sys.path so ``from scripts import ctxstore`` resolves whether this is run as
# ``python3 -m scripts.rollback_driver``, imported, or invoked as ``scripts/rollback_driver.py``.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import ctxstore  # noqa: E402  (path shim must precede this import)

# The env var a sanctioned caller sets to authorize a headless rollback reset.
SANCTION_ENV = "ATLAS_SANCTIONED_ROLLBACK"

# Path markers of an isolated headless worktree (SKILL: .atlas/<run_id>/worktree).
_ISOLATION_DIR = ".atlas"
_WORKTREE_LEAF = "worktree"


def sanctioned_rollback(
    target: str, git_common_dir: str, git_dir: str, env_token: str | None
) -> bool:
    """Pure predicate: may this rollback reset proceed? (no I/O, no subprocess).

    Returns ``True`` only when ALL hold:

    * ``target`` resolves inside an isolated headless worktree — its normalized path has a
      ``.atlas`` segment AND a ``worktree`` segment (``.atlas/<run_id>/worktree``);
    * ``git_common_dir != git_dir`` — the signature of a real *linked* git worktree (in the
      main working tree the two are equal), so the reset can never land on the primary tree;
    * ``env_token`` is a non-empty caller-set token (the sanctioned-rollback authorization).

    Any missing/empty signal ⇒ ``False`` (refuse). Enforceable purely from paths + env — the
    only signals that actually exist — so it needs neither ``guard-destructive.sh`` nor a live
    git call.
    """
    if not target or not env_token or not str(env_token).strip():
        return False
    if not git_common_dir or not git_dir or git_common_dir == git_dir:
        return False
    parts = pathlib.PurePath(os.path.normpath(target)).parts
    return _ISOLATION_DIR in parts and _WORKTREE_LEAF in parts


def _git_reset(target_sha: str, cwd: str) -> tuple[str, int]:
    """The monkeypatchable git-reset seam: ``git reset --hard <target_sha>`` in ``cwd``.

    Returns ``(combined_output, returncode)``; a missing git binary / OS error maps to
    returncode 127. Tests replace this attribute wholesale (like ``sast.semgrep_path``), so the
    driver's control flow is exercised without a real repository. The ONLY subprocess in the
    rollback path — ctxstore never shells out.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "reset", "--hard", target_sha],
            capture_output=True, text=True, check=False,
        )
    except (FileNotFoundError, OSError):
        return "", 127
    return (proc.stdout or "") + (proc.stderr or ""), proc.returncode


def _git_dirs(cwd: str) -> tuple[str, str]:
    """Resolve ``(git_common_dir, git_dir)`` for ``cwd`` (empty strings on any failure)."""
    def _one(flag: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "-C", cwd, "rev-parse", flag],
                capture_output=True, text=True, check=False,
            )
        except (FileNotFoundError, OSError):
            return ""
        return proc.stdout.strip() if proc.returncode == 0 else ""
    return _one("--git-common-dir"), _one("--git-dir")


def run_rollback(
    base: str, run_id: str, cwd: str, target_sha: str, target_stage: str,
    git_common_dir: str, git_dir: str, env_token: str | None,
) -> int:
    """Execute one sanctioned two-phase rollback; 0 on success, non-zero on refusal/failure.

    Refuses (returns 2, NO ledger write, NO reset) whenever ``sanctioned_rollback(...)`` is
    False. Otherwise records ``rollback_intent`` BEFORE touching the tree, runs the idempotent
    ``_git_reset`` seam, then records ``rollback_complete``. A non-zero reset returncode aborts
    BEFORE the completion marker (returns 3), leaving a recoverable ``rollback_intent`` for
    ``resume_rollback``.
    """
    if not sanctioned_rollback(cwd, git_common_dir, git_dir, env_token):
        sys.stderr.write("rollback refused: not a sanctioned isolated worktree / missing token\n")
        return 2
    ctxstore.rollback_to(base, run_id, target_sha, target_stage, "rollback_intent")
    _, rc = _git_reset(target_sha, cwd)
    if rc != 0:
        sys.stderr.write(f"rollback reset failed (rc={rc}); intent recorded for resume\n")
        return 3
    ctxstore.rollback_to(base, run_id, target_sha, target_stage, "rollback_complete")
    return 0


def resume_rollback(base: str, run_id: str, cwd: str) -> int:
    """Redo an interrupted rollback (``rollback_intent`` w/o ``rollback_complete``); idempotent.

    Reads ``ctxstore.pending_rollback`` (ledger-derived, not the possibly-torn state.json). No
    pending intent ⇒ nothing to do (returns 0). Otherwise REDO the idempotent ``_git_reset`` to
    the recorded SHA and record ``rollback_complete``. Resetting to an already-reset SHA is a
    no-op, so repeated resumes are safe. A failed reset leaves the intent open (returns 3) for
    the next resume.
    """
    pending = ctxstore.pending_rollback(base, run_id)
    if not pending:
        return 0
    target_sha = pending.get("target_sha", "")
    target_stage = pending.get("target_stage", "")
    _, rc = _git_reset(target_sha, cwd)
    if rc != 0:
        sys.stderr.write(f"rollback resume reset failed (rc={rc}); intent left open\n")
        return 3
    ctxstore.rollback_to(base, run_id, target_sha, target_stage, "rollback_complete")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI: run or resume a headless-worktree rollback.

    ``--base --run-id --cwd [--target-sha --target-stage]`` runs a fresh rollback (resolving
    ``(git_common_dir, git_dir)`` from ``--cwd`` and the sanction token from
    ``ATLAS_SANCTIONED_ROLLBACK``); ``--resume`` redoes an interrupted one. Returns the driver
    exit code (0 = done, non-zero = refused/failed).
    """
    import argparse

    args = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="rollback_driver")
    ap.add_argument("--base", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--target-sha", default="")
    ap.add_argument("--target-stage", default="VERIFIED")
    ap.add_argument("--resume", action="store_true")
    ns = ap.parse_args(args)
    if ns.resume:
        return resume_rollback(ns.base, ns.run_id, ns.cwd)
    common, gdir = _git_dirs(ns.cwd)
    return run_rollback(
        ns.base, ns.run_id, ns.cwd, ns.target_sha, ns.target_stage,
        common, gdir, os.environ.get(SANCTION_ENV),
    )


if __name__ == "__main__":
    sys.exit(main())
