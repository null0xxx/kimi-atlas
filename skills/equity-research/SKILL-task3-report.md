---
name: equity-report-task3-report
description: "Task 3 of equity report workflow. Generates the final PDF report. L2 mode reads Task 1 research doc + Task 2 Excel model + Task 2 valuation analysis. L1 mode reads Task 1 research doc only (no Excel). This file is the entry point — do NOT read SKILL.md, analysis frameworks, or valuation methodology files."
---

# Task 3: Report Generation (Final Step)

> **This is the entry point for Task 3 of the equity report workflow.**
> This is the final step — whether you're in L2 (3-Task) or L1 (2-Task) mode.
>
> | Mode | Inputs Required |
> |------|----------------|
> | **L2 (Full)** | Task 1 Research Document + Task 2 Excel Model + Task 2 Valuation Analysis |
> | **L1 (Streamlined)** | Task 1 Research Document only |

---

## ⚠️ CRITICAL RULES

### DO NOT TAKE SHORTCUTS
- ✅ Final PDF must be **≥25 pages** — this is an in-depth institutional equity report, NOT an expanded tear sheet
- ✅ Write every section with **full depth** — each major module should span at least 1.5-2 pages
- ✅ **L2**: ALL financial numbers extracted from Task 2 Excel model via openpyxl; ≥10 numbers cross-checked
- ✅ **L1**: Financial numbers extracted from Task 1 Research Document; valuation section uses comparable-company method (no DCF/sensitivity/historical band)
- ✅ Generate the required charts AND **additional charts** — aim for ≥15 total exhibits (L2) or ≥10 (L1)
- ✅ C6 stock chart: data from real market APIs ONLY (iFind/Yahoo Finance). **If price data unavailable → skip, insert note. ⛔ Never use mock/simulated price data.**
- ✅ **Page 2 is reserved for the Data Summary page** — mandatory 2-column dense financial summary (see `output/report-layout.md`)
- ✅ **Actively research** during report writing — web search for each major module to enrich content
- ✅ Create **company-specific sub-sections** (Business Segment Deep Dives: 2-4 sub-sections)
- ✅ Include a **References & Data Sources** section listing ALL sources with URLs
- ✅ Include a **Glossary** section with 6-12 sector-relevant terms (see `output/report-layout.md`)
- ✅ Run the **chart-count verification**: `python scripts/embed_charts.py count --html outputs/report.html` must return ≥3
- ❌ Do not say "see financial model for details" — EXTRACT AND INCLUDE the details
- ❌ Do not skip any module — ALL modules are mandatory (L1: ~18 modules, L2: 21 modules)
- ❌ Do NOT include any analyst byline. Do NOT copy placeholder tickers.

### L1 vs L2 Module Differences

| Module | L2 | L1 |
|--------|-----|-----|
| DCF Model Section | ✅ Full DCF with WACC/FCF/Terminal Value | ❌ Skip. Use comps-based valuation instead |
| Sensitivity Matrix | ✅ Full WACC × Growth matrix | ❌ Skip. Include simple scenario table |
| Historical Valuation Band | ✅ 5-year PE/PB band with percentiles | ❌ Skip |
| Cross-Method Synthesis | ✅ DCF + Comps + Historical combined | ✅ Comps + Consensus only |
| Financial data source | Task 2 Excel (openpyxl) | Task 1 Research Document |
| Charts C1-C5 | ✅ From Excel model | ✅ From research document data |
| Number cross-checks | ≥10 vs Excel | ≥5 vs research doc |

### PDF Skill Rules
- ✅ Use the environment PDF skill for HTML → PDF conversion
- ❌ **DO NOT let the PDF skill generate a cover page.** Our report has its own cover page design in `output/report-layout.md`.
- ❌ **DO NOT let the PDF skill add headers, footers, or front matter** not specified in our layout file.

### ⚠️ MANDATORY: Re-Check After EVERY HTML Edit
- ✅ After ANY change to the HTML, re-run the FULL QA loop (see `output/report-qa.md` §5.3)
- ✅ Before every PDF generation: verify HTML has exactly 1 `</body>` and 1 `</html>`
- ✅ After every PDF generation: check page count IMMEDIATELY — if <25 or >40 pages, something is wrong
- ❌ **NEVER deliver a report without re-running QA after your last edit**

---

## Prerequisites

### Automatic File Loading (Session Context)

When the user says "下一步"/"继续"/"continue" to enter Task 3, all previous files exist in the **current session context**. **Do NOT ask the user to provide files.**

**Auto-locate files** (search session for the most recent matching files):

| Mode | Required File | Search Pattern |
|------|--------------|----------------|
| **L1 & L2** | Task 1 Research Document | `*_Research_Document_*.md` |
| **L2 only** | Task 2 Financial Model | `*_Financial_Model_*.xlsx` |
| **L2 only** | Task 2 Valuation Analysis | `*_Valuation_Analysis_*.md` |
| **L1 & L2** | Stock chart SVG | Path from research doc metadata |
| **L1 & L2** | Stock price CSV + Benchmark CSV | From Task 1 assets |

**If files cannot be found in session**: Ask the user to confirm filenames. Do NOT start Task 3 without required inputs.

Also verify these asset files exist (from Task 1):
- Stock chart SVG (path in research document metadata)
- Stock price CSV + benchmark CSV

---

## Files to Read (in this order)

| # | File | Purpose | L1 | L2 |
|---|------|---------|-----|-----|
| 1 | Task 1 Research Document | Narrative content, six-dimension analysis | ✅ | ✅ |
| 2 | Task 2 Valuation Analysis (.md) | Rating, target price, DCF summary | ❌ | ✅ |
| 3 | `output/report-layout.md` | HTML structure, module order, CSS, L1/L2 layout differences | ✅ | ✅ |
| 4 | `modules/equity-report-charts.md` | Chart specs + embedding protocol | ✅ | ✅ |
| 5 | `modules/tables.md` | Table templates (P2 Dense, Growth & Margins, etc.) | ✅ | ✅ |
| 6 | `output/report-qa.md` | QA checklist (A/B/C tier, with L1/L2 variants) | ✅ | ✅ |

**Task 2 Financial Model (.xlsx)** (L2 only): Read via Python/openpyxl during report generation. Do NOT read it all upfront — read specific tabs as needed for each module.

---

## Step 1: Extract Metadata

From the Research Document's `## Task Handoff Metadata` section, extract:

| Field | Used For |
|-------|----------|
| `report_language` | CSS class, module title language |
| `css_container_class` | `.report-container` or `.report-container report-container-en` |
| `market` | Disclaimer text |
| `ticker` / `company_name` | Running header, cover page |
| `page_target` | QA page count validation |
| `module_count` | L2: all 21 modules mandatory. L1: 18 mandatory modules — DCF Model, Sensitivity Matrix, and Historical Valuation Band are skipped because the Excel model is not produced in L1. |
| `current_price` | Cover sidebar |

From the Valuation Analysis, extract:
| Field | Used For |
|-------|----------|
| Rating (BUY/HOLD/SELL) | Cover page badge |
| Target Price | Cover page + valuation section |
| Probability-Weighted Price | Scenario section |

---

## Step 2: Read the Financial Model

Use Python to read key data from the Excel file:

```python
import openpyxl
wb = openpyxl.load_workbook('{model_path}', data_only=True)

# Extract data needed for report modules:
# 1. Income Statement tab → Financial Analysis module tables
# 2. Revenue Model tab → Revenue segment chart (C1)
# 3. DCF tab → DCF section tables
# 4. Comps tab → Comparable companies table
# 5. Sensitivity tab → Sensitivity matrix
# 6. Scenarios tab → Scenario comparison table + chart (C5)
# 7. Operating Drivers tab → Key assumptions for margin/growth narrative
```

**CRITICAL RULE**: Every financial number in the report MUST come from the Excel model. Do NOT type numbers from memory or the research document's §VI. Extract from Excel to guarantee consistency.

---

## Step 3: Generate Report HTML

Read `output/report-layout.md` NOW and follow it exactly.

### Module Generation Order (L2: 21 modules · L1: 18 modules)

> L1 mode skips three valuation modules that depend on the Excel model: **DCF Model**, **Sensitivity Matrix**, and **Historical Valuation Band**. All other modules apply to both L1 and L2.

| # | Module | Content Source | Data Source |
|---|--------|---------------|-------------|
| 0 | Cover Page (`.cover-split` with `.price-target-bar` + `.key-data-grid`) | Research Doc §I + Valuation Analysis rating/target | Excel: key financial metrics |
| 0b | Executive Summary (`.exec-summary`) | Distilled from all sections | Excel: headline metrics |
| **0c** | **Page 2 Data Summary Page** (`.data-summary-page`, 2-col grid) | Ratios/Valuation + Growth/Margins + C6 Price Perf + perf-table (LEFT) + IS/BS/CF (RIGHT) | Excel: all core tabs + **real market price data for C6 (strictly no mock)** |
| 0d | TOC + Figure Index | Auto-generated from module list | — |
| 1 | **Stock Price & Market Performance** | **Custom matplotlib/plotly chart** (NOT tear sheet script) + narrative | Stock CSV + Benchmark CSV |
| 2 | **Investment Thesis & Key Debates** | Research Doc §I, §II + **web search for latest developments** | — |
| 3 | Investment Thesis Comprehensive Table | Research Doc §VIII | — |
| 4 | Company Overview & Business Model | Research Doc §III + **web search** | — |
| 5 | **Business Segment Deep Dives** (2-4 sub-sections) | Research Doc + **extensive web search per segment** | Excel: Revenue Model tab |
| 6 | Industry & Competitive Landscape | Research Doc §IV (Competitive Landscape + Entry Barriers) + **web search** | — |
| 7 | TAM / Market Sizing | Research Doc §IV (TAM/SAM/SOM + Market Opportunity Narrative) + **web search** | — |
| 8 | Supply Chain | Research Doc §V (Mermaid → SVG) | — |
| 9 | Upstream/Downstream Analysis | Research Doc §V | — |
| 10 | Financial Analysis & Projections | Research Doc §VII + **Excel model data** + **web search for comps** | Excel: IS, Revenue Model, CF, Operating Drivers |
| 11 | Valuation Analysis | Valuation Analysis §II-§V | Excel: DCF, Comps, Sensitivity tabs |
| 12 | Management & Governance | Research Doc §III + **web search** | — |
| 13 | ESG & Sustainability | **Web search** (ESG data, sustainability reports) | — |
| 14 | Scenario Analysis | Valuation Analysis §VI | Excel: Scenarios tab |
| 15 | Risk Assessment | Research Doc §X + `analysis/risk-framework.md` | — |
| 16 | Shareholder & Capital Structure | **Web search** (13F data, insider trades) | — |
| 17 | **References & Data Sources** | Compiled from all modules | — |
| **18** | **Glossary** (`.glossary-section`, 6-12 sector-filtered terms) | Sector term bank from `output/report-layout.md` | — |
| 19 | Compliance Disclaimer | Market-specific boilerplate | — |

> **⚠️ RESEARCH DURING REPORT WRITING**: For modules marked with **web search**, the agent MUST perform at least 1 web search to find the latest data. The Task 1/2 deliverables provide a framework — the agent should actively expand and deepen content beyond what they contain. There is NO cap on web searches. See `output/report-layout.md` §4.4.3 for full rules.

### Key Extraction Patterns

**For tables from Excel** (Financial statements, DCF, Comps, Sensitivity):
```python
# Read the Excel tab and convert to HTML table
ws = wb['Income Statement']
# Read headers from row 3
# Read data from rows 5+
# Generate <table class="report-table"> HTML with proper formatting
```

**For narrative from Research Document**:
- Read the relevant section
- Reformat into `.kw-paragraph` style (bold-keyword + colon + body)
- Add exhibit labels and numbers sequentially

**For Sensitivity Matrix** (from Excel):
```html
<table class="sensitivity-matrix">
  <!-- Read Sensitivity tab, find base case cell, apply .base-case class -->
</table>
```

### Supply Chain Rendering

The research document §V contains Mermaid code. Render using the sandbox-optimized Playwright scheme (see `modules/industry-chain.md` §Rendering Pipeline):
1. **Playwright** (primary): Use sandbox browser toolkit (`browser_visit` → screenshot → base64 PNG)
2. **HTML/CSS flex** (fallback): When Playwright fails after 1 retry

**CRITICAL**: No raw Mermaid in HTML. No `<script src="mermaid.min.js">`. PDF doesn't execute JS. Must pre-render to base64 PNG via Playwright.

---

## Step 4: Generate Charts (C1-C6) — Use the MANDATORY Embedding Protocol

Read `modules/equity-report-charts.md` §HTML Embedding for the **MANDATORY 4-STEP PROTOCOL**. Skipping any step causes 0 charts to appear in the PDF (known failure mode).

**Key change from old workflow**: Chart data comes from the **Excel model**, not from a markdown brief.

| Chart | Type | Excel Source | Tab to Read |
|-------|------|-------------|-------------|
| C1: Revenue by Segment | Stacked Bar | Revenue Model tab | Segment rows, FY-2 through FY+2E |
| C2: Margin Trends | Multi-Line | Income Statement tab | Gross/Op/Net margin rows |
| C3: Market Share | Pie | Research Doc §IV competitor table | — |
| C4: Historical PE Band | Line+Shaded | Research Doc or external data | May need API fetch |
| C5: Scenario Comparison | Grouped Bar | Scenarios tab | Revenue/EPS/Price by scenario |
| **C6: Price Performance (Rebased)** | Rebased Line | **Real market data ONLY** | iFind/Yahoo Finance 12M daily closes. **⛔ Zero tolerance for mock/simulated price data.** |

### Preferred Path — Use `scripts/embed_charts.py render`

```bash
python scripts/embed_charts.py render --specs '[
  {"id":"C1","chart_type":"revenue_segment","data":{...},"output":"outputs/c1.svg"},
  {"id":"C2","chart_type":"margin_trends","data":{...},"output":"outputs/c2.svg"},
  {"id":"C3","chart_type":"market_share","data":{...},"output":"outputs/c3.svg"},
  {"id":"C4","chart_type":"pe_band_simple","data":{...},"output":"outputs/c4.svg"},
  {"id":"C5","chart_type":"scenario_comparison","data":{...},"output":"outputs/c5.svg"},
  {"id":"C6","chart_type":"price_rebased","data":{...},"output":"outputs/c6.svg"}
]' --out-dir outputs/
```

This wrapper (1) runs `chart_generator.py`, (2) reads the SVG file, (3) base64-encodes, (4) returns `{id, base64, bytes_len}` per chart. You then insert each `base64` string into the `<img src="data:image/svg+xml;base64,...">` tag in the HTML.

### Alternative — Manual 4 steps

Only if the wrapper is unavailable, follow the explicit 4 steps in `modules/equity-report-charts.md` §HTML Embedding. The `--json` flag alone does NOT return base64 — you MUST read the SVG file and base64-encode it yourself.

### Exhibit Labels

Each chart gets an `.exhibit-label` above it and a `.chart-source` / `.data-source` below it. Numbering is sequential across tables + charts (C6 is typically Exhibit 3-5 on Page 2 depending on table order).

---

## Step 5: Inject CSS and Generate PDF

### CSS Injection
Read `output/report.css` and inject into HTML `<style>` block. Use the `css_container_class` from metadata.

### PDF Generation
```python
# WeasyPrint approach
from weasyprint import HTML
html_content = open('report.html').read()
HTML(string=html_content).write_pdf('report.pdf')
```

Or Playwright approach:
```python
page.emulate_media(media='print')
# Inject: .report-container { padding: 0 !important; }
# @page { margin: 18mm 20mm; }
```

### Post-Generation Checks
- Page count within `page_target` range
- If too few: expand thin modules
- If too many: compress disclaimer, tighten scenarios
- If last page has ≤5 lines: merge content upward

---

## Step 6: Quality Assurance

Read `output/report-qa.md` for full checklist.

### 6.1 Run Automated Validator
```bash
python scripts/report_validator.py --html report.html --mode equity_report --json
```

### 6.1a Chart-Count Verification (A22) — MANDATORY
```bash
python scripts/embed_charts.py count --html outputs/report.html
```
Must return `count >= 3` (typical: 6 charts for a full equity report). Zero charts = the embedding protocol was skipped (see Step 4).

### 6.2 Cross-Check Numbers Against Excel

This is the **most important QA step** in the 3-Task architecture. Spot-check at least 10 numbers:

| Check | Report Location | Excel Location | Must Match |
|-------|----------------|----------------|------------|
| Latest Revenue | Cover sidebar | IS tab, FY0 | Exact |
| FY+1 Revenue estimate | Earnings forecast table | IS tab, FY+1E | Exact |
| FY+1 EPS estimate | Earnings forecast table | IS tab, FY+1E EPS | Exact |
| DCF price per share | Valuation section | DCF tab, equity/share | Exact |
| WACC | DCF narrative | DCF tab, WACC cell | Exact |
| Comps median PE | Comps table | Comps tab, median row | Exact |
| Sensitivity center cell | Sensitivity matrix | Sensitivity tab, center | Exact |
| Bull case price | Scenario section | Scenarios tab, Bull | Exact |
| Base case price | Scenario section | Scenarios tab, Base | Exact |
| Bear case price | Scenario section | Scenarios tab, Bear | Exact |

**If ANY number doesn't match**: Fix the report HTML. The Excel model is the source of truth.

### 6.3 Manual QA (Key Items)

**A-tier (Must Pass)**:
- [ ] Cover has rating badge + target price (using `.price-target-bar` Current/Target/Upside)
- [ ] Cover has `.key-data-grid` (Market / Return / Valuation groups + Earnings Forecast)
- [ ] Executive Summary present with all 4 items (Thesis, Financials, Valuation, Risks)
- [ ] Cover page (cover-split + exec-summary) fits on page 1 — no overflow
- [ ] **Page 2 Data Summary present** (A21): 2-column grid, all `.ds-table-dense` populated, forecast columns shaded
- [ ] All financial tables populated (no blank cells, no orphan `[…]` placeholders)
- [ ] DCF section: WACC + FCF + Terminal + Equity Bridge all present
- [ ] Sensitivity matrix: `.base-case` highlighted
- [ ] Cross-method synthesis narrative present
- [ ] ≥15 total exhibits (charts + tables)
- [ ] Supply chain is SVG (not raw Mermaid)
- [ ] Stock chart is custom matplotlib/plotly with benchmark overlay (NOT tear sheet script)
- [ ] **Chart-count ≥ 3** (A22) — verified with `embed_charts.py count`
- [ ] Number cross-check: ≥10 numbers verified against Excel
- [ ] All required modules present (L2: 21 modules · L1: 18 modules — Cover through Disclaimer, including Page 2 Data Summary and Glossary; L1 omits DCF Model, Sensitivity Matrix, Historical Valuation Band)
- [ ] Business Segment Deep Dives has ≥2 company-specific sub-sections
- [ ] References & Data Sources section present with ≥10 cited sources

**B-tier (Should Pass)**:
- [ ] Running headers/footers on non-cover pages
- [ ] Exhibit numbering sequential
- [ ] All 6 required charts (C1-C6, including C6 Price Performance on Page 2) present + additional charts
- [ ] Glossary section present (B27) with 6-12 sector-relevant terms in 2-column grid
- [ ] TOC present with all required modules listed (21 for L2, 18 for L1)

---

## Step 7: Final Delivery — ALL Deliverables

> ⚠️ **Deliver ALL project deliverables together**, not just the PDF. The user should receive the complete research package in one handoff.

### 7.1 Pre-Delivery Checklist

Before delivering, confirm ALL items pass:

| # | Deliverable | QA Status | Source |
|---|-------------|-----------|--------|
| 1 | **Equity Report PDF** (≥25 pages) | All A-tier checks passed, B-tier ≤3 failures | This task (Step 6) |
| 2 | **Equity Report HTML** (source file) | HTML integrity verified (1× `</body>`, 1× `</html>`) | This task (Step 6) |
| 3 | **Financial Model (.xlsx)** | All 10 integrity checks passed (BS balance, cash tie-out, revenue tie, etc.) | Task 2 output — re-verify the file still opens and key numbers match |
| 4 | **Valuation Analysis (.md)** | Target price, DCF, comps range, scenarios all present | Task 2 output |
| 5 | **Research Document (.md)** | ≥6,000 words, all sections complete | Task 1 output |

**If ANY deliverable fails its check**: Fix it before delivery. Do NOT deliver a partial package.

### 7.2 Deliver to User

Provide ALL files with links:

```
📋 Complete Equity Research Package for {Company} ({Ticker}):

1. 📄 Equity Report (PDF) — [link]
   {page_count} pages, {exhibit_count} exhibits, {chart_count} charts

2. 📊 Financial Model (Excel) — [link]
   {tab_count} tabs, {projection_years}Y projections, all integrity checks passed

3. 📝 Valuation Analysis — [link]
   Rating: {rating}, Target: ${target_price} ({upside}% upside/downside)

4. 📑 Research Document — [link]
   {word_count} words, comprehensive analysis

QA Summary:
- Report: A-tier ✅ all passed, B-tier ✅ {b_failures} failures
- Excel: 10/10 integrity checks ✅
- Numbers cross-check: {cross_check_count}/10 verified ✅
```

### 7.3 STOP

**Do not continue.** All 3 Tasks of the equity report workflow are complete. The user now has the full research package.
