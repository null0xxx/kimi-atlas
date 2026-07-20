"""AST syntax/parse + lint-floor lens — a deterministic COMMIT-time verifier.

The brief's "linter" is answered by a *lens*, not delegated to an LLM critic
(blueprint Ph4). Over the ``{path: text}`` map of changed **Python** source
(``.py`` only; non-Python paths are skipped) this module runs blocking,
fully-deterministic checks and returns the canonical ``{id, category, severity,
location, fix}`` defect shape the backbone merges identically to a critic/``sast``
defect (``verdict.merge`` -> ``gate``).

This task ships the **syntax/parse** check: ``ast.parse`` plus the builtin
``compile(text, path, "exec")`` — the same compilation :mod:`py_compile` performs,
without touching disk. A parse or compile failure is a HIGH ``DOES-IT-RUN`` defect:
the module cannot import, so nothing downstream can run. The lens is labelled
**"syntax/parse", never "type-check"** — it makes no claim about types (OD-A).

Pure and free of the runtime: ``lint`` takes source text in and returns defects out,
so it is unit-testable without a filesystem or a build.
"""
from __future__ import annotations

import ast

_DOES_IT_RUN = "DOES-IT-RUN"


def _d(did: str, category: str, severity: str, location: str, fix: str) -> dict:
    """Build one defect in the canonical ``{id, category, severity, location, fix}`` shape."""
    return {"id": did, "category": category, "severity": severity,
            "location": location, "fix": fix}


def _is_py(path: str) -> bool:
    """True iff ``path`` is a Python source file this lens analyses."""
    return path.endswith(".py")


def check_syntax(path: str, text: str) -> dict | None:
    """Return a HIGH DOES-IT-RUN defect if ``text`` fails to parse/compile, else ``None``.

    Runs ``ast.parse`` (syntax) then the builtin ``compile(..., "exec")`` (the
    py_compile check, disk-free). ``ValueError`` covers pathological source such as
    embedded null bytes on Python versions that raise it there (3.12 raises a
    ``SyntaxError`` for that case — both branches produce the same HIGH defect, so
    the lens is robust across versions). The message says "syntax/parse", never
    "type-check".
    """
    try:
        ast.parse(text, filename=path)
    except SyntaxError as exc:
        return _d("astlens-syntax", _DOES_IT_RUN, "HIGH", f"{path}:{exc.lineno or 0}",
                  f"syntax/parse error: {exc.msg}; the module cannot be imported or run.")
    except ValueError as exc:
        return _d("astlens-syntax", _DOES_IT_RUN, "HIGH", f"{path}:0",
                  f"syntax/parse error: {exc}; the module cannot be imported or run.")
    try:
        compile(text, path, "exec")
    except (SyntaxError, ValueError) as exc:
        lineno = getattr(exc, "lineno", 0) or 0
        return _d("astlens-compile", _DOES_IT_RUN, "HIGH", f"{path}:{lineno}",
                  f"compile (py_compile) error: {exc}; the module cannot be imported or run.")
    return None


def lint(changed_files: dict[str, str]) -> list[dict]:
    """Run the deterministic ast lens over the changed Python source (pure).

    Non-``.py`` paths are skipped. Files are visited in sorted path order and each
    defect gets a stable, unique ``AST<n>-*`` id, so the output is fully
    deterministic. This task ships the syntax/parse pass; Task P4.2 extends it with
    the undefined-name / unused-import floor.
    """
    defects: list[dict] = []
    counter = 0
    for path in sorted(changed_files):
        if not _is_py(path):
            continue
        text = changed_files[path]
        syn = check_syntax(path, text)
        if syn is not None:
            counter += 1
            syn["id"] = f"AST{counter}-syntax"
            defects.append(syn)
            continue  # an unparseable module cannot be analysed further
    return defects
