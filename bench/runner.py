"""Thin I/O runner for the benchmark — the only part that touches the filesystem, git, and
the kimi CLI. It (a) reads a completed atlas run's ledger for its self-verdict + produced
diff, (b) applies that diff to a CLEAN materialisation of the task and runs the HIDDEN
acceptance tests (ground truth), and (c) can optionally drive atlas headless via ``kimi -p``.

The scoring decision itself lives in the pure ``bench.scorer`` — this module only gathers the
two booleans (verdict_ok, tests_pass) it needs.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

from bench import scorer, tasks


def read_run(run_dir: pathlib.Path) -> dict:
    """Extract ``{verdict_ok, diff_patch, stages, verdict}`` from a completed atlas run dir.

    ``verdict_ok`` is True iff the merged 6-lens critic returned ``OK``. Missing/degraded
    artifacts fail SAFE: no verdict -> not OK, no diff -> empty patch.
    """
    def _load(name):
        p = run_dir / name
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    merged_raw = _load("merged_critic.json")
    verdict = None
    if merged_raw:
        try:
            verdict = json.loads(merged_raw).get("verdict")
        except json.JSONDecodeError:
            verdict = None
    stages = []
    for line in _load("log.jsonl").splitlines():
        if line.strip():
            try:
                s = json.loads(line).get("stage")
                if s:
                    stages.append(s)
            except json.JSONDecodeError:
                pass
    return {
        "verdict": verdict,
        "verdict_ok": verdict == "OK",
        "diff_patch": _load("diff.patch"),
        "stages": stages,
    }


def diff_passes_hidden_tests(task_id: str, diff_patch: str, workdir: pathlib.Path) -> bool:
    """Apply ``diff_patch`` onto a fresh baseline of the task and run the hidden tests.

    Ground truth, independent of whether the human kept/discarded the change. A diff that
    does not even apply counts as a fail (the change never landed).
    """
    if not diff_patch.strip():
        return False
    d = workdir / f"{task_id}-grade"
    tasks.materialize(task_id, d, as_git=True)
    patch = d / ".atlas-candidate.patch"
    patch.write_text(diff_patch, encoding="utf-8")
    applied = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)],
                             cwd=str(d), capture_output=True, text=True)
    if applied.returncode != 0:
        return False
    ran = subprocess.run(["python3", "-m", "unittest", "-q"], cwd=str(d),
                         capture_output=True, text=True)
    return ran.returncode == 0


def score_from_ledger(task_id: str, run_dir: pathlib.Path, workdir: pathlib.Path) -> dict:
    """Turn one completed atlas run into a scored benchmark record."""
    run = read_run(run_dir)
    tests_pass = diff_passes_hidden_tests(task_id, run["diff_patch"], workdir)
    return {
        "task": task_id,
        "verdict": run["verdict"],
        "verdict_ok": run["verdict_ok"],
        "tests_pass": tests_pass,
        "outcome": scorer.classify(run["verdict_ok"], tests_pass),
        "reached_output": "OUTPUT" in run["stages"],
    }


def run_headless(task_id: str, workdir: pathlib.Path, *, timeout: int = 1500,
                 kimi: str = "kimi") -> pathlib.Path | None:
    """Materialise the task and drive atlas over it non-interactively (``kimi -p``).

    Returns the newest ``.atlas/<session>`` run dir written under the task repo, or None if
    none appeared. The human gate is never answered headless — we only need the ledger
    (verdict + diff.patch), which atlas writes before pausing at OUTPUT.
    """
    d = workdir / task_id
    tasks.materialize(task_id, d, as_git=True)
    brief = tasks.TASKS[task_id]["brief"]
    subprocess.run([kimi, "-p", brief], cwd=str(d), capture_output=True, text=True,
                   timeout=timeout)
    atlas = d / ".atlas"
    if not atlas.is_dir():
        return None
    runs = [p for p in atlas.iterdir() if p.is_dir()]
    return max(runs, key=lambda p: p.stat().st_mtime) if runs else None


def default_workdir() -> pathlib.Path:
    return pathlib.Path(tempfile.mkdtemp(prefix="atlas-bench-"))
