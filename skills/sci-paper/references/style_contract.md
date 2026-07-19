# Visual Style & Typography Contract

Extracted from the ResNet paper (He et al., CVPR 2016 Best Paper) via fitz font
analysis and visual inspection of all 12 pages.

## Table of Contents

1. [Reference Typography](#reference-typography)
2. [Page Layout](#page-layout)
3. [Heading Hierarchy](#heading-hierarchy)
4. [Mathematical Notation](#mathematical-notation)
5. [Color Palette](#color-palette)
6. [Header and Footer](#header-and-footer)
7. [Citation and Reference Formatting](#citation-and-reference-formatting)
8. [Special Formatting](#special-formatting)

---

## Reference Typography

The ResNet PDF uses the following font families (extracted via fitz):

| Role | Font Family | Style | Notes |
|------|-------------|-------|-------|
| Body text | NimbusRomNo9L-Regu | Serif, 10pt | Times New Roman equivalent |
| Bold text | NimbusRomNo9L-Medi | Serif, medium weight | Headings, emphasis |
| Bold italic | NimbusRomNo9L-MediItal | Serif, medium italic | Sub-subsection headings |
| Italic text | NimbusRomNo9L-ReguItal | Serif, italic | Emphasis, definitions |
| Math symbols | CMMI7, CMMI8, CMMI9, CMMI10 | Computer Modern Math Italic | Variables in equations |
| Math operators | CMSY6, CMSY8, CMSY9, CMSY10 | Computer Modern Symbol | Math symbols |
| Math extensions | CMEX10 | Computer Modern Extension | Large operators |
| Math text | CMR7, CMR10 | Computer Modern Roman | Math mode text |
| Math bold | CMBX10 | Computer Modern Bold | Bold math |
| Monospace | NimbusMonL-Regu | Monospace | Code, URLs |
| Fallback Chinese | MinionPro-Regular | Serif, CJK | CJK fallback |

### Typography Character

- **Family class**: Serif (academic, traditional, highly legible)
- **Body font**: NimbusRomNo9L-Regu (10pt) - equivalent to Times New Roman
- **Math font**: Computer Modern (CMMI, CMSY, CMR, CMEX, CMBX)
- **Weight contrast**: Moderate (Medium for headings, Regular for body)
- **Density**: Moderate (comfortable line spacing ~1.2x)
- **Formality**: High (no rounded or informal elements)
- **Heading/body hierarchy**: Clear 3-level hierarchy (section, subsection, body)

### Font Strategy for CJK Content

When CJK content is present, preserve the reference typography character:

- **Body text**: Noto Serif CJK or Source Han Serif (to match serif character)
- **Headings**: Same font family, heavier weight
- **Mathematics**: Computer Modern or Latin Modern Math (preserves reference style)
- **Code/Monospace**: Noto Sans Mono CJK or equivalent

Always preserve the visual impression: clean, academic, high-contrast
black-on-white, generous whitespace, strict alignment.

---

## Page Layout

### Double-Column Conference Format (CVPR/ICCV/ECCV Style)

This is the standard layout for the reference paper (12 pages):

```
+---------------------------------------------+
|  [arXiv header - single column, page 1]     |
+--------------+------------------------------+
|              |                              |
|   COLUMN 1   |       COLUMN 2               |
|   (3.25")    |      (3.25")                |
|   ~8.25 cm   |     ~8.25 cm                 |
|              |                              |
+--------------+------------------------------+
|              Page N (centered)              |
+---------------------------------------------+
```

| Parameter | Value |
|-----------|-------|
| Paper size | US Letter (8.5" x 11") |
| Columns | 2 |
| Column width | ~3.25" (8.25 cm) |
| Column gap (gutter) | ~0.25" (0.64 cm) |
| Total text width | ~6.75" |
| Top margin | 0.75-1.0" |
| Bottom margin | 1.0-1.25" |
| Left/right margin | 0.75" |
| Body font size | 10pt |
| Abstract font size | 9pt (single-column) |
| Line spacing | ~1.2x (slightly tight) |
| Paragraph indent | 1 em (first line) |
| Paragraph spacing | 0 pt (indent-based separation) |

**CRITICAL**: When generating PDF output, use a proper LaTeX double-column
template (e.g., `\documentclass[10pt,twocolumn]{article}` with IEEEtran or
CVPR style). Do NOT use HTML-based rendering which loses LaTeX typography.

### Single-Column Format (NeurIPS/ICML Style)

| Parameter | Value |
|-----------|-------|
| Paper size | US Letter |
| Columns | 1 |
| Text width | 5.5-6.0" |
| Margins | 1.0-1.25" |
| Body font size | 10-11pt |
| Line spacing | 1.15x |

---

## Heading Hierarchy

| Level | Style | Example | Font |
|-------|-------|---------|------|
| Paper title | Centered, 17pt, bold | Deep Residual Learning... | NimbusRomNo9L-Medi |
| Section (L1) | Left-aligned, 12pt, bold, numbered | 1. Introduction | NimbusRomNo9L-Medi |
| Subsection (L2) | Left-aligned, 10pt, bold, numbered | 3.1. Residual Learning | NimbusRomNo9L-Medi |
| Sub-subsection | Left-aligned, 10pt, bold italic | Plain Network. | NimbusRomNo9L-MediItal |
| Body | Justified, 10pt, regular | [paragraph text] | NimbusRomNo9L-Regu |

**Heading spacing**:
- Section: 12pt before, 6pt after
- Subsection: 6pt before, 3pt after
- Sub-subsection: 6pt before, 3pt after (inline with text)

---

## Mathematical Notation

### Equation Formatting

- **Display equations**: Centered, numbered on right: `(1)`, `(2)`, ...
- **Numbering**: Arabic numerals, in parentheses, right-aligned
- **Multi-line equations**: Align at relation symbols (`=`, `:=`, `<=`)
- **Inline math**: Use `$...$` for short expressions, avoid numbered equations
- **Spacing**: 6pt above and below display equations

### Symbol Conventions

| Category | Convention | Example |
|----------|------------|---------|
| Scalars | Italic lowercase | $x$, $y$, $\\alpha$ |
| Vectors | Bold lowercase | **x**, **y** |
| Matrices | Bold uppercase | **W**, **H** |
| Sets | Calligraphic | $\\mathcal{H}$, $\\mathcal{F}$ |
| Functions | Italic | $F(x)$, $H(x)$ |
| Operators | Roman (upright) | $\\arg\\min$, $\\max$, $\\mathbb{E}$ |
| Constants | Roman or Greek | $\\pi$, $e$ |

### Equation Environment Example

Key equations should be presented as:

```
    y = F(x, {W_i}) + x.                              (1)
```

With surrounding text defining every symbol:
- "Here **x** and **y** are the input and output vectors of the layers considered.
  The function $F(x, \\{W_i\\})$ represents the residual mapping to be learned."

---

## Color Palette

The ResNet paper uses a **minimal, high-contrast academic palette**:

| Element | Color | Hex |
|---------|-------|-----|
| Body text | Black | #000000 |
| Heading text | Black | #000000 |
| Figure text / labels | Black | #000000 |
| Table text | Black | #000000 |
| Figure curves | Multi-color | #E41A1C (red), #4DAF4A (green), #377EB8 (blue), #984EA3 (purple), #FF7F00 (orange) |
| Table rules (borders) | Black | #000000 |
| Table header rules | Black, thicker | #000000 |
| Hyperlinks (if any) | Dark blue | #0000AA |

**Figure color scheme**:
- Use **distinct, colorblind-safe colors** for different curves/conditions
- Red for baseline / negative result
- Green/blue for proposed method / positive result
- Purple/orange for additional variants
- Dashed lines for training, solid for validation/test

---

## Header and Footer

| Element | Convention |
|---------|------------|
| Page numbers | Bottom center, 10pt |
| Running header | None (conference style) |
| arXiv ID | Left margin, page 1 only (if preprint) |
| Footnotes | Bottom of column, 8pt, numbered with superscript |
| Footnote rule | 2-inch horizontal rule above footnotes |

---

## Citation and Reference Formatting

### In-Text Citations

- Format: `[n]` where n is the reference number
- Multiple: `[1, 9]`, `[23, 9, 37, 13]`
- Range: `[2-5]` (when consecutive)
- Position: Immediately after the claim, before punctuation

### Reference List

- Numbered `[1]`, `[2]`, ... in order of first appearance
- Format: `[n] Author(s). Title. Venue, Year.`
- Author rules:
  - Full author list for <=6 authors
  - "et al." for >=7 authors
  - First author last name + initials, then "et al."
- Venue: Standard abbreviation (CVPR, ICCV, NeurIPS, ICML, TPAMI, IJCV, etc.)
- Page numbers: Omit in reference list for conferences; include for journals

Example:
```
[1] Y. Bengio, P. Simard, and P. Frasconi. Learning long-term dependencies
    with gradient descent is difficult. IEEE Transactions on Neural Networks,
    5(2):157-166, 1994.
[2] K. Simonyan and A. Zisserman. Very deep convolutional networks for
    large-scale image recognition. In ICLR, 2015.
```

**Reference count**: A typical paper has 40-60 references. Ensure ALL cited works
appear in the reference list.

---

## Special Formatting

### Abstract

- Single-column (spans both columns in double-column format)
- 9pt font, slightly narrower measure
- 1 paragraph, no heading "Abstract" (or small-caps "Abstract")
- Must include: background, problem, method, key result(s), significance

### Footnotes

- Use for: URLs, dataset links, additional clarifications
- Avoid for: critical content (may be missed)
- Format: Superscript number, bottom of page

### URLs and Code Links

- Format: Typewriter/monospace font, optionally as footnote
- Example: `http://image-net.org/challenges/LSVRC/2015/`
- Modern practice: Include GitHub repository link in footnote on title page

### Acknowledgments

- After Conclusion, before References
- Smaller font (9pt) or footnote style
- Acknowledge funding sources, compute resources, helpful discussions
