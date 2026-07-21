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
    any trailing ``\t`` metadata. Header-less changes (pure ``rename``/``copy``) are read
    from their ``rename from/to`` / ``copy from/to`` lines, so a rename endpoint is never
    invisible to the conflict gate. Splits strictly on ``"\n"`` (git's line separator) —
    NOT ``str.splitlines()``, which would fragment a hunk-content line on a form-feed or
    other Unicode boundary git emits verbatim and desync the state machine into a phantom
    path. This is the ACTUAL touched-file set — ground truth for the cross-change conflict
    gate, which declared scope_paths and a clean ``git apply`` cannot be trusted to reflect.
    """
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        path = raw.split("\t", 1)[0].strip()
        if path[:2] in ("a/", "b/"):
            path = path[2:]
        if path and path != "/dev/null" and path not in seen:
            seen.add(path)
            out.append(path)

    in_hunk = False
    for line in diff_text.split("\n"):
        if line.startswith("diff --git "):
            in_hunk = False
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if in_hunk:
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            add(line[4:])
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            add(line.split(" ", 2)[2])
    return out


def actual_conflicts(changes: list[dict]) -> list[dict]:
    """Return a CORRECTNESS/CRITICAL defect per file touched by more than one change.

    ``changes`` = ``[{"id": str, "diff": str}]``. Re-validates disjointness against
    the files each diff ACTUALLY touched — the post-coding backstop the P6 review
    required, because a planner's declared ``scope_paths`` and a clean ``git apply``
    both miss same-file-different-hunk edits (which concatenate silently). Two
    changes editing one file would corrupt each other, so each shared file is a
    blocking conflict. Conflict is counted by the number of distinct CHANGES touching a
    file (their list position), NOT distinct non-None ids — so a missing or duplicate
    ``id`` fails SAFE (still flagged) rather than open, and one change touching a file in
    two hunks is never a self-conflict. Defects are sorted by path for deterministic
    output; empty list means the changes are actually disjoint.
    """
    file_to_touchers: dict[str, list[tuple[int, object]]] = {}
    for idx, change in enumerate(changes):
        for path in touched_files(change.get("diff", "")):
            file_to_touchers.setdefault(path, []).append((idx, change.get("id")))
    defects: list[dict] = []
    for path in sorted(file_to_touchers):
        touchers = file_to_touchers[path]
        if len({idx for idx, _ in touchers}) < 2:
            continue
        labels = sorted({cid if cid is not None else f"#{idx}" for idx, cid in touchers})
        defects.append({
            "id": f"integrate-conflict:{path}",
            "category": "CORRECTNESS",
            "severity": "CRITICAL",
            "location": path,
            "fix": f"file {path} is edited by multiple changes ({', '.join(labels)}); "
                   f"make the node scopes actually disjoint",
        })
    return defects


def apply_failures(u: dict) -> list[dict]:
    """Return a CRITICAL blocker per change the combined-tree union could not land.

    ``u`` is a ``uniontree.apply_union`` result
    ``{"worktree": str|None, "applied": [...], "failed": [{"id","reason"}], ...}``.
    A change whose diff the union ``git apply`` REJECTED — or a union worktree that could
    not be built at all — is absent from the merged tree, so the combined suite would
    verify the WRONG tree. Per the pure cores' degrade-toward-BLOCK rule this is the third
    disjointness net (``actual_conflicts`` catches same-file overlap; the differential
    catches a green-alone/red-combined test; this catches a change that never landed):
    a node whose change is not in the merged tree can never be credited green by the seam,
    so it is flagged deterministically here, NOT left to the integration critic.

    ``worktree is None`` means the whole union tree is unbuildable (``apply_union`` then
    lists every change in ``failed`` with a "worktree add failed" reason); those per-change
    entries are spurious, so it yields a SINGLE ``combined-tree-unbuildable`` blocker. A
    cleanly-built union with no rejects (or an empty change set) yields ``[]``. Pure.
    """
    if u.get("worktree") is None:
        if not u.get("failed"):
            return []
        return [{
            "id": "combined-tree-unbuildable",
            "category": "CORRECTNESS",
            "severity": "CRITICAL",
            "location": "union",
            "fix": "could not build the combined worktree; integration is unverifiable",
        }]
    defects: list[dict] = []
    for f in u.get("failed", []) or []:
        cid = f.get("id")
        defects.append({
            "id": f"combined-apply-failed:{cid}",
            "category": "CORRECTNESS",
            "severity": "CRITICAL",
            "location": str(cid),
            "fix": f"change {cid} did not apply onto the combined tree: {f.get('reason')}",
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
