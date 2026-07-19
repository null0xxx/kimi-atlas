# Stock Chart Module Specification / 股价图模块规范

**Related File**: `scripts/stock_chart_generator.py`

---

## Module Overview

**Module Position**: First page, immediately below stylized title area

**Layout**: Left-Right Dual Box, no module-level section-title, use exhibit-label inside chart as title
- Left Box (`.stock-chart-box`): 52-week stock price chart + benchmark index overlay (flex: 1.2~1.5)
- Right Box (`.core-data-box`): Core trading data table (flex: 1.0)

---

## Left Box: 52-week Stock Price Chart

### Content Requirements

- Display past 52 weeks (1 year) stock price trend
- **Must use forward-adjusted (Forward Adjusted) price**, avoid price cliff from stock split, reverse split, dividend
- Overlay major benchmark index trend (A股→上证指数, HK stocks→恒生指数, US→S&P 500)
- Mark key price points: 52-week high, 52-week low, current price
- Show excess return vs benchmark

### [Note] Adjustment Processing (Must Comply)

**Problem**: If stock underwent split (e.g. 1:10 split), reverse split or paid special dividend within 52 weeks, unadjusted price shows cliff jump, causing serious chart distortion.

**Processing Rules**:

| Data Source | How to Get Forward-Adjusted Price |
|---|---|
| iFind | `ifind_get_price(ticker, start_date, end_date, file_path, adjust="forward")` |
| Yahoo Finance | Use `Adj Close` field (auto forward-adjusted) |

**Note**: Old docs `adjust_type="pre"` deprecated, use `adjust: "forward"`.

**Verification Method**: If 52-week shows single-day >30% jump, must check if stock split/reverse split:
1. Search `[Company Name] split reverse stock split` confirm
2. If confirmed split and price unadjusted, must reget forward-adjusted data
3. If confirmed real crash/surge (e.g. earnings blowup), keep original data but annotate event on chart

### ⛔ ABSOLUTE PROHIBITION: No Mock Data Under Any Circumstance

**Using simulated/random/mock data for stock charts is STRICTLY FORBIDDEN.**

| Violation | Consequence |
|-----------|------------|
| Mock stock prices | 52-week high/low completely wrong → misleading investment signals |
| Mock benchmark | Excess return vs benchmark fictitious → false alpha claims |
| Mock volume | Split detection fails → unadjusted price cliffs in chart |
| Any fabricated price data | Report loses all credibility; potential compliance violation |

**The script `stock_chart_generator.py` has permanently removed the `--use-mock` parameter.**
If CSV data is unavailable, **skip the stock chart module entirely** and add a data source annotation:
> "52-week stock chart: Data temporarily unavailable. Price data sourced separately."

### Generation Flow (Strict Sequence, Cannot Skip)

#### Step 1: Data Retrieval with Retry Logic

**Primary source**: iFind `ifind_get_price()` with `adjust="forward"`.

```python
# 重试逻辑 — iFind API可能不稳定，必须执行最多3次重试
import time

def get_price_with_retry(ticker, start_date, end_date, file_path, max_retries=3):
    """获取股价数据，带重试逻辑"""
    for attempt in range(1, max_retries + 1):
        try:
            result = get_data_source(
                data_source_name="ifind",
                api_name="ifind_get_price",
                params={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                    "file_path": file_path,
                    "adjust": "forward"
                }
            )
            # 验证返回数据非空
            import os
            if os.path.exists(file_path) and os.path.getsize(file_path) > 100:
                return True, f"Success on attempt {attempt}"
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 指数退避: 2s, 4s, 8s
                time.sleep(wait_time)
            else:
                return False, f"Failed after {max_retries} attempts: {str(e)}"
    return False, "All retries exhausted"
```

**Retry Flow**:
```
Attempt 1: iFind get_price → success? → done
     ↓ fail
Attempt 2: iFind get_price (参数诊断后重试) → success? → done
     ↓ fail
Attempt 3: iFind get_price (指数退避等待后) → success? → done
     ↓ fail
Fallback: Yahoo Finance get_historical_stock_prices → success? → done
     ↓ fail
Action: Skip stock chart module. Annotate "data unavailable".
     ↓
NEVER: Generate mock/simulated/random data
```

**Yahoo Finance Fallback Call** (executed only after all 3 iFind attempts have failed):

```python
# Ticker must be in Yahoo format — see references/data-sources.md §Stock Code Format
get_data_source(
    data_source_name="yahoo_finance",
    api_name="get_historical_stock_prices",
    params={"ticker": "{TICKER_YAHOO_FORMAT}", "period": "1y", "interval": "1d"}
)
# Save returned data to CSV; ensure the "Adj Close" column is present
# (Yahoo's adjusted close is the equivalent of iFind's forward-adjusted price).
```

**Benchmark index retrieval follows the exact same retry logic** — try iFind first, fall back to Yahoo Finance, exhaust both before declaring failure. See `references/data-sources.md §Benchmark Index Codes` for the per-market ticker mapping (A股 / HK / US).

#### Step 2: Data Validation (Strict, Cannot Skip)

- Check CSV file exists and not empty (file size > 100 bytes)
- Check data rows ≥ 50 (52-week trading days ~250)
- **If validation fails**: The data is genuinely unavailable for this stock/period.
  - Skip the stock chart module
  - Add annotation: `"52-week stock chart: Market data temporarily unavailable from all sources (iFind + Yahoo Finance). Price statistics sourced from most recent trading data."`
  - **DO NOT** attempt to "fill in" or "estimate" prices

**Pre-script-call sanity check** (mandatory before invoking `stock_chart_generator.py` in Step 4):

```python
import os
# Both files must exist AND contain real data — never call the script otherwise
assert os.path.exists(stock_csv) and os.path.getsize(stock_csv) > 100, \
    "Stock CSV missing or empty — skip module, do NOT generate mock data"
assert os.path.exists(benchmark_csv) and os.path.getsize(benchmark_csv) > 100, \
    "Benchmark CSV missing or empty — skip module, do NOT generate mock data"
```

#### Step 3: Adjustment Verification

Check for single-day >30% jumps, eliminate stock split/reverse split interference.

#### Step 4: Call Script Generate Chart (Cannot Skip --json)

```bash
python scripts/stock_chart_generator.py \
  --stock_csv /path/to/stock.csv \
  --benchmark_csv /path/to/benchmark.csv \
  --output /path/to/chart.png --json
```

> **Script Parameters**:
> - `--stock_csv` and `--benchmark_csv` are **required** (no defaults)
> - `--use-mock` parameter has been **removed** from the script
> - Passing no CSV will cause immediate error exit
> - **Must Include `--json`**. Script outputs complete JSON, agent must parse `image_base64` field (complete string, ~40,000+ characters), prohibit taking only first N characters.

#### Step 5-7: Extract, Embed, Verify

5. **Extract Script Output**: Extract complete `image_base64` (~40,000+ characters, must be complete string, prohibit truncation) and stats (52-week high/low/change, etc)
6. **Embed HTML**: Embed base64 image in `<img src="data:image/png;base64,xxx">`
7. **Verify**: Check axes, annotations, legend, benchmark overlay

**Must call `scripts/stock_chart_generator.py` generate, prohibit writing any matplotlib/matplotlib code.**

> **Hard Rules**:
> 1. **Must** call script generate chart, not calling disqualifies module generation
> 2. **Prohibit** writing matplotlib/plotly/echarts any chart library code
> 3. Script **must** receive real CSV paths (`--stock_csv` / `--benchmark_csv`)
> 4. **Prohibit** using `--use-mock` — this flag has been removed from the script
> 5. **Prohibit** generating or using any synthetic/simulated/random price data for any purpose
> 6. If real price data is unavailable after all retries → **skip the chart**, annotate "data unavailable"
> 7. **Rule Violation** behavior: if see HTML `<script>` chart code, `<canvas>` tag, hand-written Python plotting, or mock data → immediately delete and call script with real CSV
>
> **Not Calling Script Consequences**: Chart style inconsistent, 52-week high/low annotations missing, benchmark overlay may error, adjustment handling incorrect → report quality fails, Phase 5 checklist cannot pass
>
> **Mock Data Consequences**: Mock data causes 52-week high/low distortion, false excess return calculation, completely misleading investment signals → report credibility destroyed, serious compliance risk

### Script Call Verification Checklist (All Must Pass)

```markdown
□ **Script Called**: `python scripts/stock_chart_generator.py` executed and returned JSON
□ **CSV Passed**: `--stock_csv` and `--benchmark_csv` point to real data files
□ **Complete base64 Obtained**: `image_base64` string length ≥ 20,000 chars (~40,000+ normal), prohibit truncation
□ **Image Embedded**: HTML uses `<img src="data:image/png;base64,xxx">`
□ **No Hand Code**: HTML has no `<script>` chart code, `<canvas>`, or hand-written matplotlib
```

### Data Quality Verification Checklist

```markdown
□ Data points ≥50, no missing values, price range reasonable
□ Use forward-adjusted price (not raw price), no stock split cliffs
□ iFind vs Yahoo cross-verification, difference <5% (yfinance rate-limit iFind priority)
□ Benchmark index data complete, dates aligned with stock
□ If real crash/surge event (not split), annotated on chart
```

---

## Right Box: Core Trading Data Table

### Table Structure (Must Include)

| Metric | Value | Metric | Value |
|---|---|---|---|
| Current Price | ¥XX.XX | Market Cap | ¥XX bn |
| 52-week High | ¥XX.XX | PE (TTM) | XX.x |
| 52-week Low | ¥XX.XX | PB | X.X |
| Daily Change | X.XX% | Revenue (TTM) | ¥XX bn |
| Volume | ¥XX million shares | Net Profit (TTM) | ¥XX bn |
| Turnover | X.XX% | EPS (TTM) | ¥X.XX |

---

## Data Sources and Script Call Example

| Data Type | Data Source | API |
|---|---|---|
| Stock price data | iFind | `ifind_get_price` |
| Benchmark index | iFind | `ifind_get_price` |
| Trading data | iFind | `ifind_get_stock_info` |
| Valuation metrics | iFind | `ifind_get_stock_financial_index` |

### Script Call Example (CSV Input)

```bash
python scripts/stock_chart_generator.py \
  --market A \
  --stock_code 002594.SZ \
  --stock_csv /path/to/stock_prices.csv \
  --stock_date_col time \
  --stock_price_col close \
  --stock_volume_col volume \
  --benchmark_csv /path/to/benchmark_prices.csv \
  --benchmark_date_col time \
  --benchmark_price_col close \
  --auto-adjust-splits \
  --stock_name "{stock_name}" \
  --lang cn \
  --output /path/to/chart.png \
  --json
```

**Key Parameter Notes**:
- `--auto-adjust-splits`: When iFind/Yahoo return unadjusted data, script auto-detects split/reverse split signals (>30% single-day price jump + volume surge), applies forward adjustment to historical price. A股 users strongly recommend enabling.
- `--stock_volume_col`: Provide volume column name, improves split detection accuracy.
- `--lang cn|en`: X-axis month language. Default: A/HK market→cn ("4月""6月"), US market→en ("Apr""Jun"). Generate Chinese report for US stocks pass `--lang cn`.
- Y-axis: Currency symbol only show axis top, tick values pure numbers.

**Prohibit**: Running script without CSV input (defaults to mock data).

---

## Exhibit Numbering

Stock chart and core trading data table each need Exhibit number, usually first two in document.

HTML template (no module-level section-title, title inside chart):
```html
<div class="module-row">
  <div class="two-column">
    <div class="stock-chart-box" style="flex: 1.5;">
      <div class="exhibit-label">
        <span class="exhibit-number">Exhibit 1:</span>
        <span class="exhibit-desc">52-week Price Trend vs Benchmark</span>
      </div>
      <div class="chart-container">
        <!-- [Script output complete image_base64] ~40,000+ chars, prohibit truncation -->
        <img src="data:image/png;base64,[Complete image_base64 String]" alt="52-week Stock Chart">
      </div>
      <div class="data-source">iFind, as of YYYY-MM-DD</div>
    </div>
    <div class="core-data-box" style="flex: 1;">
      <div class="exhibit-label">
        <span class="exhibit-number">Exhibit 2:</span>
        <span class="exhibit-desc">Core Trading Data</span>
      </div>
      <table class="core-data-table">
        <tr><td>Latest Price</td><td>¥XX.XX</td><td>Market Cap</td><td>¥XX bn</td></tr>
        <tr><td>52-week High</td><td>¥XX.XX</td><td>PE (TTM)</td><td>XX.x</td></tr>
        <tr><td>52-week Low</td><td>¥XX.XX</td><td>PB</td><td>X.X</td></tr>
        <tr><td>52-week Change</td><td>X.XX%</td><td>Revenue (TTM)</td><td>¥XX bn</td></tr>
        <tr><td>YTD Change</td><td>X.XX%</td><td>Net Profit (TTM)</td><td>¥XX bn</td></tr>
        <tr><td>Avg Daily Volume</td><td>¥XX million shares</td><td>EPS (TTM)</td><td>¥X.XX</td></tr>
        <tr><td>Beta</td><td>X.XX</td><td>Dividend Yield</td><td>X.XX%</td></tr>
      </table>
      <div class="data-source">iFind, Real-time Market</div>
    </div>
  </div>
</div>
```

**Key Rules**:
- Prohibit using `<div class="section-title">52-week Price Trend and Core Trading Data</div>` as module-level title
- Title via `.exhibit-label` placed inside each Box, left "Exhibit 1", right "Exhibit 2"
- Left uses `.stock-chart-box` (dark blue left border `#003366`), right uses `.core-data-box` (blue left border `#1E90FF`)
- **Image must convert to base64 embed**: `<img src="data:image/png;base64,xxx">`. Prohibit relative path (e.g. `src="chart.png"`), Playwright cannot resolve causing image not display
- Right `.core-data-table` must use 4-column structure (metric/value/metric/value), CSS defines odd/even column style (metric name gray left-align, value black right-align monospace, etc)

---

## Checklist

- [ ] Left: `.stock-chart-box`, 52-week trend+benchmark, 52-week high/low complete, image base64 embedded (complete string, ~40,000+ characters)
- [ ] Right: `.core-data-box`, `.core-data-table` (4 columns), numbers right-align
- [ ] No module-level `section-title`, title via `.exhibit-label` inside Box
- [ ] Data source annotation
