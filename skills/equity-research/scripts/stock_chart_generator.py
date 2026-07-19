#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股价图生成脚本 - CSV输入版 (Production Only / 生产环境专用)
Investment Research Report Stock Chart Generator (CSV Input)

使用方法:
    python stock_chart_generator.py --market A \
        --stock_csv stock_prices.csv --stock_date_col date --stock_price_col close \
        --benchmark_csv benchmark_prices.csv --benchmark_date_col date --benchmark_price_col close \
        --output chart.png --json

⚠️ 严禁使用模拟数据: 本脚本仅接受真实 CSV 数据输入。不提供模拟数据模式。
⚠️ NO MOCK DATA: This script accepts ONLY real CSV data. No mock/simulated mode available.
"""

import matplotlib
matplotlib.use('Agg')

from matplotlib import font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter, MonthLocator
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import base64
from io import BytesIO
import argparse
import sys
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any, Union
from enum import Enum

# =============================================================================
# 配置常量
# =============================================================================

DPI = 300
WIDTH_PX = 600
HEIGHT_PX = 220

LEFT_MARGIN = 0.10
RIGHT_MARGIN = 0.02
TOP_MARGIN = 0.08
BOTTOM_MARGIN = 0.12

STOCK_LINE_COLOR = '#003366'
BENCHMARK_LINE_COLOR = '#999999'
GRID_COLOR = '#E0E0E0'
TICK_COLOR = '#666666'

MIN_DATA_POINTS_52W = 50
MAX_PRICE_VALUE = 100000
MIN_PRICE_VALUE = 0.001
PRICE_TOLERANCE = 0.05
MAX_TRADING_GAP_DAYS = 20  # A股长假可能超过7天，放宽到20天
SPLIT_JUMP_THRESHOLD = 0.30  # 单日涨跌超过30%视为可能的拆股/并股信号

TICK_LABEL_SIZE = 3.0
ANNOTATION_SIZE = 4.5
LEGEND_SIZE = 3.0

# =============================================================================
# 日志配置
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# =============================================================================
# 字体配置
# =============================================================================

_cjk_font_available = False

def configure_fonts():
    global _cjk_font_available
    try:
        chinese_fonts = [
            'PingFang SC', 'Heiti SC', 'Hiragino Sans GB', 'STSong',  # macOS
            'WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'SimHei',        # Linux
            'Microsoft YaHei',                                          # Windows
            'Arial Unicode MS',                                         # Cross-platform
        ]
        available_chinese_font = None
        for font_name in chinese_fonts:
            try:
                font_path = fm.findfont(fm.FontProperties(family=font_name))
                if font_path and 'DejaVuSans' not in font_path:
                    available_chinese_font = font_name
                    break
            except Exception:
                continue
        if available_chinese_font:
            plt.rcParams['font.sans-serif'] = [available_chinese_font, 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            _cjk_font_available = True
            logger.info(f"Using Chinese font: {available_chinese_font}")
        else:
            _cjk_font_available = False
            logger.warning("No Chinese font found, using default font. Chinese labels will auto-fallback to English.")
    except Exception as e:
        _cjk_font_available = False
        logger.warning(f"Font configuration warning: {e}")

configure_fonts()

# =============================================================================
# 数据类定义
# =============================================================================

class MarketType(Enum):
    A_SHARE = "A"
    HK = "HK"
    US = "US"

@dataclass
class StockData:
    code: str
    name: str
    market: MarketType
    dates: List[datetime]
    prices: List[float]
    volumes: Optional[List[float]] = None

    def __post_init__(self):
        if len(self.dates) != len(self.prices):
            raise ValueError("dates和prices长度必须相同")

    @property
    def max_price(self) -> float:
        return max(self.prices) if self.prices else 0

    @property
    def min_price(self) -> float:
        return min(self.prices) if self.prices else 0

    @property
    def current_price(self) -> float:
        return self.prices[-1] if self.prices else 0

    @property
    def start_price(self) -> float:
        return self.prices[0] if self.prices else 0

@dataclass
class ChartConfig:
    width_px: int = WIDTH_PX
    height_px: int = HEIGHT_PX
    dpi: int = DPI
    left_margin: float = LEFT_MARGIN
    right_margin: float = RIGHT_MARGIN
    top_margin: float = TOP_MARGIN
    bottom_margin: float = BOTTOM_MARGIN

    @property
    def figsize(self) -> Tuple[float, float]:
        return (self.width_px / self.dpi, self.height_px / self.dpi)

# =============================================================================
# 市场配置
# =============================================================================

MARKET_CONFIG = {
    MarketType.A_SHARE: {
        "benchmark_index": "000001.SH",
        "benchmark_name": "上证指数",
        "price_suffix": "¥",
        "high_color": "#CC0000",
        "low_color": "#2E7D32",
    },
    MarketType.HK: {
        "benchmark_index": "HSI",
        "benchmark_name": "恒生指数",
        "price_suffix": "HK$",
        "high_color": "#2E7D32",
        "low_color": "#CC0000",
    },
    MarketType.US: {
        "benchmark_index": "^GSPC",
        "benchmark_name": "标普500",
        "price_suffix": "$",
        "high_color": "#2E7D32",
        "low_color": "#CC0000",
    }
}

# =============================================================================
# 数据读取函数（新增：CSV支持）
# =============================================================================

def read_stock_data_from_csv(
    csv_path: str,
    date_col: str,
    price_col: str,
    stock_code: str,
    market: MarketType,
    volume_col: Optional[str] = None
) -> StockData:
    """从CSV读取股票数据"""
    df = pd.read_csv(csv_path)
    if date_col not in df.columns:
        raise ValueError(f"CSV中未找到日期列: {date_col}。可用列: {list(df.columns)}")
    if price_col not in df.columns:
        raise ValueError(f"CSV中未找到价格列: {price_col}。可用列: {list(df.columns)}")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=date_col).dropna(subset=[date_col, price_col])
    df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
    df = df.dropna(subset=[price_col])

    dates = df[date_col].tolist()
    prices = df[price_col].tolist()
    volumes = None
    if volume_col and volume_col in df.columns:
        df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce')
        volumes = df[volume_col].fillna(0).tolist()

    return StockData(
        code=stock_code,
        name=stock_code.split('.')[0] if '.' in stock_code else stock_code,
        market=market,
        dates=dates,
        prices=prices,
        volumes=volumes
    )

# =============================================================================
# [REMOVED] Mock 数据函数已彻底删除
# 原因: 模拟数据会严重扭曲52周高低点、基准对比和超额收益计算
#       使用模拟数据生成的报告将完全失去参考价值
#       如果真实股价数据不可用，应跳过股价图模块并标注"数据暂不可用"
# =============================================================================

# =============================================================================
# 数据验证函数
# =============================================================================

def validate_stock_data(stock_data: StockData) -> Tuple[bool, List[str]]:
    errors = []
    if len(stock_data.dates) < MIN_DATA_POINTS_52W:
        errors.append(f"数据点不足: {len(stock_data.dates)} < {MIN_DATA_POINTS_52W}")
    if stock_data.max_price > MAX_PRICE_VALUE:
        errors.append(f"最高价格异常: {stock_data.max_price} > {MAX_PRICE_VALUE}")
    if stock_data.min_price < MIN_PRICE_VALUE:
        errors.append(f"最低价格异常: {stock_data.min_price} < {MIN_PRICE_VALUE}")
    price_range = stock_data.max_price - stock_data.min_price
    if stock_data.min_price > 0 and price_range / stock_data.min_price > 10:
        errors.append(f"价格波动过大: {price_range / stock_data.min_price:.1f}x")
    date_diffs = []
    for i in range(1, len(stock_data.dates)):
        diff = (stock_data.dates[i] - stock_data.dates[i - 1]).days
        date_diffs.append(diff)
    if date_diffs:
        max_diff = max(date_diffs)
        if max_diff > MAX_TRADING_GAP_DAYS:
            errors.append(f"数据不连续: 最大间隔{max_diff}天")
    for i in range(1, len(stock_data.prices)):
        price_change = abs(stock_data.prices[i] - stock_data.prices[i - 1]) / stock_data.prices[i - 1]
        if price_change > SPLIT_JUMP_THRESHOLD:
            errors.append(
                f"价格跳跃异常: 第{i}天涨跌{price_change * 100:.1f}% "
                f"(可能是未复权的拆股/并股，建议启用 --auto-adjust-splits)"
            )
            break
    return len(errors) == 0, errors

def cross_validate_data(ifind_data: StockData, yahoo_data: StockData) -> Tuple[bool, float]:
    if len(ifind_data.prices) != len(yahoo_data.prices):
        return False, 1.0
    total_diff = 0
    for i in range(len(ifind_data.prices)):
        diff = abs(ifind_data.prices[i] - yahoo_data.prices[i]) / ifind_data.prices[i]
        total_diff += diff
    avg_diff = total_diff / len(ifind_data.prices)
    passed = avg_diff < PRICE_TOLERANCE
    return passed, avg_diff

def adjust_splits_forward(stock_data: StockData) -> StockData:
    """
    自动检测拆股/并股并进行前复权处理。
    规则：从前向后扫描，找到单日涨跌>SPLIT_JUMP_THRESHOLD(30%)的数据点。
    如果当日成交量也显著放大(>前1日成交量的2倍)，将该日期之前的所有价格乘/除以ratio。
    """
    prices = stock_data.prices.copy()
    dates = stock_data.dates.copy()
    volumes = stock_data.volumes.copy() if stock_data.volumes else None
    adjusted = False
    cumulative_factor = 1.0
    # 从后往前处理：先找到最后一个跳跃点，计算factor，再往前应用
    factors = [1.0] * len(prices)
    for i in range(len(prices) - 1, 0, -1):
        prev_p = prices[i - 1]
        curr_p = prices[i]
        if prev_p <= 0:
            continue
        price_change = abs(curr_p - prev_p) / prev_p
        if price_change > SPLIT_JUMP_THRESHOLD:
            ratio = curr_p / prev_p
            # 拆股后价格下降（ratio < 1），将之前的价格乘以 ratio 保持连续性
            # 并股后价格上升（ratio > 1），将之前的价格乘以 ratio
            # 但必须排除真实暴涨暴跌：用成交量辅助判断
            # Volume-based corroboration of split / reverse-split signal.
            # Robust to None entries (some sessions lack volume data) and to
            # the falsy-zero pitfall: `if volumes[i]` would treat 0 as missing.
            volume_spike = False
            has_volume_data = bool(volumes) and any(
                v is not None and v > 0 for v in volumes
            )
            if has_volume_data and i > 0:
                prev_vol = max(volumes[i - 1] or 0, 1)  # never divide by 0/None
                curr_vol = volumes[i] or 0              # treat None as 0
                if curr_vol > prev_vol * 1.5:
                    volume_spike = True
            # 如果价格下跌>30%且成交量放大，或价格上涨>30%且成交量放大 → 视为股本变动
            # 否则视为普通异常，发出警告但不自动调整
            if volume_spike or price_change > 0.4:
                logger.info(f"检测到拆股/并股信号: 第{i}天 ({dates[i].strftime('%Y-%m-%d')}) 涨跌{price_change*100:.1f}%, ratio={ratio:.3f}")
                cumulative_factor *= ratio
                adjusted = True
            else:
                logger.warning(f"第{i}天价格跳跃{price_change*100:.1f}%但成交量未显著放大，未自动复权，建议人工核查")
        factors[i - 1] = cumulative_factor
    if adjusted:
        for i in range(len(prices)):
            prices[i] = prices[i] * factors[i]
        logger.info("已执行自动前复权调整")
    return StockData(
        code=stock_data.code,
        name=stock_data.name,
        market=stock_data.market,
        dates=dates,
        prices=prices,
        volumes=volumes
    )

# =============================================================================
# 图表生成函数
# =============================================================================

def _fmt_price(price: float) -> str:
    """根据价格量级动态格式化"""
    if price >= 1000:
        return f"{price:.0f}"
    elif price >= 100:
        return f"{price:.1f}"
    else:
        return f"{price:.2f}"

def _smart_annotate(ax, x, y, text, color, is_high, y_range, other_x=None):
    """智能标注：自动处理边缘冲突和标注重叠"""
    # 默认向外偏移
    offset_y = 8 if is_high else -12
    va = 'bottom' if is_high else 'top'

    # 边缘检测：如果靠近顶部/底部边缘，反向标注到图表内部
    y_top_ratio = (ax.get_ylim()[1] - y) / y_range if y_range > 0 else 1
    y_bottom_ratio = (y - ax.get_ylim()[0]) / y_range if y_range > 0 else 1

    reversed_dir = False
    if is_high and y_top_ratio < 0.12:
        offset_y = -12
        va = 'top'
        reversed_dir = True
    if not is_high and y_bottom_ratio < 0.12:
        offset_y = 8
        va = 'bottom'
        reversed_dir = True

    # 重叠检测：如果两个极值点在水平方向上很近，水平错开
    ha = 'center'
    offset_x = 0
    if other_x is not None and reversed_dir:
        try:
            x_diff_days = abs((x - other_x).days)
        except Exception:
            x_diff_days = 999
        if x_diff_days < 20:
            if is_high:
                offset_x = -10
                ha = 'right'
            else:
                offset_x = 10
                ha = 'left'

    ax.annotate(text,
                xy=(x, y),
                xytext=(offset_x, offset_y),
                textcoords='offset points',
                fontsize=ANNOTATION_SIZE,
                color=color,
                fontweight='bold',
                ha=ha,
                va=va,
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                         edgecolor=color, alpha=0.9, linewidth=0.8),
                clip_on=False,
                zorder=5)

def normalize_benchmark(stock_prices: List[float], benchmark_prices: List[float]) -> List[float]:
    if not benchmark_prices or not stock_prices:
        return []
    ratio = stock_prices[0] / benchmark_prices[0]
    return [p * ratio for p in benchmark_prices]

def generate_stock_chart(
    stock_data: StockData,
    benchmark_data: Optional[StockData] = None,
    config: ChartConfig = None,
    output_path: Optional[str] = None
) -> str:
    if config is None:
        config = ChartConfig()
    market_config = MARKET_CONFIG[stock_data.market]
    fig, ax = plt.subplots(figsize=config.figsize, dpi=config.dpi)
    plt.subplots_adjust(
        left=config.left_margin,
        right=1 - config.right_margin,
        top=1 - config.top_margin,
        bottom=config.bottom_margin
    )
    ax.plot(stock_data.dates, stock_data.prices,
            color=STOCK_LINE_COLOR, linewidth=1.5,
            label=stock_data.name, zorder=3)
    if benchmark_data:
        normalized_benchmark = normalize_benchmark(stock_data.prices, benchmark_data.prices)
        if normalized_benchmark:
            ax.plot(stock_data.dates, normalized_benchmark,
                    color=BENCHMARK_LINE_COLOR, linewidth=1.0,
                    linestyle='--', label=benchmark_data.name, zorder=2, alpha=0.7)

    max_price = stock_data.max_price
    min_price = stock_data.min_price
    max_idx = stock_data.prices.index(max_price)
    min_idx = stock_data.prices.index(min_price)
    y_range = stock_data.max_price - stock_data.min_price
    if y_range <= 0:
        y_range = stock_data.max_price * 0.1

    _smart_annotate(ax, stock_data.dates[max_idx], max_price,
                   _fmt_price(max_price), market_config["high_color"],
                   is_high=True, y_range=y_range, other_x=stock_data.dates[min_idx])

    _smart_annotate(ax, stock_data.dates[min_idx], min_price,
                   _fmt_price(min_price), market_config["low_color"],
                   is_high=False, y_range=y_range, other_x=stock_data.dates[max_idx])

    ax.tick_params(axis='y', labelsize=TICK_LABEL_SIZE, colors=TICK_COLOR, length=1.5)
    ax.tick_params(axis='x', labelsize=TICK_LABEL_SIZE, colors=TICK_COLOR, length=1.5, pad=1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:.0f}"))
    # Currency symbol at the top of y-axis
    suffix = market_config.get("price_suffix", "")
    if suffix:
        ax.text(-0.01, 1.02, suffix, transform=ax.transAxes,
                fontsize=TICK_LABEL_SIZE, color=TICK_COLOR,
                ha='right', va='bottom')
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.3, color=GRID_COLOR)
    ax.set_axisbelow(True)
    # X-axis month labels: Chinese for A/HK, English for US (overridable via --lang)
    lang = getattr(stock_data, '_chart_lang', None)
    if lang is None:
        lang = 'cn' if stock_data.market in (MarketType.A_SHARE, MarketType.HK) else 'en'
    if lang == 'cn':
        if not _cjk_font_available:
            logger.warning("CJK font unavailable, falling back to English month labels")
            lang = 'en'
    if lang == 'cn':
        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda x, pos: f"{mdates.num2date(x).month}月"))
    else:
        ax.xaxis.set_major_formatter(DateFormatter('%b'))
    ax.xaxis.set_major_locator(MonthLocator(interval=2))
    plt.xticks(rotation=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['bottom'].set_color(GRID_COLOR)
    if benchmark_data:
        ax.legend(loc='upper left', fontsize=LEGEND_SIZE,
                  frameon=False,
                  handlelength=1.2,
                  handletextpad=0.3,
                  borderpad=0.2,
                  labelspacing=0.2)

    # Adjust Y-axis range to prevent annotation clipping
    # Add 8% padding above max and below min for price annotations
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    ax.set_ylim(y_min - y_range * 0.08, y_max + y_range * 0.08)

    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=config.dpi,
                facecolor='white', edgecolor='none',
                bbox_inches='tight', pad_inches=0.02)
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    if output_path:
        buffer.seek(0)
        with open(output_path, 'wb') as f:
            f.write(buffer.read())
        logger.info(f"图表已保存到: {output_path}")
    plt.close()
    return img_base64

def generate_chart_with_stats(
    stock_data: StockData,
    benchmark_data: Optional[StockData] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    img_base64 = generate_stock_chart(stock_data, benchmark_data, output_path=output_path)
    current_price = stock_data.current_price
    max_price = stock_data.max_price
    min_price = stock_data.min_price
    avg_price = sum(stock_data.prices) / len(stock_data.prices)
    change_pct = (current_price - stock_data.start_price) / stock_data.start_price * 100
    vs_benchmark = 0
    if benchmark_data:
        stock_return = (stock_data.prices[-1] - stock_data.prices[0]) / stock_data.prices[0]
        bench_return = (benchmark_data.prices[-1] - benchmark_data.prices[0]) / benchmark_data.prices[0]
        vs_benchmark = (stock_return - bench_return) * 100
    market_config = MARKET_CONFIG[stock_data.market]
    return {
        "image_base64": img_base64,
        "stats": {
            "current_price": current_price,
            "max_price": max_price,
            "min_price": min_price,
            "avg_price": avg_price,
            "change_pct": change_pct,
            "vs_benchmark": vs_benchmark,
            "currency_suffix": market_config["price_suffix"]
        }
    }

# =============================================================================
# 主函数
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='股价图生成脚本')
    parser.add_argument('--stock_code', type=str, help='股票代码')
    parser.add_argument('--market', type=str, default='A',
                       choices=['A', 'HK', 'US'], help='市场类型')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出')
    parser.add_argument('--no_benchmark', action='store_true', help='不显示基准指数')

    # CSV 输入参数 (唯一合法输入方式 — 必须通过真实CSV数据)
    parser.add_argument('--stock_csv', type=str, required=True,
                        help='个股价格CSV路径 (必填, 仅接受真实数据)')
    parser.add_argument('--stock_date_col', type=str, default='date', help='个股CSV日期列名')
    parser.add_argument('--stock_price_col', type=str, default='close', help='个股CSV价格列名')
    parser.add_argument('--stock_volume_col', type=str, default='volume', help='个股CSV成交量列名')
    parser.add_argument('--benchmark_csv', type=str, required=True,
                        help='基准指数CSV路径 (必填, 仅接受真实数据)')
    parser.add_argument('--benchmark_date_col', type=str, default='date', help='基准CSV日期列名')
    parser.add_argument('--benchmark_price_col', type=str, default='close', help='基准CSV价格列名')

    # [REMOVED] --use-mock 参数已删除。模拟数据被永久禁用。
    # 理由: 研究报告必须使用真实股价数据。模拟数据会导致错误的52周高低点、
    #       错误的超额收益计算，使报告完全失去投资参考价值。

    # 自动复权开关
    parser.add_argument('--auto-adjust-splits', action='store_true', help='自动检测拆股/并股并进行前复权调整')
    parser.add_argument('--stock_name', type=str, default=None, help='个股显示名称（用于图例）')
    parser.add_argument('--lang', type=str, default=None, choices=['cn', 'en'],
                       help='图表语言（cn=中文月份, en=英文月份）。默认: A/HK→cn, US→en')

    args = parser.parse_args()

    market_map = {'A': MarketType.A_SHARE, 'HK': MarketType.HK, 'US': MarketType.US}
    market = market_map[args.market]

    try:
        logger.info(f"开始生成股价图: market={args.market}")

        # 确定数据来源 — 仅接受真实CSV数据
        if not args.stock_csv:
            parser.error("--stock_csv 为必填参数。严禁使用模拟数据。必须先通过ifind/Yahoo Finance获取真实股价CSV。")
        if not args.stock_code:
            # 从CSV文件名推断股票代码
            args.stock_code = args.stock_csv.split('/')[-1].replace('.csv', '')
        stock_data = read_stock_data_from_csv(
            args.stock_csv, args.stock_date_col, args.stock_price_col,
            args.stock_code, market, volume_col=args.stock_volume_col
        )
        logger.info(f"从CSV读取个股数据: {args.stock_csv}, 共 {len(stock_data.dates)} 条")

        # 自动复权（在验证前执行，以消除拆股导致的价格跳跃）
        if args.auto_adjust_splits:
            stock_data = adjust_splits_forward(stock_data)

        # 验证数据
        is_valid, errors = validate_stock_data(stock_data)
        if not is_valid:
            logger.error("数据验证失败:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
        logger.info("数据验证通过")

        # 获取基准指数数据 — 仅接受真实CSV数据
        benchmark_data = None
        if not args.no_benchmark:
            if not args.benchmark_csv:
                parser.error("--benchmark_csv 为必填参数（除非使用 --no_benchmark）。基准指数必须与个股数据同源获取。")
            benchmark_code = MARKET_CONFIG[market]["benchmark_index"]
            benchmark_data = read_stock_data_from_csv(
                args.benchmark_csv, args.benchmark_date_col, args.benchmark_price_col,
                benchmark_code, market
            )
            logger.info(f"从CSV读取基准数据: {args.benchmark_csv}")
            if benchmark_data:
                benchmark_data.name = MARKET_CONFIG[market]["benchmark_name"]
                # Override benchmark name for English reports
                if args.lang == 'en' or (args.lang is None and market == MarketType.US):
                    en_names = {MarketType.A_SHARE: "SSE Index", MarketType.HK: "HSI", MarketType.US: "S&P 500"}
                    benchmark_data.name = en_names.get(market, benchmark_data.name)
                logger.info(f"基准指数: {benchmark_data.name}")

        # 应用显示名称
        if args.stock_name:
            stock_data.name = args.stock_name

        # 应用语言设置（用于x轴月份显示）
        if args.lang:
            stock_data._chart_lang = args.lang
        else:
            stock_data._chart_lang = 'cn' if market in (MarketType.A_SHARE, MarketType.HK) else 'en'

        # 生成图表
        result = generate_chart_with_stats(stock_data, benchmark_data, args.output)
        logger.info(f"图表生成完成")
        logger.info(f"  当前价格: {result['stats']['current_price']:.2f}")
        logger.info(f"  52周最高: {result['stats']['max_price']:.2f}")
        logger.info(f"  52周最低: {result['stats']['min_price']:.2f}")
        logger.info(f"  涨跌幅: {result['stats']['change_pct']:.2f}%")

        # 总是输出完整 JSON（包含完整 base64），无论 --json 参数是否存在
        # agent 必须解析此 JSON 获取完整的 image_base64
        print(json.dumps(result, indent=2, default=str))

        return 0

    except Exception as e:
        logger.error(f"生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
