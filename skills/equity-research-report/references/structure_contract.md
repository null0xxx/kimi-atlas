# Structure Contract: Institutional Research Report

## Table of Contents
1. [Document Section Hierarchy](#document-section-hierarchy)
2. [Cover Page Structure](#cover-page-structure)
3. [Table of Contents](#table-of-contents)
4. [Executive Summary](#executive-summary)
5. [Body Sections](#body-sections)
6. [Exhibit Numbering](#exhibit-numbering)
7. [Vega Exposure Section](#vega-exposure-section)
8. [Appendix Sections](#appendix-sections)
9. [Glossary of Terms](#glossary-of-terms)
10. [Disclosure Appendix](#disclosure-appendix)
11. [Page Break Rules](#page-break-rules)
12. [Cross-References](#cross-references)

---

## Document Section Hierarchy

```
Cover Page
Table of Contents
Executive Summary
Section 1: [Primary Topic]
  1.1 [Sub-topic]
  1.2 [Sub-topic]
    1.2.1 [Sub-sub-topic]
Section 2: [Primary Topic]
  2.1 [Sub-topic]
  ...
Section N: [Primary Topic]
  ...
Appendix: Where to find stuff
  Data sources
  Methodology references
Glossary of Terms
Disclosure Appendix
```

### Heading Level Mapping
| Level | Style | Usage |
|-------|-------|-------|
| H1 | 16-18pt bold, underline | Major sections (Executive Summary, Section titles) |
| H2 | 12-13pt bold | Sub-sections within major sections |
| H3 | 11pt bold | Sub-sub-sections, specific topics |
| Body | 10pt regular | Paragraph text |
| Bold lead-in | 10pt bold | Bold opening phrase in bullets |

### Required Section Types (per judge feedback)
A complete institutional research report MUST include:
1. **Cover Page** with summary and key takeaways
2. **Table of Contents** with page numbers
3. **Executive Summary** with bold opening thesis paragraph
4. **Body Sections** (multiple analytical sections)
5. **Appendix: Where to find stuff** with data sources and methodology links
6. **Glossary of Terms** defining key terminology
7. **Disclosure Appendix** with legal disclaimers

---

## Cover Page Structure

### Required Elements (in order)
1. **Top banner**: Navy blue bar with date (left) and firm identifier (right)
2. **Title**: Large white bold text on navy banner - the main report title
3. **Category label**: Below banner right side - report category (e.g., "Options Research")
4. **Subtitle**: Below banner - descriptive subtitle in large dark text
5. **Two-column layout**:
   - Left column (~60%): 4-5 brief summary paragraphs with H2-style blue headings
     * Each summary covers a key topic (2-4 sentences)
     * Include key statistics and figures
   - Right column (~40%): Sidebar with light gray background containing:
     * Analyst info: Name, credentials, phone, email, firm
     * "N Things to Know" or "Key Takeaways" numbered list (10 items typical)
     * Sidebar headings in medium blue (`#4472C4`)
6. **Horizontal rule**: Thin line above disclaimer
7. **Bottom disclaimer**: Full-width legal text in small font (8pt)

### Sidebar "N Things to Know" Pattern
Each item follows: **N. Bold topic phrase**: Brief 1-2 sentence explanation
Example:
```
1. Know what you're trading
   VIX ETPs track VIX futures, not the VIX.
2. Learn from the performance record
   Long vol is difficult to buy and hold but has strong gains during market shocks.
```

---

## Table of Contents

### Layout
- Page 2 (immediately after cover)
- "Table of Contents" as H1 with underline
- Single column, full width

### Entry Format (IMPORTANT - per judge feedback)
- **Major sections**: Bold text with right-aligned page number
- **Sub-sections**: Regular text, indented ~0.3 inch, with right-aligned page number
- Page numbers must be right-aligned (not dot leaders; clean spacing between title and page number)
- Format example:
  ```
  Executive Summary: Navigating the VIX ETP market                 3
  Trading: VIX ETPs are benchmarked to VIX futures                  5
    Accessing volatility exposure: What actually trades?            5
    Trading Activity: How big is the space?                         5
  VIX ETP performance                                               8
  ```

### Bottom Note
- After TOC entries, a centered note: "All prices and volumes in this report are as of [date]."

---

## Executive Summary

### Position
- Page 3, following Table of Contents

### Content Structure
- H1: "Executive Summary: [Report Topic]"
- **Opening paragraph: FULLY BOLD** - this is the core thesis statement that summarizes the entire report
  - Sets the context, states the main findings, and outlines key conclusions
  - Typically 4-6 sentences
- 4-5 subsections each with H2 heading covering key themes
- Each subsection: 2-4 paragraphs
- Bold lead-in phrases for key points

### Style Notes
- The first paragraph being fully bold is a **critical** distinguishing feature
- Subsections mirror the major body sections that follow
- Include specific numbers and percentages
- Reference key exhibits by number

### Example Opening Bold Paragraph
```
**Policy uncertainty is elevated around the globe and yet the VIX has posted one of its
lowest starts to a calendar year on record. Many investors want to get long volatility
via VIX ETPs. But buyer beware. Not a single VIX ETP actually tracks the VIX. They
track VIX futures and the performance differential can be large. In our view it is
important to understand how VIX ETPs are constructed, key return drivers and
historical performance across bull, bear, and boring markets before trading.**
```

---

## Body Sections

### Standard Section Structure
```
H1: Section Title: Descriptive Subtitle
  [Introductory paragraph(s) - often bold for emphasis]

H2: Sub-section Title
  [Body text with bullets and/or paragraphs]
  
  [Exhibit - Table or Chart]
  
  [More body text]

H2: Next Sub-section Title
  ...
```

### Content Patterns
- Each major section (H1) starts on a new page
- Sections open with context-setting paragraph(s) - often **bold** for the opening paragraph
- Sub-sections use H2 headings
- Data is presented through exhibits (tables/charts)
- Analysis follows exhibits explaining the data
- Bold lead-in pattern for bullet items

### Text Content Rules
- Use present tense for analysis
- Cite specific numbers and percentages
- Reference exhibits by number: "Exhibit 3 shows..."
- Use professional, objective tone
- Include forward-looking statements with appropriate qualifiers
- Use mathematical formulas where relevant (weight formulas, portfolio return equations)

---

## Exhibit Numbering

### Sequential System
- All exhibits (charts AND tables) share a single sequential numbering
- Format: "Exhibit N: [Descriptive Title]"
- Title is descriptive, not generic

### Examples
```
Exhibit 1: VIX ETPs have been a driving force behind the increase in VIX futures liquidity
Exhibit 2: Characteristics of VIX ETPs
Exhibit 3: VIX ETP market breakdown by leverage, term, and geography
```

### Exhibit Components
1. **Label**: "Exhibit N:" in bold
2. **Title**: Descriptive title in bold
3. **Description** (optional): 1-2 sentence explanation below title
4. **Data**: The table or chart
5. **Source**: "Source: [provider], [firm] Global Investment Research." in italic

---

## Vega Exposure Section

### Purpose
- Quantify how much volatility exposure (vega) VIX ETPs control
- Show percentage of VIX futures open interest attributed to ETPs

### Required Content Structure
```
H1: Vega Exposure: ETPs [X]% of VIX futures OI in [Year]; [Y]% in [Year]
  [Opening paragraph explaining the importance of vega exposure analysis]

H2: In [Quarter]: VIX ETPs accounted for [X]% of VIX futures OI
  - Bullet points with key statistics:
    * Investor appetite for VIX futures trends
    * Liquidity changes since ETP launch
    * VIX futures volumes and open interest data
    * Breakdown by ETP type

H2: Demand: Long volatility VIX ETPs
  - Single-levered longs: volume and OI data
  - Doubled-levered longs: volume and OI data

H2: Supply: Short volatility VIX ETPs
  - Inverse single-levered: volume and OI data
  - Trends in short vol exposure

[Exhibit with chart showing VIX futures open interest over time]
```

---

## Appendix Sections

### "Appendix: Where to find stuff"

#### Data Section
- H2: "Data: Where to find [topic] data"
- Bullet list of data sources with:
  - **Bold source name**: Description
  - Hyperlinks to external resources (blue, underlined)
- Example:
  ```
  - **CBOE VIX futures historical price data**: price and volume data for VIX futures
    contracts, back to May 2004 (http://www.cfe.cboe.com/data/historicaldata.aspx).
  - **Standard & Poor's Dow Jones VIX Futures Indices**: daily closing index levels can
    be found at http://www.spindices.com/index-family/strategy/vix.
  ```

#### Methodology Section
- H2: "Methodology: How the benchmark indices are built"
- Bullet list of methodology documents with:
  - **Bold methodology name**: Description + hyperlink

---

## Glossary of Terms

### Position
- After Appendix, before Disclosure Appendix
- Typically 1-2 pages

### Format
- H1: "Glossary of Terms"
- Each term: **Bold term**: Definition paragraph
- Terms should be alphabetically ordered
- Include relevant exhibits (e.g., mapping tables of index names to notations)

### Required Term Types
For financial/derivatives research, include definitions for:
- Key metrics (Backwardation, Contango)
- Product types (ETF, ETN, ETP)
- Index terminology (Excess return, Total return)
- Notation conventions used in the report
- Industry jargon relevant to the topic

### Example Format
```
**Backwardation:** Occurs when the VIX term structure is downward sloping and the spot
VIX level is higher than the VIX futures (VIXt > F1,t > F2,t). Backwardation is also referred to as
an inversion of the term structure.

**Contango:** Futures contracts are said to be in contango when the VIX term structure is
upward sloping with VIX futures trading at higher levels than VIX spot (VIXt < F1,t < F2,t).
```

### Notation Table (if applicable)
- Exhibit with mapping between shorthand notation and full index names
- Include Bloomberg tickers, term, leverage, ER/TR flags

---

## Disclosure Appendix

### Position
- Final section of document (last 2-3 pages)

### Required Content
1. **Reg AC**: Analyst certification paragraph
2. **Disclosures**:
   - Option Specific Disclosures
   - Price target methodology
   - Pricing disclosure
   - General Options Risks
   - Buying/Selling options risks
3. **Distribution of ratings/investment banking relationships**: Table showing rating distribution
4. **Disclosures required by United States laws and regulations**: Ownership, conflicts, compensation
5. **Additional disclosures by jurisdiction**: Australia, Brazil, Canada, Hong Kong, India, Japan, Korea, New Zealand, Russia, Singapore, Taiwan, UK, EU, etc.
6. **General disclosures**: Research availability, conflict of interest, risk warnings
7. **Global product; distributing entities**: Firm entities by region

### Format
- H2 headings for major subsections
- Dense legal text in small font (9pt)
- Bold for defined terms within legal text
- Tables for rating distributions

---

## Page Break Rules

### Required Page Breaks
- Before Cover Page (document start)
- Before Table of Contents
- Before Executive Summary
- Before each H1 major section
- Before Appendix
- Before Glossary of Terms
- Before Disclosure Appendix

### No Page Break
- Between H2 subsections (keep flow continuous)
- Between body text and exhibits (keep exhibit with preceding context when possible)
- Between exhibit and its source line

---

## Cross-References

### Internal References
- Reference exhibits by number: "As shown in Exhibit 3..."
- Reference sections by name: "In the Trading section, we discuss..."
- Reference page numbers: "See page 14 for details."

### External References
- URLs in blue, underlined
- Format: descriptive text with hyperlink (not raw URLs when possible)
