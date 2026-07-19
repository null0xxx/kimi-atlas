#!/usr/bin/env python3
"""
Equity Report Chart Embedding Helper
=====================================
Fixes the 0-image bug in Task 3 PDF output.

Problem this solves:
    - chart_generator.py produces an .svg file AND (optionally) a base64 string
    - When called with --json, it only prints metadata (NO base64 payload)
    - Task 3 must therefore read the .svg file and base64-encode it manually
    - If Task 3 skips this step, the final HTML references files that WeasyPrint
      cannot resolve, producing a PDF with 0 embedded images.

What this helper does:
    1. Takes a list of chart specs (chart_type + data JSON)
    2. Calls chart_generator.py for each spec
    3. Reads the produced .svg file
    4. Returns a dict of {chart_id: {path, base64, width, height, html_snippet}}
    5. Also writes a manifest.json for debugging

Usage (programmatic):
    from embed_charts import render_and_embed, build_img_tag

    specs = [
        {"id": "C1", "chart_type": "revenue_segment", "data": {...}},
        {"id": "C2", "chart_type": "margin_trends",   "data": {...}},
        ...
    ]
    results = render_and_embed(specs, out_dir="./charts")
    for r in results:
        html = build_img_tag(r["base64"], alt=r["id"])
        # substitute into your HTML template

Usage (CLI):
    python embed_charts.py render --specs specs.json --out-dir ./charts
    python embed_charts.py count --html report.html
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path





# ============================================================
# Chart rendering & embedding
# ============================================================

def _run_chart_generator(chart_type, data, output_path, currency="$", unit="B"):
    """
    Invoke chart_generator.py as a subprocess.
    Returns the path to the written SVG, or raises RuntimeError on failure.
    """
    script = Path(__file__).parent / "chart_generator.py"
    if not script.exists():
        raise FileNotFoundError(f"chart_generator.py not found at {script}")

    cmd = [
        sys.executable,
        str(script),
        "--chart_type", chart_type,
        "--data", json.dumps(data, ensure_ascii=False),
        "--output", str(output_path),
        "--currency", currency,
        "--unit", unit,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"chart_generator.py failed for {chart_type}: "
            f"stderr={e.stderr.strip()}"
        )

    if not Path(output_path).exists():
        raise RuntimeError(
            f"chart_generator.py did not write {output_path}. stdout={result.stdout}"
        )

    return output_path


def _svg_to_base64(svg_path):
    """Read an SVG file and return a base64-encoded UTF-8 string."""
    with open(svg_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_img_tag(b64_string, alt="Chart", max_width="100%"):
    """
    Build the standard <img> HTML tag for embedding a base64 SVG chart.
    This is the EXACT pattern Task 3 must use in its HTML template.
    """
    return (
        f'<img src="data:image/svg+xml;base64,{b64_string}" '
        f'alt="{alt}" style="max-width:{max_width}; height:auto;" />'
    )


def build_exhibit_block(exhibit_number, title, b64_string, source_label):
    """
    Build the full exhibit block (label + chart + source line) for one chart.
    Use this to avoid forgetting any of the three required elements.
    """
    return (
        f'<div class="exhibit-label">\n'
        f'  <span class="exhibit-number">Exhibit {exhibit_number}:</span>\n'
        f'  <span class="exhibit-desc">{title}</span>\n'
        f'</div>\n'
        f'<div class="chart-container" style="text-align:center; margin:12px 0;">\n'
        f'  {build_img_tag(b64_string, alt=title)}\n'
        f'</div>\n'
        f'<p class="chart-source" style="font-size:8pt;color:#999;'
        f'text-align:right;margin-top:4px;">\n'
        f'  Source: {source_label}\n'
        f'</p>'
    )


def render_and_embed(specs, out_dir, currency="$", unit="B"):
    """
    Render a list of charts and return their base64-embedded payloads.

    specs: list of dicts, each like:
      {
        "id": "C1",
        "chart_type": "revenue_segment",
        "data": {...},           # the JSON data for that chart
        "currency": "$",         # optional override
        "unit": "B",             # optional override
        "title": "Revenue by Segment FY2022-FY2026E",  # optional, for exhibit block
        "source_label": "Company filings; model calculation"  # optional
      }

    Returns: list of dicts with keys:
      id, chart_type, path, base64, base64_length, html_img_tag, html_exhibit
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    manifest = []

    for i, spec in enumerate(specs):
        chart_id = spec.get("id", f"C{i+1}")
        chart_type = spec["chart_type"]
        data = spec["data"]
        cur = spec.get("currency", currency)
        un = spec.get("unit", unit)
        title = spec.get("title", chart_id)
        source_label = spec.get("source_label", "Model calculation; public filings")

        out_path = out_dir / f"{chart_id}.svg"

        try:
            _run_chart_generator(chart_type, data, out_path, currency=cur, unit=un)
            b64 = _svg_to_base64(out_path)
            ok = True
            err = None
        except Exception as e:
            b64 = ""
            ok = False
            err = str(e)

        result = {
            "id": chart_id,
            "chart_type": chart_type,
            "path": str(out_path) if ok else None,
            "ok": ok,
            "error": err,
            "base64": b64,
            "base64_length": len(b64),
            "html_img_tag": build_img_tag(b64, alt=title) if ok else "",
            "html_exhibit": build_exhibit_block(
                exhibit_number=i + 1,
                title=title,
                b64_string=b64,
                source_label=source_label,
            )
            if ok
            else f"<!-- Chart {chart_id} generation failed: {err} -->",
        }
        results.append(result)
        manifest.append(
            {
                "id": chart_id,
                "chart_type": chart_type,
                "path": result["path"],
                "ok": ok,
                "error": err,
                "base64_length": result["base64_length"],
            }
        )

    # Write manifest for debugging
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return results


def count_embedded_charts(html_path):
    """
    Count how many base64 SVG images are actually embedded in the HTML.
    Used by QA check A23.
    """
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    return len(re.findall(r'src="data:image/svg\+xml;base64,', content))


# ============================================================
# CLI
# ============================================================

def _cli_render(args):
    with open(args.specs, "r", encoding="utf-8") as f:
        specs = json.load(f)
    results = render_and_embed(
        specs, out_dir=args.out_dir, currency=args.currency, unit=args.unit
    )
    # Print a compact summary (not the full base64)
    summary = [
        {k: v for k, v in r.items() if k not in ("base64", "html_img_tag", "html_exhibit")}
        for r in results
    ]
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # Write full payload to disk so Task 3 can read it back
    payload_path = Path(args.out_dir) / "embedded_charts.json"
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"\nFull payload written to: {payload_path}", file=sys.stderr)


def _cli_count(args):
    n = count_embedded_charts(args.html)
    print(f"Embedded base64 SVG charts: {n}")
    if args.min is not None and n < args.min:
        print(f"FAIL: expected at least {args.min}, got {n}")
        sys.exit(1)
    sys.exit(0)


def main():
    p = argparse.ArgumentParser(description="Equity Report Chart Embedding Helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_render = sub.add_parser(
        "render", help="Render charts from a JSON specs file and embed as base64"
    )
    p_render.add_argument("--specs", required=True, help="JSON file with chart specs")
    p_render.add_argument("--out-dir", required=True, help="Output directory for SVGs")
    p_render.add_argument("--currency", default="$")
    p_render.add_argument("--unit", default="B")
    p_render.set_defaults(fn=_cli_render)

    p_count = sub.add_parser(
        "count", help="Count embedded base64 SVG charts in the final HTML"
    )
    p_count.add_argument("--html", required=True)
    p_count.add_argument("--min", type=int, default=None, help="Fail if below this")
    p_count.set_defaults(fn=_cli_count)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
