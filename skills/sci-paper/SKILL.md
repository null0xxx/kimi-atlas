---
name: sci-paper
description: "Structured guidance for composing, formatting, and presenting scientific research papers for top-tier venues (CVPR, ICCV, NeurIPS, ICML, ACL, ICLR, etc.). Covers the full workflow: section-by-section drafting, figure and table design, LaTeX typography, narrative logic, and submission-ready polishing. Use to write, revise, or format a manuscript into camera-ready or preprint PDF."

---

# SCI Paper Writing Skill

Guidance for producing publication-quality scientific research papers, extracted
from analysis of the ResNet (He et al., CVPR 2016 Best Paper) SOTA artifact and
generalized for computer vision, machine learning, and broader scientific domains.

## Reference Source

- **Type**: Uploaded PDF artifact (native PDF)
- **Artifact**: ResNet paper - "Deep Residual Learning for Image Recognition"
- **Reference File Type**: PDF (conference proceeding style, double-column LaTeX)
- **Primary Language**: English (CJK-capable typography strategy defined for
  mixed-script output)
- **Page count**: 12 pages (8 main + 1 references + 3 appendix)

## Supported Outputs

| Format | Default | Notes |
|--------|---------|-------|
| PDF    | Yes     | Primary target for camera-ready submission via LaTeX |
| DOCX   | Yes     | For collaborative drafting and advisor review |
| PPTX   | Yes     | For oral-presentation slide decks derived from paper |

When the user does not specify a format, default to **PDF** for final manuscripts
and **PPTX** for oral-presentation derivatives.

**CRITICAL**: When generating a full paper, produce **all required sections** with
**all figures, tables, equations, and references** - never produce a partial or
abbreviated paper. The reference artifact is 12 pages; match this scale for full
paper reproductions.

## Workflow Overview

1. **Plan** - Define target venue, page limit, and section budget
2. **Draft** - Write ALL sections following the narrative-logic contract
3. **Design** - Create ALL figures, tables, and equations per the guidelines
4. **Polish** - Apply typography, cross-references, and submission formatting
5. **Convert** - Render to requested output format

## Core Contracts

Load the relevant reference file when the user request touches that domain:

- **Structure & Narrative**: See `references/structure_contract.md`
  - Section hierarchy, narrative arc, paragraph-level patterns, citation strategies.
- **Visual Style & Typography**: See `references/style_contract.md`
  - Page layout, font system, color usage, mathematical notation, header/footer rules.
- **Figures, Tables & Equations**: See `references/figure_table_guidelines.md`
  - Caption conventions, numbering, chart styling, table formatting, equation layout.

## Complete Paper Requirements

When producing a full paper reproduction or draft, the output MUST include:

### All Sections (in order)
1. Title page: Title, Authors, Affiliations, Abstract, Keywords
2. Section 1: Introduction (1-1.5 pages)
3. Section 2: Related Work (0.5-1 page)
4. Section 3: Method/Approach (2-3 pages) with subsections 3.1, 3.2, 3.3, 3.4
5. Section 4: Experiments/Results (2.5-3.5 pages) with subsections 4.1, 4.2, 4.3
6. Section 5: Conclusion (0.3-0.5 pages)
7. References (1 page, numbered [1]-[N])
8. Appendices A-C (optional, 2-3 pages)

### All Visual Elements
- **Figures**: ALL referenced figures with proper captions below (Fig. 1-N)
- **Tables**: ALL referenced tables with proper captions above (Table 1-N)
- **Equations**: ALL numbered equations with sequential numbering (1), (2), ...
- **Footnotes**: Numbered superscript footnotes at page bottom

### Page Count Rules
- Full paper: 8-12 pages depending on content
- Minimum: Each major section must have enough content (Introduction >= 5 paragraphs)
- Never produce a paper compressed into 1-2 pages

## Venue-Specific Adaptation

| Parameter | CVPR/ICCV/ECCV | NeurIPS/ICML/ICLR | ACL/EMNLP |
|-----------|---------------|-------------------|-----------|
| Page limit | 8 + refs | 9 + refs | 8 + refs |
| Columns | 2 | 1 (NeurIPS/ICML), 2 (ICLR) | 2 |
| Abstract | 1 para, ~150 words | 1 para, ~200 words | 1 para, ~150 words |
| Fig/Table per page | 1-2 | 1-2 | 1-2 |

## Quick Checklist (Pre-Submission)

- [ ] **Title**: Concise, specific, no unnecessary jargon
- [ ] **Abstract**: Contains background, problem, method, key results, significance
- [ ] **Introduction**: Domain -> sub-domain -> specific gap -> contribution list -> roadmap
- [ ] **Related Work**: Organized by theme, not by paper; explicit differentiation
- [ ] **Method**: Mathematical formulation before implementation; all subsections present
- [ ] **Experiments**: ALL subsections with datasets, metrics, baselines, results, ablations
- [ ] **Figures**: All referenced before appearing; captions self-contained; BELOW figure
- [ ] **Tables**: All referenced; best results in **bold**; captions ABOVE table
- [ ] **Equations**: Numbered sequentially; all symbols defined in surrounding text
- [ ] **References**: Complete numbered bibliography [1]-[N]
- [ ] **Page count**: Matches target venue (8-12 pages), not compressed
