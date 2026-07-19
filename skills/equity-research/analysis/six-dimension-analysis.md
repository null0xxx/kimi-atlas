# 六维分析 Framework (Authoritative Source) / Six-Dimension Analysis Framework

**[Note] This file is the authoritative complete source for 六维分析. SKILL.md does not contain detailed templates for 六维分析.**

---

## Overview

The 六维分析 framework is the core analysis tool for investment research reports and must be fully executed during Phase 2 (deep analysis).

**Mandatory Requirements**:
- Each dimension must have independent reasoning paragraph
- Every conclusion must have data support
- Distinguish information reliability levels during analysis phase (supporting reasoning), but final report should not show verification tags
- Each data point must answer "so what"

---

## Dimension 1: One-Sentence Company Stage

**Question**: What stage is this company in? What does it mean for investors?

```markdown
**Data Foundation** (3-5 core data points):
• Revenue Trend: [Specific data], YoY [X]%, QoQ [Y]%
• Profit Quality: [Net profit/Gross margin/ROE], [Specific value]
• Valuation Level: [PE/PB/PS], [Specific value], historical percentile [X]%
• Cash Flow: [Operating cash flow/Free cash flow], [Specific value]
• Market Position: [Market share/Industry ranking], [Specific data]

**Reasoning Process**:
• Based on above data, company is in [Growth/Maturity/Decline/Transformation] stage
• Excluded alternative explanations:
  - Not [Alternative 1], because [Data refutation]
  - Not [Alternative 2], because [Data refutation]

**Conclusion**:
• One-sentence qualitative: [What stage company is in, what it means for investors]
• Confidence: High/Medium/Low | Evidence: [Core data]
```

**Example (Premium Consumer Company / 消费龙头公司)**:
- Data Foundation: 2024 revenue RMB 174.1B (+15.7%), gross margin 92%, ROE 25.5%, PE 21x (5-year 30th percentile), operating cash flow RMB 92.5B
- Reasoning: In maturity stage but still stable growth. Rules out decline stage (double-digit growth), rules out high-speed growth (growth down from 30%+)
- Conclusion: Mature premium consumer leader suitable for core asset allocation. Confidence: High

---

## Dimension 2: What Market Is Pricing

**Question**: What expectations are embedded in current valuation? Are these expectations reasonable?

```markdown
**Valuation Breakdown**:
• Current Valuation: [PE/PB/PS], industry median: [Value], Premium/Discount: [X]%
• Historical Percentile: Past 5 years [X]%

**Implicit Assumption Restoration** (What growth is needed to support current market cap?):
• Assumption 1: [e.g., Future 3-year CAGR 15%]
• Assumption 2: [e.g., Gross margin maintains 90%+]
• Assumption 3: [e.g., Market share unchanged]

**Assumption Verification**:
| Assumption | Reasonableness | Data Support | Risk Point |
|------|--------|----------|--------|
| Assumption 1 | High/Medium/Low | [Data] | [Risk] |

**Conclusion**: Pricing judgment [Reasonable/Overpriced/Underpriced], Reason: [Explanation], Confidence: High/Medium/Low
```

---

## Dimension 3: Where Market May Be Wrong

**Question**: What have you spotted that is undervalued or overvalued? Positive or negative findings welcome.

```markdown
**Information Gap Analysis**:
• What I see: [Specific information]
• What market may miss: [Why it's overlooked]
• Information source: [Source] | Timeliness: [Recency]

**Expectation Gap Direction**:
• Positive expectation gap: [Undervalued positive factor]
  - Impact: High/Medium/Low | Timing: Short/Medium/Long-term | Trigger: [Condition]
• Negative expectation gap: [Undervalued negative factor]
  - Impact: High/Medium/Low | Timing: Short/Medium/Long-term | Trigger: [Condition]

**Conclusion**: Most likely expectation gap direction [Positive/Negative], Evidence: [Data], Confidence: High/Medium/Low
```

---

## Dimension 4: Key Variables

**Question**: In next 6 months, which 1-2 variables would most change the view?

```markdown
**Variable 1**: [Variable name]
• Why select this: [Importance explanation]
• Bull scenario: [Description], Probability [X]%, Impact [+/-Y%]
• Base scenario: [Description], Probability [Y]%, Impact [+/-Z%]
• Bear scenario: [Description], Probability [Z]%, Impact [+/-W%]
• Monitoring metrics: [Tracking method]

**Variable 2 (Strongly recommend including fund flow/market sentiment)**: [Variable name]
• Why select this: In short-term, stock prices often driven by fund flows and sentiment, especially 解禁, major shareholder 减持, 定增 unlock, 北向资金 sustained outflows can cause significant volatility without fundamental changes
• Bull scenario: [Fund flow improvement, e.g., major shareholder 增持/回购 acceleration/北向 large inflow], Probability [X]%, Impact [+/-Y%]
• Bear scenario: [Fund flow deterioration, e.g., large 解禁+减持 announcements+institutional sustained selling], Probability [Z]%, Impact [+/-W%]
• Monitoring metrics: [北向 daily net inflow, 龙虎榜 institutional seats, 大宗交易 discount rate, 解禁 countdown]

**Variable Sensitivity Analysis**:
| Variable | Current State | Direction | Valuation Impact |
|------|----------|----------|------------|
| Variable 1 | [State] | Up/Down | +X%/-Y% |
| Variable 2 (Fund Flow) | [State] | Up/Down | +X%/-Y% |
```

---

## Dimension 5: Main Contradiction (Bull vs. Bear Debate)

**Question**: What is the biggest point of disagreement between bulls and bears?

```markdown
**Strongest Bull Arguments**:
• Argument 1: [Argument], [Data support]
• Argument 2: [Argument], [Data support]
• Argument 3: [Argument], [Data support]

**Strongest Bear Arguments**:
• Argument 1: [Argument], [Data support]
• Argument 2: [Argument], [Data support]

**Disagreement Point Analysis**:
| Disagreement Dimension | Bull View | Bear View | Core Disagreement |
|----------|----------|----------|----------|
| Dimension 1 | [View] | [View] | [Core dispute] |

**Which side holds up better?**
• Judgment: [Bull/Bear/Neutral]
• Reasoning: [Data analysis]
• Key verification point: [Data or event to verify/refute one side]
```

---

## Dimension 6: Data Anomalies

**Question**: What anomalies in financial/operational data deserve scrutiny?

```markdown
**Anomaly 1 (Financial/Operating Data)**: [Anomaly description]
• What is the anomaly: [Specific data]
• What should be normal: [Comparison baseline]
• Possible explanation 1: [Explanation], Confidence [X]%
• Possible explanation 2: [Explanation], Confidence [Y]%
• If explanation 1 holds: [Impact on investment judgment]
• If explanation 2 holds: [Impact on investment judgment]
• Verification method: [How to verify]

**Anomaly 2 (Fund Flow/Market Behavior Data, New Mandatory Item)**: [Anomaly description]
• Anomaly signal: [Specific data, e.g., "北向 net outflow >RMB 2B in past 5 days, largest consecutive outflow in half year", "大宗交易 discount >10% with surging volume", "Major shareholder 减持 announcement involves RMB XX billion market cap"]
• Market norm: [Comparison baseline, e.g., "Past 3 months average 北向 monthly inflow ~RMB 500M"]
• Possible explanation 1: [Normal fund rotation/reallocation], Confidence [X]%
• Possible explanation 2: [Well-informed funds worried about fundamentals/policy], Confidence [Y]%
• Impact: If explanation 2 holds, short-term may face [X]% valuation compression/stock price pressure
• Verification method: [Track subsequent fund flows + 龙虎榜 seats + further 减持 announcements]

**Anomaly Signal Summary Table**:
| Anomaly | Severity | Short-term Impact | Long-term Impact | Follow-up Needed |
|------|----------|----------|----------|--------|
| Anomaly 1 | High/Medium/Low | [Impact] | [Impact] | Yes/No |
| Anomaly 2 (Fund Flow/Market Behavior) | High/Medium/Low | [Impact] | [Impact] | Yes/No |
```

---

## 六维分析 Integration Output

Upon completing 六维分析, integrate into following format:

```markdown
## Core Investment Judgment

**One-sentence Summary**: [Core investment conclusion based on 六维分析]

**Key Data Support**:
• [Data 1] • [Data 2] • [Data 3]

**Bull vs. Bear Comparison**:
• Bull core argument: [Summary]
• Bear core argument: [Summary]
• Our position: [Position and reasoning]

**Key Monitoring Metrics**:
• [Metric 1]: [Monitoring method]
• [Metric 2]: [Monitoring method]

**Scenario Analysis**:
• Bull: [Description], Probability [X]%, Target price [Price]
• Base: [Description], Probability [Y]%, Target price [Price]
• Bear: [Description], Probability [Z]%, Target price [Price]
```

---

## "So What" Mandatory Analysis Requirement

**Each data point must explicitly complete the following template. Data alone without reasoning is not allowed.**

### Standard Format (Must follow)

```markdown
**Data Point**: [Specific value + context like YoY/QoQ/percentile]
**What It Means**: [Data's position in industry/history/competition or direction of change]
**Impact on Investment Judgment**: [How data supports or weakens current investment conclusion]
```

### Example (Must reach this depth)

```markdown
**Data Point**: 2024 revenue +15.7% YoY (2023: +18%)
**What It Means**: Growth decelerated consecutive second year, but still exceeds industry average +8%
**Impact on Investment Judgment**: Company growth resilience intact, but must watch for growth entering downtrend, current valuation needs safety margin
```

### Minimum "So What" Requirements by Dimension

| Dimension | Question Each Data Point Must Answer |
|------|------------------------|
| Dimension 1 | How does this data support "company in X stage" judgment? |
| Dimension 2 | How does this data prove whether current valuation's implicit assumption is reasonable? |
| Dimension 3 | What information overlooked by market does this data reveal? |
| Dimension 4 | How does this data quantify key variable sensitivity? |
| Dimension 5 | How does this data support "which side holds up better"? |
| Dimension 6 | If this data anomaly is verified/refuted, how would it change investment judgment? |

**Data points without "so what" reasoning are considered incomplete analysis.**

## Information Classification Tags (For Phase 2-3 Analysis Only, Do Not Output to Final Report)

The following tags are for internal analysis reasoning only. **Final report HTML must never include these tags.**

| Tag | Meaning | Use Case |
|------|------|----------|
| 【已验证】 | Verified by published financial reports | Historical financial data |
| 【部分验证】 | Preliminary data available but not fully confirmed | Channel research, industry data |
| 【未验证】 | Market expectations or forward-looking information | Earnings forecasts, consensus estimates |

---

## Quality Checklist

```markdown
□ Dimension 1: 3-5 data points + reasoning process + conclusion and confidence
□ Dimension 2: Complete valuation breakdown + implicit assumption restoration + assumption verification
□ Dimension 3: Information gap identified + positive/negative expectation gaps + clear conclusion
□ Dimension 4: 1-2 key variables + three scenarios + sensitivity analysis
□ Dimension 5: Complete bull/bear arguments + disagreement point analysis + clear judgment → mapped to 投资论点综合分析表 competition row (H1)
□ Dimension 6: At least 2 anomalies + explanations + verification method → mapped to 投资论点综合分析表 earnings quality row (H3)
□ Overall: Analysis phase distinguishes information reliability + each data point answers "so what" + logic coherent + final report contains no verification tags
```
