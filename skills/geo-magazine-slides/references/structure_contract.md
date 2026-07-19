# Structure Contract — Geographic Magazine Presentation

## Document Organization

The presentation follows an editorial magazine structure with a **strict slide count of 15 slides**. This count must be maintained unless the user explicitly requests a different length. The narrative flows from collection introduction → regional sections → data analysis → cross-cutting themes → closing.

## Required Slide Sequence (15 Slides)

| # | Slide Type | Purpose | Layout Pattern |
|---|-----------|---------|----------------|
| 1 | **Cover** | Magazine cover with hero image, title, tagline | Split left text / right B&W photo + diagonal bars |
| 2 | **Overview / Index** | Grid of ALL featured items with thumbnail placeholders | 5-column x 4-row grid of dark cards with names + location tags |
| 3 | **Section Divider A** | First geographic region divider | Left text ~40% + red vertical line + right dark image ~60% |
| 4 | **Detail Slide A1** | Featured item deep-dive | Title + red underline + 3-column (image + specs + quote/price) |
| 5 | **Collection Summary A** | Side-by-side comparison within first region | Horizontal bar chart left + 2x2 info cards right + feature bullets |
| 6 | **Section Divider B** | Second geographic region divider | Same layout as Section Divider A |
| 7 | **Detail Slide B1** | Featured item deep-dive from second region | Same layout as Detail Slide A1 |
| 8 | **Collection Summary B** | Side-by-side comparison within second region | 2x3 property cards with dark images + feature bullets |
| 9 | **Market Data / Analysis** | Vertical bar chart with market-wide price comparison | Vertical bar chart + metric callout boxes + dual bottom bars |
| 10 | **Themes — Architecture** | Cross-cutting architect/designer spotlight | Left architect list (red bullets) + right image + skyline card |
| 11 | **Themes — Interiors** | Cross-cutting interior design & amenities | Left finishes + center image grid 2x3 + right amenities + floor plan thumbnails |
| 12 | **Investment / Opportunity** | Sales data, trends, performance metrics | Left metrics with mini charts + right image grid 2x3 + bottom stat bars |
| 13 | **Geographic Breakdown** | Multi-quadrant region spotlight with map | 2x2 neighbourhood cards + large map placeholder with red dots |
| 14 | **Comparison / Floor Plans** | Side-by-side featured options | 4-column floor plan cards with gray placeholders + CTA bar |
| 15 | **Closing** | Summary stats, key metrics, contact info | Left metrics + mini chart + right image/logo + red contact panel |

### Minimum Viable Structure

If content is limited, the absolute minimum slides are:
1. Cover
2. Overview/Index (with all items)
3. At least one Section Divider + one Detail Slide
4. At least one Data/Analysis slide (horizontal OR vertical bar chart)
5. Closing

**However, aim for the full 15-slide structure whenever possible.**

## Section Hierarchy

| Level | Element | Formatting |
|-------|---------|------------|
| H1 | Slide Title | Oranienbaum, ALL CAPS, largest on slide, black |
| H2 | Section Subtitle | Liter, sentence case, dark gray `#333333` |
| H3 | Card/Box Title | Liter, ALL CAPS, bold, black |
| Label | Metadata Tags | Liter, ALL CAPS, 9 pt, red `#D32F2F` (location, price, count) |
| Body | Descriptions | Liter, sentence case, 11–14 pt, dark gray |
| Data | Statistics | Liter, 18–22 pt, red or black depending on emphasis |
| Caption | Image Captions | Liter, ALL CAPS, 9 pt, white on dark bg |

## Exhibit Numbering

- Slides use simple sequential numbering (1, 2, 3... 15)
- Page number displayed in **red square box** (`#D32F2F`), bottom-left corner, white number inside
- Footer text: "{Publication Title} | {PageNumber}" bottom-right, ALL CAPS, 9 pt, dark gray
- Cover slide (slide 1) has page number box but NO footer text

## Cross-Reference Patterns

- Location tags: "| SOUTHBANK", "| MELBOURNE CBD" — red, Liter, 9 pt, ALL CAPS
- Price callouts: "$XXM" or "From $XXXK" — red, Liter, 18–22 pt, bold
- Price ranges in bottom bars: "ULTRA-LUXURY RANGE: $560K — $25M" — white on black
- Category averages: "MELBOURNE CBD AVG: $8,000/SQM | ULTRA-LUXURY: $12,000-$33,000/SQM"

## Content Block Patterns

### Property / Location Detail Block (Slides 4, 7)
```
┌─────────────────────────────────────────────────────────────┐
│ PROPERTY NAME: TAGLINE            ← H1, Oranienbaum, ALL CAPS│
│ ───────                         ← red underline, ~1" wide   │
│                                                                 │
│  ┌──────────┐  KEY SPECIFICATIONS    ┌─────────────────────┐ │
│  │          │  • Spec: Value         │ ARCHITECT + DESIGNER │ │
│  │  [DARK   │  • Spec: Value         │ "Quote text..."      │ │
│  │  IMAGE   │  FEATURES              ├─────────────────────┤ │
│  │  PLACE-  │  • Feature 1           │  [DARK IMAGE]        │ │
│  │  HOLDER] │  • Feature 2           │                      │ │
│  │          │  • Feature 3           │ $PRICE/SQM           │ │
│  │          │                        │ [LABEL]              │ │
│  ├──────────┤  ───────────────────   └─────────────────────┘ │
│  │ PENTHOUSE│  ULTRA-LUXURY RANGE                              │
│  │ $XXM     │  $X.XM — $XXM                                    │
│  └──────────┘                                                 │
│                                                               │
│  ───────────────────────────────────────────────────────────  │
│  ULTRA-LUXURY RANGE: $XXXK — $XXM     ← black bottom info bar│
└─────────────────────────────────────────────────────────────┘
```

### Grid Card Block (Overview Slide 2)
```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│[Dark Img]│ │[Dark Img]│ │[Dark Img]│ │[Dark Img]│ │[Dark Img]│
│#1A1A1A   │ │#222222   │ │#2A2A2A   │ │#333333   │ │#1E1E1E   │
├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤
│ITEM NAME │ │ITEM NAME │ │ITEM NAME │ │ITEM NAME │ │ITEM NAME │
│| LOCATION│ │| LOCATION│ │| LOCATION│ │| LOCATION│ │| LOCATION│
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```
- 20 items total arranged in 4 rows of 5 columns
- Each dark rectangle: ~3.06" wide x 0.97" tall
- Property name: Liter, 11 pt, bold, black, ALL CAPS
- Location tag: Liter, 9 pt, red, "| LOCATION" format

### Horizontal Bar Chart Block (Slide 5)
```
┌─────────────────────────────────────────────────────────────┐
│ CATEGORY COLLECTION: TITLE                                    │
│ ───────                                                     │
│                                                               │
│  ┌──────────────────────┐    ┌─────────────┐ ┌─────────────┐│
│  │ Item A  ████ 3,650   │    │ ITEM A      │ │ ITEM B      ││
│  │ Item B  ██████ 4,924 │    │ $XXM        │ │ $XXM        ││
│  │ Item C  ████████5,550│    │ specs       │ │ specs       ││
│  │ Item D  █████████7,500│   └─────────────┘ └─────────────┘│
│  │ Item E  ████████████9,980│  ┌─────────────┐ ┌─────────────┐│
│  │ Item F  ████████████████17,000  │ ITEM C      │ │ ITEM D      ││
│  └──────────────────────┘    │ $XXM        │ │ From $XK    ││
│  PRICE COMPARISON (A$ 000s)   │ specs       │ │ specs       ││
│                               └─────────────┘ └─────────────┘│
│                               CATEGORY FEATURES               │
│                               • Feature 1    • Feature 4      │
│                               • Feature 2    • Feature 5      │
│                               • Feature 3    • Feature 6      │
│  ───────────────────────────────────────────────────────────  │
│  MELBOURNE AVG: $X/SQM | ULTRA-LUXURY: $XK-$XXK/SQM         │
└─────────────────────────────────────────────────────────────┘
```

### Vertical Bar Chart Block (Slide 9)
```
┌─────────────────────────────────────────────────────────────┐
│ PRICE PER SQUARE METRE:                      MARKET TRENDS:  │
│ MARKET ANALYSIS                              +14% GROWTH ↑   │
│                                              INVESTMENT:     │
│ ───────                                      HIGH DEMAND     │
│                                                               │
│  33,333 █                                                    │
│  28,571 █  █                                                 │
│  26,923 █  █  █                                              │
│       ... (descending bars)                                  │
│                                                               │
│  ItemA ItemB ItemC ItemD ItemE ItemF ...                     │
│                                                               │
│  ─────────────────────────────  ────────────────────────────  │
│  MELBOURNE AVG: $8,000/SQM      ULTRA-LUXURY: $12K-$33K/SQM  │
│  (black bar)                    (red bar)                    │
└─────────────────────────────────────────────────────────────┘
```

### Bottom Info Bar Pattern
```
┌────────────────────────────────────────────────────────────────────┐
│  BLACK BAR: White ALL CAPS text with category stats/ranges         │
└────────────────────────────────────────────────────────────────────┘
```
- Full-width, ~0.4"–0.6" tall, black fill (`#000000`)
- Text: Liter, 11–12 pt, ALL CAPS, white (`#FFFFFF`)
- May appear as single bar or side-by-side black + red bars

## Header / Footer Rules

- **Page number box**: Red square (`#D32F2F`), ~0.4" x 0.4", white number, bottom-left, EVERY slide
- **Footer text**: "{TITLE} | {PAGE}", Liter, 9 pt, ALL CAPS, `#333333`, bottom-right, slides 2–15 only
- **No running header**: Titles are slide-specific, not repeated across slides

## Content Organization by Geographic Region

The reference organizes 20 properties into 2 main geographic sections:

### Section A: CBD & Southbank (8 properties)
- Properties: Australia 108, BLVD Melb Square, R.Iconic, Aspire Residences, Park Quarter, Tintern Toorak, Regatta Collins Wharf, 623 Collins
- Characteristics: Financial & cultural heart, tower residences, city views

### Section B: South Yarra & Bayside (6 properties) + Inner East (4 properties) + others (2)
- South Yarra: South Yarra House
- Bayside: The Muse, Society, One Charles, 448 Brighton, Louise Melbourne
- Inner East: The Regent, Seren Row, Dyason
- Others: Neue Grand, UNO

When adapting to a new topic, organize items into 2–3 geographic or thematic sections of roughly equal size.

## Adaptation Guidelines

When applying this structure to different geographic magazine topics:

| Domain | Item Name | Key Metric | Feature Label | Creator Label |
|--------|-----------|------------|---------------|---------------|
| Real estate / architecture | Property name | Price | Features/Amenities | Architect/Designer |
| Travel / destinations | Location name | Cost/Season | Attractions | Best time to visit |
| Cultural / heritage sites | Site name | Era/Period | Significance | Historical period |
| Natural geography | Landmark name | Elevation/Size | Characteristics | Discovery date |

The core pattern remains: **Cover → Overview (all items) → Section Dividers → Detail Slides → Collection Summaries → Data/Analysis Charts → Cross-cutting Themes → Geographic Breakdown → Comparison → Closing**, with consistent visual treatment of names, locations, metrics, and feature lists.

## Critical Requirements Checklist

Before delivering the presentation, verify:
- [ ] Exactly 15 slides (or minimum 5 if content-constrained)
- [ ] Slide 1: Cover with split layout (left text + right B&W hero + diagonal bars)
- [ ] Slide 2: Overview grid showing ALL items (4x5 or 5x4 grid)
- [ ] Slides 3 & 6: Section dividers with left text + red vertical line + right dark image
- [ ] Slides 4 & 7: Detail slides with title + red underline + 3-column layout
- [ ] Slide 5: Horizontal bar chart with comparison cards
- [ ] Slide 8: Collection summary with property cards
- [ ] Slide 9: Vertical bar chart with dual bottom info bars (black + red)
- [ ] Slide 10: Architectural Excellence with architect list + red bullets
- [ ] Slide 11: Interior Design & Amenities with image grid + floor plan thumbnails
- [ ] Slide 12: Investment/Opportunity with mini bar charts + stat bars
- [ ] Slide 13: Neighbourhood Spotlights with 2x2 cards + map placeholder
- [ ] Slide 14: Featured Floor Plans with 4-column comparison cards
- [ ] Slide 15: Closing with metrics + contact panel + diagonal bars
- [ ] Every slide has red page-number box bottom-left
- [ ] Every slide (except cover) has footer text bottom-right
- [ ] All image placeholders are dark near-black rectangles (no external image downloads)
- [ ] All bar charts use solid black fill
- [ ] Red accent color `#D32F2F` used consistently for emphasis
