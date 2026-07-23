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

import json
import os
import os.path as _osp
import pathlib
import shutil
import subprocess
import tempfile

from scripts import proccap

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


_MAX_OUTPUT_BYTES = 512_000       # strict output cap before any storage (spec §1.2)
_TASKS_MAX = 256                  # PID cap: an RSS cap does not bound fork count
_NOFILE_MAX = 1024                # fd cap for the untrusted GATED sh -c lane (spec §1.2)
_NETNS: bool | None = None        # cached: `unshare -n` (network-off) works


def _tool_path(name: str) -> str | None:
    """Resolve a safe-AUTO binary from PATH/standard sites only (never repo)."""
    found = shutil.which(name)
    if found:
        return found
    for cand in (os.path.expanduser(f"~/.local/bin/{name}"),
                 f"/usr/local/bin/{name}", f"/usr/bin/{name}"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _cgroup_cap_available() -> bool:
    """True iff a ``systemd-run --scope`` MemoryMax cap works (delegates to proccap).

    CGROUP resource props (MemoryMax, TasksMax) ARE valid for ``--scope`` (external-
    process) units; namespace/sandbox props (PrivateNetwork, PrivateTmp) are NOT — they
    belong to manager-forked *service* units and make a ``--scope`` invocation fail with
    "Unknown assignment". So this tier carries ONLY the cgroup caps; network-off is a
    separate tier via ``unshare -n``. (The plan-challenge caught the original all-in-one
    ``--scope`` probe failing on every host, disabling every control.)
    """
    return proccap._detect_mem_backend() == proccap._BACKEND_CGROUP


def _netns_available() -> bool:
    """True iff ``unshare -n`` yields a private (loopback-only) net namespace (cached).

    Best-effort network-off. Fails (→ False) on hosts without unprivileged netns; the
    hermetic env (which already strips GITHUB_TOKEN/NPM_TOKEN/…) remains the PRIMARY
    secret-exfil control, so a False here degrades gracefully rather than disabling caps.
    """
    global _NETNS
    if _NETNS is not None:
        return _NETNS
    try:
        proc = subprocess.run(
            ["unshare", "-n", "true"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=15,
        )
        _NETNS = proc.returncode == 0
    except Exception:  # noqa: BLE001 — any probe failure → no netns (degrade).
        _NETNS = False
    return _NETNS


def _harden_argv(workload_argv: list, mem_mb: int) -> list:
    """Wrap a workload under the isolation ACTUALLY available on this host (spec §1.2).

    Two INDEPENDENT, individually-degrading tiers:
    * **network-off** — prepend ``unshare -n`` (loopback-only) when ``_netns_available()``.
    * **cgroup caps** — wrap under ``systemd-run --scope -p MemoryMax -p TasksMax`` when
      ``_cgroup_cap_available()``. These props DO work for scope units; PrivateNetwork/
      PrivateTmp do NOT and are never used (that was the challenge-caught bug).
    HOME/TMPDIR isolation is delivered by the hermetic env's throwaway dirs (not
    PrivateTmp). If neither tier is available the workload runs bare under the hermetic
    env. Impure over the two cached probes.
    """
    inner = ["unshare", "-n", *workload_argv] if _netns_available() else list(workload_argv)
    if _cgroup_cap_available() and mem_mb and mem_mb > 0:
        return [
            "systemd-run", "--scope", "--quiet",
            "-p", f"MemoryMax={int(mem_mb)}M",
            "-p", f"TasksMax={_TASKS_MAX}",
            "--", *inner,
        ]
    return inner


def _reset_probe_caches() -> None:
    """Test hook: clear the cached netns probe (proccap owns its own cgroup cache)."""
    global _NETNS
    _NETNS = None


def _cap_bytes(text: object) -> str:
    """Coerce to str, UTF-8-sanitize, and cap to _MAX_OUTPUT_BYTES (pure)."""
    if not text:
        return ""
    s = text if isinstance(text, str) else str(text)
    s = s.encode("utf-8", errors="replace").decode("utf-8")  # sanitize surrogates
    encoded = s.encode("utf-8")
    if len(encoded) > _MAX_OUTPUT_BYTES:
        return encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
    return s


def _empty_result() -> dict:
    return {"stdout": "", "stderr": "", "returncode": None, "timed_out": False}


def _launch(job: dict, review_root: str, timeout_s: int, mem_mb: int) -> dict:
    """Launch ONE job hardened, IN ``review_root``; return capped output. NEVER raises.

    The workload runs with ``cwd=review_root`` so the linters actually SEE the repo's
    changed files and discover the repo's (declarative) config — while HOME/TMPDIR are
    throwaway dirs via the hermetic env (no ~/.npmrc/~/.ssh read, no cache into operator
    space). safe-AUTO is an argv; the GATED ``sh -c`` lane (untrusted repo, operator-
    consented command) also caps file descriptors via ``ulimit -n``. Any failure — tool
    absent, seam exception, malformed job — degrades to an empty result. Throwaway dirs
    are always rmtree'd. (Running in ``review_root`` — not a throwaway HOME — was the
    challenge-caught fix; the previous cwd=home made every linter see an empty tree.)
    """
    home = tmp = None
    try:
        if job["kind"] == "argv":
            tool = _tool_path(job["argv"][0])
            if tool is None:
                return _empty_result()          # tool absent → no-op (never a defect)
            workload = [tool, *job["argv"][1:]]
        else:  # GATED shell command (operator-consented) — cap fds for the untrusted repo
            workload = ["sh", "-c",
                        f"ulimit -n {_NOFILE_MAX} 2>/dev/null || true; {job['shell']}"]
        home = tempfile.mkdtemp(prefix="lintlens-home-")
        tmp = tempfile.mkdtemp(prefix="lintlens-tmp-")
        wrapped = _harden_argv(workload, mem_mb)
        res = proccap._launch_and_wait(
            wrapped, cwd=review_root, timeout_s=timeout_s, env=_hermetic_env(home, tmp)
        )
        if not res.get("launched", False):
            return _empty_result()
        return {
            "stdout": _cap_bytes(res.get("stdout", "")),
            "stderr": _cap_bytes(res.get("stderr", "")),
            "returncode": res.get("returncode"),
            "timed_out": bool(res.get("timed_out")),
        }
    except Exception:  # noqa: BLE001 — never-raise (spec §1.2).
        return _empty_result()
    finally:
        for d in (home, tmp):
            if d is not None:
                shutil.rmtree(d, ignore_errors=True)


_PER_JOB_TIMEOUT_S = 60
_MEM_MB = 2048


def _parse(parser: str, stdout: str, tool: str, lane: str) -> list:
    """Turn a tool's raw stdout into advisory records (pure, never raises)."""
    try:
        if parser == "ruff_json":
            data = json.loads(stdout or "[]")
            out = []
            for d in data if isinstance(data, list) else []:
                loc = d.get("location") or {}
                out.append(_rec(tool, lane, d.get("filename"),
                                loc.get("row"), d.get("message", ""), d.get("code")))
            return out
        if parser == "shellcheck_json":
            data = json.loads(stdout or "[]")
            out = []
            for d in data if isinstance(data, list) else []:
                out.append(_rec(tool, lane, d.get("file"), d.get("line"),
                                d.get("message", ""), "SC%s" % d.get("code", "")))
            return out
        if parser == "gofmt_list":
            return [_rec(tool, lane, ln.strip(), None, "not gofmt-formatted", None)
                    for ln in (stdout or "").splitlines() if ln.strip()]
        if parser == "gated_text":
            text = (stdout or "").strip()
            return [_rec(tool, lane, None, None, text, None)] if text else []
    except Exception:  # noqa: BLE001 — a parse surprise contributes nothing.
        return []
    return []


def _rec(tool, lane, path, line, message, rule) -> dict:
    """One canonical advisory record (never a defect; advisory only)."""
    return {"id": "", "tool": tool, "lane": lane,
            "path": path, "line": line,
            "message": str(message)[:2000], "rule": rule}


def check(changed_files: dict, cwd: str, lint_cmd: str | None = None) -> list:
    """Run the advisory linters and return advisory records. NEVER raises.

    Plans jobs (pure), launches each hardened + never-raising, parses output, and
    mints per-record unique ``LNT<n>`` ids after a stable sort. Empty on any
    failure or when nothing fires (no-op → never blocks). Output is ADVISORY: the
    caller stores it under ``lintlens_advisory`` and NEVER adds it to
    ``script_defects`` (the firewall, spec §Component 2).
    """
    try:
        if not isinstance(changed_files, dict):
            return []
        # review_root confinement (spec §1.2): drop any changed path whose realpath
        # escapes `cwd` (escape symlink / traversal) BEFORE it can become a linter
        # target. The GATED lint_cmd is unaffected — it runs in `cwd` regardless.
        safe_files = {rel: text for rel, text in changed_files.items()
                      if isinstance(rel, str) and _confine_ok(os.path.join(cwd, rel), cwd)}
        jobs = _plan_jobs(safe_files, cwd, lint_cmd)
        records: list = []
        for job in jobs:
            res = _launch(job, cwd, _PER_JOB_TIMEOUT_S, _MEM_MB)
            records += _parse(job["parser"], res.get("stdout", ""),
                              job["tool"], job["lane"])
        records.sort(key=lambda r: (r["tool"], str(r["path"]),
                                    r["line"] if r["line"] is not None else -1,
                                    str(r["rule"]), r["message"]))
        for i, r in enumerate(records, 1):
            r["id"] = "LNT%d" % i
        return records
    except Exception:  # noqa: BLE001 — the whole lane is advisory; failure = silence.
        return []
