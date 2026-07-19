# Calculation Guide

Use this reference when computing comps metrics, deciding whether a value is meaningful, or validating the final output.

## Core Inputs

Collect or derive these fields for each peer when available:

- Current share price
- Diluted shares outstanding
- Market capitalization
- Cash and cash equivalents
- Total debt
- Revenue
- EBITDA
- Net income
- EPS for any `P / E` output

Use one reporting basis across the peer set:

- Historical full year
- Calendarized year
- LTM
- Forward year

Do not mix these unless the user explicitly requests it.

If the user specifies a year or year window, lock that period before calculating anything. If the user does not specify one, default to today's date and derive the period set from the current date context. Do not silently switch to any other year or time range.

## Core Formulas

Use these default formulas:

- `Market Cap = Current Share Price x Diluted Shares`
- `Enterprise Value = Market Cap + Debt + Preferred Equity + Minority Interest - Cash`
- `Revenue Growth = Current Period Revenue / Prior Period Revenue - 1`
- `EBITDA Margin = EBITDA / Revenue`
- `Profit Margin = Net Income / Revenue`
- `EV / Revenue = Enterprise Value / Revenue`
- `EV / EBITDA = Enterprise Value / EBITDA`
- `P / E = Current Share Price / EPS`

For selected-comps summary rows:

- `Minimum = MIN(selected meaningful values)`
- `Mean = AVERAGE(selected meaningful values)`
- `Median = MEDIAN(selected meaningful values)`
- `Maximum = MAX(selected meaningful values)`

For the target valuation bridge:

- `Implied Enterprise Value = Selected Multiple x Target Metric`
- `Implied Equity Value = Implied Enterprise Value - Debt - Preferred Equity - Minority Interest + Cash`
- `Implied Share Price = Implied Equity Value / Diluted Shares`

For `P / E`-based valuation:

- `Implied Share Price = Selected P / E x Target EPS`
- `Implied Equity Value = Implied Share Price x Diluted Shares` when needed

## Meaningful vs. Not Meaningful

Mark a metric as `NM` rather than forcing a number when:

- EBITDA is zero or negative for `EV / EBITDA`
- EPS is zero or negative for `P / E`
- Revenue is zero for margin or `EV / Revenue`
- Capital-structure adjustments are incomplete and make enterprise value unreliable

Do not include `NM` or blanks in `Mean` and `Median`.

Use `--` when the bridge structure includes a column that is intentionally unused for a given metric.

## Peer-Selection Heuristics

Prioritize:

1. Business model similarity
2. Customer and end-market overlap
3. Margin structure
4. Growth profile
5. Geography and regulatory exposure
6. Scale and liquidity

Document the reason when excluding an otherwise obvious name from the selected set.

## Quality Checks

Before delivering the table, verify:

1. `Enterprise Value` is not lower than `Market Cap` without a clear net-cash explanation.
2. Multiples implied by the raw numbers reconcile to the displayed multiples.
3. `Mean` and `Median` use only the selected peers, not the full database.
4. Year labels are consistent across metrics and valuation outputs.
5. Header years actually match the source periods used in formulas; a labeled period must reconcile to inputs from that same period.
6. `P / E` is not shown for peers with negative earnings unless the user explicitly wants it shown as `NM`.
7. The implied valuation range is directionally plausible relative to current trading levels.
8. The selected comps table traces back to the database rather than relying on manually retyped values.
9. Blue-font hardcodes and black-font formulas are used consistently in the valuation bridge.

## Default Modeling Choices

If the user does not specify otherwise:

- Use diluted shares.
- Use cash and total debt in the equity bridge.
- Prefer median as the anchor valuation output and mean as a secondary check.
- Keep extreme outliers in the database, but consider excluding them from the selected set if they distort the comp story.
