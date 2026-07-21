"""CLI for the kimi-atlas benchmark.

  # confirm every task is sound (reference passes, stub fails) — no model, no cost:
  python3 -m bench.run_bench --validate

  # score completed atlas runs you drove interactively in Kimi Code:
  python3 -m bench.run_bench --score t1-roman=/path/.atlas/session_xxx t2-median-bugfix=/path/...

  # drive atlas headless over tasks and score them end to end (uses the kimi CLI + API):
  python3 -m bench.run_bench --headless t1-roman,t3-csvlite

Prints a Markdown scorecard. The pass/fail verdict is computed by the pure bench.scorer.
"""
from __future__ import annotations

import sys
import pathlib

from bench import report, runner, scorer, tasks


def _validate() -> int:
    wd = runner.default_workdir()
    sys.stdout.write(f"{'task':22} ref_pass stub_fail valid\n")
    ok = True
    for tid in tasks.TASKS:
        v = tasks.validate(tid, wd)
        ok = ok and v["valid"]
        sys.stdout.write(f"{tid:22} {str(v['ref_pass']):8} {str(v['stub_fail']):9} "
                         f"{'VALID' if v['valid'] else 'INVALID'}\n")
    return 0 if ok else 1


def _score(pairs: list[str]) -> int:
    wd = runner.default_workdir()
    results = []
    for pair in pairs:
        tid, _, run_dir = pair.partition("=")
        if tid not in tasks.TASKS or not run_dir:
            sys.stderr.write(f"skip: bad --score arg {pair!r}\n")
            continue
        results.append(runner.score_from_ledger(tid, pathlib.Path(run_dir), wd))
    if not results:
        sys.stderr.write("no runs scored\n")
        return 1
    sys.stdout.write(report.render(results, scorer.scorecard(results)))
    return 0


def _headless(csv: str) -> int:
    wd = runner.default_workdir()
    results = []
    for tid in [t.strip() for t in csv.split(",") if t.strip()]:
        if tid not in tasks.TASKS:
            sys.stderr.write(f"skip: unknown task {tid!r}\n")
            continue
        sys.stderr.write(f"running atlas headless on {tid} ...\n")
        run_dir = runner.run_headless(tid, wd)
        if run_dir is None:
            sys.stderr.write(f"  no .atlas run produced for {tid}\n")
            continue
        results.append(runner.score_from_ledger(tid, run_dir, wd))
    if not results:
        return 1
    sys.stdout.write(report.render(results, scorer.scorecard(results)))
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--validate":
        return _validate()
    if argv[0] == "--score":
        return _score(argv[1:])
    if argv[0] == "--headless" and len(argv) > 1:
        return _headless(argv[1])
    sys.stderr.write(__doc__ or "")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
