---
name: equity-research-task1
description: "Task 1 of equity report workflow. Produces a Research Document (≥6,000 words) consumed by Task 2 and Task 3. Entry point after SKILL.md routes output_type = EQUITY_REPORT."
---

# Equity Report — Task 1: Research + Analysis

> **Mode**: Equity Report (3-Task Architecture)
> **This is Task 1 of 3.** It produces a Research Document (≥6,000 words) consumed by Task 2 and Task 3.
> **Entry**: This file is read after `SKILL.md` routes `output_type = EQUITY_REPORT`.
> **Core Principles**: See `SKILL.md` §Core Principles (already read).

---

## ⚠️ CRITICAL RULES

### DO NOT TAKE SHORTCUTS
- ✅ Write the full Research Document — ≥6,000 words, every section complete
- ✅ §VI Historical Financials: Fill ALL cells for ≥3 years of IS/BS/CF (no blanks, no "N/A")
- ✅ §VII Revenue Model: ≥3 segments with Volume × Price decomposition
- ✅ §IV Competitive: ≥5 named competitors with revenue and market share data
- ✅ Phase 2.7 deep research: Complete ALL 6 sub-steps with minimum word counts
- ✅ Every claim must have a real data source — no fabrication
- ❌ Do not abbreviate sections to save context — this document feeds Task 2 and Task 3
- ❌ Do not fabricate financial data — if unavailable, search harder or document the gap
- ❌ Do not skip Phase 2.7 or merge sub-steps — each produces distinct analytical output
- ❌ Do not use placeholder text ("TBD", "to be determined", "[insert data]")

### Task Boundary
- ✅ Deliver the Research Document and STOP
- ✅ Save stock chart SVG + CSVs alongside the document
- ❌ **Do not continue to Task 2.** The user must explicitly start the next task.
- ❌ **Do not create summary documents, next-steps guides, or any extra files.** Deliver ONLY the Research Document.

---

## Hard Gate Table (Equity Report Task 1)

Before each Phase begins, complete the corresponding pre-inspection. **Any uncompleted item prohibits entry to that Phase.**

| Phase | Pre-Inspection Item | Action if Incomplete |
|-------|-----------|---------------|
| Phase 1 | Confirmed `references/data-sources.md` is read | Immediately ReadFile, then continue |
| Phase 1 | Confirmed `references/data-sources-detail.md` is read (if API params needed) | Immediately ReadFile or Grep, then continue |
| Phase 2.1 | Confirmed `modules/industry-chain.md` is read | Immediately ReadFile, then continue |
| Phase 2.2-2.3 | Confirmed §II, §III, §IV requirements in `references/research-document-template.md` are understood | Re-read template, then continue |
| Phase 2.4 | Confirmed `analysis/six-dimension-analysis.md` is read | Immediately ReadFile, then continue |
| Phase 2.5 | Confirmed `analysis/investment-logic.md` is read | Immediately ReadFile, then continue |
| Phase 2.5 | Confirmed `valuation/comparable.md` is read | Immediately ReadFile, then continue |
| Phase 2.6 | Confirmed `valuation/dcf-and-sensitivity.md` is read (L2 only) | Immediately ReadFile, then continue |
| Phase 2.7 | Confirmed `analysis/revenue-model.md` is read | Immediately ReadFile, then continue |
| Phase 2.7 | Confirmed `analysis/projection-assumptions.md` is read | Immediately ReadFile, then continue |
| Phase 2.7 | Confirmed `analysis/scenario-deep-dive.md` is read | Immediately ReadFile, then continue |
| Phase 2.7 | Confirmed `analysis/risk-framework.md` is read | Immediately ReadFile, then continue |

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
| ≥25 pages | 25-40 pages (user-specified) |

If user specifies a page target (e.g., "20-page report"), record and use for Task 3 validation.

### 0.4 Expansion Module Selection

Ask user or auto-determine based on company characteristics:

| Expansion Module | When to Include |
|-----------------|-----------------|
| ESG Analysis | User requests, or company in ESG-sensitive industry |
| Management Deep Dive | User requests, or recent management changes |
| Historical Valuation Review | Always included (part of Level 2 valuation) |
| Sub-Industry Detailed Analysis | Multi-segment conglomerates |
| Technical Roadmap / Patent | Tech, biotech, semiconductor companies |
| Shareholder Structure Tracking | Recent major shareholder changes |

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

> **Why this matters**: Web search is slow and burns context. An equity report needs more
> sources than a tear sheet (industry deep-dive + competitor profiles + regulatory context),
> but unlimited search invites diminishing returns and "perfect source" paralysis.

**Cap: ≤25 web searches across Task 1 (Phases 1-3 combined).** API calls (iFind, Yahoo)
do NOT count against this cap; only `WebSearch` and `WebFetch` calls do.

**Suggested allocation**:
- Phase 1 (Data Collection): ~10 searches (industry data, competitor identification, regulatory landscape)
- Phase 2 (Analysis): ~10 searches (TAM validation, moat evidence, management background, recent earnings transcripts)
- Phase 3 (Synthesis): ~5 searches (catalysts, recent news within 7 days, peer reactions)

**When approaching the cap (≥20 used)**:
- Stop hunting for incremental sources; consolidate what you have
- Prioritize remaining budget for time-sensitive items (recent news, catalysts)
- Genuine data gaps should flow to §X Risk Assessment as "data limitation" — they do NOT block delivery

**When the cap is hit**: Proceed with available data. Note unresolved questions in the
research document's §X Risks. Task 2/3 should not re-attempt these searches.

### 1.2 Data Collection Checklist (Core)

- [ ] Company fundamentals (financial statements, business structure, management)
- [ ] Industry and competitive landscape (CR concentration, pricing power, supply chain)
- [ ] Equity structure (Chinese companies: 天眼查 `shareholder_info`; others: annual reports/SEC)
- [ ] Valuation and comparables (PE/PB/PS/EV, 3-5 comparable companies)
- [ ] Funding data (see `references/data-sources.md` §Short-term Investment Logic Dedicated Data Collection Rules)
- [ ] 52-week stock price + benchmark index CSV (**must** call `scripts/stock_chart_generator.py`, prohibit manual code)

### 1.3 Additional Data Collection

- [ ] 5-year historical financial statements (for DCF and historical band)
- [ ] CapEx, D&A, working capital breakdown (for FCF projection)
- [ ] Beta and risk metrics
- [ ] Historical valuation data (5-year PE/PB weekly)
- [ ] Segment-level financial data (if SOTP applicable)
- [ ] ESG data (if ESG module included)
- [ ] Management track record and compensation data (if management deep dive included)

### 1.4 Deep Research Data Collection (feeds Phase 2.7)

- [ ] Segment-level revenue with volume and price/ASP breakdown (3-5 years)
- [ ] Industry/market sizing data: TAM estimates from research firms, industry associations
- [ ] Competitor financials: revenue, margins, growth for top 5-8 peers
- [ ] Market share data: current and 3-year trend (by revenue or units)
- [ ] Consensus estimates: FY+1 and FY+2 revenue, EPS from analyst consensus
- [ ] Regulatory landscape: pending legislation, enforcement actions, timeline
- [ ] Geographic revenue breakdown (if >15% from non-home market)

---

## Phase 2: Analysis

**Pre-inspection** (all must be read):
- [ ] `references/research-document-template.md` §II Six-Dimension Deep Analysis, §III Company Overview, §IV Industry & Competitive Landscape (read if you did not read them during Phase 0)
- [ ] `analysis/six-dimension-analysis.md`
- [ ] `analysis/investment-logic.md`

If any unread, immediately stop and ReadFile. The research-document-template already contains the full frameworks for moat classification, earnings-quality checks, and management assessment — do not look for separate files.

### Depth Control (Equity Report)

| Dimension | Requirement |
|-----------|------------|
| Per-dimension output | 2-3 paragraph deep-dives |
| Data tables | Supporting charts/tables inline |
| Cross-referencing | Cross-reference between dimensions |
| Valuation level | L2: Level 1 + Level 2; L1: Level 1 only |
| Revenue analysis | Segment-level volume × price decomposition (Phase 2.7) |
| Competitive analysis | 5-8 named competitors with positioning (Phase 2.7) |
| Market sizing | TAM/SAM/SOM with growth drivers (Phase 2.7) |
| Projection documentation | Product-by-product assumptions documented (Phase 2.7) |
| Scenario analysis | Quantified Bull/Base/Bear with probability weights (Phase 2.7) |
| Risk assessment | 8-12 structured risks across 4 categories (Phase 2.7) |
| **Total analytical word count** | **~8,000-12,000 words (L2); ~7,000-10,000 words (L1)** |

### 2.1 Industry Background & Competitive Landscape

**Read**: `modules/industry-chain.md` + `valuation/comparable.md` §Competitive Landscape
**Output**: Industry analysis conclusion

### 2.2 Company Fundamentals Deep Research

**Reference**: `references/research-document-template.md` §II.2.1 Competitive Moat (6 moat types with quantifiable evidence) and §III Company Overview (Background / Business Model / Management & Governance / Ownership Structure). The template's word-count floors and sub-section structure are the source of truth.
**Output**: Write §III Company Overview and §II.2.1 Competitive Moat of the research document in full analytical prose.

### 2.3 Financial Analysis

**Reference**: `references/research-document-template.md` §II.2.3 Earnings Quality Anomaly Flags (OCF/NI ratio, working-capital red flags, non-recurring items, accounting policy vs peers). Fill §VI Historical Financial Data tables with real numbers from filings.
**Output**: §VI Historical Financials + §II.2.3 Anomaly Flags dimension of the research document.

### 2.4 Six-Dimension Deep Analysis

**Read**: `analysis/six-dimension-analysis.md` (sole source — DO NOT execute from memory)
**Output**: 6 dimension conclusions with data support and "So What"

### 2.5 Valuation & Investment Logic — Level 1 (Required for ALL modes)

**Read**: `analysis/investment-logic.md` + `valuation/comparable.md`
**Valuation Level**: Level 1 (comparable companies + multiples + consensus expectations)
**Output**: Valuation conclusion + Investment logic framework + Investment thesis table

For **L1 (streamlined)**: This is the ONLY valuation section. Ensure §XII Comparable Companies table has ≥5 peers with complete financial metrics (Market Cap, Revenue, PE, PB, EV/EBITDA). This data feeds directly into Task 3 — there is no Excel model to refine it.

For **L2 (full)**: This provides the preliminary comps list. Task 2 will build the full Excel model.

### 2.6 Valuation — Level 2 (L2 only; SKIP for L1)

> **Check `valuation_depth` before executing this section.**
> - If `valuation_depth = L1`: **SKIP 2.6 entirely.** Write "Level 2 valuation skipped — streamlined mode" in the research document and move to Phase 2.7.
> - If `valuation_depth = L2`: Execute all steps below.

**Read**: `valuation/dcf-and-sensitivity.md` (covers DCF mechanics + historical valuation band + sensitivity matrix in a single reference).

**Steps**:
1. **DCF Model**: WACC → FCF projection (5Y) → Terminal value → Equity bridge → Per-share value
2. **Historical Valuation Band**: 5Y PE/PB band with percentile analysis
3. **Sensitivity Matrix**: WACC × Terminal Growth (mandatory), Revenue × Margin (optional)
4. **SOTP**: If company has distinct segments, sum-of-the-parts valuation
5. **Cross-Method Synthesis**: Compare all methods, identify convergence/divergence, determine valuation range

**Output**: Complete Level 2 valuation data per `references/output-schema.md` §Section VIII Level 2.

### 2.7 Deep Research Modules

> **This phase is what separates the equity report from the tear sheet.**
> It produces the analytical depth that makes the report worth 15+ pages.
> Each sub-step has a dedicated analysis file with structured frameworks,
> data requirements, and word count minimums. Do NOT skip or abbreviate.

**Pre-inspection**: Read ALL 4 files before beginning analysis. For the industry/competitive and TAM content, follow §IV of `references/research-document-template.md` directly — no separate framework file is needed.
- [ ] `analysis/revenue-model.md`
- [ ] `analysis/projection-assumptions.md`
- [ ] `analysis/scenario-deep-dive.md`
- [ ] `analysis/risk-framework.md`

**Sub-steps** (execute in order):

| Step | Reference | Output | Minimum Word Count |
|------|-----------|--------|-------------------|
| 2.7.1 | `references/research-document-template.md` §IV Industry Overview + TAM/SAM/SOM | Market sizing, growth drivers, penetration analysis (written into §IV of the research doc) | 600-1,000 |
| 2.7.2 | `references/research-document-template.md` §IV Competitive Landscape + Entry Barriers | 5-8 competitor profiles, market share, positioning, pricing power (written into §IV) | 800-1,200 |
| 2.7.3 | `analysis/revenue-model.md` | Segment-level revenue decomposition, volume × price, consensus comparison | 800-1,500 |
| 2.7.4 | `analysis/projection-assumptions.md` | Margin bridge, CapEx/WC assumptions, assumption sensitivity tags | 1,500-2,500 |
| 2.7.5 | `analysis/scenario-deep-dive.md` | Quantified Bull/Base/Bear, probability weights, transition triggers | 1,000-1,500 |
| 2.7.6 | `analysis/risk-framework.md` | 8-12 categorized risks with probability × impact scoring | 1,200-1,800 |

**Total Phase 2.7 analytical output**: 5,900-9,500 words of structured analysis.

**Quality gate**: Each sub-step has an output quality checklist at the bottom of its analysis file. All checklist items must pass before proceeding to Phase 3.

**Integration mandate**: Phase 2.7 outputs feed directly into the Research Document and eventually Task 3 report modules:
- TAM → Industry & Competitive Landscape (Section 7)
- Competitive deep dive → Industry & Competitive Landscape (Section 7)
- Revenue model → Financial Analysis (Section 9) + Projection Assumptions (new section)
- Projection assumptions → Valuation Analysis (Section 5) + Financial Analysis (Section 9)
- Scenario deep dive → Scenario Analysis & Risk (Section 14)
- Risk framework → Scenario Analysis & Risk (Section 14)

---

## Phase 3: Synthesis & Distillation

**Pre-inspection**:
- [ ] All 6 dimensions have explicit conclusions
- [ ] Each conclusion assigned to report module (see 3.2 mapping)

### 3.1 Core Investment Narrative

5-8 sentences connecting: industry trends → company strengths → financial performance → valuation judgment → key risks.

All subsequent modules must align with this narrative.

### 3.2 Six-Dimension → Module Mapping

| Six-Dimension Conclusion | Core Viewpoint | Report Module |
|--------------------------|----------------|---------------|
| One-sentence judgment | [Conclusion] | Caption title, 公司概览 |
| Market Pricing | [Conclusion] | Valuation module |
| Market Error | [Conclusion] | Investment logic (bullish/bearish) |
| Key Variable | [Conclusion] | Catalyst calendar, scenario analysis |
| Main Contradiction | [Conclusion] | Investment thesis table (competitive landscape row) |
| Anomaly Signal | [Conclusion] | Investment thesis table (earnings quality row), risk, financials |

Also map all 21 mandatory report modules to relevant dimensions (see `output/report-layout.md` §4.3 for the full module list).

### 3.3 Investment Thesis Comprehensive Analysis Table

4 rows × 6 columns. Specification in `analysis/investment-logic.md` §投资论点综合分析表.

### 3.4 Output Document: Research Document

Write all findings to `{Company}_{Ticker}_Research_Document_{Date}.md` per `references/research-document-template.md`.

**This is the handoff artifact to Task 2 (Financial Model) and Task 3 (Report Generation).**
- Contains all research, analysis, historical financial data, and competitive intelligence
- Does NOT contain valuation calculations (that's Task 2's job)
- Must pass ALL acceptance criteria in the template's Content Quality Gate

**Research Document Requirements**:
- ≥6,000 words total
- §VI Historical Financials: ALL cells filled with real data for ≥3 years (NO blanks)
- §VII Revenue Model: ≥3 segments with Volume×Price decomposition
- §IV Competitive: ≥5 named competitors with revenue and market share
- §XII Preliminary Valuation Inputs: ≥3 comparable companies + DCF starting assumptions
- NO placeholder text anywhere

**Self-check**: Read the Content Quality Gate at the bottom of `references/research-document-template.md`. Every checkbox must pass. If any fails, return to Phase 2/3 to fill the gap.

---

## Phase 3.5: Task 1 Exit Protocol

> **This is where Task 1 ends.** The research document is the handoff artifact.

After the research document passes the Content Quality Gate:

1. **Save the document** to disk: `{Company}_{Ticker}_Research_Document_{Date}.md`
2. **Save generated assets** alongside:
   - Stock chart SVG (from `scripts/stock_chart_generator.py`)
   - Stock price CSV + benchmark CSV
3. **Run acceptance gate**: Verify all checks in `references/research-document-template.md` §Content Quality Gate
4. **Deliver to user** with a **continuation-ready message**:

   **For L2 (Full Version, 3 Tasks):**
   > ✅ Step 1 完成 — 研究文档已生成。
   >
   > 接下来进入 Step 2：财务建模与估值（Excel 三表模型 + DCF + 敏感性分析）。
   > 你只需要说 **"下一步"**、**"继续"** 或 **"continue"**，我将自动读取本步骤生成的研究文档并继续。

   **For L2 (English):**
   > ✅ Step 1 complete — Research Document generated.
   >
   > Next: Step 2 — Financial Modeling & Valuation (Excel 3-statement model + DCF + sensitivity).
   > Just say **"next"**, **"continue"**, or **"下一步"** and I'll automatically proceed using the files generated in this session.

   **For L1 (Streamlined Version, 2 Tasks):**
   > ✅ Step 1 完成 — 研究文档已生成。
   >
   > 接下来进入 Step 2：生成最终 PDF 研报。精简版不包含复杂的 Excel 财务模型，估值基于可比公司倍数法。
   > 你只需要说 **"下一步"**、**"继续"** 或 **"continue"**，我将自动读取本步骤生成的研究文档并继续。

   **For L1 (English):**
   > ✅ Step 1 complete — Research Document generated.
   >
   > Next: Step 2 — Generate final PDF report (streamlined version, comparable-company valuation, no Excel model).
   > Just say **"next"**, **"continue"**, or **"下一步"** and I'll automatically proceed using the files generated in this session.

5. **STOP.** Wait for user's continuation signal. Do not continue until user says "下一步"/"继续"/"continue"/"next".
