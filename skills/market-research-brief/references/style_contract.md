# Style Contract -- Consulting Market Insight Report

## Reference Source
- **Source type**: Uploaded artifact (PDF)
- **Artifact type**: PDF
- **Reference file type**: PDF
- **Primary language**: Chinese (Simplified) with English mixed

## Typography System

### Reference Font Families (extracted via fitz from the reference PDF)
| Script | Font Family | Weights | Usage |
|--------|-------------|---------|-------|
| Chinese (CJK) | Alibaba PuHuiTi (阿里普惠体) | Light (L), Regular (R), Medium (M), Bold (B) | All Chinese text -- Light for cover title, Bold for chapter headings, Regular for body |
| English (headings) | Graphik | Light, Regular, Semibold | English headings, labels, chart axis titles |
| English (body) | TiemposText | Regular, RegularItalic | English body text, citations, email addresses |

### Font Substitution Strategy
When output format requires font embedding but reference fonts are unavailable:
1. **Chinese**: Noto Sans SC or Source Han Sans SC (closest geometric sans-serif substitutes)
2. **English headings**: Montserrat or Inter
3. **English body**: Georgia or Noto Serif
4. **All-in-one fallback**: Noto Sans SC (covers both CJK and Latin well, professional)

### Typographic Hierarchy
| Element | Weight | Size Impression | Color |
|---------|--------|-----------------|-------|
| Cover title | Light / Regular | Very large, expanded | Deep red (#CC0000) |
| Chapter headings (H1) | Bold | Large (~18-22pt) | Deep red (#CC0000) |
| Section headings (H2) | Bold | Medium (~14-16pt) | Black (#333333) |
| Sub-section headings (H3) | Bold | Medium-small (~12-14pt) | Black (#333333) |
| Body text | Regular | Standard (~10-11pt) | Black (#333333) |
| Chart labels / captions | Regular | Small (~9-10pt) | Dark gray |
| Footnotes / sources | Regular | Very small (~8-9pt) | Gray |
| Header partner text | Regular | Small | Deep red (#CC0000) |
| Header subtitle | Regular | Small | Black (#333333) |

## Color Palette

### Primary Colors
- **Deep red** (accent): `#CC0000` -- chapter titles, chart accent colors, header text, figure labels, highlighted cells in tables
- **Black** (primary text): `#333333`
- **White** (background): `#FFFFFF`

### Chart Colors
- **Primary accent**: Deep red `#CC0000` -- most recent data period, highlighted category
- **Secondary**: Medium-dark gray `#666666`
- **Tertiary**: Medium gray `#999999` -- secondary data series, older data
- **Light**: Light gray `#CCCCCC` -- gridlines, background fills
- **Negative values / red-tones**: Keep red family
- **Positive values / gray-tones**: Gray family
- Background fills: White or very light gray

## Page Layout

### Margins and Spacing
- Top margin: generous (~3cm) to accommodate header
- Side margins: ~2-2.5cm
- Bottom margin: ~2cm with centered page number
- Line spacing: ~1.5x for body text
- Paragraph spacing: ~0.8-1em after paragraphs

### Running Header (every content page except cover, author page, and back cover)
The reference uses a **three-tier header system** on every content page from TOC onwards:
1. **Top line**: "[Research Partner] | [Consulting Firm]" (partner names) centered, in **deep red**
2. **Horizontal rule** below the red text (thin, spanning most of the page width)
3. **Below the rule**: Report subtitle (e.g., "[Report Title]") centered in **black**

### Footer
- Page number centered at bottom
- No other footer content

## Cover Page Design (CRITICAL -- must match reference exactly)

**Upper portion (~60% of page)**:
- Full-width hero photograph showing a relevant market/shopping scene
  (example: woman shopping in supermarket, looking at products)
- Photo bleeds to edges, no border

**Lower portion (~40% of page)**:
- Main title in **deep red**, large Light-weight font (no bold), centered
  - Example: "[Report Title]"
  - Title is the most prominent visual element on the page
- Subtitle / series name in **black**, smaller, below the title, centered
  - Example: "[Report Series Name]"
- Generous white space between title and logos
- Bottom: Partner logos side by side
  - Left: [Research Partner] logo + tagline (small, gray)
  - Right: [Consulting Firm] logo + accent mark

## Author / Acknowledgments Page Design
- Title "作者简介及致谢" in **deep red**, bold, left-aligned, large
- Author entries in plain black text:
  - Name in bold (Chinese name + English name in parentheses)
  - Title and location on next line
  - Contact email in italic
- Team acknowledgments paragraph in regular black text
- Disclaimer/legal text at bottom in very small gray text
- **No blue side borders, no decorative styling** -- simple black text on white
- Copyright notice at very bottom

## Table of Contents Page Design
- Same running header as all content pages
- Title "目录" in **deep red**, bold, left-aligned
- TOC entries:
  - Major sections (摘要, 完整报告) in **red** with dot leaders
  - Subsections (回顾2022, etc.) in **black** with dot leaders
  - Page numbers right-aligned at the end of dot leaders
- Page number centered at bottom

## "Full Report" Section Divider Photo Page
- Top ~40% of page: Full-width photograph (shopping/market image)
- Overlaid or below: White/gray banner with large **black bold** text "完整报告"
- Below banner: 1-2 short paragraphs of intro text in black
- No running header on this page (exception to the header rule)

## Chart Visual Treatment

### Chart Numbering
- Format: "图 X:" -- the "图 X" part in **deep red**, description in **black**
- Sequential numbering throughout: 图1, 图2, 图3...
- Placed above each chart, left-aligned

### Chart Types (must support all types found in reference)

**1. Annotated line charts** (图1, 图7, 图9 style)
- Time-series with multiple lines (3-4 series)
- Key events annotated with vertical gray bars + labels (e.g., "全国新冠感染高峰", "部分城市封控管理")
- Annual comparison table below: year labels + YoY growth rates
- Right-most segment highlighted (most recent period)

**2. Multi-metric grouped bar charts** (图2 style)
- Three side-by-side charts on one page
- Metrics: 销售额, 销量, 平均售价
- Quarterly bar charts with red for standout values
- Red horizontal dashed reference line showing overall growth
- Subtitle for each sub-chart

**3. Stacked 100% bar charts with CAGR side tables** (图5 style)
- 100% stacked columns showing channel share by year
- Percentage labels inside each segment
- Right side: CAGR table for each channel across periods
- Legend to the right

**4. Waterfall / bridge charts** (图6 style)
- Horizontal bars showing brand share change by category
- Centered at zero; positive (left) = top-5 brands gain, negative (right) = top-5 brands lose
- Three components per bar: 排名前5 (red), 排名前6-20 (pink), 长尾 (gray)
- Category labels below columns

**5. Multi-panel mini-charts** (图8, 图10, 图11 style)
- 2x2 grid of small bar charts
- Each panel: one category with title on top
- Shared y-axis scale, consistent visualization
- Red bars for standout quarters

**6. 4-quadrant scatter plots** (图9, 图12 style)
- X-axis and Y-axis showing different metrics
- Each dot labeled with category name
- Dot colors represent industries
- Diagonal dividing lines creating quadrants with labels
- Dense labeling: all 26+ category labels must be visible

### Chart Style Details (ALL chart types)
- Clean white background
- No chart borders
- Gridlines: light gray horizontal only
- Data labels directly on bars/columns (percentage values)
- Legend positioned below chart or to the right
- Source citation below each chart: "资料来源：[Research Partner]；[Consulting Firm]分析"
- Footnotes below source when needed
- Annotations in red text boxes with arrows pointing to relevant data points

## Table Style
- Clean minimal design
- Header row with bold text
- Light horizontal rules only (no vertical rules)
- No alternating row shading
- Highlighted cells use red text or light red background for emphasis
- Source citation below table

## Back Cover
- Mostly white page
- Upper left: [Consulting Firm] logo
- Bottom section: contact info, global office list in small gray text
- QR codes for social media channels (optional)
- "欲了解更多信息" message with website
- No running header/footer on back cover

## Author Page Content Rules
- Simple text-only layout
- No decorative elements, no colored side borders
- Black text on white background throughout
- Title is the only red element on this page
