# Projection Assumptions Deep Dive — Equity Report Only

> **Scope**: This file is read ONLY when `output_type = EQUITY_REPORT`.
> It supplements (not replaces) the base six-dimension analysis by forcing granular,
> product-by-product and region-by-region assumption documentation.

---

## Purpose

Institutional-quality equity reports require transparent, auditable projection assumptions.
Every forward-looking number in the financial tables must trace back to a specific assumption
documented in this section. The goal is to let a reader challenge any single assumption
and understand its impact on the overall valuation.

---

## 1. Revenue Buildup — Segment Level

For EACH major business segment (minimum 3, ideally 4-6):

### Required Data Points Per Segment

| Element | Requirement | Example |
|---------|-------------|---------|
| **Historical revenue** | 3-5 years with YoY growth | FY22: $78.1B (+7.8%) |
| **Revenue driver decomposition** | Volume × Price (or Users × ARPU, Units × ASP) | iPhone units × ASP |
| **FY+1 estimate** | Consensus + our adjustment with rationale | Consensus $88B; our $86B (conservative on China) |
| **FY+2 and FY+3 estimates** | With growth rate assumption and basis | +6% (replacement cycle normalization) |
| **Market share assumption** | Current share + trajectory | 20% global → 21% (AI upgrade pull) |
| **Key risk to segment** | What breaks this estimate | Memory cost pass-through compresses ASP |

### Segment Buildup Table Template

```
Exhibit X: Revenue Projection by Segment ($B)

Segment       | FY24A | FY25A | FY26E | FY27E | FY28E | CAGR
─────────────────────────────────────────────────────────────
[Segment 1]   | xxx   | xxx   | xxx   | xxx   | xxx   | x.x%
  - Volume    | xxx   | xxx   | xxx   | xxx   | xxx   |
  - ASP/ARPU  | xxx   | xxx   | xxx   | xxx   | xxx   |
[Segment 2]   | xxx   | xxx   | xxx   | xxx   | xxx   | x.x%
  ...
─────────────────────────────────────────────────────────────
Total Revenue  | xxx   | xxx   | xxx   | xxx   | xxx   | x.x%
```

### Writing Requirement

For EACH segment, write a **bold-keyword paragraph** (`.kw-paragraph`) explaining:
1. The growth driver (what changes volume or price)
2. The basis for the estimate (management guidance, channel checks, industry data)
3. The key assumption that could be wrong
4. What we would see if the assumption breaks (monitoring signal)

**Minimum**: 150-200 words per segment. Total segment section: 600-1,200 words.

---

## 2. Revenue Buildup — Geographic Level

For companies with meaningful geographic diversification (>15% from any single non-home region):

### Required Per Geography

| Element | Requirement |
|---------|-------------|
| Historical revenue or % share | 3 years minimum |
| Growth driver for that region | Market expansion, penetration, pricing, regulation |
| Currency exposure | Functional currency, hedging, translation impact |
| Competitive dynamics | Different competitors by region |
| FY+1 through FY+3 estimate | With basis |

### Geographic Mix Table Template

```
Exhibit X: Revenue by Geography

Region          | FY24A  | %   | FY25A  | %   | FY26E  | %   | Driver
──────────────────────────────────────────────────────────────────────
[Home market]   | xxx    | xx% | xxx    | xx% | xxx    | xx% | [driver]
[Region 2]      | xxx    | xx% | xxx    | xx% | xxx    | xx% | [driver]
[Region 3]      | xxx    | xx% | xxx    | xx% | xxx    | xx% | [driver]
Other           | xxx    | xx% | xxx    | xx% | xxx    | xx% |
──────────────────────────────────────────────────────────────────────
Total           | xxx    | 100%| xxx    | 100%| xxx    | 100%|
```

**Minimum**: 100-150 words per material region. Total geographic section: 300-600 words.

---

## 3. Margin Bridge

Document how margins evolve from current to projected:

### Gross Margin Bridge

| Driver | Impact (bps) | Basis |
|--------|-------------|-------|
| Revenue mix shift (e.g., Services growing faster) | +XX bps | Services at 70% GM vs. Hardware at 35% |
| Input cost changes (COGS, raw materials, memory) | ±XX bps | Memory pricing cycle, commodity outlook |
| Pricing power / ASP trends | ±XX bps | Premium positioning, competition |
| FX impact | ±XX bps | Currency exposure, hedging |
| **Net GM change** | **+XX bps** | FY25 → FY26E: XX.X% → XX.X% |

### Operating Margin Bridge

| Driver | Impact (bps) | Basis |
|--------|-------------|-------|
| Operating leverage (revenue growth > OpEx growth) | +XX bps | Fixed cost base on SG&A |
| R&D investment trajectory | ±XX bps | % of revenue trend, capitalization |
| SG&A efficiency | ±XX bps | Channel optimization, marketing ROI |
| One-time items | ±XX bps | Restructuring, litigation, impairment |
| **Net EBIT margin change** | **+XX bps** | FY25 → FY26E: XX.X% → XX.X% |

**Writing requirement**: 200-300 words narrating the margin bridge, explaining which driver matters most and why.

---

## 4. Capital Expenditure & Working Capital

### CapEx Assumptions

| Element | Requirement |
|---------|-------------|
| Historical CapEx / Revenue % | 3-5 years |
| Management guidance (if any) | Quote or paraphrase |
| CapEx type split | Maintenance vs. Growth (if estimable) |
| FY+1 through FY+3 CapEx estimate | $ amount and % of revenue |
| Key driver | Capacity expansion, technology upgrade, regulatory |

### Working Capital Assumptions

| Element | Requirement |
|---------|-------------|
| Days Sales Outstanding (DSO) trend | 3 years + projection |
| Days Inventory Outstanding (DIO) trend | 3 years + projection |
| Days Payable Outstanding (DPO) trend | 3 years + projection |
| Cash Conversion Cycle trend | Improving/stable/deteriorating |
| Working capital as % of revenue | Historical + projected |

**Writing requirement**: 150-200 words. Highlight any structural changes (e.g., shift to subscription model improving working capital).

---

## 5. Tax Rate & Other Assumptions

| Element | Assumption | Basis |
|---------|-----------|-------|
| Effective tax rate | XX% | Statutory rate ± permanent differences |
| Share count | XX.XB (diluted) | Buyback trajectory, option dilution |
| D&A as % of revenue | X.X% | Asset base, useful life policies |
| Interest expense | $XXM | Debt outstanding, avg coupon |
| Minority interest / JVs | $XXM | Consolidated vs. equity method |

---

## 6. Assumption Sensitivity Tags

For each major assumption, tag its sensitivity impact on the final valuation:

| Assumption | Base Case | Bull Variant | Bear Variant | Valuation Swing |
|-----------|-----------|-------------|-------------|----------------|
| iPhone revenue growth | +5% | +10% | 0% | ±$25/share |
| Services margin | 72% | 75% | 68% | ±$15/share |
| Terminal growth rate | 3.0% | 3.5% | 2.0% | ±$40/share |
| WACC | 7.4% | 6.9% | 8.4% | ±$30/share |

This table directly links to the scenario-deep-dive.md and sensitivity analysis.

---

## Output Quality Gate

- [ ] ≥3 segments with volume/price decomposition
- [ ] Geographic breakdown if company has >15% non-home revenue
- [ ] Gross margin bridge with ≥3 drivers quantified in bps
- [ ] Operating margin bridge with ≥3 drivers quantified in bps
- [ ] CapEx and working capital assumptions documented
- [ ] Total section word count ≥1,500 words (target 2,000-2,500)
- [ ] Every forward number traces to a documented assumption
- [ ] Assumption sensitivity tags connect to scenario analysis
