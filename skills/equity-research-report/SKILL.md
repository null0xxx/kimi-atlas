---
name: equity-research-report
description: Create institutional-grade investment research reports with sell-side styling, dense information layout, and comprehensive section structure. Use for equity, fixed-income, strategy, sector, derivatives, ETF, or quantitative research. Mimics Goldman Sachs, Morgan Stanley, or JPMorgan style with cover pages, exhibit-numbered charts, glossary, and disclosures. Supports PDF, DOCX, and PPTX output.
---

# Institutional Research Report

Create polished investment research reports styled after top-tier sell-side research with dense content-rich pages and comprehensive section structure.

## Reference Source

- **Source type**: Uploaded artifact (PDF)
- **Reference artifact type**: PDF
- **Reference File Type**: PDF
- **Original reference**: Goldman Sachs Global Investment Research report on VIX ETPs (35 pages)

## Supported Outputs

| Format | Support |
|--------|---------|
| PDF    | Primary output - best fidelity for the reference style |
| DOCX   | Supported - editable document with full styling |
| PPTX   | Supported - for slide-deck adaptation of research content |

**Default output**: DOCX (when user does not specify a format)

## Font Strategy

The reference uses **Univers LT Std** (regular, light, bold) as the primary font family with **Roboto Condensed** for labels and **Arial** for chart elements.

- For Latin-only content, use a clean neo-grotesque sans-serif as the primary font (Univers, Helvetica Neue, or Arial)
- For mixed CJK/Latin content, use a single CJK-capable font family consistently across the entire document:
  - **English + CJK**: Noto Sans CJK, Source Han Sans, or PingFang SC for all text
  - Preserve the reference's visual character: clean, modern, institutional sans-serif
- Never leave any component (headings, body, tables, captions, headers, footers, cover text) on a default Latin-only font while patching CJK support elsewhere
- Table cells with CJK text must wrap and grow vertically; do not clip or allow overflow

## Workflow

1. **Read the style contract** at `references/style_contract.md` for complete visual specifications
2. **Read the structure contract** at `references/structure_contract.md` for document organization rules
3. Gather content from the user (topic, data, charts, analysis)
4. Build the document section by section following the structure contract
5. Apply the style contract consistently across all elements

## Style Quick Reference

### Color Palette
- Primary: `#003B5C` (deep navy blue) - cover bar only
- Table header: `#D6DCE4` (light blue-gray) with dark text
- Text: `#333333` (dark charcoal) - body text; `#000000` - headings
- Secondary: `#4472C4` (medium blue) - links, sidebar headings, emphasis
- Chart colors: `#4472C4`, `#5B9BD5`, `#A5A5A5`, `#264478`, `#636363`
- Background: `#FFFFFF` (white); light gray `#F2F2F2` for alternating table rows, sidebar

### Cover Page (DENSE CONTENT-RICH)
- Top navy blue (`#003B5C`) banner spanning full width, white title text ~32pt
- Date left, firm name right on banner
- Subtitle below banner in dark charcoal ~18pt
- **Two-column layout**: left ~60% has summary sections with blue headings; right ~40% has light gray sidebar with analyst info and "N Things to Know" numbered list
- Bottom disclaimer in 8pt small text
- Cover must be dense with information, NOT minimalist

### Page Layout
- US Letter (8.5 x 11 in) or A4
- Margins: top ~1in, bottom ~0.8in, left ~1in, right ~1in
- Single-column for body; two-column for cover page only

### Typography Scale
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Cover title | 30-32pt | Bold | White on navy |
| Cover subtitle | 18pt | Regular | Dark charcoal |
| H1 (section) | 16-18pt | Bold | Dark charcoal, underline |
| H2 (subsection) | 12-13pt | Bold | Dark charcoal |
| H3 (sub-sub) | 11pt | Bold | Dark charcoal |
| Body text | 10pt | Regular | Dark charcoal |
| Caption/source | 8pt | Italic | Gray |
| Header (date/sector) | 8pt | Regular | Gray |
| Footer (firm) | 8pt | Regular | Gray |
| Page number | 8pt | Regular | Gray |
| Disclosure text | 9pt | Regular | Dark charcoal |
| Glossary term | 10pt | Bold | Dark charcoal |

### Tables
- Header row: **light blue-gray (`#D6DCE4`) background with dark bold text** (NOT dark navy with white text)
- Alternating white / light gray (`#F2F2F2`) data rows
- Thin gray borders
- "Exhibit N:" prefix for numbered tables
- Source line in italic below table

### Charts
- Gray border and light gray (`#D9D9D9`) title bar background
- "Exhibit N:" prefix for numbered charts
- Bar charts: navy/blue palette; Line charts: navy + gray
- Source line in italic below
- Axis labels: 8-9pt sans-serif

### Headers/Footers (on all body pages)
- Header: date (left), region/sector tag (right), 8pt gray, separated by thin rule
- Footer: firm name + division (left), page number (right), 8pt gray, separated by thin rule

## Section Structure

A complete report must include ALL of these sections:

1. **Cover Page** - Dense layout with banner, title, two-column summary, sidebar, disclaimer
2. **Table of Contents** - With right-aligned page numbers
3. **Executive Summary** - With FULLY BOLD opening thesis paragraph
4. **Body Sections** (multiple) - Analytical content with exhibits
5. **Appendix: Where to find stuff** - Data sources and methodology links
6. **Glossary of Terms** - Defined key terminology
7. **Disclosure Appendix** - Legal disclaimers and regulatory disclosures

## Key Rules

- All exhibits (charts, tables) use sequential "Exhibit N:" numbering (NOT "Figure N:")
- Source citations must appear below every exhibit in italic
- Cover page must have navy blue banner with white title text; dense with content
- Table of Contents has right-aligned page numbers
- Executive Summary opening paragraph must be **fully bold** (core thesis)
- Document ends with Glossary of Terms then Disclosure Appendix
- Bullet points use filled circles with bold lead-in text
- Hyperlinks in medium blue (`#4472C4`), underlined
- **High information density** - 35+ pages typical; pack content tightly
- **NO colored callout boxes** (no "Key Finding", "Warning", or similar bordered boxes)
- **NO minimalist cover** - cover must be content-rich with sidebar and summaries
- Include mathematical formulas with labels on left, equations on right

## Output Notes

- **DOCX**: Apply styles via native style system; use theme colors for navy/medium-blue; table headers use light blue-gray
- **PDF**: Maintain exact color values and spacing; embed fonts; high density layout
- **PPTX**: Adapt cover as title slide; each major section becomes a slide; exhibits on separate slides
