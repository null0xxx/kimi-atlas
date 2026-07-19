---
name: pitch-deck-creator
description: "Creates professional pitch decks and business plans in the style of a Chinese startup funding proposal (融资计划书 / BP). Triggered by requests to create investor decks, financing proposals, company overviews with market analysis, or any fundraising presentation. Supports Chinese and English content, outputs PPTX by default, and follows a polished 18-slide template with clean white backgrounds and navy blue accents."
---

# Business Plan Pitch Deck Skill

Create polished, investor-facing business plan / financing proposal presentations following a proven professional template style.

## Reference Source

- **Reference type**: Uploaded artifact (PDF)
- **Reference artifact type**: PDF (18-slide Chinese startup pitch deck for power-electronics company)
- **Effective Reference File Type**: PPTX (slide-deck presentation)
- **Primary language**: Chinese (Simplified) with English technical terms
- **Reference fonts**: KaiTi (STKaiti) for Chinese body/headings; Arial for Latin/numbers; MicrosoftYaHei-Bold for emphasis

## Supported Outputs

| Format | Support | Notes |
|--------|---------|-------|
| PPTX | Primary | Default output; fully editable slides |
| PDF | Yes | Export from PPTX for distribution |

## Default Output Selection

1. If user explicitly requests a format, use that format.
2. Otherwise, default to **PPTX** (editable presentation).
3. If the user asks for a "shareable" / "final" version, offer PDF as well.

## Workflow: Creating a Pitch Deck

### Step 1 — Gather Inputs

Collect from the user:
- Company name, logo, tagline
- Industry / sector
- Funding round and target amount
- Key metrics (revenue, growth rate, margins, team size, IP count)
- Product/service description + photos (if available)
- Competitive landscape (3–5 peers)
- Financial projections (3–5 years)
- Team bios + photos
- Market size / TAM data

If the user provides a text brief or existing document, extract the above.

### Step 2 — Plan Slide Structure

Map the user's content to the standard section flow. Read `references/structure_contract.md` for the full hierarchy and layout patterns. The default 14-section flow is:

1. **Cover** — Company identity + investor branding + dramatic image
2. **Investment Highlights** — 6-point grid of key selling points
3. **Market Opportunity** — Market-size charts + growth thesis
4. **Industry Landscape** — Competitor mapping / peer comparison
5. **Company Positioning** — Strategic pillars / value proposition
6. **Core Competitiveness** — Advantages matrix
7. **Product Portfolio** — Product overview + technical architecture
8. **Technology Differentiation** — Technical flow comparison + parameter tables
9. **Team Introduction** — Founder + core team + advisory
10. **Growth Forecast** — Revenue/order projections with charts
11. **Vision / Roadmap** — Multi-phase strategic roadmap
12. **Financing Plan** — Fund-raise ask + allocation breakdown
13. **Appendix** — Supporting data, product photos, detailed comparisons
14. **Disclaimer** — Legal disclaimer + contact information

**Adaptation rule**: Skip sections the user does not have content for. Merge closely related sections if the deck would otherwise exceed 20 slides. For seed-stage companies, sections 7–9 may be lighter; for growth-stage, sections 10–12 are heavier.

**CRITICAL**: The reference uses a flat 18-page structure with NO section-divider pages between major sections. Do NOT add chapter-divider slides.

### Step 3 — Apply Visual Style

Read `references/style_contract.md` for the full style specification. Key rules:

- **Background**: WHITE (`#FFFFFF`) on ALL content slides. No dark backgrounds ever.
- **Color palette**: Primary Blue `#1B3A6B` (navy blue) as the dominant accent. Green is ONLY for secondary chart series (e.g., green bars for overseas/secondary data). No green as primary accent.
- **Header**: Navy blue horizontal line (2 px) below the page title on every content slide. Company logo in top-right corner on every content page.
- **Data visualization**: Navy blue bars/columns as PRIMARY color. Green only for secondary data series. Donut charts use navy blue + green (or navy blue + gray).
- **Highlight style**: Key metrics in bold, 2–4 pt larger than surrounding text.
- **Conclusion banners**: Full-width navy blue rectangle at bottom with white takeaway text.

### Step 4 — Design Each Slide

For each slide, choose from the layout pattern catalog defined in `references/structure_contract.md`:

- **Grid Highlights** (Pattern A) — 3×2 cards with icons, titles, and two-line bullet summaries
- **Dual Chart** (Pattern B) — Two side-by-side charts with dark title bars
- **Comparison Flow** (Pattern C) — Horizontal arrow flow + comparison table below
- **Strategic Pillars** (Pattern D) — Vertical stack: navy blue label pill + bullet list per row
- **Three-Column Matrix** (Pattern E) — Three side-by-side modules + bottom icon grid
- **Top/Bottom Comparison** (Pattern F) — Upper/lower flow diagrams with callout boxes
- **Photo Grid** (Pattern G) — 3-column product photos with captions
- **Conclusion Banner Bottom** (Pattern H) — Navy blue full-width takeaway banner

Design principles per slide:
- One slide, one message
- Max 40–50 CJK chars or ~80 English words of body text
- 3–6 highlighted data points
- Prefer charts/diagrams over text bullets
- Every claim backed by a number, chart, or named source

### Step 5 — Review & Polish

- Ensure all content pages have WHITE backgrounds — no exceptions
- Verify navy blue is the primary accent color everywhere
- Check that all charts use navy blue as the primary fill color
- Confirm logo placement (top-right) is consistent on every content slide
- Ensure header underline (navy blue) appears below every page title
- Validate that text does not overflow shapes
- Verify team member photos are actual photos, not generic icons
- Verify product photos are actual images, not placeholders
- Do NOT add "Strictly Confidential" watermarks or footers

## Slide Type Quick Reference

| Slide Type | Recommended Layout Pattern | Key Visual Elements |
|---|---|---|
| Cover | Split 1/3 white + 2/3 image | Logo, title, subtitle, investor logo, hero image on right |
| Highlights | Pattern A (Grid) | 6 icon cards, key numbers |
| Market size | Pattern B (Dual Chart) | Navy blue bar charts, source labels |
| Competitors | Pattern C (Comparison Flow) | Arrow flow, peer logos, comparison table |
| Positioning | Pattern D (Pillars) | Navy blue label pills + bullet lists |
| Advantages | Pattern E (3-Column Matrix) | Side-by-side modules, icon grid |
| Tech differentiation | Pattern F (Top/Bottom) | Flow diagrams, callout boxes |
| Team | Custom: Photo + Bio cards | Headshots (actual photos), names, titles, bullet bios |
| Financial projections | Pattern B (Dual Chart) | Navy blue bar chart + navy/green pie chart |
| Roadmap | Sequential stages | Rounded rectangles, arrows, stage numbers |
| Funding ask | Custom: Centered large number + 4 ring charts | Large amount, 4 separate donut charts, allocation labels |
| Product photos | Pattern G (Photo Grid) | 3 actual product images with captions |
| Comparison tables | Custom: Full-width table | Navy blue header, zebra rows, bold first column |
| Disclaimer | Text-heavy single column | Large title, bullet disclaimers, contact grid |

## Font Strategy for CJK Content

When the deck contains Chinese text (default assumption):
- **Heading font**: KaiTi / STKaiti (or Source Han Serif SC as substitute)
- **Body font**: Same as heading (single-family consistency)
- **Latin/number supplement**: Arial (for English terms and numerals)
- **Bold emphasis**: Use the font's bold weight or switch to a bold-compatible CJK face (e.g., Microsoft YaHei Bold)

When the deck is English-only:
- **Heading font**: Georgia or Merriweather (serif, professional)
- **Body font**: Same family
- **Accent/bold**: Use the bold weight of the same family
