---
name: photo-magazine
description: Create premium landscape documents with magazine-quality editorial design. Produces visually rich reports featuring bold typography, full-bleed photography, data visualization cards, and narrative layouts. Use for corporate, research, or creative reports needing editorial aesthetics, multi-column layouts, big-number dashboards, and section-based navigation that blend narrative storytelling with data.
---

# Editorial Magazine Report Skill

Create premium landscape documents inspired by editorial magazine design — combining full-bleed photography, bold typography, data visualization cards, and narrative storytelling.

## Reference Information
- **Reference Source Type**: Uploaded artifact (native PDF)
- **Reference Artifact Type**: PDF
- **Reference File Type**: PDF
- **Supported Outputs**: PDF, DOCX, PPTX
- **Default Output**: PDF (landscape format best preserves the visual design)

## When to Use This Skill

Use this skill for creating documents that combine:
- Narrative storytelling with data and metrics
- Full-bleed photography with editorial typography
- Data visualization (big-number cards, progress charts)
- Multi-column magazine-style layouts
- Section-based navigation and clear information hierarchy
- Premium visual impact for any content domain

## Design Philosophy

The reference design follows these principles:
1. **Question-driven narrative** — Each section opens with an aspirational question
2. **Visual hierarchy** — Large photographs + big data + concise text
3. **Magazine editorial quality** — Landscape orientation, generous whitespace, professional photography
4. **Sustainable readability** — Multi-column text with clear subheadings and visual breaks
5. **Transparency** — Present both successes and challenges openly

## Output Format Selection

| User Request | Recommended Output |
|-------------|-------------------|
| No format specified | PDF (landscape) |
| "Presentation" / "slides" | PPTX |
| "Editable document" / "Word" | DOCX |
| "Print-ready" | PDF |
| "Share online" | PDF or PPTX |

## Core Style Contract

Read `references/style_contract.md` for the complete visual specification including:
- Typography system (SegoeSans + SegoeSerif)
- Color palette (warm cream backgrounds, green accents, pastel data cards)
- Layout patterns (navigation, multi-column, section dividers)
- Graphic elements (hand-drawn underlines, image credit cards, big-number highlights)

### Quick Reference — Key Style Rules

**Page**: Landscape, warm off-white background (#F5F0E8)

**Typography**: Light-weight large headings (42-56pt H1), regular body (10-11pt), serif for quotations

**Colors**: Green accent (#3A7D44) for underlines and active states; pastel cards (mint, yellow, lavender, sky) for data highlights

**Navigation**: Top tab bar with active section highlighted in dark green pill

**Section Openers**: Left text (40%) + Right full-bleed photo (60%)

**Content Pages**: Multi-column (3-4 cols) with vertical dividers

**Data Cards**: Rounded rectangles with colored background + big number + description

## Core Structure Contract

Read `references/structure_contract.md` for the complete document architecture including:
- 5-part section hierarchy (Overview → Themes → Topics → Sub-topics)
- 9 page type templates (Cover, TOC, Section Opener, Content, Dashboard, Target/Progress, Story, Appendix, Back Cover)
- Narrative flow pattern (Question → Challenge → Commitments → Progress → Gaps → Learnings → Future)
- Cross-reference and numbering conventions

### Quick Reference — Document Structure

```
Cover Page
Table of Contents + Key Statistics
Section 1: Overview
  - Leadership message / foreword
  - Highlights dashboard (big metrics)
  - Framework / approach explanation
Section 2-N: Thematic Sections (3-4 major themes)
  - Section opener (photo + title + mini TOC)
  - Approach / strategy pages
  - Progress / data pages
  - Learnings & what's next
Appendix
  - Reporting methodology
  - Disclosures
Back Cover
```

## CJK Typography Strategy

When content includes Chinese, Japanese, or Korean text:
- Use **Noto Sans CJK** or **Source Han Sans** as the primary font family (replacing SegoeSans)
- Use **Noto Serif CJK** or **Source Han Serif** for display/quotation text (replacing SegoeSerif)
- Maintain the same weight hierarchy: Light for H1-H2, Regular for body, Bold for subheadings
- Preserve the large-size + light-weight display treatment for titles
- Ensure line-height is increased to 1.6-1.8 for CJK body text
- Use a single CJK-capable font consistently across the entire document

## Implementation Guidance

### For PDF Output (Recommended)
- Use landscape page orientation (11.69 x 8.27 in)
- Implement the warm cream background color
- Create the top navigation bar as a recurring element
- Use multi-column text frames for content pages
- Place full-bleed images on section opener pages
- Add rounded data highlight cards with pastel backgrounds
- Include green hand-drawn style underline beneath major titles

### For PPTX Output
- Use 16:9 widescreen slides
- Apply warm cream background to all slides
- Create master slides for: Title/Cover, Section Divider, Content (multi-column), Data Dashboard, Two-Column Comparison
- Use the navigation bar as a consistent top element
- Maintain big-number cards and photo treatments

### For DOCX Output
- Use landscape orientation
- Set page background to warm cream
- Use tables to achieve multi-column layouts
- Apply heading styles matching the typography hierarchy
- Insert images with rounded corner treatments where possible

## Content Generation Workflow

1. **Gather content** from user: metrics, stories, photography, goals, progress data
2. **Structure the narrative** using the 5-part hierarchy and question-driven approach
3. **Design section openers** — one per major theme with photo + title + mini TOC
4. **Build content pages** — multi-column layout with subheadings and inline images
5. **Create data pages** — big-number cards, progress charts, target/progress tables
6. **Add appendix** — reporting methodology, disclosures, forward-looking statements
7. **Review for transparency** — ensure challenges and gaps are reported alongside successes

## Quality Checklist

- [ ] Landscape orientation maintained throughout
- [ ] Warm cream background on all pages
- [ ] Top navigation bar with active section highlighted
- [ ] Green hand-drawn underline on section titles
- [ ] Big-number data cards with pastel backgrounds
- [ ] Full-bleed photographs on section openers
- [ ] Multi-column body text with vertical dividers
- [ ] Image credits on all photographs
- [ ] Both successes AND challenges reported
- [ ] Question-driven section openings
- [ ] Clear target vs. progress comparisons
- [ ] Appendix with methodology and disclosures
