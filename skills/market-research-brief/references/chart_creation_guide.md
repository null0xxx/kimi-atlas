# Chart Creation Guide — Market Insight Report

## Mandate: Charts Must Be Rendered as Embedded Images

**Every exhibit that visualizes data must contain an actual rendered chart image, not a text description, placeholder, or table-only substitute.** Charts are the primary visual evidence for the report's arguments. Reports with only tables and no chart images fail the quality bar.

When generating output (PDF/DOCX), use matplotlib, plotly, or equivalent charting libraries to render chart images and embed them inline. Tables supplement charts — they do not replace them.

## Exhibit-to-Chart Mapping

Use this mapping to determine which exhibit types require chart images vs. tables:

| Analysis Section | Exhibit Type | Chart Needed | Recommended Chart Kind |
|-----------------|-------------|-------------|----------------------|
| Market sizing / TAM | Market size trend | **Yes** | Bar chart + growth rate line (dual-axis) |
| Market sizing / cross-validation | Comparison table | No — table only | — |
| Growth decomposition | Driver comparison | **Yes** | Grouped bar chart or waterfall |
| Time-series trends (users, time spent) | Trend line | **Yes** | Line chart with annotations |
| Category / segment share | Share breakdown | **Yes** | Pie/donut chart or stacked 100% bar |
| Channel share evolution | Share over time | **Yes** | Stacked 100% bar chart with CAGR side table |
| Channel migration | Migration matrix | No — table only | — |
| Channel efficiency | Efficiency comparison | **Yes** | Grouped bar chart |
| Consumer segmentation | Segment comparison | **Yes** | Radar/spider chart or grouped bar |
| Consumer need-state | Quadrant mapping | **Yes** | 4-quadrant scatter plot |
| Competitive landscape | Market share | **Yes** | Pie/donut chart or horizontal bar |
| Competitive attribution | Share bridge | **Yes** | Waterfall/bridge chart |
| Platform ranking | App MAU ranking | **Yes** | Horizontal bar chart |
| Forecast / projections | Projection trend | **Yes** | Line chart with forecast demarcation |
| Detailed financials | Data table | No — table only | — |

**Rule of thumb**: If the data has a visual story (trends, comparisons, distributions), use a chart. If the data is reference/lookup (detailed numbers, multi-column comparisons), use a table. Most sections should have **at least one chart image**.

## Color Palette for Charts

All charts must use this palette, derived from the report's consulting style:

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Primary accent | Deep red | `#CC0000` | Most recent data, key series, highlighted category |
| Secondary | Dark gray | `#666666` | Secondary data series, prior period |
| Tertiary | Medium gray | `#999999` | Older data, background series |
| Positive | Teal green | `#2E8B8B` | Positive variance, growth |
| Negative | Coral red | `#E74C3C` | Negative variance, decline |
| Background | Light gray | `#F5F5F5` | Chart background fill |
| Gridlines | Light gray | `#CCCCCC` | Horizontal gridlines only |
| Multi-series rotation | — | `#CC0000`, `#666666`, `#2E8B8B`, `#E8913A`, `#4A90D9`, `#999999` | For charts with 3+ data series |

**Critical**: Deep red (`#CC0000`) is always the PRIMARY chart color (most important series). Never use bright rainbow palettes.

## Chart Type Specifications

### 1. Bar Chart + Growth Line (Dual-Axis)

**Use for**: Market size trends, revenue trends, user growth over time

**Layout**:
- Bars on primary Y-axis (left): absolute values (revenue, users)
- Line on secondary Y-axis (right): growth rate (%)
- X-axis: time periods (years or quarters)

**Rendering spec**:
- Bar fill: Deep red (`#CC0000`) solid, width ~0.6
- Line: Dark gray (`#666666`), 2px solid, circle markers
- Background: white, no border
- Horizontal gridlines only, light gray (`#CCCCCC`), 0.5px
- No vertical gridlines
- Data labels above bars (value) and on line points (%)
- Y-axis labels with units ("亿元", "%")
- Legend: top-right or top-center, inside chart area

**Aspect ratio**: 16:9 (~width 14cm, height 8cm)

### 2. Pie / Donut Chart

**Use for**: Market share, revenue mix, channel split, user composition

**Layout**:
- Donut preferred over pie (inner radius ~55% of outer)
- Maximum 6 segments; group smaller segments into "其他"
- Largest segment starts at 12 o'clock, clockwise descending

**Rendering spec**:
- Primary segment: Deep red (`#CC0000`)
- Other segments: rotate through `#666666`, `#2E8B8B`, `#E8913A`, `#4A90D9`, `#999999`
- White separator lines between segments (1px)
- Percentage labels inside or outside segments (bold, 10pt)
- Category labels outside with leader lines, or in legend below
- No 3D effects, no drop shadows

### 3. Stacked 100% Bar Chart with CAGR Side Table

**Use for**: Channel share evolution, category share over time, revenue mix trends

**Layout**:
- Stacked bars at 100% height, one bar per year/quarter
- X-axis: time periods
- Y-axis: 0%–100%
- Side table (right): CAGR for each segment across the time range

**Rendering spec**:
- Segments use the multi-series color rotation
- Percentage labels inside each segment (white text if on dark fill, black if on light)
- CAGR side table: small, aligned with bar chart, plain text with bold values
- Thin horizontal gridlines at 25%, 50%, 75%

### 4. Waterfall / Bridge Chart

**Use for**: Market share change attribution, revenue bridge, growth decomposition

**Layout**:
- Horizontal bars centered at zero
- Green (#2E8B8B) for positive contributions (gains)
- Red (#E74C3C) for negative contributions (losses)
- Dark gray for total/starting/ending bars
- Connecting lines between bars (thin gray dashed)

**Rendering spec**:
- Category labels on Y-axis (left-aligned)
- Value labels at end of each bar
- Zero line: solid dark gray, 1px
- Starting bar (left): "起始份额" or "Starting Share"
- Ending bar (right): "最终份额" or "Ending Share"

### 5. Multi-Panel Mini-Charts (2×2 Grid)

**Use for**: Category comparisons, segment breakdowns, regional comparison

**Layout**:
- 2 columns × 2 rows = 4 small charts in one exhibit
- Each panel: its own title, same chart type, shared Y-axis scale
- Small gap between panels (3-5mm)

**Rendering spec**:
- Each panel ~7cm × 5cm
- Shared Y-axis range across all 4 panels for comparability
- Panel title: bold, 9pt, above each mini-chart
- Simplified axes: fewer tick labels, no redundant axis titles
- Deep red for standout values, gray for others

### 6. Annotated Line Chart

**Use for**: Time-series trends with event markers (policy changes, product launches, market events)

**Layout**:
- Line chart with 1-4 data series over time
- Vertical annotation bars or arrows marking key events
- Event labels in small text boxes

**Rendering spec**:
- Primary series: Deep red (`#CC0000`), 2px solid
- Secondary series: `#666666`, 1.5px solid
- Event annotations: vertical gray dashed line + text label (8pt) in rounded box
- Forecast demarcation: vertical dashed line + "预测" label with right-pointing arrow
- Legend: inside top area of chart

### 7. Horizontal Bar Chart (Ranking)

**Use for**: App rankings, platform comparisons, factor importance ranking

**Layout**:
- Horizontal bars, sorted by value (largest at top)
- Category labels on Y-axis
- Value labels at end of each bar

**Rendering spec**:
- Bar fill: Deep red (`#CC0000`) for top item, gradient to gray for lower items
- OR: all bars in deep red, with the key comparison item highlighted
- Value labels: bold, right of bar end
- No vertical gridlines; optional light horizontal gridlines

### 8. Radar / Spider Chart

**Use for**: Multi-dimensional competitive comparison, brand competitiveness assessment

**Layout**:
- 5-6 axes radiating from center
- 2-4 overlapping polygons (one per competitor/segment)
- Scale: 0 at center, max at outer edge

**Rendering spec**:
- Each competitor uses a different color from the palette
- Fill: semi-transparent (alpha ~0.15)
- Lines: solid, 2px
- Axis labels: 9pt, at outer edge of each spoke
- Grid: concentric pentagons/hexagons, light gray (#CCCCCC)
- Legend: below chart

### 9. 4-Quadrant Scatter Plot

**Use for**: Category positioning, market opportunity mapping, need-state analysis

**Layout**:
- X-axis and Y-axis representing different metrics
- Quadrant dividers: dashed lines at axis medians
- Each dot labeled with category/brand name
- Dot size may encode a third variable (e.g., market size)

**Rendering spec**:
- Dots: colored by group (use multi-series palette)
- Labels: 8pt, positioned to avoid overlap
- Quadrant labels: bold, 10pt, in each corner
- Axis titles with units
- Background: white, quadrant backgrounds may have very subtle tinting

## Chart Title & Source Block

Every chart must have:

```
图 N：[Descriptive assertion title — what the chart shows, not just the data]
                    ← chart image →
资料来源：[Data Source]；[Firm Name]分析
```

- "图 N" in **deep red**, bold, 10pt
- Description in **black**, bold, 10pt
- Source line: gray, italic, 8pt, below chart
- Optional note line: between chart and source, gray, 8pt

**Title writing rule**: Chart titles should be **assertions**, not descriptions.
- Good: "图3：短视频占据用户时长38.4%，抖音一家占半壁江山"
- Bad: "图3：用户时长分布"

## Chart Density Rule

- **Minimum**: 1 chart per 2 content pages
- **Ideal**: 1-2 charts per content page
- **Maximum**: 3 charts per page (only in appendix/comparison sections)
- **Executive summary**: NO charts — text only
- If a section has 3+ paragraphs of analysis without a chart, add one

## Output Technical Requirements

- **Resolution**: Minimum 150 DPI, recommended 200 DPI
- **Format**: PNG (for consistent rendering across PDF/DOCX)
- **Embedding**: Charts must be embedded as inline images in the document flow, immediately after their first text reference
- **Size**: Standard chart ~14cm wide × 8cm tall; dual-panel ~14cm × 6cm per panel; mini-charts ~7cm × 5cm per panel
- **Font in charts**: Use system sans-serif (PingFang SC, Noto Sans SC, Arial) matching the report body font
- **Anti-aliasing**: Enabled for smooth line rendering
