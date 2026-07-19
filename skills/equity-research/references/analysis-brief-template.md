# Investment Analysis Brief Template (Tear Sheet Handoff)

> **Which mode uses this file?**
> - **TEAR_SHEET**: This is the primary handoff document from Phase 3 → Phase 4 (single session).
> - **EQUITY_REPORT**: Do **NOT** use this file. Equity reports use `references/research-document-template.md` instead, which feeds into the 3-Task architecture. All equity-report content — including deeper narratives, cross-method valuation synthesis, scenario deep-dives, and extended risk tables — now lives in that single template.

This file defines the structured analysis output format for **tear sheet mode**. After Phase 3 completion, the agent writes analysis conclusions into `{company}_{ticker}_analysis_brief.md` following this template. This document is the **sole interface** between Phase 2-3 (analysis engine) and Phase 4-5 (presentation layer).

**The analysis brief is the analytical foundation, not a summary.** Every claim, number, and insight in the final tear sheet must trace back to content in this brief. If something isn't in the brief, it won't appear in the report. **If the brief is thin, the tear sheet will be thin.** A tear sheet is compact but still has to stand up to institutional scrutiny — brief content quality determines report credibility.

---

## Section Index

> **This is a tear-sheet-only template.** The table below lists every section, the minimum word count per section, and what it drives in the final PDF. Use it as a quick reference while writing.

| Section | Target Length | What it drives in Phase 4 PDF |
|---------|--------------|-------------------------------|
| **§I Core Narrative** | 5-8 sentences (**150-250 words**) | Cover-page "Core Viewpoint" paragraph |
| **§II Six-Dimension Summary** | ~80-120 words per dimension (**480-720 total**) | Page 1 dimension boxes + any deep-dive box |
| **§III Dimension → Module Mapping** | Table only | Phase 4 uses this to decide module positioning |
| **§IV Thesis Table** | Each cell 2-3 sentences (**40-80 words** per bull/bear) | Debate/Thesis module |
| **§V Financials** | Table + 2-3 sentence commentary | Key Financials module |
| **§VI Valuation Comparison** | Table + 30-50 word judgment per row | Valuation module |
| **§VII Catalyst Calendar** | ≥4 events with dates | Catalyst module |
| **§VIII Scenario Analysis** | Table + 25-50 word key assumption per scenario | Scenario module |
| **§IX Risks** | 4-6 risks, 30-60 words each (with trigger) | Risk Disclosure module |
| **§X Information Sources** | Table only | Footer / audit trail |
| **Total brief word count** | **≥2,500 words** (target 2,500-3,500) | Ensures every module has real substance |

> **Why these lengths are mandatory**: Tear sheets are visually compact — that tempts agents to write compact analysis too. But the PDF is only compact because the layout compresses dense text; the underlying analysis still needs institutional-grade depth. A thesis row written in 10 words produces a "so what" blank stare from a reader; the same row written in 60 words with a turning-point signal reads like a buy-side analyst wrote it.

---

## File Naming

```
{company}_{ticker}_analysis_brief.md
```

Example: `{Company}_{Ticker}_analysis_brief.md`

---

## Template Structure

```markdown
# {Company Name} ({ticker}) Investment Analysis Brief

> Generation Date: YYYY-MM-DD
> Output Mode: TEAR_SHEET
> Data Cutoff: YYYY-MM-DD
> Markets: [A-shares / HK / US]
> Language: [Chinese / English]

## Metadata

> This metadata is consumed by Phase 4 (same session) for layout generation.
> The agent MUST fill every field below. Phase 4 MUST NOT proceed if any field is missing.

| Field | Value |
|-------|-------|
| `output_type` | TEAR_SHEET |
| `report_language` | [zh-CN / en] |
| `css_container_class` | [`.report-container` / `.report-container report-container-en`] |
| `market` | [A-share / HK / US] |
| `ticker` | [e.g., AAPL, 600519.SH, 0700.HK] |
| `company_name` | [Full company name] |
| `company_name_en` | [English name, if bilingual] |
| `page_target` | [3-5] |
| `benchmark_index` | [e.g., ^GSPC, 000001.SH] |
| `benchmark_name` | [e.g., S&P 500, 上证指数] |
| `module_count` | 11 (all mandatory for tear sheet) |
| `stock_chart_path` | [Relative path to pre-generated stock chart SVG] |
| `stock_csv_path` | [Relative path to stock price CSV] |
| `benchmark_csv_path` | [Relative path to benchmark CSV] |
| `report_date` | [YYYY-MM-DD] |
| `latest_financial_report` | [e.g., "FY2025 Q3" or "2024 Annual Report"] |
| `current_price` | [e.g., $198.50 or ¥1,850.00] |
| `rating` | [BUY / HOLD / SELL / NOT RATED] |
| `target_price` | [e.g., $220.00 or ¥2,100.00, or "N/A" if not rated] |

### Supply Chain Structure (for Mermaid Rendering)

> Phase 4 needs this to render the supply chain diagram without re-reading `modules/industry-chain.md`.

```mermaid
[Paste the complete Mermaid flowchart code here — Phase 2.1 designs the supply chain
and records it here. Phase 4 renders it to SVG.]
```

---

## I. Core Investment Narrative

> **Length: 5-8 sentences, 150-250 words.** This paragraph becomes the cover-page "Core Viewpoint" — it's the single most-read piece of the tear sheet.

Structure the paragraph to cover:
- **Industry context** (1-2 sentences): the secular trend the company rides or resists
- **Company position** (1-2 sentences): differentiated advantage with one concrete proof point (market share, margin spread, product milestone)
- **Financial trajectory** (1 sentence): direction of revenue/margin/FCF in the most recent period, with the number
- **Valuation judgment** (1 sentence): cheap / fair / expensive vs history AND peers (name both anchors)
- **Principal risk** (1 sentence): the single biggest reason you could be wrong

Avoid: adjectives without data ("strong growth"), vague time references ("recently"), unquantified claims ("leading player").

---

## II. Six-Dimension Deep Analysis Summary

> **Length per dimension: 3-5 data bullets + a 3-5 sentence Assessment paragraph + a So-What line. Target 80-120 words per dimension, ~480-720 words across §II total.**

### 2.1 Competitive Landscape (H1)

**Conclusion**: [One-sentence verdict: is the company winning or losing ground?]

**Key Data Support**:
- Market share: [Company]'s share is X% (vs. Y% 3 years ago), indicating [gaining/losing/stable]
- CR3/CR5 concentration: [X%], trend is [consolidating/fragmenting]
- Pricing power indicator: [gross margin trend, ASP trend, or pass-through ability]

**Competitive Moat Assessment** (3-5 sentences, 80-120 words): Identify the moat type (brand / scale / network / switching cost / intangible), give at least one specific piece of evidence (e.g., "contract length averages 4.2 years vs. peers at 1.8"), assess durability (5-year view: strengthening / eroding / stable), and flag any single threat that could compress it. Do not write generic "strong brand moat" — name the mechanism.

**So What for Report**: [How this dimension shapes the investment thesis — e.g., "Dominant market position supports premium valuation, but share erosion from [competitor] limits upside"]

### 2.2 Growth Drivers (H2)

**Conclusion**: [One-sentence verdict: is growth accelerating, decelerating, or inflecting?]

**Key Data Support**:
- Revenue CAGR (3Y): X%, (next 2Y consensus): Y%
- Primary growth driver: [product cycle / geographic expansion / pricing / M&A]
- Secondary driver: [quantify contribution]

**Growth Sustainability Assessment** (3-5 sentences, 80-120 words): How much TAM whitespace remains (penetration % today)? Is growth coming from volume, price, or mix? What's the management execution track record (2-3 recent guidance vs. actuals)? Flag any single factor that could break the trajectory.

**So What for Report**: [How growth trajectory affects target price and scenario probabilities]

### 2.3 Earnings Quality (H3)

**Conclusion**: [One-sentence verdict on earnings reliability]

**Key Data Support**:
- OCF/Net Income ratio: X (>1.0 = high quality, <0.7 = concern)
- Non-recurring items: [quantify if material]
- Working capital trends: [receivables growing faster than revenue? inventory build?]

**Anomaly Flags** (3-5 sentences, 80-120 words, or "No material anomalies" + 1 sentence why): Any data points deviating from historical patterns? Examples: "DSO expanded 15 days YoY despite flat revenue — suggesting channel stuffing or collection deterioration." If no anomalies, state so and explain which metrics you specifically checked.

**So What for Report**: [How earnings quality affects reliability of projections]

### 2.4 Valuation & Expectations (H4)

**Conclusion**: [One-sentence: cheap, fair, or expensive vs history and peers?]

**Key Data Support**:
- Current PE: X vs. 5Y avg: Y vs. peer median: Z
- Forward PE: X vs. consensus growth: Y% → PEG: Z
- Where consensus may be wrong: [identify the gap between market pricing and your analysis]

**Market Expectation Gap** (3-5 sentences, 80-120 words): What specifically is the market pricing in (revenue growth, margin)? Where does your analysis disagree? What catalyst could close the gap, and on what timeline? This is where alpha thinking happens — if you can't identify a mispricing, say so honestly.

**So What for Report**: [Direct implication for target price range]

### 2.5 Geopolitics/Policy (H5)

**Conclusion**: [One-sentence: net positive, neutral, or negative policy environment?]

**Key Data Support**:
- Specific policy/regulatory developments: [name them with dates]
- Tariff/trade exposure: [quantify if relevant]
- Subsidy/incentive programs: [quantify if relevant]

**So What for Report** (2-3 sentences, 40-80 words): [How policy shapes risk/reward — e.g., "Subsidy phase-out by 2026 creates margin headwind worth ~200bps; partial offset from domestic procurement rules worth ~80bps net. Net negative in the near term."]

### 2.6 Technology/Product Cycle (H6)

**Conclusion**: [One-sentence: where in the product cycle? early/mid/late?]

**Key Data Support**:
- Key product launch timeline: [specific dates and products]
- R&D spend: X% of revenue (vs. peers: Y%)
- Technology moat indicators: [patents, first-mover advantage, switching costs]

**So What for Report** (2-3 sentences, 40-80 words): [Product cycle timing affects near-term revenue visibility — specify which product cycle, expected peak, and what comes next.]

---

## III. Six-Dimension Conclusion → Report Module Mapping

| Six-Dimension Conclusion | Core Viewpoint | Corresponding Report Module |
|--------------------------|----------------|----------------------------|
| One-line judgment | [Conclusion] | Report title, Company Overview |
| Market Pricing | [Conclusion] | Valuation module |
| Market Error / Mispricing | [Conclusion] | Investment Logic (bull/bear) |
| Key Variables to Watch | [Conclusion] | Catalyst calendar, scenario analysis |
| Primary Contradiction | [Conclusion] | Investment thesis table (competitive landscape row) |
| Anomaly Signals | [Conclusion] | Earnings quality, risk disclosure, financial analysis |

---

## IV. Investment Thesis Comprehensive Analysis Table

> **Length: Every `Bull Arguments` and `Bear Arguments` cell must be 2-3 sentences (40-80 words) with at least one number or named piece of evidence. A one-phrase entry like "dominant market position" is NOT acceptable.**

| Dimension | Bull Arguments | Bear Arguments | Key Assumptions | Turning Point Signal | Our Judgment |
|-----------|----------------|----------------|------------------|----------------------|--------------|
| Competitive Landscape | [40-80 words with specific data] | [40-80 words with specific counter-data] | [What must be true — 15-30 words] | [Observable signal that would flip the verdict — 15-30 words] | [Net assessment + why — 20-40 words] |
| Growth Drivers | [40-80 words] | [40-80 words] | [15-30 words] | [15-30 words] | [20-40 words] |
| Earnings Quality | [40-80 words] | [40-80 words] | [15-30 words] | [15-30 words] | [20-40 words] |
| Valuation & Expectations | [40-80 words] | [40-80 words] | [15-30 words] | [15-30 words] | [20-40 words] |

> **Why the word counts matter here**: This table is the intellectual heart of the tear sheet. A reader scanning this in 30 seconds needs to understand both sides of every debate. If your bull cell is "dominant share" and your bear cell is "margin pressure", the reader learns nothing. If your bull is "~38% NA market share (up from 31% in FY22), supported by 18-mo customer lock-in contracts averaging 4.2Y duration" and your bear is "price discounting at top-5 accounts compressed gross margin 180bps YoY as AWS and GCP re-engaged aggressively", the reader immediately has testable claims.

---

## V. Key Financial Data At-a-Glance

| Metric | Latest Value | YoY Change | QoQ Change | Data Source | Note |
|--------|-------------|------------|------------|-------------|------|
| Revenue (TTM) | | | | | |
| Net Income (TTM) | | | | | |
| Gross Margin | | | | | Trend: [expanding/compressing/stable] |
| Operating Margin | | | | | |
| Net Margin | | | | | |
| ROE | | | | | DuPont: [margin/turnover/leverage driven] |
| Operating Cash Flow | | | | | |
| Free Cash Flow | | | | | FCF yield: X% |
| Net Debt/Equity | | | | | |
| Revenue per Employee | | | | | [Only if meaningful] |

**Financial Snapshot Commentary** (2-3 sentences, 40-80 words): Summarize the "shape" of the financials — is this a margin-expansion story, an FCF story, or a balance-sheet-deleveraging story? One sentence on the most important recent inflection (up or down).

---

## VI. Valuation Comparison

> **Length: Every filled row's `Judgment` column must have a 30-50 word explanation, not just "expensive" or "fair".**

| Valuation Method | Current | 5Y Historical Avg | 5Y Historical Median | Industry/Peer Avg | Premium/Discount | Judgment |
|------------------|---------|-------------------|---------------------|-------------------|-----------------|----------|
| PE(TTM) | | | | | | [30-50 words: cheap/fair/expensive + vs-which-anchor + why] |
| Forward PE (NTM) | | | | | | [30-50 words] |
| PB | | | | | | [30-50 words, only if meaningful for this sector] |
| PS | | | | | | [30-50 words, include only if company has low/negative earnings] |
| EV/EBITDA | | | | | | [30-50 words] |
| PEG | | | | | | [30-50 words, include only if growth is a core thesis] |
| FCF Yield | | | | | | [30-50 words, only if FCF is stable enough to anchor valuation] |

**Cross-Method Takeaway** (2-3 sentences, 40-80 words): Do the methods agree? If they diverge, name which method you weight most heavily for this company and why (e.g., "EV/EBITDA is the right anchor given CapEx-heavy profile; PE distorted by non-cash amortization").

---

## VII. Catalyst Calendar

| Date | Event | Impact Direction | Importance | Expected Reaction |
|------|-------|------------------|------------|-------------------|
| YYYY-MM-DD | [Next earnings report] | [Bull/Bear/Neutral] | High | [What market is pricing; how result could surprise] |
| YYYY-MM-DD | [Product launch / event] | | | |
| YYYY-MM-DD | [Regulatory / policy event] | | | |
| YYYY-MM-DD | [Industry conference / data release] | | | |

Minimum: 4 events. At least 1 must be the next earnings report. At least 2 must be "High" importance.

---

## VIII. Scenario Analysis

> **Length: Every scenario's `Key Assumptions` cell must be 25-50 words — specific and testable (not "strong macro"). The `Trigger Conditions` cell must name an observable signal, 15-30 words.**

| Scenario | Probability | Revenue | Net Income | EPS | Target Price | Key Assumptions | Trigger Conditions |
|----------|-------------|---------|------------|-----|-------------|-----------------|-------------------|
| Bull | XX% | | | | | [25-50 words] | [15-30 words — observable signal] |
| Base | XX% | | | | | [25-50 words] | [15-30 words — default path] |
| Bear | XX% | | | | | [25-50 words] | [15-30 words — observable signal] |

**Rules**: Bull + Base + Bear = 100%. Base probability: 45-60%.

**Probability-Weighted Target**: Σ(probability × target price) = ¥/$ XX (compute this explicitly — it anchors the headline rating).

---

## IX. Main Risk List

> **Length: 4-6 risks. Each risk entry must be 30-60 words and include: what specifically goes wrong, the financial/operational mechanism, an observable trigger/early warning, and an Impact × Probability tag.**

1. **Risk Name**: [30-60 words covering: the mechanism of harm, the financial/operational channel, one observable early-warning signal, and the scale of impact if it materializes] — Impact: High/Medium/Low — Probability: High/Medium/Low
2. ...
3. ...
4. ...

> **Why longer risk lines matter**: A one-line risk like "customer concentration" is untestable — the reader can't know what to watch for. A 40-word version ("Top-3 customers are 46% of revenue; largest customer's contract expires Q2 2026 and is entering re-negotiation with competing bids from [peer]; DSO extension >15 days would be the early warning") gives the reader everything they need to monitor the risk.

---

## X. Information Sources

| Data Type | Source | Retrieval Date | Reliability Note |
|-----------|--------|----------------|-----------------|
| Stock Price Data | [iFind / Yahoo Finance] | | |
| Financial Statements | [iFind / Yahoo Finance] | | [Reporting period: YYYY-MM-DD] |
| Earnings Forecasts | [iFind consensus] | | [# analysts in consensus] |
| Industry Data | [Source name] | | |
| Company Announcements | [Source] | | |
| News / Real-time Events | [Source] | | [Recency: within X days] |
```

---

## Content Quality Gate

Before Phase 4 begins, the agent must self-check the analysis brief against these minimum standards. If any check fails, return to Phase 2/3 to fill the gap — do NOT proceed to Phase 4 with a thin brief.

- [ ] **§I Core Narrative**: 5-8 sentences, 150-250 words, covering all 5 elements (industry → company → financials → valuation → risk)
- [ ] **§II Each H-dimension**: 3-5 data bullets + assessment paragraph (3-5 sentences, 80-120 words) + So-What; total ≥480 words across all 6 dimensions
- [ ] **§IV Thesis Table**: All 4 rows have bull AND bear cells at 40-80 words each with at least one named number or evidence; key assumption and turning point cells filled (15-30 words)
- [ ] **§V Financials**: All 10 metrics filled with actual data (no placeholders); financial snapshot commentary included (40-80 words)
- [ ] **§VI Valuation**: Each filled row has a 30-50 word judgment; cross-method takeaway present (40-80 words)
- [ ] **§VII Catalysts**: ≥4 events with specific dates (≥1 earnings, ≥2 High importance)
- [ ] **§VIII Scenarios**: All 3 rows have specific numbers; key assumptions at 25-50 words; triggers at 15-30 words; probability-weighted target computed
- [ ] **§IX Risks**: 4-6 risks, each 30-60 words with mechanism + trigger + impact × probability tags
- [ ] **Total word count**: ≥2,500 words (target range 2,500-3,500)

**If any check fails**: Return to Phase 2/3 to fill the gap. Do NOT proceed to Phase 4 with an incomplete brief. A compact-looking PDF still needs institutional-depth analysis underneath — the layout compresses the text, not the thinking.

---

## Usage Instructions

1. **This file is a template**; the agent fills actual analysis content per this structure after Phase 3 completion.
2. **MANDATORY generation**: The analysis brief is always generated (it's the handoff to Phase 4). The choice of whether to deliver it to the user is separate.
3. **Output Location**: Same directory as final PDF.
4. **Metadata**: The metadata table is used by Phase 4 to set up report parameters. All fields must be filled.
5. **Supply Chain Structure**: The Mermaid code block in the metadata section must contain the complete flowchart designed during Phase 2.1. This allows Phase 4 to render it without re-reading `modules/industry-chain.md`.
6. **Delivery rules**:

| User Request | Delivery Behavior |
|-------------|------------------|
| Default (no special request) | Generate brief internally, continue to Phase 4 → Phase 5 → PDF (single session). |
| "分析过程" / "analysis brief" / "中间成果" | Deliver brief to user, then continue to Phase 4. |
| "只要分析" / "analysis only" | Deliver brief to user, SKIP Phase 4-5. |

> **For EQUITY_REPORT mode**: This template is not involved. The research document template (`references/research-document-template.md`) holds the equivalent Task 1 handoff for equity reports.
