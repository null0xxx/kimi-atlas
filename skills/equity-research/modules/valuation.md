# Valuation + Catalyst Calendar Module Specification / 估值分析 + 催化剂日历模块规范

**Related File**: `modules/comparable.md` (Valuation Metric Selection Guide)

---

## Module Overview

**Module Position**: First page, below 公司概览 module

**Layout**: Left-Right Dual Box (default)
- Left Box: Valuation Analysis (border-color: `#1E3A5F`)
- Right Box: Catalyst Calendar (border-color: `#F57C00`)

---

## Left Box: Valuation Analysis

### Content Requirements

- Historical PE/PB trends
- Current valuation level
- Forecast valuation (if available)
- Comparison with industry average

### Table Structure

```markdown
| Metric | 2022A | 2023A | 2024A | 2025E | 2026E |
|---|---|---|---|---|---|
| PE (x) | 25.0 | 20.8 | 17.9 | 15.3 | 13.2 |
| PB (x) | 4.5 | 4.0 | 3.5 | 3.2 | 2.9 |
| PS (x) | 3.2 | 2.8 | 2.5 | 2.3 | 2.1 |
| EV/EBITDA | 18.5 | 16.2 | 14.5 | 13.0 | 11.8 |

*Data Source: iFind, as of YYYY-MM-DD*
```

**Valuation Metric Selection**: Select appropriate metrics per industry type, see `modules/comparable.md` valuation metric selection guide.

### Market Consensus Forecast Analysis (Must Include)

Below valuation table, add consensus forecast analysis paragraph. Data source: Phase 1 collected iFind forecast data.

```markdown
**Market Consensus Forecast**
• Core Forecast: [Analyst coverage count] institutions covering, consensus FY25E EPS [value] yuan, revenue [value] ¥bn
• Historical Valuation Review: Past 3 years PE declined from [2022A value]x to [2024A value]x, valuation center [risen/fallen/stable]
• Implicit Assumption: Consensus forecast implies revenue growth [X]%, net margin [Y]%, meaning market expects [key assumption]
• Revision Trend: Past 4 quarters EPS forecast [raised/lowered/stable], magnitude [X]%
  - [Most recent revision direction and reason]
• Valuation Fit: Current PE [X]x vs consensus forecast implicit growth [Y]%, PEG=[Z]
  - [Reasonable/Overvalued/Undervalued] judgment and basis
```

**Writing Requirements**:
1. Consensus forecast data must have specific sources and cutoff dates
2. Revision trend must distinguish direction (up vs down) and magnitude
3. Valuation fit requires giving PEG or other relative metric judgment

---

## Right Box: Catalyst Calendar

### Content Requirements

- Major events next 6 months (minimum 4)
- Event impact analysis
- Market expectations
- Data source annotations

### Catalyst Importance Levels

| Importance | Mark | Definition | Stock Impact |
|---|---|---|---|
| [Red Light] High | Must Include | Earnings release, major contracts, shareholder meeting | Possible 5-15% volatility |
| [Yellow Light] Medium | Recommended | Product launch, capacity expansion, industry policy | Possible 3-8% volatility |
| [Green Light] Low | Optional | Management changes, ESG rating, industry conference | Possible 1-3% volatility |

**Catalyst Selection Principles**:
1. Must include next earnings release (importance: high)
2. Include ≥2 high-importance events
3. Time distribution reasonable, cover next 6 months
4. Each event must have clear "impact analysis" and "market expectation"

### Table Structure

```markdown
| Date | Event | Importance | Impact Analysis | Market Expectation | Source |
|---|---|---|---|---|---|
| YYYY-MM-DD | Q1 Earnings Release | [Red Light] High | Market focuses on revenue growth | Expect revenue YoY +18%~22% | Earnings Calendar |
| YYYY-MM-DD | Shareholder Meeting | [Red Light] High | Watch dividend plan | Expect dividend payout 30%~40% | Company Announcement |
| YYYY-MM-DD | Half-year Report | [Red Light] High | Verify earnings realization | Expect net profit YoY +15%~20% | Earnings Calendar |
| YYYY-MM-DD | Industry Policy Release | [Yellow Light] Medium | Policy adjustment impact | Expect industry growth change | 财新 / Web Search |

*Data Source: Company Announcement, Exchange Earnings Calendar, 财新, Web Search*
```

### Impact Analysis Writing Requirements

- Explain core metrics market focuses on and expectations
- Analyze potential stock price impact direction from event
- Cite market consensus or analyst forecast
- Annotate data sources

### Typical Catalyst Event Types

**High Importance ([Red Light])**:
- Earnings release (Q1/Half/Q3/Full-year)
- Shareholder meeting (dividend plan)
- Major contracts/orders
- Merger integration
- Major capacity investment
- **Large-cap 解禁**
- **Important shareholder 增减持 announcement (e.g. Buffett reducing, major shareholder increasing)**

**Medium Importance ([Yellow Light])**:
- Product launch/upgrade
- Capacity expansion announcement
- Industry policy changes
- Major raw material price swings
- Competitive landscape changes
- **Directed equity offering/rights offering progress**
- **Share repurchase plan progress announcement**
- **北向资金 / main capital force phase anomaly (e.g. consecutive 7 days net outflow exceeding threshold)**

**Low Importance ([Green Light])**:
- Management changes
- ESG rating adjustment
- Industry conference/exhibition
- 解禁 reduction (already fully expected)
- Equity incentive award

---

## Data Sources

| Data Type | Data Source | API |
|---|---|---|
| Valuation metrics | iFind | `ifind_get_stock_financial_index` |
| Earnings forecast | iFind | `ifind_get_forecast` |
| Earnings calendar | Web Search | `[Company Name] earnings calendar` |
| Company announcement | iFind | `ifind_get_stock_announcement` |
| Industry policy | 财新 | `caixin_api_search` |

---

## Exhibit Numbering

Valuation module and catalyst calendar each need Exhibit number:

```html
<!-- Valuation table -->
<div class="exhibit-label">
  <span class="exhibit-number">Exhibit X:</span>
  <span class="exhibit-desc">Historical and Forecast Valuation Levels</span>
</div>

<!-- Catalyst calendar -->
<div class="exhibit-label">
  <span class="exhibit-number">Exhibit X:</span>
  <span class="exhibit-desc">Next 6 Month Catalyst Calendar</span>
</div>
```

---

## Checklist

- [ ] Valuation: Historical PE/PB complete, includes consensus forecast analysis (coverage, revision trend, fit)
- [ ] Catalyst: ≥4 events, includes next earnings, ≥2 high-importance
- [ ] Exhibit number + data source annotation
