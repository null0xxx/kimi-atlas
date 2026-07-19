---
name: market-research-brief
description: "Generate professional consulting-style market insight reports with data-driven analysis, executive summaries, and strategic recommendations. Triggers when users request market or industry analysis, competitive landscape reports, consumer behavior studies, or strategic documents in a top-tier consulting firm visual style."
---

# Market Insight Report Skill

Generate professional consulting-style market insight reports modeled after top-tier consulting firm standards.

## Reference Source
- **Type**: Uploaded PDF artifact
- **Artifact type**: PDF
- **Reference file type**: PDF
- **Based on**: Top-tier consulting firm + market research partner joint report (32 pages)
- **Primary language**: Chinese (Simplified) with English mixed

## Supported Outputs
- **PDF** (primary, matches reference artifact)
- **DOCX** (editable version)
- **PPTX** (presentation version)

## Default Output Selection
- If user explicitly requests a format, use that format
- Otherwise, default to **PDF** for print-ready reports, **DOCX** for editable drafts

## Reference Files

Read these when generating the report:
- `references/analysis_framework.md` -- **Analysis methodology**: market sizing, category analysis, channel analysis, consumer behavior, competitive analysis, data-to-insight methodology
- `references/chart_creation_guide.md` -- **Chart rendering specifications**: exhibit-to-chart mapping, color palette, 9 chart type specs, technical output requirements. **Charts must be rendered as embedded images, not text placeholders or tables.**
- `references/style_contract.md` -- Visual style: typography, colors, layout, chart treatment
- `references/structure_contract.md` -- Document structure: section hierarchy, content flow, chart numbering
- `references/sota_analysis.md` -- How contracts were derived from the reference

## Report Generation Workflow

### Step 1: Understand Requirements
Identify from user query:
- **Topic/domain**: Which market or industry?
- **Time scope**: Historical review period + current analysis period
- **Data sources**: What data should the analysis be based on?
- **Target audience**: Executives, marketers, investors?
- **Key questions**: What insights must the report answer?
- **Output format**: PDF, DOCX, or PPTX?

### Step 2: Conduct Analysis
Read `references/analysis_framework.md` and apply the relevant analytical methods:
- **Market sizing**: Use top-down + bottom-up cross-validation (Module 1)
- **Category analysis**: Decompose growth into penetration × frequency × spend; perform volume/price split (Module 2)
- **Channel analysis**: Track channel share evolution, build migration matrix, compare channel efficiency (Module 3)
- **Consumer behavior**: Map the purchase journey, segment users, analyze need-states (Module 4)
- **Competition**: Attribute share shifts, calculate concentration metrics, build competitive radar (Module 5)
- **Insight synthesis**: Follow the 5-step discovery process; apply "So what?" test to every data point (Module 6)

Every analytical claim in the report must trace back to one of these frameworks.

### Step 3: Plan Report Structure
Follow the standard consulting report architecture (see `references/structure_contract.md`):

```
1. Cover Page (hero shopping photograph + red title + partner branding)
2. Author Profiles & Acknowledgments (simple text layout, no decorative borders)
3. Table of Contents
4. Executive Summary (1-3 dense pages, key findings only, no charts)
5. "Full Report" photo divider page (large photo + title overlay + intro paragraph)
6. Full Report Body (chapters flow directly without numbered divider pages)
   - Chapter heading in red bold, followed by intro paragraph + analysis with charts
   - Each subsection heading in black bold
7. Strategic Recommendations / Future Outlook
8. Back Cover (minimal with logo + office list + contact info)
```

**Key rules from reference**:
- NO numbered section divider pages (like 01, 02, 03)
- NO extra pages (no methodology description page, no appendix)
- Content should be dense -- avoid nearly-empty pages
- NO breadcrumb numbering system (like 1.1, 1.2)

Refer to `references/structure_contract.md` for full details.

### Step 4: Apply Visual Style

Read `references/style_contract.md` for full details. Key rules:

- **Color palette**: Deep red (#CC0000) for accents, black for body text, grays for chart secondary data
- **Typography**: Alibaba PuHuiTi (Chinese), Graphik (English headings), TiemposText (English body)
- **Header on every content page**: "Partner1 | Partner2" in red + horizontal rule + subtitle centered below
- **Footer**: Page number centered at bottom
- **Charts**: Numbered "图X:" with red label, source attribution below each

### Step 5: Content Development Rules

#### Data Presentation
- Always lead with the insight, then support with data
- Include specific percentages, growth rates, and absolute numbers
- State comparison periods explicitly (e.g., "2023 Q1 vs 2022 Q1")
- Reference charts in text using "（见图X）" format

#### Chart Guidelines
- **Charts must be rendered as actual embedded images** (PNG, 150+ DPI), NOT text placeholders or table-only substitutes. This is the #1 quality requirement. See `references/chart_creation_guide.md` for full specs.
- Use red accent (`#CC0000`) for primary data series, gray for secondary
- Include data labels directly on bars/columns
- Add source citation below every chart: "资料来源：..."
- Place charts near first text reference
- Use sequential numbering: 图1, 图2, 图3...
- Chart titles should be **assertions** ("短视频占据用户时长38.4%"), not descriptions ("用户时长分布")
- **Minimum 1 chart per 2 content pages**; ideal is 1-2 charts per page
- 9 supported chart types: bar+growth line (dual-axis), pie/donut, stacked 100% bar with CAGR table, waterfall/bridge, 2×2 mini-chart grid, annotated line chart, horizontal bar (ranking), radar/spider, 4-quadrant scatter
- See `references/chart_creation_guide.md` for rendering specs, color palette, and exhibit-to-chart mapping

#### Writing Style
- **Flowing consulting narrative** — the report reads as connected paragraphs, NOT as bullet lists, data tables, or labeled blocks (INSIGHT/DRIVER/RECOMMENDATION labels are analytical scaffolding, invisible in output)
- Each paragraph follows "assertion → evidence → interpretation → implication" flow in natural prose
- Professional, analytical tone; third-person perspective
- Data-backed assertions only — every claim must pass the "So what?" test (see `references/analysis_framework.md` Module 6)
- **Bold key figures inline** ("用户规模达**11.16亿**"), never list data in isolation
- **Compare, don't just state** — every number needs a benchmark (YoY, vs consensus, vs peer)
- Clear cause-and-effect explanations woven into narrative, not listed as separate blocks
- Chapters open with a context-setting paragraph framing the core question, close with a bridge paragraph connecting to the next section
- Recommendations written as argued conclusions with specific actions, not bullet-point wishlists
- Growth decomposition (penetration × frequency × spend) should be applied to every category analysis
- See `references/structure_contract.md` "Consulting Narrative Writing Rules" for paragraph templates, transition patterns, and examples

#### Content Density
- Pack content densely; avoid leaving nearly-empty pages
- Each page should have substantial text (800-1200 chars) or 1-2 full-size charts
- Highlight paragraphs should combine with nearby content, not waste a whole page

### Step 6: Font Handling (CJK-compatible)

- **Primary CJK font**: Alibaba PuHuiTi (阿里普惠体) -- Light, Regular, Medium, Bold
- **English headings**: Graphik (Light, Regular, Semibold)
- **English body**: TiemposText (Regular, RegularItalic)
- If Alibaba PuHuiTi unavailable: Noto Sans SC or Source Han Sans SC as substitute
- If Graphik unavailable: Montserrat or Inter as substitute
- If TiemposText unavailable: Georgia or Noto Serif as substitute
- Use consistent font strategy across all text paths -- do not mix Latin defaults with CJK patches

## Output Format Notes

### PDF Output
- Preserve exact style contract: photo-based cover, red title text, partner logos
- Running header on all content pages (TOC through report body), absent on cover, author page, and back cover
- CJK font embedding required
- Page numbers start from TOC (page 1)

### DOCX Output
- Maintain same section hierarchy and heading styles
- Photo cover page with title text overlaid or below
- Red H1 headings, black H2/H3 headings
- Charts embedded as images or native Office charts
- Include header/footer matching the style contract

### PPTX Output
- Convert report to slide format: 1-2 slides per major section
- Cover slide with hero image + title
- Content slides: insight headline + bullet points + key chart
- Maintain red/gray/black color scheme
