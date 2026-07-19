---
name: commodities-outlook
description: "Produce institutional-grade commodity outlook reports with supply-demand analysis, price forecasts, and trade recommendations, formatted as PDF, DOCX, or PPTX documents. Triggered when users request commodity market reports, ask for trade ideas on energy, metals, or agricultural commodities, or mention keywords like commodity outlook, research note, or price drivers."
---

# Commodity Research Outlook

Produce institutional-grade commodity outlook reports following a proven sell-side research structure.

## Reference Source

- **Type**: Uploaded PDF artifacts (three editions: 2024, 2025, 2026)
- **Reference File Type**: PDF
- **Primary Style Reference**: 2026 edition (clean minimal design, geometric sans-serif typography)
- **Supported outputs**: PDF (primary), DOCX (editable), PPTX (presentation subset)
- **Default output**: PDF when user does not specify

## Style Contract

Load `references/style_contract.md` for full visual specification. Key rules below.

### Must-Follow Style Rules

1. **Cover page — NO dark gradient bars**. White background throughout. Text-only header: brand logo name top-left, "Commodities Research" top-right with date/time. Thin vertical navy accent line on left margin below header.
2. **No section number hierarchy** (no 1., 1.1, 2., etc.). Use paragraph-style flowing text with bold subheadings like "Long Gold" or "Insurance Value of Commodities" embedded in the narrative.
3. **No colored section heading bars**. Clean white page background on all body pages.
4. **Typography**: Geometric neo-grotesque sans-serif; use Helvetica Neue / Arial as primary font. Never use LiberationSans.
5. **Charts**: Navy (#003366) and red/terracotta (#C62828) as primary series colors. Clean minimal gridlines. Multi-panel exhibits (2 charts side-by-side) are standard.

### Quick Reference

| Element | Specification |
|---|---|
| Brand header text | Clean text logo on white — NO gradient/dark bars |
| Section headings | Bold, inline with text flow, narrative style |
| Body text | ~10-11pt, left-aligned, ragged right |
| Running header | Thin rule; "[Firm Name]" left, "Commodity Views" right |
| Footer | Date left, page number right |
| Exhibit titles | Bold, "Exhibit N: [Descriptive Title]" |
| Source line | Small gray text, "Source: [Agencies], [Firm Name] Global Investment Research" |

## Structure Contract

Load `references/structure_contract.md` for full structural specification.

### Document Flow (No TOC Page)

```
Cover Page (page 1)
  |-- Brand text header + date
  |-- Thin vertical navy left-accent line
  |-- "COMMODITY VIEWS" series label
  |-- Report title + subtitle
  |-- Key takeaways (left column, ~60%): 5-8 bullets with filled-square markers
  |-- Author team (right column, ~40%): Name | Phone | Email | Entity
  |-- Top trades: empty-square markers with bold trade names
  |-- disclaimer bar at bottom
  
Body Pages (page 2 onward) — NO TOC PAGE, flow directly into content
  |-- Running header + thin rule
  |-- Opening thesis paragraph + overview narrative
  |-- Exhibits inline with text (multi-panel charts, tables)
  |-- Thematic sections with bold subheadings in text flow
  |-- Per-commodity deep dives with supply/demand analysis
  |-- ~15-16 exhibits per 19-page report (high exhibit density)

Disclosure Appendix (last 1-2 pages)
  |-- Reg AC certification
  |-- Global product / distributing entities
  |-- General disclosures
  |-- Copyright notice
```

## Exhibit Requirements

- **Quantity**: Target 15-16 substantial exhibits for a ~19-page report. Each major theme needs 2-4 supporting exhibits.
- **Types**: Multi-panel time-series (dual-axis), grouped/stacked bar charts, regression scatter plots, data tables, framework diagrams.
- **Cross-references**: Every exhibit referenced in body text as "(Exhibit N)" or "Exhibit N, left panel"
- **Source attribution**: Every exhibit has a source line

## Workflow

### Step 1: Gather Inputs

- Target year/period for the outlook
- Commodity sectors to cover (energy, metals, agriculture)
- Key macro assumptions (GDP growth, Fed policy, geopolitical backdrop)
- Specific trade convictions or views to highlight
- Author/team attribution

### Step 2: Build Structure

1. Define 2-4 thematic themes based on macro thesis
2. Map each commodity sector to themes
3. Draft 5-8 key takeaway bullets for cover page
4. Compile 3-4 Top Trades with empty-square markers
5. Plan ~15-16 exhibits with data sources

### Step 3: Draft Content

For each theme, follow the narrative pattern:
- **Opening thesis** → 1-2 paragraph overview
- **Macro context** → link to top-down story with cross-referenced exhibits
- **Supply-side analysis** → production, inventories, spare capacity
- **Demand-side analysis** → regional demand, structural vs cyclical drivers
- **Price forecast** → base case with bull/bear sensitivity
- **Trade recommendation** → bold recommendation statement embedded in text

### Step 4: Review Checklist

- [ ] Cover page has text-only header (NO gradient bars), vertical left accent line
- [ ] NO Table of Contents page — flows directly from cover to body
- [ ] NO numbered section hierarchy — bold inline subheadings only
- [ ] Each theme has 2-4 supporting exhibits
- [ ] All ~15-16 exhibits numbered sequentially and cross-referenced
- [ ] Source attribution on every exhibit
- [ ] Trade recommendations include bold embedded statements + risk factors
- [ ] Bull/bear/tail-scenario risks articulated
- [ ] Detailed disclosure appendix with Reg AC, regulatory notices, copyright
- [ ] Font is Helvetica Neue / Arial (or equivalent geometric sans) — NOT LiberationSans
