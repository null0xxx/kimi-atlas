# Style Contract — Geographic Magazine Presentation

## Reference Source

- **Type**: Uploaded artifact (PPTX)
- **Artifact**: "Melbourne's Ultra-Luxury Condos.pptx" — 15-slide luxury real estate showcase
- **Design language**: High-end editorial / geographic magazine aesthetic
- **Fonts extracted from reference**: Oranienbaum (serif headings), Liter (sans-serif body)

## Color Palette (Exact Hex from Reference)

| Role | Hex | Usage |
|------|-----|-------|
| Primary Accent | `#D32F2F` | Red — bullet dots, separator lines, page number boxes, price highlights, tagline text, CTA buttons, bottom accent bars |
| Text Primary | `#000000` | Black — main headings, chart bars, bottom info bars, shape fills |
| Text Secondary | `#333333` | Dark gray — body text, captions, subtitle descriptions |
| Background Base | `#CCCCCC` / `#D3D3D3` | Light warm gray — slide canvas background |
| Background Panel | `#D9D9D9` / `#E0E0E0` | Slightly lighter gray — left text panels on cover/closing |
| Image Placeholder | `#1A1A1A` – `#353535` | Near-black dark grays — photo placeholder rectangles (vary shades across grid for visual interest) |
| Inverse Text | `#FFFFFF` | White — text on black/red bars, inside red page-number boxes, caption text on dark images |
| Card Background | `#FFFFFF` | White — info cards, feature boxes, floor plan cards |

## Typography System

### Font Families (Exact from Reference)

| Role | Font | Fallback Strategy |
|------|------|-------------------|
| Headings | Oranienbaum | High-contrast elegant serif. Fallback: Cormorant Garamond, Playfair Display, or Noto Serif SC for CJK |
| Body / Labels | Liter | Clean humanist sans-serif. Fallback: Lato, Open Sans, or Noto Sans SC for CJK |

### Type Scale (Exact Sizes from Reference)

| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| Cover Title | 52 pt | Regular | All-caps, largest on slide, Oranienbaum |
| Section Title | 38–48 pt | Regular | All-caps, slide-level headings, Oranienbaum |
| Slide Title | 32–36 pt | Regular | All-caps, property/location names, Oranienbaum |
| Subtitle | 14–16 pt | Regular | Sentence case, descriptive taglines, Liter |
| Body Text | 11–14 pt | Regular | Specifications, descriptions, Liter |
| Caption / Label | 9–10 pt | Regular / Bold | Image captions, footer, metadata, ALL CAPS, Liter |
| Data Highlight | 18–22 pt | Regular / Bold | Price figures, key statistics, Liter |
| Card Title | 14–16 pt | Bold | Item names in cards, Liter |

### Typography Rules

- Headings: **ALL CAPS**, Oranienbaum, black (`#000000`)
- Subtitles / taglines: Sentence case, Liter, dark gray (`#333333`)
- Tagline accent: Red (`#D32F2F`), Liter, ALL CAPS — used on cover and section dividers
- Emphasis text (prices, locations): Red (`#D32F2F`), Liter
- Labels and metadata: ALL CAPS, Liter, 9–10 pt
- Footer text: ALL CAPS, Liter, 9 pt, dark gray
- Image captions: ALL CAPS, Liter, 9 pt, white on dark backgrounds
- Red underline decoration: Short horizontal rule (~1 inch wide, 4–6 px tall, `#D32F2F`) beneath main slide titles

## Layout System

### Slide Dimensions
- Aspect ratio: **16:9**
- Size: 10" height x 17.78" width (1280 x 720 pt equivalent)

### Margins & Spacing
- Page margins: ~0.5" from left/right edges, ~0.4" from top
- Content safe zone: Keep text/shapes within 0.5" of all edges
- Card gaps in grids: ~0.3"–0.4" between cards

### Mandatory Elements on EVERY Slide

1. **Red page-number box**: Bottom-left corner
   - Square shape, ~0.4" x 0.4", red fill (`#D32F2F`)
   - White number text inside, centered, ~12 pt
   - Position: ~0.3" from left edge, ~0.3" from bottom

2. **Footer text**: Bottom-right corner (slides 2–15)
   - Format: "{PUBLICATION TITLE} | {PAGE NUMBER}"
   - Liter, 9 pt, ALL CAPS, dark gray (`#333333`)
   - Position: ~0.3" from right edge, ~0.3" from bottom
   - Slide 1 (cover) does NOT have footer text

## Focal Decorative Elements

- **Red vertical separator line**: ~4–6 px wide, full-height or tall, `#D32F2F`, between left text panel and right image panel on section dividers
- **Red horizontal rule**: ~1" wide, 4–6 px tall, `#D32F2F`, beneath slide titles on detail/data slides
- **Red dot bullets**: Filled red circle (`#D32F2F`) preceding feature list items
- **Black diagonal accent bar**: Thick black diagonal strip (~1" wide, ~45° angle) crossing photo area on cover/closing
- **Red diagonal accent bar**: Thinner red diagonal strip, parallel to black one, on cover/closing
- **Red left-edge accent**: Thin red vertical bar on left edge of cover text panel (~0.1" wide, ~4" tall)
- **Bottom info bar**: Full-width black bar (`#000000`) at slide bottom, white ALL CAPS text inside
- **Bottom accent bar pair**: Side-by-side black + red bars at bottom (e.g., page 9)

## Visual Treatment of Images

- **Hero photos**: Large, spanning partial or full slide height
- **Image placeholders**: Dark rectangles (`#1A1A1A`–`#353535`) where photos will be inserted — NEVER attempt to download external images, always use dark placeholder rectangles
- **Placeholder color variation**: Use varying shades of near-black across grid items for visual interest (e.g., #1A1A1A, #222222, #252525, #282828, #2A2A2A, #2D2D2D, #303030, #333333, #353535)
- **Photo treatment**: Full-bleed or panel-based; never small thumbnails except in overview grid
- **Captions below images**: ALL CAPS, Liter, 9 pt, white (`#FFFFFF`) on dark backgrounds
- **B&W photography**: Cover hero image uses black-and-white treatment for editorial effect

## Chart & Data Visualization Style

### Bar Charts (CRITICAL — must include at least 2 chart slides)
- Bar fill: **Solid black** (`#000000`), no gradients, no patterns
- Chart background: Transparent (showing slide gray background)
- Data labels: White or black text directly on/above bars
- Grid lines: Light gray (`#CCCCCC`), horizontal only
- Axis labels: Liter, dark gray, 10 pt
- Chart titles: ALL CAPS, Oranienbaum

### Horizontal Bar Chart (e.g., CBD Collection price comparison)
- Y-axis: Item names (Liter, 10 pt)
- X-axis: Numeric values
- Bars extend rightward from Y-axis labels
- Data values labeled at bar ends

### Vertical Bar Chart (e.g., Price Per Square Metre market analysis)
- X-axis: Item names (Liter, 9–10 pt, angled if needed)
- Y-axis: Numeric values
- Bars extend upward
- Data values labeled at top of each bar

### Metric Callout Boxes
- White or black bordered rectangles
- Label: ALL CAPS, small, Liter
- Value: Large, bold, red (`#D32F2F`) or black
- Used for price highlights, growth percentages

## Slide-Specific Layout Patterns

### Cover Slide (Slide 1)
- Left ~45% (0"–8" from left): Light-gray panel
  - Thin red vertical accent bar at left edge (~0.1" wide, ~4" tall, positioned at y~2.5")
  - Title: Oranienbaum, 52 pt, ALL CAPS, black, positioned at y~2.5"
  - Tagline: Liter, 16 pt, ALL CAPS, red (`#D32F2F`), positioned below title at y~5.8"
- Right ~55% (8"–17.78" from left): Full-height hero photograph (B&W skyline)
  - Black diagonal accent bar crossing lower portion (~6.7" from left, ~7.2" from top, ~1" wide)
  - Red diagonal accent bar parallel to black one (~8.3" from left, ~8.1" from top, ~0.6" wide)
- White rectangle at bottom-right corner (~15.3" from left, ~8.6" from top, ~1.9" x 1.1")
- NO footer text on cover

### Overview / Index Slide (Slide 2)
- Title at top-left: Oranienbaum, 38 pt, ALL CAPS, black
- Subtitle below: Liter, 14 pt, sentence case, dark gray
- 5-column x 4-row grid of property cards below title area
- Each card consists of:
  - Dark placeholder rectangle: ~3.06" wide x 0.97" tall
  - Property name below: Liter, 11 pt, bold, black, ALL CAPS
  - Location tag below name: Liter, 9 pt, red (`#D32F2F`), "| LOCATION" format
- Grid starts at ~0.56" from left, ~2.4" from top
- Column gap: ~0.3" (shapes start at 0.56", 3.82", 7.08", 10.35", 13.61")
- Row gap: ~0.7" (rows start at ~2.4", ~4.1", ~5.8", ~7.4" from top)
- Red page-number box bottom-left
- Footer: "MELBOURNE'S ULTRA-LUXURY CONDOS | 2" bottom-right

### Section Divider Slide
- Left ~40% (0"–7.2" from left): Text panel
  - Section title: Oranienbaum, 38–48 pt, ALL CAPS, black
  - Subtitle: Liter, 14 pt, sentence case, dark gray
  - Item count: Liter, 14 pt, sentence case, dark gray
  - Red bullet + tagline: Red dot + Liter, 14 pt, red (`#D32F2F`), sentence case
- Red vertical separator line at ~40% mark, full height (~0.1" wide)
- Right ~60%: Large dark image placeholder rectangle
  - Caption at bottom inside placeholder: ALL CAPS, white, 9 pt
- Red page-number box bottom-left
- Footer text bottom-right

### Detail / Feature Slide
- Top-left: Slide title (Oranienbaum, 32–36 pt, ALL CAPS, black)
- Red underline decoration: ~1" wide, 4 px tall, `#D32F2F`, directly below title
- Multi-column layout below title:
  - Left column (~35%): Large dark image placeholder + price box below (red or black filled rectangle with white price text)
  - Center column (~30%): Key Specifications heading (Liter, bold, ALL CAPS) + spec list + Features heading + red dot bullet list
  - Right column (~35%): Quote/architect box (white card with border) + secondary image placeholder + price/sqm callout (large red text)
- Bottom info bar: Full-width black bar, white ALL CAPS text with price range
- Red page-number box bottom-left
- Footer text bottom-right

### Data / Chart Slide (Horizontal Bar Chart)
- Title at top-left with red underline
- Left ~50%: Horizontal bar chart (black bars, item names on Y-axis, values at bar ends)
- Right ~50%: 2x2 grid of info cards (white rectangles with black border)
  - Each card: Property name (bold), price (red, large), brief specs
- Below cards: Feature heading + red dot bullet list (2 columns)
- Bottom info bar: Full-width black bar with market data
- Red page-number box bottom-left
- Footer text bottom-right

### Data / Chart Slide (Vertical Bar Chart)
- Title at top-left: Oranienbaum, 36 pt, ALL CAPS
- Top-right: Two metric callout boxes side by side
  - "MARKET TRENDS: +X% GROWTH" — label black, value red
  - "INVESTMENT: HIGH DEMAND" — label black, value red
- Central area: Vertical bar chart (black bars, X-axis=item names, Y-axis=values)
- Bottom: Side-by-side info bars
  - Left bar: Black, "MELBOURNE AVG: $X/SQM"
  - Right bar: Red (`#D32F2F`), "ULTRA-LUXURY RANGE: $X — $X/SQM"
- Red page-number box bottom-left
- Footer text bottom-right

### Collection Summary Slide (e.g., Bayside Collection)
- Title at top-left with red underline
- 2x3 grid of property cards, each card:
  - Left portion: Dark image placeholder (~2.5" wide)
  - Right portion: White info area with property name (bold, ALL CAPS), price (red, large), specs
- Right side: Feature heading + 2-column red dot bullet list
- Bottom info bar: Full-width black bar
- Red page-number box bottom-left
- Footer text bottom-right

### Architectural Excellence Slide
- Title at top-left with red underline
- Left ~45%: Red dot bullet list of architect names (Liter, 16–18 pt, red)
- Bottom-left: Red info bar with price range
- Right ~55%: Large dark image placeholder + caption below
- Below image: White card with "SKYLINE CONTRIBUTION" heading + 2-column arrow-bullet list
- Red page-number box bottom-left
- Footer text bottom-right

### Interior Design & Amenities Slide
- Title at top-left with red underline
- Left column: "LUXURY FINISHES" heading + red dot bullet list
- Center: 2x3 grid of dark image placeholders with captions below each (LIVING ROOM, BATHROOM, INFINITY POOL, KITCHEN, GYM, DINING ROOM)
- Between image rows: Price labels (red box "$X/SQM" and black box "$X/SQM")
- Right column: "WORLD-CLASS AMENITIES" heading + red dot bullet list
- Bottom: "AMENITY MAP" black button + 5 floor plan thumbnail boxes with red dots
- Red page-number box bottom-left
- Footer text bottom-right

### Investment / Market Performance Slide
- Title at top-left with red underline
- Left ~35%: "2025 SALES DATA & TRENDS" heading + descriptive paragraph + 3 mini bar charts (black bars, 4 bars each) with red labels
- Right ~65%: 2x3 grid of dark image placeholders
- Below images: 3 bottom info bars side by side (black, red, black)
- Red page-number box bottom-left
- Footer text bottom-right

### Neighbourhood Spotlights Slide
- Title at top-left with red underline
- 2x2 grid of white neighbourhood cards:
  - Each card: Black left border (4–6 px), neighbourhood name (bold, ALL CAPS), project count (red), price range (red), descriptive paragraph
- Below cards: Large dark rectangle map placeholder with red location dots + caption "MELBOURNE LUXURY APARTMENT LOCATIONS"
- Red page-number box bottom-left
- Footer text bottom-right

### Featured Floor Plans Slide
- Title at top-left with red underline
- 4-column grid of floor plan cards:
  - Each card: White background, gray floor plan placeholder rectangle at top, property name (bold), unit type (red), price (red, large), description text
- Bottom info bar: Full-width black bar with CTA text
- Red page-number box bottom-left
- Footer text bottom-right

### Closing Slide
- Left ~55%: Title (Oranienbaum, 44 pt, ALL CAPS) + paragraph + key metrics
  - Large red price figure "$X,XXX" + label
  - Mini bar chart (black bar showing MIN–MAX range)
  - "TOP 1% MARKET TRENDS" label with red dot + "INVESTMENT POTENTIAL: HIGH DEMAND" in red
  - Bottom: "{TITLE} | {EDITION}" small text
- Right ~45%:
  - Top: Large dark image placeholder
  - Middle: Logo area (white on gray)
  - Bottom: Red contact panel with white text (phone, email, "CONTACT FOR PRIVATE VIEWINGS:")
- Black diagonal accent bar crossing upper-right image area
- Red page-number box bottom-left (numbered 15)
