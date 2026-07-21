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
import builtins

_DOES_IT_RUN = "DOES-IT-RUN"
_CODE_QUALITY = "CODE-QUALITY"

# Names always available without a binding: Python builtins + the module dunders a
# module can reference implicitly. Used to suppress undefined-name false positives.
_BUILTINS: frozenset = frozenset(dir(builtins)) | {
    "__name__", "__file__", "__doc__", "__builtins__", "__spec__", "__loader__",
    "__package__", "__all__", "__annotations__", "__dict__", "__path__", "__cached__",
    "__class__",  # implicit cell referenced by an arg-less ``super()`` in a method
}

# A load of any of these means the module manipulates its own namespace dynamically,
# so a name we cannot see the binding of may still be defined at runtime -> skip the
# undefined-name pass entirely rather than risk blocking a valid build.
_DYNAMIC_NS: frozenset = frozenset({"exec", "eval", "globals", "locals", "vars"})


def _d(did: str, category: str, severity: str, location: str, fix: str) -> dict:
    """Build one defect in the canonical ``{id, category, severity, location, fix}`` shape."""
    return {"id": did, "category": category, "severity": severity,
            "location": location, "fix": fix}


def _is_py(path: str) -> bool:
    """True iff ``path`` is a Python source file this lens analyses."""
    return path.endswith(".py")


class _ModuleScan(ast.NodeVisitor):
    """Walk a module collecting definitions/uses, keeping annotation loads apart (pure).

    Bindings are unioned MODULE-WIDE (scopes flattened) — a deliberate
    over-approximation of *definitions* so the undefined-name pass produces very few
    false positives (at the cost of some false negatives). ``Name`` loads inside an
    **annotation** are recorded as *uses* (so an import referenced only by a type hint
    is not "unused") but are NOT eligible for the undefined-name pass: under
    ``from __future__ import annotations`` — the house style here — annotations are
    strings never evaluated, so an unresolved hint is not a runtime ``NameError`` and
    must never be flagged. String forward-refs (``x: "T"``) are parsed for the names
    they reference, and names in a ``del`` also count as uses.

    Two collections drive the two passes: ``loaded`` (runtime ``Load`` positions only)
    feeds undefined-name; ``used`` (every reference at all) feeds unused-import.
    """

    def __init__(self) -> None:
        self.bound: set[str] = set()
        self.imported: dict[str, int] = {}
        self.loaded: dict[str, int] = {}    # runtime Load positions only -> undefined pass
        self.used: set[str] = set()         # any reference at all -> unused-import pass
        self.star_import = False
        self.dunder_all: set[str] = set()
        self._in_annotation = 0             # >0 while inside an (unevaluated) annotation

    # -- imports -----------------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            local = a.asname or a.name.split(".")[0]
            self.bound.add(local)
            self.imported.setdefault(local, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # ``from __future__ import X`` is a compiler directive, not a real binding a
        # module ever references by name -> it must never be flagged "unused".
        future = node.module == "__future__"
        for a in node.names:
            if a.name == "*":
                self.star_import = True
                continue
            local = a.asname or a.name
            self.bound.add(local)
            if not future:
                self.imported.setdefault(local, node.lineno)

    # -- definitions / bindings --------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bound.add(node.name)
        for dec in node.decorator_list:     # decorators are real runtime loads
            self.visit(dec)
        for tp in getattr(node, "type_params", []):
            self.visit(tp)
        self.visit(node.args)               # params (visit_arg) + real default exprs
        self._visit_annotation(node.returns)
        for stmt in node.body:
            self.visit(stmt)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bound.add(node.name)
        self.generic_visit(node)            # bases/keywords/decorators are real loads

    def visit_arg(self, node: ast.arg) -> None:
        self.bound.add(node.arg)
        self._visit_annotation(node.annotation)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.target)             # target + value are real code;
        if node.value is not None:
            self.visit(node.value)
        self._visit_annotation(node.annotation)  # only the annotation is unevaluated

    # PEP 695 type parameters (3.12+) bind a name usable at runtime.
    def visit_TypeVar(self, node) -> None:
        self.bound.add(node.name)
        self.generic_visit(node)            # the bound expression is real

    def visit_ParamSpec(self, node) -> None:
        self.bound.add(node.name)

    def visit_TypeVarTuple(self, node) -> None:
        self.bound.add(node.name)

    def visit_Global(self, node: ast.Global) -> None:
        self.bound.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.bound.update(node.names)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.bound.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.bound.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.bound.add(node.name)
        self.generic_visit(node)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.bound.add(node.rest)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for tgt in node.targets:
            if (isinstance(tgt, ast.Name) and tgt.id == "__all__"
                    and isinstance(node.value, (ast.List, ast.Tuple, ast.Set))):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        self.dunder_all.add(elt.value)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bound.add(node.id)         # ``del x`` binds x here and counts as a use
            self.used.add(node.id)
        else:                               # ast.Load
            self.used.add(node.id)
            if not self._in_annotation:     # a real runtime load, not a type hint
                self.loaded.setdefault(node.id, node.lineno)

    def visit_Constant(self, node: ast.Constant) -> None:
        # A string in annotation position is a forward reference: parse the names it
        # references so an import used only via ``x: "T"`` is not called "unused". Names
        # go to ``used`` only (never ``loaded``) — still no undefined-name false flag.
        if self._in_annotation and isinstance(node.value, str):
            try:
                sub = ast.parse(node.value, mode="eval")
            except (SyntaxError, ValueError):
                return
            for n in ast.walk(sub):
                if isinstance(n, ast.Name):
                    self.used.add(n.id)

    def _visit_annotation(self, ann) -> None:
        if ann is None:
            return
        self._in_annotation += 1
        self.visit(ann)
        self._in_annotation -= 1


def _analyze_module(text: str):
    """Parse ``text`` and return (bound, imported, loaded, used, star_import, dunder_all).

    ``imported`` maps each import's local name to its lineno; ``loaded`` maps each
    runtime ``Load`` name (annotations excluded) to its first lineno; ``used`` is every
    referenced name (Load/Del/Store/annotation/string-forward-ref) for the
    unused-import pass; ``dunder_all`` holds the string entries of a module-level
    ``__all__`` (re-exports count as uses).
    """
    scan = _ModuleScan()
    scan.visit(ast.parse(text))
    return (scan.bound, scan.imported, scan.loaded, scan.used,
            scan.star_import, scan.dunder_all)


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

    Non-``.py`` paths are skipped. Per file: a syntax/parse failure is a HIGH
    DOES-IT-RUN defect (and no further analysis). Otherwise the lint floor emits an
    ``undefined-name`` HIGH DOES-IT-RUN defect for a name loaded at runtime but never
    bound module-wide and not a builtin (a runtime ``NameError``), and an
    ``unused-import`` MEDIUM CODE-QUALITY defect for an import never referenced or
    re-exported. The undefined-name pass is skipped when the module star-imports or
    dynamically manipulates its namespace (``exec``/``eval``/``globals``/…), so it
    never blocks a valid build. Files sorted; ids ``AST<n>-*`` unique — fully
    deterministic.
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
        bound, imported, loaded, used, star_import, dunder_all = _analyze_module(text)
        # A star import or a dynamic-namespace call can inject names we cannot see;
        # skip undefined-name entirely rather than risk blocking a valid build.
        dynamic = star_import or bool(_DYNAMIC_NS & set(loaded))
        if not dynamic:
            for name in sorted(loaded):
                if name not in bound and name not in _BUILTINS:
                    counter += 1
                    defects.append(_d(
                        f"AST{counter}-undefined", _DOES_IT_RUN, "HIGH",
                        f"{path}:{loaded[name]}",
                        f"undefined name {name!r} is used but never bound in this module "
                        f"(runtime NameError); import it, define it, or fix the typo."))
        for name in sorted(imported):
            if name not in used and name not in dunder_all:
                counter += 1
                defects.append(_d(
                    f"AST{counter}-unused-import", _CODE_QUALITY, "MEDIUM",
                    f"{path}:{imported[name]}",
                    f"imported name {name!r} is never used; remove the dead import."))
    return defects
