# Financial Model Build Specification

> **This file is the sole source of truth for Task 2: Financial Model + Valuation.**
> The agent MUST build a real, working Excel (.xlsx) file with formulas that link across sheets.
> Do NOT produce a markdown table pretending to be a model. Do NOT calculate numbers "in your head."
> The deliverable is an actual Excel workbook that an analyst can open, change an assumption, and see the entire model update.

---

## File Naming

```
{Company}_{Ticker}_Financial_Model_{Date}.xlsx
```

Example: `{Company}_{Ticker}_Financial_Model_{Date}.xlsx`

---

## Required Tabs (8 minimum)

| # | Tab Name | Purpose | Approx. Rows |
|---|----------|---------|-------------|
| 1 | **Raw Data** | Historical financials extracted from APIs/filings (untouched source data) | 60-90 |
| 2 | **Operating Drivers** | All assumptions with Source + Rationale columns | 25-35 |
| 3 | **Revenue Model** | Segment-level revenue buildup (Volume × Price) | 30-50 |
| 4 | **Income Statement** | Full P&L: Revenue through Net Income, 3-5Y historical + 5Y projected | 40-50 |
| 5 | **Balance Sheet** | Full BS: Assets / Liabilities / Equity, with balance check row | 35-45 |
| 6 | **Cash Flow** | Full CF: Operating / Investing / Financing + FCF, ending cash ties to BS | 30-40 |
| 7 | **DCF** | WACC calculation + 5Y FCF discounting + Terminal Value + Equity Bridge | 30-40 |
| 8 | **Comps** | 5-10 comparable companies + statistical summary (Max/75th/Median/25th/Min) | 20-30 |

### Optional Tabs (add as needed)

| Tab | When to Include |
|-----|----------------|
| **Sensitivity** | Always recommended. WACC × Terminal Growth matrix. |
| **Scenarios** | Always recommended. Bull/Base/Bear parameter sets + output comparison. |
| **Supporting Schedules** | If PP&E/depreciation or debt schedules are complex. |
| **SOTP** | If company has 3+ distinct business segments with different valuation profiles. |
| **Historical Band** | If 5-year PE/PB data available for percentile analysis. |

---

## Tab 1: Raw Data

### Purpose
Store the unmodified historical financial data exactly as retrieved from APIs or filings. This tab is the **source of truth** — all other tabs reference it.

### Structure

```
Row 1: [Company Name] ([Ticker]) — Raw Financial Data ([Currency] millions)
Row 2: (blank)
Row 3: Headers →  B: Line Item | C: FY-4 | D: FY-3 | E: FY-2 | F: FY-1 | G: FY0 (latest)
Row 4: (blank)
Row 5: "Income Statement" (section header)
Row 6-25: IS line items (Revenue, COGS, Gross Profit, R&D, SG&A, D&A, Operating Income, Interest, Tax, Net Income, EPS, Shares, EBITDA, SBC)
Row 26: (blank)
Row 27: "Balance Sheet" (section header)
Row 28-55: BS line items (Cash, AR, Inventory, Current Assets, PP&E, Goodwill, Intangibles, Total Assets, AP, Accrued, Deferred Revenue, Current Debt, Current Liabilities, LT Debt, Total Liabilities, Equity, Retained Earnings, Total L+E)
Row 56: (blank)
Row 57: "Cash Flow Statement" (section header)
Row 58-80: CF line items (Net Income, D&A, SBC, WC changes, CFO, CapEx, Acquisitions, CFI, Debt issuance/repayment, Dividends, CFF, Net Change, Beginning Cash, Ending Cash, FCF)
Row 81: (blank)
Row 82: "Per Share & Ratios" (section header)
Row 83-90: Key ratios (Gross Margin, Op Margin, Net Margin, ROE, ROA, D/E, Current Ratio, FCF Margin)
```

### Data Entry Rules
- **Blue font** for all hardcoded data (manual entry from APIs)
- **Source annotation**: Column A can optionally note the API/source for each section
- **Currency**: State currency in the header row. All numbers in same currency.
- **Units**: Millions unless otherwise stated. Per-share data in actual units.

---

## Tab 2: Operating Drivers

### Purpose
Central assumption dashboard. Every forward-looking number in the model traces back to an assumption here.

### Structure

```
Row 1: [Company Name] ([Ticker]) — Operating Drivers & Assumptions ([Currency] millions)
Row 2: (blank)
Row 3: Headers → B: Driver | C-G: FY-4A through FY0A | H-L: FY+1E through FY+5E | M: Source | N: Rationale
Row 4: (blank)
Row 5: "Revenue Growth Drivers" (section header)
Row 6: Revenue YoY Growth %
Row 7: Total Revenue (formula: prior year × (1 + growth))
Row 8: Gross Margin %
Row 9: R&D / Revenue %
Row 10: SG&A / Revenue %
Row 11: D&A / Revenue %
Row 12: Tax Rate (Normalized) %
Row 13: (blank)
Row 14: "Balance Sheet Assumptions" (section header)
Row 15: AR Days (DSO)
Row 16: Inventory Days (DIO)
Row 17: AP Days (DPO)
Row 18: Deferred Revenue / Revenue %
Row 19: CapEx / Revenue %
Row 20: Depreciation / Gross PPE %
Row 21: SBC / Revenue %
Row 22: (blank)
Row 23: "Other Assumptions" (section header)
Row 24: Interest Income Rate %
Row 25: Interest Expense Rate %
Row 26: Dividend Payout Ratio %
Row 27: Minority Interest / Revenue %
Row 28: Diluted Share Count (millions)
```

### Critical Rules
- **Historical columns (A)**: Show actual historical ratios calculated from Raw Data (formulas, not hardcoded)
- **Projected columns (E)**: Hardcoded assumptions (blue font) that the user can change
- **Source column**: Must be filled for every projected assumption (e.g., "Mgmt guidance", "Historical avg", "Consensus", "Our estimate")
- **Rationale column**: 1-2 sentence explanation of why this assumption is reasonable

---

## Tab 3: Revenue Model

### Purpose
Bottom-up revenue buildup by business segment. Shows Volume × Price (or equivalent driver) for each segment.

### Structure

```
Section A: Revenue by Segment
─────────────────────────────────────────────────────
[Segment 1 Name]
  Revenue            =Volume × Price (formula)
  Volume / Units     hardcoded assumptions
  ASP / ARPU         hardcoded assumptions
  YoY Growth %       formula
  % of Total         formula

[Segment 2 Name]
  Revenue            =Volume × Price
  ...

[Segment 3-6]
  ...
─────────────────────────────────────────────────────
Total Revenue        =SUM of all segments (must match IS)
  YoY Growth %       formula

Section B: Revenue by Geography (if applicable)
─────────────────────────────────────────────────────
[Region 1]           Revenue + % of Total + YoY Growth
[Region 2]           ...
─────────────────────────────────────────────────────
Total                =Must match Section A total
```

### Rules
- Minimum 3 segments, ideally 4-6
- Each segment must have an explicit volume × price (or equivalent) driver
- Historical data (3-5 years) + projected (5 years)
- **Cross-check**: Total Revenue in Revenue Model tab MUST equal Total Revenue in Income Statement tab (link via formula)

---

## Tab 4: Income Statement

### Purpose
Complete Profit & Loss statement with full cost structure breakdown.

### Structure (40-50 line items)

```
Income Statement
─────────────────────────────────────────────────────
Total Revenue                    =Revenue Model!Total
  YoY Growth %                   formula
Cost of Revenue                  =Revenue × (1 - Gross Margin from Drivers)
─────────────────────────────────────────────────────
Gross Profit                     =Revenue - COGS
  Gross Margin %                 formula

R&D Expense                      =Revenue × R&D% from Drivers
SG&A Expense                     =Revenue × SG&A% from Drivers
Depreciation & Amortization      =Supporting Schedules or Revenue × D&A% from Drivers
Other Operating Income/(Expense) hardcoded or zero
─────────────────────────────────────────────────────
Operating Income (EBIT)          =Gross Profit - R&D - SG&A - D&A - Other
  Operating Margin %             formula

Interest Income                  =Avg Cash × Interest Income Rate from Drivers
Interest Expense                 =Avg Debt × Interest Expense Rate from Drivers
Other Non-Operating              hardcoded or zero
─────────────────────────────────────────────────────
EBT (Earnings Before Tax)        =EBIT + Int Income - Int Expense + Other
Tax Provision                    =EBT × Tax Rate from Drivers
  Effective Tax Rate %           formula
─────────────────────────────────────────────────────
Net Income to Company            =EBT - Tax
  Minority Interest              hardcoded or Revenue × MI% from Drivers
Net Income                       =Net Income to Company - MI
  Net Margin %                   formula

Diluted Shares (millions)        from Drivers
Diluted EPS                      =Net Income / Diluted Shares

─────────────────────────────────────────────────────
Memo Items:
EBITDA                           =EBIT + D&A
  EBITDA Margin %                formula
Stock-Based Compensation         =Revenue × SBC% from Drivers
```

### Critical Rules
- **Historical columns**: Must match Raw Data tab exactly (use formulas referencing Raw Data, not re-entered numbers)
- **Projected columns**: All driven by Operating Drivers assumptions (formulas, not hardcoded)
- **Revenue link**: Revenue MUST be a formula linking to Revenue Model tab
- **Margin calculations**: Every margin is a formula (not hardcoded)

---

## Tab 5: Balance Sheet

### Purpose
Complete Balance Sheet that balances for every period.

### Structure (35-45 line items)

```
Assets
─────────────────────────────────────────────────────
Cash & Equivalents               =Prior Cash + Net Change from CF tab
Short-Term Investments           hardcoded or zero
Total Cash & ST Investments      =Cash + STI
Accounts Receivable              =Revenue × (AR Days / 365)
Inventory                        =COGS × (Inventory Days / 365)
Prepaid & Other Current          hardcoded or % of revenue
─────────────────────────────────────────────────────
Total Current Assets             =SUM

Net PP&E                         =Supporting Schedules or formula
Goodwill                         hardcoded (constant unless M&A)
Intangible Assets                =Supporting Schedules or declining
Other Non-Current Assets         hardcoded or % of revenue
─────────────────────────────────────────────────────
Total Non-Current Assets         =SUM
Total Assets                     =Current + Non-Current

Liabilities
─────────────────────────────────────────────────────
Accounts Payable                 =COGS × (AP Days / 365)
Accrued Expenses                 hardcoded or % of revenue
Deferred Revenue                 =Revenue × Deferred Rev% from Drivers
Current Portion of Debt          from debt schedule or constant
Other Current Liabilities        hardcoded or % of revenue
─────────────────────────────────────────────────────
Total Current Liabilities        =SUM

Long-Term Debt                   from debt schedule or constant
Other Non-Current Liabilities    hardcoded or % of revenue
─────────────────────────────────────────────────────
Total Non-Current Liabilities    =SUM
Total Liabilities                =Current + Non-Current

Equity
─────────────────────────────────────────────────────
Common Stock & APIC              =Prior + SBC
Treasury Stock                   hardcoded or zero
Retained Earnings                =Prior + Net Income - Dividends
OCI / Other                      hardcoded or zero
─────────────────────────────────────────────────────
Total Common Equity              =SUM
Minority Interest                hardcoded or formula
Total Equity                     =Common Equity + MI
─────────────────────────────────────────────────────
Total Liabilities & Equity       =Total Liabilities + Total Equity

⚠️ BALANCE CHECK                 =Total Assets - Total L&E (MUST = 0)
```

### Critical Rules
- **Balance Check row**: MUST be present. Value MUST be 0 (or <$1M rounding) for every column.
- **Cash**: Derived from Cash Flow tab (not hardcoded for projected years)
- **Working capital items**: Driven by days ratios from Operating Drivers
- **Retained Earnings**: Formula linking to Net Income from IS tab

---

## Tab 6: Cash Flow

### Purpose
Complete Cash Flow Statement with FCF calculation. Ending cash must tie to Balance Sheet.

### Structure (30-40 line items)

```
Cash From Operations
─────────────────────────────────────────────────────
Net Income                       =IS!Net Income
  Depreciation                   =IS!D&A (or Supporting Schedules)
  Amortization                   from schedules or IS
  Stock-Based Compensation       =IS!SBC
  Other Non-Cash Items           hardcoded or zero
  Change in Receivables          =-(Current AR - Prior AR)
  Change in Inventory            =-(Current Inv - Prior Inv)
  Change in Payables             =Current AP - Prior AP
  Change in Other Working Capital formula
─────────────────────────────────────────────────────
Cash From Operations (CFO)       =SUM

Cash From Investing
─────────────────────────────────────────────────────
  Capital Expenditure            =-(Revenue × CapEx% from Drivers)
  Acquisitions / Investments     hardcoded or zero
  Other Investing                hardcoded or zero
─────────────────────────────────────────────────────
Cash From Investing (CFI)        =SUM

Cash From Financing
─────────────────────────────────────────────────────
  Net Debt Issuance / (Repayment) from debt schedule or hardcoded
  Equity Issuance / SBC Exercise  hardcoded or zero
  Dividends Paid                  =-(Net Income × Payout Ratio)
  Other Financing                 hardcoded or zero
─────────────────────────────────────────────────────
Cash From Financing (CFF)        =SUM

Net Change in Cash               =CFO + CFI + CFF
  FX Effect                      hardcoded or zero
Net Change in Cash (incl. FX)    =Net Change + FX
Beginning Cash                   =Prior period Ending Cash (or BS!Cash for first projected year)
Ending Cash                      =Beginning + Net Change

⚠️ CASH TIE-OUT                  =Ending Cash - BS!Cash (MUST = 0)

─────────────────────────────────────────────────────
Free Cash Flow                   =CFO - CapEx (positive CapEx as absolute value)
  FCF Margin %                   =FCF / Revenue
```

### Critical Rules
- **Cash Tie-Out**: Ending Cash MUST equal Balance Sheet Cash for every period
- **Working capital changes**: Derived from BS changes (formulas, not hardcoded)
- **CapEx**: Driven by Operating Drivers assumption (formula)
- **FCF definition**: CFO - CapEx (standard definition)

---

## Tab 7: DCF

### Purpose
Discounted Cash Flow valuation from projected FCF to per-share equity value.

### Structure

```
Section A: WACC Calculation
─────────────────────────────────────────────────────
Risk-Free Rate               hardcoded (10Y govt bond yield)
Beta                         hardcoded (from data source)
Equity Risk Premium          hardcoded (market-specific: A股 6-7%, US 4.5-5.5%, HK 5.5-6.5%)
Size Premium                 hardcoded (0-3% based on market cap)
Cost of Equity (Ke)          =Rf + Beta × ERP + Size Premium
Cost of Debt (pre-tax)       hardcoded (weighted avg interest rate)
Tax Rate                     =Operating Drivers tax rate
Cost of Debt (after-tax)     =Kd × (1 - Tax Rate)
Equity Weight (E/V)          =Market Cap / (Market Cap + Debt)
Debt Weight (D/V)            =1 - Equity Weight
WACC                         =Ke × E/V + Kd(1-t) × D/V

Section B: FCF Projection + Discounting
─────────────────────────────────────────────────────
                             FY+1E    FY+2E    FY+3E    FY+4E    FY+5E
Revenue                      =IS link
EBIT                         =IS link
NOPAT (EBIT × (1-t))        formula
+ D&A                        =IS link
- CapEx                       =CF link
- Change in NWC               =CF link (or BS-derived)
─────────────────────────────────────────────────────
Unlevered FCF (UFCF)         =NOPAT + D&A - CapEx - ΔNWC
Discount Factor              =1 / (1 + WACC)^year
PV of UFCF                   =UFCF × Discount Factor

Section C: Terminal Value
─────────────────────────────────────────────────────
Terminal Growth Rate          hardcoded (1.5-4% based on market)
Terminal UFCF                 =FY+5 UFCF × (1 + g)
Terminal Value (Gordon)       =Terminal UFCF / (WACC - g)
PV of Terminal Value          =TV × Discount Factor for Year 5

⚠️ TV as % of EV             =PV(TV) / EV (flag if >80%)

Section D: Equity Bridge
─────────────────────────────────────────────────────
Sum of PV(UFCF)              =SUM of discounted FCFs
PV of Terminal Value          from above
Enterprise Value              =Sum PV(UFCF) + PV(TV)
- Net Debt                    =(Total Debt - Cash) from BS
- Minority Interest           from BS
- Preferred Stock             if applicable
+ Associates / JVs            if applicable
─────────────────────────────────────────────────────
Equity Value                  =EV - Net Debt - MI - Preferred + Associates
Diluted Shares Outstanding    from Operating Drivers
Equity Value per Share        =Equity Value / Shares

Current Price                 hardcoded
Upside / (Downside) %        =(Implied - Current) / Current
```

### Rules
- WACC reasonability: Must be within market-typical range (see `valuation/dcf-and-sensitivity.md` §Part 1 — WACC Calculation)
- All FCF inputs are formula links to IS/CF tabs (not hardcoded)
- Terminal Value sanity check row is mandatory

---

## Tab 8: Comps

### Purpose
Comparable company analysis with mandatory statistical summary.

### Structure

```
Section A: Comparable Companies
─────────────────────────────────────────────────────
Company | Ticker | Market Cap | Revenue(TTM) | EBITDA(TTM) | Net Income | EV/Rev | EV/EBITDA | P/E(TTM) | P/E(NTM) | P/B | P/S | PEG
[Comp 1] | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ...
[Comp 2-10] ...
[Target Company — highlighted row]

Section B: Statistical Summary (MANDATORY)
─────────────────────────────────────────────────────
           | EV/Rev | EV/EBITDA | P/E(TTM) | P/E(NTM) | P/B | P/S
Maximum    | formula | formula  | formula  | formula  | formula | formula
75th Pctl  | formula | formula  | formula  | formula  | formula | formula
Median     | formula | formula  | formula  | formula  | formula | formula
Mean       | formula | formula  | formula  | formula  | formula | formula
25th Pctl  | formula | formula  | formula  | formula  | formula | formula
Minimum    | formula | formula  | formula  | formula  | formula | formula

[Target]   | actual  | actual   | actual   | actual   | actual  | actual
Percentile | formula | formula  | formula  | formula  | formula | formula

Section C: Implied Valuation Range
─────────────────────────────────────────────────────
Method          | Low (25th) | Mid (Median) | High (75th)
EV/EBITDA       | formula    | formula      | formula
P/E (NTM)       | formula    | formula      | formula
Implied Price   | formula    | formula      | formula
vs. Current     | formula    | formula      | formula
```

### Rules
- Minimum 5 comparable companies (ideally 8-10)
- Statistical summary with Max/75th/Median/25th/Min is **MANDATORY** (non-negotiable)
- All statistics use Excel formulas (PERCENTILE.INC, MEDIAN, MAX, MIN)
- Target company row uses `.row-highlight` equivalent formatting
- Currency unified per `valuation/comparable.md` rules

---

## Tab 9: Sensitivity (Recommended)

### Structure

```
Section A: WACC × Terminal Growth (Primary — MANDATORY if DCF tab exists)
─────────────────────────────────────────────────────
                g=1.5%    g=2.0%    g=2.5%    g=3.0%    g=3.5%
WACC=X-1.0%     formula   formula   formula   formula   formula
WACC=X-0.5%     formula   formula   formula   formula   formula
WACC=X (base)   formula   formula   [BASE]    formula   formula
WACC=X+0.5%     formula   formula   formula   formula   formula
WACC=X+1.0%     formula   formula   formula   formula   formula

Section B: Revenue CAGR × Terminal EBITDA Margin (Optional)
─────────────────────────────────────────────────────
Same 5×5 grid structure
```

### Rules
- Center cell = DCF base case value (formula linking to DCF tab)
- All cells are formulas that recalculate when DCF inputs change
- Symmetric ranges around base case

---

## Tab 10: Scenarios (Recommended)

### Structure

```
                        Bull Case    Base Case    Bear Case
Probability              XX%          XX%          XX%
─────────────────────────────────────────────────────
Key Assumptions:
  Revenue CAGR (5Y)      X%           X%           X%
  Terminal Gross Margin   X%           X%           X%
  Terminal Op Margin      X%           X%           X%
  WACC                    X%           X%           X%
  Terminal Growth         X%           X%           X%
─────────────────────────────────────────────────────
Outputs:
  FY+2 Revenue            formula      formula      formula
  FY+2 EPS                formula      formula      formula
  DCF Value/Share         formula      formula      formula
  Target P/E              X            X            X
  Implied Price           formula      formula      formula
─────────────────────────────────────────────────────
Probability-Weighted Price  =SUM(Prob × Price)
Current Price               hardcoded
Upside/(Downside)           formula
```

### Rules
- Bull + Base + Bear probabilities = 100%
- Base probability: 45-60%
- Each scenario's outputs should be formula-driven where possible

---

## Excel Formatting Standards

### Font Colors (Data Type Convention)
| Color | Meaning |
|-------|---------|
| **Blue** | Hardcoded input / assumption (user can change) |
| **Black** | Formula / calculated value |
| **Green** | Cross-sheet link (formula referencing another tab) |

### Number Formatting
| Type | Format | Example |
|------|--------|---------|
| Revenue / large numbers | #,##0 | 96,773 |
| Per-share values | #,##0.00 | 4.73 |
| Percentages | 0.0% | 18.3% |
| Negative values | (#,##0) in red or parentheses | (1,234) |
| Ratios (PE, PB) | 0.0x | 25.3x |

### Layout Standards
- Row 1: Company name + tab description + currency
- Row 3: Column headers (years)
- Section headers in bold with light gray background
- Totals / subtotals with top border
- Balance check / tie-out rows with conditional formatting (green if 0, red if ≠0)

---

## Model Integrity Checks (Agent Must Verify)

Before declaring Task 2 complete, the agent MUST verify:

| # | Check | Method | Pass Criteria |
|---|-------|--------|---------------|
| 1 | BS balances | =Total Assets - Total L&E | = 0 for all periods |
| 2 | Cash ties | =CF Ending Cash - BS Cash | = 0 for all periods |
| 3 | Revenue ties | =Revenue Model Total - IS Revenue | = 0 for all periods |
| 4 | Historical accuracy | Compare IS/BS/CF to Raw Data | Difference < 1% |
| 5 | WACC range | Check vs market-typical range | Within normal range (flag if outside) |
| 6 | TV % of EV | =PV(TV) / EV | < 80% (flag if higher) |
| 7 | Sensitivity center | =Sensitivity center cell - DCF base | = 0 |
| 8 | Comps stats | Check PERCENTILE formulas work | No #N/A or #REF errors |
| 9 | Scenarios sum | =Bull% + Base% + Bear% | = 100% |
| 10 | FCF sign | Check FCF is positive for base case | Positive (flag if negative with explanation) |

**If any check fails**: Fix the model before proceeding. Do NOT deliver a broken model.

---

## Implementation Notes for Agent

### Using openpyxl (Python)

The agent builds the Excel file using Python's `openpyxl` library:

```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers

wb = openpyxl.Workbook()

# Color conventions
BLUE_FONT = Font(color="0000FF")        # Hardcoded inputs
BLACK_FONT = Font(color="000000")        # Formulas
GREEN_FONT = Font(color="008000")        # Cross-sheet links
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
SECTION_FILL = PatternFill("solid", fgColor="F2F2F2")

# Number formats
PCT_FORMAT = '0.0%'
NUM_FORMAT = '#,##0'
DECIMAL_FORMAT = '#,##0.00'
```

### Formula Patterns

```python
# Cross-sheet reference (green font)
cell.value = "='Income Statement'!G6"
cell.font = GREEN_FONT

# Within-sheet formula (black font)
cell.value = "=G6-G7"
cell.font = BLACK_FONT

# Hardcoded assumption (blue font)
cell.value = 0.19
cell.font = BLUE_FONT
cell.number_format = PCT_FORMAT
```

### Key Principle
Every projected number must be either:
1. A **blue hardcoded assumption** in Operating Drivers (with Source + Rationale), or
2. A **formula** that references other cells

There should be ZERO unexplained hardcoded numbers in projected columns of IS/BS/CF tabs.
