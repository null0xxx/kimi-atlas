---
name: dcf-analysis
description: Build, review, or standardize discounted cash flow valuation models and implied share-price outputs in an investment-banking style Excel format. Use when Agent needs to extend a completed three-statement model into a DCF, calculate NOPAT and unlevered free cash flow, derive WACC with transparent assumptions, estimate terminal value and enterprise value, bridge to equity value and implied share price, or present DCF sensitivities in a professional banking layout.
---

# DCF Analysis

## Overview

Build a DCF as a clean extension of an existing forecast model, not as a disconnected valuation page. The model should start from forecast operating data, calculate `NOPAT`, derive `Unlevered Free Cash Flow`, build a transparent `WACC`, calculate `Terminal Value`, discount to `Enterprise Value`, bridge to `Equity Value`, and end with `Implied Share Price` plus sensitivity tables.

The output should be compact, auditable, and presentation-ready. Default to a banker-style Excel layout with disciplined color usage, explicit hardcode vs. formula distinction, minimal borders, and clearly labeled sections.

The DCF must also show real market judgment and business sense. The forecast linkage, `WACC`, terminal assumptions, valuation bridge, and sensitivities should reflect a defendable understanding of the market, the company, the business model, and how investors would underwrite the valuation. Do not choose assumptions mechanically; show business understanding through the numbers.

If the user does not provide a fixed layout requirement and does not upload a template workbook to mimic, default to the embedded `# DCF Format Reference` section in this file.

## Workflow

1. Define the valuation frame.
   Confirm `valuation date`, `currency`, `units`, forecast horizon, tax convention, discounting convention, terminal value method, diluted share-count convention, and bridge-year balance sheet date. If the user does not specify, default to `5-year explicit forecast`, `mid-year convention`, `perpetuity growth` as the primary terminal method, and `exit multiple` as a cross-check.

2. Link forecast data from the operating model.
   Pull forecast lines directly from the existing model rather than retyping values. At minimum, link `Revenue`, `EBIT`, `Depreciation`, `Amortization`, `Capex`, `Operating Working Capital` or its components, tax rate, cash, debt, lease liabilities when relevant, and diluted shares.

3. Build the `NOPAT -> UFCF` schedule.
   Use operating income as the starting point. The default structure is:
   - `EBIT`
   - `Less: Taxes on EBIT`
   - `NOPAT`
   - `+ D&A`
   - `- Capex`
   - `- Increase in Operating Working Capital`
   - `+/- Other recurring operating adjustments` only when clearly justified
   - `= Unlevered Free Cash Flow`

4. Build a transparent `WACC`.
   Show `Cost of Equity`, `Cost of Debt`, capital structure weights, tax shield, and any premiums or adjustments. `WACC` must be explainable from visible assumptions. Do not hardcode a final rate without showing how it was built.

5. Calculate `Terminal Value`.
   Use `Perpetuity Growth Method` as the default primary method. Use `Exit Multiple Method` as a cross-check when the business and market context support it. Make sure the terminal base and the terminal multiple are consistent.

6. Discount the forecast and terminal value.
   Discount explicit-period `UFCF` and `Terminal Value` separately. Use `mid-year convention` by default unless the user requests year-end discounting or the workbook structure makes year-end discounting more appropriate.

7. Bridge `EV` to `Equity Value` and `Implied Share Price`.
   Start from `Enterprise Value`, subtract net debt and other senior claims, add non-operating assets when justified, then divide by diluted shares. Keep the bridge explicit and traceable.

8. Build sensitivity analysis.
   At minimum, include one two-way sensitivity table. Default sensitivity tables:
   - `WACC x Terminal Growth`
   - `WACC x Exit Multiple` when an exit multiple is shown
   - Sensitivity table values must be formula-driven in Excel. Do not hardcode the sensitivity body with pre-calculated numbers from Python or manual paste.

9. Review before delivery.
   Check signs, units, years, tax treatment, terminal assumptions, discount factors, net debt bridge, and diluted share count. Confirm the sensitivity tables move in the right direction: higher `WACC` lowers value; higher `g` or `exit multiple` raises value.

## Output Rules

- Default to one dedicated `DCF` tab unless the user asks for a different workbook structure.
- Keep the page compact. Do not create large presentation-style gaps that hide the math.
- Keep hardcodes visibly distinct from formulas at all times.
- Use one year-label style across the full sheet. Do not mix `2028E`, `'28`, and `LTM` without explicit reason.
- Show one clear base case and use cross-checks only as secondary support.
- Display `--` or `NM` instead of visible Excel errors or broken formulas.

## Decision Rules

- If the user does not specify otherwise, use `5 years` of explicit forecast.
- Use `NOPAT = EBIT x (1 - tax rate)` as the default operating after-tax profit measure.
- `UFCF` must remain unlevered and pre-debt. Do not include interest expense, debt issuance, debt repayment, or dividends.
- Use market-value capital structure weights for `WACC` unless the user explicitly requests another method.
- Default `Cost of Equity` to `CAPM`.
- Add `size premium`, `country risk premium`, or company-specific premium only when there is a visible rationale.
- Use a normalized operating tax rate where possible instead of a distorted one-off effective tax rate.
- Keep `Terminal Growth Rate < WACC`.
- Make sure terminal multiples match the terminal operating base.
- If terminal value drives an unusually high share of `EV`, surface that sensitivity explicitly.
- Default to diluted shares for per-share value.

## Modeling Rules

### Forecast Linkage

- Link forecast operating data directly from the model.
- Avoid hardcoding values in formulas. Do not write formulas such as `=36726*(1+C12)`; instead, reference the appropriate source cells, including across worksheets when needed.
- Do not rebuild a second operating forecast inside the DCF page.
- If operating working capital is not already shown clearly, add a support block that defines what is included in operating current assets and operating current liabilities.

### `NOPAT -> UFCF`

Default formulas:

- `Taxes on EBIT = EBIT x tax rate`
- `NOPAT = EBIT - Taxes on EBIT`
- `UFCF = NOPAT + D&A - Capex - Change in Operating Working Capital`

Treatment rules:

- Use sustainable operating tax assumptions.
- Add back `D&A` because it is non-cash, but avoid double counting with other adjustments.
- Use cash capex rather than a depreciation proxy unless the user asks for a steady-state simplification.
- Include only operating working capital items in `Change in Operating Working Capital`.
- Do not mechanically add back `SBC` unless share dilution treatment remains consistent.

### `WACC`

Build `WACC` step by step:

1. `Cost of Equity`
   Default:
   - `Cost of Equity = Risk-Free Rate + Levered Beta x Equity Risk Premium`
   Optional:
   - `+ Size Premium`
   - `+ Country Risk Premium`
   - `+ Company-Specific Premium`

2. `Beta`
   When a peer beta build is needed:
   - Gather peer `levered beta`
   - Calculate `D / E` and tax rate
   - `Unlevered Beta = Levered Beta / (1 + (1 - tax rate) x D / E)`
   - Use selected-peer `median` or a justified average
   - Relever to the target capital structure:
     `Relevered Beta = Unlevered Beta x (1 + (1 - target tax rate) x target D / E)`

3. `Cost of Debt`
   Preferred sources:
   - Current borrowing rate or bond yield
   - Credit spread / rating-based estimate
   - `Interest Expense / Average Debt` as fallback

4. Capital Structure Weights
   Default:
   - `E / V = Market Value of Equity / (Market Value of Equity + Market Value of Debt)`
   - `D / V = Market Value of Debt / (Market Value of Equity + Market Value of Debt)`

5. Tax Shield
   - `After-Tax Cost of Debt = Pre-Tax Cost of Debt x (1 - tax rate)`

6. Final `WACC`
   - `WACC = (E / V x Cost of Equity) + (D / V x After-Tax Cost of Debt)`

### `Terminal Value`

Primary method:

- `TV = Final Year UFCF x (1 + g) / (WACC - g)`

Rules:

- `g` must be below `WACC`
- `g` must be realistic for mature long-term nominal growth
- The final-year `UFCF` should be close to a sustainable level

Cross-check method:

- `TV = Terminal Metric x Exit Multiple`

Rules:

- Match metric and multiple correctly, for example `EBITDA` with `EV / EBITDA`
- Use an exit multiple that can be explained by trading context or peer evidence

### Discounting

- Use `mid-year convention` by default
- Show discount periods and discount factors explicitly
- `PV of UFCF = UFCF / Discount Factor`
- `PV of TV = TV / Discount Factor`
- `Enterprise Value = Sum of PV of UFCFs + PV of TV`

### `EV -> Equity Value -> Price`

Default bridge:

- `Enterprise Value`
- `Less: Net Debt`
- `Less: Preferred Equity`
- `Less: Minority Interest`
- `Add: Non-operating Cash / Investments / Associates` when appropriate
- `= Equity Value`
- `Equity Value / Diluted Shares = Implied Share Price`

Rules:

- Use balance sheet values that match the valuation date or bridge year
- Avoid double counting items already reflected in `EV` or `UFCF`
- Let net cash situations flow through naturally
- If `Equity Value` or `Implied Share Price` is negative in the base case, do not pass through the result mechanically. Recheck the operating forecast, sign conventions, net debt bridge, non-operating adjustments, diluted share count, and any other core valuation logic, and only treat the output as deliverable after confirming the result is justified.

## Validation

Before finishing, confirm:

1. Every DCF forecast line ties to the model.
2. `NOPAT` excludes financing effects.
3. `UFCF` treatment for `D&A`, `Capex`, and working capital is internally consistent.
4. `WACC` assumptions are visible and traceable.
5. `g < WACC`.
6. Terminal bases and terminal methods are matched correctly.
7. Discount factors increase with time.
8. The `EV -> Equity Value` bridge does not double count items.
9. Share count treatment is consistent with dilution assumptions.
10. Sensitivity tables move in the expected direction.
11. If the base-case `Equity Value` or `Implied Share Price` is negative, the model logic has been rechecked and the result has been confirmed as justified before delivery.

## Deliverable Shape

For Excel delivery, include:

1. A title and context box
2. A `NOPAT -> UFCF` schedule
3. A detailed `WACC` build
4. A `Terminal Value` and discounting block
5. An `Enterprise Value -> Equity Value -> Implied Share Price` bridge
6. At least one two-way sensitivity table
7. Support blocks for beta, capital structure, or net debt when needed

For text delivery, summarize:

1. Base-case `WACC`
2. Base-case terminal assumption
3. `Enterprise Value`
4. `Equity Value`
5. `Implied Share Price`
6. Key sensitivity takeaways
7. Main valuation caveats

# DCF Format Reference

This is the canonical DCF page layout reference for the agent to refer unless users query asked differently or provide templates. **Use the same language as the user's query when referring to this format**

Use one dedicated `DCF` tab by default. Keep the page compact. Do not introduce presentation-style blank space.

## 1. Sheet skeleton

```text
Merged Title:                 B1:H1
Title Box Labels / Values:    B3:C8
Context / Notes Box:          E3:H8

Section Bar:                  B9:G9     NOPAT to Unlevered Free Cash Flow
Header Row:                   B10:G10
Data Rows:                    B11:G28

Section Bar:                  K12:P12   WACC Build and Key Assumptions
Header Row:                   K13:M13
Assumption Rows:              K14:P27

Section Bar:                  B30:G30   Terminal Value and Discounting
Header Row:                   B31:G31
Terminal Rows:                B32:G44
Model Notes Box:              K31:P37

Section Bar:                  B46:C46   Enterprise Value to Implied Share Price
Header Row:                   B47:C47
Bridge Rows:                  B48:C57

Section Bar:                  B61:P61   Sensitivity Analysis
Left Sensitivity Title:       B63:G63   Implied Share Price - WACC vs Terminal Growth
Right Sensitivity Title:      J63:O63   Implied Share Price - WACC vs Exit Multiple
Sensitivity Headers:          B64:G64 and J64:O64
Sensitivity Bodies:           C65:G69 and K65:O69
```

## 2. Title block

```text
B1:H1   Target Name - DCF Valuation

B3      Ticker               C3      [yellow fill + dashed outer border]
B4      Date                 C4      yyyy/m/d
B5      Currency             C5      RMB / USD / reported currency
B6      Units                C6      RMB mn / USD mn
B7      Convention           C7      Mid-Year
B8      Terminal Method      C8      Perpetuity Growth

E3:H8   Context / valuation notes
        - bridge year
        - forecast years discounted
        - terminal method
        - net debt bridge notes
```

Rules:

- Only `C3` uses yellow fill and dashed border by default. `C4:C8` should not use yellow fill.
- Labels in column `B` are bold and left-aligned.
- The title sits in the upper left; do not center it across the sheet.

## 3. NOPAT to UFCF block

```text
Section Bar: B9:G9

B10   Line Item     C10   2025E / 2026E / ...   through the final forecast year

B11   Revenue
B12   EBIT
B13   EBIT Margin
B14   Tax Rate
B15   Taxes on EBIT
B16   NOPAT
B17   Depreciation
B18   Amortization
B19   D&A
B20   Cash Capex
B21   Intangible Additions
B22   Total Reinvestment
B23   Operating Current Assets
B24   Operating Current Liabilities
B25   Operating Working Capital
B26   Change in Operating WC
B27   UFCF
B28   UFCF Margin
```

Rules:

- Keep the first column left-aligned and the year columns centered in the header.
- Link forecast rows directly from the operating model whenever possible.
- Important subtotal rows such as `NOPAT` and `UFCF` are bold.

## 4. WACC block

```text
Section Bar: K12:P12

K13   Assumption    L13   Value    M13:P13   Rationale

K14   Risk-free rate
K15   Equity risk premium
K16   Levered beta
K17   Company-specific premium
K18   Cost of equity
K19   Pre-tax cost of debt
K20   Tax rate
K21   After-tax cost of debt
K22   Target debt weight
K23   Target equity weight
K24   WACC
K25   Terminal growth rate
K26   Exit EV / EBITDA
K27   Diluted shares
```

Rules:

- `K13:M13` uses header fill and bold text.
- Hardcoded assumptions in column `L` use bright blue font.
- Formula outputs remain black.
- The rationale text runs across `M:P` and wraps.

## 5. Terminal value and discounting block

```text
Section Bar: B30:G30

B31   Line Item      C31:... final forecast years
B32   UFCF
B33   Discount Period
B34   Discount Factor
B35   PV of UFCF
B36   Terminal UFCF
B37   TV @ Perpetuity Growth
B38   Terminal EBITDA
B39   TV @ Exit Multiple
B40   PV of Terminal Value
B41   PV of TV @ Exit Multiple
B42   PV of Interim UFCF
B43   Enterprise Value (Perpetuity)
B44   Enterprise Value (Exit Multiple)

K31:P37   compact model notes box
```

Rules:

- Use mid-year discounting by default.
- `Enterprise Value` output rows are bold.
- The section bar must stop at column `G`; do not extend it farther.

## 6. EV bridge

```text
Section Bar: B46:C46

B47   Line Item                      C47   Value
B48   Enterprise Value (Perpetuity)
B49   Less: Debt & Lease Liabilities
B50   Less: Minority Interest / Other Senior Claims
B51   Add: Cash & Short-Term Investments
B52   Add: Non-operating Investments (when justified)
B53   Equity Value
B54   Diluted shares
B55   Implied Price
B56   TV / EV %
B57   EV / Terminal Metric
```

Rules:

- Keep this block narrow and compact.
- `Equity Value` and `Implied Price` are bold.
- Do not hide the bridge logic inside one net-debt line if more explicit rows improve auditability.

## 7. Sensitivity layout

```text
Section Bar: B61:P61

Left Table
B63:G63   Implied Share Price - WACC vs Terminal Growth
B64       g / WACC
C64:G64   WACC headers
B65:B69   terminal growth headers
C65:G69   body

Right Table
J63:O63   Implied Share Price - WACC vs Exit Multiple
J64       Exit / WACC
K64:O64   WACC headers
J65:J69   exit multiple headers
K65:O69   body
```

Rules:

- Header rows use light blue-gray fill.
- Label the axes explicitly.
- Keep the tables compact and aligned on one baseline.
- A soft red-yellow-green scale is acceptable in the body, but keep it restrained.

## 8. Core formatting rules

- Font: `Arial`
- Title: `Arial` 14-16 bold
- Body: `Arial` 8-10
- Header fill: light blue-gray close to `#D9E2F3`
- Section bar fill: deep navy close to `#0F243E`, white bold text
- Input fill: pale yellow close to `#FFF2CC`
- Hardcode font: bright blue `#0000FF`
- Standard labels and formulas: black
- Do not over-border the page
- Do not make section bars longer than the tables they introduce
- Do not apply yellow fill to every input
- Do not introduce green summary-row styling from comps pages

## 9. What the agent should preserve

- the compact `title block + note box` structure
- the exact section order
- the narrower `EV bridge` block
- the two-table sensitivity finish at the bottom
- restrained banker-style spacing instead of slide-style spacing
