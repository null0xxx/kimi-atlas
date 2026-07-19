# Tear Sheet — Phase 4: Visual Design + Report Generation

> **This file is read by the agent during Phase 4 when `output_type = TEAR_SHEET`.**
> All paths are relative to the skill root directory.

---

## 4.1 Design Specification

**CSS sole source**: `output/tearsheet.css`

**Usage**: Read `output/tearsheet.css` and embed the full CSS content inside a `<style>` tag in the HTML `<head>`. Do NOT use `<link rel="stylesheet">` — the execution environment has no file system access to `output/tearsheet.css`.

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <!-- Paste the COMPLETE contents of output/tearsheet.css here -->
  <style>
    /* ... full tearsheet.css content ... */
  </style>
</head>
<body>
  <div class="report-container">...</div>
</body>
</html>
```

**Hard Constraints**:
- Page Margin: 8mm top/bottom, 12mm left/right
- Chinese: `.report-container`
- English: `.report-container report-container-en`
- Bullet Structure: HTML bullets use `<div class="bullet-item">` + CSS `::before{content:"•"}`; prohibit manually writing `•` in HTML causing double dots
- Page Quality: No visible large white space except last page; last page ≥30% content

---

## 4.2 HTML Structure

Standard dual-column module:
```html
<div class="module-row">
  <div class="section-title">Module Title</div>
  <div class="two-column">
    <div class="box box-primary">...</div>
    <div class="box box-secondary">...</div>
  </div>
</div>
```

Module Title Checklist (must use these exact titles):

| Module | Chinese Title | English Title |
|--------|--------------|---------------|
| Stock Price + Trading Data | No module-level title, use exhibit-label | No module-level title, use exhibit-label |
| Company Overview | 公司概览 | Company Overview |
| Investment Logic | 投资逻辑 | Investment Logic |
| Valuation + Catalysts | 估值分析与催化剂 | Valuation & Catalysts |
| Industry & Valuation Comparison | 行业与估值对比 | Industry & Valuation Comparison |
| Supply Chain | 产业链全景 | Supply Chain Panorama |
| Upstream/Downstream | 上下游深度分析 | Upstream/Downstream Analysis |
| Financial Analysis | 财务分析 | Financial Analysis |
| Scenarios + Risk | 情景分析与风险提示 | Scenario Analysis & Risk |

Use the language column matching `report_language` set in Phase 0.1.

---

## 4.3 Page Layout

```
┌──────────────────────────────────────────────────┐
│ Header: Company Name | Stock Code | Key Data     │
├──────────────────────────────────────────────────┤
│ Caption Title + Subtitle + Core Viewpoint        │
├────────────────────┬─────────────────────────────┤
│ 52-week Stock Chart│ Core Trading Data Table     │
├────────────────────┼─────────────────────────────┤
│ Short-term Logic   │ Long-term Logic             │
├──────────────────────────────────────────────────┤
│ Investment Thesis Comprehensive Table (4×6)      │
├────────────────────┬─────────────────────────────┤
│ Company Overview   │ Business Structure Table    │
├────────────────────┼─────────────────────────────┤
│ Valuation Analysis │ Catalyst Calendar           │
├────────────────────┼─────────────────────────────┤
│ Comparable Company │ Industry Analysis           │
├──────────────────────────────────────────────────┤
│ Supply Chain Panorama (Mermaid, full-width)      │
├────────────────────┬─────────────────────────────┤
│ Upstream Analysis  │ Downstream Analysis         │
├────────────────────┼─────────────────────────────┤
│ Financial Analysis │ Financial Analysis          │
│ (Profitability)    │ (Solvency + Cash Flow)      │
├────────────────────┼─────────────────────────────┤
│ Scenario Analysis  │ Risk Disclosure             │
├──────────────────────────────────────────────────┤
│ Compliance Disclaimer                            │
└──────────────────────────────────────────────────┘
```

---

## 4.4 Report Header HTML

```html
<div class="header-unified">
  <div class="header-top">
    <div class="header-company">
      <span class="header-name">Company Name</span>
      <span class="header-code">600519.SH</span>
    </div>
    <div class="header-tags">
      <span class="tag highlight">Market Cap: ¥XXX Billion</span>
      <span class="tag">Sector: XXX</span>
      <span class="tag">PE(TTM): XX.X</span>
      <span class="tag">Report Date: YYYY-MM-DD</span>
    </div>
  </div>
  <div class="header-main-title">[Core judgment, 8-15 chars]</div>
  <div class="header-title-footer">
    <div class="header-sub-title">[Supplementary, 15-25 chars]</div>
  </div>
  <div class="header-summary">
    <span class="summary-label">Core Viewpoint:</span>
    [3-4 sentences: ①Position ②Financials ③Valuation ④Risks]
  </div>
</div>
```

---

## 4.5 Page Break Control

### Core Philosophy: Free Flow by Default

**By default, do NOT add any forced page breaks.** Content flows naturally. Only intervene when visual inspection detects specific problems.

```
Default:    No module-newpage anywhere
Exception:  Add only when visual inspection confirms a problem
```

### CSS Guardrails (Already in tearsheet.css)

These rules automatically prevent the most common breakage — **no manual intervention needed**:

| Element | CSS Rule | Effect |
|---------|----------|--------|
| Tables (`.report-table`, `.debate-table`) | `page-break-inside: avoid` | Table never splits across pages |
| Charts (`.chart-container`, `.mermaid`) | `page-break-inside: avoid` | Chart never splits across pages |
| Section titles (`.section-title`, `.box-title`, `h3`, `h4`) | `page-break-after: avoid` | Title stays with content after it |
| Title + content (`.section-title + *`) | `page-break-before: avoid` | If table/chart pushed to next page, title follows |
| Exhibit labels (`.exhibit-label + *`) | `page-break-before: avoid` | Exhibit title follows its chart/table |

**Critical behavior**: When a table or chart is too large to fit at the bottom of a page, `page-break-inside: avoid` pushes it to the next page. The `page-break-after: avoid` on the title ensures the title goes with it — **no orphan titles**.

### When to Use `module-newpage` (Visual-Detection-Only)

Only add `module-newpage` **after generating the PDF and visually inspecting**:

```html
<!-- Only add this AFTER visual inspection confirms a problem -->
<div class="module-row module-newpage">
  <div class="section-title">Module Title</div>
  <div class="two-column">...</div>
</div>
```

| Problem Detected | Solution |
|------------------|----------|
| Section title orphaned at page bottom (title on page N, content on page N+1) | Add `module-newpage` to that `.module-row` |
| Table/chart split across pages (CSS failed) | Add `module-newpage` to that `.module-row` |
| Over-crowded page (>80% filled with large modules) | Add `module-newpage` to the later module |

**NEVER add `module-newpage` pre-emptively** — only after visual detection.

### Modules with Special Rules

| Module | `module-newpage`? | Rule |
|--------|-------------------|------|
| Supply Chain | **Never** | Always flows naturally. CSS handles diagram protection. Never force new page. |
| Financial Analysis | After visual check only | Only if previous page is over-crowded |
| All other modules | After visual check only | Default = free flow |

### Fallback: `stacked-layout`

Only for extreme content imbalance (e.g., left box has 3 lines, right box has 30 lines). NOT as first choice.

```html
<div class="two-column stacked-layout">
  <div class="box box-primary">...</div>
  <div class="box box-secondary">...</div>
</div>
```

---

## 4.6 Module Generation Checklist (Strict Order)

| #   | Module                             | Group       | Layout                    | Required Reading               | Key Requirements                                                                                                                                                                       |
| --- | ---------------------------------- | ----------- | ------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 52-week Stock Price + Trading Data | First Half  | Dual-Box                  | `modules/stock-chart.md`       | **Must call script**, prohibit manual chart code. Width fills container, includes benchmark index                                                                                      |
| 2   | Investment Logic                   | First Half  | Dual-Box + Full-Width Row | `analysis/investment-logic.md` | Must include bearish viewpoint, thesis table full-width                                                                                                                                |
| 3   | Company Overview                   | First Half  | Dual-Box                  | `modules/company-overview.md`  | Left bullets incl. management, right business table                                                                                                                                    |
| 4   | Valuation + Catalyst Calendar      | First Half  | Dual-Box                  | `modules/valuation.md`         | Consensus expectations, ≥4 catalysts incl. earnings                                                                                                                                    |
| 5-6 | Industry & Valuation Comparison    | First Half  | Dual-Box                  | `valuation/comparable.md`      | Left comparables, right industry analysis (incl. competitive landscape)                                                                                                                |
| 7   | Supply Chain Panorama              | Second Half | Full-Width                | `modules/industry-chain.md`    | Pre-rendered SVG (Mermaid design → auto-select best render method, ≥4 layers). See `industry-chain.md` §Rendering Pipeline. HTML/CSS flex only if <4 layers or all render methods fail |
| 8   | Upstream/Downstream                | Second Half | Dual-Box                  | `modules/industry-chain.md`    | Left upstream, right downstream                                                                                                                                                        |
| 9   | Financial Analysis                 | Second Half | Dual-Box                  | `modules/tables.md`            | Left profitability+growth, right solvency+cash flow, incl. 盈利质量信号                                                                                                                      |
| 10  | Scenario + Risk                    | Second Half | Dual-Box **60%/40%**      | `modules/tables.md`            | Left bull/base/bear (`.scenario-box`), right risk list (`.risk-box`)                                                                                                                   |
| 11  | Compliance Disclaimer              | Second Half | Full-Width                | —                              | Market-specific disclaimer (see below)                                                                                                                                                 |

### Module 11: Disclaimer Content

The disclaimer must include **"Kimi Research"** as the issuing entity. Use market-appropriate language:

- **A-shares (zh)**: "本报告由 Kimi Research 基于AI辅助分析生成，仅供参考，不构成投资建议。投资者应独立判断并自行承担投资风险。"
- **HK stocks (zh)**: Same as A-shares, plus SFC risk disclosure if applicable.
- **US stocks (en)**: "This report was generated by Kimi Research using AI-assisted analysis. It is provided for informational purposes only and does not constitute investment advice. Investors should exercise independent judgment and assume their own investment risks."

> **Phase 4 Supplementary Research (Tear Sheet)**: If any module's content from the analysis brief feels thin (only 1 bullet point, missing data), do a quick Web Search to add 1-2 supporting data points before writing that module. If the catalyst calendar has fewer than 4 events, search for upcoming events. If comparable company metrics are incomplete, check iFind/Yahoo Finance. Keep supplementary searches light — max 3 total.

---

## 4.7 Generate Report

| Output Format | Trigger Condition | Implementation |
|----------|----------|----------|
| **PDF (Default)** | Format unspecified or PDF requested | Generate PDF from HTML directly using headless browser `page.pdf()`. No cover page. `page.emulate_media(media='print')`. Do NOT inject any CSS override — margins are controlled by `tearsheet.css` `@page { margin: 8mm 12mm; }` |
| **DOCX** | Request "DOCX"/"Word" | Call DOCX generation skill |
| **HTML** | Request "HTML" | Output HTML file directly |

**Key Rules**:
1. Default output PDF. Generate from the self-contained HTML + CSS using headless browser `page.pdf()`.
2. ❌ **DO NOT call or invoke the environment PDF skill.** Tear sheets use their own CSS (`output/tearsheet.css`) and `@page` rules for layout — the PDF skill would conflict with this and may add an unwanted cover page.
3. **Margin scheme** (sole source, already defined in `output/tearsheet.css`):
   - `@page { size: A4; margin: 8mm 12mm; }` — 8mm 上下 / 12mm 左右，**每一页都生效**
   - `.report-container { padding: 0; }` — container 不再重复加边距
   - **为什么用 @page 而不是 container padding**：container 的 padding 在跨页时只在第一页顶部和最后一页底部生效，中间页会丢边距；`@page margin` 由 PDF 引擎在每页物理边界预留，每页都生效
   - **Do NOT inject any margin override** (no `!important` padding override, no `@page margin` override)
   - Do NOT pass margin parameter in `page.pdf()` — the CSS controls everything
4. After generating check page count: 3-5 pages. If not matching, return to Phase 4 to adjust

**Last Page Optimization**: When last page effective content ≤ 5 lines, compress disclaimer → merge risks bullets → condense scenario analysis, max 2 rounds.

### Supply Chain Diagram Rendering (CRITICAL)

**Supply chain diagrams must be pre-rendered to PNG via Playwright before embedding in HTML.** PDF renderers do NOT execute JavaScript — raw Mermaid code will appear as plain text.

See `modules/industry-chain.md` §Rendering Pipeline for the sandbox-optimized Playwright scheme:
1. **Playwright** (primary — use sandbox browser toolkit to render Mermaid → base64 PNG)
2. **HTML/CSS flex** (fallback when Playwright fails after 1 retry)

**Key Rules**:
- Do NOT include `<script src="mermaid.min.js">` in final HTML
- Do NOT embed raw `<pre class="mermaid">` code in final HTML
- ⚠️ **Use `.chart-container-free` for the industry chain image, NOT `.chart-container`!** The `.chart-container` class has `max-height: 170px` (for stock charts only) — it will severely truncate the industry chain diagram.
- Embed the **pre-rendered base64 PNG** as `<img src="data:image/png;base64,...">` inside `.mermaid-container > .chart-container-free`

### Base64 Image Embedding — Two-Step Method (Required)

The `write_file` tool does NOT execute Python f-string interpolation. You **must** use a two-step process:

```python
# Step 1: Generate the HTML template with a placeholder
html_template = """<div class="chart-container-free">
    <img src="data:image/png;base64,${CHAIN_BASE64}" alt="Industry Chain" style="width:100%;">
</div>"""

# Step 2: Replace placeholder with actual base64 (in Python/IPython)
html_content = html_template.replace('${CHAIN_BASE64}', actual_base64_string)
# Then write html_content to file
```

**NEVER** write `f"...{variable}..."` directly into `write_file` — it will be stored as literal text, not interpolated.
