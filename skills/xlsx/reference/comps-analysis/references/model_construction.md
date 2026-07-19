# Model Construction

Use this reference to preserve the logic shown in the screenshot-based comps template. The key principle is `database first, selected comps second, analytics third, valuation bridge last`.

## Construction Order

Build the worksheet in this order:

1. Title and context box
2. `DATABASE` table
3. Selected comps table above the database
4. Growth, margin, and trading multiple calculations inside the selected comps area
5. Mean and median summary rows
6. `Calculating Implied Share Price` bridge

Do not start by typing the top comps table manually. The selected table is a view of the database, not a disconnected table.

## Year Lock Protocol

Before building headers, formulas, or the database schema, define one explicit workbook `Year Set`.

Examples:

- `2024A / 2025E / 2026E`
- `2025A / 2026E / 2027E`
- `CY2026E / CY2027E`

Apply that exact `Year Set` to:

- Database year columns
- Selected comps headers
- Growth and margin calculations
- Trading multiple headers
- Valuation-bridge labels and references

If the user explicitly requests a year or time range, that requested period must remain in the sheet. If the user does not specify a period, default to today's date and build the sheet from the current date context. Do not substitute any other year set unless the user explicitly asks for it.

## Source of Truth

The `DATABASE` block is the source of truth for peer-company fields such as:

- `Ticker`
- `Company Name`
- `Current Price`
- `Share Count`
- `Enterprise Value`
- `Market Cap`
- `Revenue`
- `EBITDA`
- `Net Income`

If the selected comps table exists above the database, those base fields should be populated by one of these methods:

- Direct cell references when the selected names are fixed
- `XLOOKUP` keyed by ticker or company name
- `INDEX/MATCH`
- `VLOOKUP` if the workbook already uses it

Prefer `XLOOKUP` `VLOOKUP` or `INDEX/MATCH` for new builds, but follow the existing workbook convention if one is already in place.

## Cell-Type Conventions


### 1. Hardcodes / Assumptions

Use blue font `rgb(79, 113, 190)` for manually entered values, especially in the implied share price bridge. Typical blue-font inputs include:

- Target `Revenue`
- Target `EBITDA`
- Target `EPS`
- `Cash`
- `Debt`
- `Shares`

These are user inputs or assumption cells. They should not look like formula outputs.

### 2. Formula Outputs

Use black font for calculated cells such as:

- `Revenue Growth`
- `EBITDA Margin`
- `Profit Margin`
- `EV / Revenue`
- `EV / EBITDA`
- `P / E`
- `Mean`
- `Median`
- `Implied Enterprise Value`
- `Implied Equity Value`
- `Implied Share Price`

### 3. Labels / Identifiers

Keep text labels black. Tickers may use blue hyperlink-style text if the workbook convention supports it, but do not confuse ticker styling with input-cell styling.

## Formula Flow

Use this dependency chain:

1. Database stores raw peer values.
2. Selected comps table pulls raw peer values from the database.
3. Growth, margin, and multiple columns calculate from those pulled values.
4. Mean and median rows summarize only the selected comps.
5. The implied share price bridge references those summary multiples and combines them with target inputs.

This means the bridge should not pull directly from the database unless there is a specific reason. It should mostly reference:

- Summary multiple rows from the selected comps table
- Blue-font target inputs
- Formula-based enterprise and equity value calculations

The presentation logic should also follow the same separation:

- Top selected-comps `Mean` and `Median` rows are highlighted because they summarize the comps set.
- Bridge `Minimum`, `Mean`, `Median`, and `Maximum` rows are valuation cases, not comps-summary rows, so they should not inherit the selected-comps green highlight.
- The selected-comps green highlight should span the full table width of the `Mean` and `Median` rows, including blank cells inside that table width.
- Header labels should be centered and merged where appropriate so the model reads like a formatted banking worksheet rather than a plain spreadsheet.
- `Ticker` and `Company Name` remain left-aligned as identifier columns, while the rest of the model content is generally center-aligned.
- Year labels must also stay synchronized across the chain. If the selected comps table shows a given period for a metric, the bridge must reference that same period for both the multiple and the target metric.

## What to Hardcode vs. What to Calculate

Hardcode only items that are assumptions, target inputs, or source values deliberately entered for the target.

Calculate:

- Growth rates
- Margins
- Trading multiples
- Mean and median
- Implied enterprise value
- Implied equity value
- Implied share price

Do not hardcode calculated multiples just to match the format. The format is a layout target, not a reason to break modeling discipline.

## Metric Selection by Use Case

Keep the modeling structure fixed, but do not force one universal metric set across all comps tables.

Choose the analytical columns based on:

- Audience
- Industry
- Task

Examples:

- `Big Tech` comps usually focus on scale, growth, margins, cash generation, and large-cap trading metrics for mature platform businesses.
- `SaaS` comps usually place more weight on recurring-revenue growth, margin progression, and `EV / Revenue`; `P / E` may be secondary or not meaningful.
- The same principle applies across other sectors. Banks, insurers, REITs, energy, semis, industrials, consumer names, and internet platforms can each require different operating and valuation metrics.

When the industry-specific metric set changes, keep the core workbook logic the same:

1. `DATABASE` holds the source data.
2. The top table pulls raw fields from the `DATABASE`.
3. Analytical columns calculate from those raw fields.
4. The valuation bridge references the selected-comps outputs and target inputs.

## Database and Top-Table Relationship

Include a visible `DATABASE` divider bar beneath the implied share price block. Use the same column structure in the database as in the top table whenever practical, so it is obvious that the selected comps are pulled from the same field set.

Keep the top table short and curated. Keep the database broad and comprehensive.

The top table may contain analytical columns that do not exist in the database. That is acceptable as long as:

1. The raw fields in the top table are pulled from the database.
2. The analytical fields in the top table are calculated from those pulled raw fields.
3. The database remains a raw-data block instead of becoming a second presentation table.
4. The database columns and top-table analytical columns are aligned to the same locked `Year Set`.

## Error Handling

Do not leave Excel errors exposed in the presentation area.

Use:

- `NM` when the ratio is not meaningful
- `--` when the item is intentionally not populated

Examples:

- Negative EBITDA should make `EV / EBITDA` display as `NM`
- Negative EPS should make `P / E` display as `NM`
- Unused bridge columns can display `--`

## Validation

Before finishing, check:

1. Every selected comp can be traced to a database row.
2. Top-table raw fields are references or lookups, not silently retyped numbers.
3. Growth, margin, and multiple cells use formulas.
4. Target input cells use blue font `rgb(79, 113, 190)` and are visually distinct from calculated outputs.
5. Mean and median are highlighted with `rgb(228, 238, 220)` across the full selected-comps table width and exclude `NM`, blanks, and companies not in the selected set.
6. Yellow title-box inputs use dashed outer borders and do not include unnecessary fields such as `Basis` unless explicitly requested.
7. Every header year in the selected comps table, bridge, and database matches the locked `Year Set`.
8. No header labeled with one year or period is populated with source data from a different year or period.
