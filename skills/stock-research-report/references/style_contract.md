# Guotai Haitong Style Contract

## Reference Source

Extracted from two uploaded PDF reference artifacts:
1. 【国泰海通】AI产业跟踪：Qwen开源4B端侧模型.pdf (6 pages)
2. 【海通国际】豆包大模型嵌入手机系统，推动端侧AI从应用级迈向系统级.pdf (8 pages)

Colors extracted via pixel sampling from rendered screenshots at 200 DPI.
Fonts extracted via `fitz` (PyMuPDF) font enumeration.

---

## 1. Color Palette (Pixel-Extracted)

### Guotai Haitong Domestic (国泰海通证券) Variant

| Element | Hex | RGB | Usage |
|---------|-----|-----|-------|
| Primary brand blue | `#00509c` | 0, 80, 156 | Main title, section headings (1., 2., ...) |
| Secondary blue | `#124c8f` | 18, 76, 143 | Header text, bullet markers, 产业观察 label |
| Horizontal rule blue | `#419bf9` | 65, 155, 249 | Header separator line |
| Body text | `#333333` | 51, 51, 51 | Body paragraphs |
| Sub-heading text | `#000000` | 0, 0, 0 | News item titles (bold) |
| Header/footer text | `#666666` | 102, 102, 102 | Disclaimer, page numbers |
| Background | `#ffffff` | 255, 255, 255 | Page background |

### Haitong International (海通国际) Variant

| Element | Hex | RGB | Usage |
|---------|-----|-----|-------|
| Logo text / title | `#0e4c87` | 14, 76, 135 | Logo text "海通国际 HAITONG" |
| Primary blue | `#00509c` | 0, 80, 156 | Main title text |
| Sidebar dark blue | `#004f97` | 0, 79, 151 | Top half of left sidebar |
| Sidebar light blue | `#53c3f1` | 83, 195, 241 | Bottom half of left sidebar |
| Footer gradient | `#0081cc` | 0, 129, 204 | Footer gradient decorative line |
| Bullet accent | `#2fb3d8` | 47, 179, 216 | Bullet point markers |
| Body text | `#333333` | 51, 51, 51 | Body paragraphs |
| Sidebar text | `#ffffff` | 255, 255, 255 | White text on blue sidebar |
| Background | `#ffffff` | 255, 255, 255 | Page background |

---

## 2. Typography System (Font-Extracted via fitz)

### Confirmed Font Families

**Guotai Haitong Domestic:**
- Chinese body + headings: 楷体_GB2312 (KaiTi)
- Latin: Arial, Times New Roman
- Latin bold: Arial Bold, Times New Roman Bold

**Haitong International:**
- Chinese body + headings: KaiTi_GB2312 (楷体)
- Latin: Calibri, Arial, Helvetica, Times New Roman
- Latin bold: Calibri Bold, Times New Roman Bold
- Latin italic: Calibri Italic

### Type Hierarchy

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Main title | 18-22pt | Bold | `#00509c` |
| Section heading (1., 2., ...) | 14-16pt | Bold | `#00509c` |
| Sub-heading (news item title) | 12-13pt | Bold | `#000000` |
| Body text | 10.5-11pt | Regular | `#333333` |
| Header/footer text | 9pt | Regular | `#666666` |
| Page number | 9pt | Regular | `#666666` |
| Disclaimer text | 8-9pt | Regular | `#666666` |
| Cover TOC items | 11pt | Regular | `#000000` |
| Analyst info | 9-10pt | Regular | `#333333` |
| Date | 10pt | Regular | `#333333` |

---

## 3. Page Layout

### Page Dimensions
- Standard A4 (210mm x 297mm)
- Portrait orientation

### Margins

**Guotai Haitong Domestic:**
- Top: ~25mm (header occupies ~15mm)
- Bottom: ~25mm (footer occupies ~15mm)
- Left: ~30mm
- Right: ~25mm

**Haitong International:**
- Top: ~25mm (header occupies ~15mm)
- Bottom: ~25mm (footer occupies ~15mm)
- Left: ~35mm (sidebar banner adds ~20mm)
- Right: ~25mm

### Header Design

**Guotai Haitong:**
- Content: Company logo + "国泰海通证券 GUOTAI HAITONG SECURITIES" (left) | "产业观察" (right)
- Separator: Bright blue horizontal rule `#419bf9` below header
- Font: 9pt, brand blue `#124c8f`
- Appears on all pages EXCEPT cover (page 1)

**Haitong International:**
- Content: Company logo with "海通国际 HAITONG" text (left) + report type label (right)
- Separator: Thin horizontal rule below header
- Logo area includes the blue globe icon + bilingual text
- Appears on all pages EXCEPT cover

### Footer Design

**Guotai Haitong:**
- Content: "请务必阅读正文之后的免责条款部分" (left) + "X of Y" page numbering (right)
- Font: 8-9pt, dark gray `#666666`
- Appears on all pages

**Haitong International:**
- Blue gradient decorative line `#0081cc` spanning full width
- Disclaimer text above gradient line: "请务必阅读正文之后的信息披露和法律声明"
- Page number centered below gradient line
- Small company logo in footer bottom-right area
- Appears on all pages

---

## 4. Cover Page Layout (Detailed)

### Guotai Haitong Cover - Critical Elements

```
+----------------------------------------------------------+
| [Logo+文字]  国泰海通证券          [banner]  产业观察 2025.08.13 |
|          [blue city skyline graphic]                     |
|----------------------------------------------------------|
| 【AI产业跟踪】Qwen开源4B端侧模型                        |
| 摘要：产业最新趋势跟踪，点评产业最新风向                   |
|                                                          |
| ○  AI行业资讯                                            |
|    上海发布具身智能产业发展实施方案                       |
|    2025世界机器人大会8月开幕                             |
| ○  AI应用资讯                                            |
|    百度发布智能云数字员工                                 |
| ○  AI大模型资讯                                          |
|    Qwen团队开源两款4B端侧模型                             |
|    ...                                                   |
| ○  AI科技前沿                                            |
|    ...                                                   |
| ○  风险提示                                               |
|    AI软件销售不及预期...                                  |
|                                                          |
|                    产业研究中心    分析师信息              |
|                    李嘉琪(分析师)                         |
|                    010-83939821                          |
|                    lijiaqi2@gtht.com                     |
|                    登记编号 S0880524040001                |
|                                                          |
|                    往期回顾                              |
|                    【新材料产业周报】... 2025.08.11      |
|                    ...                                   |
+----------------------------------------------------------+
| 请务必阅读正文之后的免责条款部分 1 of 6                  |
+----------------------------------------------------------+
```

Key cover page rules:
- **NO decorative circles, abstract shapes, or ornamental graphics**
- Company logo must be prominent at top-left
- Blue city skyline / decorative banner at top-right (vector graphic)
- "产业观察" as a branded label/banner near top-center
- Date at top-right corner
- Main title in large bold blue (`#00509c`)
- Bullet-point TOC with blue circle markers (`#124c8f`)
- Right panel: 产业研究中心 header, analyst details with icons
- Bottom-right: 往期回顾 section with previous report titles and dates
- Footer with disclaimer + page numbering

### Haitong International Cover - Critical Elements

```
+---+------------------------------------------------------+
|股 | [Logo] 海通国际 HAITONG     股票研究 / 2025-12-02      |
|票 |------------------------------------------------------|
|研 | 豆包大模型嵌入手机系统，推动端侧AI                      |
|究 | 从应用级迈向系统级                                      |
|   |                                                      |
|   |                                         计算机         |
|   |                                         Lin Yang      |
|   |                                         lin.yang@...  |
|---|                                                      |
|行 | 本报告导读：                                            |
|业 | 12月1日，字节跳动豆包团队发布豆包手机助手...            |
|跟 |                                                      |
|踪 | 投资要点：                                              |
|报 | ○ 投资建议：12月1日，字节跳动豆包团队发布...            |
|告 | ○ 12月1日，字节跳动豆包团队发布豆包手机助手...          |
|   | ○ 豆包大模型全面融入操作系统...                         |
|   | ○ 手机作为核心载体，为大模型开拓...                     |
|   | ○ 风险提示：大模型迭代速度不及预期...                    |
|   |                                                      |
|   |                          右侧免责摘要                   |
|   |                          本研究报告由海通国际分销...    |
+---+------------------------------------------------------+
| Footer gradient line + disclaimer text                   |
+----------------------------------------------------------+
```

Key cover page rules:
- Left sidebar: Full-height gradient blue bar (dark `#004f97` to light `#53c3f1`)
- Sidebar text rotated 90 degrees counter-clockwise in white
- Top: "股票研究" | Bottom: "行业跟踪报告" | Very bottom: "证券研究报告"
- Logo at top-left with bilingual text
- Date format: YYYY-MM-DD
- Title in large blue bold text, may span 2 lines
- Investment highlights with blue circle bullets
- Right-side disclaimer summary in smaller text

---

## 5. Visual Elements

### Bullet Points
- **Guotai Haitong**: Filled circles in `#124c8f`, ~0.3em diameter
- **Haitong International**: Filled circles in `#2fb3d8`, ~0.3em diameter
- Aligned with text baseline
- Consistent spacing from text

### Horizontal Rules
- **Guotai Haitong**: Bright blue line `#419bf9`, spans content width
- **Haitong International**: Blue gradient or solid gray line

### Numbered Sections
- Format: "1.", "2.", "3." (Arabic numeral + period)
- Color: Brand blue `#00509c`
- Font weight: Bold
- Followed by section title in same style

### Tables
- Simple grid style with minimal borders
- Header row: Bold text or light blue/gray background
- Body: White rows
- Border color: Light gray `#cccccc`
- **Ratings distribution tables** (Haitong International): Two side-by-side tables showing Chinese and English ratings distribution

### City Skyline Graphic (Guotai Haitong)
- Decorative vector graphic at top-right of cover page
- Shows stylized city skyline (Shanghai/China motif)
- Blue gradient styling matching brand colors
- Used ONLY on cover page, not on body pages

---

## 6. Information Density Guidelines

Professional Chinese securities research reports have **high information density**:

- Body pages should contain dense, continuous text
- Minimize vertical whitespace between news items
- Use compact paragraph spacing (single or 1.15 line spacing)
- Justified text alignment for body content
- Each body page should feel text-rich
- Avoid excessive padding in tables and lists
- Risk warning section may have more whitespace (acceptable)
- Disclaimer pages are densely packed with legal text

---

## 7. CJK Font Strategy

Since reports contain primarily Simplified Chinese with English technical terms:

1. **Primary Chinese font**: KaiTi (楷体) - confirmed in BOTH reference files
   - Use KaiTi / FZKai-Z03 / STKaiti for Chinese text
   
2. **Heading font**: SimHei / Noto Sans CJK SC Bold for all headings

3. **Font fallback strategy**: Define one consistent font family covering both CJK and Latin. Do NOT mix Latin-only fonts with CJK fonts on a per-paragraph basis.

4. **English text**: When embedded in Chinese paragraphs, use the same font family. If the font has Latin glyphs, use them. Otherwise specify compatible Latin fallback in same font stack.

5. **Table cells**: Use wrapping-aware layout for CJK text to prevent overflow

6. **Recommended font stacks**:
   - Chinese body: `KaiTi, STKaiti, FZKai-Z03, "Noto Serif CJK SC", serif`
   - Chinese headings: `SimHei, "Noto Sans CJK SC", "Microsoft YaHei", sans-serif`
   - Latin (GTH): `Arial, "Times New Roman", sans-serif`
   - Latin (HTI): `Calibri, Arial, "Times New Roman", sans-serif`
