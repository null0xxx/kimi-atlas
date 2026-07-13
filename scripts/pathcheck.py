"""Deterministic path-grounding cross-check — the code backstop for lenses 1/6.

Every backticked, file-like token cited in ``text`` (a draft, plan, or diff)
must be a *verified* path: either present in ``ctx['relevant_files']`` or
existing on disk under ``root``. Ported from apex ``scripts/pathcheck.py`` with
**symbol resolution dropped** (CMP-06) — this module checks PATHS ONLY; dotted
code refs like ``obj.method`` are never treated as path claims. An unverified
path is a hard, deterministic grounding failure, so it is emitted at CRITICAL
under the canonical ``CORRECTNESS`` dimension.
"""
from __future__ import annotations

import pathlib
import re

# Backticked tokens that look like a file path (dotted extension, or a "/").
_PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)`")

# A bare token counts as a *path claim* only if it carries a known source
# extension; otherwise dotted code refs (`obj.method`) and numeric literals
# (`0.0`) false-positive. A token containing "/" is always a path claim.
_KNOWN_EXTS: set[str] = {
    "py", "js", "ts", "tsx", "jsx", "go", "rs", "java", "rb", "c", "h", "cpp",
    "hpp", "cc", "cs", "php", "swift", "kt", "scala", "lua", "sh", "bash",
    "md", "txt", "rst", "json", "toml", "yaml", "yml", "cfg", "ini", "env",
    "xml", "html", "css", "scss", "sql", "proto", "tf",
}


def _is_path_claim(token: str) -> bool:
    """True if ``token`` is a path-like citation (has a slash or a known extension)."""
    if "/" in token:
        return True
    return token.rsplit(".", 1)[-1].lower() in _KNOWN_EXTS


def cross_check(text: str, ctx: dict, root: str) -> list[dict]:
    """Return CORRECTNESS defects for every cited path that cannot be verified.

    Args:
        text: the draft / plan / diff text whose backticked path citations are
            checked.
        ctx: grounding context; verified paths are read from
            ``ctx['relevant_files']`` (each ``{path: ...}``), when present.
        root: repository root; a cited path existing on disk under ``root`` also
            counts as verified.

    Returns:
        One defect per distinct unverified path citation, in citation order. A
        bare basename (no "/") that matches the basename of a verified file is
        accepted (it names a real file); an unknown token stays flagged.
    """
    known = {f["path"] for f in ctx.get("relevant_files", []) if isinstance(f, dict) and "path" in f}
    known_basenames = {k.rsplit("/", 1)[-1] for k in known}
    root_path = pathlib.Path(root)
    defects: list[dict] = []

    candidates = [m for m in dict.fromkeys(_PATH_RE.findall(text)) if _is_path_claim(m)]
    for i, m in enumerate(candidates):
        if m in known or (root_path / m).exists():
            continue
        if "/" not in m and m in known_basenames:
            continue
        defects.append({
            "id": f"P{i}",
            "category": "CORRECTNESS",
            "severity": "CRITICAL",
            "location": m,
            "fix": f"Path `{m}` is unverified; remove it or replace it with a path "
                   f"that exists under the repo root.",
        })
    return defects
