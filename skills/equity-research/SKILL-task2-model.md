---
name: equity-report-task2-model
description: "Task 2 of equity report workflow (L2 only). Builds a complete financial model (Excel) and valuation analysis from the Task 1 research document. Produces: (1) a fully linked 3-statement financial model with DCF, comps, and sensitivity; (2) a valuation analysis summary document. This file is the entry point — do NOT read SKILL.md or Task 1's analysis framework files."
---

# Task 2: Financial Model + Valuation (L2 Only)

> **This is the entry point for Task 2 of the equity report workflow (L2 Full Version).**
> Task 1 (Research + Analysis) has already been completed and produced a research document.
> Your job: build an actual Excel financial model and perform valuation analysis.
> **If this is an L1 (streamlined) report**: Skip this file entirely. Go directly to `SKILL-task3-report.md`.

---

## ⚠️ CRITICAL RULES

### DO NOT TAKE SHORTCUTS
**Data Authenticity** All data must have real sources; strictly prohibit fabrication. No placeholders, no "TBD". 
**Data Verification** Critical data cross-verified by 2+ independent sources 
**Timeliness**  Must use latest financial reports and real-time market data 

- ✅ Build a REAL Excel model with formulas that recalculate when inputs change — not static numbers
- ✅ All 3 financial statements (IS → BS → CF) must link and balance
- ✅ Balance Sheet: Assets = Liabilities + Equity on EVERY projected year (BALANCE CHECK row mandatory)
- ✅ Cash Flow: Ending Cash must tie to BS Cash on every year (CASH TIE-OUT row mandatory)
- ✅ Revenue must link from Revenue Model tab to Income Statement tab (not typed twice)
- ✅ DCF: WACC calculated from CAPM, not hardcoded. FCF discounted with formulas.
- ✅ Sensitivity matrix: Must use Excel formulas that reference WACC and Terminal Growth inputs
- ✅ Comps table: ≥5 peers with statistical summary (Max/75th/Median/25th/Min)
- ❌ Do not hardcode projected numbers — every projection must flow from Operating Drivers
- ❌ Do not skip the Scenarios tab — Bull/Base/Bear with probability-weighted price
- ❌ Do not fabricate comparable company data — use real market data

### Font Color Convention
- 🔵 Blue font = hardcoded input / assumption
- ⚫ Black font = formula (calculated from other cells)
- 🟢 Green font = cross-sheet link (references another tab)

### Task Boundary
- ✅ Deliver: Excel model (.xlsx) + Valuation Analysis document (.md) — then STOP
- ❌ **Do not continue to Task 3.** Wait for user's continuation signal.
- ❌ **Do not create summary documents or extra files.** Deliver ONLY the 2 specified outputs.

---

## Prerequisites

### Automatic File Loading (Session Context)

When the user says "下一步"/"继续"/"continue" to enter Task 2, the Task 1 files exist in the **current session context**. **Do NOT ask the user to provide files.**

1. **Auto-locate Task 1 Research Document**: Search the session for the most recent file matching `*_Research_Document_*.md`. Read it directly.
2. **Extract from the research document**:
   - Company name, ticker, market, currency
   - Historical financial data (§VI)
   - Revenue segment breakdown (§VII)
   - Comparable companies (§V)
   - Operating assumptions mentioned in the analysis
3. **Do NOT read**: `SKILL.md`, `analysis/*.md`, `modules/*.md` — these were consumed in Task 1.

**If the research document cannot be found in session**: Ask the user to confirm the filename. Do NOT start Task 2 without it.

---

## Files to Read

| # | File | Purpose |
|---|------|---------|
| 1 | Task 1 Research Document | Source of all analytical content and historical data |
| 2 | `references/financial-model-spec.md` | **SOLE SOURCE** for Excel model structure — tab specs, line items, formula patterns, formatting |
| 3 | `valuation/dcf-and-sensitivity.md` | Consolidated reference — Part 1: DCF (WACC, projection, terminal value, equity bridge); Part 2: Historical Band (data collection, statistical bands, percentile interpretation); Part 3: Sensitivity Matrix (variable selection, range calibration, interpretation) |
| 4 | `valuation/comparable.md` | Comps methodology — peer selection, metric selection by industry, analysis framework |
| 5 | `references/data-sources.md` | Data source priority and API specs (for fetching additional data if needed) |

**Total files to read**: 5 (down from 7 — DCF, sensitivity, and historical band are now consolidated)

---

## Step 1: Collect Financial Data

### 1.1 Extract from Research Document

The Task 1 research document §VI contains 3-5 years of historical financials. Extract:
- Income Statement: Revenue, COGS, Gross Profit, R&D, SG&A, D&A, EBIT, Interest, Tax, Net Income, EPS, Shares
- Balance Sheet: Cash, AR, Inventory, PP&E, Total Assets, AP, Debt, Total Liabilities, Equity
- Cash Flow: CFO, CapEx, FCF, Dividends
- Key ratios: Margins, ROE, ROA

### 1.2 Fetch Additional Data (if needed)

If the research document's financial data is incomplete, fetch from APIs:
- **A-shares/HK**: iFind API (`ifind_get_financial_statements`, `ifind_get_stock_financial_index`)
- **US stocks**: Yahoo Finance API or SEC filings via Web Search
- **Comparable companies**: iFind industry classification or Web Search

Data to fetch that may not be in the research document:
- [ ] 5-year historical PE/PB weekly data (for historical band)
- [ ] Comparable company financial metrics (for comps tab)
- [ ] Beta, risk-free rate (for WACC)
- [ ] Consensus estimates for FY+1 and FY+2 (for sanity-checking projections)
- [ ] Detailed segment-level revenue (if research document only has top-line)

### 1.3 Record Everything in Raw Data Tab

Every number fetched goes into the Raw Data tab with its source. No data should be used in the model without first being recorded in Raw Data.

---

## Step 2: Build the Financial Model (Excel)

### ⚠️ ENVIRONMENT SKILL INTEGRATION (READ FIRST)

**Before building the model yourself, check if the following environment skills are available.** If they are, **use them** — they produce more professional, institutional-grade Excel outputs than building from scratch.

**Check following path and files in your skill hub: 

/app/.agents/skills/xlsx/reference/ 

xlsx (SKILL.md)
  ├── 3_statement_model_skill.md  ← financial model skills
  └── DCF_SKILL.md                ← DCF valuation skills


## Finance Sub-Skills

### 1. `3 statement model`- Entry file: `./reference/3_statement_model_skill.md`- Use when the task needs a full operating model, linked IS/BS/CF, 
  supporting schedules, balance checks, or a forecast-model foundation 
  for DCF or other valuation work.

### 2. `DCF`- Entry file: `./reference/DCF_SKILL.md`- Use for DCF valuation, NOPAT, UFCF, WACC, terminal value, discounting, 
  EV → Equity Value → Implied Share Price, sensitivity tables.


**Integration Rules:**
- ✅ **Use environment skills for Excel model building** (they have superior formatting, formula patterns, and integrity checks)
- ✅ **Feed them the data you extracted from the Task 1 Research Document** (historical financials, assumptions, peer list)
- ✅ **After each skill finishes, verify its output passes our integrity checks** (Step 5 below)
- ✅ ** Must Perform additional data cross-verification checks on key numbers for latest financial period to ensure skill use is all good, no data corruption or mock data used.
- ✅ **Combine all outputs into a single workbook** — the 3-statement model, DCF tab, and Comps tab should all be tabs in ONE Excel file
- ❌ **Do NOT let environment skills write the Valuation Analysis document** — that stays in our framework (Step 4 below)
- ❌ **Do NOT let environment skills change the font color convention** — enforce 🔵 Blue=input, ⚫ Black=formula, 🟢 Green=cross-sheet

**If environment skills are NOT available**, fall back to building the model yourself using `references/financial-model-spec.md` (read that file instead).

### Build Order

Whether using environment skills or building manually, the model must contain these tabs in this order:

```
PHASE A — 3-Statement Model (use financial-analysis:3-statement-model if available)
  1. Raw Data          → Populate with historical financials from Task 1
  2. Operating Drivers → Set all forward-looking assumptions with Source + Rationale
  3. Revenue Model     → Bottom-up segment revenue buildup (Volume × Price)
  4. Income Statement  → Full P&L driven by Drivers and Revenue Model
  5. Balance Sheet     → Full BS driven by Drivers, with balance check
  6. Cash Flow         → Full CF driven by IS and BS changes, cash tie-out

PHASE B — Valuation Tabs (use financial-analysis:dcf-model + comps-analysis if available)
  7. DCF              → WACC + FCF discounting + Terminal Value + Equity Bridge
  8. Comps            → 5-10 peers + statistical summary (Max/75th/Median/25th/Min)
  9. Sensitivity      → WACC × Terminal Growth matrix
  10. Scenarios       → Bull/Base/Bear parameter sets + probability-weighted price
```

**If using environment skills**: After Phase A completes, verify BS balance + cash tie-out BEFORE starting Phase B. After Phase B, verify all 10 integrity checks (Step 5).

### Operating Drivers — Key Assumptions to Set

For each projected year (FY+1 through FY+5), set these assumptions:

| Category | Assumptions | Guidance |
|----------|------------|----------|
| **Revenue** | YoY growth rate per segment | Start with consensus for Y1-2, converge to industry long-term for Y3-5 |
| **Margins** | Gross margin, R&D%, SG&A%, D&A% | Historical trend ± justified adjustments (operating leverage, mix shift) |
| **Tax** | Effective tax rate | Normalize to statutory rate unless structural reason |
| **Working Capital** | DSO, DIO, DPO | Use historical averages unless structural change expected |
| **CapEx** | CapEx % of revenue | Management guidance or historical trend |
| **Valuation** | WACC inputs, terminal growth | Market-specific (see `valuation/dcf-and-sensitivity.md` §Part 1 ranges) |

**CRITICAL**: Every assumption MUST have:
1. A **Source** (e.g., "Management guidance Q4 2025 call", "3Y historical average", "Consensus Bloomberg")
2. A **Rationale** (e.g., "Margin recovery from 4680 cell manufacturing efficiency gains")

---

## Step 3: Perform Valuation Analysis

### 3.1 DCF Valuation

Read `valuation/dcf-and-sensitivity.md` §Part 1 for DCF methodology. Execute Steps 1-7:
1. Calculate WACC (check reasonability vs. market range)
2. Project 5 years of UFCF from the model
3. Calculate Terminal Value (Gordon Growth + check TV/EV ratio)
4. Discount to present value
5. Equity Bridge: EV → Net Debt → Equity Value → Per Share
6. Build sensitivity matrix (WACC × Terminal Growth)

### 3.2 Comparable Companies

Read `valuation/comparable.md` for peer selection and metric guidance.
- Select 5-10 peers (same industry, similar scale ±50%)
- Populate: Market Cap, Revenue, EBITDA, NI, key multiples
- **MANDATORY**: Statistical summary row with Max/75th/Median/25th/Min
- Calculate implied valuation range (25th to 75th percentile applied to target)

### 3.3 Historical Valuation Band

Read `valuation/dcf-and-sensitivity.md` §Part 2 for historical band methodology.
- Collect 5Y PE/PB data (weekly)
- Calculate: Max, Min, Mean, Median, ±1σ, Current, Percentile
- Interpretation: Where does current valuation sit vs. history?

### 3.4 Cross-Method Synthesis

Compare all valuation methods and identify convergence/divergence:
- DCF implies $XX per share
- Comps median implies $XX per share
- Historical band median implies $XX per share
- **Final valuation range**: $XX — $XX, with base case $XX

### 3.5 Scenario Analysis

Build Bull/Base/Bear scenarios:
- Different revenue growth + margin assumptions
- Different WACC (if macro risk differs)
- Probability-weighted target price = Σ(prob × price)

---

## Step 4: Write Valuation Analysis Document

Produce: `{Company}_{Ticker}_Valuation_Analysis_{Date}.md`

### Structure

```markdown
# {Company} ({Ticker}) Valuation Analysis

> Date: YYYY-MM-DD
> Analyst: Kimi Research (AI-Assisted)
> Rating: [BUY / HOLD / SELL]
> Current Price: $XXX.XX
> Target Price: $XXX.XX (XX% upside/downside)
> Probability-Weighted Price: $XXX.XX

---

## I. Price Target Summary

[2-3 sentences: final recommendation, target price, key driver]

## II. DCF Analysis

[WACC: X.X%, Terminal Growth: X.X%, Implied value: $XXX]
[Key sensitivity: ±1% WACC = ±$XX per share]
[TV as % of EV: XX% — comment if high]

## III. Comparable Companies

[Peer set: [list], Selection rationale: [1 sentence]]
[Target trades at Xth percentile of peers on P/E]
[Implied range from comps: $XX — $XX]

## IV. Historical Valuation Band

[PE currently at Xth percentile of 5Y range]
[PB currently at Xth percentile of 5Y range]
[Historical context: re-rating/de-rating drivers]

## V. Cross-Method Synthesis

[Do methods converge? Which to weight more?]
[Final valuation range: $XX — $XX]
[Base case: $XX (methodology and weighting)]

## VI. Scenario Analysis

### Bull Case (XX% probability)
[Assumptions + implied price + what triggers this]

### Base Case (XX% probability)
[Assumptions + implied price + default path]

### Bear Case (XX% probability)
[Assumptions + implied price + what triggers this]

Probability-weighted target: $XXX.XX

## VII. Key Catalysts

[Top 3-5 catalysts that could move the stock toward bull or bear case]

## VIII. Key Risks to Target

[Top 3-5 risks that could invalidate the valuation, with quantified impact where possible]
```

---

## Step 5: Model Integrity Verification

Run ALL 10 checks from `references/financial-model-spec.md` §Model Integrity Checks:

| # | Check | Pass? |
|---|-------|-------|
| 1 | BS balances (all periods) | ☐ |
| 2 | Cash ties (CF ending = BS cash) | ☐ |
| 3 | Revenue ties (Rev Model = IS) | ☐ |
| 4 | Historical accuracy (vs Raw Data <1%) | ☐ |
| 5 | WACC in normal range | ☐ |
| 6 | TV < 80% of EV | ☐ |
| 7 | Sensitivity center = DCF base | ☐ |
| 8 | Comps stats no errors | ☐ |
| 9 | Scenario probs = 100% | ☐ |
| 10 | FCF positive (base case) | ☐ |

**All 10 must pass before delivery.** If any fail, fix and re-verify.

---

## Step 6: Deliver

1. Save `{Company}_{Ticker}_Financial_Model_{Date}.xlsx` to output directory
2. Save `{Company}_{Ticker}_Valuation_Analysis_{Date}.md` to output directory
3. Report:
   - Model summary (# tabs, # years projected)
   - Key outputs: Revenue CAGR, terminal margin, WACC, DCF price, comps range, target price
   - All 10 integrity checks passed
4. Provide **continuation-ready message** to user:

   **Chinese:**
   > ✅ Step 2 完成 — 财务模型与估值分析已生成。
   > - Excel 模型: {N} 张工作表, {M} 年预测
   > - DCF 目标价: ¥XXX (XX% 上行/下行空间)
   > - 可比公司区间: ¥XX — ¥XX
   > - 10/10 完整性检查通过
   >
   > 接下来进入 Step 3：生成最终 PDF 研报（≥25页）。
   > 你只需要说 **"下一步"**、**"继续"** 或 **"continue"**，我将自动读取本步骤和前面步骤生成的所有文件并继续。

   **English:**
   > ✅ Step 2 complete — Financial model and valuation analysis generated.
   > - Excel model: {N} tabs, {M} years projected
   > - DCF target: $XXX (XX% upside/downside)
   > - Comps range: $XX — $XX
   > - 10/10 integrity checks passed
   >
   > Next: Step 3 — Generate final PDF report (≥25 pages).
   > Just say **"next"**, **"continue"**, or **"下一步"** and I'll automatically proceed using all files generated in this session.

5. **STOP.** Wait for user's continuation signal. Do not continue until user says "下一步"/"继续"/"continue"/"next".

---

