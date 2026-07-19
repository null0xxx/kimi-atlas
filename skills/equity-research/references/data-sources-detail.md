# Data Sources Detail Reference

**[Note] This file supplements `data-sources.md` with detailed API parameters. Grep search by keyword as needed; do not load entire file.**

---

## 1. iFind API Detailed Parameters

### 1.1 Company Basic Info API

```python
ifind_get_stock_info(
    ticker: str,          # e.g. "600519.SH"
    file_path: str        # Output CSV path, required
)
```

| Field | Description | Example Value |
|-------|-------------|----------------|
| `company_name` | Company name | [目标公司全称] |
| `industry` | Industry | 白酒 |
| `listing_date` | Listing date | 2001-08-27 |
| `total_shares` | Total shares | 1.256 billion |
| `float_shares` | Floating shares | 1.256 billion |
| `market_cap` | Total market cap | 2.1 trillion |
| `pe_ttm` | P/E (TTM) | 28.5 |
| `pb` | Price-to-Book | 8.2 |
| `main_business` | Main business | [主营业务描述] |

### 1.2 Financial Statements API

```python
ifind_get_financial_statements(
    ticker: str,                          # e.g. "600519.SH". Supports multiple: "600519.SH,000858.SZ"
    statement: str,                       # income/balance/cashflow
    financial_parameter: str,             # Reporting period: "YYYYMMDD" where MM DD ∈ {0331,0630,0930,1231}
                                          # e.g., "20241231"=FY2024, "20250331"=Q1 2025
    file_path: str                        # Output CSV path, required
)
```

> **⚠️ `financial_parameter` format**: Must be `YYYY`+`MM DD` where MM DD is one of {0331, 0630, 0930, 1231}. Values like `"2024"`, `"FY2024"`, `"2024Q1"` will return empty data.

**Income Statement**: `revenue`, `operating_cost`, `gross_profit`, `operating_profit`, `net_profit`, `eps`
**Balance Sheet**: `total_assets`, `total_liabilities`, `total_equity`, `current_assets`, `current_liabilities`, `inventory`, `accounts_receivable`
**Cash Flow Statement**: `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`, `free_cash_flow`, `capex`

### 1.3 Financial Metrics API

```python
ifind_get_stock_financial_index(
    ticker: str,              # e.g. "600519.SH". Supports multiple: "600519.SH,000858.SZ"
    financial_parameter: str, # Reporting period: "YYYYMMDD" where MM DD ∈ {0331,0630,0930,1231}
    file_path: str            # Output CSV path, required
)
```

**Profitability**: `roe`, `roa`, `gross_margin`, `net_margin`, `operating_margin`
**Growth**: `revenue_growth`, `net_profit_growth`, `asset_growth`, `eps_growth`
**Solvency**: `debt_to_asset`, `current_ratio`, `quick_ratio`, `interest_coverage`
**Operating Efficiency**: `asset_turnover`, `ar_days`, `inventory_days`, `operating_cycle`
**Cash Flow**: `ocf_to_profit`, `free_cash_flow`, `ocf_interest_coverage`

**Note**: `financial_parameter` format: `YYYY` + `MM DD` where MM DD is one of {0331, 0630, 0930, 1231}.
- `"20241231"` = FY2024 annual report
- `"20250331"` = Q1 2025 report
- **Wrong formats that will fail**: `"2024"`, `"FY2024"`, `"2024Q1"`, `"2024-12-31"`
- If call fails with empty return, first verify `financial_parameter` uses correct format, then retry.

### 1.4 Business Segmentation API

```python
ifind_get_stock_business_segmentation(
    ticker: str,              # e.g. "600519.SH"
    financial_parameter: str, # Reporting period, e.g. "20241231"
    file_path: str            # Output CSV path, required
)
```

Returns: `segment_name`, `revenue`, `revenue_pct`, `yoy_growth`, `gross_margin`

> **⚠️ Cross-market restriction**: Do NOT mix A-shares with HK/US stocks in a single call. HK + US can be mixed, but A-shares must be queried separately.

### 1.5 Earnings Forecast API

```python
ifind_get_forecast(
    ticker: str,       # e.g. "600519.SH" — SINGLE ticker only, multiple tickers will error
    file_path: str     # Output CSV path, required
)
```

Returns: `revenue_forecast`, `net_profit_forecast`, `eps_forecast`, `pe_forecast`, `target_price`, `rating`, `analyst_count`

> **⚠️ Restrictions**: (1) A-shares only — HK/US stocks return empty; (2) Single ticker only — do NOT pass comma-separated tickers.

### 1.6 Stock Price Data API

```python
ifind_get_price(
    ticker: str,           # e.g. "600519.SH" (A股), "0700.HK" (HK), "AAPL.O" (US NASDAQ), "XOM.N" (US NYSE)
    start_date: str,       # e.g. "2025-01-01"
    end_date: str,         # e.g. "2026-01-01"
    file_path: str,        # Output CSV path, required
    adjust: str = "forward"  # Ex-dividend adjustment, required
)
```

**Note**: `adjust_type="pre"` is deprecated; use `adjust: "forward"` uniformly.

**US Stock Ticker Format for iFind**:
| Exchange | iFind Format | Example |
|----------|-------------|---------|
| NYSE | `XXX.N` | `XOM.N` |
| NASDAQ | `XXX.O` | `AAPL.O` |
| NYSE (Class A) | `XXX.A.N` | `BRK.A.N` |
| NYSE (Class B) | `XXX.B.N` | `BRK.B.N` |

Returns: `date`, `open`, `high`, `low`, `close`, `volume`, `amount`

---

## 2. Yahoo Finance API Detailed Parameters

### 2.1 Company Info

```python
get_stock_info(ticker: str)  # e.g. "AAPL"
```

Returns: `name`, `sector`, `industry`, `market_cap`, `pe_ttm`, `pb`, `dividend_yield`, `52_week_high`, `52_week_low`

### 2.2 Financial Statements

```python
get_financial_statement(ticker: str, statement_type: str, period: str = "annual")
```

### 2.3 Analyst Recommendations

```python
get_recommendations(ticker: str)
```

Returns: `rating`, `target_price`, `analyst_count`, `buy_count`, `hold_count`, `sell_count`

---

## 3. 天眼查 API Detailed Parameters

```python
tianyancha_api_search(keyword: str, limit: int = 10)
tianyancha_api_call(endpoint: str, params: dict)
```

| endpoint | Function |
|----------|----------|
| `/company/baseinfo` | Company basic info |
| `/company/holders` | Shareholder info |
| `/company/suppliers` | Suppliers |
| `/company/customers` | Customers |
| `/company/competitors` | Competitors |

---

## 4. Caixin API

```python
caixin_api_search(keyword: str, limit: int = 10, start_date: str = None, end_date: str = None)
caixin_api_call(endpoint: str, params: dict)
```

---

## 5. Stock Code Format Quick Reference

> Stock code formats and index codes are detailed in the "Stock Code Format" section of `references/data-sources.md`; not repeated here.
