# Analysis Framework — Market Insight Report

Guidance for conducting market analysis and producing data-driven insights. This framework defines **how to analyze**, not just how to format. Every analytical section in the report should trace back to one or more methods described here.

## Table of Contents

1. [Market Sizing Methodology](#1-market-sizing-methodology)
2. [Category & Growth Driver Analysis](#2-category--growth-driver-analysis)
3. [Channel Analysis](#3-channel-analysis)
4. [Consumer Behavior Analysis](#4-consumer-behavior-analysis)
5. [Competitive Analysis](#5-competitive-analysis)
6. [Data-to-Insight Methodology](#6-data-to-insight-methodology)

---

## 1. Market Sizing Methodology

### Top-Down Approach
Start from macro data and narrow down:

```
Total Population / Households
  × Target Demographic %
  × Category Penetration Rate
  × Average Purchase Frequency (per year)
  × Average Spend per Purchase
  = Total Addressable Market (TAM)
```

**When to use**: Initial market sizing, new market entry analysis, cross-country comparison.

**Data sources**: National statistics bureaus, Euromonitor, Statista, industry associations.

### Bottom-Up Approach
Start from unit-level data and aggregate up:

```
Number of Active SKUs/Brands
  × Average Revenue per SKU
  = Brand-level Revenue

Sum of all brand revenues = Market Size

OR:

Number of Retail Outlets (online + offline)
  × Average Category Revenue per Outlet
  = Market Size
```

**When to use**: Validation of top-down estimates, detailed segment sizing, market with good company-level data.

**Data sources**: Company filings, channel data (e-commerce platform GMV), retail audit data (Nielsen/Kantar).

### Cross-Validation Rule
**Always use both methods and compare.** If the difference exceeds 20%, investigate the gap:
- Top-down > Bottom-up: likely undercounting brands/channels in bottom-up
- Bottom-up > Top-down: likely overestimating penetration/frequency in top-down
- Present both estimates with the validated range

### TAM / SAM / SOM Framework

| Level | Definition | How to Calculate |
|-------|-----------|------------------|
| **TAM** (Total Addressable Market) | Total market demand if every potential customer bought | Population × penetration ceiling × average spend |
| **SAM** (Serviceable Addressable Market) | The slice your product/service can reach | TAM × geographic/channel/segment filters |
| **SOM** (Serviceable Obtainable Market) | Realistic capture in 3-5 years | SAM × expected market share (typically 5-20%) |

### Data Source Priority
1. Government statistics / census data (most authoritative)
2. Industry association reports
3. Retail audit data (Nielsen, Kantar, GfK)
4. Public company filings and earnings calls
5. E-commerce platform data (official reports or third-party trackers)
6. Third-party research reports (consulting firms, equity research)
7. Expert interviews and field research

---

## 2. Category & Growth Driver Analysis

### Growth Decomposition Formula

The fundamental equation for any consumer market:

```
Revenue = Penetration × Purchase Frequency × Spend per Occasion

Growth (%) = Penetration Growth + Frequency Growth + Price/Mix Growth
```

For every category, decompose growth into these three drivers and identify which is the primary engine.

### Volume vs. Price Decomposition

```
Revenue Growth = Volume Growth + ASP Growth

Where:
  Volume Growth = Unit Shipment Growth (quantity effect)
  ASP Growth = Average Selling Price change (price/mix effect)
```

**Interpretation matrix**:

| Volume | Price | Diagnosis |
|--------|-------|-----------|
| + | + | Healthy growth (expand penetration + premiumization) |
| + | - | Volume-driven growth, possible price war |
| - | + | Premiumization / market maturation |
| - | - | Market contraction, structural decline |

### Category Lifecycle Positioning

Place each category on the lifecycle curve:

| Stage | Growth Rate | Penetration | Competitive Intensity | Strategy Implication |
|-------|------------|-------------|----------------------|---------------------|
| **Introduction** | >30% | <10% | Low (few players) | Educate market, build awareness |
| **Growth** | 15-30% | 10-40% | Rising | Grab share, scale distribution |
| **Maturity** | 0-15% | 40-70% | High | Defend share, optimize margins |
| **Decline** | <0% | Falling | Consolidating | Harvest or pivot |

### Category Matrix (Four-Quadrant Analysis)

Plot categories on a 2×2 matrix:
- **X-axis**: Revenue growth rate (%)
- **Y-axis**: Market share change (pp)

| Quadrant | Growth | Share | Interpretation |
|----------|--------|-------|---------------|
| Star (top-right) | High | Gaining | Category leader, invest aggressively |
| Cash Cow (bottom-right) | High | Losing | Growing market but losing ground |
| Question Mark (top-left) | Low | Gaining | Gaining share in slow market |
| Dog (bottom-left) | Low | Losing | Underperformer, restructure or exit |

### Price Band Analysis

Segment the market by price tiers and track migration:

```
Price Band Structure:
  Premium (top 20% price):    XX% of revenue, XX% of volume
  Mid-range (middle 50%):     XX% of revenue, XX% of volume
  Value (bottom 30% price):   XX% of revenue, XX% of volume

Price Band Migration (YoY change in share):
  Premium: +X pp (premiumization trend)
  Mid-range: -X pp (hollowing out)
  Value: +/-X pp
```

---

## 3. Channel Analysis

### Channel Share Tracking

Track channel share evolution over 3-5 years minimum:

```
Channel Share Table:
              Year 1   Year 2   Year 3   CAGR
Online total:  XX%      XX%      XX%      XX%
  - Platform A XX%      XX%      XX%      XX%
  - Platform B XX%      XX%      XX%      XX%
  - Platform C XX%      XX%      XX%      XX%
Offline total: XX%      XX%      XX%      XX%
  - Modern trade XX%    XX%      XX%      XX%
  - Traditional  XX%    XX%      XX%      XX%
```

Visualize as stacked 100% bar chart with CAGR side table.

### Channel Migration Matrix

For each major channel shift, trace the flow:

```
Where did [Channel A]'s lost share go?
  → X pp to Channel B (driven by: [reason])
  → Y pp to Channel C (driven by: [reason])
  → Z pp to Channel D (driven by: [reason])

Where did [Channel E]'s new share come from?
  → X pp from Channel A (driven by: [reason])
  → Y pp from Channel B (driven by: [reason])
```

### Channel Efficiency Comparison

Compare channels on standardized metrics:

| Metric | Channel A | Channel B | Channel C |
|--------|-----------|-----------|-----------|
| GMV / Traffic (conversion value) | | | |
| Conversion Rate | | | |
| Average Order Value | | | |
| Repeat Purchase Rate | | | |
| Customer Acquisition Cost | | | |
| Return Rate | | | |

### Emerging Channel Assessment Framework

For any new/fast-growing channel, evaluate:

1. **Scale**: Current GMV/users, growth rate
2. **Penetration trajectory**: What % of target users have tried this channel?
3. **User overlap**: How much overlap with existing channels? (high overlap = cannibalization, low = incremental)
4. **Unit economics**: Is the channel profitable at scale?
5. **Sustainability**: Is growth driven by subsidies/promotions or organic demand?

---

## 4. Consumer Behavior Analysis

### Purchase Decision Journey

Map the consumer journey for the category:

```
Awareness → Interest → Consideration → Purchase → Loyalty/Advocacy
   ↑            ↑           ↑              ↑            ↑
[Touchpoints] [Content]  [Comparison]  [Channel]   [Retention]
```

For each stage, identify:
- What triggers movement to the next stage?
- What are the key touchpoints?
- Where are the biggest drop-offs?

### Consumer Segmentation Framework

Layer multiple segmentation dimensions:

**Dimension 1: Demographics**
- Age cohorts (Gen Z / Millennials / Gen X / Silver)
- City tier (Tier 1 / New Tier 1 / Tier 2 / Tier 3+)
- Income bands

**Dimension 2: Behavioral**
- Purchase frequency (heavy / medium / light / lapsed)
- Channel preference (online-first / offline-first / omnichannel)
- Price sensitivity (premium-seeking / value-seeking / deal-hunting)

**Dimension 3: Psychographic**
- Lifestyle values (health-conscious / convenience-driven / status-seeking / eco-aware)
- Information sources (social media driven / expert-driven / peer-driven)

**Cross-tabulation rule**: The most actionable segments emerge from crossing demographics × behavior, not from demographics alone.

### Need-State / Occasion Analysis

Map consumption occasions to understand demand drivers:

```
Occasion Matrix:
                    High Frequency    Low Frequency
High Spend/Order    [Habitual Premium] [Special Occasion]
Low Spend/Order     [Daily Routine]    [Impulse/Trial]
```

For each quadrant: identify category fit, growth potential, and unmet needs.

### Survey Data Interpretation Rules

When citing consumer survey data:
- **Always state sample size and methodology** (online panel, street intercept, etc.)
- **Distinguish claimed behavior from actual behavior** — surveys overstate intention, understate habitual behavior
- **Cross-validate with transactional data** when possible
- **Watch for recency bias** — consumers over-weight recent experiences
- **Report confidence intervals** for small sample sizes

### From Behavior Data to Persona

Build personas from data, not imagination:

```
Step 1: Identify behavioral clusters in the data (purchase patterns, channel usage, price points)
Step 2: Profile each cluster demographically (age, city, income)
Step 3: Validate with qualitative data (interviews, social listening)
Step 4: Name the persona and define its defining behavior (not just demographics)
Step 5: Size each persona (% of total market, % of total revenue)
```

**Rule**: A good persona is defined by what they DO, not who they ARE.

---

## 5. Competitive Analysis

### Market Share Attribution

When market share shifts, decompose the drivers:

```
Brand X Share Change = Brand Effect + Channel Effect + Price Effect + Innovation Effect

Where:
  Brand Effect:     Share change due to brand preference/loyalty shifts
  Channel Effect:   Share change due to distribution gains/losses
  Price Effect:     Share change due to relative pricing moves
  Innovation Effect: Share change due to new product launches
```

For each major share shift in the market, attribute the primary driver.

### Concentration Metrics

| Metric | Formula | Interpretation |
|--------|---------|---------------|
| **CR3** | Sum of top 3 market shares | >60% = oligopoly; <40% = fragmented |
| **CR5** | Sum of top 5 market shares | >80% = highly concentrated |
| **HHI** | Sum of squared market shares (×10,000) | <1,500 = competitive; 1,500-2,500 = moderate; >2,500 = concentrated |

Track CR3/CR5 over time — rising = consolidation, falling = fragmentation.

### Brand Competitiveness Radar

Evaluate each major brand on 5-6 dimensions:

1. **Brand awareness / mindshare** (aided/unaided recall, search index)
2. **Product strength** (quality perception, innovation pipeline, portfolio breadth)
3. **Channel coverage** (distribution width × depth, online/offline balance)
4. **Price competitiveness** (price positioning, promotion intensity, value perception)
5. **Marketing efficiency** (share of voice, social buzz, ROI on spend)
6. **Growth momentum** (revenue growth, share trend, new user acquisition)

Visualize as radar/spider chart for 3-5 key competitors.

### Competitive Landscape Narrative Framework

Structure the competitive narrative as an evolution story:

```
Phase 1: [Past state] — "[Describe the old competitive landscape]"
  Key characteristics: [who dominated, why]

Phase 2: [Disruption] — "[What changed]"
  Trigger: [technology shift / new entrant / regulation / demand change]

Phase 3: [Current state] — "[Today's competitive landscape]"
  Key characteristics: [new leaders, new dynamics]

Outlook: [Where the landscape is heading]
  Driving forces: [what will shape the next phase]
```

### Brand Share Bridge Chart

Decompose total market share change as a waterfall/bridge:

```
Starting Share (Year N-1)
  + Gains from new product launches
  + Gains from distribution expansion
  + Gains from pricing strategy
  - Losses to competitor innovation
  - Losses from channel shifts
  - Losses from brand perception decline
  = Ending Share (Year N)
```

Visualize as a waterfall chart (green for gains, red for losses).

---

## 6. Data-to-Insight Methodology

### The Insight Discovery Process (5 Steps)

```
Step 1: OBSERVE — Spot an anomaly or pattern in the data
  "This number is surprisingly high/low/different from expectations"

Step 2: HYPOTHESIZE — Form a testable explanation
  "This might be because..."

Step 3: VALIDATE — Test the hypothesis with additional data
  "The data [confirms/refutes] this because..."

Step 4: ATTRIBUTE — Identify the root cause
  "The primary driver is X, secondary driver is Y"

Step 5: SYNTHESIZE — Distill into an actionable insight
  "[Stakeholder] should [action] because [finding] which means [implication]"
```

**Every analytical paragraph in the report should trace back to this 5-step process.** The paragraph may not spell out all 5 steps explicitly, but the analyst must have gone through them mentally.

### The "So What?" Test

Every data point in the report must pass this test:

```
Data point: "Category X grew 15% YoY"
So what?  → "This outpaced the overall market growth of 8%"
So what?  → "Category X is gaining wallet share from adjacent categories"
So what?  → "Brands in Category X should invest in capacity/distribution now
             while the growth window is open"
```

**Rule**: Keep asking "So what?" until you reach an actionable implication. If you can't get to an action, the data point doesn't belong in the report.

### Comparison-Driven Insight

Insights emerge from comparisons, not from isolated data points. Always compare against at least one benchmark:

| Comparison Type | Example | Insight Trigger |
|----------------|---------|-----------------|
| **YoY** (year-over-year) | "Growth decelerated from 25% to 12%" | Trend change |
| **QoQ** (quarter-over-quarter) | "Q4 was 3x Q3" | Seasonality or event-driven spike |
| **Cross-category** | "Skincare grew 20% while makeup declined 5%" | Category substitution |
| **Cross-channel** | "Online grew 30% while offline fell 8%" | Channel migration |
| **Cross-region** | "Tier 1 cities declined while Tier 3 grew" | Demand shift |
| **vs. Consensus** | "Actual was 2x analyst expectations" | Market mispricing |
| **vs. Benchmark** | "Company A's margin is 10pp above industry average" | Competitive advantage |

### Insight Quality Criteria

A good insight meets ALL four criteria:

1. **Specific**: Contains a concrete number, percentage, or named entity — not vague generalization
2. **Quantified**: The magnitude of the finding is clearly stated
3. **Actionable**: Leads to a concrete recommendation for a specific stakeholder
4. **Causal**: Explains WHY, not just WHAT — includes a cause-and-effect chain

**Bad example**: "The market is growing" (vague, no magnitude, no action, no causation)

**Good example**: "Category X grew 22% YoY driven primarily by penetration gains in Tier 3-4 cities (+8pp), suggesting brands should accelerate distribution in lower-tier markets where the growth ceiling remains high (current penetration 15% vs. 45% in Tier 1)"

### Insight-to-Recommendation Template

```
INSIGHT: [What we found — specific, quantified]
DRIVER: [Why this is happening — root cause]
IMPLICATION: [What this means — for whom, by when]
RECOMMENDATION: [What to do — specific action, expected impact]
```

Every recommendation section in the report should follow this structure. Recommendations without clear insight backing are opinions, not analysis.

---

## Adaptation Guide

This framework is designed for consumer/retail markets but can be adapted:

- **For B2B markets**: Replace "penetration × frequency × spend" with "number of accounts × contract value × renewal rate"
- **For technology markets**: Add "adoption curve" analysis (innovators → early adopters → early majority)
- **For service markets**: Add "utilization rate" and "lifetime value" to the growth decomposition
- **For platform/marketplace markets**: Add "supply-side" and "demand-side" metrics separately

When adapting, always preserve:
1. The growth decomposition logic (what × how much × how often)
2. The competitive attribution framework (why shares shifted)
3. The 5-step insight discovery process
4. The "So what?" test for every data point
