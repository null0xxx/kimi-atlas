# Investment Logic Module Detailed Specification (Sole Source) / 投资逻辑模块详细规范（唯一来源）

**[Note] This file is the sole complete source for investment logic writing.**

**Core Principles**:
1. **Eliminate Forced Content**: Factors without clear information sources (e.g., inability to find specific 解禁/增减持 data) are prohibited from being written into the report.
2. **Six-Dimension Mapping**: Investment logic must be a **direct mapping and concentrated essence of Phase 2.4 六维分析**, not independent creation.
3. **Marginal and Inflection-Point Thinking**: Each argument must embody "what is changing now" and "what could reverse current trends", prohibiting simple linear extrapolation.

---

## Module Overview

**Module Position**: First page, below 公司概览 module (or per latest layout specifications)

**[Note] Length Constraint: Investment Logic module must conclude within first page of PDF.**

**Hard Constraints (self-check before generation)**:
- Short-term investment logic: 5-6 bullets, with **at least 1 must be 利空/risk factor** (marked in dark gray font `style="color:#555555;"`, prohibiting eye-catching red), remainder as 利多. Each bullet **must include specific data support**
- Short-term investment logic **must include 1 bullet on capital/market structure analysis**: institutional holding changes, options Put/Call ratio, implied volatility, short-selling ratio, 北向/南向资金 flows, major shareholder 增减持, etc. (US stocks use institutional holdings/options data, A股 use 北向资金/解禁 data)
- Long-term investment logic: 5-6 bullets, with **at least 1 must be long-term risk/paradigm challenge** (marked in dark gray font), remainder as 利多. Each bullet **must have quantified forecast or timeline**
- **Risk/Bear Bullet Color Standard**: Use `color:#555555` (dark gray) + bold for distinction, prohibiting `#B71C1C` or other bright red, avoiding visual eye-strain
- Investment Thesis Comprehensive Analysis Table: strictly 4 rows × 6 columns (Dimension/Bull/Bear/Assumption/Inflection Signal/Judgment). **Default black font**, use only `<span class="bull-text">` (dark green)/`<span class="bear-text">` (dark red)/`<span class="warn-text">` (orange) at key data points, prohibiting full-column colored font
- **Entire investment logic module (dual Box + full-width analysis table) total content controlled within 35 lines**
- **Bull-Bear Balance Principle**: Investment logic module prohibited from being all 利多 narrative. Both short-term and long-term Boxes must each contain ≥1 bear/risk bullet, otherwise considered structural defect requiring repair
- **First Page Space Constraint (Critical)**: Investment logic module cannot fill entire first page. First page must simultaneously accommodate: stylized title area + stock price chart/trading data module + investment logic module + 公司概览 module title (at minimum). If investment logic content expands to push 公司概览 to first page bottom with only title remaining, must streamline investment logic content or add `page-break-before: always` to 公司概览 module
- **Page-break Protection Standard**: Modules with content > 600 characters (such as 公司概览, 财务分析), must use `<div class="module-row module-newpage">` to force new page start, preventing title and content from being split across pages

**Content Quality Standards (each bullet must satisfy ALL four)**:
1. **Has Data**: Contains specific numbers (revenue, growth rate, market share, amounts, etc.)
2. **Has Source**: Annotates data source (Yahoo Finance, company financials, industry reports, etc.)
3. **Has Logic**: Explains "why"—causal relationship clear, not simple fact listing
4. **Has Distinction**: Short-term focuses on 6-12 month verifiable catalysts, long-term focuses on 1-3 year structural trends

**Quantitative Bullet Standard (Tear Sheet + Equity Report)**:

| Metric | Minimum | Good Example | Bad Example |
|--------|---------|-------------|-------------|
| Length | ≥30 Chinese chars / ≥15 English words | "Q3 revenue +23% YoY to ¥152bn, 4pp above consensus, driven by premium mix shift (iFind)" | "Revenue grew well" |
| Data points | ≥1 per bullet | "Gross margin 42.3%, +180bps YoY, 5pp above Samsung" | "High gross margin" |
| Causal link | "why" or "so what" explained | "PE 15x below 5yr avg 22x, reflecting market concern over margin compression" | "PE is 15x" |

**Self-check**: Before generating any module, review each bullet. If a bullet has <30 chars and zero numbers, rewrite it with data from Phase 1-2 analysis. Thin bullets waste the analysis effort.

**Streamlining Priority (execute in order when overflowing)**:
1. Delete non-core sub-bullets (retain main bullet only)
2. Merge highly similar items (e.g., two similar bear factors)
3. Condense secondary description text into phrases (remove modifying clauses)
4. Keep investment thesis comprehensive analysis table at 4 rows, cannot compress further

Core Principle: **Retain depth, cut redundancy**—important arguments can be expanded fully (with data+logic), but marginally valuable content should be ruthlessly streamlined.

**Page-break Prevention**: After generating HTML, estimate total height of investment logic module. If predicting exceeds 80% of first page remaining space, immediately execute streamlining process, don't wait until PDF generation.

**Layout**: Left-Right Dual Box
- Left Box: **Short-term Investment Logic** (0-6 months)
- Right Box: **Long-term Investment Logic** (1-3 years)

**[Note] Mandatory Title Standard**:
- Left title must be: **短期投资逻辑**
- Right title must be: **长期投资逻辑**
- **Prohibited** to use other titles

---

## Methodology: From Six-Dimension Analysis to Investment Logic

Investment logic is **not independent creation**, but rather **structured output of 六维分析**. Must complete Phase 2.4 六维分析 before writing, and map per table below:

| Six-Dimension | Mapping to Investment Logic | Mapping Rule |
|---------------|----------------------------|--------------|
| Dimension 2: What market is pricing | Short/long-term 利多 or 利空 | Rationally priced factors→consensus; pricing deviation factors→expectation gaps |
| Dimension 3: Where market might be wrong | Short/long-term 利多 or 利空 | Positive expectation gap→利多; negative expectation gap→利空 |
| Dimension 4: Key variables | Short-term investment logic core items | Most likely to change stock price in next 6 months: 1-2 variables |
| Dimension 5: Main contradiction | Investment Thesis Comprehensive Analysis Table → Competitive landscape row (H1) | Direct excerpts of strongest bull/bear arguments |
| Dimension 6: Anomaly signals | Investment Thesis Comprehensive Analysis Table → Earning quality row (H3) + short-term bear/risk hints | Financial anomalies or capital anomalies must map to short-term logic |

> **Note**: Original separate "bull-bear debate table" and "key assumption verification table" merged into "Investment Thesis Comprehensive Analysis Table" (4 rows × 6 columns), see `references/investment-logic.md`.
> Dimension 2 → Valuation & Expectation row (H4), Dimension 4 → Growth Drivers row (H2), Dimension 5 → Competitive Landscape row (H1), Dimension 6 → Earning Quality row (H3).

**Mandatory Requirements**:
- Bullets without information sources **must be deleted**, rather have less content than fabricate.
- Analysis phase (Phase 2-3) can internally tag information reliability levels to aid reasoning, but **final report prohibits【已验证】【部分验证】【未验证】 tags**. Report targets investors, verification tags are internal work artifacts.

---

## Left Box: Short-term Investment Logic (0-6 months)

### Writing Principles: Marginal Change and Inflection Points

Short-term logic core is not "company is good", but **"over next 6 months, what is changing, what has already changed"**. Must answer:
- Has current stock price already priced in recent 利好/利空?
- Are there upcoming **inflection-point events** (earnings inflection, policy inflection, capital inflection)?
- Are market sentiment and fundamentals **diverging**?

### Structure Template

```markdown
**Bull Factors** (2-3 items, each must have data or event support, delete if no support)
• [Marginal improvement 1]: [specific description] + [why this is marginal change at current stage] + [data/event support]
  - Inflection condition: [what signal means this bull factor ends]
  - Pricing level: [how much market has priced / how much remains]

**Bear Factors** (1-2 items, must have)
• [Marginal deterioration/potential risk 1]: [specific description] + [why this is biggest short-term pressure]
  - Risk level: High/Medium/Low
  - Trigger/mitigation condition: [what scenario means risk realizes or subsides]

**Capital and Market Structure**
• [Only write when clear data collected]:
  - 北向/南向资金 flows (must have specific amounts and time periods)
  - Major shareholder 增减持 (must have announcement basis and specific share count/ratio)
  - 解禁/定增/回购 (must have specific dates and amounts)
  - 龙虎榜/大宗交易 anomalies (must have specific discount rates and trading volumes)
• **Prohibited Example**: If unable to find specific 解禁 data, **not allowed** to write "No significant large-cap 解禁 in A股 next 3 months, short-term 解禁 pressure controllable" type of forced placeholder language.
• If truly no significant capital anomalies found, can write: "No major 解禁, 增减持, or anomalous capital flow announcements/data found recently; capital structure in normal state."

**Key Disagreement Points**
• Bulls believe: [bull view]
• Bears believe: [bear view]
• Our judgment: [data-based judgment, must reflect marginal view or inflection judgment]
```

### Short-term Logic "So What" Checklist

Each bullet must pass following checks:
1. Is this a **marginal change** or **static description**? Must be marginal change.
2. How is the market pricing this? 
3. Will this be overturned or reversed within 6 months?

---

## Right Box: Long-term Investment Logic (1-3 years)

### Writing Principles: Structural Forces and Paradigm Shifts

Long-term logic core is not "future revenue will grow by how much", but **"what structural forces support this company's long-term profit capacity, and whether these forces are strengthening or being circumvented"**. Must answer:
- What changes is happening to industry's **competitive paradigm**? (e.g., from capacity competition to technology competition, from price wars to brand wars)
- Is company's **护城河** deepening or being bypassed?
- Do **second growth curves** or **end-market shifts** exist bringing nonlinear opportunities?
- What is **biggest long-term risk** to the logic? Is this risk probabilistic or structural?

### Structure Template

```markdown
**Core Investment Thesis/Long-term Narrative** (1 sentence, replacing "core investment thesis")
• [One-sentence summary of company's long-term investment value, must include structural advantage or paradigm positioning]
  - Example (EV Manufacturer): Vertically integrated new energy manufacturing platform, constructing cost and technology dual 护城河 globally through battery-vehicle-chip integration, long-term benefits from EV penetration increase and auto export wave.
  - Example (Premium Consumer Brand): Premium consumer cultural symbol, irreplaceable in consumer upgrade and social scenarios, long-term value from scarce capacity release and pricing power.

**Structural Bull Factors** (2-3 items)
• [Competitive paradigm shift/护城河 deepening 1]: [describe industry's long-term structural change and company benefits]
  - 护城河 type: Brand/Cost/Network effects/Technology/License/Scale
  - Sustainability: Why this advantage won't be easily toppled in next 3 years
  - Inflection signal: [what data shows this logic accelerating/weakening]

• [Second growth curve/market shift 2]: [describe nonlinear long-term growth source]
  - TAM/SAM: [total addressable market and accessible market size]
  - Current penetration/progress: [what stage reached]
  - Inflection signal: [what milestone event marks true second curve launch]

**Long-term Risks and Paradigm Challenges** (1-2 items, must include)
• [Long-term risk 1]: [challenge to core investment thesis, must be structural not cyclical]
  - Risk type: Technology disruption/Policy environment deterioration/Competitive landscape shift/Demand paradigm shift/Geopolitical
  - Impact level: Damage degree to core thesis (Fatal/Medium/Light)
  - Monitoring indicator: [what signal means this risk shifts from "possible" to "real"]

**Key Assumptions, Monitoring Indicators and Scenario Triggers**
• Key assumptions: [core assumptions supporting long-term logic]
• Verification indicators: [quarterly/annual monitoring]
• Scenario triggers: [what circumstances require re-evaluating long-term logic]
```

### Long-term Logic Prohibitions

1. **Prohibit simple linear extrapolation**: Cannot write "because past 3 years grew 30%, so next 3 years will grow 25%+".
2. **Prohibit empty slogans**: Cannot write "new energy is big trend" without explaining so-what for specific company profit model.
3. **Prohibit ignoring inflection risks**: Must have at least one clear "monitoring indicator" for judging whether long-term logic fails.

---

## Investment Thesis Comprehensive Analysis Table (spans full row, below dual Boxes)

**[Note] This table merges original "bull-bear deep debate table" and "key assumption verification table", as independent full-width row spanning below both Boxes.**

### Six-Dimension Model Mapping

| Unified Table Dimension Row | Six-Dimension Model | Mapping Logic | Assumption Code | Time Dimension |
|---------------------------|-------------------|----------------|----------------|----------------|
| Competitive Landscape | Dim5 Main Contradiction | Bull-bear largest disagreement usually around competitive position | H1 | Long-term (L) |
| Growth Drivers | Dim4 Key Variables + Dim3 Info Gap | Growth most common key variable, info gaps often reflect in growth expectation deviation | H2 | Short+Long (S+L) |
| Earning Quality | Dim6 Anomaly Signals | Earning quality anomalies most common data red flag | H3 | Short-term (S) |
| Valuation & Expectation | Dim2 Market Pricing | Valuation's hidden assumptions reasonableness is most direct bull-bear battleground | H4 | Short-term (S) |

**Unmapped Dimension Handling**:
- **Dim1 (One-sentence judgment)**: Provides framework context for entire table—company's current stage determines which dimensions more critical
- **Dim3 (Info gap)**: Fuses into "Growth Drivers" and "Valuation & Expectation" bull argument columns—undervalued info gaps are bull arguments

### Table Structure (6 columns)

| Analysis Dimension | Bull Arguments | Bear Arguments | Key Assumption | Inflection Signal | Our Judgment |
|------------------|---|---|---|---|---|
| Competitive Landscape (H1) | [1-2 strongest bull points+data] | [1-2 strongest bear points+data] | [Quantifiable core assumption] | [Observable metric/event] + status tag | time-tag + [bull/bear/neutral]+[monitoring indicator] |
| Growth Drivers (H2) | [Evidence+data] | [Evidence+data] | [Assumption] | [Condition] + status tag | time-tag + [Judgment] |
| Earning Quality (H3) | [Evidence+data] | [Evidence+data] | [Assumption] | [Condition] + status tag | time-tag + [Judgment] |
| Valuation & Expectation (H4) | [Evidence+data] | [Evidence+data] | [Assumption] | [Condition] + status tag | time-tag + [Judgment] |

### Column Content Standard

- **Analysis Dimension**: Dimension name + Assumption code (e.g. "Competitive Landscape (H1)")
- **Bull Arguments**: 1-2 strongest bull points, must have specific data support (no pure qualitative descriptions)
- **Bear Arguments**: 1-2 strongest bear points, must have specific data support
- **Key Assumption**: This dimension's core assumption statement (one sentence, quantifiable)
- **Inflection Signal**: Concrete observable quantitative indicator or event + current status tag embedded:
  - `<span class="status-safe">[成立] Assumption holds</span>` — green
  - `<span class="status-warn">[注意] Marginal weakening</span>` — orange
  - `<span class="status-risk">[不成立] Assumption invalidated</span>` — red
- **Our Judgment**: Direction (bull/bear/neutral) + time tag `<span class="time-tag">Short-term/Long-term/Short+Long</span>` + key monitoring indicator

### Complementarity with Short/Long-term Investment Logic

- **S (Short-term)** marked rows feed arguments to left "Short-term Investment Logic" Box
- **L (Long-term)** marked rows feed arguments to right "Long-term Investment Logic" Box
- **S+L** marked rows feed to both sides
- Box provides narrative argument, table provides structured assumption verification—top-bottom complementary

### Requirements
- Exactly **4 rows** (Competitive Landscape/Growth Drivers/Earning Quality/Valuation & Expectation), each row corresponds to one assumption code
- Each "bull argument" and "bear argument" has specific data support
- Each "key assumption" is one-sentence quantifiable proposition
- Each "inflection signal" is observable quantitative indicator or specific event, with embedded status tag
- Each "our judgment" includes direction + time tag + key monitoring indicator
- 4 assumptions cover Dim2/4/5/6 → ensure six-dimension model full coverage
- S-tagged row arguments must align with left "Short-term Investment Logic" Box
- L-tagged row arguments must align with right "Long-term Investment Logic" Box
- Table row count strictly controlled, coordinating first page length constraint of investment logic module
- Use CSS classes: `.debate-table` (entire table). **Background colors limited to white/blue/gray only**: table header dark blue+white text, dimension column light gray background, remaining columns white background, alternating rows very light gray. Column distinction through **font color**: `.bull-col` dark green (bull), `.bear-col` dark red (bear), `.assumption-col` dark blue (assumption), `.inflection-col`/`.judge-col` black. Prohibit colored backgrounds (green/red/yellow/purple, etc).

---

## Complete Example (EV Manufacturer / 新能源车企)

### Short-term Investment Logic

**Bull Factors**
• New models + smart driving upgrade bring product mix improvement: Q1 high-end ratio increases, ASP stabilizes, market's pessimistic single-car profit expectations may be over-bottomed (inflection: if Q2 ASP drops sequentially then invalid; market partly priced technology upgrade, hasn't fully reflected export profit elasticity)

**Bear Factors**
• Domestic price wars exceed expectations crushing profit: Q1 industry promotions intensify, multiple carmakers follow with price cuts, per-vehicle earnings pressured (risk: high; mitigation: Q2 volume growth+export ratio increase offset)

**Capital and Market Structure**
• Long-term strategic investor continues reducing H-shares: holding ratio declining, market cautious about future selling pressure
• A股 recently found no major 解禁 or anomalous capital flows, capital structure normalized

**Key Disagreement Points**
• Bulls: Scale efficiency + export growth offset domestic price wars
• Bears: Price wars will systematically compress vehicle profit
• Judgment: Price war is known cyclical bear factor, while export and premiumization are marginal improvement direction; short-term watch if Q2 gross margin inflects.

### Long-term Investment Logic

**Core Investment Thesis/Long-term Narrative**
• Vertically integrated new energy manufacturing platform, constructing cost and technology dual 护城河 globally through battery-vehicle-chip integration, long-term benefits from EV penetration increase and auto export wave.

**Structural Bull Factors**
• Competitive paradigm shifts to "cost+efficiency race": industry consolidation stage, vertically integrated companies' cost advantage rare (护城河: cost+technology+scale, 5-10 years accumulation hard to replicate; inflection: competitors achieve equivalent integration self-sufficiency)
• Export and overseas factory second curve: SE Asia, Europe, LatAm plants gradually ramping, overseas revenue 28.55% still has substantial room (inflection: overseas factory capacity utilization>80% and gross margin exceeds domestic)

**Long-term Risks and Paradigm Challenges**
• Geopolitics and trade barriers: US/EU tariffs on Chinese EVs tightening, export profit faces policy compression risk (impact: medium, delays second curve; monitoring: tariff rate changes, localization requirements)

**Investment Thesis Comprehensive Analysis**
| Analysis Dimension | Bull Arguments | Bear Arguments | Key Assumption | Inflection Signal | Our Judgment |
|----------|---|---|---|---|---|
| Competitive Landscape (H1) | Domestic NEV share 35%, technology gap widening | Price wars erode profit, new entrants from tech sector | Market share maintains >30% | CR drops below 28% consecutive 2 quarters [成立] Current 35% | Long-term Bull, monitor quarterly share |
| Growth Drivers (H2) | Export +120% YoY, multi-brand matrix expanding | EU tariff risk, new brands not profitable | Overseas revenue ratio rises to >15% | Export volume consecutive 2 months down >20% [成立] Current trend upward | Short+Long Bull, watch EU tariff implementation |
| Earning Quality (H3) | Operating cash/net profit >1.2, capex controllable | Post-subsidy profit authenticity questionable | Non-GAAP net margin maintains >4% | OCF/NI<0.8 or non-GAAP margin <3% [注意] Subsidy ratio rising | Short-term Neutral-cautious |
| Valuation & Expectation (H4) | 24x PE vs industry 30x, implicit 15% growth reasonable | PB 4.5x at historical high | FY2025E net profit growth >15% | Consecutive 2 quarters EPS miss >10% [成立] 24Q4 beat | Short-term Bull, valuation has safety margin |

---

## Internal Analysis Tags (Phase 2-3 only, prohibited from appearing in final report)

【已验证】/【部分验证】/【未验证】 tag definitions see `references/six-dimension-analysis.md` "Information Classification Tagging" section.

**Mandatory Rule: These tags only for Phase 2-3 internal reasoning, final report HTML strictly prohibits any【】tags.**

---

## Quality Checklist

```markdown
□ Title Standard: Left "短期投资逻辑", Right "长期投资逻辑"
□ Short-term
  □ Each logic is marginal change not static description
  □ Has clear inflection conditions and pricing level judgment
  □ Bull factors ≥2, bear factors ≥1
  □ Capital/market structure: write only points with clear data support, don't fabricate without data
  □ Key disagreement points have independent judgment, not fence-sitting

□ Long-term
  □ "Core Investment Thesis/Long-term Narrative" complete and in Chinese
  □ Has structural analysis, not simple linear extrapolation
  □ 护城河 type clear
  □ Has second curve/nonlinear growth analysis
  □ Long-term risks ≥1, and structural risk
  □ Bull-bear debate includes "Our Judgment and Inflection Conditions"
  □ Has clear scenario triggers

□ Investment Thesis Comprehensive Analysis Table
  □ Exactly 4 rows (Competitive Landscape/Growth Drivers/Earning Quality/Valuation & Expectation), each row corresponds to one assumption code
  □ Each "bull argument" and "bear argument" has specific data support
  □ Each "key assumption" is one-sentence quantifiable proposition
  □ Each "inflection signal" is observable quantitative indicator or event, with embedded status tag
  □ Each "our judgment" includes direction + time tag (short-term/long-term/short+long) + key monitoring indicator
  □ S-tagged row arguments align with left "Short-term Investment Logic" Box
  □ L-tagged row arguments align with right "Long-term Investment Logic" Box

□ Report Output Standard
  □ Investment logic module must conclude within PDF first page
  □ Report excludes 【已验证】【部分验证】【未验证】 internal analysis tags
```
