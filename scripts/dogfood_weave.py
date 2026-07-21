"""End-to-end deterministic dogfood harness for the FULL ATLAS-WEAVE flow (P12/7).

Runs the whole pipeline on a REAL git repo with SCRIPTED coder outputs (no live
agents), so the composition of the pure cores and the I/O hands can be exercised
and pinned in CI:

    PLAN caps (runcaps) -> coerce DAG / degrade-to-atlas (planstage)
      -> SCHEDULE trampoline (scheduler + verdict per node)
        -> INTEGRATE: real git-apply union (uniontree) + real suite runs
           (suiterun) folded through the pure conflict/regression oracles
           (integrate / differential)
             -> AGGREGATE + status (scheduler.final_aggregate / run_status).

This module is a thin ROOT: it only marshals inputs into the existing modules and
performs the deferred "hands" (a baseline-sha read plus the union git-apply and the
suite runs, both via the existing hands). It NEVER computes pass/fail itself — that
authority stays in ``verdict`` / ``integrate`` / ``differential``.

Fail-safe by construction (mirrors the pure cores' degrade-toward-BLOCK rule): a
missing baseline sha, a failed ``git worktree add``, a rejected ``git apply``, or a
parse failure can only ADD a blocking defect or leave ``baseline_pass`` conservative
— never manufacture a false green. A node with no scripted output, or a non-"ok"
self-gate, fails safe (FAILED -> unresolved -> the run FAILs). Every worktree and
the whole ``.atlas/`` scratch dir are torn down in a ``finally``; nothing is left in
``repo_cwd``.
"""
from __future__ import annotations

import copy
import os
import shutil
import subprocess

from scripts import (
    differential,
    integrate,
    planstage,
    runcaps,
    scheduler,
    suiterun,
    uniontree,
    verdict,
)


def _baseline_sha(repo_cwd: str):
    """Read ``HEAD`` of ``repo_cwd`` (``git -C``); None on any failure (fail-safe)."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo_cwd, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    sha = (proc.stdout or "").strip()
    return sha or None


def _find_job(dag: dict, job_id) -> dict | None:
    for job in dag.get("jobs", []):
        if job.get("job_id") == job_id:
            return job
    return None


def _node_defects(nid, status) -> list:
    """A node's deterministic defect list: [] iff its self-gate reported ``"ok"``."""
    if status == "ok":
        return []
    return [{
        "id": f"node-failed:{nid}",
        "category": "CORRECTNESS",
        "severity": "CRITICAL",
        "location": nid,
        "fix": "node self-gate failed",
    }]


def _blocking_defect(defect_id: str, location: str, fix: str) -> dict:
    return {
        "id": defect_id,
        "category": "CORRECTNESS",
        "severity": "CRITICAL",
        "location": location,
        "fix": fix,
    }


def dogfood(repo_cwd: str, packet: dict, planner_output, scripted_nodes: dict) -> dict:
    """Drive the full ATLAS-WEAVE flow end-to-end and return its aggregate result.

    Returns ``{"verdict", "run_status", "nodes", "waves", "gas_spent", "conflicts",
    "regressions", "combined_pass"}``. ``planner_output=None`` (or any invalid DAG) degrades to the
    byte-identical 1-node atlas run. See the module docstring for the fail-safe
    contract.
    """
    packet = packet if isinstance(packet, dict) else {}
    scripted_nodes = scripted_nodes if isinstance(scripted_nodes, dict) else {}
    verify_cmd = packet.get("verify_cmd", "")

    # --- PLAN: halting caps + DAG (degrade to 1-node atlas on any planner failure) ---
    caps = runcaps.seed_caps(packet)
    dag = copy.deepcopy(planstage.coerce_dag(planner_output, packet, caps))
    # The planner proposes STRUCTURE; the harness provisions the halting FUEL. A valid
    # planner DAG is returned by coerce_dag verbatim (no meta), so seed the caps here;
    # single_node_dag already carries its own meta, which setdefault preserves.
    meta = dag.setdefault("meta", {})
    meta.setdefault("depth_max", caps["depth_max"])
    meta.setdefault("node_max", caps["node_max"])
    meta.setdefault("gas_remaining", caps["gas"])
    meta.setdefault("next_seq", 0)
    dag = scheduler.seed_jobs(dag)

    node_verdicts: dict = {}
    waves = 0
    gas0 = dag["meta"]["gas_remaining"]
    # Halting bound: every dispatch charges >=1 gas and expansion is capped, so the
    # loop cannot run longer than this. Asserted so a regression that broke halting
    # surfaces loudly instead of hanging.
    safety = gas0 + len(dag.get("nodes", {})) + 5

    # --- SCHEDULE trampoline (leaf nodes only; no DECOMPOSE children) ---
    iters = 0
    while not scheduler.is_terminated(dag):
        iters += 1
        assert iters <= safety, "dogfood trampoline exceeded its halting bound"
        wave = scheduler.plan_wave(dag, free_mb=8192)
        if not wave:
            break
        waves += 1
        dag = scheduler.dispatch_wave(dag, wave)
        for wjob in wave:
            job_id = wjob.get("job_id")
            running = _find_job(dag, job_id)
            if running is None:
                continue
            node_id = running.get("node_id")
            lease = running.get("lease")  # equals stamp_lease(job_id, attempts)
            # A node with no scripted output fails safe (not "ok" -> FAILED -> FAIL).
            status = scripted_nodes.get(node_id, {"status": "missing"}).get("status")
            receipt = {"job_id": job_id, "lease": lease, "status": status}
            dag = scheduler.apply_receipt(dag, receipt)
            node_verdicts[node_id] = verdict.merge([], _node_defects(node_id, status))

    gas_spent = gas0 - dag["meta"]["gas_remaining"]

    # Resolved (DONE) nodes in DAG insertion order — the union apply order.
    done_nodes = {j.get("node_id") for j in dag.get("jobs", []) if j.get("state") == "DONE"}
    resolved = [nid for nid in dag.get("nodes", {}) if nid in done_nodes]
    changes = [{"id": nid, "diff": scripted_nodes.get(nid, {}).get("diff", "")}
               for nid in resolved]

    # Pure cross-change conflict oracle over the ACTUAL touched files (independent of git).
    conflicts = integrate.actual_conflicts(changes)

    baseline_sha = _baseline_sha(repo_cwd)
    worktrees: list = []           # (worktree_path, session) to clean up
    apply_defects: list = []
    try:
        # --- baseline_pass: honest per-node isolated suite runs (union of green ids) ---
        baseline_pass: set = set()
        if baseline_sha:
            for ch in changes:
                session = f"node-{ch['id']}"
                u = uniontree.apply_union(baseline_sha, [ch], repo_cwd, session)
                wt = u.get("worktree")
                if wt:
                    worktrees.append((wt, session))
                    res = suiterun.run_suite(verify_cmd, wt)
                    baseline_pass |= {t for t, s in res.items() if s == "pass"}
                # A per-node apply/worktree failure degrades CONSERVATIVELY: its tests
                # simply never enter baseline_pass, so it can only under-credit (safe).

        # --- combined: the merged tree's union suite ---
        combined: dict = {}
        if baseline_sha:
            u = uniontree.apply_union(baseline_sha, changes, repo_cwd, "union")
            wt = u.get("worktree")
            if wt:
                worktrees.append((wt, "union"))
                combined = suiterun.run_suite(verify_cmd, wt)
            # A change the union git-apply REJECTED (or an unbuildable union tree) never
            # landed on the merged tree -> a CRITICAL blocker, never a false green. Single
            # source: the same integrate.apply_failures the ATLAS-WEAVE SKILL folds in.
            apply_defects.extend(integrate.apply_failures(u))
        elif changes:
            apply_defects.append(_blocking_defect(
                "baseline-sha-unresolved", repo_cwd,
                "could not resolve the baseline sha; integration is unverifiable"))

        # --- differential regression oracle + folded integration verdict ---
        regressions = differential.regressions(baseline_pass, combined)
        integ = integrate.integration_verdict([
            conflicts,
            differential.integration_defects(regressions),
            apply_defects,
        ])

        # --- AGGREGATE ---
        agg = scheduler.final_aggregate(dag, node_verdicts, integ)
        status = scheduler.run_status(dag, agg)
        return {
            "verdict": agg["verdict"],
            "run_status": status,
            "nodes": len(dag.get("nodes", {})),
            "waves": waves,
            "gas_spent": gas_spent,
            "conflicts": [d["location"] for d in conflicts],
            "regressions": regressions,
            # How many union tests genuinely reported the "pass" token — lets a green
            # assertion prove the combined suite actually RAN, not that it was skipped.
            "combined_pass": sum(1 for s in combined.values() if s == "pass"),
        }
    finally:
        for wt, session in worktrees:
            uniontree.cleanup(wt, repo_cwd, session)
        # Drop git's worktree admin records + remove the .atlas scratch dir so no
        # litter survives in repo_cwd.
        subprocess.run(["git", "-C", repo_cwd, "worktree", "prune"],
                       capture_output=True, check=False)
        shutil.rmtree(os.path.join(repo_cwd, ".atlas"), ignore_errors=True)
