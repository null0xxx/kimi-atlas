# Tear Sheet — Phase 5: Quality Assurance

> **This file is read by the agent during Phase 5 when `output_type = TEAR_SHEET`.**
> All paths are relative to the skill root directory.

---

## 5.1 Automated Pre-Check

Run `scripts/report_validator.py --html [report.html] --json` → structured failure list.

### Handling Validator Output

**Step 1: Identify false positives** (do NOT waste time fixing these):

| Check Name | False Positive Pattern | Why It's a False Positive | Action |
|-----------|----------------------|---------------------------|--------|
| `industry_chain_diagram` | Reports ".mermaid-container not found" | Mermaid was pre-rendered to PNG and embedded as `<img>` — the container class may differ | Verify: open HTML, confirm chain diagram renders as image (not raw text). If image displays correctly → **ignore** |
| `supply_chain_svg` | Reports "SVG not found" or "not SVG format" | Skill explicitly allows Mermaid → PNG pre-rendering; PNG is the expected output format | Verify: confirm chain diagram is visible as image. If yes → **ignore** |
| `page_balance` | Reports "exhibit-label missing page-break-after" in Tear Sheet mode | Tear sheets use CSS `page-break-inside: avoid` + `.exhibit-label + * { page-break-before: avoid }` for title-following — explicit `page-break-after` on every label is unnecessary | If visual inspection shows no orphan titles → **ignore** |

**Step 2: Fix genuine failures** — everything not in the false positive table above must be fixed.

**Step 3: After ANY fix** → re-run the FULL QA loop (not just the failed check). See §5.3.

---

## 5.2 Layout Self-Check

| # | Priority | Check Item |
|---|----------|------------|
| 1 | Highest | Title isolated at page bottom |
| 2 | Highest | Table spans page |
| 3 | High | Chart/diagram cut off |
| 4 | High | Supply chain diagram not rendered (raw text visible or blank) |
| 5 | Medium | Over-pagination (large white space) |
| 6 | Medium | Chart/table too small |
| 7 | Low | Last page too short |

**Toolkit** (available fix methods):

| Tool | Applicable Scenario | Operation |
|------|---------|------|
| **Add `module-newpage`** | Title isolated / Table spans page / Over-pagination | Add `module-newpage` to `.module-row`, force entire module (incl. title) to new page |
| `page-break-after: avoid` | Exhibit title isolated | Add to `.exhibit-label`, prevent title and content separation |
| Remove `module-newpage` | Over-pagination (caused by overuse) | Delete unnecessary forced pagination |
| Enlarge chart/table | Chart/table too small | Mermaid add nodes, table add rows |
| HTML/CSS fallback | Mermaid not rendered | Replace Mermaid code with HTML/CSS flex layout (see `modules/industry-chain.md` §Appendix) |
| Condense/Merge | Content too short and cannot expand | Merge adjacent short modules, delete non-essential content |
| Expand content | Overall too sparse causing multi-page white space | Increase analysis depth (only when pages < target minimum) |
| **`.stacked-layout`** | Severe content imbalance and `module-newpage` cannot solve | Vertical stacking fallback — NOT as first choice |

**Iteration Rules** ( aligned with §4.5 free-flow philosophy ):
1. **Highest Priority**: Title isolated and table/chart split across pages must fix immediately — add `module-newpage` to force entire module to new page. No acceptance of "minor overage".
2. **Default**: No forced pagination. Only add `module-newpage` AFTER visual inspection confirms a problem. Never pre-emptively.
3. **Per-fix verification**: After EVERY single fix (even adding one CSS class), re-run the **entire** QA loop (Steps 1-6), not just the check you fixed. A fix for problem A often introduces problem B.
4. **Max 2 rounds.** Prioritize structural fix (`module-newpage` / class adjustment), avoid returning to Phase 4 unless necessary.

---

## ⚠️ 5.3 MANDATORY Quality Gate Loop Rules

> **THIS IS THE MOST CRITICAL SECTION IN THIS FILE.**
> The output quality gate exists to prevent broken, duplicated, or oversized reports from being delivered. Every single iteration — including "small fixes" — MUST re-run the full check loop before delivery.

### ❌ COMMON FAILURE MODE (READ THIS FIRST)

The most frequent and most serious quality failures happen like this:
1. Agent generates initial HTML → runs QA → finds issues
2. Agent fixes one issue (e.g., adjusts a module)
3. Agent **skips re-running QA** after the fix → delivers broken report
4. Result: **HTML duplication** (`</body></html>` appears mid-file, entire report repeats), **8+ page tear sheets**, **broken layout**

**THIS PATTERN IS ABSOLUTELY PROHIBITED.**

### The Iron Rule: Re-Check After EVERY Change

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ AFTER ANY MODIFICATION TO THE HTML — NO MATTER HOW     │
│  SMALL — YOU MUST RE-RUN THE FULL QA LOOP BEFORE DELIVERY. │
│                                                             │
│  This includes:                                             │
│  • Adding/removing module-newpage classes                   │
│  • Fixing a single table cell                              │
│  • Adjusting CSS                                           │
│  • Re-rendering a chart                                    │
│  • Fixing a data error                                     │
│  • ANY edit to the HTML file                               │
│                                                             │
│  NO EXCEPTIONS. EVER.                                       │
└─────────────────────────────────────────────────────────────┘
```

### Quality Gate Loop (Execute This Exact Sequence)

```
LOOP START (max 3 iterations):
│
├─ Step 1: STRUCTURAL INTEGRITY CHECK (new — run FIRST every iteration)
│   □ Count occurrences of </body> and </html> in the HTML file
│     → If >1 of either tag: HTML IS DUPLICATED → discard and regenerate from clean source
│   □ Count total lines in HTML file
│     → If >800 lines for tear sheet: suspicious, investigate for duplication
│   □ Verify HTML is well-formed: exactly 1 <html>, 1 <head>, 1 <body>
│
├─ Step 2: GENERATE PDF from the current HTML
│   □ Use headless browser page.pdf()
│   □ Record the page count immediately
│
├─ Step 3: PAGE COUNT GATE (check IMMEDIATELY after PDF generation)
│   □ Tear sheet: MUST be 3-5 pages
│   □ If >5 pages: DO NOT proceed to A/B/C checks
│     → Investigate: HTML duplication? Modules repeated? CSS broken?
│     → Fix root cause → return to LOOP START
│   □ If <3 pages: content too thin → return to Phase 4 to expand
│
├─ Step 4: A-TIER CHECKS → **Execute ALL 15 checks every iteration**
│   → Even if you only fixed one thing, run the FULL A-tier checklist
│   → Any failure = prohibit delivery → locate failed module → repair → return to LOOP START
│
├─ Step 5: B-TIER CHECKS → **Execute ALL 10 checks every iteration**
│   → Even if A-tier all passed, still run complete B-tier (not just the ones that failed before)
│   → >3 failures = prohibit delivery → repair most critical → return to LOOP START
│
├─ Step 6: C-TIER CHECKS → record failures (informational)
│   → Execute all 7 checks for completeness
│
├─ Step 7: ALL CHECKS PASS → deliver report
│   → Only proceed here if ALL checks in Steps 1-6 passed
│
LOOP END
```

### Regression Protection
- During repair, only modify failed sections — do not regenerate entire pages
- After modification, re-verify modified items AND adjacent items
- If repair causes previously passed items to fail, **roll back the change** and try an alternative approach
- ❌ Never "fix forward" by making additional changes without re-checking — always return to LOOP START

---

## A-Tier Checks (Any Failure = Prohibit Delivery)

| No. | Check Item | Standard | Check Method |
|------|--------|------|---------|
| A1 | Page Layout | No large white space; content on last page ≥30% | Visual inspection |
| A2 | Module Sequence | Matches `output/tearsheet-layout.md` §4.6 order | Compare with module checklist |
| A3 | Module Completeness | All 11 required modules present | Verify each module |
| A4 | Chart Alignment | Charts aligned with box size, no overflow | Visual inspection |
| A5 | Page Margins | **Top/bottom 8mm, left/right 12mm** — controlled by `@page { margin: 8mm 12mm; }`（每页都生效），`.report-container { padding: 0 }`。No double-padding, no missing margins. | 目视检查：**翻到 PDF 第2页和最后一页**，确认顶部/底部都有白边（不只是第一页） |
| A6 | No Scaffold Data | All data from real sources, no fabrication | Spot-check data, verify sources |
| A7 | Data Cross-Validation | Key data verified from dual sources | Check iFind vs. Yahoo Finance |
| A8 | Model Data Tags | Calculated data labeled | Check "model calculation" labels |
| A9 | Narrative Consistency | All modules align with Phase 3 core narrative | Read through report |
| A9a | **Bullet Density** | Every bullet ≥30 Chinese chars (or ≥15 English words) AND contains ≥1 specific number. No bullet should be a bare fact statement without data. | Spot-check 5 random bullets |
| A10 | 投资论点综合分析表 | 4 rows with bull/bear arguments + key assumptions + pivot signals | Check table completeness |
| A11 | Short-term Fund Flow | Short-term 投资逻辑 includes fund flow / market structure analysis | Check left box text |
| A12 | Page Balance | No split content/charts across pages; Exhibit titles not orphaned; **No >40% blank page immediately before supply chain** (if so, remove `module-newpage` from supply chain) | Run validator + visual check |
| A13 | Analysis Brief | If requested, `{company}_{ticker}_analysis_brief.md` exists and complete | Check file |
| A14 | **HTML Integrity** | Exactly 1 `</body>` and 1 `</html>` in HTML file. No duplicated report content. | `grep -c '</body>' file.html` must return `1` |
| A15 | **Page Count Range** | PDF is 3-5 pages. If >5 pages, report is broken (likely HTML duplication). | Check PDF page count immediately after generation |

---

## B-Tier Checks (>3 Failures = Prohibit Delivery)

| No. | Check Item | Standard |
|------|--------|------|
| B1 | Page Count | **3-5 pages A4** |
| B2 | Data Source Tags | All data tagged with source |
| B3 | Catalyst Calendar | ≥4 events, includes next earnings, ≥2 high-importance |
| B4 | Comparable Companies | 3-5 competitors |
| B5 | 52-Week Stock Chart | Width fills container, benchmark overlay, labels complete |
| B6 | Company Snapshot | Bullet format, management highlights |
| B7 | Supply Chain Map | **Playwright pre-rendered Mermaid PNG** (≥4 layers); HTML/CSS flex only for <4 layers or Playwright failure. **NO forced page break** — supply chain flows naturally after previous module |
| B8 | Earnings Quality Signals | Financial module contains OCF/NI metrics |
| B9 | Consensus Expectation | Valuation module includes sell-side expectations |
| B10 | Competitive Landscape | Industry module has CR concentration, pricing power |

---

## C-Tier Checks (Record Failures)

| No. | Check Item | Standard |
|------|--------|------|
| C1 | Table Count | 8-10 |
| C2 | **Dual-Box Balance** | Content difference <30% between left/right boxes |
| C3 | Data Timeliness | Latest financials and market data |
| C4 | Compliance Statement | Bottom of page 2 |
| C5 | Exhibit Numbering | Sequential, no repeats/gaps |
| C6 | Change Highlighting | YoY/QoQ use `.change-positive` / `.change-negative` |
| C7 | English Font | US stock English reports use `.report-container-en` |

---

## Structure Inspection Details

### Page 1

```
□ Header: Company name + stock code + key data (no buy/sell ratings)
□ Featured Title: Title + subtitle + core view (no buy/sell conclusion)
□ Core Data: Left 52-week stock chart (fills box, vs. benchmark) + right trading data table
□ Company Snapshot: Left bullets (background/business/recent+management) + right business structure table
□ 投资逻辑: Left short-term (includes 利空) + right long-term (includes risks+debate+护城河)
□ 投资论点综合分析表 (full-width 4×6)
□ Valuation + Catalysts: Left valuation (consensus analysis) + right catalysts (≥4 events)
□ Industry & Valuation Comparison: Left comps table + right industry analysis (CR/pricing power)
```

### Page 2+

```
□ Supply Chain Panorama: Mermaid flowchart (not simple three-part)
□ Upstream/Downstream: Left upstream + right downstream
□ Financial Analysis: Left profitability+growth (earnings quality signals) + right solvency+cash flow
□ Scenario + Risk: Left three scenarios + right risk list
□ Compliance Disclaimer: Market-specific
```

---

## Special Check Details

### Stock Chart (Zero Tolerance for Mock Data)
```
□ Correct benchmark index (A-shares→上证 / HK→恒生 / US→S&P 500)
□ Forward-adjusted prices (no split cliffs)
□ **Must use `scripts/stock_chart_generator.py` with `--json`**, prohibit manual code
□ base64 complete: `image_base64` length ≥ 20,000 chars
□ Script uses `--stock_csv` and `--benchmark_csv` with real CSV (both files exist, size > 100 bytes)
□ **⛔ NO mock data**: verify stock_csv and benchmark_csv contain real API data (iFind/Yahoo Finance), not simulated/generated data
□ If CSV files missing or empty → chart module must be skipped with "data unavailable" annotation
□ HTML has no `<script>` chart code, `<canvas>` tags
```

### 投资逻辑
```
□ Left: "Short-term 投资逻辑" — 2-3 利多 + 1-2 利空 (mandatory) + key disagreement
□ Right: "Long-term 投资逻辑" — core thesis + 2-3 利多 + 1-2 risks (mandatory)
□ 投资论点综合分析表: 4 rows, 六维 mapping complete
```

### Catalyst Calendar
```
□ ≥4 events covering next 6 months
□ Next earnings date included (high importance)
□ ≥2 high-importance events
```

### Supply Chain
```
□ Playwright pre-rendered diagram (≥4 value chain layers) → base64 PNG embed
□ No raw <pre class="mermaid"> or <script src="mermaid.min.js"> in final HTML
□ All company-involved nodes highlighted dark (fill:#003366)
□ Real company names, compact nodes (3-5 per stage)
□ Prohibit plain table or text description
□ NO module-newpage on supply chain module (flows naturally)
```

---

## Visual Inspection Details

### White Space Control
- Each page except last page <12% white space

### Chart Alignment
- Stock chart aligns with box top/bottom/left/right
- Supply chain chart width matches module
- Tables don't overflow

### Page Margins
- Margin scheme (single source of truth): `@page { size: A4; margin: 8mm 12mm; }` + `.report-container { padding: 0 }`
- Effective margins: top/bottom 8mm, left/right 12mm（每一页都生效，不只是第一页）
- **为什么不用 container padding**：跨页时 container padding 只在第一页顶部和最后一页底部生效，中间页会丢边距；@page margin 才是每页物理边界
- Content must not touch page edges on **任何一页**; white space visible on all four sides
- Tables and disclaimers must display completely within the padded area
- If margins appear missing: check that CSS is fully inlined (not `<link>`-referenced) and no override is injected
- **强制目视核查**：生成 PDF 后翻到第 2 页和最后一页，确认顶部/底部都有 ~8mm 白边

---

## Data Cross-Validation Reference

| Data Type | Primary Source | Verification Source | Acceptable Variance |
|----------|------|--------|-----------|
| Revenue / Net Income | iFind | Yahoo Finance | <5% |
| PE / PB | iFind | Yahoo Finance | <10% |
| Earnings Forecast | iFind | — | — |
| Business Breakdown | iFind | Web Search | <10% |
| Industry Data | 财新 | Web Search | <15% |
| Next Earnings Date | Web Search | Exchange Calendar | No variance |

---

## Quality Check Execution Instructions

### Execution Steps

```bash
# Step 1: After report generation, execute A-tier checks
echo "=== A-Tier Checks ==="
for check in A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13; do
    echo "Check $check: [Pass/Fail]"
done

# Step 2: If all A-tier pass, execute B-tier checks
echo "=== B-Tier Checks ==="
B_failed=0
for check in B1 B2 B3 B4 B5 B6 B7 B8 B9 B10; do
    echo "Check $check: [Pass/Fail]"
    if [ Fail ]; then ((B_failed++)); fi
done

# Step 3: Determine result
if [ $B_failed -gt 3 ]; then
    echo "B-tier checks fail >3 items, prohibit delivery, repair and re-check"
else
    echo "B-tier checks pass, execute C-tier checks"
fi

# Step 4: Execute C-tier checks
echo "=== C-Tier Checks ==="
for check in C1 C2 C3 C4 C5 C6 C7; do
    echo "Check $check: [Pass/Fail]"
done
```

---

## Quality Check Report Template

```markdown
# Quality Check Report

## Report Information
- Company Name: [Company]
- Stock Code: [Code]
- Report Date: [Date]
- Check Time: [Time]

## A-Tier Check Results
| Check Item | Status | Note |
|--------|------|------|
| A1 White Space Control | [PASS]Pass | White space 8% |
| A2 Module Sequence | [PASS]Pass | Complies with standard |
| ... | ... | ... |

**A-Tier Check Conclusion**: [PASS]All pass

## B-Tier Check Results
| Check Item | Status | Note |
|--------|------|------|
| B1 Page Count | [PASS]Pass | 4 pages |
| B2 Data Source Tags | [PASS]Pass | All tagged |
| ... | ... | ... |

**B-Tier Check Conclusion**: [PASS]Pass (1 item fail, within acceptable range)

## C-Tier Check Results
| Check Item | Status | Note |
|--------|------|------|
| C1 Table Count | [PASS]Pass | 9 tables |
| C2 Dual-Box Balance | [NOTICE]Fail | Left/right 35% difference |
| ... | ... | ... |

**C-Tier Check Conclusion**: [NOTICE]2 items fail, recorded

## Final Conclusion
[PASS] Report passes quality check, ready to deliver
or
[FAIL] Report fails quality check, needs repair and re-check
```

---

## Common Problem Troubleshooting

| Problem | Likely Cause | Solution |
|------|----------|---------|
| Excessive white space | Insufficient module content | Expand content or adjust layout |
| Content overflow | Too much text/tables | Condense text, shrink tables |
| Unbalanced boxes | Large content difference | Rebalance content distribution |
| Table truncation | Too many columns | Reduce columns or use condensed template |
| Module title orphaned | Title at page bottom, content on next page | Add `module-newpage` to that `.module-row` (CSS `page-break-inside: avoid` + title-following rules should prevent this automatically; if it still happens, force new page) |
| Crowded page | Consecutive large modules without break | Add `module-newpage` class for >600 character modules |
| Exhibit title orphaned | Title at page bottom, chart on next page | Add `page-break-after: avoid` to label or push chart to new page |
| Chart spanning pages | Page break through chart | Ensure chart-container / mermaid has `page-break-inside: avoid` |
| Table row truncation | Page break cuts through table row | Ensure table and tr have `page-break-inside: avoid` |
| Supply chain diagram blank/text | Raw Mermaid not pre-rendered, or render method failed | Re-run Playwright pre-render per `modules/industry-chain.md` §Rendering Pipeline (Playwright → HTML/CSS flex fallback) |
| Data conflict | Dual-source variance | Process per `references/data-sources.md` conflict resolution tree |
