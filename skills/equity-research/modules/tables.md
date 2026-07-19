# Table Specification / 表格通用规范

## Table Design Principles

1. **Simple Professional**: Remove flashy decoration, focus on data presentation
2. **Compact Efficient**: Maximize information density, reduce whitespace
3. **Hierarchical Clear**: Headers stand out, data clear
4. **Alignment Standard**: Numbers right-align (`.col-number`), text left-align (`.col-text`), labels center (`.col-center`)
5. **Column Width Smart**: Browser auto-allocates column width per content, no manual percentage specification needed
6. **Page-break Friendly**: Table `page-break-inside: avoid` already set globally in `output/tearsheet.css` — tables and charts never split across pages; their preceding titles follow them to the next page automatically

### Column Width Control Standard

CSS already sets `table-layout: auto`, browser auto-allocates per cell content. **No need manually specify `<colgroup>` percentage width**, unless special layout needed.

**Available alignment classes** (only control alignment, don't force width):
| class | Function | Applicable Scenario |
|-------|----------|---------------------|
| `.col-narrow` | Left-align, limit max-width | Numbers, dates, short labels |
| `.col-number` | Right-align, monospace font | Number columns (PE, amounts, etc) |
| `.col-text` | Left-align | Normal text columns (company names, metric names) |
| `.col-wide` | Left-align, allow wrap | Long text columns (impact analysis, judgment description) |
| `.col-center` | Center-align | Status marks, importance level |

**Smart Column Width Principle**:
- Browser auto-adjusts per content, narrow content → narrow column, wide content → wide column
- If column content too long, browser auto wraps rather than truncates
- If one row >6 columns, consider split into two tables or streamline columns
- Only when auto-allocation unsatisfactory (e.g. some column over-compressed), use `<colgroup>` manual specification

---

## Common Table Templates

### Financial Data Table

```markdown
| Metric | 2022A | 2023A | 2024A | 2025E | 2026E |
|--------|-------|-------|-------|-------|-------|
| Revenue (¥bn) | 1,200 | 1,350 | 1,500 | 1,680 | 1,890 |
| YoY (%) | 8.5 | 12.5 | 11.1 | 12.0 | 12.5 |
| Net Profit (¥bn) | 150 | 180 | 210 | 245 | 285 |
| YoY (%) | 10.2 | 20.0 | 16.7 | 16.7 | 16.3 |
| EPS (¥) | 2.50 | 3.00 | 3.50 | 4.08 | 4.75 |
| PE (x) | 25.0 | 20.8 | 17.9 | 15.3 | 13.2 |

*Data Source: iFind, as of YYYY-MM-DD*
```

### Financial Metric Analysis Table

```markdown
| Metric Category | Metric | 2022A | 2023A | 2024A | Industry Avg |
|---|---|---|---|---|---|
| Profitability | Gross Margin (%) | 35.0 | 36.5 | 38.0 | 35.0 |
| | Net Margin (%) | 12.5 | 13.3 | 14.0 | 12.0 |
| | ROE (%) | 15.0 | 16.5 | 18.0 | 15.0 |
| Growth | Revenue Growth (%) | 8.5 | 12.5 | 11.1 | 10.0 |
| Solvency | Asset-Liability Ratio (%) | 45.0 | 42.0 | 40.0 | 45.0 |
| | Current Ratio | 1.5 | 1.6 | 1.8 | 1.5 |

*Data Source: iFind, 2024 Annual Report*
```

### Scenario Analysis and Risk Disclaimer Layout

**Layout**: Left-Right Dual Box, **Scenario Analysis left 60% / Risk Disclaimer right 40%** (`.scenario-box` / `.risk-box`)

```html
<div class="module-row">
  <div class="section-title">Scenario Analysis and Risk Disclaimer</div>
  <div class="two-column">
    <div class="box box-primary scenario-box">
      <div class="box-title">Three Scenario Analysis</div>
      <!-- Scenario analysis table -->
    </div>
    <div class="box box-danger risk-box">
      <div class="box-title">Risk Disclaimer</div>
      <!-- Risk disclaimer table -->
    </div>
  </div>
</div>
```

> Scenario analysis contains 6 columns (Scenario/Assumption/Revenue/Net Profit/PE/Market Cap), requires wider space; risk disclaimer 4 columns, 40% sufficient.

### Scenario Analysis Table

```markdown
| Scenario | Assumption | 2025E Revenue (¥bn) | 2025E Net Profit (¥bn) | Target PE | Implied Market Cap (¥bn) |
|---|---|---|---|---|---|
| Optimistic | Demand exceeds expectations, gross margin improves | 1,800 | 300 | 18x | 5,400 |
| Base | Demand meets expectations | 1,680 | 245 | 15x | 3,675 |
| Pessimistic | Demand falls short, competition intensifies | 1,500 | 200 | 12x | 2,400 |

*Data Source: Model estimates, based on different assumptions*
```

### Risk Disclaimer Table

```markdown
| Risk Type | Risk Description | Impact Level | Probability |
|---|---|---|---|
| Demand Risk | Downstream demand falls short | High | Medium |
| Competition Risk | Industry competition intensifies, price war | High | Medium |
| Policy Risk | Industry policy adjustments | Medium | Low |
| Raw Material Risk | Raw material price increases | Medium | Medium |

*Data Source: Research Analysis*
```

---

## Data Source Annotation Standard (Sole Source)

### Annotation Format

```markdown
*Data Source: [Data Source], [Date/Period]*
```

### Annotation Examples

| Data Type | Annotation Example |
|---|---|
| Financial Data | *Data Source: iFind, 2024 Annual Report* |
| Valuation Metrics | *Data Source: iFind, as of YYYY-MM-DD* |
| Market Data | *Data Source: iFind, Real-time Market* |
| Industry Data | *Data Source: 财新, Web Search* |
| Earnings Forecast | *Data Source: iFind, Last 30-day Consensus* |
| Model Calculation | *Data Source: Model Calculation, based on [Assumptions]* |

### Model Calculation Data Annotation

```markdown
| Metric | 2026E |
|---|---|
| Revenue (¥bn) | 1,890* |

*Data Source: Model Calculation, based on past 3-year CAGR 12% assumption*
```

---

## Table Optimization Tips

**When space insufficient**: Streamline columns → Reduce font size (8pt→7pt) → Reduce padding → Use abbreviations

**When content excessive**: Split tables → Dataviz

---

## Dense Table Variant — P2 Data Summary Page (MANDATORY for Equity Report)

Page 2 of the Equity Report is a **dense two-column Data Summary page** (see `report-layout.md` P2 template). All tables inside it MUST use `.ds-table-dense` for 8.5pt condensed rendering. This is only for the Equity Report mode (not Tear Sheet).

### P2 Dense Table — Ratios & Valuation (LEFT column, 45% width)

```html
<div class="exhibit-label">
  <span class="exhibit-number">[Exhibit N:]</span>
  <span class="exhibit-desc">[Ratios & Valuation]</span>
</div>
<table class="report-table-minimal ds-table-dense">
  <thead>
    <tr>
      <th class="col-text">[Metric]</th>
      <th>[FY-2]</th><th>[FY-1]</th><th>[FY0A]</th>
      <th class="ds-col-forecast">[FY+1E]</th>
      <th class="ds-col-forecast">[FY+2E]</th>
      <th class="ds-col-forecast">[FY+3E]</th>
    </tr>
  </thead>
  <tbody>
    <tr><td class="col-text">EPS ([currency])</td><td class="col-number">[x.xx]</td><td class="col-number">[x.xx]</td><td class="col-number">[x.xx]</td><td class="col-number ds-col-forecast">[x.xx]</td><td class="col-number ds-col-forecast">[x.xx]</td><td class="col-number ds-col-forecast">[x.xx]</td></tr>
    <tr><td class="col-text">P/E (x)</td><td class="col-number">[xx.x]</td><td class="col-number">[xx.x]</td><td class="col-number">[xx.x]</td><td class="col-number ds-col-forecast">[xx.x]</td><td class="col-number ds-col-forecast">[xx.x]</td><td class="col-number ds-col-forecast">[xx.x]</td></tr>
    <tr><td class="col-text">EV/EBITDA (x)</td><td class="col-number">[xx.x]</td><td class="col-number">[xx.x]</td><td class="col-number">[xx.x]</td><td class="col-number ds-col-forecast">[xx.x]</td><td class="col-number ds-col-forecast">[xx.x]</td><td class="col-number ds-col-forecast">[xx.x]</td></tr>
    <tr><td class="col-text">P/B (x)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">Dividend Yield (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">FCF Yield (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
  </tbody>
</table>
<div class="data-source">[iFind / Company filings, as of YYYY-MM-DD]</div>
```

### P2 Dense Table — Growth & Margins (LEFT column, 45% width)

```html
<div class="exhibit-label">
  <span class="exhibit-number">[Exhibit N:]</span>
  <span class="exhibit-desc">[Growth & Margins]</span>
</div>
<table class="report-table-minimal ds-table-dense">
  <thead>
    <tr>
      <th class="col-text">[Metric]</th>
      <th>[FY-2]</th><th>[FY-1]</th><th>[FY0A]</th>
      <th class="ds-col-forecast">[FY+1E]</th>
      <th class="ds-col-forecast">[FY+2E]</th>
      <th class="ds-col-forecast">[FY+3E]</th>
    </tr>
  </thead>
  <tbody>
    <tr><td class="col-text">Revenue YoY (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">EBIT YoY (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">Net Profit YoY (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">Gross Margin (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">EBIT Margin (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">Net Margin (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">ROE (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
    <tr><td class="col-text">ROIC (%)</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td><td class="col-number ds-col-forecast">[x.x]</td></tr>
  </tbody>
</table>
<div class="data-source">[iFind / Company filings, as of YYYY-MM-DD]</div>
```

### P2 Dense Table — Condensed IS/BS/CF (RIGHT column, 55% width)

Each of Income Statement / Balance Sheet / Cash Flow Statement uses `.ds-table-dense`. Recommended **6 rows per statement** to fit page 2 grid:

**Income Statement** recommended rows:
Revenue → Gross Profit → EBIT → EBT → Net Profit → EPS ([currency])

**Balance Sheet** recommended rows:
Total Assets → Total Liabilities → Net Debt → Total Equity → Shares Outstanding → Book Value / Share

**Cash Flow** recommended rows:
CFO → CapEx → FCF → Dividends Paid → Net Change in Debt → Net Change in Cash

All three tables use the same 6-column period structure as above (3 historical + 3 forecast, forecast columns get `.ds-col-forecast`).

### Price Performance Table (LEFT column, sits under chart C6)

```html
<table class="perf-table">
  <thead>
    <tr><th>[Period]</th><th>[Absolute]</th><th>[Rel. to Index]</th></tr>
  </thead>
  <tbody>
    <tr><td class="col-text">1M</td><td class="col-number">[+x.x%]</td><td class="col-number">[+x.x%]</td></tr>
    <tr><td class="col-text">3M</td><td class="col-number">[+x.x%]</td><td class="col-number">[+x.x%]</td></tr>
    <tr><td class="col-text">6M</td><td class="col-number">[+x.x%]</td><td class="col-number">[+x.x%]</td></tr>
    <tr><td class="col-text">YTD</td><td class="col-number">[+x.x%]</td><td class="col-number">[+x.x%]</td></tr>
    <tr><td class="col-text">1Y</td><td class="col-number">[+x.x%]</td><td class="col-number">[+x.x%]</td></tr>
    <tr><td class="col-text">3Y</td><td class="col-number">[+x.x%]</td><td class="col-number">[+x.x%]</td></tr>
  </tbody>
</table>
```

> **Absolute** = stock raw return. **Rel. to Index** = stock return minus the sector/market index (CSI 300 for A-shares, HSI for HK, S&P 500 for US).

### P2 Population Rules

- All cells marked `[...]` MUST be populated from Task 2 Excel model (sheets: `Income Statement`, `Balance Sheet`, `Cash Flow Statement`, `Valuation`).
- **Never fabricate numbers.** If a data point is unavailable, render `N/A` and record in the omissions log.
- Forecast columns (`FY+1E` / `FY+2E` / `FY+3E`) must carry `.ds-col-forecast` class so the CSS applies the light-blue shading.
- 5-year or 6-year horizons are acceptable; if Task 2 provides 5 historical + 3 forecast, use the 5+3 layout.

---

## Minimal Table Variant (Recommended for English)

English reports recommend using `.report-table-minimal` (minimal style):

```html
<div class="exhibit-label">
  <span class="exhibit-number">Exhibit 3:</span>
  <span class="exhibit-desc">Key Financial Summary (FY2022-2026E)</span>
</div>
<table class="report-table-minimal">
  <colgroup>
    <col style="width: 25%">
    <col style="width: 15%">
    <col style="width: 15%">
    <col style="width: 15%">
    <col style="width: 15%">
    <col style="width: 15%">
  </colgroup>
  <thead>
    <tr><th class="col-text">Metric</th><th>FY22A</th><th>FY23A</th><th>FY24A</th><th>FY25E</th><th>FY26E</th></tr>
  </thead>
  <tbody>
    <tr><td class="col-text">Revenue ($mn)</td><td class="col-number">1,200</td><td class="col-number">1,350</td><td class="col-number">1,500</td><td class="col-number">1,680</td><td class="col-number">1,890</td></tr>
    <tr><td class="col-text">YoY Growth</td><td class="col-number">8.5%</td><td class="col-number"><span class="change-positive">+12.5%</span></td><td class="col-number">11.1%</td><td class="col-number">12.0%</td><td class="col-number">12.5%</td></tr>
  </tbody>
</table>
<div class="data-source">iFind, as of 2026-04-09</div>
```

Characteristics: Only top/bottom line, no vertical line, change values highlighted.

---

## Change Value Highlight Standard

When data involves YoY/QoQ change, use color blocks mark direction:

| class | Applicable Scenario | Visual Effect |
|---|---|---|
| `.change-positive` | Positive change (growth, improvement) | Light green background + green text |
| `.change-negative` | Negative change (decline, deterioration) | Light red background + red text |
| `.change-neutral` | No change or no clear direction | Light gray background + gray text |

**Note**: A股 market red rise green fall, use `.positive-a` / `.negative-a` (different from universal color block rules).

---

## Exhibit Numbering Standard

Each table/chart above must have unified Exhibit number, continuous numbering throughout:

- Chinese Version: `图表 1:` `图表 2:` ...
- English Version: `Exhibit 1:` `Exhibit 2:` ...

Each Exhibit below must have `.data-source` annotation.

---

## Checklist

- [ ] Use `.report-table` or `.report-table-minimal`, column width auto-allocated
- [ ] Numbers right-align (`.col-number`), text left-align, total row bold
- [ ] Exhibit numbers continuous, `.exhibit-label` above, `.data-source` below
- [ ] Change values use `.change-positive/.change-negative` highlight
