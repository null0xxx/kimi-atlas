# Company Overview Module Specification / 公司概览模块规范

**Related**: `references/analysis-brief-template.md` §III (Company Overview — Business Model / Management / Ownership) and `references/research-document-template.md` §III (same section with expanded word counts for equity reports).

---

## Module Overview

**Module Position**: First page, below core data and market data module

**Layout**: Left-Right Dual Box (default)
- Left Box: Company Background + Business Model/Profit Model + Recent Tracking (border-color: `#6366F1`)
- Right Box: Business Structure Table + Core Business Analysis + Structure Analysis (border-color: `#1E90FF`)

---

## Left Box: Company Basic Information

### Content Requirements

- Use bullet point and text display, **don't use table**
- 3 core bullets, each one sentence
- Sub-bullets acceptable if needed (each ≤2 items)

### Structure Template

```markdown
<div class="snapshot-section-title">Company Background</div>
<div class="snapshot-content">
• [Founder] founded in [year] at [location], [brief development history], [listing status], is [industry position]
  <div class="snapshot-sub">Management: Reference Phase 2.2 management assessment conclusion (e.g.: "Management stable, CEO tenure X years, guidance realization rate >X%" or note governance risk)</div>
  <div class="snapshot-sub">Shareholding Structure: [Controlling shareholder/Major shareholder]+shareholding ratio+shareholding characteristic (e.g. "family control/state control/dispersed/AB shares/VIE structure"), important institutional shareholders if any</div>
</div>

<div class="snapshot-section-title">Business Model/Profit Model</div>
<div class="snapshot-content">
• Company positioned in [industry ecosystem position], provides [value proposition] to [customers] via [core capabilities/resources], profit from [revenue sources], core 护城河/competitive advantage is [specific barriers]
  <div class="snapshot-sub">Key Resources: [specific description, e.g. license/tech/network effects/scale efficiency]</div>
  <div class="snapshot-sub">Cost Structure: [main cost components and trends]</div>
</div>

<div class="snapshot-section-title">Recent Tracking</div>
<div class="snapshot-content">
• Recently company [important events/earnings highlights], [market reaction/impact], [future watch points]
  <div class="snapshot-sub">Financial Metrics: [key financial metric changes]</div>
  <div class="snapshot-sub">Important Announcement: [recent major announcements/news]</div>
</div>

<div class="data-source">iFind, as of YYYY-MM-DD</div>
```

### Writing Requirements

1. Each sentence controlled ≤50 words
2. Cover background, business model, recent status three dimensions
3. **Business Model bullet must answer**:
   - Mature company: what ecosystem position on value chain, how makes money, what competitive advantage/护城河?
   - Early/innovative company: Why business exist? (solving what pain point? Why now? Why you?)
4. Key data needs source annotation
5. Objective neutral, no subjective judgment and ratings

### English Version Variant

English version uses `.key-point` marker replacing Chinese bullet format:

```html
<div class="key-point">
  <span class="key-point-title">Company Background:</span> Founded in 1993 by Jensen Huang in Santa Clara, CA. Listed on NASDAQ in 1999. Global leader in GPU and AI chip design.
</div>
<div class="key-point">
  <span class="key-point-title">Business Model:</span> Monetizes through AI chip sales + software licensing via CUDA ecosystem. Moat: 20-year software stack and developer network effects.
</div>
<div class="key-point">
  <span class="key-point-title">Recent Developments:</span> FY2024 revenue up 126% YoY driven by data center AI demand; Q4 gross margin at 76.7%, a record high.
</div>
```

### Writing Examples

**[Tech Hardware Leader] (Mature Growth Example)**:
```html
<div class="snapshot-section-title">Company Background</div>
<div class="snapshot-content">
• Founder established company in 1990s, invented core technology, listed on major exchange, is global segment leader
  <div class="snapshot-sub">Management: Founder CEO for 30+ years, strategy execution strength extreme</div>
  <div class="snapshot-sub">Shareholding: Founder holds ~3.5%, institutional holds >70%, top two holders are major index funds, highly dispersed</div>
</div>

<div class="snapshot-section-title">Business Model/Profit Model</div>
<div class="snapshot-content">
• Positioned upstream compute infrastructure, provides compute foundation via "high-end hardware+proprietary software ecosystem" to cloud providers and enterprises, profits from chip sales and licensing, software ecosystem creates extremely high switching cost 护城河
  <div class="snapshot-sub">Core segment ~80% revenue, customer stickiness extreme</div>
</div>

<div class="snapshot-section-title">Recent Tracking</div>
<div class="snapshot-content">
• Latest FY revenue YoY +126%, core business doubled, demand sustained strong, market watches next-gen product launch
  <div class="snapshot-sub">Q4 gross margin 76.7%, all-time high</div>
</div>
```

**[E-commerce Platform] (Early Innovation Type Example)**:
```html
<div class="snapshot-section-title">Company Background</div>
<div class="snapshot-content">
• Founder established company in 2015, listed on major exchange 2018, became third-largest e-commerce platform in market
  <div class="snapshot-sub">Shareholding: Founder controls via VIE, founder team holds, AB share structure (B shares 10x voting)</div>
</div>

<div class="snapshot-section-title">Business Model/Profit Model</div>
<div class="snapshot-content">
• Solves down-market "plentiful, fast, cheap" shopping pain point, aggregates dispersed demand via C2M group-buying forming price advantage, profits from platform ads and transaction commission, social virality and low-price mindset form core barriers
  <div class="snapshot-sub">Social ecosystem traffic was early explosion key</div>
</div>

<div class="snapshot-section-title">Recent Tracking</div>
<div class="snapshot-content">
• 2023 revenue YoY +90%, Temu overseas expansion rapid, market watches US policy risk
</div>
```

---

## Right Box: Business Structure and Core Analysis

### Content Requirements

Right Box is business information aggregated display area, must include three parts:
1. **Business Structure Table** (mandatory)
2. **Core Business Description** (moved from original left Box)
3. **Structure Analysis** (supplement per whitespace availability, must have ≥1-2 points)

### Right Box Structure Template

```html
<div class="box box-accent">
  <div class="exhibit-label"><span class="exhibit-number">Exhibit X:</span> <span class="exhibit-desc">2024 Business Structure</span></div>
  
  <!-- 1. Business structure table -->
  <table class="report-table">
    <thead><tr><th>Business Segment</th><th>Revenue (¥bn)</th><th>Share (%)</th><th>YoY (%)</th><th>Gross Margin (%)</th></tr></thead>
    <tbody>
      <tr><td>Core Business A</td><td class="col-number">800</td><td class="col-number">53.3</td><td class="col-number">15.2</td><td class="col-number">35.0</td></tr>
      <tr><td>Core Business B</td><td class="col-number">450</td><td class="col-number">30.0</td><td class="col-number">8.5</td><td class="col-number">28.5</td></tr>
      <tr><td>Other Business</td><td class="col-number">50</td><td class="col-number">3.4</td><td class="col-number">5.0</td><td class="col-number">18.0</td></tr>
      <tr class="row-total"><td><b>Total</b></td><td class="col-number"><b>1,500</b></td><td class="col-number"><b>100.0</b></td><td class="col-number"><b>13.5</b></td><td class="col-number"><b>33.2</b></td></tr>
    </tbody>
  </table>

  <!-- 2. Core business description -->
  <div style="font-size:8.5pt;margin-top:4px;line-height:1.4;">
    <b>Core Business</b>: Company's main [core business], via [business model] provides [product/service] to [customer type], [core competitive advantage].
  </div>

  <!-- 3. Structure analysis (balance left-right Box height, must supplement) -->
  <div style="font-size:8.5pt;margin-top:4px;line-height:1.4;">
    <b>Structure Analysis</b>:
    • [Segment growth rate]: Core segment past 3 years CAGR ~X%, main growth engine; XX business contributes stable cash flow.<br>
    • [Geographic breakdown if any]: Domestic revenue ~X% share, overseas revenue share rose from X% to X%, [key region] fastest growth.<br>
    • [Business trend/customer structure optional]: High value-add product ratio rising / customer concentration changes / channel structure changes.
  </div>
  <div class="data-source">iFind, 2024 Annual Report</div>
</div>
```

### Right Box Writing Requirements

1. Table must include total row, shares sum to 100%
2. **Core Business Description**: 1-2 sentences summarizing how company makes money, serves whom, what competitive advantage (original left Box 2nd bullet content)
3. **Structure Analysis**:
   - When left content abundant, right table small leaving blank, must supplement structure analysis paragraph filling blank
   - Cover "segment growth rate" + "geographic/customer/channel structure" at least one dimension
   - Use short bullets or line breaks, maintain compact (8.5pt font)
4. All data annotated source

### Table Structure Standard

```markdown
| Business Segment | Revenue (¥bn) | Share (%) | YoY (%) | Gross Margin (%) |
|---|---|---|---|---|
| Core Business A | 800 | 53.3 | 15.2 | 35.0 |
| Core Business B | 450 | 30.0 | 8.5 | 28.5 |
| Other Business | 50 | 3.4 | 5.0 | 18.0 |
| **Total** | **1,500** | **100.0** | **13.5** | **33.2** |

*Data Source: iFind, 2024 Annual Report*
```

---

## Data Sources

| Data Type | Data Source | API |
|---|---|---|
| Company basic info | iFind | `ifind_get_stock_info` |
| Shareholding (Chinese) | 天眼查 | `tianyancha_api_call(api_name='shareholder_info')` |
| Shareholding (Non-Chinese) | Company annual report/SEC EDGAR/Official IR | Web Search |
| Business segmentation | iFind | `ifind_get_stock_business_segmentation` |
| Financial data | iFind | `ifind_get_financial_statements` |
| Recent news | Web Search | - |

---

## Checklist

- [ ] Left: 3 bullets complete, each ≤50 words, include management+shareholding sub-bullet
- [ ] Right: Business table complete (total row correct), includes core business description+structure analysis
- [ ] Data source annotation
