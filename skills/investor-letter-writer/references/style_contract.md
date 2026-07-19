# Style Contract — Investment Memo

Two reference styles: narrative investor letter from a top credit/value investor and a structured VC deal memo from a leading venture firm.

## Core Principle: Plain, Text-First Documents

Investment memos are **content vehicles, not design objects**. Both reference memos are intentionally minimal: black text on white paper, no decorative elements, no color, no styled boxes. The professionalism comes from the quality of analysis, never from formatting.

## Color Palette

| Usage | Color |
|-------|-------|
| Body text | Black (#000000) |
| Section headings | Black — underlined (narrative) or bold (structured) |
| Rules/lines | Black, 0.5pt |
| Footer text | Black |
| Hyperlinks | Black (or blue #0000EE if hyperlinked) |

**No other colors. No gray text, no colored backgrounds, no accent colors, no shading, no fills.**

## Typography System

### Font Family

**Times New Roman** (or equivalent system serif: Georgia, Cambria) for **all text** — body, headings, block quotes, footer, captions, tables. No mixing of font families within the document.

The narrative memo reference uses:
- TimesNewRomanPSMT (regular body)
- TimesNewRomanPS-BoldMT (bold emphasis)
- TimesNewRomanPS-ItalicMT (italic quotes, captions)

### Type Scale

| Element | Size | Style |
|---------|------|-------|
| Memo header values (Re: line) | 12pt | Regular |
| Section headings | 11-12pt | Underlined (narrative) OR Bold (structured) |
| Body text | 11pt | Regular |
| Bold emphasis within body | 11pt | Bold |
| Block quotes / indented text | 11pt | Italic |
| Bullet list items | 11pt | Regular |
| Footer (copyright, page number) | 9-10pt | Regular (page number may be bold) |
| Legal disclaimers | 9pt | Italic |
| Exhibit captions | 10pt | Italic |

### Line Spacing

- Body paragraphs: 1.15 to 1.5 line spacing
- Paragraph spacing after: 6-12pt
- Headings: flush with text flow, no extra spacing above, 6-12pt below
- Block quotes: 1.15 line spacing, indented ~0.5 inch left

## Page Layout

### Margins

- Top: 1 inch (2.54 cm)
- Bottom: 1 inch (2.54 cm)
- Left: 1 inch (2.54 cm)
- Right: 1 inch (2.54 cm)

### Cover Page

**NONE.** The document begins immediately with the memo header block. No title page, no decorative cover, no graphics.

### Memo Header Block (Page 1)

```
Memo to:     [Recipient]
From:        [Author]
Re:          [Subject]
Date:        [Date]
________________________________________________________________________
```

Labels ("Memo to:", "From:", "Re:", "Date:") flush left. Values follow a consistent indentation (tab-aligned). A horizontal rule spans the full width below the header.

No "Memo to:" variant: use compact single-line header for deal memos only:
```
To: [Recipient]    From: [Author]    Re: [Subject]    Date: [Date]
________________________________________________________________________
```

### Body Layout

- Single-column, full-width text
- Left-aligned (not justified)
- No first-line indent for paragraphs; use paragraph spacing instead
- Continuous text flow — sections flow directly into one another with no page breaks

### Running Headers

**NONE.** No section-name headers in page margins. Page headers are blank.

### Footer

Three-part footer across the bottom:
```
© [Year] [Firm Name]                              [Page N]          All Rights Reserved
```
- Left: Copyright notice (e.g., "© [Year] [Firm Name]")
- Center: Page number in bold (e.g., "2")
- Right: "All Rights Reserved"

For deal memos with confidentiality, use:
```
CONFIDENTIAL — FOR INTERNAL USE ONLY                              [Page N]
```

## Section Heading Style

### Narrative/Investor Letter Style (Default)

Section headings are **underlined text on its own line**, in the flow of the document:

```
...end of previous paragraph.
Understanding AI

Before moving on to the meat of the matter...
```

Characteristics:
- Underlined, same or slightly larger than body text (11-12pt)
- On its own line, followed by a blank line then body text
- NOT numbered
- NOT bold (unless bold is the only emphasis; underline is the primary marker)
- NOT in a larger font or different color
- Not preceded by a page break

Examples of narrative section headings:
- "Understanding AI"
- "Can AI Think?"
- "Recent Developments in AI"
- "Legal Information and Disclosures" (final section, italic + underlined)

### Structured/Deal Memo Style (Alternative)

For venture deal memos, use **bold text headings** (top-tier VC convention):

```
Introduction

[Company] represents an interesting seed-stage investment opportunity...

Deal

Our proposal is to invest $1m in the seed stage...
```

Characteristics:
- Bold, 11-12pt, on its own line
- Followed by a blank line then body text
- NOT numbered (no "1.", "2.", "3." prefixes)
- Sub-headings may be bold and smaller (e.g., "Company Purpose:", "Problem:")

## Text Treatment Rules

### Bold

Use bold for emphasis **within** paragraphs, not for headings (unless using structured style):
- Key conclusions or recommendations
- Important phrases that anchor the reader
- Metric highlights
- Opening thesis sentences

Example: "**First, there's the pace at which developments in AI are occurring.** That speed is unlike anything we've seen before..."

### Italic

- Block quotes and third-party excerpts
- Exhibit captions
- Legal disclaimers
- Company/product names on first mention (optional convention)
- Section title for legal/disclaimer section: "*Legal Information and Disclosures*" with underline

### Underline

- Section headings in narrative-style memos (this is the PRIMARY heading style)
- Do NOT use underline for body text emphasis

### Quoted / Indented Blocks

- Left indent: 0.5 inch from left margin
- Font: italic, 11pt, same line spacing as body
- No quotation marks at block level
- No left border or background shading
- No colored accent bar
- Attribution on a new line, preceded by em-dash, right-aligned or inline

Example:
```
        Someone designed a nine-module curriculum specifically for you, built
        around your December memo, your intellectual frameworks...

        —[Source attribution]
```
## Table Style

Both reference memos avoid formal tables. The narrative memo contains **zero tables**. Data should be presented as:

- Inline text with bold key values
- Bullet-point lists with indented sub-items
- Simple indented blocks for structured data

If a table is absolutely necessary (e.g., financial summary in a deal memo):
- Thin black lines for header row and outer border only
- No colored fills (header row may have bold text only)
- Black text throughout
- 10pt font

## Exhibit Style

- Exhibits embedded inline, not on separate pages
- Simple line charts or basic figures; no styled charts
- Exhibit label above: "Exhibit 1: [Description]" — bold or italic, 10pt
- No colored backgrounds or borders around exhibits
- Reference in text: "(see Exhibit 1)" or "as shown in Exhibit 1"

## Confidentiality & Legal Markings

When the memo contains sensitive information, add to the footer only:
- Left-aligned: "Confidential — For Internal Use Only" or "Highly Confidential"
- 9pt, uppercase or small caps

Legal disclaimers at document end:
- Italic, 9pt, left-aligned
- Preceded by a horizontal rule
- Heading: "*Legal Information and Disclosures*" underlined
- Standard disclaimers: views subject to change, past performance, not an offer, sources

## CJK Typography

If the memo contains Chinese/Japanese/Korean content, substitute Times New Roman with a CJK-capable serif: Noto Serif CJK, Source Han Serif, or Songti (宋体). Apply this substitution uniformly across all text elements.
