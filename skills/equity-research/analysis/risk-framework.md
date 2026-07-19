# Structured Risk Framework — Equity Report Only

> **Scope**: This file is read ONLY when `output_type = EQUITY_REPORT`.
> It replaces the brief risk bullet points used in the tear sheet with a comprehensive,
> categorized risk assessment featuring probability × impact scoring.

---

## Purpose

Institutional research demands more than a list of risks — it requires:
- Categorization across multiple risk domains
- Quantification of probability and potential impact
- Identification of monitoring signals for each risk
- Prioritization via a risk matrix
- Connection to scenario analysis and valuation

The tear sheet can list 4-5 risks in compact bullets.
The equity report must identify **8-12 distinct risks** across **4 categories**,
each with structured assessment data.

---

## 1. Risk Categories

### Category A: Company-Specific Risks (4-6 risks)

Risks unique to the target company's business model, operations, or strategy.

**Required subtypes to evaluate**:
- Execution risk (management delivery, product launches, integration)
- Key person risk (CEO succession, critical talent departure)
- Customer/supplier concentration risk
- Technology risk (obsolescence, IP challenges, development failure)
- Capital allocation risk (overinvestment, M&A track record)
- Governance / accounting risk (audit quality, related-party, disclosure)

### Category B: Industry / Market Risks (2-4 risks)

Risks affecting the entire sector or competitive environment.

**Required subtypes to evaluate**:
- Competitive intensity (new entrants, price wars, market share shifts)
- Demand cyclicality (economic sensitivity, replacement cycle exhaustion)
- Disruption risk (business model, technology, regulatory-driven)
- Supply chain risk (input cost, single-source, geopolitical)

### Category C: Financial Risks (2-3 risks)

Risks embedded in the company's financial structure.

**Required subtypes to evaluate**:
- Leverage risk (debt/EBITDA, interest coverage, refinancing)
- Liquidity risk (cash runway, working capital, FCF sufficiency)
- Currency risk (revenue/cost currency mismatch, translation)
- Valuation risk (multiple compression, DCF sensitivity, crowded positioning)

### Category D: Macro / Regulatory Risks (2-3 risks)

External forces beyond the company's or industry's control.

**Required subtypes to evaluate**:
- Interest rate sensitivity (duration, cost of capital, consumer credit)
- Regulatory risk (antitrust, data privacy, environmental, industry-specific)
- Geopolitical risk (trade tensions, sanctions, supply chain disruption)
- Macro cycle risk (recession, inflation, unemployment)

---

## 2. Risk Assessment Template

For EACH identified risk (8-12 total), document:

### Per-Risk Data Card

| Field | Content |
|-------|---------|
| **Risk ID** | R1, R2, R3... |
| **Category** | A (Company) / B (Industry) / C (Financial) / D (Macro) |
| **Risk Title** | Concise name (5-10 words) |
| **Description** | What could go wrong? (50-80 words) |
| **Probability** | Low (10-25%) / Medium (25-50%) / High (50-75%) / Very High (>75%) |
| **Impact** | Low (±5% on valuation) / Medium (±5-15%) / High (±15-30%) / Very High (>30%) |
| **Priority Score** | Probability × Impact matrix position |
| **Time Horizon** | Near-term (0-12 months) / Medium-term (1-3 years) / Long-term (3+ years) |
| **Mitigation** | What is the company doing to address this? (or: unmitigated) |
| **Monitoring Signal** | What data point would indicate this risk is materializing? |
| **Connection to Scenario** | Which scenario (Bull/Base/Bear) does this risk primarily affect? |

---

## 3. Risk Summary Table

```
Exhibit X: Risk Assessment Matrix

ID | Category | Risk                        | Prob.  | Impact | Priority | Horizon  | Monitor Signal
────────────────────────────────────────────────────────────────────────────────────────────────────
R1 | D-Reg    | DOJ antitrust ruling        | MED    | HIGH   | ■■■■     | 1-3Y     | Court filings
R2 | B-Comp   | AI feature parity by rivals | MED    | MED    | ■■■      | 6-18M    | Feature launches
R3 | B-Supply | Key foundry single-source risk | LOW    | V.HIGH | ■■■      | Ongoing  | Geopolitical
R4 | A-Exec   | CEO succession              | MED    | MED    | ■■■      | 1-3Y     | Board announcements
R5 | C-Val    | Multiple compression        | MED    | MED    | ■■■      | 0-12M    | 10Y Treasury
R6 | D-Reg    | EU DMA enforcement          | HIGH   | MED    | ■■■■     | Ongoing  | EC rulings
R7 | A-Prod   | Flagship product cycle exhaustion | MED    | HIGH   | ■■■■     | 6-18M    | Quarterly units
R8 | C-Cost   | Memory cost inflation       | HIGH   | LOW    | ■■       | 0-12M    | DRAM spot prices
R9 | D-Geo    | China geopolitical tension  | LOW    | HIGH   | ■■■      | 1-3Y     | Trade policy
...
```

**Priority scoring legend**:
- ■■■■■ = Critical (High Prob × High Impact) — must be in executive summary
- ■■■■ = Significant — discussed in detail
- ■■■ = Moderate — documented and monitored
- ■■ = Low — acknowledged
- ■ = Minimal — listed for completeness

---

## 4. Risk Narrative

### Top 3 Risks — Extended Discussion

For the 3 highest-priority risks, write a **dedicated paragraph** (150-200 words each):

1. **Full description** of the risk mechanism
2. **Historical precedent** (has this risk materialized before, for this company or peers?)
3. **Quantified impact** (what would happen to revenue, earnings, or valuation?)
4. **Management response** (what is the company doing or could do?)
5. **Our assessment** (probability-weighted view, is the market pricing this correctly?)

### Remaining Risks — Compact Format

For risks 4-12, use **bold-keyword paragraphs** (80-120 words each):
- `<span class="kw-lead">[Risk Name]:</span>` followed by description, probability assessment, and monitoring signal.

---

## 5. Risk-Reward Synthesis

Close the risk section with a 150-200 word synthesis:
- Overall risk profile: Is this a high-risk/high-reward or low-risk/moderate-reward stock?
- Risk asymmetry: Are upside risks (positive surprises) balanced against downside risks?
- Risk pricing: Are the major risks already reflected in the current valuation?
- Key risk to our thesis: Which single risk would most challenge our base case?

---

## Integration with Other Analysis Files

- **Scenario deep dive** (`scenario-deep-dive.md`): Top risks map to Bear case triggers
- **Projection assumptions** (`projection-assumptions.md`): Risk impacts quantify assumption sensitivity
- **Competitive landscape** (`research-document-template.md §IV` — Competitive Landscape + Entry Barriers): Industry risks inform competitive positioning
- **Six-dimension H5** (main contradiction): The highest-priority risk often aligns with the bull/bear debate

---

## Output Quality Gate

- [ ] 8-12 distinct risks identified
- [ ] All 4 categories represented (A: 4-6, B: 2-4, C: 2-3, D: 2-3)
- [ ] Risk summary table with probability × impact scoring
- [ ] Top 3 risks have extended narrative (150-200 words each)
- [ ] Remaining risks have compact narrative (80-120 words each)
- [ ] Risk-reward synthesis paragraph (150-200 words)
- [ ] Monitoring signals for each risk
- [ ] Connection to scenario analysis documented
- [ ] Total section word count ≥1,200 words (target 1,500-1,800)
