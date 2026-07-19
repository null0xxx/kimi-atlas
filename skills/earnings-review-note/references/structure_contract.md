# Structure Contract - Equity Earnings Review

## Reference Source

Extracted from institutional sell-side equity research earnings review documents.

## Document Section Hierarchy

### Section 1: Cover / Summary (Page 1)

**Top banner**: Firm logo left, "Equity Research" right, publication date + time below right

**Title block** (full width):
- Company Name + (TICKER) in large bold
- Report subtitle: "[Quarter] review: [key theme]" -- descriptive headline

**Two-column body begins**:

**Left column (~60%):**
- Rating + Price target summary bar: TICKER | 12m Price Target: $XXX.XX | Price: $XXX.XX | Upside/Downside: X.X%
- Executive summary paragraph(s): 200-400 words total
  - Open with the headline metric (e.g., "X's F4Q26 EPS of $X.XX beat house/consensus of $X.XX/$X.XX")
  - State the primary driver of the beat/miss
  - Mention guidance/outlook takeaway in the opening paragraph
  - Second paragraph: strategic context, product updates, themes
- Standard disclaimer text block at bottom (~60 words)

**Right column (~40%):**
- **Rating box**: Large solid color block (Buy=green, Neutral=dark charcoal, Sell=red, Not Rated=gray) with rating text in white and date of rating change
- **Analyst block**: Name(s), CFA designations, phone, email, firm
- **Key Data** section with horizontal rule:
  - Market cap
  - Enterprise value
  - 3m ADTV (Average Daily Trading Volume)
  - Country / sector coverage classification
  - M&A Rank (if applicable)
- **Forecast** table (horizontal rule separator):
  - Rows: Revenue ($ mn) New/Old, EBITDA ($ mn), EBIT ($ mn), EPS ($) New/Old, P/E (X), Dividend yield (%), Net debt/EBITDA (X)
  - Columns: Current FY, +1E, +2E, +3E
  - Quarterly EPS row: Q1, Q2, Q3, Q4 of current FY with $ values (e.g., "12/25, 3/26E, 6/26E, 9/26E")
- **Factor Profile** chart (horizontal bar chart): Growth, Financial Returns, Multiple, Integrated vs. percentile scale
- Source note: "Source: Company data, [Firm Name] Research estimates. See disclosures for details."

### Section 2: Financial Snapshot (Page 2)

**Rating box** (top left): Rating + "Rating since [date]" in solid color block
**Company name** (top right of content area): Company Name (TICKER) in bold

**Six financial table groupings** arranged compactly in a 2-column layout covering the full page:

1. **Ratios & Valuation** (left, top):
   - Columns: Current FY, +1E, +2E, +3E (labeled by fiscal year end, e.g., "12/25", "12/26E")
   - Rows: P/E (X), EV/EBITDA (X), EV/sales (X), FCF yield (%), EV/DACF (X), CROCI (%), ROE (%), Net debt/EBITDA (X), Net debt/equity (%), Interest cover (X), Inventory days, Receivable days, Days payable outstanding

2. **Growth & Margins (%)** (left, middle):
   - Rows: Total revenue growth, EBITDA growth, EPS growth, DPS growth, Gross margin, EBIT margin

3. **Price Performance** (left, bottom):
   - Stock price line chart vs. S&P 500 (see style_contract.md for chart spec)
   - 3m / 6m / 12m absolute and relative performance stats
   - Source: FactSet
   - **This is a MANDATORY element** on the Financial Snapshot page

4. **Income Statement ($ mn)** (right, top):
   - Rows: Total revenue, Cost of goods sold, SG&A, R&D, Other operating inc./(exp.), EBITDA, D&A, EBIT, Net interest inc./(exp.), Income/(loss) from associates, Pre-tax profit, Provision for taxes, Minority interest, Preferred dividends, Net inc. (pre-exceptionals), Net inc. (post-exceptionals), EPS (basic, pre-except), EPS (diluted, pre-except), EPS (ex-ESO exp., dil.), DPS, Div. payout ratio, Wtd avg shares out. (basic/diluted)

5. **Balance Sheet ($ mn)** (right, middle):
   - Rows: Cash & equivalents, Accounts receivable, Inventory, Other current assets, Total current assets, Net PP&E, Net intangibles, Total investments, Other LT assets, Total assets, AP, Short-term debt, Current lease liabilities, Other current liabilities, Total current liabilities, Long-term debt, Non-current lease liabilities, Other LT liabilities, Total LT liabilities, Total liabilities, Preferred shares, Total common equity, Minority interest, Total L&E, BVPS

6. **Cash Flow ($ mn)** (right, bottom):
   - Rows: Net income, D&A add-back, Minority interest add-back, Net inc/(dec) working capital, Others, Cash flow from operations, CapEx, Acquisitions, Divestitures, Others, Cash flow from investing, Dividends paid, Share issuance/(repurchase), Inc/(dec) in debt, Others, Cash flow from financing, Total cash flow, Free cash flow, FCF per share (basic)

Source line: "Source: Company data, [Firm Name] Research estimates."

### Section 3: Detailed Analysis (Pages 3-6)

**Hierarchical text commentary** using three-level bullet hierarchy. Content flows continuously across pages without premature breaks.

#### 3.1 Key Takeaways from the Quarter
- Level-1 bullets summarizing each major result (by segment)
  - "**[Segment] revenue of $X.X bn beat HouseE of $X.X bn and [guidance/consensus]...**"
  - "**Gross profit / EBITDA / EBIT of $X beat HouseE/consensus $X/$X...**"
- Level-2 bullets for sub-segment detail
  - Within segment revenue drivers, margin commentary, volume/unit metrics
- Level-3 bullets for product-level or geographic detail

#### 3.2 Segment Financial Results
- Revenue, gross margin, operating margin by reported segment
- Comparison against estimates and prior periods
- Volume / unit economics (applicable to product companies)

#### 3.3 Product / Strategic Updates
- Sub-sections by business line or product category
- Management commentary on key initiatives
- Competitive positioning notes

#### 3.4 Financial Outlook and Commentary
- Guidance recap: forward quarter + full-year expectations
- Capex plans and capital allocation commentary
- Cost/margin trajectory expectations

#### 3.5 Estimate Changes
- Summary sentence: "We [raise/lower] our [FY] estimates by X% on average driven by..."

#### 3.6 Valuation, Price Target, and Key Risks
- Rating statement: "We are [Buy/Neutral/Sell] rated on [COMPANY] with a 12-month target price of $XXX (v. $XXX prior) based on X.Xx [multiple] our [method]."
- Key risks: 5-10 bullet points covering upside and downside scenarios

### Section 4: Exhibits (detailed tables)

Each exhibit is a full-width table labeled:

> **Exhibit N: [Descriptive Title]**
> *$ mn, except per-share data*

Exhibits appear inline with the analysis -- not collected at the end. They often follow the estimate/valuation section (around pages 6-7).

**Standard Exhibits (varies by company):**

1. **Exhibit 1: Variance Summary** -- Actual vs. House Estimate vs. Street (FactSet) vs. Guidance
   - Rows: Revenue, Gross profit, Operating income, EBIT margins, Net income, Diluted EPS (GAAP and Non-GAAP)
   - Columns: Actual ($, %, YoY%), HouseE ($, YoY%), Street ($, YoY%), Guidance (Low/High), Actual vs. HouseE, Actual vs. Street, Actual vs. Guidance
   - Segment-level breakdown below (if multi-segment company)

2. **Exhibit 2: Guidance Summary**
   - Forward quarter and full-year guidance
   - Columns: Guidance (Low-end / High-end), Street (FactSet) ($), Mid-point outlook vs. Street
   - Rows: Revenue, Diluted EPS (GAAP and Non-GAAP)

3. **Exhibit 3: Estimate Changes**
   - Full P&L line items for multiple fiscal years
   - Columns grouped by: Current FY, Next FY, +2 FY -- each showing Current | Prior | Delta ($) | Delta (%)
   - Rows: Revenue, Cost of sales, Gross profit, SG&A, R&D, Operating income, Interest, Earnings before tax, Tax rate, Net income (GAAP/non-GAAP), Diluted shares, Diluted EPS, Adjusted EBITDA
   - Segment details section below (for multi-segment companies)
   - This is typically a compact table that may share a page with valuation/risk commentary

4. **Exhibit 4+: Income Statement Model** (detailed quarterly + annual)
   - Quarterly columns: 8-12 historical/projected quarters
   - Annual columns: 4-5 fiscal years
   - Rows: Full P&L with YoY growth (%) rows below

### Section 5: Back Matter (Pages 8-11)

**Estimate and price target changes** (separate mini-section before disclosures)
- One-paragraph summary of estimate revision rationale
- May include a mini "Updated [TICKER] estimates" table (small exhibit with old HouseE vs. new HouseE)

**Disclosure Appendix**:
- Reg AC certification (analyst name(s), statement of view accuracy)
- Factor Profile methodology explanation
- M&A Rank methodology
- Quantum database description
- Company-specific regulatory disclosures (investment banking relationships, compensation)
- Distribution of ratings / investment banking relationships table

**Price target and rating history chart**:
- Dual-axis line/area chart showing stock price and rating history over time
- Rating labels (Buy, Neutral, Sell) shown as horizontal bands at standard levels
- Price target history shown as horizontal dashed lines with labels
- Source: [Firm Name] Investment Research for ratings and price targets; FactSet for closing prices

**Regulatory disclosures** (by jurisdiction: US, Australia, Brazil, Canada, Hong Kong, India, Japan, Korea, New Zealand, etc.)

## Exhibit Numbering Rules

- Exhibits numbered sequentially starting from 1
- Each exhibit has a descriptive title following the pattern linking to the ticker
- Subtitle line: "$ mn, except per-share data" (or appropriate units)
- Source attribution below each exhibit table
- Exhibits appear inline with analysis -- not at end of document

## Content Writing Patterns

### Beat/Miss Headline Pattern
"[COMPANY] [PERIOD] [METRIC] of $[ACTUAL] beat/missed house/consensus (FactSet) of $[HouseE]/$[STREET]..."

### Segment Commentary Pattern
"**[Segment] revenue of $[X] [beat/missed] HouseE of $[Y] and [guidance/consensus] of $[Z]**, driven by [driver]."

### Margin Pattern
"Gross margin of [X]% was [above/below] HouseE [Y]% and [above/below] consensus [Z]%, [up/down] [W] bps [qoq/yoy]."

### Estimate Change Pattern
"We [raise/lower] our [FY] [metric] estimates by [X]% to $[NEW] from $[PRIOR], driven by [reason]."

### Rating/Valuation Pattern
"We are [Buy/Neutral/Sell] rated on [COMPANY] with a 12-month target price of $[NEW] (v. $[PRIOR] prior) based on [X.Xx] [multiple] our [NTM+Y EPS / DCF / SOTP]."

## Data Comparison Conventions

- **House estimate references**: "HouseE" for estimate, "[Firm Name]" for generic firm reference
- **Consensus references**: "Street (FactSet)", "Visible Alpha Consensus", "StreetAccount consensus"
- **Guidance references**: "guidance of $X-$Y" or "guidance midpoint of $Z"
- **Variance language**: "beat" / "missed" / "was in-line with"
- **Directional terms**: "driven by" / "offset by" / "more than offsetting" / "benefiting from"
- **Sequential vs. annual**: "qoq" for quarter-over-quarter, "yoy" for year-over-year, "qoq and yoy" when both apply

## Financial Model Table Conventions

### Column Naming
- Historical actuals: [FY][Q] e.g., "4Q25" or "FQ4'26A"
- Forecasts: append "E" e.g., "1Q26E" or "FQ1'27E"
- Fiscal years: "12/25", "12/26E", "12/27E" (matching company's fiscal year-end)
- Alternative format: "FY26A", "FY27E", "FY28E" if fiscal year differs from calendar

### Row Grouping
Bold the following key subtotals:
- Total revenue, Total costs, EBITDA, EBIT, Pre-tax profit, Net income, Total cash flow, Free cash flow
- Segment totals (for multi-segment companies)

### Formatting Rules
- $ mn or $ bn unit in table title
- Percentages with one decimal place
- Per-share figures with two decimal places
- Parentheses for negatives: `(10.5)` not `-10.5`
- NM for "not meaningful" in ratio cells

## Front Matter / Back Matter

**Front matter** (Page 1 only):
- Publication date and time in top-right corner
- [Firm Name] logo in top-left (not plain text)
- Optional: client watermark on left margin

**Back matter** (Pages 8-11):
- No exhibit numbering in back matter
- Disclosure sections use bold sub-headings but no bullets
- Rating distribution tables use simple two-column layouts
- Regulatory text is dense, small-font (9pt), full-width
- Price target and rating history chart appears before regulatory disclosures
