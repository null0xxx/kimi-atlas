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
