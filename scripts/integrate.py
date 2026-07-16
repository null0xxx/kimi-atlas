"""INTEGRATE-sink decision core for ATLAS-WEAVE (pure, deterministic).

Mirrors verdict.py/plandag.py discipline: NO orchestration/LLM/I/O — only
deterministic functions over diffs and defect lists. This module decides what the
combined-tree sink must FLAG (cross-change file conflicts, folded integration
verdict); the runtime "hands" — actually `git apply`-ing the union of diffs onto a
worktree and running the union of suites — are the scheduler-wiring layer and are
deliberately OUT OF SCOPE here (mirrors how P6/P7 built pure cores first).
"""
from __future__ import annotations

from scripts import verdict


def touched_files(diff_text: str) -> list[str]:
    """Return the repo-relative paths a unified diff touches (order-preserving, deduped).

    A line-oriented parse: ``diff --git`` starts a file section (resets hunk state),
    ``@@`` starts a hunk body. A ``+++``/``--- `` line is read as a file header ONLY
    when NOT inside a hunk — so a deleted line whose content starts with ``-- `` (or an
    added ``++ ``) is never mistaken for a header. Both the ``--- a/<path>`` (deletes,
    whose ``+++`` is ``/dev/null``) and ``+++ b/<path>`` (adds/modifies) headers are
    read in text order, dropping ``/dev/null`` and the optional ``a/``/``b/`` prefix and
    any trailing ``\t`` metadata. This is the ACTUAL touched-file set — ground truth for
    the cross-change conflict gate, which declared scope_paths and a clean ``git apply``
    cannot be trusted to reflect.
    """
    seen: set[str] = set()
    out: list[str] = []
    in_hunk = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            in_hunk = False
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if in_hunk or not (line.startswith("+++ ") or line.startswith("--- ")):
            continue
        path = line[4:].split("\t", 1)[0].strip()
        if path[:2] in ("a/", "b/"):
            path = path[2:]
        if path and path != "/dev/null" and path not in seen:
            seen.add(path)
            out.append(path)
    return out


def actual_conflicts(changes: list[dict]) -> list[dict]:
    """Return a CORRECTNESS/CRITICAL defect per file touched by more than one change.

    ``changes`` = ``[{"id": str, "diff": str}]``. Re-validates disjointness against
    the files each diff ACTUALLY touched — the post-coding backstop the P6 review
    required, because a planner's declared ``scope_paths`` and a clean ``git apply``
    both miss same-file-different-hunk edits (which concatenate silently). Two
    changes editing one file would corrupt each other, so each shared file is a
    blocking conflict. Defects are sorted by path for deterministic output; empty
    list means the changes are actually disjoint.
    """
    file_to_ids: dict[str, list[str]] = {}
    for change in changes:
        for path in touched_files(change.get("diff", "")):
            file_to_ids.setdefault(path, []).append(change.get("id"))
    defects: list[dict] = []
    for path in sorted(file_to_ids):
        ids = sorted({i for i in file_to_ids[path] if i is not None})
        if len(file_to_ids[path]) >= 2 and len(ids) >= 2:
            defects.append({
                "id": f"integrate-conflict:{path}",
                "category": "CORRECTNESS",
                "severity": "CRITICAL",
                "location": path,
                "fix": f"file {path} is edited by multiple changes ({', '.join(ids)}); "
                       f"make the node scopes actually disjoint",
            })
    return defects


def integration_verdict(defect_lists) -> dict:
    """Fold conflict + differential defect lists into one canonical integration critic.

    ``defect_lists`` is an iterable of defect lists (e.g. ``actual_conflicts(...)``
    plus ``differential.integration_defects(...)``). Reuses ``verdict.merge`` (which
    already accepts a list of script defects), so the result is the canonical
    ``{dimensions, defects, verdict}`` shape that ``verdict.aggregate``/``gate``
    consume, with ``verdict == "FAIL"`` iff any folded defect is blocking. Pure.
    """
    all_defects = [defect for lst in defect_lists for defect in (lst or [])]
    return verdict.merge([], all_defects)
