---
name: earnings-review-note
description: "Generate professional sell-side earnings review reports for quarterly or annual results, producing PDF/DOCX/PPTX documents with EPS analysis, guidance review, and variance tables. Triggered when users request an earnings review, need a quarterly wrap, ask for a beat/miss analysis, or mention summarizing an earnings call for any public company."
---

# Equity Earnings Review

## Reference Source

- **Reference type**: Uploaded PDF artifacts
- **Reference artifact type**: PDF
- **Reference File Type**: PDF (professionally typeset institutional equity research reports)
- **Language**: Primarily English (Latin script)

## Supported Outputs

- PDF (default visual fidelity output)
- DOCX (editable document)
- PPTX (presentation format for management summary)

**Default output selection**: PDF when the user does not specify a format. DOCX when editability is requested.

## Typography & Font Strategy

- **Reference fonts**: Inter family (clean geometric sans-serif), UniversLTStd (Light, Bold), RobotoCondensed, ArialMT
- **Visual character**: Clean, modern, condensed sans-serif with a strong weight hierarchy; geometric proportions typical of institutional financial research
- **Substitute font strategy** (when reference fonts unavailable):
  - Use a clean geometric sans-serif with light/regular/medium/bold weights
  - Primary: Inter, Noto Sans, IBM Plex Sans, or similar CJK-compatible sans-serif
  - Condensed headings: Use Inter Condensed, Noto Sans Condensed, or a narrow-width companion
  - Preserve the light-weight body impression and bold-heavy heading hierarchy
  - All document text should use one consistent font family to ensure mixed Latin and CJK content renders correctly

See [references/style_contract.md](references/style_contract.md) for full visual style specification including logo, rating badge, Factor Profile chart, whitespace rules, and page content distribution.

## Document Structure

See [references/structure_contract.md](references/structure_contract.md) for the full section hierarchy, page sequencing rules, exhibit numbering conventions, and financial table patterns.

Key structural sections:
1. Cover / Summary (page 1) -- two-column layout with executive summary, key data, forecast, Factor Profile
2. Financial Snapshot (page 2) -- ratio table, growth/margins, stock performance chart, financial statements
3. Detailed Analysis (pages 3-6) -- bullet-hierarchy commentary, segment review, strategic updates, outlook
4. Estimate & Valuation Changes -- revised estimates, price target, risks
5. Exhibits -- numbered variance summaries, guidance tables, financial models
6. Disclosure Appendix -- back-matter regulatory text

## Workflow

### 1. Gather Inputs

Required inputs before writing:
- Company name, ticker, exchange
- Fiscal period being reviewed (e.g., 4Q25, F4Q26)
- Actual reported figures (revenue, EPS, EBIT/EBITDA, margins by segment)
- Consensus estimates (FactSet / Visible Alpha / StreetAccount)
- House (analyst) estimates (prior/new)
- Company guidance (forward quarter + full-year)
- Key management commentary themes from earnings call or release
- Current stock price, 12-month price target, rating

### 2. Structure the Document

Follow the section ordering from [references/structure_contract.md](references/structure_contract.md).

Key writing rules:
- Open with the headline surprise: lead the first paragraph with whether the company beat/missed on EPS, revenue, or key metrics
- Use bold for key financial figures in the text (e.g., **4Q25 revenue of $24.9 bn**)
- Apply the bullet hierarchy: filled square (primary), hollow square (secondary), filled diamond (tertiary)
- Compare every actual against house estimate, consensus, and guidance (where applicable)
- Include margin commentary with bps/qoq/yoy comparisons
- For estimate changes, show old vs. new with % delta
- End analysis section with valuation method, price target, and key risks (bulleted)

### 3. Build Financial Tables

Tables must be constructed for:
- **Page 2 Financial Snapshot**: Ratios & Valuation (P/E, EV/EBITDA, FCF yield), Growth & Margins (revenue growth, EBITDA growth, EPS growth, gross margin, EBIT margin), compact 3-statement summary
- **Exhibit tables** (each labeled "Exhibit N: [Title]", "$ mn, except per-share data"):
  - Variance Summary: Actual vs. House vs. Street vs. Guidance, with YoY%, column for variance commentary
  - Segment-level variance (where applicable)
  - Guidance Summary: Low-end / High-end vs. Street vs. midpoint delta
  - Estimate Changes Table: Current vs. Prior by fiscal year, showing $ delta and % delta
  - Income Statement Model: Quarterly columns (historical + projected) with YoY growth row
  - Balance Sheet & Cash Flow: Quarterly/projections
- Number formatting: one decimal place for $ mn/bn, two for per-share, one for percentages
- Use parenthetical notation for negatives: `(10.5)` not `-10.5`

### 4. Apply Visual Style

Apply the full style contract from [references/style_contract.md](references/style_contract.md).

Quick reference:
- Page size: US Letter (8.5 x 11 in)
- Margins: ~0.75 in all sides
- Body text: 10-11pt sans-serif regular
- Headings: 12-14pt bold, company name/title larger at 16-20pt
- Table body: 8-9pt, headers in bold with navy background (#003087) and white text
- Color: predominantly black text on white; navy blue for section accents; green for positive variances, red for negative
- Page header: firm name (left) + company ticker (right), separated by horizontal rule
- Page footer: date (left) + page number (right)

### 5. Output Generation

For each output format:
- **PDF**: Preserve page composition, table styling, and typography as closely as the rendering engine permits
- **DOCX**: Reproduce section hierarchy, tables, and formatting natively for editability
- **PPTX**: Convert to executive-summary slides covering key surprises, guidance, and estimate changes only

## Table of Contents for Reference Files

- [references/style_contract.md](references/style_contract.md) -- Visual style specification (colors, typography, layout, spacing, logo, rating badge, Factor Profile chart, whitespace rules, content distribution)
- [references/structure_contract.md](references/structure_contract.md) -- Document structure, section hierarchy, exhibit numbering, content patterns
