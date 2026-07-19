# SOTA Analysis Notes

## Reference Artifact
- **File**: Consulting firm + research partner joint market report (PDF)
- **Pages**: 32
- **Produced by**: [Consulting Firm] and [Research Partner]
- **Title**: [Report Title]

## Critical Style Findings (from visual inspection)

### Cover Page (Page 1)
- Hero photo occupying upper ~60% (woman shopping in supermarket with product shelves)
- Title "[Report Title]" in large red (thin/light weight) text, centered below photo
- Subtitle "[Report Series Name]" smaller, black, right-aligned-ish below title
- Bottom: [Research Partner] logo (left) + [Consulting Firm] logo right (red accent)
- White background for lower portion

### Author Page (Page 2)
- Title "作者简介及致谢" in red bold, top-left
- Author entries with name+English name in bold, title below, email in italic
- Team acknowledgments paragraph in regular text
- Disclaimer/legal text in tiny font at bottom
- **Simple black text, NO decorative borders or colored elements**
- Copyright notice at very bottom

### Table of Contents (Page 3)
- Running header: "[Research Partner] | [Consulting Firm]" in red + horizontal rule + "[Report Title]" in black below
- "目录" in red bold
- "摘要" and "完整报告" in red with dots and page numbers
- Subsections in black
- Page number "1" centered at bottom

### Content Pages (Pages 4-7, 10-32)
- Same three-tier header on every content page
- Chapter titles (摘要, 回顾2022, etc.) in red bold
- Subsection headings (品类发展动态, 渠道动态更新, etc.) in black bold
- Body text in black, ~10-11pt
- Charts numbered sequentially
- Page numbers centered at bottom

### "Full Report" Photo Divider (Page 10 equivalent)
- Full-width photo at top
- White banner/overlay with large black text "完整报告"
- Introductory paragraphs below
- No running header on this specific page

### Back Cover (Page 32)
- White page, minimal
- Red firm logo upper left
- Info text and QR codes at bottom
- Global office list in tiny text

## Font Extraction Summary (via fitz)
- **Alibaba PuHuiTi**: L, R, M, B weights used across all pages
- **Graphik**: Light, Regular, Semibold used for Latin text
- **TiemposText**: Regular, RegularItalic used for body and citations
- Page 1 (cover) uses PuHuiTi-L + PuHuiTi-R + Graphik-L + Graphik-R
- Content pages use the full font suite

## Chart Inventory (19 charts total)
| Chart | Type | Description |
|-------|------|-------------|
| 图1 | Annotated line chart | Quarterly FMCG growth 2018-2022 with COVID event annotations |
| 图2 | Multi-metric grouped bars | 销售额/销量/平均售价 quarterly YoY, 3 side-by-side charts |
| 图3 | Multi-panel mini-charts | 4 quadrants: 4 category groups price trends |
| 图4 | Stacked 100% bars | Price distribution changes across categories + CAGR table |
| 图5 | Stacked 100% bars | Channel share evolution with CAGR side table |
| 图6 | Waterfall/bridge chart | Brand competition: top-5 vs long-tail share changes |
| 图7 | Annotated line chart | Q1/Q4 growth trends with recovery annotations |
| 图8 | Multi-panel mini-charts | 2x2 category growth decomposition |
| 图9 | Line chart + category table | 4 recovery pattern categories with color-coded table |
| 图10 | Multi-panel mini-charts | 2x2 price trend charts for 4 sectors |
| 图11 | Multi-panel mini-charts | 2x2 growth recovery pattern charts |
| 图12 | 4-quadrant scatter plot | 26 categories: growth vs share change |
| 图13 | Category classification | Color-coded recovery pattern table |
| 图14 | Multi-panel mini-charts | 2x2 channel dynamics |
| 图15 | Growing/reducing share table | Retailer growth decomposition |
| 图16 | Channel comparison table | O2O platform growth vs penetration |
| 图17 | Stacked bar chart | Channel share evolution with O2O |
| 图18 | Channel classification | O2O penetration by category |
| 图19 | Channel comparison table | O2O vs traditional e-commerce penetration |

## Structural Patterns Observed
- **No numbered section dividers** -- chapters flow directly one after another
- **Dense content** -- each page is information-rich
- **Text-first, chart-second** -- narrative always leads, chart supports
- **Cross-references everywhere** -- (见图X) used consistently
- **Source attribution mandatory** -- every single chart has a source line
- **Footnotes for methodology** -- sample changes, data caveats noted on relevant pages
