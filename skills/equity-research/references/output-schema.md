# Output Schema: Interface Contract Between Analysis and Presentation Layers

This document defines the structured data contract that the analysis engine (Phase 0-3) produces and the presentation layer (Phase 4-5) consumes. Both `tear-sheet` and `equity-report` skills rely on this schema.

---

## Overview

```
Phase 0-3 (Analysis Engine)  →  Output Schema  →  Phase 4-5 (Presentation Layer)
                                     ↑
                              This document defines
                              the interface contract
```

The analysis engine produces a structured intermediate object (written to `{company}_{ticker}_analysis_brief.md`). The presentation layer reads this object and formats it into the final report (HTML → PDF).

**Neither layer should bypass this contract.** The analysis engine must populate all required fields; the presentation layer must not re-derive analysis conclusions.

---

## Schema Definition

### Section I: Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_name` | string | Yes | Full company name (Chinese + English if applicable) |
| `ticker` | string | Yes | Stock code with exchange suffix (e.g., `600519.SH`, `AAPL`) |
| `market` | enum | Yes | `A-share` / `HK` / `US` |
| `report_language` | enum | Yes | `zh-CN` / `en` |
| `report_date` | date | Yes | Report generation date |
| `latest_trading_date` | date | Yes | Most recent trading date with data |
| `latest_financial_report` | string | Yes | e.g., "2024 Annual Report" / "Q3 2025" |
| `next_earnings_date` | date | Recommended | Estimated next earnings release |
| `benchmark_index` | string | Yes | Benchmark index code (e.g., `000001.SH`) |
| `benchmark_name` | string | Yes | Benchmark index name (e.g., "Shanghai Composite / 上证指数") |
| `output_level` | enum | Yes | `tear-sheet` / `equity-report` |

### Section II: Core Investment Narrative

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `core_narrative` | string (3-5 sentences) | Yes | Connects: industry trend → company advantage → financial performance → valuation judgment → key risk |
| `main_title` | string (8-15 chars) | Yes | One-sentence core judgment for report header |
| `sub_title` | string (15-25 chars) | Yes | Supplementary explanation for report header |
| `core_viewpoint` | string (3-4 sentences) | Yes | ①Company position ②Financial highlights ③Valuation judgment ④Main risks |

### Section III: Six-Dimension Analysis (六维分析)

Each dimension follows this structure:

```
{
  "dimension_id": "H1" | "H2" | "H3" | "H4" | "H5" | "H6",
  "dimension_name": string,
  "conclusion": string,
  "key_data_support": string[],
  "so_what": string,
  "anomalies": string[] | null,       // H3 (earnings quality) specific
  "information_class": "verified" | "partially_verified" | "unverified"  // Internal only, never shown in report
}
```

| Dimension | Name | Maps to Report Module |
|-----------|------|-----------------------|
| H1 | Competitive Landscape (竞争格局) | Caption title, 公司概览, Investment Thesis Table Row 1 |
| H2 | Growth Drivers (增长驱动) | Investment Logic (short-term catalysts), Investment Thesis Table Row 2 |
| H3 | Earnings Quality (盈利质量) | Financial Analysis (盈利质量信号), Investment Thesis Table Row 3, Risk Disclosure |
| H4 | Valuation & Expectations (估值与预期) | Valuation module, Investment Thesis Table Row 4 |
| H5 | Geopolitics/Policy (地缘/政策) | Risk Disclosure, Catalyst Calendar |
| H6 | Technology/Product Cycle (技术/产品周期) | Industry Analysis, Supply Chain |

### Section IV: Investment Logic

```
{
  "short_term": {
    "bull_factors": [
      {
        "description": string,
        "data_support": string,
        "inflection_condition": string,
        "pricing_level": string
      }
    ],  // 2-3 items
    "bear_factors": [
      {
        "description": string,
        "risk_level": "High" | "Medium" | "Low",
        "trigger_condition": string
      }
    ],  // 1-2 items (mandatory ≥1)
    "capital_market_structure": {
      "description": string,
      "data_support": string
    }
  },
  "long_term": {
    "bull_factors": [...],    // 2-4 items
    "bear_factors": [...]     // 1-2 items (mandatory ≥1)
  }
}
```

### Section V: Investment Thesis Comprehensive Analysis Table (投资论点综合分析表)

4 rows × 6 columns, strictly structured:

| Row | Dimension | Bull Arguments | Bear Arguments | Key Assumptions | Turning Point Signal | Judgment |
|-----|-----------|----------------|----------------|-----------------|---------------------|----------|
| 1 | Competitive Landscape (H1) | | | | | |
| 2 | Growth Drivers (H2) | | | | | |
| 3 | Earnings Quality (H3) | | | | | |
| 4 | Valuation & Expectations (H4) | | | | | |

### Section VI: Company Overview Data

```
{
  "background": {
    "founding": string,        // Founder, year, location, listing history
    "management": string,      // Key management assessment (see analysis-brief-template.md §III Management & Governance)
    "ownership": string        // Equity structure, controlling shareholder, institutional holders
  },
  "business_model": {
    "value_proposition": string,  // What they do, for whom, how they make money
    "moat": string,               // Core competitive advantage (see analysis-brief-template.md §II.2.1 Competitive Moat — 6 types: brand / switching cost / network / scale / technology / policy)
    "cost_structure": string      // Key cost drivers
  },
  "recent_developments": {
    "summary": string,
    "key_financials": string,
    "announcements": string
  },
  "business_segments": [
    {
      "segment_name": string,
      "revenue": number,
      "revenue_pct": number,
      "yoy_growth": number,
      "gross_margin": number
    }
  ]
}
```

### Section VII: Financial Data

```
{
  "income_statement": { ... },       // Revenue, net income, EPS, margins (3Y historical + 2Y forecast)
  "balance_sheet_highlights": { ... },
  "cash_flow_highlights": { ... },
  "earnings_quality_signals": string[],  // Anomaly checks: OCF/NI ratio, DSO/DIO/DPO trends, non-recurring items, accounting policy vs peers (see analysis-brief-template.md §V / research-document-template.md §II.2.3)
  "key_ratios": {
    "profitability": { "gross_margin", "net_margin", "roe", ... },
    "growth": { "revenue_yoy", "net_income_yoy", ... },
    "solvency": { "debt_ratio", "current_ratio", ... },
    "cash_flow": { "ocf", "fcf", "ocf_to_net_income", ... }
  }
}
```

### Section VIII: Valuation Data

**Level 1 (Tear Sheet):**
```
{
  "valuation_table": {
    // PE/PB/PS/EV-EBITDA for 3Y historical + 2Y forecast
  },
  "consensus_expectations": {
    "coverage_count": number,
    "eps_forecast": number,
    "revenue_forecast": number,
    "revision_trend": string,
    "peg": number
  },
  "comparable_companies": [
    { "name", "ticker", "market_cap", "pe", "pb", "ps", ... }
  ],
  "industry_average": { "pe", "pb", "ps", ... },
  "premium_discount_analysis": string
}
```

**Level 2 (Equity Report) — extends Level 1 with:**
```
{
  "dcf": {
    "wacc": number,
    "terminal_growth": number,
    "fcf_projections": [...],
    "terminal_value": number,
    "enterprise_value": number,
    "equity_value_per_share": number,
    "sensitivity_matrix": { ... }
  },
  "historical_band": {
    "pe_band": { "high", "low", "median", "current_percentile" },
    "pb_band": { ... }
  },
  "sotp": { ... },  // Sum-of-the-parts if applicable
  "valuation_synthesis": string  // Cross-method comparison narrative
}
```

### Section IX: Catalyst Calendar

```
[
  {
    "date": date,
    "event": string,
    "importance": "High" | "Medium" | "Low",
    "impact_analysis": string,
    "market_expectation": string,
    "source": string
  }
]
// Minimum 4 events, must include next earnings, ≥2 High importance
```

### Section X: Scenario Analysis

```
{
  "optimistic": { "probability", "assumptions", "revenue", "net_income", "target_pe", "implied_market_cap" },
  "base_case": { ... },
  "pessimistic": { ... }
}
```

### Section XI: Risk List

```
[
  { "risk_type": string, "description": string, "impact": "High"|"Medium"|"Low", "probability": "High"|"Medium"|"Low" }
]
```

### Section XII: Industry & Supply Chain

```
{
  "industry_overview": string,
  "market_concentration": string,      // CR3/CR5
  "pricing_power": string,
  "entry_barriers": string,
  "competitive_trend": string,
  "supply_chain": {
    "upstream": [...],
    "midstream": [...],
    "downstream": [...],
    "end_users": [...]
  }
}
```

### Section XIII: Stock Price & Trading Data

```
{
  "stock_csv_path": string,        // Path to 52-week stock price CSV
  "benchmark_csv_path": string,    // Path to benchmark index CSV
  "current_price": number,
  "52w_high": number,
  "52w_low": number,
  "market_cap": number,
  "pe_ttm": number,
  "pb": number,
  "daily_volume": number,
  "turnover_rate": number,
  "beta": number,
  "dividend_yield": number
}
```

---

## Consumption Rules

### For `tear-sheet` skill (Level 1):
- Consumes all sections
- Valuation uses Level 1 only
- All modules condensed into 3-5 page dual-box layout
- Content is bullet-focused, maximum information density

### For `equity-report` skill L2 (Full Version):
- Consumes all sections
- Valuation uses Level 1 + Level 2 (DCF + Historical Band + Sensitivity)
- Task 1 → Task 2 (Excel model) → Task 3
- Modules expand into full paragraphs with deeper analysis
- ≥25 pages, flexible layout

### For `equity-report` skill L1 (Streamlined Version):
- Consumes all sections EXCEPT §XII (Preliminary DCF inputs are replaced with comps data)
- Valuation uses Level 1 only (Comparable companies + consensus + scenario table)
- Task 1 → Task 3 directly (no Task 2 Excel model)
- §XII of the research document must contain: ≥3 comparable companies with full financial metrics, consensus target price, and scenario assumptions
- ≥25 pages, flexible layout
- DCF, Historical Band, and Sensitivity Matrix modules are SKIPPED in Task 3

### Validation Rules:
1. `core_narrative` must not be empty
2. All 6 dimensions of six-dimension analysis must have conclusions
3. Investment thesis table must have exactly 4 rows
4. Both short-term and long-term investment logic must have ≥1 bear factor
5. Catalyst calendar must have ≥4 events including next earnings
6. All financial data must have source attribution
7. No fabricated/placeholder data allowed
