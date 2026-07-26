"""Build the frozen dogfood corpus the Phase 1 coverage experiment replays.

This module is a **capture tool**, not part of the review path. Nothing in
``skills/atlas/SKILL.md`` imports it, ``make ci`` never runs it, and it can
neither emit a defect nor influence a verdict. Its whole job is to move a
perishable measurement out of a session-scoped scratch directory and into
version control, with provenance attached, so the experiment can be re-run by
someone who was not there.

WHY CAPTURE IS FIRST (plan §7, "The ``full_paths`` freeze is one-way").
``floorsynth.out_of_scope_defects`` is fed ``difftool.change_paths(baseline_sha,
review_root)`` — the WHOLE-TREE changed-path list of the tree the coder actually
wrote in. That list cannot be recomputed once the run sandboxes are collected:
the durable archive at ``/root/atlas-dogfood-corpus-2026-07-26`` holds each
run's ``.git`` under a ``git-objects/`` name with NO working tree, so
``change_paths`` there returns ``[]`` for every item — "measured, nothing
outside scope", which is a fabricated zero, not a measurement. The only copy
that still answers is the session scratchpad, and it dies with the session.

THE SEC-2 GUARD, confirmed by execution, not by reading.
``difftool.change_paths`` assembles ``git diff --name-only -z --relative
<baseline>`` with **no ``--`` terminator** (``scripts/difftool.py``:283-286), so
a baseline beginning with ``-`` is parsed by git as an OPTION. Measured at HEAD:
``change_paths("--output=/tmp/probe/PWNED.txt", <a git tree>)`` returns ``[]``
**and creates ``/tmp/probe/PWNED.txt``**. The value is not hypothetical input:
``state.json`` lives inside the coder-writable ``.atlas/`` in interactive mode
and this very corpus already contains a free-text sha slot — ``after-t3-a``
records ``checkpoints.VERIFIED = "worktree-at-1343ecc+pass1-diff"``.
``scripts/difftool.py`` is on the runtime review path and Phase 1 is additive,
so it is NOT modified here; :func:`frozen_tree_paths` validates the sha against
``[0-9a-fA-F]{7,40}`` **before any git call** and records ``unmeasured`` on
failure. A capture tool that fixes this by editing the runtime module would
violate the phase's own constraint; a capture tool that skips the check would
hand an attacker-shaped string to git.

THE ARGUMENT-ORDER TRAP (plan TA-C1). ``difftool.git_tree_has_baseline(cwd,
baseline_sha)`` and ``difftool.change_paths(baseline_sha, cwd)`` take the same
two strings in **opposite** positional order, and both degrade silently: a swap
yields ``False``/``[]``, i.e. an unmeasured item that looks like a clean one.
The order is pinned by a test in ``tests/test_predcov.py`` rather than by
comment alone.

REVIEW-ROOT RESOLUTION, and a measured disagreement with the plan.
The review root is read from the run's own ``review_root`` file inside the
session directory — the value the run itself used for ``change_paths`` — and
NOT assumed to be ``<session>/worktree``. Measured over the 12 dogfood runs: 8
recorded a worktree path and **4 recorded ``"."``** (``after-t3-a``,
``after-t3-b``, ``before-t2-a``, ``before-t3-b``), which have no ``worktree``
directory at all. Resolving by the recorded value gives, over the 11 honest
items, **10 measured / 1 unmeasured** — the single unmeasured item is
``before-t1-a``, whose worktree is a linked git worktree whose ``.git`` file
points at ``runs/PILOT-before-t1``, a directory that no longer exists, so
``git_tree_has_baseline`` is False there. The plan's Task 1 expects "measured 7,
unmeasured 4"; that split is reproduced exactly by resolving the review root as
``<session>/worktree`` unconditionally, which mislabels the four in-place runs
as unreconstructible. Both numbers are recorded in the capture index
(``state`` and ``state_if_worktree_only``) so the disagreement is auditable
rather than argued.

WHAT THE CAPTURED PATHS ARE NOT. They are the changed-path list of each sandbox
**as it stands today**, not a snapshot taken at the moment the run ended. The
sandboxes have not been edited since (no commit, no checkout), but nothing
proves that from inside this tool, so ``item.json`` records the capture time and
the source path and the report never calls the list machine-attested.
``.atlas/`` was coder-writable during recording (SEC-4): every byte copied from
a session directory is model-influenced evidence.

CLI: ``python3 -m scripts.corpusbuild --capture`` writes the durable capture
index; it is human-invoked, never wired into ``make ci``, and returns non-zero
only when it captured nothing at all.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

from scripts import difftool

# A baseline sha is 7-40 hex characters and nothing else. Anything that could be
# read by git as an option, a path or a revision expression is refused (SEC-2).
_SHA = re.compile(r"[0-9a-fA-F]{7,40}")

# The only copy of the 2026-07-26 dogfood runs that still carries git objects AND
# a working tree. Session-scoped and ephemeral by construction — which is the
# entire reason this tool exists. Overridable with --runs.
DEFAULT_RUNS = (
    "/tmp/claude-0/-var-www-kimi-sub-kimi-atlas/"
    "7d80d815-419b-471c-ba00-772d792eb539/scratchpad/runs"
)

# Durable, outside the repository: the capture must survive the session that
# produced it even if the corpus build that follows is abandoned.
DEFAULT_CAPTURE = "/root/atlas-dogfood-corpus-2026-07-26/_capture"


def frozen_tree_paths(review_root: str, baseline_sha: str) -> tuple[list[str] | None, str]:
    """Return (paths, state). state is 'measured' | 'unmeasured'. NEVER raises, NEVER
    passes an unvalidated string to git (SEC-2: a baseline beginning with '-' is parsed
    as a git option and can write an arbitrary file -- confirmed by execution)."""
    if not _SHA.fullmatch(baseline_sha or ""):
        return None, "unmeasured:non-sha-baseline"
    if not os.path.isdir(review_root):
        return None, "unmeasured:worktree-absent"
    if not difftool.git_tree_has_baseline(review_root, baseline_sha):
        return None, "unmeasured:not-a-git-tree-with-baseline"
    return difftool.change_paths(baseline_sha, review_root), "measured"


# --------------------------------------------------------------------------
# Pure cores — text in, judgment out. No filesystem, no git, no exceptions.
# --------------------------------------------------------------------------
def rc_from_meta(meta_text: str) -> int | None:
    """The ``rc=`` line of a run's ``<label>.meta``, or None if unstated.

    None is NOT 0: a missing exit status must never be read as success, and the
    arm rule (:func:`arm_of`) is keyed on the recorded value.
    """
    for line in (meta_text or "").splitlines():
        if line.startswith("rc="):
            try:
                return int(line[3:].strip())
            except ValueError:
                return None
    return None


def last_stage(log_text: str) -> str:
    """The ``stage`` of the last parsable JSON record in a ``log.jsonl``.

    Trailing garbage (a run killed mid-write) is skipped from the end rather
    than raising, because the interrupted arm exists precisely to hold runs that
    died mid-write.
    """
    for line in reversed((log_text or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("stage"), str):
            return rec["stage"]
    return ""


def arm_of(rc: int | None, final_stage: str) -> str:
    """'honest' iff rc == 0 AND the ledger's last stage is OUTPUT, else 'interrupted'.

    Mechanical by design (plan §5.1): arm membership is decided by the recorded
    exit status and the ledger, never by a judgment call, and the counting arm is
    then a directory name — so widening the numerator requires a visible file
    move in a diff.
    """
    return "honest" if (rc == 0 and final_stage == "OUTPUT") else "interrupted"


# --------------------------------------------------------------------------
# Thin I/O hands.
# --------------------------------------------------------------------------
def _read(path: str) -> str:
    """File text, or '' when absent/unreadable. Never raises."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def session_dir(run_dir: str) -> str:
    """The single ``.atlas/session_*`` directory of a run sandbox, or ''.

    More than one session directory is ambiguous provenance, not a tie to break:
    '' is returned so the caller records the item as uncapturable.
    """
    atlas = os.path.join(run_dir, ".atlas")
    try:
        names = sorted(n for n in os.listdir(atlas) if n.startswith("session_"))
    except OSError:
        return ""
    if len(names) != 1:
        return ""
    return os.path.join(atlas, names[0])


def capture_run(runs_root: str, label: str) -> dict:
    """Capture one run: arm, provenance and the frozen whole-tree path list.

    Every failure mode degrades to a recorded state string; nothing raises, so a
    single broken sandbox cannot abort the capture of the other eleven.
    """
    run_dir = os.path.join(runs_root, label)
    sess = session_dir(run_dir)
    rec: dict = {
        "label": label,
        "source_run_dir": os.path.abspath(run_dir),
        "source_session_dir": os.path.abspath(sess) if sess else "",
    }
    if not sess:
        rec.update({"arm": "", "state": "unmeasured:no-session-dir", "paths": None})
        return rec

    rc = rc_from_meta(_read(os.path.join(runs_root, label + ".meta")))
    stage = last_stage(_read(os.path.join(sess, "log.jsonl")))
    try:
        state_json = json.loads(_read(os.path.join(sess, "state.json")) or "{}")
    except ValueError:
        state_json = {}
    if not isinstance(state_json, dict):
        state_json = {}

    recorded_root = _read(os.path.join(sess, "review_root")).strip()
    baseline = state_json.get("baseline_sha")
    baseline = baseline if isinstance(baseline, str) else ""
    scope = state_json.get("scope_paths")
    scope = [s for s in scope if isinstance(s, str)] if isinstance(scope, list) else []

    resolved = os.path.normpath(os.path.join(run_dir, recorded_root or "."))
    paths, state = frozen_tree_paths(resolved, baseline)
    # The plan's Task 1 expects the worktree-only resolution; recorded, not argued.
    _wt_paths, wt_state = frozen_tree_paths(os.path.join(sess, "worktree"), baseline)

    rec.update({
        "arm": arm_of(rc, stage),
        "rc": rc,
        "final_stage": stage,
        "run_id": state_json.get("run_id", ""),
        "baseline_sha": baseline,
        "scope_paths": scope,
        "recorded_review_root": recorded_root,
        "resolved_review_root": resolved,
        "state": state,
        "state_if_worktree_only": wt_state,
        "paths": paths,
    })
    return rec


def capture(runs_root: str, out_dir: str) -> dict:
    """Capture every run sandbox under ``runs_root`` into ``out_dir``.

    Writes ``<out_dir>/capture.json`` (the index) and, for each measured item,
    ``<out_dir>/<label>/tree.paths``. Returns the index.
    """
    try:
        labels = sorted(
            n for n in os.listdir(runs_root)
            if os.path.isdir(os.path.join(runs_root, n))
            and os.path.isdir(os.path.join(runs_root, n, ".atlas"))
        )
    except OSError:
        labels = []
    items = [capture_run(runs_root, label) for label in labels]
    index = {
        "schema": "predcov-capture/1",
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "capture_command": "python3 -m scripts.corpusbuild --capture --runs %s --out %s"
                           % (runs_root, out_dir),
        "runs_root": os.path.abspath(runs_root),
        "provenance_warning": ".atlas/ was coder-writable during recording; these "
                              "artifacts are model-influenced, not machine-attested.",
        "items": items,
    }
    os.makedirs(out_dir, exist_ok=True)
    for rec in items:
        if rec.get("paths") is None:
            continue
        item_dir = os.path.join(out_dir, rec["label"])
        os.makedirs(item_dir, exist_ok=True)
        with open(os.path.join(item_dir, "tree.paths"), "w", encoding="utf-8") as fh:
            fh.write("".join(p + "\n" for p in rec["paths"]))
    with open(os.path.join(out_dir, "capture.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return index


def _summarize(index: dict) -> str:
    """The human line: the honest-arm measured/unmeasured split, plus per item."""
    items = index.get("items") or []
    honest = [r for r in items if r.get("arm") == "honest"]
    measured = [r for r in honest if r.get("state") == "measured"]
    unmeasured = [r for r in honest if r.get("state") != "measured"]
    lines = [
        "corpus capture: %d run(s), %d honest, %d interrupted"
        % (len(items), len(honest), len(items) - len(honest)),
        "honest arm: measured %d, unmeasured %d"
        % (len(measured), len(unmeasured)),
    ]
    for rec in items:
        lines.append(
            "  %-13s %-11s %-40s %s"
            % (rec.get("label", "?"), rec.get("arm", "?"), rec.get("state", "?"),
               "paths=%d" % len(rec["paths"]) if rec.get("paths") is not None else "paths=-")
        )
    if unmeasured:
        lines.append("unmeasured honest items: %s"
                     % ", ".join(sorted(r["label"] for r in unmeasured)))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI: capture the perishable dogfood run data. Never wired into ``make ci``."""
    parser = argparse.ArgumentParser(
        description="Capture the atlas dogfood runs for the Phase 1 coverage corpus."
    )
    parser.add_argument("--capture", action="store_true",
                        help="Capture whole-tree change paths + provenance.")
    parser.add_argument("--runs", default=DEFAULT_RUNS,
                        help="Directory holding the run sandboxes (default: %(default)s).")
    parser.add_argument("--out", default=DEFAULT_CAPTURE,
                        help="Where to write the capture index (default: %(default)s).")
    args = parser.parse_args(argv)

    if not args.capture:
        parser.print_help()
        return 0

    index = capture(args.runs, args.out)
    print(_summarize(index))
    print("capture index: %s" % os.path.join(args.out, "capture.json"))
    if not index["items"]:
        print("NOTHING CAPTURED: no run sandboxes under %s" % args.runs, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
