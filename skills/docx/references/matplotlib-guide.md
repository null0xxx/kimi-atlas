# Matplotlib Guide

Charts are inserted as 300dpi PNG into professional documents. The difference between SOTA and AI slop is not technical skill — it's whether the chart has a point of view.

## What Makes a Chart Professional

**The chart argues, not just displays.** Every design choice — what's thick, what's faint, what's labeled, what's omitted — reflects an analytical judgment about what matters.

Three principles:

1. **Title = the analyst's conclusion.** "TMT valuations pale vs Tech Bubble" not "TMT Forward P/E 1980-2025". The title is the takeaway; the chart is the evidence.

2. **Visual weight = information weight.** The primary data series is thick and dark. Secondary/reference series are thin and faint. Annotations only on the 3-5 points that support the title's argument. Everything else recedes.

3. **The chart belongs to the document.** Colors, fonts, and density match the Word document's design system. A chart that looks "imported from somewhere else" breaks the reader's trust.

## Anti-Slop Checklist

- [ ] Title states a conclusion
- [ ] ≤3 colors with clear hierarchy (not rainbow)
- [ ] No exploded pie, no 3D, no legend box
- [ ] Annotations directly on data, selective (3-5 max)
- [ ] White bg, L-shaped frame (left+bottom only), near-invisible horizontal grid
- [ ] Source + date bottom-right
- [ ] Font matches document
- [ ] `dpi=300, bbox_inches='tight', transparent=True`
- [ ] `fig.patch.set_alpha(0)` + `ax.patch.set_alpha(0)` — no white rectangle on document backgrounds

## Font & Color: Inherit From the Document

```python
# Match the document's font and color system
# Creation route: match the design brief
# Editing route: extract from the document's existing styles
FONT_EN = 'Calibri'    # or whatever the document uses
FONT_CJK = 'SimSun'    # match document CJK font
plt.rcParams['font.sans-serif'] = [FONT_EN, FONT_CJK, 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
```

Colors: pick from the document's palette. No fixed chart palette — the chart is part of the document's visual system. Fallback if no palette defined: `['#5D6D7E', '#7D8F69', '#A67C52', '#8B7D9C', '#6B8E8E']`

## Chart Type Selection

Ask "what's the analytical point?" first, then pick the chart type:
- Comparison → grouped bar / clustered column
- Composition → pie / donut / stacked bar
- Trend over time → line / area
- Ranking → horizontal bar (sorted)
- Distribution → histogram / box plot
- Relationship → scatter

The chart style serves the content — not the other way around. Different data stories need different visual treatments.

## Techniques the Model Doesn't Know Well

### L-frame: remove top/right spines, fade axis lines
```python
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
ax.spines['left'].set_color('#cccccc')
ax.spines['bottom'].set_color('#cccccc')
ax.yaxis.grid(True, alpha=0.12, linestyle='--', color='#aaaaaa')
ax.tick_params(colors='#666666', labelsize=9)
```

### Direct value labels on bars (replaces legend for simple charts)
```python
for bar in bars:
    val = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, val + offset,
            f'{val:,.0f}', ha='center', va='bottom', fontsize=8, color='#555')
```

### Label collision avoidance
```python
# Strategy 1: alternate above/below for grouped bars
offsets = [+12, -18]  # points
for i, bar in enumerate(bars):
    ax.annotate(label, xy=(...), xytext=(0, offsets[i % 2]), textcoords='offset points', ...)

# Strategy 2: adjustText library (pip install adjustText)
from adjustText import adjust_text
texts = [ax.text(x, y, label) for x, y, label in data]
adjust_text(texts)
```

### Annotate with coordinate transforms (arrow + offset)
```python
ax.annotate('52x', xy=(2000, 52), xytext=(15, 10),
    textcoords='offset points', fontsize=9, fontweight='bold',
    arrowprops=dict(arrowstyle='->', color='#333', lw=0.8))
```

### Heatmap table without imshow (cell-level control)
```python
from matplotlib.colors import LinearSegmentedColormap, Normalize
cmap = LinearSegmentedColormap.from_list('div', ['#C75B5B', '#FFF', '#5B8C6B'])
norm = Normalize(vmin=-10, vmax=10)
for i, row in enumerate(matrix):
    for j, val in enumerate(row):
        ax.add_patch(plt.Rectangle((j, nrows-1-i), 1, 1,
            facecolor=cmap(norm(val)), edgecolor='white', lw=1))
        ax.text(j+0.5, nrows-0.5-i, f'{val:+.1f}%', ha='center', va='center', fontsize=8)
```

### Broken axis / value truncation
```python
ax.set_ylim(0, 55)
# Bar exceeds axis — clip and annotate real value
ax.annotate('82%\n~', xy=(bar_x, 54), fontsize=8, ha='center')
```

### Custom tick suffixes
```python
from matplotlib.ticker import FuncFormatter
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}x'))
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
```

### Dual Y-axis overlay (bars + scatter)
```python
ax2 = ax.twinx()
ax.bar(x, vals, color=primary)
ax2.scatter(x, totals, color=accent, zorder=5, s=30)
```

### CJK font fallback (must be before any plotting)
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = [FONT_EN, FONT_CJK, 'Arial Unicode MS', 'DejaVu Sans']
```

---

## Reference Entry Points

- For overall routing: `../SKILL.md`
- For creating new documents: `openxml-sdk-reference.md`
- For editing existing documents: `wir-reference.md`
