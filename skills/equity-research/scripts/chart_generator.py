#!/usr/bin/env python3
"""
Equity Report Chart Generator
==============================
Generates publication-quality SVG charts for equity research reports.
Used ONLY by the equity report workflow (not tear sheets).

Usage:
    python chart_generator.py --chart_type revenue_segment --data '{...}' --output chart.svg --json
    python chart_generator.py --chart_type margin_trends --data '{...}' --output chart.svg
    python chart_generator.py --chart_type market_share --data '{...}' --output chart.svg
    python chart_generator.py --chart_type pe_band --data '{...}' --output chart.svg
    python chart_generator.py --chart_type pe_band_simple --data '{...}' --output chart.svg
    python chart_generator.py --chart_type scenario_comparison --data '{...}' --output chart.svg

Options:
    --chart_type    One of: revenue_segment, margin_trends, market_share, pe_band, pe_band_simple, scenario_comparison
    --data          JSON string with chart data (structure depends on chart_type)
    --output        Output SVG file path (default: chart.svg)
    --currency      Currency symbol for labels (default: $)
    --unit          Unit suffix for large numbers: B=billions, M=millions (default: B)
    --json          If set, print JSON metadata to stdout after generation
"""

import argparse
import json
import sys
import os
import base64
import io

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend — no display needed
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.patches as mpatches
    import numpy as np
except ImportError:
    print("ERROR: matplotlib and numpy are required. Install with:")
    print("  pip install matplotlib numpy --break-system-packages")
    sys.exit(1)


# ============================================================
# Global Style
# ============================================================

COLORS = {
    'primary':    '#003366',
    'secondary':  '#0D7377',
    'tertiary':   '#D4A843',
    'quaternary': '#6B7B8D',
    'quinary':    '#C75B3F',
    'senary':     '#7BA05B',
    'bull':       '#2E7D32',
    'bear':       '#C62828',
    'base':       '#1565C0',
    'grid':       '#E8E8E8',
    'text':       '#333333',
}

PALETTE = [
    COLORS['primary'],
    COLORS['secondary'],
    COLORS['tertiary'],
    COLORS['quaternary'],
    COLORS['quinary'],
    COLORS['senary'],
]

CHART_STYLE = {
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'font.family': 'sans-serif',
    # Cross-platform font stack with CJK coverage first.
    # Why: Chinese labels (e.g. 营业收入, 毛利率) must render on Linux/Windows
    # boxes that lack PingFang/YaHei; without these fallbacks they turn into
    # tofu squares (□□□) — a fatal visual bug for A-share / HK reports.
    'font.sans-serif': [
        'Source Han Sans SC',    # Adobe open-source, cross-platform first choice
        'Noto Sans CJK SC',      # Google open-source (common on Linux)
        'PingFang SC',           # macOS built-in
        'Microsoft YaHei',       # Windows built-in
        'WenQuanYi Zen Hei',     # Linux community fallback
        'Heiti SC', 'SimHei',    # Older macOS/Windows CJK
        'Helvetica Neue', 'Arial', 'DejaVu Sans',
    ],
    'axes.unicode_minus': False,  # keep minus sign correct under CJK fonts
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.color': COLORS['grid'],
    'text.color': COLORS['text'],
    'axes.labelcolor': COLORS['text'],
    'xtick.color': COLORS['text'],
    'ytick.color': COLORS['text'],
}


def apply_style():
    """Apply global chart style settings."""
    plt.rcParams.update(CHART_STYLE)


def save_svg(fig, output_path):
    """Save figure as SVG and return base64-encoded string."""
    fig.savefig(output_path, format='svg', bbox_inches='tight', pad_inches=0.15)

    # Also generate base64 for embedding
    buf = io.BytesIO()
    fig.savefig(buf, format='svg', bbox_inches='tight', pad_inches=0.15)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return b64


def is_forecast(year_label):
    """Check if a year label represents a forecast (contains 'E' or 'e')."""
    return 'E' in str(year_label) or 'e' in str(year_label)


# ============================================================
# C1: Revenue by Segment (Stacked Bar)
# ============================================================

def chart_revenue_segment(data, currency='$', unit='B'):
    """
    Stacked bar chart showing revenue by business segment over time.

    data = {
        "years": ["FY2022", "FY2023", ...],
        "segments": {
            "Segment A": [val1, val2, ...],
            "Segment B": [val1, val2, ...],
        }
    }
    """
    apply_style()

    years = data['years']
    segments = data['segments']
    n_years = len(years)
    x = np.arange(n_years)

    fig, ax = plt.subplots(figsize=(9, 5))

    # Stack bars
    bottom = np.zeros(n_years)
    bars_list = []
    seg_names = list(segments.keys())

    for i, (seg_name, values) in enumerate(segments.items()):
        values = np.array(values, dtype=float)
        color = PALETTE[i % len(PALETTE)]

        bars = ax.bar(x, values, bottom=bottom, label=seg_name, color=color,
                       width=0.6, edgecolor='white', linewidth=0.5)

        # Add hatching for forecast years
        for j, bar in enumerate(bars):
            if is_forecast(years[j]):
                bar.set_hatch('///')
                bar.set_edgecolor(color)
                bar.set_alpha(0.85)

        bars_list.append(bars)
        bottom += values

    # Total labels on top
    totals = bottom
    for j, total in enumerate(totals):
        ax.text(j, total + total * 0.01, f'{currency}{total:.0f}{unit}',
                ha='center', va='bottom', fontsize=8, fontweight='bold',
                color=COLORS['text'])

    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_ylabel(f'Revenue ({currency}{unit})')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, p: f'{currency}{v:.0f}{unit}'))

    # Legend below chart
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1),
              ncol=min(len(seg_names), 4), frameon=False)

    ax.set_ylim(0, max(totals) * 1.12)

    return fig


# ============================================================
# C2: Margin Trends (Multi-Line)
# ============================================================

def chart_margin_trends(data, **kwargs):
    """
    Multi-line chart tracking gross, operating, and net margins over time.

    data = {
        "years": ["FY2022", "FY2023", ...],
        "gross_margin": [43.3, 44.1, ...],
        "operating_margin": [30.3, 29.8, ...],
        "net_margin": [25.3, 25.0, ...]
    }
    """
    apply_style()

    years = data['years']
    n = len(years)
    x = np.arange(n)

    margins = {
        'Gross Margin': (data.get('gross_margin', []), COLORS['primary'], 'o'),
        'Operating Margin': (data.get('operating_margin', []), COLORS['secondary'], 's'),
        'Net Margin': (data.get('net_margin', []), COLORS['tertiary'], '^'),
    }

    fig, ax = plt.subplots(figsize=(9, 5))

    # Find where forecast starts
    forecast_start = None
    for i, yr in enumerate(years):
        if is_forecast(yr):
            forecast_start = i
            break

    for label, (values, color, marker) in margins.items():
        if not values:
            continue
        values = np.array(values, dtype=float)

        if forecast_start is not None and forecast_start > 0:
            # Solid line for actuals
            ax.plot(x[:forecast_start], values[:forecast_start],
                    color=color, marker=marker, markersize=6,
                    linewidth=2, label=label, zorder=3)
            # Dashed line for forecast (overlapping one point for continuity)
            ax.plot(x[forecast_start-1:], values[forecast_start-1:],
                    color=color, marker=marker, markersize=6,
                    linewidth=2, linestyle='--', zorder=3)
        else:
            ax.plot(x, values, color=color, marker=marker, markersize=6,
                    linewidth=2, label=label, zorder=3)

        # Data point labels
        for j, v in enumerate(values):
            ax.annotate(f'{v:.1f}%', (x[j], v),
                       textcoords="offset points", xytext=(0, 10),
                       ha='center', fontsize=7.5, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_ylabel('Margin (%)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f'{v:.0f}%'))

    # Y-axis range: pad above and below
    all_vals = []
    for _, (v, _, _) in margins.items():
        if v:
            all_vals.extend(v)
    if all_vals:
        ax.set_ylim(min(all_vals) - 5, max(all_vals) + 5)

    ax.legend(loc='upper right', frameon=True, facecolor='white',
              edgecolor=COLORS['grid'], framealpha=0.9)
    ax.grid(axis='y', alpha=0.3)
    ax.grid(axis='x', alpha=0)

    return fig


# ============================================================
# C3: Market Share (Pie)
# ============================================================

def chart_market_share(data, **kwargs):
    """
    Pie chart showing market share breakdown.

    data = {
        "target": "Company A",
        "shares": {
            "Company A": 27.6,
            "Competitor A": 19.4,
            ...
        }
    }
    """
    apply_style()

    target = data['target']
    shares = data['shares']

    # Group small slices (<3%) into "Others"
    grouped = {}
    others = 0
    for name, pct in shares.items():
        if name == 'Others':
            others += pct
        elif pct < 3.0 and name != target:
            others += pct
        else:
            grouped[name] = pct
    if others > 0:
        grouped['Others'] = others

    labels = list(grouped.keys())
    sizes = list(grouped.values())

    # Colors: target company gets dark blue, others get palette
    colors = []
    explode = []
    palette_idx = 0
    for name in labels:
        if name == target:
            colors.append(COLORS['primary'])
            explode.append(0.05)  # Pull out target slice
        elif name == 'Others':
            colors.append('#CCCCCC')
            explode.append(0)
        else:
            colors.append(PALETTE[(palette_idx + 1) % len(PALETTE)])
            palette_idx += 1
            explode.append(0)

    fig, ax = plt.subplots(figsize=(7, 7))

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%',
        colors=colors, explode=explode,
        startangle=90, pctdistance=0.75,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
        textprops={'fontsize': 10, 'color': COLORS['text']},
    )

    # Bold the target company label
    for text in texts:
        if text.get_text() == target:
            text.set_fontweight('bold')

    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color('white')

    ax.axis('equal')

    return fig


# ============================================================
# C4: Historical PE Band (Full Time-Series)
# ============================================================

def chart_pe_band(data, **kwargs):
    """
    Line chart with shaded standard deviation bands showing historical PE.

    data = {
        "periods": ["Q1-21", "Q2-21", ...],
        "pe_values": [32.1, 30.5, ...],
        "mean": 29.2,
        "std": 3.8,
        "current": 28.5,
        "current_percentile": 62
    }
    """
    apply_style()

    periods = data['periods']
    pe_values = np.array(data['pe_values'], dtype=float)
    mean = data['mean']
    std = data['std']
    current = data['current']
    pctile = data.get('current_percentile', '')

    n = len(periods)
    x = np.arange(n)

    fig, ax = plt.subplots(figsize=(9, 5))

    # ±2σ band (very light)
    ax.fill_between(x, mean - 2*std, mean + 2*std,
                     alpha=0.1, color=COLORS['primary'], label='±2σ')
    # ±1σ band (medium)
    ax.fill_between(x, mean - std, mean + std,
                     alpha=0.2, color=COLORS['primary'], label='±1σ')
    # Mean line
    ax.axhline(y=mean, color=COLORS['primary'], linewidth=1.5,
                linestyle='--', alpha=0.7, label=f'Mean: {mean:.1f}x')

    # PE line
    ax.plot(x, pe_values, color=COLORS['primary'], linewidth=1.8, zorder=3)

    # Current PE marker
    ax.plot(n-1, current, 'o', color=COLORS['quinary'], markersize=10, zorder=5)
    pctile_text = f' — {pctile}th pctile' if pctile else ''
    ax.annotate(f'Current: {current:.1f}x{pctile_text}',
                (n-1, current), textcoords="offset points",
                xytext=(10, 15), fontsize=9, fontweight='bold',
                color=COLORS['quinary'],
                arrowprops=dict(arrowstyle='->', color=COLORS['quinary'], lw=1.2))

    # X-axis: show every nth label to avoid crowding
    step = max(1, n // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([periods[i] for i in range(0, n, step)], rotation=45)
    ax.set_ylabel('PE Ratio (x)')

    ax.legend(loc='upper left', frameon=True, facecolor='white',
              edgecolor=COLORS['grid'])

    return fig


# ============================================================
# C4 alt: Historical PE Band (Simplified — Summary Stats Only)
# ============================================================

def chart_pe_band_simple(data, **kwargs):
    """
    Simplified horizontal band chart when only summary statistics are available.

    data = {
        "metric": "PE(TTM)",
        "high": 38.5,
        "plus_1sd": 33.0,
        "mean": 29.2,
        "minus_1sd": 25.4,
        "low": 22.1,
        "current": 28.5,
        "percentile": 62
    }
    """
    apply_style()

    metric = data.get('metric', 'PE')
    high = data['high']
    p1sd = data['plus_1sd']
    mean = data['mean']
    m1sd = data['minus_1sd']
    low = data['low']
    current = data['current']
    pctile = data.get('percentile', '')

    fig, ax = plt.subplots(figsize=(9, 3.5))

    y_center = 0.5
    band_height = 0.3

    # Full range band (lightest)
    ax.barh(y_center, high - low, left=low, height=band_height,
            color=COLORS['primary'], alpha=0.1, edgecolor='none')

    # ±1σ band (medium)
    ax.barh(y_center, p1sd - m1sd, left=m1sd, height=band_height,
            color=COLORS['primary'], alpha=0.25, edgecolor='none')

    # Mean line
    ax.axvline(x=mean, color=COLORS['primary'], linewidth=2,
                linestyle='--', alpha=0.7)
    ax.text(mean, y_center + band_height/2 + 0.05, f'Mean\n{mean:.1f}x',
            ha='center', va='bottom', fontsize=8, color=COLORS['primary'])

    # Current marker
    ax.plot(current, y_center, 'D', color=COLORS['quinary'],
            markersize=14, zorder=5)
    pctile_text = f' ({pctile}th pctile)' if pctile else ''
    ax.text(current, y_center - band_height/2 - 0.08,
            f'Current: {current:.1f}x{pctile_text}',
            ha='center', va='top', fontsize=9, fontweight='bold',
            color=COLORS['quinary'])

    # Low/High labels
    ax.text(low, y_center + band_height/2 + 0.05, f'Low\n{low:.1f}x',
            ha='center', va='bottom', fontsize=8, color=COLORS['text'])
    ax.text(high, y_center + band_height/2 + 0.05, f'High\n{high:.1f}x',
            ha='center', va='bottom', fontsize=8, color=COLORS['text'])

    # ±1σ labels
    ax.text(m1sd, y_center - band_height/2 - 0.03, f'-1σ: {m1sd:.1f}x',
            ha='center', va='top', fontsize=7, color=COLORS['quaternary'])
    ax.text(p1sd, y_center - band_height/2 - 0.03, f'+1σ: {p1sd:.1f}x',
            ha='center', va='top', fontsize=7, color=COLORS['quaternary'])

    ax.set_xlabel(f'{metric} (x)')
    ax.set_yticks([])
    ax.set_xlim(low - (high-low)*0.1, high + (high-low)*0.1)
    ax.set_ylim(-0.1, 1.1)
    ax.spines['left'].set_visible(False)

    return fig


# ============================================================
# C5: Scenario Comparison (Grouped Bar)
# ============================================================

def chart_scenario_comparison(data, currency='$', **kwargs):
    """
    Grouped bar chart comparing Bull/Base/Bear scenarios across metrics.

    data = {
        "scenarios": ["Bull", "Base", "Bear"],
        "metrics": {
            "Revenue ($B)": [420, 395, 370],
            "Net Income ($B)": [110, 100, 88],
            "EPS ($)": [7.20, 6.50, 5.70],
            "Target Price ($)": [260, 230, 195]
        },
        "probabilities": [25, 50, 25]
    }
    """
    apply_style()

    scenarios = data['scenarios']
    metrics = data['metrics']
    probabilities = data.get('probabilities', [])

    metric_names = list(metrics.keys())
    n_metrics = len(metric_names)
    n_scenarios = len(scenarios)

    # If scales are too different (>10x range), use 2×2 subplots
    all_vals = [v for vals in metrics.values() for v in vals]
    val_range = max(all_vals) / max(min(all_vals), 0.01)

    scenario_colors = [COLORS['bull'], COLORS['base'], COLORS['bear']]

    if val_range > 10 and n_metrics >= 3:
        # Subplot layout
        n_cols = 2
        n_rows = (n_metrics + 1) // 2
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(9, 3 * n_rows))
        axes = axes.flatten() if n_metrics > 1 else [axes]

        for idx, (metric_name, values) in enumerate(metrics.items()):
            if idx >= len(axes):
                break
            ax = axes[idx]
            bars = ax.bar(scenarios, values, color=scenario_colors[:n_scenarios],
                         width=0.5, edgecolor='white', linewidth=0.5)

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       f'{val:,.1f}' if isinstance(val, float) and val < 100 else f'{val:,.0f}',
                       ha='center', va='bottom', fontsize=8, fontweight='bold')

            ax.set_title(metric_name, fontsize=10, fontweight='bold')
            ax.set_ylim(0, max(values) * 1.18)

        # Hide unused subplots
        for idx in range(n_metrics, len(axes)):
            axes[idx].set_visible(False)

        fig.tight_layout(h_pad=2.5)

    else:
        # Single grouped bar chart
        fig, ax = plt.subplots(figsize=(9, 5.5))

        x = np.arange(n_metrics)
        width = 0.25

        for i, scenario in enumerate(scenarios):
            values = [metrics[m][i] for m in metric_names]
            offset = (i - (n_scenarios - 1) / 2) * width
            bars = ax.bar(x + offset, values, width, label=scenario,
                         color=scenario_colors[i], edgecolor='white', linewidth=0.5)

            for bar, val in zip(bars, values):
                label_text = f'{val:,.1f}' if isinstance(val, float) and val < 100 else f'{val:,.0f}'
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       label_text, ha='center', va='bottom', fontsize=7.5)

        ax.set_xticks(x)
        ax.set_xticklabels(metric_names)
        ax.set_ylim(0, max(all_vals) * 1.18)

        # Legend with probabilities
        legend_labels = []
        for i, s in enumerate(scenarios):
            if probabilities and i < len(probabilities):
                legend_labels.append(f'{s} ({probabilities[i]}%)')
            else:
                legend_labels.append(s)

        handles = [mpatches.Patch(color=scenario_colors[i], label=legend_labels[i])
                   for i in range(n_scenarios)]
        ax.legend(handles=handles, loc='upper right', frameon=True,
                  facecolor='white', edgecolor=COLORS['grid'])

    return fig


# ============================================================
# Main CLI
# ============================================================

CHART_FUNCTIONS = {
    'revenue_segment':      chart_revenue_segment,
    'margin_trends':        chart_margin_trends,
    'market_share':         chart_market_share,
    'pe_band':              chart_pe_band,
    'pe_band_simple':       chart_pe_band_simple,
    'scenario_comparison':  chart_scenario_comparison,
}


def main():
    parser = argparse.ArgumentParser(description='Equity Report Chart Generator')
    parser.add_argument('--chart_type', required=True,
                       choices=list(CHART_FUNCTIONS.keys()),
                       help='Type of chart to generate')
    parser.add_argument('--data', required=True,
                       help='JSON string with chart data')
    parser.add_argument('--output', default='chart.svg',
                       help='Output SVG file path')
    parser.add_argument('--currency', default='$',
                       help='Currency symbol')
    parser.add_argument('--unit', default='B',
                       help='Unit suffix (B=billions, M=millions)')
    parser.add_argument('--json', action='store_true',
                       help='Output JSON metadata to stdout')

    args = parser.parse_args()

    # Parse data
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f'ERROR: Invalid JSON data: {e}', file=sys.stderr)
        sys.exit(1)

    # Generate chart
    chart_fn = CHART_FUNCTIONS[args.chart_type]
    try:
        fig = chart_fn(data, currency=args.currency, unit=args.unit)
    except Exception as e:
        print(f'ERROR: Chart generation failed: {e}', file=sys.stderr)
        sys.exit(1)

    # Save SVG
    b64 = save_svg(fig, args.output)

    # Output metadata
    file_size = os.path.getsize(args.output)

    result = {
        'path': args.output,
        'chart_type': args.chart_type,
        'format': 'svg',
        'file_size_bytes': file_size,
        'image_base64': b64,
    }

    if args.json:
        # Print only metadata (not base64) to keep stdout readable
        meta = {k: v for k, v in result.items() if k != 'image_base64'}
        meta['base64_length'] = len(b64)
        print(json.dumps(meta, indent=2))
    else:
        print(f'Chart saved to {args.output} ({file_size:,} bytes)')


if __name__ == '__main__':
    main()
