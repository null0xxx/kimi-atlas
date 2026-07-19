---
name: stock-research-report
description: Generate securities research reports in Guotai Haitong / Haitong International style. Use for Chinese equity research, industry tracking, investment notes, and financial research documents. Triggers on mentions of Guotai Haitong, Haitong International, industry tracking, equity research, or securities research. Supports domestic and international templates.
---

# Guotai Haitong Research Report Style

Generate securities research reports following the visual identity and document structure of Guotai Haitong Securities (国泰海通证券) and Haitong International (海通国际).

## Overview

Two report style variants from actual SOTA reference artifacts:

1. **Guotai Haitong Domestic (国泰海通证券)** - For mainland China industry tracking reports (产业观察/产业跟踪)
2. **Haitong International (海通国际)** - For international equity research and industry tracking reports (股票研究/行业跟踪报告)

## Workflow

1. Determine target style variant (see "Style Selection")
2. Read the appropriate contract files from `references/`
3. Apply style contract and structure contract when generating the document
4. Produce output in user's requested format

## Style Selection

| Context | Use Variant |
|---------|------------|
| User mentions 国泰海通, 产业观察, 产业跟踪, mainland Chinese research | Guotai Haitong Domestic |
| User mentions 海通国际, HTI, 股票研究, 行业跟踪报告, international | Haitong International |
| User does not specify | Default to Guotai Haitong Domestic |
| User requests both or either | Prefer Guotai Haitong Domestic |

Read `references/style_contract.md` for full visual specifications.
Read `references/structure_contract.md` for document structure templates.

## Reference Source

- **Reference type**: Uploaded PDF artifacts
- **Reference artifact type**: PDF
- **Reference File Type**: PDF
- **Primary language**: Chinese (Simplified) with English mixed content

## Typography (Corrected from SOTA Analysis)

The reference documents use **KaiTi (楷体_GB2312)** for Chinese body text in BOTH variants, confirmed via font extraction:

- **Chinese body text**: KaiTi / KaiTi_GB2312 (楷体) - semi-cursive style
- **Chinese headings**: SimHei (黑体) - sans-serif bold
- **Guotai Haitong Latin**: Arial, Times New Roman (Bold for headings)
- **Haitong International Latin**: Calibri, Arial, Times New Roman (Bold for headings)

Font strategy for output generation:
1. Use a CJK-capable KaiTi-family font for Chinese body text in both variants
2. Use SimHei / Noto Sans CJK SC Bold for headings in both variants
3. Define a consistent font family covering both CJK and Latin scripts
4. Do not mix Latin-only fonts (Helvetica, Calibri) with CJK fonts on a per-paragraph basis
5. Ensure table cells support wrapping for CJK text to prevent overflow

## Supported Outputs

- **PDF** (default for final reports)
- **DOCX** (for editable documents)
- **PPTX** (when slide format is explicitly requested)

## Default Output Selection

- If user explicitly requests a format, use that format
- Otherwise, default to **PDF** for final reports
- Use **DOCX** when user requests editable/draft format
- Use **PPTX** only when user explicitly requests presentation format

## Key Style Summary (Critical Details)

### Guotai Haitong Domestic Colors (Extracted from SOTA)

| Element | Hex | RGB |
|---------|-----|-----|
| Primary brand blue (title, headings) | `#00509c` | 0, 80, 156 |
| Header text / bullet accent | `#124c8f` | 18, 76, 143 |
| Horizontal rule (bright blue) | `#419bf9` | 65, 155, 249 |
| Body text | `#333333` | 51, 51, 51 |
| Header/footer / disclaimer text | `#666666` | 102, 102, 102 |
| Background | `#ffffff` | 255, 255, 255 |

### Haitong International Colors (Extracted from SOTA)

| Element | Hex | RGB |
|---------|-----|-----|
| Title text / logo | `#0e4c87` | 14, 76, 135 |
| Primary blue (same as GTH) | `#00509c` | 0, 80, 156 |
| Sidebar dark blue | `#004f97` | 0, 79, 151 |
| Sidebar light blue | `#53c3f1` | 83, 195, 241 |
| Footer gradient line | `#0081cc` | 0, 129, 204 |
| Bullet accent | `#2fb3d8` | 47, 179, 216 |

### Critical Cover Page Elements (Guotai Haitong)

- Company logo image (top-left): 国泰海通证券 with blue globe icon
- Blue city skyline decorative banner (top-right) - vector/gradient graphic
- Category label banner: 产业观察 (center-top, in branded style)
- Date: YYYY.MM.DD (top-right)
- Main title: Large bold blue text, format `【类别跟踪】主标题`
- One-line summary starting with "摘要："
- Structured bullet-point TOC on cover with blue circle bullets
- Right panel: 产业研究中心 + analyst info (name, title, phone, email, cert number)
- Bottom-right: 往期回顾 section listing previous reports with dates
- **NO decorative circles or abstract geometric decorations**

### Critical Cover Page Elements (Haitong International)

- Left sidebar: Full-height vertical gradient blue bar with white rotated text (股票研究 / 行业跟踪报告 / 证券研究报告)
- Company logo: 海通国际 HAITONG with blue globe icon (top-left)
- Category label + date (top-right): 股票研究 / YYYY-MM-DD
- Main title: Large bold blue text
- Category tag (right): 计算机 / Computer
- Analyst block: Name, email
- 本报告导读 section
- 投资要点 section with blue circle bullets
- Right-side disclaimer summary
- Bottom: Blue gradient decorative line + disclaimer text

### Table of Contents (Page 2)

- Centered heading "目录"
- **Must include dotted leaders connecting section names to page numbers**
- Page numbers right-aligned
- Format: `1. AI行业动态 .................. 3`

### Header/Footer Rules

**Guotai Haitong:**
- Header (all pages except cover): Logo + company name (left) | 产业观察 (right), separated by bright blue horizontal rule
- Footer: "请务必阅读正文之后的免责条款部分" (left) + "X of Y" page numbering (right)

**Haitong International:**
- Header (all pages except cover): Logo (left) | Report type label (right), separated by horizontal rule
- Footer: Blue gradient decorative line + disclaimer text + page number centered + small logo

### Document Structure Rules

- Cover page = page 1
- Table of Contents = page 2
- Body content starts page 3
- Risk Warning section starts on new page
- Legal Disclaimer starts on new page (multiple pages)
- Each main section starts on new page when space insufficient
- No orphaned headings

### Information Density

Professional Chinese brokerage reports are **densely packed** with text. Minimize whitespace:
- Body text: justified alignment, 10.5-11pt
- Generous but not excessive paragraph spacing
- News items flow continuously with minimal gaps
- Body pages should feel text-rich, not sparse

## Output Policy

- Maintain consistent section hierarchy across all output formats
- Preserve exhibit numbering, table semantics, and visual hierarchy
- Header/footer rules apply per selected variant contract
- Cross-reference sections by number throughout document
