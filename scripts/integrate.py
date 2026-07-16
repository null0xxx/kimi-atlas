"""INTEGRATE-sink decision core for ATLAS-WEAVE (pure, deterministic).

Mirrors verdict.py/plandag.py discipline: NO orchestration/LLM/I/O — only
deterministic functions over diffs and defect lists. This module decides what the
combined-tree sink must FLAG (cross-change file conflicts, folded integration
verdict); the runtime "hands" — actually `git apply`-ing the union of diffs onto a
worktree and running the union of suites — are the scheduler-wiring layer and are
deliberately OUT OF SCOPE here (mirrors how P6/P7 built pure cores first).
"""
from __future__ import annotations

import re

from scripts import verdict

# A unified-diff file header: the path after `+++ ` / `--- ` (optionally `b/`/`a/`).
_PLUS = re.compile(r"^\+\+\+ (?:b/)?(.+)$", re.M)
_MINUS = re.compile(r"^--- (?:a/)?(.+)$", re.M)


def touched_files(diff_text: str) -> list[str]:
    """Return the repo-relative paths a unified diff touches (order-preserving, deduped).

    Reads both `+++ b/<path>` (adds/modifies) and `--- a/<path>` (deletes) headers so
    a deleted file (whose `+++` is `/dev/null`) is still counted; `/dev/null` is
    dropped. This is the ACTUAL touched-file set — the ground truth for the
    cross-change conflict gate, which the planner's declared scope_paths and a clean
    `git apply` cannot be trusted to reflect.
    """
    seen: set[str] = set()
    out: list[str] = []
    for match in list(_PLUS.finditer(diff_text)) + list(_MINUS.finditer(diff_text)):
        path = match.group(1).strip()
        if path and path != "/dev/null" and path not in seen:
            seen.add(path)
            out.append(path)
    return out
