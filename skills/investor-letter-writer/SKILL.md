---
name: investor-letter-writer
description: "Draft classic investment memos as DOCX or PDF files, in the style of top VC deal memos or investor letters. Triggered when users ask to write an investment memo, deal memo, or IC memo, or to analyze a company, startup, or theme and document the thesis."
---

# Investment Memo Skill

## Reference Source

- **Type**: Uploaded artifact (two reference PDFs)
- **Reference artifact type**: PDF
- **Reference File Type**: PDF
- **Primary language**: English (Latin script)
- **Reference fonts**: Times New Roman (narrative memo), Helvetica (deal memo)

## Supported Outputs

| Format | Support |
|--------|---------|
| DOCX   | Primary (default) |
| PDF    | Supported |
| PPTX   | Supported (summary/deck format only) |

**Default output**: DOCX unless user explicitly requests another format.

## Output Philosophy

Investment memos from both references are **plain, text-first documents** — black text on white paper, no cover page, no colored backgrounds, no styled boxes, no decorative elements. The formatting should be invisible; the analysis should carry all the weight.

## Workflow Overview

1. **Determine memo type** — thematic memo (default) vs. venture deal memo vs. public equity memo
2. **Gather inputs** — company name, ticker, sector, data the user provides
3. **Conduct analysis** using `references/analysis_framework.md`
4. **Draft content** following `references/structure_contract.md`
5. **Apply formatting** per `references/style_contract.md`
6. **Produce artifact** in requested format (DOCX default)

### Memo Type Selection

| Trigger phrase / context | Memo type | Primary reference | Heading style |
|--------------------------|-----------|-------------------|---------------|
| "investment thesis on AI", "write about sector/theme", "market outlook", "bubble?" | Thematic memo | Narrative style | Underlined |
| "invest in [company]", "deal memo", "VC memo", "seed/Series A" | Venture deal memo | Deal style | Bold |
| "stock analysis", "equity research", "public company" | Public equity memo | Hybrid | Underlined or Bold |
| "due diligence", "DD memo", "investment committee" | IC memo | Deal style | Bold |

## Critical Style Rules

Read `references/style_contract.md` for the full specification. These rules are non-negotiable:

- **NO COVER PAGE** — document starts immediately with the memo header block
- **NO COLOR** — strictly black text on white background throughout
- **Times New Roman** (or equivalent serif) for ALL text — body, headings, quotes, footer, captions
- **NO running headers** — blank page headers
- **NO styled boxes, borders, or background fills** — no gray backgrounds, no colored accent bars
- **NO decorative elements** — no geometric shapes, no badges, no styled quote blocks with left borders
- **Quote blocks**: simple indented italic text, no border or background
- **NO formal tables** — present data as inline text or bullet lists; tables only when absolutely necessary with minimal formatting
- **Footer**: copyright notice left, page number centered, "All Rights Reserved" right

### Section Heading Style

For **narrative/thematic memos** (default):
- Use **underlined text** on its own line: `Understanding AI`, `Can AI Think?`
- NOT numbered, NOT bold, NOT large font — same size as body text with underline

For **structured deal memos**:
- Use **bold text** on its own line: `Introduction`, `Competition`, `Deal Terms`
- NOT numbered, NOT displayed in large font

## Structure Contract

Read `references/structure_contract.md` for the full document structure including section hierarchy, header/footer rules, page break behavior, and the three memo type templates.

Key structural rules:
- **No table of contents**
- **No executive summary** for thematic memos (opening paragraph serves this purpose)
- **Continuous text flow** between sections — no forced page breaks
- **Legal disclaimers** at the end, separated by a horizontal rule, in italic
- Exhibits numbered sequentially: **Exhibit 1**, **Exhibit 2**, etc.

## Voice & Tone Guidelines

### Narrative/Thematic Memos
Write like a top value/credit investor writing to LPs: first-person, conversational, intellectually honest. Use "I believe", "I've been thinking", "I recently learned". Ask provocative questions. Draw historical parallels. Acknowledge uncertainty.

### Deal Memos
Write like a top-tier VC analyst: direct, concise, bullet-oriented. State facts quickly. Lead with recommendation. Every sentence advances the investment case or flags a risk.

## Exhibit Guidance

Include exhibits when quantitative analysis strengthens the case:
- Market size/growth as inline text or simple line charts
- Competitive landscape as bullet lists, not matrices
- Financial metrics as bolded inline figures or bullet points

Reference exhibits in text: "(see Exhibit 3)". Keep exhibits simple — plain line charts preferred.

## Data Sourcing Strategy

When data is needed:
1. Use available financial data sources for public companies (stock prices, financials, ratios)
2. Search the web for company-specific information and market data
3. Cite sources inline — external data strengthens credibility
4. Flag missing data explicitly rather than fabricating numbers

## Confidentiality Marking

Add a confidentiality footer only when the memo contains non-public information:
- **"Confidential — For Internal Use Only"** for IC memos
- **"Highly Confidential"** for live deal materials
- Omit for public thematic memos intended for broad distribution

## Output-Specific Notes

### DOCX (Default)

Produce a native Word document with:
- Times New Roman applied consistently to all text elements
- Underlined section headings (narrative) or bold headings (structured)
- Memo header with horizontal rule separator
- Page numbers centered in footer
- Copyright and rights notice in footer
- Left-aligned body text
- Proper bullet list formatting
- Italic indented blocks for quotes
- Horizontal rule before legal disclaimers section

### PDF

Render the DOCX to PDF preserving all formatting. The result should match the plain, text-first appearance of both reference memos.

### PPTX (Summary Deck)

When the user requests a slide deck instead of a memo document:
- Condense each major section to 1-2 slides
- Lead with the investment thesis on the title slide
- Use bullet points, not paragraphs
- Include 1-2 key exhibits per slide
- End with recommendation/next steps slide
- Use Times New Roman throughout, black text on white background, plain formatting
