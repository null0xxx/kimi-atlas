"""Inventory-drift gate — retires the hand-maintained artifact index.

The old ``analysis/artifact-index.md`` was a manually-synced list of doc
artifacts. This module replaces that workflow with a machine-checked manifest:
the *index* is built from what the documentation actually references
(markdown links in ``references/*.md`` + ``README.md``, plus those source docs
themselves), and the *actual* set is the doc tree on disk. Any mismatch is drift.

Phase-aware (DS-9): the index is built from the current-phase doc sources only —
never from ``PLAN.md`` (which lists future P2–P5 paths) — and the on-disk scan
excludes known-future directories and non-doc files, so the gate is green from
P1 onward. It catches a broken doc link (a source references a ``.md`` that is
absent → ``missing_from_disk``) and a doc artifact on disk that no source doc
references (``missing_from_index``). The source docs (``references/*.md`` +
``README.md``) index themselves, so the orphan signal fires on docs added
*outside* that source set (a new top-level doc or a new directory), not on a new
sibling dropped into ``references/``.

Skill-package exemption: a directory containing a ``SKILL.md`` is a vendored
skill package (``skills/<name>/``) whose payload markdown is third-party data,
not tracked documentation — :func:`scan_tree` does not descend into it. The
exemption lives in the shared walk (``scripts/skillpkgs.py``) ONLY;
:func:`is_tracked_doc` stays pure per-path.

:func:`diff_inventory` is pure; only :func:`main` touches the filesystem.
"""
from __future__ import annotations

import argparse
import pathlib
import posixpath
import re
import sys

# When run directly as ``python3 scripts/inventory_drift.py`` the interpreter
# puts ``scripts/`` (not the repo root) on ``sys.path[0]``, so
# ``from scripts import ...`` would fail. Put the plugin root on the path so
# the package imports resolve both when run directly and when imported as
# ``scripts.inventory_drift`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import skillpkgs  # noqa: E402  (path shim precedes this import)

# Directories whose contents are created by a later phase; excluded from the scan
# and dropped from the index so the gate is green at P1 (DS-9).
FUTURE_DIRS: tuple[str, ...] = (
    "agents",
    "probe",
    "tests/fixtures",
    "skills/atlas-resume",
)

# Basenames that are skill/config artifacts, not tracked documentation.
EXCLUDED_BASENAMES: frozenset[str] = frozenset({"SKILL.md"})

# Directory segments never walked when scanning the tree. Alongside VCS/build
# scratch (``.git``/``__pycache__``/``node_modules``), ``.superpowers`` is the
# git-ignored SDD tooling workspace (task briefs, implementer reports, the
# progress ledger) and ``.atlas`` is the git-ignored atlas run-ledger workspace
# (state.json, plan.md, diffs, critic JSONs written by a live run) — their
# ``.md`` files are scratch, never tracked documentation.
_SKIP_SEGMENTS: frozenset[str] = frozenset(
    {".git", "__pycache__", "node_modules", ".superpowers", ".atlas"}
)

# Markdown inline-link target: the URL/path inside ``](...)``.
_LINK_RE = re.compile(r"\]\(([^)]+)\)")


def diff_inventory(index_paths: list[str], actual_paths: list[str]) -> dict:
    """Return inventory drift between the doc index and the on-disk doc tree.

    ``missing_from_index`` = paths present on disk but referenced by no doc
    (undocumented artifacts). ``missing_from_disk`` = paths referenced by a doc
    but absent on disk (broken links / stale references). Both lists are sorted;
    empty lists mean no drift. Pure — no filesystem access.
    """
    index = set(index_paths)
    actual = set(actual_paths)
    return {
        "missing_from_index": sorted(actual - index),
        "missing_from_disk": sorted(index - actual),
    }


def extract_link_targets(markdown_text: str) -> list[str]:
    """Return the raw target of every ``](target)`` markdown link (pure)."""
    return [m.strip() for m in _LINK_RE.findall(markdown_text)]


def resolve_reference(source_relpath: str, target: str) -> str | None:
    """Resolve a link ``target`` (relative to its source doc) to a repo path.

    Returns a normalized repo-relative POSIX path, or ``None`` for external
    links (``http(s)://``, ``mailto:``), pure anchors, absolute paths, or targets
    that escape the repo root. Anchors/query strings are stripped first, so
    ``kimi-runtime.md#section`` in ``references/x.md`` resolves to
    ``references/kimi-runtime.md``.
    """
    cleaned = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not cleaned:
        return None
    if cleaned.startswith(("http://", "https://", "mailto:", "//", "/")):
        return None
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(source_relpath), cleaned))
    if joined == ".." or joined.startswith("../"):
        return None
    return joined


def _is_future(relpath: str) -> bool:
    return any(relpath == d or relpath.startswith(d + "/") for d in FUTURE_DIRS)


def is_tracked_doc(relpath: str) -> bool:
    """Return True iff ``relpath`` is a doc artifact this gate tracks.

    A tracked doc is a ``.md`` file that is neither an excluded basename
    (skill/config markdown) nor inside a known-future directory.
    """
    return (
        relpath.endswith(".md")
        and posixpath.basename(relpath) not in EXCLUDED_BASENAMES
        and not _is_future(relpath)
    )


def _source_docs(root: pathlib.Path) -> list[pathlib.Path]:
    """Return the phase-aware index sources: ``references/*.md`` + ``README.md``."""
    sources = sorted((root / "references").glob("*.md"))
    readme = root / "README.md"
    if readme.is_file():
        sources.append(readme)
    return sources


def build_index(root: pathlib.Path) -> set[str]:
    """Build the doc index from the phase-aware sources (references + README).

    Each source doc indexes itself, plus every tracked-doc path it links to.
    ``PLAN.md`` is never read as a source (it lists future paths), though it may
    still appear in the index as the target of a link from another doc.
    """
    index: set[str] = set()
    for src in _source_docs(root):
        rel = src.relative_to(root).as_posix()
        if is_tracked_doc(rel):
            index.add(rel)
        text = src.read_text(encoding="utf-8", errors="replace")
        for target in extract_link_targets(text):
            resolved = resolve_reference(rel, target)
            if resolved and is_tracked_doc(resolved):
                index.add(resolved)
    return index


def scan_tree(root: pathlib.Path) -> set[str]:
    """Return every tracked doc file on disk, relative to ``root`` (POSIX).

    The walk is the shared skill-package-aware one
    (:func:`skillpkgs.walk_markdown`): a directory that contains a ``SKILL.md``
    is a vendored skill package, so its payload markdown is never mistaken for
    an undocumented doc (the ``SKILL.md`` basename itself was already excluded
    via :data:`EXCLUDED_BASENAMES` — the net effect of the exemption is
    payload ``.md`` only). This gate layers the :func:`is_tracked_doc` filter
    on top.
    """
    actual: set[str] = set()
    for rel in skillpkgs.walk_markdown(root, _SKIP_SEGMENTS):
        if is_tracked_doc(rel):
            actual.add(rel)
    return actual


def main(argv: list[str] | None = None) -> int:
    """CLI: fail (exit 1) if the doc index drifts from the filesystem."""
    parser = argparse.ArgumentParser(
        description="Fail if the documentation index drifts from the filesystem."
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    index = build_index(root)
    actual = scan_tree(root)
    drift = diff_inventory(sorted(index), sorted(actual))

    missing_from_disk = drift["missing_from_disk"]
    missing_from_index = drift["missing_from_index"]

    for path in missing_from_disk:
        sys.stderr.write(f"DRIFT: referenced by docs but missing from disk: {path}\n")
    for path in missing_from_index:
        sys.stderr.write(f"DRIFT: on disk but referenced by no doc: {path}\n")

    if missing_from_disk or missing_from_index:
        sys.stderr.write(
            f"\n{len(missing_from_disk) + len(missing_from_index)} inventory drift(s) found.\n",
        )
        return 1

    sys.stdout.write(f"Inventory in sync: {len(actual)} tracked doc(s), no drift.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
