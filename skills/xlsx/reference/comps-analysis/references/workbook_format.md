# Workbook Format

Use this format when building a comps analysis worksheet intended to follow a banking-style comps template. The visual goal is not generic spreadsheet cleanliness. The goal is a dense, banker-style worksheet with explicit section hierarchy, visible source/input distinctions, and analytical heatmaps only where they add signal.

## Sheet Layout

Arrange the worksheet in this order from top to bottom:

1. Title block
2. Selected comps table
3. Summary valuation bridge
4. Database section

Leave enough whitespace between blocks to keep the page readable, but do not create a sparse or presentation-only layout that hides the math. Use a compact layout with only modest vertical spacing between blocks.

## Typography

Default to `Arial` for this style of sheet.

- Use `Arial` 14 to 16 bold for the main title.
- Use `Arial` 8 to 10 for body cells.
- Use bold text for row labels such as `Mean`, `Median`, `Minimum`, `Maximum`, and section labels such as `Calculating Implied Share Price` and `DATABASE`.
- Use black font for normal labels and formula outputs.
- Use blue font `rgb(79, 113, 190)` for hardcoded inputs or assumptions in the valuation bridge.

If working inside an existing workbook that already uses another font consistently, preserve that workbook's font. Otherwise, default to `Arial`.

## Color System

Use a small, repeated palette rather than many unrelated colors.

- Header fill: muted light blue-gray, close to `#D9E2F3`
- Input box fill for `Date` and `Currency`: pale yellow, close to `#FFF2CC`
- Summary-row fill for `Mean` and `Median`: use exactly `rgb(228, 238, 220)`
- Section-divider fill for `DATABASE`: deep navy blue, close to `#0F243E`, with white text
- Blue font for hardcodes: use exactly `rgb(79, 113, 190)`

Keep the palette restrained. Do not introduce extra accent colors unless the workbook already has a house style.

## Title Block

Place the title on the upper left, for example `Target Name - Comps Table` or `Industry Name - Comps Table`.

Show at least:

- `Date`
- `Currency`
 
Do not add `Basis` to the small title box unless the user explicitly asks for it. Keep the title box limited to the essential yellow-highlight inputs by default.
Format the `Date` value in slash style `yyyy/m/d`, for example `2022/7/23`.
If the user specifies a year or time range, make sure the visible headers throughout the sheet clearly reflect that locked period. If the user does not specify one, default to today's date and the current date context.

Put these labels in a small box near the title so the valuation context is obvious at a glance.

Formatting details:

- Label cells should be bold and left-aligned.
- Value cells should use the pale yellow input fill.
- Each yellow input cell should have its own dashed or dotted outer border.

## Selected Comps Table

This is the primary table. Use a compact, left-to-right flow:

1. Identification
2. Market data and capitalization
3. Operating metrics
4. Growth and margins
5. Trading multiples

Recommended column order:

| Section | Columns |
| --- | --- |
| Identification | `Ticker`, `Company Name` |
| Market data | `Current Price`, `Share Count`, `Enterprise Value`, `Market Cap` |
| Revenue block | `Revenue` for three periods when available |
| EBITDA block | `EBITDA` for the periods used in margin and multiple calculations |
| Net income block | `Net Income` for the periods used in margin and `P / E` calculations |
| Growth block | `Revenue Growth` for consecutive periods |
| Margin block | `EBITDA Margin`, `Profit Margin` |
| Multiples block | `EV / Revenue`, `EV / EBITDA`, `P / E` |

Header structure:

- Use a three-layer header when the trading-multiples block is present.
- Top header layer: umbrella labels such as `Trading Multiples` when a wider block needs one.
- Middle header layer: group labels such as `Revenue`, `EBITDA`, `Net Income`, `Revenue Growth`, `EBITDA Margin`, `Profit Margin`, `EV / Revenue`, `EV / EBITDA`, and `P / E`.
- Bottom header layer: field labels or year labels such as `Ticker`, `Company Name`, `Current Price`, `'23`, `'24`, or `'23-'24`. These are examples only, not fixed required years.
- If the task is anchored to a specific year or time range, the bottom header layer should visibly use that requested period set. If the task is not anchored by the user, derive the displayed years from today's date and the ticker context.
- Standalone fields such as `Ticker`, `Company Name`, `Current Price`, `Share Count`, `Enterprise Value`, and `Market Cap` should visually span the full header depth rather than looking like they only belong to one row.
- When a metric has multiple year columns, merge the metric label cell across those year columns and center it.
- When an umbrella category has multiple sub-metrics, merge the umbrella label across all of those sub-metrics and center it. `Trading Multiples` should visibly span `EV / Revenue`, `EV / EBITDA`, and `P / E`.

Formatting rules:

- Use one header color across the table, preferably the muted light blue-gray header fill.
- Group column blocks with a top-line label such as `Revenue`, `EBITDA`, `Net Income`, `Revenue Growth`, `EBITDA Margin`, `Profit Margin`, and `Trading Multiples`.
- Center all header text horizontally and vertically.
- Merge header cells when a label logically spans multiple columns or multiple header rows.
- Under each middle-layer group label, use a thin black bottom border to create a clear bracket effect for the grouped columns.
- Apply the bracket consistently across the full group width. If `Net Income` covers two year columns, both year columns must sit under the same grouped top border.
- Apply the bracket across all columns within the metric group, not just the first year column.
- Leave a small visual gap between adjacent group brackets so separate metrics do not read like one continuous line.
- Do not use white left or right borders to create that gap. The side edges of the grouped header should stay in the same fill color as the header cell itself unless an actual border is needed.
- Keep `Ticker` and `Company Name` left-aligned.
- Center-align the remaining table data and headers unless a specific workbook convention requires otherwise.
- Keep tickers visually distinct, often blue if hyperlink-style formatting is used.
- Show `Mean` and `Median` rows immediately below the selected peers, highlighted across the full selected-comps table width with `rgb(228, 238, 220)`.
- Do not over-grid the table. Use borders mainly for section logic, group headers, and summary separation rather than drawing full borders around every cell.
- Label the trading-multiples columns explicitly. Do not leave a year-only subheader without making clear whether it belongs to `EV / Revenue`, `EV / EBITDA`, or `P / E`.
- Do not show a header for one year or period unless the data and formulas beneath it also point to that same year or period. Header-period accuracy matters as much as visual format.
- Keep trading-multiple cells numeric and apply an explicit Excel custom number format such as `0.0\"x\"` so values display like `6.2x` without converting the cell to text.

## Conditional Formatting

Apply color scales only to analytical sections, not to all numeric data.

- `Revenue Growth`: three-color scale where higher growth is greener and lower growth is redder.
- `EBITDA Margin` and `Profit Margin`: three-color scale where higher margin is greener and lower or negative margin is redder.
- `Trading Multiples`: inverse scale where lower multiples are greener and higher multiples are redder.

Use a soft red-yellow-green style. Keep the fill fairly muted so the numbers remain readable and the heatmap does not overpower the table.

## Summary Valuation Bridge

Place this directly under the selected comps table. The structure should read left to right:

1. Selected-peer trading multiples
2. Target financial metrics
3. Implied enterprise value
4. Balance-sheet bridge or direct equity value
5. Implied share price

Recommended rows:

- `Minimum`
- `Mean`
- `Median`
- `Maximum`

Recommended columns:

| Section | Columns |
| --- | --- |
| Trading multiple | `Revenue`, `EBITDA`, `P / E` |
| Target metric | `Revenue`, `EBITDA`, `EPS` |
| Enterprise value | `Revenue`, `EBITDA`, `Net Income` only when relevant |
| Balance sheet bridge | `Cash`, `Debt`, `Shares` |
| Equity value | `Revenue`, `EBITDA`, `Net Income` |
| Implied share price | `Revenue`, `EBITDA`, `Net Income` |

If the table uses `P / E`, the implied share price can be computed directly from the selected multiple times target EPS. If you still show equity value, make sure the logic is transparent.

Header structure:

- Use a two-layer header in the bridge.
- Left title cell: `Calculating Implied Share Price`. Keep it inside the highlighted bridge header area and place it on the same row as the metric labels such as `Revenue`, `EBITDA`, `EPS`, `Cash`, `Debt`, and `Shares`, not on the upper grouped-header row.
- Top group row: labels such as `2024 Trading Multiple`, `2024 Financial Metric`, `Enterprise Value`, `Equity Value`, and `Implied Share Price`.
- When the workbook is anchored to a specific year set, the bridge group labels should use that same year anchor.
- Bottom header row: metric labels such as `Revenue`, `EBITDA`, `P / E`, `EPS`, `Cash`, `Debt`, and `Shares`.
- Merge bridge section labels across the full width of their sub-metrics and center them.

Formatting rules:

- Use the same blue-gray header fill for bridge section headers.
- Highlight both bridge header rows so the title row and the metric-label row read as one header block.
- Center all bridge headers. Merge cells when a bridge section label spans multiple metric columns.
- Keep target inputs such as `Revenue`, `EBITDA`, `EPS`, `Cash`, `Debt`, and `Shares` in blue font `rgb(79, 113, 190)` to signal hardcodes.
- Keep calculated outputs such as `Implied Enterprise Value`, `Equity Value`, and `Implied Share Price` in black font.
- Use `--` rather than blank-looking formula errors in bridge cells that are not used.
- Do not highlight the bridge `Mean` and `Median` rows in green. The green highlight is for the selected-comps summary rows, not for the implied share price bridge.

## Database Section

Start the section with a clear divider, using a deep navy-blue bar labeled `DATABASE` with white text.

This section should hold the broader peer universe, including companies not ultimately selected into the top table. Use the same column order as the selected comps table when possible so the top table can be traced back to the database without remapping columns.

Keep the database factual and denser than the top table. Do not apply heatmaps to the full database. The database is primarily a source block, not the presentation block.

Header structure:

- Use the deep navy-blue `DATABASE` divider bar first.
- Under the divider, use grouped headers only for the raw financial blocks that actually appear in the database, typically `Revenue`, `EBITDA`, and `Net Income`.
- Merge those raw financial block headers across their year columns and center them.
- Do not force analytical headers such as `Revenue Growth`, `Margins`, or `Trading Multiples` into the database if the database is intended to remain a raw-data source block.

## Border Rules

Use borders sparingly and intentionally.

- Add a strong bottom border under grouped section headers.
- Use header-row borders to separate labels from data.
- Use a stronger separator before the `DATABASE` section.
- Avoid boxing every cell. This format should rely more on section bars and group underlines than on full cell grids.
- Summary rows can use fill plus a top or bottom border if needed, but do not make them visually heavier than the section headers.
- When a group spans two year columns, both year columns must sit under the same top border. Do not leave one year visually ungrouped.
- Default to thin black borders for these layout rules. Do not promote them to heavy or thick borders unless the user explicitly asks for it.

## Presentation Standards

- Keep units consistent across the full sheet.
- Use clear year labels such as `2024`, `2025`, `2026` or abbreviated `'25`, `'26`; do not mix styles inside one block.
- Keep the chosen year labels tied to the user request. If the user did not specify a period, use today's date and the current ticker/date context to determine them.
- Use stronger borders for section separation and minimal internal borders elsewhere.
- Avoid unnecessary decimals for large financial values.
- Preserve formula transparency. A professional sheet should still be auditable by someone reviewing the workbook line by line.
- Always preserve the logical relationship between the top table and the database below it. The format is only correct when the modeling flow is also correct.
- Turn off Excel gridlines on deliverable sheets so only intentional formatting remains visible.
