# Research Document Template (Task 1 Output — Equity Report)

> **Which mode uses this file?**
> - **EQUITY_REPORT**: This is the single handoff document from Task 1 to Task 2/3. Both L1 (2-Task) and L2 (3-Task) variants use this template.
> - **TEAR_SHEET**: Do NOT use this file. Tear sheets use `references/analysis-brief-template.md`.

After completing Phase 0-3 of Task 1, the agent writes all findings into `{Company}_{Ticker}_Research_Document_{Date}.md`. This document is the **primary input to Task 2** (Financial Model + Valuation in L2) and **Task 3** (Report Generation in both L1 and L2).

**The research document is the analytical foundation of a ≥25-page equity report.** Every paragraph, table, and chart in the final PDF traces back to content here. If it isn't in the research document, it won't — and shouldn't — appear in the report. **A thin research document produces a thin report.**

---

## Design Principles

1. **Research document ≠ final report.** It's a structured data repository plus fully-written analytical prose, not a formatted presentation.
2. **Every claim needs data.** No unsupported assertions. Every statement backed by a number, source, or named piece of evidence.
3. **Task 2 extracts financial data from this document** to build the Excel model. So §VI and §VII must contain actual numbers, not vague descriptions.
4. **Task 3 extracts narrative from this document** to populate report sections. So §I–§V, §VIII, §X, and §XIII must contain fully-written analysis paragraphs, not bullet outlines.
5. **Word counts are minimums, not targets.** The ranges below are the floor that keeps each section genuinely analytical. Going longer when the company warrants it is encouraged.

---

## File Naming

```
{Company}_{Ticker}_Research_Document_{Date}.md
```

Example: `{Company}_{Ticker}_Research_Document_{Date}.md`

---

## Template

```markdown
# {Company Name} ({Ticker}) Research Document

> Generation Date: YYYY-MM-DD
> Data Cutoff: YYYY-MM-DD (latest data used)
> Market: [A-share / HK / US]
> Language: [Chinese / English]

---

## Task Handoff Metadata

> Task 2 and Task 3 read this section to recover all parameters.

| Field | Value |
|-------|-------|
| `output_type` | EQUITY_REPORT |
| `report_language` | [zh-CN / en] |
| `css_container_class` | [`.report-container` / `.report-container report-container-en`] |
| `market` | [A-share / HK / US] |
| `ticker` | [e.g., AAPL, 600519.SH, 0700.HK] |
| `company_name` | [Full company name] |
| `company_name_en` | [English name] |
| `currency` | [USD / CNY / HKD] |
| `page_target` | [e.g., 25-40] |
| `benchmark_index` | [e.g., ^GSPC, 000001.SH] |
| `benchmark_name` | [e.g., S&P 500, 上证指数] |
| `module_count` | 21 (all mandatory) |
| `stock_chart_path` | [Relative path to pre-generated stock chart SVG] |
| `stock_csv_path` | [Relative path to stock price CSV] |
| `benchmark_csv_path` | [Relative path to benchmark CSV] |
| `report_date` | [YYYY-MM-DD] |
| `latest_financial_report` | [e.g., "FY2025 Q3" or "2024 Annual Report"] |
| `current_price` | [e.g., $198.50 or ¥1,850.00] |

---

## I. Core Investment Narrative (400-600 words)

> **This is the single most-read paragraph in the entire report.** Task 3 uses it as the cover-page viewpoint and the opening of the executive summary. A thin narrative here translates to a weak report opening.

[15-22 sentences forming a complete investment thesis. Expand beyond simple one-sentence points — each element should have one sentence that states the position and a second sentence that cites a concrete piece of evidence. Structure:
- **Industry context and secular trend** (2-3 sentences): Name the trend, quantify it (TAM growth rate, adoption curve position), and note where the company sits in that trend.
- **Company's differentiated position** (2-3 sentences): Describe the competitive advantage with one named mechanism (scale, network, IP, switching cost) and one supporting data point (market share, margin spread vs peers).
- **Recent financial trajectory** (2-3 sentences): Most recent period's revenue/margin/FCF direction with numbers. Include one-sentence explanation of what's driving it.
- **Valuation assessment** (2-3 sentences): Cheap / fair / expensive vs BOTH history AND peers; name specific anchors (e.g., "trading at 18x forward vs 5Y avg 23x and peer median 21x").
- **Key catalysts and timeline** (2-3 sentences): Name 2-3 catalysts with specific dates or event triggers.
- **Principal risks** (2-3 sentences): The 1-2 biggest reasons the thesis could break, with observable early-warning signals.
- **Bottom-line rating rationale** (1 sentence): Tie it together with an overall rating conclusion.]

---

## II. Six-Dimension Deep Analysis (1,500-2,400 words total)

### 2.1 Competitive Landscape (H1) — 250-400 words

**Conclusion**: [One-sentence verdict]

**Data Support**:
- Market share: [X]% (vs [Y]% 3 years ago)
- CR3/CR5: [X]%, trend: [consolidating/fragmenting]
- Pricing power: [evidence]

**Competitive Moat** (2-3 full paragraphs, 150-250 words): Identify the moat type (brand / scale / network / switching cost / intangible), give 2-3 specific pieces of evidence (e.g., contract length, switching cost data, patent moat), assess durability over a 5-year horizon, and explicitly call out any single mechanism that could erode it. Avoid generic language — name the specific mechanism by which the moat translates into pricing power or share defensibility.

**So What** (40-80 words): How this dimension shapes the investment thesis — name target-price impact and scenario weighting consequence.

### 2.2 Growth Drivers (H2) — 250-400 words

**Conclusion**: [One-sentence verdict]

**Data Support**:
- Revenue CAGR (3Y): X%, consensus (2Y forward): Y%
- Primary driver: [with quantification]
- Secondary driver: [with quantification]

**Sustainability** (2-3 full paragraphs, 150-250 words): TAM remaining (today's penetration %, S-curve position), volume vs. price vs. mix decomposition of historical growth, competitive risk to growth (peer encroachment, new entrants), management execution track record (cite 2-3 recent guidance vs. actuals comparisons), and one explicit factor that could break the growth trajectory.

**So What** (40-80 words): Implication for target price, scenario probability weighting, and which catalysts to watch for trajectory confirmation.

### 2.3 Earnings Quality (H3) — 250-400 words

**Conclusion**: [One-sentence verdict]

**Data Support**:
- OCF/Net Income: X
- Non-recurring items: [quantify]
- Working capital: [DSO/DIO/DPO trends]

**Anomaly Flags** (2-3 paragraphs, 150-250 words): Walk through the working capital signals (DSO/DIO/DPO trend), one-off items in the last 8 quarters (with quantification), accounting policy comparisons vs. peers, and revenue recognition red flags. If no anomalies exist, state that explicitly and list which checks you ran. Reader should be able to tell exactly what was investigated.

**So What** (40-80 words): Impact on projection reliability and confidence band of any forecasts the report will publish.

### 2.4 Valuation & Expectations (H4) — 250-400 words

**Conclusion**: [Cheap/fair/expensive vs history and peers]

**Data Support**:
- PE(TTM): X vs 5Y avg: Y vs peer median: Z
- Forward PE: X, PEG: Y
- Consensus gap: [where market may be wrong]

**Expectation Gap** (2-3 paragraphs, 150-250 words): What is the market explicitly pricing in (revenue growth, margin level, terminal multiple)? Where do you disagree with consensus and by how much? Which 1-2 catalysts could close the gap, and on what timeline? This is the alpha-thinking section — if you cannot identify a mispricing, say so honestly and frame as "fairly valued, neutral rating".

**So What** (40-80 words): Direct implication for target price range and recommended action.

### 2.5 Geopolitics/Policy (H5) — 250-400 words

**Conclusion**: [Net positive/neutral/negative]

**Data Support**:
- Specific policies: [with dates]
- Tariff/trade: [quantify if relevant]
- Subsidies: [quantify if relevant]

**Policy Impact Analysis** (1-2 paragraphs, 100-200 words): For each material policy item, quantify the financial impact (revenue/margin/CapEx in absolute terms), name the mechanism, and give a probability-weighted view if the policy outcome is uncertain. Distinguish near-term (12 mo) from medium-term (12-36 mo) impacts.

**So What** (40-80 words): How policy shapes risk/reward; what scenario weighting changes; what regulatory milestones to watch.

### 2.6 Technology/Product Cycle (H6) — 250-400 words

**Conclusion**: [Early/mid/late cycle]

**Data Support**:
- Product launches: [dates and products]
- R&D: X% of revenue (vs peers: Y%)
- Tech moat: [patents, first-mover, switching costs]

**Cycle Position & Pipeline** (1-2 paragraphs, 100-200 words): Where in the cycle is the current flagship product (years to peak, years to decline)? What's in the pipeline and on what timeline? How does R&D efficiency compare to peers (revenue per R&D dollar over 5 years)? Name one specific tech-cycle risk and what would signal it materializing.

**So What** (40-80 words): How product cycle timing affects near-term revenue visibility and FY+1/+2 estimates.

---

## III. Company Overview (1,200-1,800 words)

### Background & History (300-450 words)
[Founding story, listing history, 4-6 major strategic milestones with dates, any M&A / spin-offs / restructurings. Include one paragraph on how the company arrived at its current positioning — what decisions shaped the business model.]

### Business Model (300-450 words)
[Value proposition, revenue model (subscription / transaction / product sale / hybrid), unit economics framework (revenue per unit × number of units), cost structure (fixed vs variable split), operating leverage pattern. Name 2-3 business-model risks that are specific to this company's structure — e.g., customer concentration mechanics, capacity utilization sensitivity.]

### Management & Governance (300-450 words)
[Key executives with 3-4 sentence bios focusing on relevant track record, not just title history. Management quality assessment: guidance accuracy history (compare last 4-6 guidance points to actuals), capital allocation decisions (buybacks / dividends / M&A with IRR evidence where computable), succession risk, compensation alignment (skin in the game, LTIP structure). Flag any recent executive departures or insider-trading patterns.]

### Ownership Structure (200-300 words)
[Top 5-10 shareholders with % ownership, institutional vs. insider vs. retail split, recent insider buying/selling activity (last 6 months), any voting-rights structure anomalies (dual-class shares, strategic stakes). Note presence of activist investors or sovereign holders if relevant.]

---

## IV. Industry & Competitive Landscape (1,500-2,200 words)

> **This is the most differentiated value in an equity report vs. a tear sheet.** Depth here is what separates institutional-grade research from a retail summary. Do not compress this section.

### Industry Overview (450-650 words)
[Market size and growth rate with named source. Regulatory environment (recent 24 months + expected next 12 months). 3-4 key secular trends with quantification. Industry profitability structure (where the money is made — upstream, midstream, downstream). Cycle position (early/mid/late) with indicators. Any structural shifts underway (consolidation, disintermediation, technology disruption) with evidence.]

### TAM/SAM/SOM

| Level | Size | Growth (CAGR) | Source |
|-------|------|---------------|--------|
| TAM | $XXB | X% | [Source] |
| SAM | $XXB | X% | [Source] |
| SOM (current) | $XXB | — | Company data |
| Penetration | X% of SAM | | |

**Market Opportunity Narrative** (200-350 words): Walk the reader through the TAM → SAM → SOM logic. Name 2-3 specific drivers of TAM expansion. Identify whitespace (what portion of the SAM is unpenetrated?) and S-curve position (how fast is adoption accelerating or decelerating?). Flag any reasons the TAM estimate could be wrong (methodological issues, time-period sensitivity).

### Competitive Landscape

| Competitor | Revenue | Market Share | Key Advantage | Key Weakness | Threat Level |
|-----------|---------|-------------|---------------|--------------|-------------|
| [5-8 competitors with data] | | | | | |

**Competitive Positioning Analysis** (350-500 words): Describe the 2 most important axes of competition in this industry (e.g., price vs. performance, scale vs. specialization). Position the target company and its top 3-4 peers on these axes with named evidence. Explain the basis of rivalry — are competitors converging or diverging? Is the industry heading toward consolidation, commoditization, or specialization? Call out 1-2 "dark horse" emerging competitors not yet on the main leaderboard.

### Entry Barriers & Pricing Power (200-300 words)
[Barrier types and strength — capital requirements, regulatory approval, scale economies, network effects, brand, IP. Quantify where possible (e.g., "capital cost to enter at scale ≈ $2B"). Pricing power evidence: historical ability to pass through cost inflation, customer concentration constraints on pricing. Name one area where pricing power is weaker than investors assume.]

---

## V. Supply Chain Structure (400-600 words combined for upstream + downstream)

### Mermaid Code (for Task 3 rendering)

```mermaid
[Complete Mermaid flowchart code for supply chain diagram]
```

### Upstream Analysis (200-300 words)
[Key suppliers by category (raw materials, components, services) with named examples and share of COGS if disclosed. Concentration risk: top 3 supplier concentration %, any single-source dependencies, geographic concentration of supply base. Bargaining power dynamics: are input prices set by the company, by the supplier, or by an external benchmark? Recent supply disruptions (last 24 months) and how the company responded. One sentence on substitutability — can the company swap suppliers within 6 months without meaningful cost?]

### Downstream Analysis (200-300 words)
[Key customer archetypes (enterprise / consumer / government / OEM) with revenue mix %. Channel structure: direct sales vs. distributor vs. marketplace, with channel economics. Customer concentration: top 1 / top 5 / top 10 revenue %, named customers where disclosed. End-user dynamics: what is the buyer's actual use case, what does the demand driver behind that use case look like, and how sensitive is it to end-market conditions (e.g., consumer confidence, corporate IT budgets, government procurement cycles). Pricing dynamics downstream: does the company have pricing power at the point of sale, or is it price-taker.]

---

## VI. Historical Financial Data (Task 2 primary data source)

> **CRITICAL**: Task 2 will extract these exact numbers to populate the Raw Data tab.
> Use real numbers from APIs/filings. NO placeholders. NO approximations.

### Income Statement

| Metric | FY-4 | FY-3 | FY-2 | FY-1 | FY0 (Latest) | Source |
|--------|------|------|------|------|-------------|--------|
| Revenue | | | | | | |
| Cost of Revenue | | | | | | |
| Gross Profit | | | | | | |
| Gross Margin % | | | | | | |
| R&D Expense | | | | | | |
| SG&A Expense | | | | | | |
| D&A | | | | | | |
| Operating Income | | | | | | |
| Operating Margin % | | | | | | |
| Interest Income | | | | | | |
| Interest Expense | | | | | | |
| EBT | | | | | | |
| Tax Provision | | | | | | |
| Effective Tax Rate | | | | | | |
| Net Income | | | | | | |
| Net Margin % | | | | | | |
| Diluted EPS | | | | | | |
| Diluted Shares (M) | | | | | | |
| EBITDA | | | | | | |
| SBC | | | | | | |

### Balance Sheet (Year-End)

| Metric | FY-4 | FY-3 | FY-2 | FY-1 | FY0 | Source |
|--------|------|------|------|------|-----|--------|
| Cash & Equivalents | | | | | | |
| Accounts Receivable | | | | | | |
| Inventory | | | | | | |
| Total Current Assets | | | | | | |
| Net PP&E | | | | | | |
| Goodwill + Intangibles | | | | | | |
| Total Assets | | | | | | |
| Accounts Payable | | | | | | |
| Current Debt | | | | | | |
| Total Current Liabilities | | | | | | |
| Long-Term Debt | | | | | | |
| Total Liabilities | | | | | | |
| Retained Earnings | | | | | | |
| Total Equity | | | | | | |
| Total L&E | | | | | | |

### Cash Flow

| Metric | FY-4 | FY-3 | FY-2 | FY-1 | FY0 | Source |
|--------|------|------|------|------|-----|--------|
| CFO | | | | | | |
| CapEx | | | | | | |
| FCF | | | | | | |
| Net Debt Issuance | | | | | | |
| Dividends | | | | | | |

### Key Ratios

| Metric | FY-4 | FY-3 | FY-2 | FY-1 | FY0 |
|--------|------|------|------|------|-----|
| ROE | | | | | |
| ROA | | | | | |
| D/E Ratio | | | | | |
| Current Ratio | | | | | |
| OCF/NI Ratio | | | | | |
| FCF Margin | | | | | |
| DSO | | | | | |
| DIO | | | | | |
| DPO | | | | | |

---

## VII. Revenue Model & Growth Drivers (1,000-1,500 words)

### Segment Revenue Decomposition

| Segment | FY-2 Rev | FY-1 Rev | FY0 Rev | Driver Type | Volume | Price/ARPU | Growth Driver |
|---------|---------|---------|---------|-------------|--------|-----------|---------------|
| [Seg 1] | | | | [Units×ASP / Subs×ARPU / etc.] | | | |
| [Seg 2] | | | | | | | |
| [Seg 3+] | | | | | | | |
| Total | | | | | | | |

### Per-Segment Analysis (200-300 words each)
[For each major segment, cover four elements: (1) **Growth trajectory** — 3-year CAGR with named drivers for the acceleration or deceleration; (2) **Volume vs. price mix decomposition** — quantify how much of growth came from unit expansion vs. price increases vs. mix shift; (3) **Forward-looking driver diagnosis** — what specifically has to go right over the next 8 quarters for this segment to hit consensus, with one piece of observable evidence for or against that outcome; (4) **Risk to estimate** — name the one variable whose mis-estimation would have the largest impact on segment revenue and roughly how much the estimate could miss by. Task 2 will use this analysis to build segment-level projections in the Excel model.]

### Revenue Concentration (150-250 words)
[Customer concentration: top 1 / top 5 / top 10 %, with any named anchor customers disclosed in filings. Product concentration: revenue from the #1 product as a % of total. Geographic concentration: top 3 regions as a % of revenue. Explain how concentration affects operating leverage, working capital (DSO), and negotiating posture. Flag any single customer, product, or geography whose loss would create a ≥10% revenue hole, and name the mitigating contractual or switching-cost protections (if any).]

---

## VIII. Investment Thesis Table

| Dimension | Bull Arguments | Bear Arguments | Key Assumptions | Turning Point Signal | Our Judgment |
|-----------|----------------|----------------|-----------------|---------------------|--------------|
| Competitive Landscape | [Data-backed] | [Data-backed] | [What must be true] | [What to watch] | [Net assessment] |
| Growth Drivers | [Data-backed] | [Data-backed] | [What must be true] | [What to watch] | [Net assessment] |
| Earnings Quality | [Data-backed] | [Data-backed] | [What must be true] | [What to watch] | [Net assessment] |
| Valuation & Expectations | [Data-backed] | [Data-backed] | [What must be true] | [What to watch] | [Net assessment] |

**Commentary** (400-600 words): Walk through each row with named judgment rationale. For each dimension: (1) name the single most important bull fact AND the single most important bear fact from the row; (2) state which side of the argument currently dominates and why (cite a specific data point); (3) identify the key assumption whose breakdown would flip your judgment from bull → bear (or vice versa); (4) name one observable signal readers can watch over the next 3-6 months to confirm or refute your current read. End with a 2-3 sentence synthesis paragraph that explains how the four dimensions interact — for example, how strong competitive position (H1) enables durable growth (H2) which in turn supports the premium valuation (H4). The goal is to show that the thesis is internally consistent, not a bag of unrelated observations.

---

## IX. Catalyst Calendar

| Date | Event | Impact Direction | Importance | Expected Reaction |
|------|-------|------------------|------------|-------------------|
| YYYY-MM-DD | [Event] | [Bull/Bear/Neutral] | [High/Med/Low] | [What market expects, how it could surprise] |
| (minimum 4 events, ≥1 earnings, ≥2 High importance) |

---

## X. Risk Assessment (900-1,200 words)

> Each risk should be a self-contained 80-130 word analytical paragraph, not a one-line headline. The reader should leave each entry knowing the mechanism, the magnitude, the early warning signal, and the mitigant.

### Operational Risks (2-3 risks, 80-130 words each)
1. **[Risk Name]**: Describe the underlying mechanism (what would actually go wrong), quantify the financial impact in the bear case (revenue or margin hit), name the early warning signal that would precede the risk materializing, and state any management mitigant or contractual protection. — P: X/5, I: X/5, P×I: X

### Financial Risks (2-3 risks, 80-130 words each)
2. **[Risk Name]**: Cover leverage metrics, refinancing wall, FX exposure, working capital sensitivity, or off-balance-sheet items as relevant. Quantify the worst-case impact and tie back to a covenant, a specific debt maturity, or a stress scenario. — P: X/5, I: X/5, P×I: X

### Industry/Competitive Risks (2-3 risks, 80-130 words each)
3. **[Risk Name]**: Address share loss, margin compression from new entrants, technology disruption, or distribution-channel shifts. Reference the specific competitor, technology, or channel and quantify the displaced revenue at stake. — P: X/5, I: X/5, P×I: X

### Macro/Regulatory Risks (2-3 risks, 80-130 words each)
4. **[Risk Name]**: Tariff actions, antitrust, data/privacy regulation, ESG mandates, geopolitical exposure. State the specific policy or scenario, the geography, the timing window, and the financial impact range. — P: X/5, I: X/5, P×I: X

> P (Probability) and I (Impact) are 1-5 ratings. P×I produces the heat-map ranking that Task 3 will render in the report.

---

## XI. Data Sources

| Data Type | Source | Retrieval Date | Reliability |
|-----------|--------|----------------|-------------|
| [Every data source used] | | | |

---

## XII. Preliminary Valuation Inputs

> This section provides starting-point data for valuation. Content adapts based on `valuation_depth`.

### Comparable Companies (required for both L1 and L2)
| Company | Ticker | Market Cap | Revenue(TTM) | PE(TTM) | PB | EV/EBITDA | Why Selected |
|---------|--------|-----------|-------------|---------|----|-----------|----|
| [3-5 candidates] | | | | | | | |

**L1 Mode**: This table is the PRIMARY valuation data source. Must be complete with real data from iFind/Yahoo Finance. Include at least 5 peers with full financial metrics.

**L2 Mode**: This is a preliminary list for Task 2 to refine.

### DCF Starting Assumptions (L2 only; L1 skip this subsection)
| Parameter | Suggested Value | Basis |
|-----------|----------------|-------|
| Risk-Free Rate | X% | [Country] 10Y bond |
| Beta | X.X | [Source] |
| WACC (estimated) | X-X% | CAPM preliminary |
| Terminal Growth | X-X% | [Rationale] |
| Revenue CAGR (5Y) | X-X% | Consensus ± adjustment |
| Terminal Margin | X-X% | Historical trend |

### Consensus Estimates (required for both L1 and L2)
| Metric | FY+1E | FY+2E | Source | # Analysts |
|--------|-------|-------|--------|-----------|
| Revenue | | | | |
| EPS | | | | |
| EBITDA | | | | |
| Target Price | | | | |

### Scenario Assumptions (L1: simple table; L2: detailed inputs)
| Scenario | Revenue Growth | Margin | Implied PE | Implied Price | Probability |
|----------|---------------|--------|-----------|--------------|------------|
| Bull | X% | X% | XXx | ¥XX | XX% |
| Base | X% | X% | XXx | ¥XX | XX% |
| Bear | X% | X% | XXx | ¥XX | XX% |

---

## XIII. Cross-Method Valuation Synthesis (250-400 words)

> **Why this section exists**: A single valuation method can mislead. Cross-method synthesis is how the final target price is defended. Task 3 reads this section directly to write the "Valuation Conclusion" subsection and to justify the rating.
>
> **Mode-specific handling**:
> - **L1 (streamlined, 2-Task)**: Fill this section completely in Task 1 using only the comparable-companies method (§XII Comps table) plus consensus target price. No DCF. State explicitly that DCF was not performed and why (e.g., "L1 scope — no explicit DCF model built").
> - **L2 (full, 3-Task)**: Fill in the **Comparable Companies** row and any **Historical Trading Band** row during Task 1 based on the data you already have. Leave the **DCF** row and the **Final Synthesis** paragraph marked `[TO BE COMPLETED IN TASK 2]`. Task 2 will fill them in after building the DCF model and will rewrite the synthesis paragraph with all three methods reconciled.

### Method Summary Table

| Method | Implied Price | Target Multiple / Key Assumption | Confidence | Weighting | Notes |
|--------|--------------|----------------------------------|-----------|----------|-------|
| Comparable Companies (peer multiples) | $XXX | [e.g., 18x FY+1 EPS, peer median] | High/Med/Low | XX% | [L1 and L2 both] |
| DCF (L2 only) | $XXX | [e.g., WACC 9.5%, TG 2.5%] | High/Med/Low | XX% | [L2 — filled in Task 2] |
| Historical Trading Band | $XXX | [e.g., 5Y avg forward PE 22x] | High/Med/Low | XX% | [Optional but recommended] |
| Consensus Target Price | $XXX | [analyst median] | — | Reference only | [For calibration, not weighted] |
| **Weighted Target Price** | **$XXX** | | | 100% | |

### Synthesis Paragraph (150-250 words)
[Explain the weighting logic: why each method is weighted as it is given the company's stage, cyclicality, data reliability, and peer comparability. Reconcile the spread between methods — if comps imply $120 and DCF implies $150, explain which assumption drives the gap and which method you trust more. State the final target price and the 12-month total-return expectation (price appreciation + dividend yield). Derive the rating (Buy / Hold / Sell) from the total-return vs. your firm's rating bands, and tie back to the scenario probabilities from §XII. Close with one sentence on what would cause you to revise the target price by >10%.]

Before delivering the research document, verify ALL of the following:

### Completeness Checks
- [ ] Total word count ≥ 9,000 (full analytical prose across §I-§V, §VII, §VIII, §X, §XIII)
- [ ] §I Core Narrative: 400-600 words covering all 7 structural elements
- [ ] §II Six-Dimension: All 6 dimensions 250-400 words each with Conclusion + Data + expanded analysis sub-section + So What
- [ ] §III Company Overview: 1,200-1,800 words with all 4 subsections hitting their individual word floors
- [ ] §IV Industry: ≥5 named competitors with revenue and market share data; Industry Overview ≥450 words; Competitive Positioning Analysis ≥350 words
- [ ] §IV TAM/SAM/SOM: All 4 rows filled with actual numbers and sources PLUS 200-350 word narrative
- [ ] §V Supply Chain: Complete Mermaid code + Upstream (200-300 words) + Downstream (200-300 words)
- [ ] §VI Historical Financials: ALL cells filled for at least 3 years (NO blanks in IS/BS/CF)
- [ ] §VII Revenue Model: ≥3 segments with Volume×Price decomposition, 200-300 words per-segment analysis, Revenue Concentration paragraph
- [ ] §VIII Thesis Table: All 4 rows have both Bull AND Bear arguments (no blanks) + 400-600 word Commentary
- [ ] §IX Catalysts: ≥4 events with dates (including next earnings)
- [ ] §X Risks: ≥8 risks across ≥3 categories with P×I scoring; each risk 80-130 words
- [ ] §XII Comparable Companies: ≥3 companies with real data (L1: must have ≥5 with full metrics)
- [ ] §XII Consensus Estimates: Target price + FY+1E/FY+2E revenue and EPS (both L1 and L2)
- [ ] §XII Scenario Assumptions: Bull/Base/Bear with implied prices and probabilities (both L1 and L2)
- [ ] §XII DCF Starting Assumptions: Filled (L2 only; L1 may skip)
- [ ] §XIII Cross-Method Valuation Synthesis: Method Summary Table + 150-250 word synthesis paragraph. L1: fully completed in Task 1 (comps + historical band + consensus). L2: comps row filled in Task 1; DCF row and final synthesis paragraph marked `[TO BE COMPLETED IN TASK 2]`.

### Data Quality Checks
- [ ] No placeholder text (e.g., "TBD", "XXX", "to be filled")
- [ ] Financial data cross-verified: Revenue in IS = Revenue in CF discussion (if mentioned)
- [ ] Revenue segments sum to total revenue (within 2% tolerance for "other" segment)
- [ ] All data sources documented in §XI

### Metadata Checks
- [ ] All Task Handoff Metadata fields filled
- [ ] Stock chart SVG file exists at specified path
- [ ] Stock CSV and benchmark CSV files exist

**If any check fails**: Fix before delivery. Do NOT proceed to Task 2 with an incomplete research document.
