"""Shared skill-package-aware markdown walk for the two doc gates.

A directory holding a ``SKILL.md`` is a skill package (a vendored
``skills/<name>/`` package or a first-party orchestrator dir) whose payload
markdown is third-party data, never a project artifact — neither the
artifact-naming gate (``scripts/check_artifact_naming.py``) nor the
inventory-drift gate (``scripts/inventory_drift.py``) descends into it. That
walk lived hand-copied in both gates and had already drifted in detail; this
module owns it ONCE. Consumers layer their own logic on top (sorting,
tracked-doc filtering); per-file decisions stay in the consumer modules.

:func:`is_package_dir` is pure; :func:`walk_markdown` is a filesystem READER.
"""
from __future__ import annotations

import os
import pathlib


def is_package_dir(filenames) -> bool:
    """True iff a directory listing marks a skill package (holds a SKILL.md)."""
    return "SKILL.md" in filenames


def walk_markdown(root, skip_segments):
    """Yield repo-relative POSIX paths of every non-exempt ``.md`` file.

    Walks ``root`` top-down, pruning any directory segment in
    ``skip_segments`` and never descending into a skill package (a directory
    holding a ``SKILL.md`` — its payload markdown is vendored data). Yields
    in walk order: sorting and tracked-doc filtering are consumer logic
    layered on top.
    """
    root = pathlib.Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_segments]
        if is_package_dir(filenames):
            dirnames[:] = []  # skill package — payload .md is vendored data
            continue
        for filename in filenames:
            if filename.endswith(".md"):
                yield (pathlib.Path(dirpath) / filename).relative_to(root).as_posix()
