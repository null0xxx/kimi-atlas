# Style Contract - Equity Earnings Review

## Reference Source

Extracted from institutional sell-side equity research earnings review PDFs.

## Page Layout

- **Page size**: US Letter (8.5 x 11 in)
- **Margins**: ~0.75 in on all sides
- **Page 1 composition**: Two-column layout
  - Left column (~60%): Executive summary text block
  - Right column (~40%): Key Data sidebar + Forecast table + Analyst contacts + Rating box + Factor Profile chart
  - Horizontal rule separator below the title area
- **Page 2 composition**: Compact multi-section layout across full width
  - Left half: Ratios & Valuation table + Growth & Margins (%) table + Price Performance chart
  - Right half: Income Statement + Balance Sheet + Cash Flow summary tables
  - Rating displayed as a large solid color block at top left
- **Pages 3+ composition**: Single-column text layout (~95% width centered)
- **Exhibit pages**: Full-width tables with titled headers

## Typography System

### Font Families
- **Primary**: Inter (clean geometric sans-serif) -- Regular, Light, Medium, Bold, Condensed, Thin
- **Secondary**: UniversLTStd-Light, UniversLTStd-Bold
- **Chart labels**: ArialMT, RobotoCondensed-Regular
- **Watermarks**: ArialMT
- **Substitute rule**: When Inter is unavailable, use Noto Sans, IBM Plex Sans, or another CJK-capable geometric sans-serif. Preserve light-weight body impression (use Light or Regular weight) and bold for headings.

### Sizing & Weights
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Firm name (header) | 9pt | Regular | Dark gray |
| Company name (page 1 title) | 18-20pt | Bold | Black |
| Ticker in title | 14pt | Bold | Black |
| Subtitle / report title | 14-16pt | Medium | Black |
| Section headings | 12-13pt | Bold | Black |
| Sub-section headings | 11pt | Bold | Black |
| Body text | 10-11pt | Regular | Black |
| Table body | 8-9pt | Regular | Black |
| Table headers | 8-9pt | Bold | White on navy bg |
| Key data labels | 9pt | Medium | Black |
| Key data values | 9pt | Bold | Black |
| Analyst names | 9pt | Bold | Black |
| Analyst contact | 8pt | Regular | Gray |
| Page footer | 8pt | Regular | Gray |
| Source line | 8pt | Regular | Gray |

### Line Spacing
- Body text: 1.3-1.4 line spacing
- Section heading to body: 8-10pt spacing
- Paragraph breaks: 6-8pt
- Table row height: tight, ~14-16pt per row

## Firm Logo / Branding

- **Placement**: Top-left corner of the cover page (page 1) and left side of every page header
- **Form**: Firm logo or distinctive typographic logo mark -- NOT plain text
- **Header pages 2+**: "[Firm Name]" text in dark gray, left-aligned above the horizontal rule
- When generating output, use the firm's brand mark if available; otherwise use a clean typographic rendering of the firm name

## Cover Page Layout (Page 1)

### Top Banner
- Left: Firm logo
- Right: "Equity Research" label + publication date + time (e.g., "29 January 2026 | 1:03AM EST")

### Title Block (full width, below horizontal rule)
- Company Name + (TICKER) in large bold (18-20pt)
- Report subtitle: "[Quarter] review: [key theme]" -- descriptive headline in 14-16pt medium

### Rating + Price Target Summary Bar (left column, below title)
Horizontal bar spanning the full content width containing:
- Ticker symbol (bold)
- 12m Price Target: $XXX.XX (bold, value in color if target changed)
- Price: $XXX.XX (regular)
- Upside/Downside: X.X% (green for positive, red for negative)

### Two-Column Body

**Left column (~60%):**
- Executive summary paragraph(s): 200-400 words total
- Standard disclaimer text block at bottom (~60 words)

**Right column (~40%):**
- **Rating box**: Large solid color block (see Rating Block below)
- **Analyst block**: Name(s), CFA designations, phone, email, firm
- **Key Data** section with horizontal rule: Market cap, Enterprise value, 3m ADTV, Country/sector, M&A Rank
- **Forecast** table with Revenue New/Old, EBITDA, EBIT, EPS New/Old, P/E, Dividend yield, Net debt/EBITDA by fiscal year
- **Quarterly EPS** row: Q1-Q4 of current FY with $ values
- **Factor Profile** chart: Horizontal bar chart (see below)
- Source note

## Rating Block

A **large solid color block** -- approximately matching the width of its column:
- **Buy**: Green solid block with white "Buy" text (large, bold, ~20-24pt), "Rating since [date]" below in smaller white text
- **Neutral**: Dark charcoal / dark blue solid block with white "NEUTRAL" text
- **Sell**: Red solid block with white text
- **Not Rated**: White/light gray block with "NOT RATED" in dark text
- **DO NOT use a small tag/badge** -- the rating must be a prominent solid letterbox-style block
- The rating block appears on the cover page right column and optionally on page 2 top-left with company name and rating date

## Factor Profile Chart

- **Placement**: Bottom of page 1 right column, below the Forecast table
- **Type**: Horizontal bar chart
- **Attributes shown**: Growth, Financial Returns, Multiple, Integrated
- **Percentile scale**: 0th to 100th with tick marks at 20th, 40th, 60th, 80th
- **Two comparison lines** (light/dark shades): (1) Relative to coverage universe, (2) Relative to sector peers
- **X-axis**: Percentile (left to right: 0th, 20th, 40th, 60th, 80th, 100th)
- Source line below: "Source: Company data, [Firm Name] Research estimates."

## Header / Footer Rules

- **Page header** (every page, top ~0.5in): Left = "[Firm Name]" text/logo, Right = "Company Name (TICKER)"
  - Separated by a thin horizontal rule (0.5pt, light gray #CCCCCC) below the header text
  - The header starts approximately 0.3-0.4in from the top of the page
- **Page footer**: Left = publication date (e.g., "29 January 2026"), Right = page number
  - Format: number only (e.g., "2"), no "Page" prefix
  - Small 8pt, dark gray
- **Vertical watermark** (left margin): Textual watermark rotated 90 degrees on left edge of pages (e.g., "For the exclusive use of [client]") -- optional

## Table Styling

### Financial Summary Tables (Page 2)
- Thin borders: 0.5pt hairline rules
- Header row: bold text, no background color (white bg with bold labels)
- Right-aligned numeric columns, left-aligned labels
- Key subtotals in bold (e.g., Total revenue, EBITDA, Net income)
- Units specified in table title (e.g., "($ mn)")
- Fiscal year column headers format: "12/25", "12/26E", "12/27E", "12/28E" (or equivalent FY26A/FY27E if company fiscal year differs from calendar)

### Exhibit Tables (Pages 3+)
- Title format: "**Exhibit N: [Descriptive Title]**"
- Subtitle: "$ mn, except per-share data" (italicized) -- placed directly under title
- Column headers: navy blue background (#003087) with white bold text
- Body rows: alternating white / very light gray for readability
- Bold for subtotal rows
- Thin grid lines between rows (0.25pt)
- Source line below table: "Source: Company data, [Firm Name] Research estimates."

### Estimate Changes Table (key exhibit)
- Compact multi-column layout with FY groupings (Current FY, Next FY, +2 FY)
- Within each FY block: Current | Prior | Delta ($) | Delta (%)
- Color coding for deltas: positive changes in dark blue/gray, negative in parentheses

### Variance Table Columns
Standard column groups:
- Actual ($) | YoY (%) -- then repeated for house estimate, Street (FactSet), Guidance
- Actual vs. Estimates columns: delta vs. house, delta vs. Street, delta vs. Guidance
- Include YoY growth rates for each metric

## Bullet Hierarchy

Three-level bullet system used throughout analysis text:
1. **Level 1** (primary point): Filled square bullet (\u25A0) -- e.g., segment headline
2. **Level 2** (sub-point): Hollow square bullet (\u25A1) -- e.g., within-segment detail
3. **Level 3** (tertiary): Filled diamond (\u25C6) or dash (-- ) -- e.g., product-level detail

Apply bold to the key metric being introduced at each bullet (e.g., "**Revenue of $33.4 bn** beat HouseE...")

## Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Primary text | Black | #000000 |
| Secondary text (headers, source) | Dark gray | #666666 |
| Navy blue (accent, table headers) | Institutional navy | #003087 |
| Positive variance / buy rating bg | Green | #008000 |
| Negative variance / sell rating bg | Red | #CC0000 |
| Table header background | Navy blue | #003087 |
| Table header text | White | #FFFFFF |
| Table alternate rows | Light gray | #F5F5F5 |
| Page header rule | Light gray | #CCCCCC |
| Rating box background (Neutral) | Dark charcoal | #37474F |
| Rating box background (Not Rated) | Light gray | #ECEFF1 |

## Price Performance Chart (Page 2)

- **Required element** on the Financial Snapshot page (page 2, bottom left)
- **Type**: Line graph showing two lines: stock price (left Y-axis) vs. S&P 500 (right Y-axis)
- **Timeframe**: 12-month trailing performance
- **X-axis**: Month labels (e.g., "Apr-25", "Jul-25", "Oct-25", "Jan-26")
- **Left Y-axis**: Stock price in $
- **Right Y-axis**: S&P 500 index level
- **Stats below chart**: 3m / 6m / 12m Absolute and Relative to S&P 500 performance percentages
- **Source**: FactSet

## Spacing & Whitespace Rules (CRITICAL)

These rules must be followed to avoid the whitespace issues observed in prior outputs:

### Page Content Density
- **No premature page breaks**: Content must flow continuously. Tables that are split should not leave massive empty space on the continuation page
- **Page 2 density**: Must contain 6 financial tables + a price chart -- extremely compact layout with 8-9pt font, minimal padding
- **Analysis pages**: Should be 60-70% filled with text (not 30% content + 70% whitespace)
- **Exhibit pages**: Full-width tables should start near the top of the page and continue to near the bottom

### Table Continuation Rules
- When a table runs across page boundaries, the continuation page should show the table header row repeated and continue with the same number of columns filling the width
- Tables that continue on a new page MUST NOT leave massive empty space (this indicates a layout bug)
- When a table naturally ends partway down a page (e.g., a short exhibit), the next section heading should start immediately after with minimal whitespace

### Section Transitions
- Section headings should follow their preceding content with 6-10pt spacing, not large page gaps
- Horizontal rules (0.5pt) between sections where appropriate -- keep to ~1-2px width
- Major section breaks should occur naturally at the end of a page filled with content, not in the middle of a page with 60%+ whitespace below

### Page Fill Check
Before considering a page complete, verify:
- Financial snapshot page (page 2): Tables fill the full width, from top header to near the footer (within 0.5in of footer)
- Analysis pages: Text fills at least the top two-thirds of the page
- Exhibit pages: Table occupies at least 40% of the page height
- Pages with predominantly empty space (>40% blank) indicate a layout error that must be fixed

## Spacing & Whitespace (General)

- Professional, dense-but-readable layout
- Tight packing on page 2 financial snapshot (6-8 data tables on one page)
- Generous but controlled white space on analysis pages (not excessive)
- Section breaks: horizontal rule (0.5pt) between major sections where appropriate
- Page breaks before new major sections (e.g., before Disclosure Appendix) -- but ONLY when the preceding section is complete
