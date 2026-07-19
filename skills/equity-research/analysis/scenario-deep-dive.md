# Scenario Deep Dive — Equity Report Only

> **Scope**: This file is read ONLY when `output_type = EQUITY_REPORT`.
> It supplements the base scenario/risk section from `modules/tables.md` by requiring
> fully quantified, probability-weighted scenario analysis with catalyst mapping.

---

## Purpose

The tear sheet scenario section uses compact bullet points in a two-column layout.
The equity report must expand this into a rigorous framework where each scenario has:
- Specific quantified assumptions (not vague directional statements)
- A probability weight that sums to 100%
- A valuation outcome per scenario
- Catalyst triggers with timing
- Monitoring signals that would cause us to shift between scenarios

---

## 1. Scenario Construction Framework

### Three Scenarios Required (minimum)

| Element | Bull Case | Base Case | Bear Case |
|---------|-----------|-----------|-----------|
| **Probability** | 15-25% | 45-60% | 20-30% |
| **Revenue growth (FY+1)** | Specific % | Specific % | Specific % |
| **Revenue growth (FY+2)** | Specific % | Specific % | Specific % |
| **EBIT margin (FY+2)** | Specific % | Specific % | Specific % |
| **Terminal PE or EV/EBITDA** | Specific x | Specific x | Specific x |
| **Target price** | $XXX | $XXX | $XXX |
| **Upside/downside vs current** | +XX% | ±XX% | -XX% |

**Hard constraint**: Probabilities must sum to 100%. Base case must be 45-60%.

### Probability-Weighted Target

```
Weighted Target = P(Bull) × Bull Price + P(Base) × Base Price + P(Bear) × Bear Price
```

Document this calculation explicitly. Compare to current price for expected return.

---

## 2. Per-Scenario Deep Dive

For EACH of the three scenarios, write a dedicated subsection with:

### 2.1 Bull Case (~250-400 words)

**Structure**:
1. **Headline thesis** (1 sentence): What goes right?
2. **Key assumptions** (3-5 numbered items): Each with a specific metric
   - Example: "iPhone unit growth of +10% annually through FY28 as AI upgrade cycle extends to mid-cycle replacement"
3. **Catalysts with timing**:
   - Near-term (0-6 months): Specific events/data points
   - Medium-term (6-18 months): Structural shifts
4. **Valuation impact**: Which multiple re-rates and why
5. **What we would need to see** to increase Bull probability (monitoring signals)

### 2.2 Base Case (~250-400 words)

**Structure**:
1. **Headline thesis**: Most likely trajectory
2. **Key assumptions** (3-5 items): Conservative consensus-aligned
3. **What's already priced in**: Which assumptions are consensus
4. **Valuation method**: Primary method used for base target
5. **Key risks to base case**: What could push to Bull or Bear

### 2.3 Bear Case (~250-400 words)

**Structure**:
1. **Headline thesis**: What goes wrong?
2. **Key assumptions** (3-5 items): Each with a specific downside metric
3. **Trigger events**: What would cause the bear case to materialize
4. **Downside protection**: Floor valuation, asset value, buyback support
5. **What we would need to see** to increase Bear probability

---

## 3. Scenario Comparison Table

### Financial Metric Comparison

```
Exhibit X: Scenario Financial Comparison

Metric              | Bull     | Base     | Bear     | Current Implied
────────────────────────────────────────────────────────────────────────
Revenue FY+1 ($B)   | xxx      | xxx      | xxx      | xxx
Revenue FY+2 ($B)   | xxx      | xxx      | xxx      | xxx
EBIT Margin FY+2    | xx.x%    | xx.x%    | xx.x%    | xx.x%
EPS FY+2            | $x.xx    | $x.xx    | $x.xx    | $x.xx
FCF Yield FY+2      | x.x%     | x.x%     | x.x%    | x.x%
Terminal PE          | xx.x     | xx.x     | xx.x     | xx.x
Target Price         | $xxx     | $xxx     | $xxx     | $xxx (current)
Return               | +xx%     | ±xx%     | -xx%     |
Probability          | xx%      | xx%      | xx%      |
```

### "Current Implied" Column

Reverse-engineer what assumptions the current stock price embeds:
- At current PE, what EPS growth is priced in?
- At current EV/EBITDA, what EBITDA growth is priced in?
- Which scenario does current pricing most closely resemble?

This is critical — it answers "what is the market betting on?" and identifies expectation gaps (links to H2/H3 from six-dimension analysis).

---

## 4. Scenario Transition Map

Document what would cause an investor to shift between scenarios:

| Transition | Trigger Signal | Data Source | Timeline |
|-----------|---------------|-------------|----------|
| Base → Bull | iPhone units exceed +8% for 2 consecutive quarters | Quarterly earnings | 6-12 months |
| Base → Bear | Gross margin below 45% for 2 consecutive quarters | Quarterly earnings | 6-12 months |
| Bear → Base | DOJ settlement with limited behavioral remedies | Court filings | 12-24 months |
| Bull → Base | AI feature parity from competitors reduces differentiation | Market share data | 6-18 months |

---

## 5. Integration with Other Analysis Files

- **Projection assumptions** (`projection-assumptions.md`): Each scenario's revenue/margin numbers must be consistent with the segment-level buildup
- **Risk framework** (`risk-framework.md`): Bear case triggers should map to the top 3-4 risks identified
- **Sensitivity matrix** (`valuation/dcf-and-sensitivity.md` §Part 3): The WACC × growth grid should bracket the three scenario outcomes
- **Six-dimension H4** (key variables): The scenario transition triggers should align with H4's identified pivotal variables

---

## Output Quality Gate

- [ ] Three scenarios with specific quantified assumptions (not vague)
- [ ] Probabilities sum to 100%, Base case 45-60%
- [ ] Each scenario has ≥250 words of dedicated narrative
- [ ] Probability-weighted target calculated explicitly
- [ ] "Current implied" column shows what the market prices in
- [ ] Scenario transition map with ≥4 trigger signals
- [ ] Total section word count ≥1,000 words (target 1,200-1,500)
- [ ] Cross-references to projection-assumptions.md and risk-framework.md
