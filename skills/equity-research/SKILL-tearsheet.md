---
name: equity-research-tearsheet
description: "Tear Sheet workflow for equity-research skill. Generates a concise 3-5 page PDF investment brief in a single session. Entry point after SKILL.md routes output_type = TEAR_SHEET."
---

# Tear Sheet Workflow

> **Mode**: Tear Sheet (single session, 3-5 page PDF)
> **Entry**: This file is read after `SKILL.md` routes `output_type = TEAR_SHEET`.
> **Core Principles**: See `SKILL.md` §Core Principles (already read).

---

## ⚠️ CRITICAL RULES

### DO NOT TAKE SHORTCUTS
- ✅ Complete ALL six-dimension analysis with data support — not vague summaries
- ✅ Fill EVERY cell in the investment thesis table (4 rows × 6 columns, no blanks)
- ✅ Include ≥4 catalyst events with specific dates
- ✅ Include 3 scenarios (Bull/Base/Bear) with specific numbers, not vague descriptions
- ✅ Analysis brief must be ≥1,500 words before entering Phase 4
- ❌ Do not fabricate data — if a data point is unavailable, note it and explain why
- ❌ Do not skip any dimension or leave sections as "N/A"
- ❌ Do not use placeholder text ("TBD", "to be determined", "[insert here]")

### PDF Generation
- ✅ Generate PDF from the self-contained HTML + CSS using headless browser `page.pdf()`
- ❌ **DO NOT call the environment PDF skill.** Tear sheets use their own CSS and `@page` rules.
- ❌ **DO NOT add a cover page.** The tear sheet starts directly with the header bar.

### Industry Chain Diagram Height
- ✅ Use `.chart-container-free` for the industry chain SVG container (height: auto, no max-height)
- ❌ **DO NOT use `.chart-container`** for industry chain diagrams — it has `max-height: 170px` (designed for stock charts only) and will severely truncate the diagram

### Output Quality
- ✅ Final PDF must be 3-5 pages (check after generation, adjust if outside range)
- ✅ Every data point must have a real source — no fabrication
- ✅ All charts must use `scripts/stock_chart_generator.py` (not manually coded SVGs)
- ❌ Do not deliver the analysis brief unless the user explicitly asks for it

### ⚠️ MANDATORY: Re-Check After EVERY HTML Edit
- ✅ After ANY change to the HTML (even a single CSS class fix), re-run the FULL QA loop (see `output/tearsheet-qa.md` §5.3)
- ✅ Before every PDF generation: verify HTML has exactly 1 `</body>` and 1 `</html>` — if more, the HTML is duplicated and MUST be regenerated
- ✅ After every PDF generation: check page count IMMEDIATELY — if >5 pages, something is broken (do NOT deliver)
- ❌ **NEVER deliver a report without re-running QA after your last edit** — this is the #1 cause of broken outputs
- ❌ **NEVER assume a "small fix" doesn't need re-checking** — small fixes frequently introduce regressions

---

## Hard Gate Table (Tear Sheet)

Before each Phase begins, complete the corresponding pre-inspection. **Any uncompleted item prohibits entry to that Phase.**

| Phase     | Pre-Inspection Item                                                          | Action if Incomplete                        |
| --------- | ---------------------------------------------------------------------------- | ------------------------------------------- |
| Phase 1   | Confirmed `references/data-sources.md` is read                               | Immediately ReadFile, then continue         |
| Phase 1   | Confirmed `references/data-sources-detail.md` is read (if API params needed) | Immediately ReadFile or Grep, then continue |
| Phase 2.1 | Confirmed `modules/industry-chain.md` is read                                | Immediately ReadFile, then continue         |
| Phase 2.2-2.3 | Confirmed `references/analysis-brief-template.md` §II, §III, §V is understood (contains moat / management / earnings-quality frameworks) | Re-read template, then continue |
| Phase 2.4 | Confirmed `analysis/six-dimension-analysis.md` is read                       | Immediately ReadFile, then continue         |
| Phase 2.5 | Confirmed `analysis/investment-logic.md` is read                             | Immediately ReadFile, then continue         |
| Phase 2.5 | Confirmed `valuation/comparable.md` is read                                  | Immediately ReadFile, then continue         |
| Phase 4   | Confirmed Phase 3 six-dimension mapping table is complete                    | Return to Phase 3 to complete               |
| Phase 4   | Confirmed `output/tearsheet-layout.md` is read                               | ReadFile immediately                        |
| Phase 5   | Confirmed `output/tearsheet-qa.md` is read                                   | ReadFile immediately                        |
| Phase 5   | Confirmed `scripts/report_validator.py` has been run                         | Run script                                  |

---

## Phase 0.1: Market Identification and Language Confirmation

| Suffix | Market | Benchmark Index |
|--------|--------|-----------------|
| `.SH` `.SZ` `.BJ` | A-shares (A股) | Shanghai Index (000001.SH) |
| `.HK` | HK stocks (港股) | Hang Seng Index (HSI) / Hang Seng Tech (HSTECH) |
| `.US` or no suffix US stocks | US stocks | S&P 500 (^GSPC) |

**Language Selection (Intelligent Judgment, Not Hard-Coded Rules)**:

Report language is determined by agent based on context. Core logic:
- Observe whether user's communication language and the stock's market "natural language" are consistent
- **When consistent use directly**: Chinese user + A-shares/HK stocks → Chinese report; English user + US stocks → English report
- **When mismatched, actively ask**: Chinese user + US stocks, English user + A-shares, etc., actively ask user's preferred report language

**Language Confirmation Gate (Must Follow)**:

```
Step 1: Determine if language is explicit
  ├─ User communication language consistent with market "natural language" → Language confirmed, directly enter Step 3
  └─ User communication language mismatched with market "natural language" → Enter Step 2

Step 2: Actively ask and wait for response (mismatched only)
  ├─ Ask user: "Would you prefer the report in Chinese or English?"
  └─ ⛔ Stop here, MUST wait for user response, prohibit continuing subsequent Phase without response

Step 3: Language confirmation check
  └─ Confirm language is explicit (Chinese or English) → May enter Phase 0.2
```

Record confirmed language: Chinese → `.report-container`; English → `.report-container report-container-en`

### 0.2 Key Date Detection

```
Report Date: YYYY-MM-DD
Latest Trading Date: YYYY-MM-DD
Latest Financial Report: YYYY-MM-DD (reporting period)
Next Earnings Estimated: YYYY-MM-DD (reporting period)
```

### 0.3 Page Target

| Default | Range |
|---------|-------|
| 4 pages | 3-5 pages |

### 0.5 Benchmark Index

Benchmark index codes in `references/data-sources.md` §Benchmark Index Codes.

---

## Phase 1: Data Collection

**Pre-inspection:**
1. Confirm `references/data-sources.md` is read
2. When checking API parameters, confirm `references/data-sources-detail.md` is read
3. If any file unread, **immediately stop**, ReadFile then continue

**This phase collects raw data only. No analysis, no chart generation.**

### 1.1 Data Source Priority

Brief priority: iFind > Yahoo Finance > 天眼查 > Web Search. Details in `references/data-sources.md`.

### 1.1a Web Search Budget

> **Why this matters**: Web search is slow and burns context. Without a cap, the agent
> tends to loop on "let me find one more confirming source" — wasting time without
> meaningfully improving the report.

**Cap: ≤12 web searches per tear sheet session.** This budget covers Phases 1-3 combined
(data collection + analysis + recent news for catalysts). API calls (iFind, Yahoo) do
NOT count against this cap; only `WebSearch` and `WebFetch` calls do.

**When approaching the cap (≥10 used)**:
- Stop searching for "the perfect source"; consolidate what you have
- A 90% answer with one source is better than a 95% answer that took 5 more searches
- Genuine data gaps should flow to §IX Risks as "data limitation" disclosure, not block delivery

**When the cap is hit**: Proceed with available data. Note any unresolved questions in
the analysis brief's §IX Risks section.

### 1.2 Data Collection Checklist

- [ ] Company fundamentals (financial statements, business structure, management)
- [ ] Industry and competitive landscape (CR concentration, pricing power, supply chain)
- [ ] Equity structure (Chinese companies: 天眼查 `shareholder_info`; others: annual reports/SEC)
- [ ] Valuation and comparables (PE/PB/PS/EV, 3-5 comparable companies)
- [ ] Funding data (see `references/data-sources.md` §Short-term Investment Logic Dedicated Data Collection Rules)
- [ ] 52-week stock price + benchmark index CSV (see §1.3 below for retrieval protocol)


### 1.3 Stock Price Data Retrieval Protocol (MANDATORY)

**This is the single most data-critical module in the entire report** — using fabricated or simulated price data destroys the report's credibility. Full details (retry code, failure definitions, parameter diagnosis, benchmark tickers, skip annotation, pre-flight validation) live in the canonical specs; this section gives only the flow overview so you know what to read.

**Retrieval flow (applies to both stock and benchmark CSVs):**

```
iFind get_price × 3 attempts (with parameter diagnosis + exponential backoff)
   ↓ all fail
Yahoo Finance get_historical_stock_prices (fallback)
   ↓ fail
Skip stock chart module + insert "data unavailable" annotation
   ⛔ NEVER fabricate, simulate, or estimate prices
```

**Where the details live (read these before executing this module):**

| Need | Location |
|------|----------|
| Retry function (Python code), backoff strategy, full Step 1-5 implementation | `modules/stock-chart.md` §Generation Flow |
| What counts as a "failure" (timeout / empty / error code / <50 rows / exception) | `references/data-sources.md` §Stock Price Data Retry Protocol → Step 1 |
| Parameter diagnosis before each retry (ticker format, date format, cross-market mixing) | `references/data-sources.md` §API Parameter Diagnostic Workflow |
| `ifind_get_price` 5-parameter checklist | `references/data-sources.md` §ifind_get_price Parameter Checklist |
| Yahoo Finance fallback call + benchmark tickers (A股 `000001.SH` / HK `HSI` / US `^GSPC`) | `modules/stock-chart.md` Step 1 + `references/data-sources.md` §Benchmark Index Codes |
| Pre-script-call CSV `assert` validation + canonical skip annotation text | `modules/stock-chart.md` Step 2 |

**Non-negotiable rules** (kept here because they are enforcement boundaries, not implementation details):

- ⛔ Never call `stock_chart_generator.py` without two real CSV files passing the Step 2 `assert` validation.
- ⛔ Never fall back to mock / simulated / "representative" data after a single failure — exhaust the full retry chain (3 iFind + Yahoo) first.
- If the full chain fails, **skip the module** and annotate — do not block the rest of the report.

---

## Phase 2: Analysis

**Pre-inspection** (all must be read):
- [ ] `references/analysis-brief-template.md` §II Six-Dimension, §III Company Overview, §V Financials (covers moat / management / earnings-quality frameworks inline — no separate framework files needed)
- [ ] `analysis/six-dimension-analysis.md`
- [ ] `analysis/investment-logic.md`

If any unread, immediately stop and ReadFile.

### Depth Control (Tear Sheet) — Content-Rich Standard

| Dimension | Requirement |
|-----------|------------|
| Per-dimension output | **3-5 bullet points**, each with data + logic (not 1-2 sentence summaries) |
| Data tables | Inline summary with key figures |
| Cross-referencing | Not required |
| Valuation level | Level 1 only |
| Revenue analysis | Top-line growth + margin trends |
| Competitive analysis | Brief landscape in comps section |
| Market sizing | Not required |
| Projection documentation | Not required |
| Scenario analysis | Compact 3-scenario bullets **with specific numbers** |
| Risk assessment | 4-5 risk bullets **with impact quantification** |
| **Total analytical word count** | **~3,000-4,000 words** |

### Content Density Standard (Every Bullet Must Meet This)

Each bullet point in the final report must satisfy **ALL** of the following:

| Standard | Minimum Requirement | Example (Bad → Good) |
|----------|---------------------|---------------------|
| **Length** | ≥30 Chinese chars or ≥15 English words | "Revenue grew well" → "Revenue grew 23% YoY to ¥152bn (iFind Q3 2024), driven by 35% volume increase in core product line" |
| **Data** | ≥1 specific number (%, ¥, ratio, date) | "High gross margin" → "Gross margin 42.3%, +180bps YoY, 5pp above industry avg" |
| **Logic** | Explains "why" or "so what" — causal link | "PE is 15x" → "PE 15x below 5yr avg 22x, reflecting market concern over margin compression" |
| **Source** | Implied or explicit data attribution | Unsourced claim → "per iFind FY2024" / "company Q3 earnings" |

**Self-check before Phase 4**: Review analysis brief bullets. If any bullet is <30 chars with no numbers, expand it with data from Phase 1-2 analysis. Do NOT pass thin bullets to Phase 4.

### 2.1 Industry Background & Competitive Landscape

**Read**: `modules/industry-chain.md` + `valuation/comparable.md` §Competitive Landscape
**Output**: Industry analysis conclusion

### 2.2 Company Fundamentals Deep Research

**Reference**: `references/analysis-brief-template.md` §II (moat classification — 6 types with evidence) + §III Company Overview (Business Model / Management & Governance / Ownership). Use the template's bullet-length floors.
**Output**: Company fundamentals bullets for the analysis brief.

### 2.3 Financial Analysis

**Reference**: `references/analysis-brief-template.md` §V Financial Summary (earnings quality anomaly checks: OCF/NI, DSO/DIO/DPO trends, non-recurring items).
**Output**: Financial analysis conclusion (profitability, growth, solvency, cash flow, earnings quality signals).

### 2.4 Six-Dimension Deep Analysis

**Read**: `analysis/six-dimension-analysis.md` (sole source — DO NOT execute from memory)
**Output**: 6 dimension conclusions with data support and "So What"

### 2.5 Valuation & Investment Logic — Level 1

**Read**: `analysis/investment-logic.md` + `valuation/comparable.md`
**Valuation Level**: Level 1 (comparable companies + multiples + consensus expectations)
**Output**: Valuation conclusion + Investment logic framework + Investment thesis table

---

## Phase 3: Synthesis & Distillation

**Pre-inspection**:
- [ ] All 6 dimensions have explicit conclusions
- [ ] Each conclusion assigned to Phase 4 report module (see 3.2 mapping)

### 3.1 Core Investment Narrative

3-5 sentences connecting: industry trends → company strengths → financial performance → valuation judgment → key risks.

All subsequent modules must align with this narrative.

### 3.2 Six-Dimension → Module Mapping

| Six-Dimension Conclusion | Core Viewpoint | Report Module                                                    |
| ------------------------ | -------------- | ---------------------------------------------------------------- |
| One-sentence judgment    | [Conclusion]   | Caption title, 公司概览                                              |
| Market Pricing           | [Conclusion]   | Valuation module                                                 |
| Market Error             | [Conclusion]   | Investment logic (bullish/bearish)                               |
| Key Variable             | [Conclusion]   | Catalyst calendar, scenario analysis                             |
| Main Contradiction       | [Conclusion]   | Investment thesis table (competitive landscape row)              |
| Anomaly Signal           | [Conclusion]   | Investment thesis table (earnings quality row), risk, financials |

### 3.3 Investment Thesis Comprehensive Analysis Table

4 rows × 6 columns. Specification in `analysis/investment-logic.md` §投资论点综合分析表.

### 3.4 Output Document: Analysis Brief

Write conclusions to `{company}_{ticker}_analysis_brief.md` per `references/analysis-brief-template.md`.

**Analysis Brief Requirements**:
- ≥1,500 words. Each six-dimension section: ≥3 data-backed bullet points. All table cells filled.

**Self-check**: Read the Content Quality Gate at the bottom of `references/analysis-brief-template.md`. Every checkbox must pass. If any fails, return to Phase 2/3 to fill the gap.

---

## Phase 4: Visual Design + Report Generation

**Pre-inspection**: Phase 3.2 mapping complete. Analysis brief quality gate passed.

**Read `output/tearsheet-layout.md` now.** That file contains the complete Phase 4 instructions: HTML structure, module order, page layout diagram, module generation checklist, page break rules, PDF generation. CSS source: `output/tearsheet.css`.

### Phase 4 Supplementary Research

Phase 4 is primarily a presentation phase, but the agent should **actively seek supplementary information** when gaps are discovered during report writing:

- If a module's content from the analysis brief feels thin (e.g., only 1 bullet point for a section), do a quick Web Search to add 1-2 supporting data points before writing that module.
- If the catalyst calendar has fewer than 4 events, search for additional upcoming events.
- If comparable company data is incomplete, check iFind/Yahoo Finance for missing metrics.

---

## Phase 5: Quality Assurance

**Read `output/tearsheet-qa.md` now.** That file contains: automated validator instructions, layout self-check list, A/B/C tier quality inspection criteria (with correct margins and page targets), regression protection rules.

**Also required**: Run `scripts/report_validator.py --html [report.html] --json` as automated pre-check.
