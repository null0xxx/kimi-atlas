# Equity Report — Phase 5: Quality Assurance

> **This file is read by the agent during Phase 5 when `output_type = EQUITY_REPORT`.**
> All paths are relative to the skill root directory.

---

## 5.1 Automated Pre-Check

Run `scripts/report_validator.py --html [report.html] --json` → structured failure list. Fix validator-reported problems first.

---

## 5.2 Layout Self-Check

| #   | Priority | Check Item                                                            |
| --- | -------- | --------------------------------------------------------------------- |
| 1   | Highest  | Section title orphaned at page bottom                                 |
| 2   | Highest  | Table spans page break                                                |
| 3   | High     | Chart/diagram cut off at page boundary                                |
| 4   | High     | Supply chain diagram not rendered (raw Mermaid text visible or blank) |
| 5   | Medium   | Over-pagination (large white space between sections)                  |
| 6   | Medium   | Chart/table too small to read                                         |
| 7   | Low      | Last page too short (<30% content)                                    |
|     |          |                                                                       |

**Fix tools**: `module-newpage`, `page-break-after: avoid`, remove newpage, enlarge chart, HTML/CSS fallback, condense, expand.

**Max 2 iteration rounds.** Title/table span issues: no acceptance of "minor overage".

---

## ⚠️ 5.3 MANDATORY Quality Gate Loop Rules

> **THIS IS THE MOST CRITICAL SECTION IN THIS FILE.**
> The output quality gate prevents broken, duplicated, or incomplete reports from being delivered. Every single iteration — including "small fixes" — MUST re-run the full check loop before delivery.

### ❌ COMMON FAILURE MODE (READ THIS FIRST)

The most frequent quality failures happen when the agent:
1. Generates initial HTML → runs QA → finds issues
2. Fixes one issue (e.g., adjusts a section, re-renders a chart)
3. **Skips re-running QA** after the fix → delivers broken report
4. Result: HTML duplication, section regressions, broken layout, page count violations

**THIS PATTERN IS ABSOLUTELY PROHIBITED.**

### The Iron Rule: Re-Check After EVERY Change

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ AFTER ANY MODIFICATION TO THE HTML — NO MATTER HOW     │
│  SMALL — YOU MUST RE-RUN THE FULL QA LOOP BEFORE DELIVERY. │
│                                                             │
│  This includes:                                             │
│  • Fixing a chart or table                                 │
│  • Adjusting CSS or page breaks                            │
│  • Correcting a number                                     │
│  • Re-rendering a diagram                                  │
│  • ANY edit to the HTML file                               │
│                                                             │
│  NO EXCEPTIONS. EVER.                                       │
└─────────────────────────────────────────────────────────────┘
```

### Quality Gate Loop (Execute This Exact Sequence)

```
LOOP START (max 3 iterations):
│
├─ Step 1: STRUCTURAL INTEGRITY CHECK (run FIRST every iteration)
│   □ Count occurrences of </body> and </html> in the HTML file
│     → If >1 of either tag: HTML IS DUPLICATED → discard and regenerate
│   □ Verify HTML is well-formed: exactly 1 <html>, 1 <head>, 1 <body>
│
├─ Step 2: GENERATE PDF from the current HTML
│   □ Record the page count immediately
│
├─ Step 3: PAGE COUNT GATE (check IMMEDIATELY after PDF generation)
│   □ Equity report: MUST be ≥25 pages
│   □ If <25 pages: content too thin → return to expand sections
│   □ If >30 pages: investigate for duplication or over-expansion
│
├─ Step 4: A-TIER CHECKS → any failure = prohibit delivery
│   → Locate failed section → repair ONLY that section → return to LOOP START
│
├─ Step 5: B-TIER CHECKS → >3 failures = prohibit delivery
│   → Repair most critical items → return to LOOP START
│
├─ Step 6: C-TIER CHECKS → record failures (informational)
│
├─ Step 7: ALL CHECKS PASS → deliver report
│
LOOP END
```

### Regression Protection
- During repair, only modify failed sections — do not regenerate entire pages
- After modification, re-verify modified items AND adjacent items
- If repair causes previously passed items to fail, **roll back the change** and try an alternative approach
- ❌ Never "fix forward" without re-checking — always return to LOOP START

---

## A-Tier Checks (Any Failure = Prohibit Delivery)

| No. | Check Item | Standard | Check Method |
|------|--------|------|---------|
| A1 | Page Layout | No large white space; content on last page ≥30% | Visual inspection |
| A1b | **Executive Summary** | `.exec-summary` present on page 1 with all 4 items (Thesis, Financials, Valuation, Risks). Each item 1-2 sentences with specific numbers. Cover page does not overflow to page 2. | Visual inspection + content check |
| A2 | Section Sequence | Matches `output/report-layout.md` §4.4 order | Compare with module list |
| A3 | Section Completeness | **All 21 modules present** (Cover through Disclaimer, including Page 2 Data Summary and Glossary). Business Segment Deep Dives has ≥2 sub-sections. | Count modules in HTML |
| A3b | **References Section** | References & Data Sources section present before Disclaimer. Contains ≥10 cited sources with URLs where applicable. No orphan citations. | Check references count and URLs |
| A3c | **Business Segment Depth** | Business Segment Deep Dives module has ≥2 company-specific sub-sections, each with ≥200 words + ≥1 exhibit | Content check |
| A3d | **Exhibit Count** | Report contains ≥15 total exhibits (charts + tables combined) | Count exhibit labels |
| A4 | Chart Alignment | Charts fit within page width, no overflow | Visual inspection |
| A5 | Page Margins | **Top/bottom 18mm, left/right 20mm** consistent | Measure PDF margins |
| A6 | No Scaffold Data | All data from real sources, no fabrication | Spot-check data, verify sources |
| A7 | Data Cross-Validation | Key data verified from dual sources | Check iFind vs. Yahoo Finance |
| A8 | Model Data Tags | Calculated data labeled (especially DCF assumptions) | Check labels |
| A9 | Narrative Consistency | All sections align with Phase 3 core narrative | Read through report |
| A10 | 投资论点综合分析表 | 4 rows with bull/bear arguments + key assumptions + pivot signals | Check table completeness |
| A11 | Short-term Fund Flow | Short-term investment logic includes fund flow / market structure | Check text |
| A12 | Page Balance | No section titles orphaned; charts/tables don't span pages | Validator + visual check |
| A13 | Analysis Brief | Intermediate object generated per `references/output-schema.md` | Check file exists |
| A14 | **DCF Assumptions Documented** | Every DCF projection has documented assumption + basis + risk | Check assumption table |
| A15 | **Sensitivity Base Case** | Base case cell clearly highlighted in every sensitivity matrix | Check matrix formatting |
| A16 | **Cross-Method Synthesis** | Valuation section contains synthesis comparing all methods | Check synthesis section |
| A17 | **Phase 2.7 Completion** | All 6 deep research modules were executed before Phase 4 | Verify analysis brief contains revenue model, TAM, competitive, projections, scenarios, risks |
| A18 | **Scenario Probabilities** | Bull + Base + Bear probabilities sum to 100%; Base is 45-60% | Check scenario section |
| A19 | **HTML Integrity** | Exactly 1 `</body>` and 1 `</html>` in HTML file. No duplicated report content. | `grep -c '</body>' file.html` must return `1` |
| A20 | **Page Count Range** | PDF is ≥25 pages and ≤40 pages. Outside range = likely broken. | Check PDF page count immediately after generation |
| A21 | **Page 2 Data Summary Present** | Page 2 of the Equity Report is the Data Summary page with `.data-summary-page` container, 2-column grid (LEFT 45% / RIGHT 55%), all `.ds-table-dense` tables populated from Task 2 Excel | Inspect page 2 structure in HTML; confirm no placeholders `[…]` remain; confirm forecast columns have `.ds-col-forecast` |
| A22 | **Charts Actually Embedded** | HTML contains ≥ **3** occurrences of `data:image/svg+xml;base64,` (must include C6 Price Performance at minimum). Confirms charts are inlined, not referenced by file path or left as placeholder tokens. | Run `python scripts/embed_charts.py count --html outputs/report.html` — must return ≥3 |

---

## B-Tier Checks (>3 Failures = Prohibit Delivery)

| No. | Check Item | Standard |
|------|--------|------|
| B1 | Page Count | **≥25 pages A4** (matches Phase 0.3 target; 25-40 pages expected) |
| B2 | Data Source Tags | All data tagged with source |
| B3 | Catalyst Calendar | ≥4 events, includes next earnings, ≥2 high-importance |
| B4 | Comparable Companies | 3-5 competitors |
| B5 | 52-Week Stock Chart | Chart renders correctly, benchmark overlay, labels complete |
| B6 | Company Overview | Full paragraph format (not bullet-only), management details |
| B7 | Supply Chain Map | Rendered as embedded SVG or `.chain-wrapper` (≥4 layers use pre-rendered SVG; <4 layers use HTML/CSS flex). **No raw `<pre class="mermaid">` or `<script src="mermaid">` in final HTML** |
| B8 | Earnings Quality | Financial section includes OCF/NI, DuPont, FCF analysis |
| B9 | Consensus Expectation | Valuation section includes sell-side expectations |
| B10 | Competitive Landscape | Industry section has CR concentration, pricing power |
| B11 | **Historical Band** | 5Y PE/PB band summary table with percentile present |
| B12 | **DCF Projection Table** | 5-year FCF projection + equity bridge table present |
| B13 | **Sensitivity Matrix** | At least WACC × Terminal Growth matrix present |
| B14 | **Module Depth** | Each of the 21 mandatory modules has ≥2 substantive paragraphs + ≥1 table/exhibit (where applicable) |
| B15 | **Revenue Decomposition** | Financial section includes segment-level revenue table with volume × price (from `analysis/revenue-model.md`) |
| B16 | **Competitive Depth** | Industry section includes ≥5 named competitors with profile table + market share data (from Research Doc §IV Competitive Landscape) |
| B17 | **TAM/SAM/SOM** | Industry section includes quantified market sizing with sources (from Research Doc §IV TAM/SAM/SOM) |
| B18 | **Projection Assumptions** | Financial section includes margin bridge table + CapEx/WC assumptions (from `analysis/projection-assumptions.md`) |
| B19 | **Risk Count** | Scenario/Risk section includes ≥8 distinct risks across ≥3 categories (from `analysis/risk-framework.md`) |
| B20 | **Scenario Quantification** | Each scenario has specific financial metrics (revenue, margin, EPS, target price), not vague statements (from `analysis/scenario-deep-dive.md`) |

---

## C-Tier Checks (Record Failures)

| No. | Check Item | Standard |
|------|--------|------|
| C1 | Table Count | 12-18 (more than tear sheet due to expanded valuation) |
| C2 | Paragraph Quality | Analysis paragraphs are 3-5 sentences (not just bullets) |
| C3 | Data Timeliness | Latest financials and market data |
| C4 | Compliance Statement | Present in report |
| C5 | Exhibit Numbering | Sequential, no repeats/gaps |
| C6 | Change Highlighting | YoY/QoQ use `.change-positive` / `.change-negative` |
| C7 | English Font | US stock reports use `.report-container-en` |
| C8 | Table of Contents | Present for reports ≥10 pages |
| C9 | **WACC Reasonability** | WACC falls within typical range per `valuation/dcf-and-sensitivity.md` §Part 1 |
| C10 | **Terminal Value Ratio** | Terminal value is 50-70% of EV (flag if >80%) |

---

## Structure Inspection Details

### Report Sections (in order)

```
□ Header: Company name + stock code + key data (no buy/sell ratings)
□ Title + subtitle + core viewpoint (4-6 sentences)
□ [Table of Contents if ≥10 pages]
□ Stock Price + Trading Data: Chart + performance narrative
□ Investment Logic: Full paragraphs, expanded arguments
□ Investment Thesis Table: 4×6 with optional commentary
□ Company Overview: Full paragraphs, management, business model
□ Valuation Analysis:
  □ Comparable company table + premium/discount narrative
  □ Historical valuation band table + percentile narrative
  □ DCF: assumptions + projection + equity bridge
  □ Sensitivity: WACC × Growth matrix (mandatory)
  □ Cross-method synthesis narrative
□ Catalyst Calendar: ≥4 events, impact analysis
□ Industry & Competitive Landscape:
  □ TAM/SAM/SOM sizing table with sources
  □ 5-8 competitor profile table
  □ Market share table (3-year trend)
  □ Competitive positioning narrative (pricing power, moat)
□ Supply Chain: Pre-rendered SVG diagram (no raw Mermaid text, no `<script src="mermaid">`)
□ Upstream/Downstream: Paired analysis
□ Financial Analysis + Projections:
  □ Segment revenue decomposition (volume × price)
  □ Margin bridge (gross + operating)
  □ CapEx/WC assumptions
  □ DuPont decomposition
  □ FCF analysis + earnings quality
□ [Expansion Modules if selected — each ≥2 paragraphs + ≥1 exhibit]
□ Scenario Analysis + Risk:
  □ Bull/Base/Bear with specific metrics + probability weights
  □ Probability-weighted target calculation
  □ Scenario comparison table
  □ 8-12 risks across 4 categories with P×I scoring
  □ Risk-reward synthesis
□ Compliance Disclaimer
```

---

## Special Check Details

### Stock Chart
Same as tear-sheet QA — must use `scripts/stock_chart_generator.py`, base64 ≥20,000 chars, correct benchmark.

### 投资逻辑
Same as tear-sheet QA — left short-term with 利空, right long-term with risks, thesis table complete.

### Catalyst Calendar
Same requirements: ≥4 events, next earnings, ≥2 high-importance.

### Supply Chain
Same requirements: Pre-rendered SVG default (via rendering cascade), ≥4 layers, target company nodes highlighted. No raw Mermaid text or Mermaid JS imports in HTML.

### Valuation Section (L1 vs L2 Checklist)

**L2 (Full Version — DCF + Comps + Historical + Sensitivity)**:
```
□ DCF: WACC calculation documented with all components
□ DCF: 5-year FCF projection with revenue/margin/CapEx assumptions
□ DCF: Terminal value method stated (Gordon Growth or Exit Multiple)
□ DCF: Equity bridge complete (EV → Net Debt → Equity → Per Share)
□ Historical Band: ≥2 metrics (PE + PB minimum)
□ Historical Band: Current percentile calculated and interpreted
□ Sensitivity: Base case highlighted with bold or .base-case class
□ Sensitivity: Ranges are symmetric and use reasonable step sizes
□ Synthesis: DCF + Comps + Historical all compared, convergence/divergence noted
□ Synthesis: Final valuation judgment stated
□ Number cross-checks: ≥10 numbers verified against Excel model
```

**L1 (Streamlined Version — Comps + Consensus only)**:
```
□ Comparable Company Table: 3-5 peers with real data (iFind/Yahoo Finance)
□ Comps: Statistical summary (Max/75th/Median/25th/Min) present
□ Comps: Premium/discount narrative with drivers
□ Scenario Table: Bull/Base/Bear with assumptions and implied prices
□ Synthesis: Comps range + consensus target compared
□ Synthesis: Final valuation judgment stated
□ ⛔ DCF/Historical Band/Sensitivity: NOT present (correct for L1)
□ Number cross-checks: ≥5 numbers verified against research document
```

---

## Data Cross-Validation Reference

| Data Type | Primary Source | Verification Source | Acceptable Variance |
|----------|------|--------|-----------|
| Revenue / Net Income | iFind | Yahoo Finance | <5% |
| PE / PB | iFind | Yahoo Finance | <10% |
| Earnings Forecast | iFind | — | — |
| Business Breakdown | iFind | Web Search | <10% |
| Industry Data | 财新 | Web Search | <15% |
| Next Earnings Date | Web Search | Exchange Calendar | No variance |
| Beta | iFind | Yahoo Finance | <20% |
| Risk-Free Rate | Web Search | Central bank data | No variance |

---

## Common Problem Troubleshooting

| Problem | Likely Cause | Solution |
|------|----------|---------|
| Report too short (<25 pages) | Phase 2.7 not fully executed | Return to Phase 2.7, complete all 6 sub-steps with minimum word counts |
| Industry section thin | Competitive deep dive / TAM not integrated | Expand Research Doc §IV (Industry Overview, TAM/SAM/SOM, Competitive Landscape, Entry Barriers) and re-render |
| Financial section lacks depth | Revenue model / projection assumptions not integrated | Incorporate segment tables from `analysis/revenue-model.md` and margin bridge from `analysis/projection-assumptions.md` |
| Scenario section vague | Scenarios lack specific metrics | Each scenario needs exact revenue, margin, EPS, target price per `analysis/scenario-deep-dive.md` |
| Risk list too short (<8 risks) | Risk framework not fully applied | Follow 4-category structure from `analysis/risk-framework.md` |
| Report too long (>20 pages) | Over-expanded modules | Tighten prose, merge related paragraphs, move secondary detail to footnotes |
| Valuation section disjointed | Methods not cross-referenced | Add synthesis narrative comparing all results |
| DCF value wildly different from market | Unreasonable assumptions | Check WACC range, terminal growth, margin projection |
| Sensitivity matrix all same color | Too-narrow variable ranges | Widen ranges per `valuation/dcf-and-sensitivity.md` §Part 3 guidelines |
| Section titles orphaned | Large section at page bottom | Add `page-break-before: always` |
| Supply chain diagram blank/text | Raw Mermaid not pre-rendered, or render method failed | Re-run Playwright pre-render per `modules/industry-chain.md` §Rendering Pipeline (Playwright → HTML/CSS flex fallback) |
| Raw `<pre class="mermaid">` in HTML | Mermaid code not pre-rendered | Must pre-render to SVG before embedding. Never embed raw Mermaid code in PDF-destined HTML |
| Chart not rendering in PDF | base64 SVG not embedded correctly | Verify `<img src="data:image/svg+xml;base64,...">` is complete |
| Chart data doesn't match table | Data extracted incorrectly | Cross-check chart JSON input against Analysis Brief |

---

## Chart Quality Checks (EQUITY REPORT ONLY)

> **This section applies ONLY to equity reports.** Tear sheets do not include data charts.

### B-Tier Chart Checks (count toward B-tier failure total)

| No. | Check Item | Standard |
|------|--------|------|
| B21 | **Revenue Segment Chart** | C1 present in Financial Analysis section, segments match revenue table, forecast bars hatched |
| B22 | **Margin Trends Chart** | C2 present in Financial Analysis section, 3 lines (gross/operating/net), forecast period dashed |
| B23 | **Market Share Chart** | C3 present in Industry section, target company highlighted, shares sum to ~100% |
| B24 | **PE Band Chart** | C4 present in Valuation section, current value marked, mean/SD bands visible |
| B25 | **Scenario Chart** | C5 present in Scenario section, 3 scenarios with correct colors (green/blue/red) |
| B26 | **Price Performance Chart + Table** | C6 Price Performance (rebased line) present on Page 2 left column, directly above `.perf-table`. Perf-table has 6 rows (1M/3M/6M/YTD/1Y/3Y) with Absolute and Rel. to Index columns both populated. **Data must come from real API (iFind/Yahoo Finance) — ⛔ zero tolerance for mock/simulated price data.** |
| B27 | **Glossary Section** | `.glossary-section` present (after Disclaimer or in appendix). Contains 6-12 sector-relevant terms in 2-column `.glossary-grid`. No orphan bracket placeholders. |

### C-Tier Chart Checks (record only)

| No. | Check Item | Standard |
|------|--------|------|
| C11 | **Chart-Table Consistency** | Chart data matches the numbers in its adjacent data table |
| C12 | **Chart Exhibit Labels** | All 5 charts have sequential exhibit labels and source lines |
| C13 | **Chart Page Placement** | No chart is split across pages; exhibit label not orphaned from chart |

### Chart Troubleshooting

| Problem | Likely Cause | Solution |
|------|----------|---------|
| Chart missing from PDF | `chart_generator.py` failed or base64 not embedded | Re-run script, check error output, verify SVG base64 in HTML |
| Chart too small in PDF | SVG viewBox not scaled properly | Ensure `max-width: 100%` on the `<img>` tag |
| Chart colors wrong | Wrong chart_type parameter | Verify `--chart_type` matches the intended chart |
| Pie chart labels overlap | Too many small slices | Slices <3% should be grouped into "Others" |
| Scenario bars unreadable | Scale mismatch across metrics | Script auto-switches to 2×2 subplot layout if range >10x |
| matplotlib not installed | Missing dependency | `pip install matplotlib numpy --break-system-packages` |
