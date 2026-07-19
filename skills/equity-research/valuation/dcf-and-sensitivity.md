# DCF, Historical Band & Sensitivity — Absolute & Relative-to-Self Valuation

> **Level 2 only** — Consumed by `equity-report` skill (full version with Task 2 Excel model). Not used by `tear-sheet` or by `equity-report` L1 (streamlined).
>
> **Companion file**: `comparable.md` covers relative-to-peers valuation. Together these two files form the complete valuation methodology layer.

---

## Why One File

DCF, historical valuation band, and sensitivity analysis are mechanically inseparable:

- The **DCF** produces a point estimate of intrinsic value.
- The **historical band** places current market pricing against the stock's own history — a sanity check on the DCF conclusion.
- The **sensitivity matrix** is not a standalone method; it is the error-bar around the DCF point estimate.

Keeping them in one file removes redundant scaffolding (WACC definitions repeated, terminal-growth ranges re-stated) and makes the triangulation narrative easier to write in §XIII of `research-document-template.md` (Cross-Method Valuation Synthesis).

---

## Part 1: DCF Methodology / 现金流折现法

### Overview

The Discounted Cash Flow model estimates intrinsic value by projecting future Free Cash Flows (FCF) and discounting them to present value. This is the **absolute** valuation method in the three-lens framework (the other two being relative-to-peers via `comparable.md` and relative-to-self via Part 2 below).

### Model Structure

```
Step 1: WACC Calculation              → Discount rate
Step 2: Historical FCF Analysis       → Base year metrics
Step 3: FCF Projection (5-year)       → Projected cash flows
Step 4: Terminal Value                → Perpetuity or exit multiple
Step 5: Enterprise Value              → Sum PV(FCF) + PV(Terminal Value)
Step 6: Equity Bridge                 → EV → Equity Value → Per Share Value
Step 7: Sensitivity Analysis          → See Part 3 below
```

### Step 1: WACC Calculation (加权平均资本成本)

**Formula:**

```
WACC = E/(E+D) × Ke + D/(E+D) × Kd × (1 - Tax Rate)
```

**Component details:**

| Component | Method | Data Source |
|-----------|--------|-------------|
| **Ke (Cost of Equity)** | CAPM: Rf + β × ERP + Size Premium | See below |
| **Risk-Free Rate (Rf)** | 10-year government bond yield of company's market | A股: China 10Y; US: US 10Y Treasury; HK: US 10Y |
| **Beta (β)** | 2-year weekly returns vs. benchmark | iFind or Yahoo Finance |
| **Equity Risk Premium (ERP)** | Market-specific | A股: 6-7%; US: 4.5-5.5%; HK: 5.5-6.5% |
| **Size Premium** | Based on market cap | Mega-cap: 0%; Large: 0.5-1%; Mid: 1-2%; Small: 2-3% |
| **Kd (Cost of Debt)** | Weighted average interest rate on debt | Financial statements or bond yields |
| **E, D** | Market cap of equity; book value of debt | Latest financial data |
| **Tax Rate** | Effective tax rate (3-year average) | Financial statements |

**WACC reasonability check:**

| Market | Typical WACC Range | Red Flag |
|--------|-------------------|----------|
| A股 (A-shares) | 8-12% | <6% or >15% |
| US | 7-11% | <5% or >14% |
| HK | 8-12% | <6% or >15% |

If WACC falls outside the typical range, explain why (e.g., unusually high leverage, very low beta, sector-specific factors).

### Step 2: Historical FCF Analysis

**Free Cash Flow definition:**

```
FCFF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔWorking Capital
```

Or equivalently:

```
FCFF = Operating Cash Flow - CapEx + Interest × (1 - Tax Rate)
```

**Historical metrics to calculate (3-5 years):**

| Metric | Purpose |
|--------|---------|
| Revenue growth rate | Projection base |
| EBIT margin | Profitability trend |
| CapEx / Revenue ratio | Investment intensity |
| D&A / Revenue ratio | Asset base |
| Working capital / Revenue ratio | Capital efficiency |
| FCFF margin | Cash conversion |
| FCFF / Net Income ratio | Earnings-to-cash conversion quality |

### Step 3: FCF Projection (5-Year Explicit Period)

**Projection framework:**

| Year | Revenue Growth | EBIT Margin | CapEx/Rev | ΔWC/Rev | Tax Rate |
|------|---------------|-------------|-----------|---------|----------|
| Year 1 | Based on consensus + own adjustment | | | | |
| Year 2 | Gradual convergence | | | | |
| Year 3 | Mid-cycle normalization | | | | |
| Year 4 | Approaching steady state | | | | |
| Year 5 | Steady state or slight convergence | | | | |

**Projection principles:**

1. **Revenue growth**: Start with consensus estimates for Y1-Y2, then converge toward industry long-term growth rate.
2. **Margin expansion/contraction**: Must be justified (operating leverage, mix shift, pricing power).
3. **CapEx intensity**: Align with management guidance and historical patterns.
4. **Working capital**: Use historical days ratios unless structural change expected.
5. **No hockey-stick projections**: Growth acceleration in later years requires explicit justification.

**Key assumption documentation.** Every projection must document:

```
Assumption: [What is assumed]
Basis:      [Why — historical trend, management guidance, industry comparison]
Risk:       [What could make this wrong]
```

### Step 4: Terminal Value

**Method A: Gordon Growth Model (preferred)**

```
Terminal Value = FCF_Year5 × (1 + g) / (WACC - g)
```

Where `g` = terminal growth rate:

| Market | Typical Terminal Growth | Rationale |
|--------|------------------------|-----------|
| A股 | 2-4% | China nominal GDP growth convergence |
| US | 1.5-3% | US nominal GDP growth |
| HK | 2-3.5% | Blend of China and global growth |

**Method B: Exit Multiple**

```
Terminal Value = EBITDA_Year5 × Exit Multiple
```

Exit multiple based on comparable company current trading multiples, with potential mean-reversion adjustment.

**Terminal value sanity check:**

- Terminal Value should typically be 50-70% of Enterprise Value. If >80%, the model is overly dependent on terminal assumptions — flag this.
- Implied terminal growth rate from exit multiple should be reasonable (2-4%).

### Steps 5-6: Enterprise Value → Equity Value

```
Enterprise Value = Σ PV(FCF_Year1-5) + PV(Terminal Value)
```

**Equity bridge:**

```
Equity Value = Enterprise Value
  - Net Debt (Total Debt - Cash & Equivalents)
  - Minority Interest
  - Preferred Stock
  + Associates & JVs (at fair value)
  + Excess Cash (if identified)
  + Non-operating Assets (at fair value)

Equity Value per Share = Equity Value / Diluted Shares Outstanding
```

### Step 7: Sensitivity Analysis

The DCF model must produce at minimum:

1. **WACC vs. Terminal Growth Rate** matrix (primary — mandatory)
2. **Revenue Growth vs. EBIT Margin** matrix (secondary — optional)

Full specification in **Part 3** below.

### DCF Output Format (for report inclusion)

The DCF section in the equity report should include:

1. **Assumption Summary Table**: Key inputs (WACC, growth rates, margins, CapEx intensity)
2. **FCF Projection Table**: 5-year explicit + terminal value
3. **Equity Bridge Table**: EV → Equity Value → Per Share
4. **Sensitivity Matrix**: WACC × Terminal Growth (from Part 3)
5. **Narrative**: 2-3 sentences interpreting the result and comparing to current market price

---

## Part 2: Historical Valuation Band / 历史估值区间分析

### Overview

Historical valuation band analysis plots a stock's valuation multiples over time to identify whether the current valuation sits at a premium or discount relative to its **own history**. This is a **relative-to-self** valuation method, complementing the **relative-to-peers** (comparable companies in `comparable.md`) and **absolute** (DCF above) methods.

### Methodology

**Step 1: Select valuation metrics**

Choose 2-3 metrics based on industry (refer to `comparable.md` §Valuation Metric Selection Guide):

| Priority | Metrics | Applicable Industries |
|----------|---------|----------------------|
| Primary | PE (TTM) | Most industries with stable earnings |
| Primary | PB | Financials, cyclicals, asset-heavy |
| Secondary | PS | Tech, high-growth, loss-making |
| Secondary | EV/EBITDA | Capital-intensive, cross-border comparison |

**Step 2: Historical data collection**

| Parameter | Specification |
|-----------|---------------|
| **Time period** | 5 years (minimum 3 years if recently listed) |
| **Frequency** | Weekly closing values preferred; monthly acceptable |
| **Adjustment** | Forward-adjusted (前复权) prices for PE/PB calculations |
| **Outlier handling** | Exclude periods where PE is negative or >200x (label as "N/M") |

Data source: iFind `ifind_get_stock_financial_index` with date range parameters.

**Step 3: Calculate statistical bands**

For each metric, calculate:

| Statistic | Calculation | Purpose |
|-----------|-------------|---------|
| **Maximum** | Max over period | Cycle peak valuation |
| **Minimum** | Min over period (excl. outliers) | Cycle trough valuation |
| **Mean** | Arithmetic average | Valuation center |
| **Median** | 50th percentile | Robust center (less outlier-sensitive) |
| **+1 Std Dev** | Mean + 1σ | Upper band (expensive zone) |
| **-1 Std Dev** | Mean - 1σ | Lower band (cheap zone) |
| **Current** | Latest value | Where we are now |
| **Current Percentile** | % of observations below current | Relative positioning |

**Step 4: Percentile interpretation**

| Percentile Range | Interpretation | Suggested Label |
|-----------------|----------------|-----------------|
| 0-20% | Historically cheap | 估值偏低 / Undervalued |
| 20-40% | Below average | 低于均值 / Below Mean |
| 40-60% | Fair value zone | 合理区间 / Fair Value |
| 60-80% | Above average | 高于均值 / Above Mean |
| 80-100% | Historically expensive | 估值偏高 / Overvalued |

**Important caveat.** Historical cheapness does NOT automatically mean "buy." A stock can be cheap for fundamental reasons (structural decline, earnings deterioration). Always cross-reference with DCF (Part 1) and comparable analysis (`comparable.md`). The synthesis across all three methods lives in §XIII of `research-document-template.md`.

### Band Output Format

**Summary table:**

```markdown
| Metric | 5Y High | 5Y Low | Mean | Median | +1σ | -1σ | Current | Percentile |
|--------|---------|--------|------|--------|-----|-----|---------|------------|
| PE(TTM) | 35.2x | 12.8x | 22.5x | 21.3x | 28.7x | 16.3x | 18.5x | 32% |
| PB | 5.8x | 2.1x | 3.8x | 3.6x | 4.9x | 2.7x | 3.2x | 38% |
```

**Narrative template:**

```
Historical Valuation Analysis:
• [Company] currently trades at [X]x PE(TTM), at the [N]th percentile of its 5-year
  range ([low]x–[high]x).
• This represents a [premium/discount] to its 5-year mean of [mean]x, suggesting
  [interpretation].
• Key driver of current [above/below] average valuation: [reason — e.g., earnings
  upgrade cycle, sector rotation, structural re-rating].
• Compared to DCF implied value of [Y], the band analysis [confirms/contradicts]
  the [undervalued/overvalued] thesis.
```

### Visual Specification (for chart generation)

If the equity-report skill generates a valuation band chart (see `modules/equity-report-charts.md` C4):

1. **Chart type**: Line chart with shaded bands
2. **X-axis**: Time (5 years, monthly ticks)
3. **Y-axis**: Valuation multiple (PE or PB)
4. **Bands**: Mean (solid line), ±1σ (shaded area), ±2σ (lighter shaded area)
5. **Current point**: Highlighted dot with label
6. **Colors**: Use blue tones consistent with the report's CSS color scheme (#003366 primary)

### Common Pitfalls

1. **Cyclical trap**: For cyclical stocks (周期股), PE is lowest at cycle peak (high earnings) and highest at cycle trough (low earnings). Use PB instead.
2. **Structural change**: If company underwent major M&A, spin-off, or business transformation mid-period, historical bands before the event are not comparable. Truncate to post-event period.
3. **Share dilution**: Large equity issuance or buyback programs can distort historical PE/PB. Use per-share metrics consistently.
4. **Accounting changes**: IFRS/CAS transitions can affect reported earnings. Note any standard changes in the analysis period.

---

## Part 3: Sensitivity Analysis / 敏感性分析

### Overview

Sensitivity analysis quantifies how changes in key assumptions affect the valuation output. It answers: "If I'm wrong about X, how much does the answer change?" This is essential for communicating confidence levels and risk ranges — it turns the DCF point estimate into a defensible range.

### Matrix Types

**Primary matrix: WACC × Terminal Growth Rate (DCF-linked — mandatory)**

This is the mandatory sensitivity matrix for any DCF valuation.

```markdown
| Equity Value/Share | g = 1.5% | g = 2.0% | g = 2.5% | g = 3.0% | g = 3.5% |
|--------------------|----------|----------|----------|----------|----------|
| **WACC = 8.0%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **WACC = 8.5%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **WACC = 9.0%** | ¥XX.XX | **¥XX.XX** | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **WACC = 9.5%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **WACC = 10.0%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
```

Formatting rules:

- Base case cell highlighted in **bold** (center of matrix)
- WACC range: ±1-2% around base WACC in 0.5% steps
- Terminal growth range: ±1-1.5% around base growth in 0.5% steps
- Currency symbol matches company's primary listing market

**Secondary matrix: Revenue Growth × EBIT Margin (optional)**

```markdown
| Equity Value/Share | Margin = 12% | Margin = 14% | Margin = 16% | Margin = 18% | Margin = 20% |
|--------------------|-------------|-------------|-------------|-------------|-------------|
| **Growth = 5%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **Growth = 8%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **Growth = 10%** | ¥XX.XX | ¥XX.XX | **¥XX.XX** | ¥XX.XX | ¥XX.XX |
| **Growth = 12%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
| **Growth = 15%** | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX | ¥XX.XX |
```

**Tertiary matrix: PE × EPS (scenario-linked)**

Useful for connecting to scenario analysis in `scenario-deep-dive.md`:

```markdown
| Implied Market Cap (亿) | EPS = ¥3.50 | EPS = ¥4.00 | EPS = ¥4.50 | EPS = ¥5.00 |
|--------------------------|-------------|-------------|-------------|-------------|
| **PE = 12x** | | | | |
| **PE = 15x** | | **Base** | | |
| **PE = 18x** | | | | |
| **PE = 20x** | | | | |
```

### Construction Guidelines

**Variable selection.** Choose the 2 variables with the **highest impact on valuation** and the **highest uncertainty**:

| Company Type | Recommended Primary Pair | Recommended Secondary Pair |
|-------------|--------------------------|---------------------------|
| Mature/Stable | WACC × Terminal Growth | PE × EPS |
| High Growth | Revenue Growth × EBIT Margin | WACC × Terminal Growth |
| Cyclical | Commodity Price × Volume | PB × ROE |
| Financial | NIM × Loan Growth | PB × ROE |
| Loss-making | Revenue Growth × Path to Profitability | PS × Revenue |

**Range calibration:**

1. **Symmetric range**: Center on base case, extend equally in both directions.
2. **Step size**: Choose granularity that produces meaningful variation (typically 5×5 grid).
3. **Extreme check**: Corner values should represent plausible (if unlikely) scenarios, not absurd ones.
4. **Scenario linking**: Optimistic/base/pessimistic scenarios from §Scenario Analysis should map to specific cells in the matrix.

### Interpretation Narrative

After each matrix, include a brief interpretation:

```markdown
**Sensitivity Interpretation:**
• Under base case assumptions (WACC [X]%, terminal growth [Y]%), implied equity
  value is ¥[Z] per share, representing [upside/downside]% vs. current price of ¥[P].
• The valuation is [more/less] sensitive to [variable A] than [variable B]:
  a 1% change in [A] moves equity value by [±X]%, while a 1% change in [B]
  moves it by [±Y]%.
• The stock trades below DCF-implied value across [N] of [25] scenarios,
  suggesting [limited downside / significant upside / balanced risk-reward].
```

### HTML Formatting for Report

```html
<div class="exhibit-label">
  <span class="exhibit-number">Exhibit X:</span>
  <span class="exhibit-desc">DCF Sensitivity: WACC vs. Terminal Growth Rate</span>
</div>
<table class="report-table">
  <thead>
    <tr>
      <th>Equity Value/Share</th>
      <th>g = 1.5%</th><th>g = 2.0%</th><th>g = 2.5%</th><th>g = 3.0%</th><th>g = 3.5%</th>
    </tr>
  </thead>
  <tbody>
    <tr><td class="col-text"><b>WACC = 9.0%</b></td>
        <td class="col-number">¥XX</td>
        <td class="col-number"><b>¥XX</b></td>  <!-- base case highlighted -->
        <td class="col-number">¥XX</td>
        <td class="col-number">¥XX</td>
        <td class="col-number">¥XX</td></tr>
    <!-- ... more rows ... -->
  </tbody>
</table>
<div class="data-source">Model estimates</div>
```

Use `.row-highlight` class for the base case row, and `<b>` for the base case cell.

---

## Combined Output Checklist

- [ ] **DCF**: Assumption summary table, FCF projection table, equity bridge, base-case per-share value
- [ ] **DCF**: WACC within market-typical range or anomaly explained
- [ ] **DCF**: Terminal Value as % of EV disclosed (flag if >80%)
- [ ] **Historical Band**: ≥2 metrics (typically PE + PB), 5-year window, summary table with percentile
- [ ] **Historical Band**: Narrative interpreting current position vs. own history, with cyclical-trap check
- [ ] **Sensitivity**: Primary matrix (WACC × terminal growth) — mandatory
- [ ] **Sensitivity**: Base case cell clearly highlighted, ranges symmetric, corner values plausible
- [ ] **Sensitivity**: Interpretation narrative included, scenarios linked where applicable
- [ ] **Cross-method synthesis** (DCF + Band + Comps): Written up in §XIII of `research-document-template.md`

---

## Data Sources

| Data Type | Source | API |
|-----------|--------|-----|
| Financial statements | iFind | `ifind_get_financial_statements` |
| Beta | iFind | `ifind_get_stock_financial_index` |
| Historical PE/PB/PS | iFind | `ifind_get_stock_financial_index` (with date range) |
| Historical stock prices | iFind | `ifind_get_price` |
| Risk-free rate | Web Search | Country-specific 10Y bond yield |
| Consensus estimates | iFind | `ifind_get_forecast` |
| Share count | iFind | `ifind_get_stock_info` |

---

## Integration With Other Files

- **`comparable.md`** — Relative-to-peers. Companion file; use valuation metric selection guide from there.
- **`research-document-template.md` §VIII** — Valuation table population (both L1 and L2).
- **`research-document-template.md` §XIII** — Cross-method valuation synthesis narrative.
- **`references/financial-model-spec.md`** Tab 7 (DCF), Tab 9 (Sensitivity) — Excel implementation in L2's Task 2.
- **`modules/equity-report-charts.md`** C4 — Historical PE band chart specification.
- **`analysis/scenario-deep-dive.md`** — Scenario-linked sensitivity (tertiary PE × EPS matrix).
