---
name: comps-analysis
description: Build, review, or standardize public-company comparable analysis tables and implied valuation outputs in an investment-banking style format. Use when Agent needs to create a comps workbook, structure a peer database, compute trading multiples, summarize mean/median valuation ranges, estimate implied share prices, or reformat Excel output to match a professional comps-table layout.
---

# Comps Analysis

## Overview

Create a public comps analysis that is structurally clean, numerically defensible, and presentation-ready. Treat the workbook as a database-first model: build a full `DATABASE` section first, pull the displayed comps from that database with references or lookup formulas, calculate growth, margins, and trading multiples from the referenced data, and then drive the implied share price bridge from the displayed trading multiples plus target inputs.

Read [references/workbook_format.md]when building or reformatting the sheet layout, fonts, fills, borders, and conditional formatting. Read [references/model_construction.md] when deciding which cells are database pulls, hardcodes, or formulas. Read [references/calculation_guide.md] when mapping formulas, deciding whether a multiple is meaningful, or checking valuation outputs.

## Workflow

1. Define the frame.
   Capture the target company, audience, task, valuation date, reporting basis (`FY`, `CY`, `LTM`, `NTM`), currency, units, and the fiscal years to show. Do not mix bases inside one table unless the user explicitly asks for it, and label any mix clearly.
   Before building anything, lock one explicit `Year Set` for the entire model, for example `2025A / 2026E / 2027E` or `CY2026E / CY2027E`. Treat this `Year Set` as a hard constraint for the selected comps table, analytics, valuation bridge, and database headers.
   If the user asks for a specific year, such as `2026`, `FY26`, `CY26`, `26E`, or a `2026 ticker`, that year request overrides any generic default. Do not silently fall back to more familiar years such as `2023` and `2024`.

2. Build the database first.
   Start with a broader universe than the final peer set. Include ticker, company name, market data, capital structure fields, and historical or forward operating metrics needed for the multiples. This block must sit below the main output and act as the source of truth for the displayed comps table above.

3. Build the displayed comps table by reference.
   Choose the peer subset that best matches business model, end market, geography, margin profile, scale, and growth profile. A typical top table contains about 6 to 10 names. Pull the base fields for each selected company from the database by direct references, `XLOOKUP`, `INDEX/MATCH`, or `VLOOKUP`. Do not manually retype values in the top table if the database exists.

4. Calculate the analytical blocks from the pulled data.
   Compute the analytical blocks that fit the audience, industry, and task from the pulled data. `Revenue Growth`, `EBITDA Margin`, `Profit Margin`, and `Trading Multiples` are the default public-equity set, but do not force the same metrics across all sectors. Keep formula logic in the analysis area instead of hardcoding computed outputs. Show `NM` or `--` when a metric is not meaningful, such as negative EBITDA for `EV / EBITDA` or negative earnings for `P / E`.

5. Derive valuation outputs.
   Use min, mean, median, and max selected-peer multiples to value the target. The valuation bridge should combine references from the selected comps summary rows, target hardcodes or assumption cells, and formulas. Show the target's financial metric, implied enterprise value, implied equity value, and implied share price. If a multiple values equity directly, such as `P / E`, skip enterprise value and go straight to implied price or implied equity value.

6. Review before delivery.
   Check that units, signs, dates, and currencies are consistent; statistics exclude `NM`; the top table traces back to the database; hardcodes are visibly distinct from formulas; and the implied valuation range is directionally reasonable relative to the current share price.

## Output Rules

- Default to one clean comps sheet rather than splitting across many tabs unless the user asks otherwise.
- Preserve the order and visual hierarchy in [references/workbook_format.md].
- Always include a `DATABASE` section when the sheet contains a comps table. Do not omit it unless the user explicitly requests a presentation-only output.
- Treat the database as the source block and the top table as a selected view of that source block.
- Prefer explicit labels such as `Revenue`, `EBITDA`, `Net Income`, `EV / Revenue`, `EV / EBITDA`, and `P / E`.
- Use the same year labels across the whole sheet. If the table uses 2024 and 2025 multiples, the target valuation bridge should use those same years.
- When the user explicitly names a year window, preserve that exact year window across the whole sheet. For example, if the user wants `2026` trading metrics, the workbook should continue to show `2026`-based headers and calculations.
- If data for a requested year is unavailable for some peers, keep the requested year labels and show `--`, `NM`, or an explicit coverage note. Never replace the requested year with an older year without clearly saying so.
- Use `Mean` and `Median` summary rows in the selected comps table.
- Highlight `Mean` and `Median` in the selected comps table, but do not carry that green highlight into the implied share price bridge.
- Extend the selected-comps `Mean` and `Median` highlight across the full table width and wrap the two-row highlighted block with one thin outer border.
- Exclude blanks and `NM` entries from summary statistics rather than coercing them to zero.
- Use formatting to distinguish cell types: hardcodes, formula outputs, and section headers should not all look the same.
- Keep header content centered and merge cells where the visual grouping requires it.
- Surface data limitations directly in the output if the peer set contains thin coverage, outlier capital structures, or accounting inconsistencies.

## Decision Rules

- Prefer operating comparability over brand recognition when the two conflict.
- Exclude companies with clearly broken comparability from the selected set even if they are in the database.
- Keep loss-making or negative-EBITDA names only when they are economically relevant; otherwise, explain the exclusion.
- Use enterprise-value multiples for capital-structure-neutral comparison and `P / E` only when earnings are positive and not distorted by one-off items.
- If the user does not specify a basis or year set, default to the most recently completed full-year basis for broad comps tables.
- If the user specifies a year set, anchor year, or forward year, that instruction takes priority over the generic default-to-latest rule.
- Do not freeze one universal metric set across industries. Choose metrics based on audience, industry, and task.
- For `Big Tech` comps, default to scale, growth, margin, cash generation, and large-cap trading metrics that matter for mature platform businesses.
- For `SaaS` comps, shift emphasis toward recurring-revenue growth, profitability progression, and revenue-based valuation metrics; many SaaS tables will care more about `EV / Revenue` than `P / E`.
- Apply the same logic to other sectors: banks, insurers, REITs, energy, semis, consumer, industrials, and internet names may each need different operating and valuation metrics.

## Modeling Rules

- Build the `DATABASE` first and only then build the top comps table.
- Define the exact `Year Set` before laying out headers or writing formulas. Every year-bearing section in the workbook must reuse that same locked set.
- Use lookup or direct-link formulas for top-table raw data fields such as `Current Price`, `Share Count`, `Enterprise Value`, `Market Cap`, `Revenue`, `EBITDA`, and `Net Income`.
- Calculate `Revenue Growth`, `EBITDA Margin`, `Profit Margin`, and `Trading Multiples` from the linked raw data instead of linking precomputed outputs from elsewhere when the formulas are straightforward.
- If a column is labeled `2026`, `FY26`, `CY26`, or `26E`, the underlying numerator, denominator, and bridge references must point to that same period. Do not label a column `2026` while feeding it `2023` or `2024` data.
- Adjust which analytical columns appear based on audience, industry, and task. Keep the layout discipline fixed, but let the metric set change when the sector demands it.
- Use blue font `rgb(79, 113, 190)` for manual hardcodes and target inputs, black font for formulas and calculated outputs, and keep ticker labels visually distinct from numeric inputs.
- Use explicit grouped headers so every year column is clearly tied to its metric. Do not leave trading-multiple columns or second-year columns visually unlabeled.
- Keep the title input box minimal by default: `Date` and `Currency` are standard; do not add `Basis` unless the user requests it.
- Use thin black header borders by default rather than gray borders.
- Use a deep navy-blue `DATABASE` divider bar with white text.
- Turn off worksheet gridlines in the delivered Excel output.
- Format title-box dates in slash style `yyyy/m/d`, for example `2022/7/23`, rather than long English month names.
- Format trading-multiple cells with an explicit Excel custom number format that appends a literal `x`, for example `0.0\"x\"`.
- Use conditional formatting only in the analytical blocks where relative performance matters; do not heatmap the entire database.
- Use `--` or `NM` for non-meaningful cells rather than leaving broken formulas or Excel errors visible.

## Deliverable Shape

When returning the result in Excel or spreadsheet form, produce:

1. A title block with the sheet title, date, and currency.
2. A selected comps table whose raw data fields are pulled from the database.
3. Analytical blocks for growth, margins, and trading multiples that calculate from the displayed data.
4. A valuation bridge showing min, mean, median, and max implied values for the target.
5. A larger `DATABASE` table beneath the main output.

When returning the result in text form, summarize:

1. Selected peers and why they fit.
2. Mean and median trading multiples.
3. Implied valuation range and share-price range.
4. The locked `Year Set` used in the workbook.
5. Any caveats that materially affect interpretation, especially if requested-year coverage is incomplete.
