# Comparable Company Valuation Module Specification / 可比公司估值对比模块规范

## Module Overview

**Module Position**: First page, below 估值分析 module

**Layout**: Alongside industry analysis module, sharing unified module title
- **Unified Module Title**: `行业与估值对比`
- Left Box: Comparable Company Valuation Comparison Table (border-color: `#1E3A5F`)
- Right Box: Industry Analysis + Competitive Landscape (border-color: `#2E7D32`)

**HTML Structure Template**:
```html
<div class="module-row">
  <div class="section-title">行业与估值对比</div>
  <div class="two-column">
    <div class="box box-primary">
      <div class="box-title">Comparable Company Valuation</div>
      <!-- Comparable company table -->
    </div>
    <div class="box box-success">
      <div class="box-title">Industry Analysis</div>
      <!-- Industry analysis content -->
    </div>
  </div>
</div>
```

**Content Requirements**:
- Select 3-5 same-industry comparable companies (competitors)
- Include target company and comparable companies' core metric comparison
- Use most appropriate valuation metrics (select per industry characteristics)
- **No buy/sell rating column included**

---

## Valuation Metric Selection Guide (Sole Source)

| Industry | Primary Metric | Secondary Metric | Notes |
|---|---|---|---|
| Manufacturing | PE | PB | Stable earnings, PE most common |
| Finance | PB | PE | Asset-driven, PB more suitable |
| Tech/Internet | PS | PEG | High growth, focus on revenue scale |
| Real Estate | NAV | PB | Asset-heavy, focus on net assets |
| Cyclical | PB | EV/EBITDA | Large earnings volatility |
| Loss-making | PS | EV/Revenue | No earnings, focus on revenue |
| Consumer | PE | PS | Brand premium, PE common |
| Pharma | PE | PS | Long R&D cycle, PE common |
| Energy | PB | EV/EBITDA | Asset-heavy, PB more suitable |

---

## Table Structure

### Standard Template

```markdown
| Company | Code | Market Cap (¥bn) | Revenue (TTM) | Net Profit (TTM) | PE (TTM) | PB | PS |
|---|---|---|---|---|---|---|---|
| Target Company | XXX | 1,500 | 1,500 | 210 | 15.2 | 2.8 | 1.0 |
| Comparable A | YYY | 2,000 | 1,800 | 250 | 16.0 | 3.0 | 1.1 |
| Comparable B | ZZZ | 800 | 900 | 100 | 14.5 | 2.5 | 0.9 |
| Industry Avg | - | - | - | - | 15.2 | 2.7 | 1.0 |

*Data Source: iFind, as of YYYY-MM-DD*
```

### Minimal Template (when space limited)

```markdown
| Company | Code | Market Cap (¥bn) | PE (TTM) | PB | PS |
|---|---|---|---|---|---|
```

---

## Comparable Company Selection Principles

**Selection Criteria**: Same industry, same market, same scale (±50%), same business model, available data

**Quantity**: Standard 3-5, minimum 2, maximum 6

**Source**: iFind industry classification → 天眼查 competitors → Web Search

---

## Currency and Market Cap Unification Standard

**Mandatory Rules**:
1. **Market cap column must unify currency**. If comparable companies in different market than target company (e.g. target is Hong Kong stock, comparables are US/Japan/A股), must convert market cap to target company's market currency.
2. **Table header clearly annotates currency unit**. E.g.: `Market Cap (¥bn HKD)`, `Market Cap (¥bn USD)`, `Market Cap (¥bn RMB)`, not just `Market Cap`.
3. **Footnote explains exchange rate**. Add footnote below table, note conversion rate used (e.g. "*Foreign currency market cap converted to HKD per current rate, USD≈7.8HKD, JPY≈0.053HKD"*).
4. **PE/PB no conversion needed**, directly cite original values, but should footnote these comparative metrics from different accounting standards.

## Analysis Points

### Valuation Premium/Discount Analysis

```markdown
**Valuation Comparison Analysis**:
• Target company PE (TTM) is X.Xx, [higher/lower] than industry average Y.Yx, [premium/discount] Z%
• Target company PB is X.Xx, [higher/lower] than industry average Y.Yx

**Possible Reasons**:
• PE [premium/discount]: [Reason analysis]
• PB [premium/discount]: [Reason analysis]
```

---

## Competitive Landscape Analysis Framework

**This section provides analysis framework for "Industry Analysis" module right Box.**

**Module Adjacency Standard**:
- Industry analysis and comparable company valuation share unified module title `行业与估值对比`
- Industry analysis (with competitive landscape) positioned right Box (border-color: `#2E7D32`), side-by-side with left comparable company table
- Default dual-column parallel, not actively stacking

### Analysis Dimension

| Dimension | Content | Data Source |
|---|---|---|
| Market Concentration | CR3/CR5 market share, 3-year change trend | iFind industry data, Web Search |
| Pricing Power Assessment | Whether industry has leading price-setter, price increase transmission | Company financials, industry report |
| Entry Barriers | Capital/tech/license/brand barrier levels | Industry analysis |
| Competition Intensity | Price war frequency, gross margin trend, industry profit pool change | Comparable company financial data |
| Substitution Threat | New tech or new business model substitution risk | Web Search, industry report |

### Competitive Landscape Box Template

```markdown
**Competitive Landscape**

Market Concentration: CR3=[X]%, [concentrated/dispersed] market, past 3 years [concentration rising/declining]
• [Leader Company 1]: market share [X]%, [core advantage]
• [Leader Company 2]: market share [X]%, [core advantage]
• [Target Company]: market share [X]%, rank #[N]

Pricing Power: [Strong/Medium/Weak] — [Judgment basis, e.g. "industry leader can raise prices first and competitors follow"]

Entry Barriers: [High/Medium/Low]
• [Main barrier type]: [specific description]

Competition Trend: [Healthy competition/Intensifying/Consolidating]
• [Recent competitive landscape changes, e.g. "industry consolidation accelerating, tail enterprises exiting"]
```

---

## Data Sources (Mandatory — No Web Search Fallback for Price/Market Cap)

| Data Type | Primary Source | API | Fallback | Annotation Required |
|---|---|---|---|---|
| Comparable company list | iFind | Industry classification / `ifind_get_related_stock` | 天眼查 `competitor_info` | Source name |
| **Market cap & stock price** | **iFind** | **`ifind_get_stock_info`** | **Yahoo Finance `get_stock_info`** | **Data source + date + market** |
| **Revenue/Profit (TTM)** | **iFind** | **`ifind_get_stock_financial_index`** | **Yahoo Finance `get_financial_statement`** | **Reporting period (e.g., FY2024)** |
| **Valuation multiples** | **iFind** | **`ifind_get_stock_financial_index`** | **Yahoo Finance `get_stock_info`** | **Calculation date** |
| Competitors | 天眼查 | `tianyancha_api_call` | Web Search | Source name |

### ⚠️ HARD RULE: Comparable Company Data Must Use Same Source as Target Company

**The comparable company valuation table MUST use the same data source and reporting date as the target company's trading data table.** This ensures consistency in metrics, adjustment methodology, and timeliness.

**Data Source Routing by Market**:

| Target Company Market | Comparable Data Source | Ticker Format |
|----------------------|----------------------|---------------|
| A股 (SH/SZ/BJ) | iFind primary, Yahoo Finance cross-check | `XXXXXX.SH` / `XXXXXX.SZ` |
| HK stocks | iFind primary, Yahoo Finance cross-check | `XXXX.HK` |
| US stocks | Yahoo Finance primary, iFind cross-check | `AAPL`, `TSLA` (no suffix) |

**Cross-Market Comparable Handling**:
- If comparables are in a different market than the target company (e.g., HK-listed target with US-listed comps):
  1. Fetch each comp's data using **that comp's market-appropriate source**
  2. Convert market cap to target company's reporting currency using **current exchange rate**
  3. Footnote: "*Market cap converted to [target currency] at rate 1[comp]=X[target] as of [date]*"
  4. PE/PB/PS: cite original values (no conversion needed), footnote "*from different accounting standards*"

**Prohibited**:
- ❌ Using Web Search for market cap, stock price, or valuation multiples (stale/inconsistent data)
- ❌ Mixing data sources within the same table column (e.g., some comps from iFind, others from Web Search)
- ❌ Omitting data source annotation or reporting date

---

## Checklist

- [ ] 3-5 comparable companies, same industry same market same scale
- [ ] Target company highlighted (`.row-highlight`), industry average row italicized, no rating column
- [ ] Currency units unified, footnote explains exchange rate
- [ ] Exhibit number + data source annotation
- [ ] **All market cap/stock price/valuation data from iFind or Yahoo Finance (NOT Web Search)**
- [ ] **Data source and reporting date consistent with target company's trading data table**
