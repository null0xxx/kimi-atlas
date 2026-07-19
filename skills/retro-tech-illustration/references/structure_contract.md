# Structure Contract - Retro Tech Art Documents

Extracted from reference DOCX and PDF artifacts.

## Table of Contents
1. [Document Section Hierarchy](#document-section-hierarchy)
2. [Page-by-Page Layout Specification](#page-by-page-layout-specification)
3. [Chapter Structure](#chapter-structure)
4. [Table Formats](#table-formats)
5. [Callout and Highlight Boxes](#callout-and-highlight-boxes)
6. [List Formats](#list-formats)
7. [Header and Footer](#header-and-footer)
8. [Page Break Rules](#page-break-rules)
9. [Information Density Guidelines](#information-density-guidelines)

## Document Section Hierarchy

Standard document has exactly 10 chapters across 14 pages:

```
Page 1:  Cover Page (dark purple gradient background)
Page 2:  Divider page (centered header + horizontal line only, rest blank)
Page 3:  Table of Contents (single page, chapter titles + right-aligned page numbers)
Page 4:  Chapter 1: Style Overview (风格概述)
Page 5:  Chapter 2: Historical Development (历史发展)
Page 6:  Chapter 3: Core Design Philosophy (核心设计哲学)
Pages 7-8: Chapter 4: Visual Elements (视觉元素详解)
Page 9:  Chapter 5: Sub-Style Comparison (子风格对比)
Page 10: Chapter 6: Modern Application Cases (现代应用案例)
Page 11: Chapter 7: Creation Tools and Resources (创作工具与资源)
Page 12: Chapter 8: Classic Color Schemes (经典配色方案)
Page 13: Chapter 9: Creation Techniques (创作技巧)
Page 14: Chapter 10: Summary and References (总结与参考)
```

## Page-by-Page Layout Specification

### Page 1 - Cover Page
- Full-page dark purple gradient background (`#1a0f2e` to `#0a0a0f`)
- Title "Retro Tech Art Style" in large rainbow gradient text (pink->cyan->purple)
- Thin purple horizontal line beneath title
- Chinese subtitle "复古科技艺术风格设计理念完整指南" in pink/magenta, centered
- Date "2026年4月" in cyan, centered, below subtitle
- NO other decorative elements, NO page number

### Page 2 - Divider Page
- Centered header text: "Retro Tech Art Style 设计理念指南"
- Dark horizontal line below header
- Rest of page is blank/white
- NO page number (or page number "2" centered if required)

### Page 3 - Table of Contents
- Centered header: "Retro Tech Art Style 设计理念指南"
- "目录" heading with purple gradient and left vertical purple bar accent
- 10 chapter entries with right-aligned page numbers
- Dotted or clean line leading from chapter title to page number
- NO subsection entries
- Target: all 10 entries fit on single page with comfortable spacing

### Content Pages (Pages 4-14)
- Centered header: "Retro Tech Art Style 设计理念指南" on every page
- Chapter H1 heading with purple gradient and underline
- Section H2 headings with pink left border accent
- Body text, lists, tables, callout boxes as needed
- Page number centered at bottom

## Chapter Structure

### Chapter Heading (H1)
- Format: "第X章：[Title]"
- Style: Large, purple-to-pink gradient, full-width gradient underline
- Page break before each chapter heading
- Generous top margin (heading appears below header with whitespace)

### Section Heading (H2)
- Format: "X.Y [Title]"
- Style: Medium-large, pink/magenta (`#ff2aa3`), left border accent (4px vertical bar)
- No page break before

### Subsection (H3)
- Format: Bold inline or small heading
- Style: Bold with accent color for key terms
- Used sparingly - prefer bold inline text within body paragraphs

## Table Formats

### Timeline Table (历史时间线)
| Period | Event | Significance |
|--------|-------|-------------|
| 1909年 | 马里内蒂发表《未来主义宣言》 | 现代复古未来主义起源 |
| 1940s-1960s | 太空时代乐观主义 | 原子朋克、太空竞赛美学 |

Rules: 3 columns, chronological order, bold period column. Dark slate header.

### Sub-Style Comparison Table (子风格对比)
| Style | Era | Core Features | Mood |
|-------|-----|--------------|------|
| Synthwave | 2000s至今 | 霓虹网格、超跑、日落 | 怀旧能量 |
| Vaporwave | 2000s至今 | 雕像、故障、消费文化 | 讽刺忧郁 |

Rules: 4 columns (Style, Era, Core Features, Mood), one row per sub-style, concise descriptions. Dark slate header.

### Resource Table (资源表格)
| Name | Usage | Price |
|------|-------|-------|
| Adobe Photoshop | 图像编辑、复古效果 | 订阅制 |
| GIMP | 免费图像编辑 | 免费 |

Rules: 3 columns (Name, Usage, Price). Dark slate header.

### Color Palette Table (配色方案)
| Name | Color 1 | Color 2 | Color 3 | Color 4 | Color 5 | Mood |
|------|---------|---------|---------|---------|---------|------|
| Synthwave Sunset | #ffd319 | #ff901f | #ff2975 | #f222ff | #8c1eff | 怀旧能量 |

Rules: 7 columns. Color cells display actual color swatch. Mood description in final column.

### Font Table (字体表格)
| Name | Type | Usage |
|------|------|-------|
| Commando | 粗体无衬线 | 标题/Logo |
| Streamster | 手写刷体 | 副标题/装饰 |

Rules: 3 columns (Name, Type, Usage). Dark slate header.

## Callout and Highlight Boxes

### Definition Box
- Light tinted background (subtle gray `#f8f9fa` or accent at 5% opacity)
- Left border accent (4px, purple `#7b2cff` or pink `#ff2aa3`)
- Used for: Key definitions, core concepts
- Example: "核心定义：Retro Tech Art Style是'从过去看未来'或'从未来看过去'的双重时间维度的视觉表达。"

### Highlight Box
- Slightly more prominent background
- Used for: Important notes, tips, concluding remarks
- Example: "结语：Retro Tech Art Style不仅是一种设计风格，更是一种对过去的致敬和对未来的想象。"

## List Formats

### Bulleted Lists
- Use for: Core concepts, feature lists, tool lists, element descriptions
- Bullet style: Black round bullet
- Format: **Bold purple key term** followed by dash and description in black
- Example: "**粗体无衬线：** Commando、Hauser - 标题和Logo"
- Indentation: Consistent, 1-2 levels max

### Numbered Lists
- Use for: Step-by-step procedures, ranked items, learning paths
- Number style: Arabic numerals with period
- Format: Number followed by bold label and description
- Example: "1. **基础：** 学习图层样式、渐变、混合模式"

## Header and Footer

### Header (Critical - Fixed Content)
- Content: EXACTLY "Retro Tech Art Style 设计理念指南"
- Position: Centered at top of every content page
- Style: Small font, regular weight, subtle dark gray color
- Same header on ALL content pages (pages 2-14)
- Do NOT use dynamic chapter/section headers

### Footer
- Content: Page number only
- Position: Centered at bottom of page
- Style: Small, regular weight
- Start numbering from page 2 (or page 1 on cover, depending on convention)

## Page Break Rules

1. **Cover page**: Always separate page (page 1)
2. **Divider page**: Separate page after cover (page 2) - header + line only
3. **Table of contents**: Single separate page (page 3)
4. **Each chapter (H1)**: New page
5. **Sections (H2)**: No forced page break, flow naturally
6. **Large tables**: May break across pages with header row repeated
7. **Images**: Keep with surrounding text where possible

## Information Density Guidelines

### Target Page Count
- Total document: approximately 14 pages (matching reference)
- Do NOT exceed 16 pages for the standard 10-chapter guide
- Keep content concise and information-dense

### Content Conciseness Rules
- Use brief, direct sentences
- Prefer bullet points over paragraphs where possible
- Each bullet: bold key term + short description (one line preferred)
- Avoid elaboration and extensive explanations
- Tables should be compact with concise cell content
- Callout boxes: 1-2 sentences maximum

### Per-Chapter Guidelines
- Chapter 1 (Style Overview): 1 page - definition, core concepts, trends
- Chapter 2 (History): 1 page - timeline table only
- Chapter 3 (Philosophy): 1 page - 4 short sections with 1-2 sentences each
- Chapter 4 (Visual Elements): 2 pages - color table, font list, graphic elements, textures
- Chapter 5 (Sub-Styles): 1 page - comparison table
- Chapter 6 (Applications): 1 page - bullet lists by category
- Chapter 7 (Tools): 1 page - software table, resource links
- Chapter 8 (Color Schemes): 1 page - color swatches
- Chapter 9 (Techniques): 1 page - bullet lists + numbered process
- Chapter 10 (Summary): 1 page - key points + learning path + closing remark

## Heading Level Summary

| Level | Tag | Visual Treatment | Page Break |
|-------|-----|-----------------|------------|
| Document title | H0 | Cover page, rainbow gradient (pink->cyan->purple) | Yes |
| Chapter | H1 | Large, purple gradient, bottom gradient underline | Yes |
| Section | H2 | Medium, pink left border accent | No |
| Subsection | H3 | Bold, inline accent | No |
| Body | P | Regular, black on white | No |
