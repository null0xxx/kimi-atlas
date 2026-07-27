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

THE FOUR ARMS (plan §5.1), and why the corpus holds no ``.md`` and no ``.py``.
``tests/corpus/`` is NOT in ``inventory_drift.FUTURE_DIRS`` (which lists
``agents``, ``probe``, ``tests/fixtures``, ``skills/atlas-resume``), so
``inventory_drift.is_tracked_doc("tests/corpus/x.md")`` is **True** — verified —
and a single copied ``.md`` would turn ``make inventory-drift`` red and move the
tracked-doc count that ``tests/test_tracked_docs_count.py`` pins against
``AGENTS.md``. ``plan.md`` and the run worktrees are therefore excluded, which
costs nothing: no predicate reads them. A ``.py`` would be discovered by
``unittest discover -s tests``, and no path may contain an ``.atlas`` segment
(``.gitignore`` line 6) or the file would be silently untracked.

  honest/<label>/       11 recorded runs, rc=0 and a ledger ending at OUTPUT
  interrupted/<label>/   1 run (``after-t3-a``, rc=143, ledger ends at REFINE)
  historical/<b>..<t>/   4 release intervals, derived from THIS repo's own tags
  dirty/changelog-50-57/ 1 documented honest-dirty-tree shape

TWO LEDGERS PER RECORDED RUN, and the truncation rule (M2). ``log.jsonl`` is the
byte copy; ``log.eval.jsonl`` is derived by dropping the TRAILING ``OUTPUT``
records, because ``floorsynth.stale_verdict_defects`` is called by the SKILL's
OUTPUT block *before* that block's own ``advance(..., "OUTPUT")`` — its own
docstring tells fixture authors to truncate exactly there, since an
OUTPUT-terminated fixture makes the H6 trailing-shape condition unfirable.
Caveat, recorded rather than coded: a final ``OUTPUT`` record carrying
``cancelled=True`` marks the sanctioned pre-CODE cancel that
``stale_verdict_defects`` skips outright, and dropping it would change that
shape. Measured across all 12 ledgers: **zero** ``cancelled`` records, so no
branch is written for a case this corpus does not contain.

WHAT THE HISTORICAL ARM STORES, and what it does not. Its source is this
repository's own tags, which are durable and re-derivable by anyone — unlike the
run sandboxes — so the arm stores the machine-derived changed-path list, a
``--numstat`` summary (machine-readable and terminal-width independent, unlike
``--stat``), and the exact byte counts (whole diff and ``scripts``/``skills``
diff, the plan's §6 second measure), together with the command that reproduces
the full patch. It deliberately does NOT vendor ~1.2 MB of release patch text
that ``git diff <base>..<tip>`` regenerates on demand; ``item.json`` marks the
stored diff evidence ``not_the_full_patch`` so nothing downstream can mistake
it for one.

THE DIRTY ARM IS NOT AUTHORED GROUND TRUTH. Its expectation is documented
independently of the fixture, at ``CHANGELOG.md``:48-57 (*"three ordinary names,
first try, zero adversary … three HIGH CORRECTNESS defects still emit … the run
still ends ⚠️ UNVERIFIED on a tree where nobody did anything wrong"*), in
``floorsynth.out_of_scope_defects``' own docstring, and in
``tests/test_v1521_regressions.py``:752, which pins the same three names. The
item stores the path list and the citation; it derives no expectation from the
thing it pins.

CLI: ``python3 -m scripts.corpusbuild --capture`` writes the durable capture
index and ``--build`` writes ``tests/corpus/``; both are human-invoked, never
wired into ``make ci``. The build REFUSES to write a partial manifest — a
manifest entry exists only for bytes copied in that invocation (TA-H1), so a
missing source is an error, never a silently smaller corpus.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

from scripts import difftool, floorsynth

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

# Where the committed corpus lives. Never ``.atlas``-segmented, never ``.md``.
DEFAULT_CORPUS = "tests/corpus"

# The 2026-07-26 dogfood corpus is exactly these run sandboxes: 3 tasks x 2 arms
# x 2 replicates. Not a sanity check — an identity check (see build_corpus).
EXPECTED_RUN_SANDBOXES = 12

# SEC-4, stated wherever the bytes are: ``.atlas/`` was coder-writable during
# recording, so every copied artifact is model-influenced evidence.
_PROVENANCE_WARNING = (
    ".atlas/ was coder-writable during recording; these artifacts are "
    "model-influenced, not machine-attested."
)

# The three judgment-critic artifact names, taken from floorsynth itself rather
# than hand-copied: a fourth critic must not silently go uncollected (CQ5's
# hand-copy class).
CRITIC_FILES: tuple[str, ...] = tuple(name for name, _dim in floorsynth.CRITIC_ARTIFACTS)

# The run artifacts a floorsynth predicate actually reads, byte-copied verbatim.
# ``det_evidence.json`` carries ``runcheck`` (the dict ``synth_runcheck`` judges),
# ``docs_clean`` (``synth_docs``) and the six lens defect lists
# (``script_defects_from``), so ``runcheck.json`` would be a second copy of data
# already here. ``plan.md``/``worktree/``/``context*.json``/``hooks.jsonl`` are
# excluded: no predicate reads them, and a ``.md`` would turn ``make ci`` red.
RUN_ARTIFACTS: tuple[str, ...] = (
    ("state.json", "log.jsonl", "det_evidence.json", "diff.patch")
    + CRITIC_FILES
    + ("merged_critic.json",)
)

# Arm C: the four release intervals the roadmap's growth thesis is about. Their
# changed ``.md`` lists are the ONLY real supply ``docs-naming`` has anywhere in
# this corpus (the three seed targets contain zero ``.md``).
RELEASE_INTERVALS: tuple[tuple[str, str], ...] = (
    ("v1.4.0", "v1.5.0"),
    ("v1.5.0", "v1.5.1"),
    ("v1.5.1", "v1.5.2"),
    ("v1.5.2", "v1.5.2.1"),
)

# Arm C's §6 second measure: the "code" half of the diff, by the plan's own
# definition of code (``scripts`` + ``skills``).
CODE_DIRS: tuple[str, ...] = ("scripts", "skills")

# Arm D. Three ordinary names, documented at CHANGELOG.md:48-57 and pinned
# independently at tests/test_v1521_regressions.py:752, plus the one file the
# coder was actually asked to write. scope_paths=["src"] is the interactive
# shape; the headless whole-tree scopes are immune and are not this item.
DIRTY_PRE_EXISTING: tuple[str, ...] = ("NOTES.md", "data/download.csv", "docs/notes.md")
DIRTY_CODER_PATH = "src/calc.py"
DIRTY_SCOPE: tuple[str, ...] = ("src",)

# The FAIL-OPEN arm (plan §5.4). Three items, and exactly three: these are the
# three fail-opens the record actually documents, and each names where. Authoring a
# should-fire input for the other seven emitters would be authoring the finding —
# the failure mode this phase exists to expose — so those emitters are rendered
# "— (none documented)" and never as "zero fail-opens".
#
# The plan's Task 9 asks for one per emitter and predicts all three record SILENCE.
# Neither survives execution. H6's ledger FIRES at HEAD (v1.5.2.1 added the
# trailing-REFINE condition), so the arm is two-valued and its status is measured
# per item, not asserted; that item is also the arm's own non-vacuity control.
#
# The namespaces are the SKILL's Step 4+5 variable names, so ``predcov`` replays
# them through the SKILL's OWN argument expressions — defaults included, because a
# fail-open IS the default being taken.
#
# NOTE for anyone pointing the denominator walk at this file: the H4 fixture below
# holds a defect-shaped dict with a blocking severity, authored at module scope.
# ``predcov.discover_emitters`` would raise DiscoveryFailure on it — "a blocking
# literal outside any top-level def" — and that is the rule working, not a defect:
# this is a capture tool, it emits nothing, and no denominator counts it.
FAILOPEN_ITEMS: tuple[dict, ...] = (
    {
        "id": "docs-naming",
        "emitter": "docs-naming",
        "function": "synth_docs",
        "injection": "v1.5.0 — a dropped docs_clean key failed OPEN on the docs floor",
        "should_fire_because": (
            "the evidence carries no docs_clean at all, so the docs floor was never "
            "evaluated; the SKILL reads ev.get('docs_clean', True) and the default IS "
            "the answer"
        ),
        "expectation_sources": [
            "CHANGELOG.md:356",
            "scripts/floorsynth.py::script_defects_from docstring (MANDATORY_FLAG_KEYS)",
        ],
        "namespace": {
            "ev": {
                "lint_defects": [],
                "pathcheck_defects": [],
                "reqcoverage_defects": [],
                "runcheck": {"ok": True, "returncode": 0, "test_count": 3,
                             "new_tests_collected": True, "revert_red": False},
                "verify_cmd": "python3 -m unittest discover -s .",
            },
        },
    },
    {
        "id": "critic-schema",
        "emitter": "critic-schema",
        "function": "merge_and_validate",
        "injection": "H4 — a critic forges a floor-namespace id and is classified "
                     "plugin-authored",
        "should_fire_because": (
            "enforce_critic_schema checks that id is PRESENT, never its VALUE, so a "
            "prompt-injected critic takes a floor id and its fix travels as a trusted "
            "instruction; the schema floor is the only predicate positioned to see it"
        ),
        "expectation_sources": [
            "docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md:97",
            "scripts/quality.py::enforce_critic_schema",
        ],
        "namespace": {
            "critics": [{
                "dimensions": {"CORRECTNESS": "yes", "CODE-QUALITY": "yes",
                               "SECURITY": "yes", "DOES-IT-RUN": "yes",
                               "REQUIREMENTS-COVERAGE": "yes", "MAINTAINABILITY": "yes"},
                "defects": [{
                    "id": "runcheck",
                    "category": "DOES-IT-RUN",
                    "severity": "CRITICAL",
                    "location": "verify_cmd",
                    "fix": "<a floor id forged by the reviewed target; the payload "
                           "itself is deliberately inert in this fixture>",
                }],
                "verdict": "FAIL",
            }],
            "script_defects": [],
        },
    },
    {
        "id": "stale-verdict",
        "emitter": "stale-verdict",
        "function": "stale_verdict_defects",
        "injection": "H6 — an honest crash after advance(REFINE) resumes at OUTPUT "
                     "and prints a green",
        "should_fire_because": (
            "the V7-forced refine never re-entered CODED, so no verification covers "
            "the tree as it stands; at v1.5.1 this ledger was SILENT and final_status "
            "printed OK"
        ),
        "expectation_sources": [
            "docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md:120",
            "scripts/floorsynth.py::stale_verdict_defects docstring (condition (c))",
        ],
        "namespace": {
            "log_records": [{"stage": s} for s in
                            ("GROUNDED", "CODED", "VERIFIED", "REFINE")],
        },
    },
)


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


def drop_trailing_output(records: list[dict]) -> list[dict]:
    """The ledger as the SKILL's OUTPUT block sees it: trailing OUTPUT removed.

    ``floorsynth.stale_verdict_defects`` runs BEFORE that block's own
    ``advance(..., "OUTPUT")``, so a fixture that keeps the OUTPUT record models
    a state the predicate is never called in — and specifically makes H6's
    trailing-shape condition unfirable. A ledger that never reached OUTPUT is
    returned unchanged; nothing but trailing OUTPUT records is ever dropped.
    """
    out = list(records or [])
    while out and isinstance(out[-1], dict) and out[-1].get("stage") == "OUTPUT":
        out.pop()
    return out


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
    items = [capture_run(runs_root, label) for label in _run_labels(runs_root)]
    index = {
        "schema": "predcov-capture/1",
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "capture_command": "python3 -m scripts.corpusbuild --capture --runs %s --out %s"
                           % (runs_root, out_dir),
        "runs_root": os.path.abspath(runs_root),
        "provenance_warning": _PROVENANCE_WARNING,
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


# --------------------------------------------------------------------------
# The corpus build. Every write is planned in memory first: a manifest entry
# exists only for bytes copied in THIS invocation (TA-H1), and a missing source
# aborts the build rather than shrinking the corpus silently.
# --------------------------------------------------------------------------
def _sha256(data: bytes) -> str:
    """Hex sha256 of the bytes actually written."""
    return hashlib.sha256(data).hexdigest()


def _json_bytes(obj) -> bytes:
    """Deterministic JSON bytes: sorted keys, 2-space indent, trailing newline."""
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _read_bytes(path: str) -> bytes | None:
    """File bytes, or None when absent/unreadable. Never raises."""
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _entry(name: str, data: bytes, source: str, kind: str) -> dict:
    """One manifest file entry: what was written, from where, and its hash."""
    return {"name": name, "kind": kind, "source": source,
            "bytes": len(data), "sha256": _sha256(data)}


def _git_bytes(repo_root: str, args: list[str]) -> tuple[bytes, int]:
    """Run git in ``repo_root`` capturing raw stdout. Never raises."""
    try:
        proc = subprocess.run(["git", "--no-pager", *args], cwd=repo_root,
                              capture_output=True, check=False)
    except (FileNotFoundError, OSError):
        return b"", 127
    return proc.stdout, proc.returncode


def plan_run_item(runs_root: str, rec: dict) -> tuple[dict, list, list[str]]:
    """Plan one recorded-run item: (manifest_item, [(relpath, bytes)], errors)."""
    label = rec["label"]
    arm = rec.get("arm") or "interrupted"
    item_id = "%s/%s" % (arm, label)
    sess = rec.get("source_session_dir") or ""
    errors: list[str] = []
    writes: list[tuple[str, bytes]] = []
    files: list[dict] = []

    for name in RUN_ARTIFACTS:
        src = os.path.join(sess, name)
        data = _read_bytes(src)
        if data is None:
            errors.append("%s: missing source artifact %s" % (item_id, src))
            continue
        writes.append(("%s/%s" % (item_id, name), data))
        files.append(_entry(name, data, src, "copied"))

    log_src = os.path.join(sess, "log.jsonl")
    log_text = _read(log_src)
    records = []
    for line in log_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            errors.append("%s: unparsable log.jsonl record" % item_id)
    eval_records = drop_trailing_output(records)
    eval_bytes = "".join(
        json.dumps(r, sort_keys=True) + "\n" for r in eval_records
    ).encode("utf-8")
    writes.append(("%s/log.eval.jsonl" % item_id, eval_bytes))
    files.append(_entry("log.eval.jsonl", eval_bytes, log_src,
                        "derived:drop-trailing-OUTPUT"))

    if rec.get("paths") is not None:
        paths_bytes = "".join(p + "\n" for p in rec["paths"]).encode("utf-8")
        writes.append(("%s/tree.paths" % item_id, paths_bytes))
        files.append(_entry(
            "tree.paths", paths_bytes,
            "difftool.change_paths(%s, %s)" % (rec.get("baseline_sha", ""),
                                               rec.get("resolved_review_root", "")),
            "derived:change_paths"))

    try:
        state_json = json.loads(_read(os.path.join(sess, "state.json")) or "{}")
    except ValueError:
        state_json = {}
    refine_passes = state_json.get("refine_passes")
    refine_passes = refine_passes if isinstance(refine_passes, int) else None

    item = {
        "arm": arm,
        "kind": "recorded-run",
        "label": label,
        "run_id": rec.get("run_id", ""),
        "rc": rec.get("rc"),
        "final_stage": rec.get("final_stage", ""),
        "refine_passes": refine_passes,
        # H4/§7: the pass-1 evaluations are GONE (critic artifact names are
        # pass-invariant and merged_critic.json is overwritten), so a per-run
        # rate is never a per-evaluation rate.
        "n_evaluations_performed": (refine_passes + 1) if refine_passes is not None else None,
        "n_evaluations_replayed": 1,
        "baseline_sha": rec.get("baseline_sha", ""),
        "scope_paths": rec.get("scope_paths", []),
        "recorded_review_root": rec.get("recorded_review_root", ""),
        "resolved_review_root": rec.get("resolved_review_root", ""),
        "tree_paths_state": rec.get("state", ""),
        "tree_paths_state_if_worktree_only": rec.get("state_if_worktree_only", ""),
        "log_records": len(records),
        "eval_log_records": len(eval_records),
        "evidence_file": "det_evidence.json",
        "diff_file": "diff.patch",
        "log_file": "log.jsonl",
        "eval_log_file": "log.eval.jsonl",
        "recorded_merged_critic_file": "merged_critic.json",
        "critic_files": list(CRITIC_FILES),
        "provenance_warning": _PROVENANCE_WARNING,
        "source_session_dir": sess,
    }
    item_bytes = _json_bytes(item)
    writes.append(("%s/item.json" % item_id, item_bytes))
    files.append(_entry("item.json", item_bytes, sess, "derived:build-metadata"))

    manifest_item = {"id": item_id, "arm": arm, "source": sess, "files": files}
    return manifest_item, writes, errors


def plan_historical_item(repo_root: str, base: str, tip: str) -> tuple[dict, list, list[str]]:
    """Plan one release-interval item from THIS repository's own tags."""
    spec = "%s..%s" % (base, tip)
    item_id = "historical/%s" % spec
    errors: list[str] = []
    names_out, rc1 = _git_bytes(repo_root, ["diff", "--name-only", spec, "--"])
    numstat, rc2 = _git_bytes(repo_root, ["diff", "--numstat", spec, "--"])
    whole, rc3 = _git_bytes(repo_root, ["diff", spec, "--"])
    code, rc4 = _git_bytes(repo_root, ["diff", spec, "--", *CODE_DIRS])
    if rc1 or rc2 or rc3 or rc4:
        errors.append("historical %s: git failed (rc %s/%s/%s/%s)" % (spec, rc1, rc2, rc3, rc4))
        return {}, [], errors

    paths = sorted(p for p in names_out.decode("utf-8", "replace").split("\n") if p)
    if not paths:
        errors.append("historical %s: no changed paths — is the tag present?" % spec)
        return {}, [], errors

    writes: list[tuple[str, bytes]] = []
    files: list[dict] = []
    paths_bytes = "".join(p + "\n" for p in paths).encode("utf-8")
    writes.append(("%s/tree.paths" % item_id, paths_bytes))
    files.append(_entry("tree.paths", paths_bytes,
                        "git diff --name-only %s" % spec, "derived:git"))
    writes.append(("%s/diff.numstat" % item_id, numstat))
    files.append(_entry("diff.numstat", numstat, "git diff --numstat %s" % spec, "derived:git"))

    item = {
        "arm": "historical",
        "kind": "release-interval",
        "base": base,
        "tip": tip,
        "range": spec,
        # A release point is a whole-tree state, not a scoped review: nothing can
        # be out of scope, which is exactly the second out-of-scope input value.
        "scope_paths": ["."],
        "changed_paths_file": "tree.paths",
        "changed_path_count": len(paths),
        "changed_md": [p for p in paths if p.endswith(".md")],
        "docs_check": "scripts/check_artifact_naming.py::check_file(root, rel) over changed_md",
        "diff_evidence": {
            "file": "diff.numstat",
            "kind": "numstat-summary",
            "not_the_full_patch": True,
            "reproduce_full_patch": "git diff %s" % spec,
            "full_diff_bytes": len(whole),
            "full_diff_sha256": _sha256(whole),
        },
        # Plan §6, in BYTES because the roadmap asked for bytes. No conclusion is
        # attached here; n=3 audited releases and the variables are not separable.
        "second_measure": {
            "whole_diff_bytes": len(whole),
            "code_diff_bytes": len(code),
            "code_dirs": list(CODE_DIRS),
        },
        "source": "git tags in this repository",
    }
    item_bytes = _json_bytes(item)
    writes.append(("%s/item.json" % item_id, item_bytes))
    files.append(_entry("item.json", item_bytes, "git diff %s" % spec, "derived:build-metadata"))
    return {"id": item_id, "arm": "historical",
            "source": "git:%s@%s" % (os.path.abspath(repo_root), spec),
            "files": files}, writes, errors


def plan_dirty_item() -> tuple[dict, list, list[str]]:
    """Plan the documented honest-dirty-tree item (arm D).

    The expectation is NOT authored here: it is quoted from ``CHANGELOG.md``
    and cross-pinned by ``tests/test_v1521_regressions.py``. This item stores
    the path list and the citations only.
    """
    item_id = "dirty/changelog-50-57"
    paths = sorted(list(DIRTY_PRE_EXISTING) + [DIRTY_CODER_PATH])
    paths_bytes = "".join(p + "\n" for p in paths).encode("utf-8")
    source = "CHANGELOG.md:48-57 + tests/test_v1521_regressions.py:752"
    writes = [("%s/tree.paths" % item_id, paths_bytes)]
    files = [_entry("tree.paths", paths_bytes, source, "derived:documented-shape")]
    item = {
        "arm": "dirty",
        "kind": "documented-shape",
        "scope_paths": list(DIRTY_SCOPE),
        "changed_paths_file": "tree.paths",
        "pre_existing": list(DIRTY_PRE_EXISTING),
        "coder_authored": DIRTY_CODER_PATH,
        "review_root_shape": ".",
        "documented_expectation": (
            "three HIGH CORRECTNESS defects still emit, both refine passes still "
            "burn, and the run still ends UNVERIFIED on a tree where nobody did "
            "anything wrong"
        ),
        "expectation_sources": [
            "CHANGELOG.md:48-57",
            "tests/test_v1521_regressions.py:752",
            "scripts/floorsynth.py::out_of_scope_defects docstring (H2)",
        ],
        "note": "documented independently of this fixture; the fixture derives no "
                "expectation from the thing it pins",
        "source": source,
    }
    item_bytes = _json_bytes(item)
    writes.append(("%s/item.json" % item_id, item_bytes))
    files.append(_entry("item.json", item_bytes, source, "derived:build-metadata"))
    return {"id": item_id, "arm": "dirty", "source": source, "files": files}, writes, []


def build_failopen(corpus_root: str) -> tuple[dict | None, list[str]]:
    """Write the fail-open arm (plan §5.4). Returns (index, errors).

    A SEPARATE build from :func:`build_corpus`, and separately invoked, for one
    reason: these items are AUTHORED inputs, not captured bytes. TA-H1 forbids a
    manifest entry for bytes an invocation did not copy, and nothing here was copied
    from anywhere — so the arm carries its own index with its own citations, and
    ``manifest.json`` stays at the seventeen items it really captured.

    What makes the items non-vacuous is not a hash: it is that each one's
    "this should have fired" is documented somewhere other than the file asserting
    it, and every citation names a path in this repository.
    """
    errors: list[str] = []
    writes: list[tuple[str, bytes]] = []
    entries: list[dict] = []
    seen: set[str] = set()
    for spec in FAILOPEN_ITEMS:
        item_id = "failopen/%s" % spec["id"]
        if spec["id"] in seen:
            errors.append("%s: duplicate fail-open item id" % item_id)
            continue
        seen.add(spec["id"])
        if not spec.get("expectation_sources"):
            errors.append("%s: no expectation source — an authored fixture that "
                          "cites nothing derives its expectation from itself" % item_id)
            continue
        item = {
            "arm": "failopen",
            "kind": "documented-fail-open",
            "emitter": spec["emitter"],
            "function": spec["function"],
            "injection": spec["injection"],
            "should_fire_because": spec["should_fire_because"],
            "expectation_sources": list(spec["expectation_sources"]),
            "marshalling": "skill-default",
            "marshalling_note": (
                "replayed through skills/atlas/SKILL.md's own Step 4+5 argument "
                "expressions, defaults INCLUDED — the adapters refuse an absent key, "
                "and a fail-open is that default being taken"
            ),
            "counts_toward_prediction": False,
            "namespace": spec["namespace"],
            "source": "authored from the cited record; NOT captured bytes",
        }
        data = _json_bytes(item)
        writes.append(("%s/item.json" % item_id, data))
        entries.append(_entry("item.json", data, "; ".join(spec["expectation_sources"]),
                              "authored:documented-fail-open"))
    for relpath, _data in writes:
        if relpath.endswith((".md", ".py")) or ".atlas" in relpath.split("/"):
            errors.append("fail-open corpus path breaks the corpus rules: %s" % relpath)
    if errors:
        return None, errors

    index = {
        "schema": "predcov-failopen/1",
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_command": "python3 -m scripts.corpusbuild --failopen --corpus %s" % corpus_root,
        "rules": [
            "AUTHORED inputs, never captured bytes — deliberately absent from manifest.json",
            "every item cites its expectation in a file outside the fixture",
            "this arm does NOT move the primary denominator",
            "an emitter with no item here has NO DOCUMENTED fail-open; that is not zero",
        ],
        "items": sorted(entries, key=lambda e: e["source"]),
    }
    target = os.path.join(corpus_root, "failopen")
    if os.path.isdir(target):
        shutil.rmtree(target)
    for relpath, data in writes:
        dest = os.path.join(corpus_root, *relpath.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
    with open(os.path.join(target, "index.json"), "wb") as fh:
        fh.write(_json_bytes(index))
    return index, []


def build_corpus(runs_root: str, repo_root: str, corpus_root: str) -> tuple[dict | None, list[str]]:
    """Build the whole corpus. Returns (manifest, errors); writes nothing on error.

    The run-count check is FIRST and is not decoration. Measured while building
    this: with an unreachable ``runs_root`` the planner happily produced a
    five-item corpus of the two arms that need no sandbox (historical, dirty),
    reported success, and left the eleven honest item directories on disk
    UNLISTED by the manifest — a corpus that disagrees with its own provenance
    record, produced by a typo. A build that finds a different number of run
    sandboxes is building a DIFFERENT corpus, which is a deliberate act: it must
    change ``EXPECTED_RUN_SANDBOXES`` and say so, not slip through as a smaller
    numerator.
    """
    labels = _run_labels(runs_root)
    if len(labels) != EXPECTED_RUN_SANDBOXES:
        return None, [
            "expected %d run sandboxes under %s, found %d (%s). A different run "
            "set is a different corpus: change EXPECTED_RUN_SANDBOXES deliberately."
            % (EXPECTED_RUN_SANDBOXES, runs_root, len(labels), ", ".join(labels) or "none")
        ]
    index = {"items": [capture_run(runs_root, label) for label in labels]}
    manifest_items: list[dict] = []
    writes: list[tuple[str, bytes]] = []
    errors: list[str] = []

    for rec in index["items"]:
        item, item_writes, item_errors = plan_run_item(runs_root, rec)
        manifest_items.append(item)
        writes += item_writes
        errors += item_errors
    for base, tip in RELEASE_INTERVALS:
        item, item_writes, item_errors = plan_historical_item(repo_root, base, tip)
        if item:
            manifest_items.append(item)
        writes += item_writes
        errors += item_errors
    item, item_writes, item_errors = plan_dirty_item()
    manifest_items.append(item)
    writes += item_writes
    errors += item_errors

    for relpath, _data in writes:
        if ".atlas" in relpath.split("/"):
            errors.append("corpus path contains an .atlas segment: %s" % relpath)
        if relpath.endswith((".md", ".py")):
            errors.append("corpus path is a .md or .py file: %s" % relpath)
    if errors:
        return None, errors

    for item in manifest_items:
        item["path"] = "%s/%s" % (corpus_root.rstrip("/"), item["id"])
    manifest = {
        "schema": "predcov-corpus/1",
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_command": "python3 -m scripts.corpusbuild --build --runs %s --corpus %s"
                         % (runs_root, corpus_root),
        "runs_root": os.path.abspath(runs_root),
        "repo_root": os.path.abspath(repo_root),
        "provenance_warning": _PROVENANCE_WARNING,
        "rules": [
            "ZERO .md and ZERO .py files; no .atlas path segment",
            "a manifest entry exists only for bytes written in this invocation",
            "tree.paths is absent, never empty, when the path list is unmeasured",
        ],
        "items": sorted(manifest_items, key=lambda i: i["id"]),
    }
    manifest_bytes = _json_bytes(manifest)

    # Prune the arms this build OWNS before writing them. Without this a rebuild
    # leaves orphans: a file dropped from RUN_ARTIFACTS would survive on disk,
    # unlisted by the manifest, and the corpus would carry bytes no invocation
    # claims (the TA-H1 class, from the other direction). Arms this builder does
    # not produce — notably ``failopen/`` — are never touched.
    for arm_dir in sorted({relpath.split("/")[0] for relpath, _d in writes}):
        target = os.path.join(corpus_root, arm_dir)
        if os.path.isdir(target):
            shutil.rmtree(target)
    for relpath, data in writes:
        dest = os.path.join(corpus_root, *relpath.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
    with open(os.path.join(corpus_root, "manifest.json"), "wb") as fh:
        fh.write(manifest_bytes)
    return manifest, []


def _run_labels(runs_root: str) -> list[str]:
    """Sorted run-sandbox names under ``runs_root``. Never raises."""
    try:
        return sorted(
            n for n in os.listdir(runs_root)
            if os.path.isdir(os.path.join(runs_root, n))
            and os.path.isdir(os.path.join(runs_root, n, ".atlas"))
        )
    except OSError:
        return []


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
    parser.add_argument("--build", action="store_true",
                        help="Write the four-arm corpus under --corpus.")
    parser.add_argument("--failopen", action="store_true",
                        help="Write the authored fail-open arm under --corpus.")
    parser.add_argument("--runs", default=DEFAULT_RUNS,
                        help="Directory holding the run sandboxes (default: %(default)s).")
    parser.add_argument("--out", default=DEFAULT_CAPTURE,
                        help="Where to write the capture index (default: %(default)s).")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS,
                        help="Where to write the corpus (default: %(default)s).")
    parser.add_argument("--repo", default=".",
                        help="Repository the historical arm is derived from "
                             "(default: %(default)s).")
    args = parser.parse_args(argv)

    if not (args.capture or args.build or args.failopen):
        parser.print_help()
        return 0

    rc = 0
    if args.capture:
        index = capture(args.runs, args.out)
        print(_summarize(index))
        print("capture index: %s" % os.path.join(args.out, "capture.json"))
        if not index["items"]:
            print("NOTHING CAPTURED: no run sandboxes under %s" % args.runs, file=sys.stderr)
            rc = 1
    if args.build:
        manifest, errors = build_corpus(args.runs, args.repo, args.corpus)
        if errors:
            for err in errors:
                print("BUILD REFUSED: %s" % err, file=sys.stderr)
            print("BUILD REFUSED: nothing written; a partial corpus is a fabricated one.",
                  file=sys.stderr)
            return 1
        counts: dict[str, int] = {}
        for item in manifest["items"]:
            counts[item["arm"]] = counts.get(item["arm"], 0) + 1
        print("corpus %s: %d items (%s)"
              % (args.corpus, len(manifest["items"]),
                 ", ".join("%d %s" % (n, arm) for arm, n in sorted(counts.items()))))
        print("manifest: %s" % os.path.join(args.corpus, "manifest.json"))
    if args.failopen:
        index, errors = build_failopen(args.corpus)
        if errors:
            for err in errors:
                print("FAIL-OPEN ARM REFUSED: %s" % err, file=sys.stderr)
            return 1
        print("fail-open arm %s/failopen: %d documented item(s)"
              % (args.corpus, len(index["items"])))
    return rc


if __name__ == "__main__":
    sys.exit(main())
