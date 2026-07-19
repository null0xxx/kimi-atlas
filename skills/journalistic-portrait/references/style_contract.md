# Style Contract - Southern People Weekly Visual Specification

Extracted from 4-page PDF visual analysis of Southern People Weekly (南方人物周刊).

## 1. Color System

### Primary Palette

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Magazine Red | `#D90712` | 217, 7, 18 | Cover border frame, accent bars, red triangle end-mark, decorative lines, circle highlight on teasers |
| Magazine Red Dark | `#B0060F` | 176, 6, 15 | Hover states |
| Body Black | `#1A1A1A` | 26, 26, 26 | Body text, article titles, headings |
| Heading Black | `#000000` | 0, 0, 0 | Cover headlines, section headers |
| Medium Gray | `#666666` | 102, 102, 102 | Author names, photo captions, secondary info, email addresses |
| Light Gray | `#999999` | 153, 153, 153 | Page numbers, watermark text, tertiary labels |
| Page White | `#FFFFFF` | 255, 255, 255 | Inner page backgrounds, cover text on photos, TOC background |
| Warm Cream | `#F5F0E8` | 245, 240, 232 | Alternate section backgrounds |
| Cover Photo Teal | `#7B8E8A` | 123, 142, 138 | Cover photo dominant background tone (greenish-teal) |

### Cover-Specific Colors

- Cover border outer: `12px solid #D90712`
- Cover border inner white gap: `8px` between red border and photo edge
- Cover border inner white line: `2px solid rgba(255,255,255,0.6)`
- Cover text on photo: `#FFFFFF` (white) with `text-shadow: 0 2px 8px rgba(0,0,0,0.6)`
- Cover slogan "时代的肖像": `#FFFFFF`, 14px, letter-spacing 0.3em, centered at top
- Masthead "南方": small box logo in white, top-left
- Masthead "人物周刊": very large (80-100px), white, bold italic/slanted, positioned left-top
- Bottom info bar: white text on transparent/semi-transparent dark strip at bottom
- Teaser text: `#FFFFFF`, right-aligned, with red circle highlight on "国际" teaser
- Plus icon "+": red `#D90712` on white circle background for international teaser

### Inner Page Colors

- Background: `#FFFFFF`
- Body text: `#1A1A1A`
- Section header text: `#000000`
- Divider line: `1px solid #1A1A1A`
- Page number: `#999999`
- Red accent triangle at article end: `#D90712` (small inline ▼)
- Eye icon: `#1A1A1A` (simple line drawing)
- Photo caption text: `#666666`
- Author info: `#666666`

## 2. Typography System

### Font Stack (CJK-First)

```css
font-family: "PingFang SC", "Noto Sans SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
```

- **Reference fonts**: PingFangSC-Regular + Helvetica (from PDF font extraction)
- **Fallback strategy**: If PingFang SC is unavailable, use Noto Sans SC
- **Latin text within CJK**: Same font stack; PingFang SC covers Latin glyphs
- **English labels in headers**: Uppercase, letter-spacing 0.05em

### Type Scale

| Element | Size | Weight | Line-Height | Color | Notes |
|---------|------|--------|-------------|-------|-------|
| Masthead "人物周刊" | 80-100px | 700 | 1.1 | #FFFFFF | White, italic/slanted, top-left on cover |
| Masthead "南方" | 16px | 400 | 1 | #FFFFFF | Small boxed label above "人物周刊" |
| Cover slogan | 14px | 400 | 1.4 | #FFFFFF | letter-spacing 0.3em, centered at very top |
| Cover headline (name) | 48-56px | 700 | 1.2 | #FFFFFF | White, on photo, lower-left |
| Cover subtitle | 36-42px | 700 | 1.3 | #FFFFFF | Below name |
| Cover author | 14px | 400 | 1.5 | #FFFFFF | Below red accent bar |
| Cover teaser page | 16px | 400 | 1 | #FFFFFF | "P62" style |
| Cover teaser section | 16px | 700 | 1 | #FFFFFF | "文化" style, bold |
| Cover teaser title | 13px | 400 | 1.4 | #FFFFFF | Description line |
| Bottom bar text | 11px | 400 | 1.4 | #FFFFFF | ISSN, price, issue info |
| TOC header EN | 42px | 400 | 1.1 | #000000 | "CONTENTS", uppercase |
| TOC header CN | 24px | 700 | 1.2 | #000000 | "目录" |
| TOC page number | 48px | 300 | 1 | #000000 | "14" style, large light weight |
| TOC label | 13px | 400 | 1.4 | #000000 | "COVER STORY 封面人物" |
| TOC person name | 36px | 700 | 1.2 | #000000 | "刘震云" |
| TOC description | 24px | 400 | 1.4 | #000000 | Subtitle lines |
| TOC photo caption | 12px | 400 | 1.4 | #666666 | Right-aligned below photo |
| TOC nav number | 36px | 300 | 1 | #000000 | "06" "78" "80" |
| TOC nav label EN | 11px | 400 | 1.4 | #000000 | "VIEWPOINTS" uppercase |
| TOC nav label CN | 11px | 700 | 1.4 | #000000 | "世界观" |
| Section header EN | 18px | 400 | 1.4 | #000000 | "VIEWPOINTS" uppercase, letter-spacing 0.05em |
| Section header CN | 16px | 700 | 1.4 | #000000 | "世界观" |
| Sub-section EN | 12px | 400 | 1.4 | #000000 | "MILITARY" uppercase |
| Sub-section CN | 12px | 700 | 1.4 | #000000 | "军事" |
| Article title | 32-36px | 700 | 1.3 | #1A1A1A | Centered |
| Author info | 13px | 400 | 1.5 | #666666 | Centered below title |
| Body text | 15px | 400 | 1.5 | #1A1A1A | Dual-column, text-indent 2em |
| Photo caption | 12px | 400 | 1.4 | #666666 | Below images |
| Page number | 12px | 400 | 1 | #999999 | Bottom corner |
| Footer note | 13px | 400 | 1.5 | #666666 | "详看本期封面报道" |
| End triangle | 8px | 400 | 1 | #D90712 | Inline at end of final paragraph |

### Text Formatting Rules

- **Paragraph indent**: `text-indent: 2em` on all body paragraphs (首行缩进两字符)
- **No indent on first paragraph after title/image**: Remove indent for paragraphs immediately following a title, subtitle, or floated image
- **Text alignment**: `text-align: justify` for body text in dual-column layout
- **Letter-spacing on English headers**: `letter-spacing: 0.05em` for uppercase English labels
- **Chinese character spacing**: Normal (no extra tracking)

## 3. Spacing & Rhythm

### Page Dimensions

- **Page max-width**: `1200px`, centered with `margin: 0 auto`
- **Page padding**: `40px` horizontal on inner pages
- **Column gap**: `40px` between dual columns
- **Section spacing**: `40px` between major sections

### Vertical Rhythm

- Section header to sub-section: `20px`
- Sub-section to title: `30px`
- Title to author: `15px`
- Author to body: `40px`
- Paragraph spacing: `0.8em` margin-bottom
- Image to text: `1em` margin
- Divider line margin: `10px 0`
- Footer divider to note: `15px`

### Cover Spacing

- Red border thickness: `12px`
- Inner white border gap: `8px`
- Inner white line: `2px` at `inset: 8px`
- Slogan top padding: `20px` from inner edge
- Masthead top: `40px` from top inner edge
- "南方" logo positioned above and left of "人物周刊"
- Headline area: lower-left, `80px` from bottom, `60px` from left
- TOC teasers: right side, `60px` from right, vertically centered in lower half
- Bottom info bar: absolute bottom, full width, `40px` height

## 4. Visual Elements

### Red Accent Bar

- Width: `50px`
- Height: `3px`
- Color: `#D90712`
- Used below cover headlines, above author names

### Eye Icon

- Size: `20px` diameter
- Style: Simple line drawing of an eye (circular with pupil)
- Color: `#1A1A1A` (match text)
- Positioned centered below Chinese section header, above divider line

### Divider Line

- `border-top: 1px solid #1A1A1A`
- Full content width
- Margin: `10px 0`

### Red End Triangle

- Content: `▼`
- Color: `#D90712`
- Size: `8px`
- Positioned inline at end of final paragraph, no space before

### Bottom Navigation Bar (TOC page)

- Three-column flex layout at page bottom
- `border-top: 1px solid #1A1A1A; border-bottom: 1px solid #1A1A1A`
- Padding: `20px 0`
- Each column: page number (36px light) + EN label (11px) + CN label (11px bold)
- Separated by `1px solid #1A1A1A` vertical dividers

### Cover Teaser Boxes

- Right-aligned stack of teaser items
- Each teaser: page number + section name + title description
- Spacing between teasers: `20px`
- "国际" teaser has special treatment: red plus icon "+" inside white circle, then content
- Teaser text color: `#FFFFFF`
- Small red horizontal bar (20px x 2px) above each teaser as accent

### Cover Bottom Info Bar

- Position: absolute bottom of cover
- Content from left to right:
  - ISSN barcode + QR code (left-aligned)
  - "定价：人民币15元 港币30元"
  - "总第865期 2026年3月16日 第7期"
  - "国内统一刊号 CN44-1614/C"
  - "www.nfpeople.com" (right-aligned)
- Font size: `11px`
- Color: `#FFFFFF`
- Background: semi-transparent dark `rgba(0,0,0,0.3)`
- Padding: `10px 20px`

## 5. Image Treatment

### Cover Photo

- Full-bleed: `object-fit: cover; width: 100%; height: 100%`
- Dark overlay: `linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.45) 100%)`
- Slight desaturation: `filter: saturate(0.85)` for editorial mood
- Photo subject centered/offset for text placement area

### TOC Page Photo

- Centered, max-width: `45%` of page width
- Aspect ratio: portrait (3:4)
- Caption below: 12px gray, right-aligned
- Margin: `40px auto`

### Inner Page Photos

- Max width within column: `100%`
- Floated images: `max-width: 48%` of column
- Figure margin right float: `margin: 0 0 1em 1.5em`
- Figure margin left float: `margin: 0 1.5em 1em 0`
- Caption: 12px gray (#666), right-aligned below image
- **CRITICAL**: Never use `position: absolute` for images (Rule 2)
