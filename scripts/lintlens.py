# scripts/lintlens.py  (Task 1 slice — the pure planner + registry; launcher lands in Tasks 2-4)
"""lintlens — the ADVISORY, language-agnostic linter lane of the floor.

Surfaces the repo's own linter findings as NON-BLOCKING hints. Security-locked
HYBRID exec model (spec §Component 1): a small ``SAFE_AUTO`` allowlist of
pure-parse linters ({ruff, shellcheck, gofmt}) whose config is DATA is auto-run
with the repo's real config; every other (code-bearing) linter runs ONLY via an
operator-supplied ``lint_cmd`` (GATED — the same trusted boundary as
``verify_cmd``). Output NEVER enters ``script_defects``; it is stored under its
own evidence key so the FROZEN pure gate cannot see or block on it.

THE PLANNER (this slice) is pure: it decides WHICH jobs would run and with what
argv/shell, launching NOTHING. The binary token for a safe-AUTO job is ALWAYS the
bare name (``ruff``/``shellcheck``/``gofmt``), resolved from the system PATH at
launch time — never a repo-relative path — so a repo cannot smuggle an executable
entrypoint (spec §1.1 mechanism 1).
"""
from __future__ import annotations

import os
import os.path as _osp
import pathlib

# safe-AUTO allowlist. Each entry: the changed-file extension(s) that trigger it,
# the argv TEMPLATE (binary token first — resolved from PATH later, never repo),
# and the parser key (wired in Task 4). ``needs_config`` gates ruff on a real
# repo ruff config so we only speak when the repo actually uses the tool.
SAFE_AUTO: dict[str, dict] = {
    "ruff": {
        "exts": (".py",),
        "argv": ["ruff", "check", "--output-format=json", "--no-cache"],
        "parser": "ruff_json",
        "needs_config": True,
    },
    "shellcheck": {
        "exts": (".sh", ".bash"),
        "argv": ["shellcheck", "-f", "json"],
        "parser": "shellcheck_json",
        "needs_config": False,
    },
    "gofmt": {
        "exts": (".go",),
        "argv": ["gofmt", "-l"],
        "parser": "gofmt_list",
        "needs_config": False,
    },
}

# Filenames whose presence proves the repo configures ruff (DATA — TOML/declared).
_RUFF_CONFIG_FILES = ("ruff.toml", ".ruff.toml")


def _has_ruff_config(cwd: str) -> bool:
    """True iff the repo declares a ruff config (ruff.toml/.ruff.toml or [tool.ruff])."""
    root = pathlib.Path(cwd)
    for name in _RUFF_CONFIG_FILES:
        if (root / name).is_file():
            return True
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        return "[tool.ruff" in text  # [tool.ruff] or [tool.ruff.*]
    return False


def _changed_exts(changed_files: dict) -> set:
    """The set of lowercased extensions among the changed files (pure)."""
    return {os.path.splitext(rel)[1].lower() for rel in changed_files}


def _targets_for(exts: tuple, changed_files: dict) -> list[str]:
    """Sorted changed paths whose extension is in ``exts`` (pure)."""
    return sorted(
        rel for rel in changed_files
        if os.path.splitext(rel)[1].lower() in exts
    )


def _plan_jobs(changed_files: dict, cwd: str, lint_cmd: str | None) -> list[dict]:
    """Decide the advisory jobs to run — PURE, launches nothing (spec §1.1).

    safe-AUTO: a tool fires when a changed file matches its ext(s) AND (for ruff)
    the repo declares a ruff config. The argv template's binary token is the bare
    name — resolved from PATH at launch, NEVER a repo-relative path. GATED: an
    operator ``lint_cmd`` yields exactly one shell job. Returns [] when nothing
    fires (no-op → never blocks).
    """
    jobs: list[dict] = []
    changed = _changed_exts(changed_files)
    for tool, spec in SAFE_AUTO.items():
        if not (changed & set(spec["exts"])):
            continue
        if spec["needs_config"] and not _has_ruff_config(cwd):
            continue
        targets = _targets_for(spec["exts"], changed_files)
        jobs.append({
            "lane": "auto", "tool": tool, "kind": "argv",
            "argv": list(spec["argv"]) + targets, "shell": None,
            "targets": targets, "parser": spec["parser"],
        })
    if lint_cmd and lint_cmd.strip():
        jobs.append({
            "lane": "gated", "tool": "lint_cmd", "kind": "shell",
            "argv": None, "shell": lint_cmd.strip(),
            "targets": [], "parser": "gated_text",
        })
    return jobs


# The child env, built from scratch (spec §1.2). Mirrors nativefloor._hermetic_env
# but adds a throwaway HOME/TMPDIR (passed in) and Go isolation knobs (harmless to
# non-Go tools; they block cgo/toolchain fetch for a GATED Go linter).
_HERMETIC_KEYS = ("PATH", "HOME", "LANG", "TMPDIR",
                  "CGO_ENABLED", "GOTOOLCHAIN", "GOFLAGS")


def _hermetic_env(home: str, tmpdir: str) -> dict:
    """Return the from-scratch child env: {PATH,HOME,LANG,TMPDIR} + Go knobs (pure).

    NOT ``os.environ.copy()`` minus a denylist — a fresh dict, so hostile hooks
    (GITHUB_TOKEN/NPM_TOKEN/AWS_*/NODE_OPTIONS/RUBYOPT/LD_PRELOAD) simply do not
    exist in the child. HOME/TMPDIR are the caller's throwaway dirs. The Go knobs
    block the cgo/toolchain/module-fetch vector (X-09) for a GATED Go linter:
    ``-mod=readonly`` (NOT ``-mod=vendor``, which would false-error a non-vendored
    repo) forbids go.mod edits; ``GOTOOLCHAIN=local`` + network-off are the real
    fetch blocks.
    """
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": home,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "TMPDIR": tmpdir,
        "CGO_ENABLED": "0",
        "GOTOOLCHAIN": "local",
        "GOFLAGS": "-mod=readonly",
    }


def _confine_ok(path: str, root: str) -> bool:
    """True iff ``path`` resolves to a location INSIDE ``root`` (pure, spec §1.2).

    Rejects absolute escapes, ``..`` traversal, and escape symlinks by comparing
    the fully-resolved realpaths. ``root`` itself resolves first so a symlinked
    review_root is handled. Any error → False (fail-closed on confinement).
    """
    try:
        root_real = _osp.realpath(root)
        target_real = _osp.realpath(path)
    except OSError:
        return False
    return target_real == root_real or target_real.startswith(root_real + os.sep)
