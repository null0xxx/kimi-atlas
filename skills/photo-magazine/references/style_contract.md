# Style Contract — Corporate Impact Report

Extracted from Microsoft Environmental Sustainability Report 2024 (88-page landscape PDF).

## Reference Source
- **Type**: Uploaded PDF artifact (native PDF)
- **Reference File Type**: PDF
- **Primary Language**: English
- **Reference Fonts**: SegoeSans (sans-serif, primary), SegoeSerif (serif, display/quotations), Calibri, TimesNewRoman

## Page System
- **Orientation**: Landscape (A4/Letter width, ~11.69 x 8.27 in)
- **Margins**: Generous — approximately 60-80px on all sides
- **Background**: Warm off-white / cream (#F5F0E8 to #F8F5EF)
- **Content width**: ~90% of page width, centered

## Typography System

### Font Families
- **Primary (Headings, Body, UI)**: SegoeSans — modern geometric sans-serif, available in multiple weights
- **Display (Quotations, Foreword titles)**: SegoeSerif — elegant serif with high contrast
- **CJK Substitution Strategy**: When generating CJK content, use a single CJK-capable sans-serif family (e.g., Noto Sans CJK, Source Han Sans) for body and headings. For display/quotation text requiring serif character, use a compatible CJK serif (e.g., Noto Serif CJK, Source Han Serif). Preserve the light-weight + large-size display treatment regardless of script.

### Hierarchy
| Level | Usage | Size | Weight | Font | Color |
|-------|-------|------|--------|------|-------|
| H1 | Section opener titles | 42-56pt | Light/Thin | SegoeSans | Dark charcoal (#2D2D2D) |
| H2 | Page headlines | 32-42pt | Light/Thin | SegoeSans | Dark charcoal |
| H3 | Subsection titles | 18-22pt | Semibold | SegoeSans | Dark charcoal |
| H4 | Paragraph headings | 14-16pt | Bold | SegoeSans | Dark charcoal |
| Body | Main content | 10-11pt | Regular | SegoeSans | Dark charcoal |
| Caption | Image credits, small text | 8-9pt | Regular | SegoeSans | Gray (#666) |
| Quote | Pull quotes, foreword | 20-28pt | Light Italic | SegoeSerif | Deep green (#3A7D44) |
| Big Number | Stat highlights | 48-72pt | Light | SegoeSans | Dark charcoal |

### Special Typography Treatments
- **Green hand-drawn underline**: Used beneath H1/H2 titles on section openers — a short (~80-120px), slightly curved green stroke below the last line of the title
- **Title casing**: Sentence case for all headings (not Title Case)
- **Line height**: 1.3-1.4 for headings, 1.5-1.6 for body

## Color Palette

### Backgrounds
| Token | Value | Usage |
|-------|-------|-------|
| page-bg | #F5F0E8 | Page background |
| card-mint | #C5E5D8 | Data highlight cards (carbon/water) |
| card-yellow | #E8D5A3 | Data highlight cards |
| card-lavender | #D4C5E8 | Data highlight cards |
| card-sky | #A8D0E6 | Data highlight cards |
| nav-active | #2D4A3E | Active nav tab background |

### Text & Accents
| Token | Value | Usage |
|-------|-------|-------|
| text-primary | #2D2D2D | Body text, headings |
| text-secondary | #666666 | Captions, metadata |
| accent-green | #3A7D44 | Decorative underlines, active states |
| accent-light-green | #7BC17E | Hand-drawn underline stroke |
| link-blue | #0056B3 | Hyperlinks (underlined) |

## Layout Patterns

### Navigation Bar (top of every page)
- **Position**: Fixed top, full width
- **Height**: ~40px
- **Content**: Horizontal tab pills — "Overview", "Microsoft sustainability", "Customer sustainability", "Global sustainability", "Appendix"
- **Active state**: Dark green pill background (#2D4A3E), white text
- **Inactive state**: Transparent background, dark text
- **Separator**: Thin horizontal rule below nav (~1px, #ccc)
- **Page number**: Right-aligned, format "☰ 04" inside a subtle gray pill

### Section Divider Pages
- **Layout**: Left 45% text + Right 55% full-bleed photograph
- **Left panel**: 
  - Section label (small, uppercase-ish, green)
  - Large H1 title with green hand-drawn underline
  - 1-2 paragraph intro
  - Mini TOC (topic + page number pairs)
- **Right panel**: Full-height photograph with bottom-right photographer credit card

### Content Pages
- **Layout**: Multi-column (3-4 columns) with thin vertical dividers
- **Left margin**: Often contains a sidebar with H2 title + section summary
- **Main area**: 2-3 columns of body text with H3/H4 subheadings
- **Images**: Inline, often with rounded corners or circular crop for portraits

### Data/Highlight Cards
- **Position**: Inline or floating over images
- **Style**: Rounded rectangle with colored background (mint/yellow/lavender/sky)
- **Content**: Big Number (48-72pt) + short description (10pt)
- **Icon**: Small icon in top-right corner of card (leaf, water drop, etc.)

### Target/Progress Tables
- **Layout**: 2-column comparison ("Our targets" | "Our progress")
- **Style**: Clean, no borders, green checkmark icons for achieved items
- **Typography**: Bold for target/progress titles, regular for descriptions

### Photograph Credit Cards
- **Position**: Bottom-right or bottom-left of photographs
- **Style**: Semi-transparent white or light-tinted rounded rectangle
- **Content**: Camera icon + "Captured by:" + Name + Title + Location

## Graphic Elements

### Dividers
- **Vertical**: 1px solid #CCCCCC, used between content columns
- **Horizontal**: 1px solid #CCCCCC, below navigation and above footers

### Bullets
- **Numbered**: Green circle with white number inside (for key initiatives)
- **Unordered**: Small green dot or checkmark

### Charts
- **Horizontal bar charts**: Clean, minimal, teal/green bars on white background
- **No 3D effects, no gradients** — flat, modern style
- **Labels**: Sans-serif, small size

### Image Treatment
- **Full-bleed photos**: High-quality nature/landscape/environmental photography
- **Inline photos**: Rounded corners (8-12px radius)
- **Portrait photos**: Circular crop
- **Illustrations**: Flat, 2D isometric style for data explanation pages

## Density & Rhythm
- **High visual variety**: Alternating between text-heavy pages, photo pages, data pages
- **Breathing room**: Generous whitespace between sections
- **Page flow**: Section opener → Content pages → Data highlights → Photo story → repeat
- **Visual anchors**: Large photographs and big-number cards serve as focal points
