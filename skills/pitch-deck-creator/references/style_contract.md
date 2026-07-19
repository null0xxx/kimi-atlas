# Style Contract: Business Plan Pitch Deck

This document defines the reusable visual-style rules extracted from the reference deck (an 18-slide Chinese FP/BP PDF for a power-electronics startup). The contract is language-agnostic — apply it to English decks by choosing equivalent font families.

## CRITICAL STYLE RULES (Must Follow)

1. **WHITE backgrounds on ALL content slides** — No exceptions. The reference uses clean white backgrounds throughout.
2. **Navy blue is the PRIMARY accent color** — Not green. Green is ONLY for secondary chart series.
3. **No section-divider pages** — The reference has a flat 18-page flow with no chapter dividers.
4. **Cover is split layout** — 1/3 white left panel + 2/3 image right panel.
5. **Funding page uses 4 separate ring charts** — Not a single donut chart.
6. **Team page shows actual photos** — Not generic icons or placeholders.
7. **Product pages show actual images** — Not empty placeholders.
8. **No "Strictly Confidential" watermarks** — The reference has no such watermark.

## Reference Typography & Language

- Primary script: Chinese (Simplified) with English technical terms mixed in.
- Reference font families identified via PDF font extraction:
  - **Chinese body & headings**: KaiTi (STKaiti) — a serif calligraphic CJK typeface used for titles, subtitles, and body text.
  - **Latin/alphanumeric supplement**: ArialMT / Arial-BoldMT — a sans-serif typeface used for numbers, English labels, and formulas.
  - **Chinese bold emphasis**: MicrosoftYaHei-Bold — used for bold-stressed phrases in Chinese.
- When content is not guaranteed to be Latin-only, prefer **one consistent CJK-capable font family** across the entire deck. Good substitutes when KaiTi is unavailable:
  - Source Han Serif (Noto Serif CJK SC) — preserves the serif calligraphic character.
  - SimSun — widely available serif CJK fallback.
  - Microsoft YaHei — clean sans-serif CJK option if a modern look is preferred.
- For English-only decks, substitute KaiTi with a clean serif such as Georgia or Merriweather.

## Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Primary Blue | `#1B3A6B` | Header bars, contrast boxes, key numbers, icons, primary chart fills, page-title underline. This is the DOMINANT color. |
| Accent Blue | `#2C5885` | Header bar backgrounds, title labels, highlighted text |
| Accent Green | `#4A9B7F` | Secondary chart color ONLY (e.g., green bars for overseas/secondary data series). NOT a primary accent. |
| Light Gray | `#F5F5F5` | Background fill for special contrast areas |
| Dark Text | `#1A1A1A` | Body text, regular Chinese characters |
| Medium Gray | `#666666` | Sub-text, annotations, chart labels |
| Light Gray BG | `#F8F8F8` | Chart background, table backgrounds |
| White | `#FFFFFF` | Primary page background, text on dark elements |
| Contrast Box BG | `#1B3A6B` | Rounded rectangles for module headers / conclusion banners (white text inside) |
| Conclusion Banner | `#1B3A6B` | Bottom-of-page banner for key takeaways (white text inside) |

## Page Layout & Spacing

### Slide Ratio
- 16:9 widescreen (standard pitch-deck ratio).

### Master Page Template (CRITICAL)
- **Background**: White (`#FFFFFF`) on EVERY content slide. No dark backgrounds anywhere.
- **Top area**: Page title in the top-left corner. Style: 22–28 pt, weight bold, color Dark Text.
- **Header underline**: A navy blue horizontal line (2 px, `#1B3A6B`) runs full width below the title area, across the entire slide width.
- **Top-right logo**: Company logo, approximately 120 × 40 px, placed flush with the right margin near the top. Must appear on EVERY content slide.
- **Safe margins**: ~40 px left/right, ~35 px top/bottom.
- **Content zone**: Full width below the header rule, leaving bottom margin for optional conclusion banners.

### Content Density
- Low-to-moderate density. Each slide should convey one core message.
- Generous whitespace between modules and between text blocks.
- Avoid cramming more than 6 bullet points or 3 chart panels per slide.

## Visual Elements

### Rounded Contrast Box
- Shape: Rounded rectangle, radius 8–12 px.
- Fill: Primary Blue (`#1B3A6B`).
- Text inside: white, centered, bold, 16–18 pt.
- Used for: module labels, section headers inside slides, category tags, key takeaway banners.

### Data Highlight Text
- Inline key metrics (e.g., `>50%`, `超10年`, `100%+`): bold and enlarged (font size +2–4 pt above surrounding text).
- Frequency: 2–4 highlighted numbers per content slide is optimal.

### Section Divider Line
- A thin horizontal line (1–2 px, Primary Blue) used to separate content sections within a slide.

## Chart & Data Visualization Style

### Bar / Column Charts
- **Primary series fill**: Navy Blue (`#1B3A6B`). This is the default color for all bars.
- **Secondary series fill**: Accent Green (`#4A9B7F`) — used ONLY for secondary/foreign/overseas data series in grouped or stacked charts.
- Background: White or Light Gray BG (`#F8F8F8`).
- Labels: data source + agency name below each chart in 10–11 pt Medium Gray.
- Category axis labels: 12–13 pt Dark Text.
- Value axis: no axis line, grid lines optional (light gray dash).

### Donut / Ring Charts
- Inner radius: approximately 55% of outer radius.
- **Funding page**: Four SEPARATE ring charts (not one donut). Each ring shows one allocation percentage (e.g., 30% R&D, 25% production, 25% capacity, 20% market expansion).
- Focused wedge: Primary Blue (`#1B3A6B`).
- Supporting wedge(s): Light Gray (`#E0E0E0`).
- Center label: bold percentage in Dark Text.
- Legend: below or to the right, matching the ring colors.

### Pie Charts
- **Revenue split pie chart** (70/30 style): Primary Blue (`#1B3A6B`) for the 70% wedge, Accent Green (`#4A9B7F`) for the 30% wedge.
- White separator line between wedges (1 px).
- Percentage labels inside wedges in white or on the outside.

### Flow / Roadmap Diagrams
- Sequential stages connected by arrows.
- Each stage container: rounded rectangle with a subtle background gradient or a light gray fill, with a white border.
- Stage number badge: small Primary Blue circle at top.
- Content: title bold, below that bullet points in normal weight.
- Arrow connectors: Primary Blue, with a sharp triangle arrowhead.

## Iconography
- Style: Minimalist outline-line icons, monochrome (Primary Blue or Dark Text).
- Size: 32–48 px diameter when used as circular-icon feature cards.
- Circular icon containers: thin circle outline, icon inside, placed above feature titles in grid layouts.

## Table Style
- Header row: Primary Blue background (`#1B3A6B`), white bold text, slight padding.
- Data rows: alternating white / `#F8F8F8` (zebra strip optional).
- Cell borders: horizontal only, 1 px solid `#E0E0E0`.
- First column: bold when it contains category labels.
- Alignment: center for numbers/metrics, left for text. Vertical alignment: middle.
- Row height: minimum 36 px to accommodate CJK text.

## Header/Footer Rules
- No page numbers displayed on content slides.
- The top-right logo acts as a persistent brand anchor on every slide.
- **No "Strictly Confidential" watermark or footer text.**
- Optional footer for the last ~2 slides: confidentiality disclaimer + company branding + contact info — but only as normal visible text, not as a watermark.

## Cover & Back Page

### Cover Slide (CRITICAL — Split Layout)
- Layout: Split — approximately 1/3 left (white background) + 2/3 right (full-bleed dramatic image).
- Left panel:
  - Company logo top-aligned.
  - Main title: very large (36–48 pt), bold, two lines, Dark Text.
  - Subtitle: 20–24 pt, Medium Gray.
  - Bottom area: investor / advisory firm logo.
- Right panel: high-quality product or industry image. The left portion of this image near the fold should have a clean, gradient-blended edge (or a compositional break) so the text in the left panel is readable.
- **Do NOT use a full-bleed dark image background for the cover.**

### Closing / Disclaimer Slide
- White background, clean layout.
- Main title: "声明" (Disclaimer) or equivalent, large bold.
- Content: structured disclaimer bullet points.
- Bottom section: contact information in two columns, investor logo.
