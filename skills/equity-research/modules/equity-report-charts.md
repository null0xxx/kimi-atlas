# Equity Report Charts — Module Specification

> **EQUITY REPORT ONLY** — This file is NOT used by the tear sheet workflow.
> Read this file during Phase 4 when `output_type = EQUITY_REPORT`.

---

## Overview

The equity report includes **6 data-driven charts** generated via `scripts/chart_generator.py` using matplotlib. Charts are rendered as **SVG** (vector, sharp at any zoom) and embedded inline in the HTML report as base64 `<img>` tags.

**Why SVG?** WeasyPrint (the HTML→PDF engine) does not execute JavaScript, so all charts must be pre-rendered static images. SVG is resolution-independent and looks crisp in PDF.

---

## Chart Set (6 Charts)

| # | Chart Name | Type | Placement in Report | Data Source |
|---|-----------|------|---------------------|-------------|
| C1 | Revenue by Segment | Stacked Bar | §Financial Analysis (after segment revenue table) | `analysis/revenue-model.md` output |
| C2 | Margin Trends | Multi-Line | §Financial Analysis (after profitability discussion) | Financial data (3-5Y gross/operating/net margin) |
| C3 | Market Share | Pie | §Industry & Competitive Landscape (after competitor table) | Research Doc §IV Competitive Landscape output |
| C4 | Historical PE Band | Line + Shaded | §Valuation Analysis (after historical band table) | `valuation/dcf-and-sensitivity.md` §Historical Band output |
| C5 | Scenario Comparison | Grouped Bar | §Scenario Analysis (after scenario table) | `analysis/scenario-deep-dive.md` output |
| **C6** | **Price Performance (Rebased)** | **Rebased Line** | **§Page 2 Data Summary (left column, above perf-table)** | **Market data (12-month daily close vs. index)** |

---

## Chart Specifications

### C1: Revenue by Segment (Stacked Bar)

**Purpose**: Show how each business segment contributes to total revenue over time, revealing mix shifts and growth drivers.

**Data Requirements**:
- 3-5 fiscal years of segment revenue (historical + forecast)
- Segment names and revenue values (in reporting currency)
- Forecast years marked with "E" suffix

**Visual Spec**:
- X-axis: Fiscal years (e.g., FY2022, FY2023, FY2024, FY2025E, FY2026E)
- Y-axis: Revenue in billions (auto-scaled, with currency prefix)
- Each segment = one color in the stack
- Color palette: Use the brand palette defined in §Global Style below
- Total revenue label on top of each bar
- Forecast years: bars have a subtle hatched pattern overlay to distinguish from actuals
- Legend: horizontal, below chart

**Script Call**:
```bash
python scripts/chart_generator.py \
  --chart_type revenue_segment \
  --data '{"years":["FY2022","FY2023","FY2024","FY2025E","FY2026E"],"segments":{"iPhone":[205.5,200.6,201.2,215.0,225.0],"Services":[78.1,85.2,96.2,108.0,120.0],"Mac":[40.2,29.4,29.9,32.0,34.0],"iPad":[29.3,28.3,26.7,28.5,30.0],"Wearables":[41.2,39.8,37.0,38.5,40.0]}}' \
  --currency '$' \
  --unit 'B' \
  --output revenue_segment.svg \
  --json
```

**Output**: SVG file + JSON metadata `{"path": "revenue_segment.svg", "width": 900, "height": 500}`

---

### C2: Margin Trends (Multi-Line)

**Purpose**: Track profitability trajectory — gross margin expansion/compression signals pricing power and cost control.

**Data Requirements**:
- 3-5 fiscal years of margin data (historical + forecast)
- Three margin lines: Gross Margin, Operating Margin, Net Margin (all as percentages)

**Visual Spec**:
- X-axis: Fiscal years
- Y-axis: Percentage (auto-ranged, e.g., 20%–50%)
- Three lines with distinct colors + markers (circle, square, triangle)
- Data point labels on each marker (e.g., "46.2%")
- Forecast period: dashed line style (vs. solid for actuals)
- Light gray grid lines on Y-axis only
- Legend: top-right corner

**Script Call**:
```bash
python scripts/chart_generator.py \
  --chart_type margin_trends \
  --data '{"years":["FY2022","FY2023","FY2024","FY2025E","FY2026E"],"gross_margin":[43.3,44.1,46.2,47.0,47.5],"operating_margin":[30.3,29.8,31.5,32.0,32.5],"net_margin":[25.3,25.0,26.7,27.0,27.5]}' \
  --output margin_trends.svg \
  --json
```

---

### C3: Market Share (Pie)

**Purpose**: Visual snapshot of who owns the market — instantly shows competitive dominance or fragmentation.

**Data Requirements**:
- Company market share percentage
- 3-5 key competitors with their shares
- "Others" bucket for the remainder

**Visual Spec**:
- Target company slice: pulled out (explode) + brand dark blue (#003366)
- Competitor slices: palette colors (see §Global Style)
- Labels: Company name + percentage on each slice (outside with leader lines if needed)
- No 3D effect — flat, clean design
- Title inside chart area is NOT needed (exhibit label handles it)
- If any slice <3%, group into "Others"

**Script Call**:
```bash
python scripts/chart_generator.py \
  --chart_type market_share \
  --data '{"target":"{Company}","shares":{"{Company}":27.6,"Competitor A":19.4,"Competitor B":14.1,"Competitor C":8.8,"Competitor D":7.5,"Others":22.6}}' \
  --output market_share.svg \
  --json
```

---

### C4: Historical PE Band (Line + Shaded)

**Purpose**: Shows whether current valuation is cheap or expensive relative to the stock's own history.

**Data Requirements**:
- 5-year monthly or quarterly PE data points (or summary stats)
- Statistics: Mean, +1σ, -1σ, +2σ, -2σ (or High/Low)
- Current PE value and its percentile

**Visual Spec**:
- X-axis: Time (quarters or years)
- Y-axis: PE ratio
- Center line: Mean PE (solid dark line)
- ±1σ band: medium shaded region (semi-transparent blue)
- ±2σ band: light shaded region (very light blue)
- Current PE: red dot with annotation label (e.g., "Current: 28.5x — 62nd percentile")
- If full time-series is unavailable, use a simplified horizontal band chart:
  - Horizontal bands showing High / +1σ / Mean / -1σ / Low
  - Current PE marked as a prominent marker with value label

**Script Call (full time-series)**:
```bash
python scripts/chart_generator.py \
  --chart_type pe_band \
  --data '{"periods":["Q1-21","Q2-21",...,"Q4-25"],"pe_values":[32.1,30.5,...,28.5],"mean":29.2,"std":3.8,"current":28.5,"current_percentile":62}' \
  --output pe_band.svg \
  --json
```

**Script Call (simplified — when only summary stats available)**:
```bash
python scripts/chart_generator.py \
  --chart_type pe_band_simple \
  --data '{"metric":"PE(TTM)","high":38.5,"plus_1sd":33.0,"mean":29.2,"minus_1sd":25.4,"low":22.1,"current":28.5,"percentile":62}' \
  --output pe_band.svg \
  --json
```

---

### C5: Scenario Comparison (Grouped Bar)

**Purpose**: Side-by-side visual comparison of Bull/Base/Bear cases — makes the investment decision framework tangible.

**Data Requirements**:
- Three scenarios: Bull, Base, Bear
- 2-4 metrics per scenario (e.g., Revenue, Net Income, EPS, Implied Price)
- Values must be specific numbers (not vague)

**Visual Spec**:
- X-axis: Metrics (Revenue, Net Income, EPS, Target Price)
- Each metric has 3 grouped bars: Bull (green), Base (blue), Bear (red/orange)
- Value labels on top of each bar
- Y-axis: primary axis for revenue/income, secondary axis for EPS/price if scale differs significantly
- Alternative: If scales are too different, generate as 2×2 sub-charts (one per metric)
- Light grid, no box frame

**Script Call**:
```bash
python scripts/chart_generator.py \
  --chart_type scenario_comparison \
  --data '{"scenarios":["Bull","Base","Bear"],"metrics":{"Revenue ($B)":[420,395,370],"Net Income ($B)":[110,100,88],"EPS ($)":[7.20,6.50,5.70],"Target Price ($)":[260,230,195]},"probabilities":[25,50,25]}' \
  --currency '$' \
  --output scenario_comparison.svg \
  --json
```

---

### C6: Price Performance — Rebased Line (NEW, MANDATORY for Page 2)

**Purpose**: Shows 12-month relative price performance of the stock vs. its sector/market index, both rebased to 100 at T-12M. Placed directly above the `.perf-table` on Page 2.

**Data Requirements**:
- Daily or weekly closing prices for the stock over the last 12 months
- Matching daily/weekly closes for the benchmark index:
  - A-shares → CSI 300 (沪深300)
  - HK stocks → HSI (恒生指数)
  - US stocks → S&P 500
- Both series rebased to 100 at T-12M

**Visual Spec**:
- X-axis: Dates across 12 months (monthly ticks)
- Y-axis: Rebased index (100 = 12 months ago)
- Two lines:
  - Stock: solid dark blue (`#003366`), 2px
  - Index: solid slate gray (`#6B7B8D`), 1.5px, semi-transparent (alpha=0.85)
- Horizontal reference line at 100 (dotted, `#CCCCCC`)
- Legend: top-left, compact
- Endpoint labels: show final rebased value next to each line's end
- No chart title (Exhibit label above handles it)
- Figure size: 7 × 3 inches (wider than tall, fits left column)

**Script Call**:
```bash
python scripts/chart_generator.py \
  --chart_type price_rebased \
  --data '{"dates":["2025-04-17","2025-05-17",...,"2026-04-17"],"stock_rebased":[100.0,102.3,...,118.5],"index_rebased":[100.0,101.1,...,109.2],"stock_label":"[TICKER]","index_label":"[CSI 300 / HSI / S&P 500]"}' \
  --output price_rebased.svg \
  --json
```

> **Data population rules**: `stock_label` must be the ticker from Task 1 (e.g., `600519.SH`), never a placeholder like `AAPL`. `index_label` must match the market detected in Task 1.

---

## Global Style Settings

### Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Primary (target company / main line) | Dark Blue | `#003366` |
| Secondary | Teal | `#0D7377` |
| Tertiary | Amber | `#D4A843` |
| Quaternary | Slate Gray | `#6B7B8D` |
| Quinary | Coral | `#C75B3F` |
| Senary | Sage Green | `#7BA05B` |
| Bull / Positive | Green | `#2E7D32` |
| Bear / Negative | Red-Orange | `#C62828` |
| Base Case | Brand Blue | `#1565C0` |
| Background | White | `#FFFFFF` |
| Grid | Light Gray | `#E8E8E8` |
| Text | Dark Gray | `#333333` |

### Typography (matplotlib settings)

```python
CHART_STYLE = {
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.color': '#E8E8E8',
}
```

### Figure Size

| Chart Type | Width × Height (inches) | DPI |
|-----------|------------------------|-----|
| Revenue Segment | 9 × 5 | 150 |
| Margin Trends | 9 × 5 | 150 |
| Market Share | 7 × 7 | 150 |
| PE Band | 9 × 5 | 150 |
| Scenario Comparison | 9 × 5.5 | 150 |
| Price Rebased (C6) | 7 × 3 | 150 |

> **Note**: DPI is 150 (not 300) because output is SVG — DPI only affects text sizing, not resolution.

---

## HTML Embedding — MANDATORY 4-STEP PROTOCOL

> **CRITICAL — reason for this explicit protocol**: Previously, some reports shipped with 0 charts embedded. Root cause: `chart_generator.py` called with `--json` flag returns metadata **without** the base64 payload (the payload is only written to the SVG file on disk). The embedding step MUST explicitly read the SVG file, base64-encode it, and construct the `<img>` tag. Do not skip any step.

### Step 1 — Run the generator

For each chart (C1–C6), call `scripts/chart_generator.py` via the `scripts/embed_charts.py` wrapper, or call it directly:

```bash
python scripts/chart_generator.py \
  --chart_type <type> \
  --data '<JSON>' \
  --output outputs/<name>.svg
```

The command writes a real SVG file to `outputs/<name>.svg`. **Do NOT rely on `--json` alone** — the stdout JSON strips the base64 payload by design.

### Step 2 — Read the SVG file and base64-encode it

```python
import base64, pathlib
svg_bytes = pathlib.Path("outputs/<name>.svg").read_bytes()
b64 = base64.b64encode(svg_bytes).decode("ascii")
```

Use `scripts/embed_charts.py render --specs <json>` for batch processing; it does this automatically and returns `{chart_id, base64, bytes_len}` per chart.

### Step 3 — Build the exhibit HTML block

```html
<div class="exhibit-label">
  <span class="exhibit-number">[Exhibit N:]</span>
  <span class="exhibit-desc">[Chart Description]</span>
</div>
<div class="chart-container" style="text-align: center; margin: 12px 0;">
  <img src="data:image/svg+xml;base64,{BASE64_SVG}"
       alt="[Chart Description]"
       style="max-width: 100%; height: auto;" />
</div>
<p class="chart-source">Source: [Data Source] | Chart: Model Calculation</p>
```

Replace `{BASE64_SVG}` with the actual base64 string from Step 2. **The `{BASE64_SVG}` placeholder must not remain in the final HTML.**

### Step 4 — Verify with `embed_charts.py count`

After the HTML is assembled, run:

```bash
python scripts/embed_charts.py count --html outputs/report.html
```

It counts `data:image/svg+xml;base64,` occurrences. Required minimum for Equity Report: **≥ 3** (this is enforced by QA check A23 in `report-qa.md`). Charts that failed to generate must be logged, not silently dropped.

### Placement — Which chart goes where

| Chart | Required Page / Section |
|-------|------------------------|
| C6 Price Performance | Page 2, left column, above `.perf-table` |
| C1 Revenue by Segment | Financial Analysis section, after segment table |
| C2 Margin Trends | Financial Analysis section, after margin discussion |
| C3 Market Share | Industry & Competitive section, after competitor table |
| C4 Historical PE Band | Valuation Analysis section, after band table |
| C5 Scenario Comparison | Scenario Analysis section, after scenario table |

### Rules

1. Always use base64-encoded SVG inlined via `data:` URI — guarantees PDF portability, no external fetches.
2. Every chart has an `.exhibit-label` above it and a `.chart-source` / `.data-source` line below it.
3. `.chart-container` ensures proper centering and prevents overflow.
4. The `alt` text must describe the chart for accessibility.
5. **Never** embed a chart with a placeholder base64 string like `{{BASE64}}` — this is a failure mode.
6. If a chart fails generation, insert `<!-- Chart C[N] generation failed: [reason] -->` and proceed; QA flags the miss.

---

## Data Flow

```
Phase 2-3 (Analysis)
  ├── Revenue model data → C1 (Revenue by Segment)
  ├── Financial data → C2 (Margin Trends)
  ├── Competitive deep dive → C3 (Market Share)
  ├── Historical band analysis → C4 (PE Band)
  └── Scenario analysis → C5 (Scenario Comparison)
      ↓
Phase 4 (Report Generation)
  1. Prepare JSON data for each chart from Analysis Brief
  2. Call `scripts/chart_generator.py` for each chart
  3. Read SVG output, base64-encode
  4. Embed in HTML at designated positions (see §Chart Set table)
```

---

## Placement Rules

1. **Each chart appears AFTER its corresponding data table** — the table provides the precise numbers, the chart provides the visual pattern.
2. **Charts should NOT appear on the same page as the cover** — they belong in the body sections.
3. **One chart per module maximum** — avoid chart overload. If a module already has a supply chain SVG or stock price chart, do not add another chart to that module.
4. **Page break awareness**: If a chart would be split across pages, add `page-break-before: always` to its container and push it to the next page.
5. **Exhibit numbering**: Charts are numbered sequentially with all other exhibits (tables, diagrams). A chart after Exhibit 5 (a table) becomes Exhibit 6.

---

## Error Handling (Critical — No Mock Data Fallback)

If `chart_generator.py` fails for any chart:

1. **Log the error** — record which chart failed and why
2. **Do NOT block report generation** — the report can still be delivered without that chart
3. **Add a placeholder note** in the HTML: `<!-- Chart C[N] generation failed: [error] -->`
4. **Record in QA** — mark the corresponding B-tier chart check as failed
5. **⛔ ABSOLUTE PROHIBITION**: Do NOT "fill in" missing chart data with estimated, synthetic, or placeholder numbers. A missing chart with an explanatory note is infinitely better than a chart with fabricated data.
6. **Common fixes**:
   - Missing data → check Excel model and API sources; if unavailable after all retries, skip the chart
   - matplotlib not installed → `pip install matplotlib --break-system-packages`
   - Invalid JSON → validate the data string with `python -m json.tool`

### ⛔ Chart Data — Zero Tolerance for Fabrication

**Every number in every chart must come from either**:
- Task 2 Excel model (primary source for C1-C5)
- iFind/Yahoo Finance API data (primary source for C6 price data)
- Task 1 Research Document verified data

**Chart data is NOT a place for "representative" or "illustrative" numbers.**
The example calls in this file use placeholder numbers for syntax demonstration ONLY.
**You MUST replace ALL example numbers with real data from the Excel model or API before calling the script.**

**Self-check before calling chart_generator.py**:
- [ ] All numbers come from Excel/API (not from examples in this file)
- [ ] Revenue values match Excel Revenue Model tab
- [ ] Margin values match Excel Income Statement tab
- [ ] Market share data comes from competitive analysis
- [ ] PE band data comes from historical API data
- [ ] Scenario values match Excel Scenarios tab
- [ ] C6 price data comes from real stock/index CSV files
