"""Render a benchmark scorecard as Markdown — per-task outcomes + the aggregate metrics,
with the gate-trustworthiness headline (false-pass count) surfaced first."""
from __future__ import annotations

_GLYPH = {"TRUE_PASS": "PASS  (verified & correct)",
          "FALSE_PASS": "FALSE PASS  (verified but WRONG)",
          "MISSED": "missed (correct but flagged UNVERIFIED)",
          "TRUE_FAIL": "fail  (honestly flagged)"}


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render(results: list[dict], card: dict) -> str:
    lines = ["# kimi-atlas benchmark scorecard", ""]
    fp = card["false_pass_count"]
    verdict = "TRUSTWORTHY GATE — 0 false passes" if fp == 0 else f"WARNING — {fp} FALSE PASS(es)"
    lines += [
        f"**Gate trust:** {verdict}",
        "",
        f"- tasks: **{card['n']}**",
        f"- solve rate (diff actually passes): **{_pct(card['solve_rate'])}**",
        f"- **false-pass rate** (verified-but-wrong): **{_pct(card['false_pass_rate'])}**  "
        f"← atlas's thesis says this is 0",
        f"- gate precision (OK really means correct): **{_pct(card['gate_precision'])}**",
        f"- gate recall (correct work confidently passed): **{_pct(card['gate_recall'])}**",
        f"- honesty (verdict matches reality): **{_pct(card['honesty'])}**",
        "",
        "| task | verdict | tests | outcome |",
        "|------|---------|-------|---------|",
    ]
    for r in results:
        lines.append(
            f"| {r['task']} | {r.get('verdict') or '—'} | "
            f"{'pass' if r['tests_pass'] else 'fail'} | {_GLYPH.get(r['outcome'], r['outcome'])} |"
        )
    return "\n".join(lines) + "\n"
