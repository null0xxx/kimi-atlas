---
name: astro-observation-report
description: "Skill for writing gravitational-wave observational results papers for compact binary coalescence events (BNS, BBH, NSBH) detected by LIGO, Virgo, or KAGRA. Covers paper architecture, first-page layout, parameter estimation figures, uncertainty notation, credible region plots, statistical conventions, and running headers in Physical Review X two-column journal style."

---

# Gravitational-Wave Observational Results Writing Guide

A markdown-driven skill encoding document structure, presentation patterns, and
statistical conventions from LIGO/Virgo/KAGRA collaboration SOTA papers.

## Reference Source

- **Reference type**: Uploaded PDF artifact (Physical Review X journal article)
- **Reference artifact type**: PDF (peer-reviewed physics journal)
- **Reference File Type**: PDF
- **Supported outputs**: PDF, DOCX, PPTX
- **Default output**: PDF (academic journal manuscript, two-column layout)

## First-Page Layout (Critical)

The Physical Review X format places ALL of the following on page 1:

1. Journal header line: "PHYSICAL REVIEW X 9, 011001 (2019)" (centered, small caps)
2. Title (bold, centered, ~14pt)
3. Author line: "B. P. Abbott et al." with collaboration in parentheses
4. Received/revised/published dates
5. Abstract (single paragraph, ~200-250 words, full width or two-column)
6. DOI line and Subject Areas
7. Beginning of I. INTRODUCTION (small-caps heading)

**There is NO separate title page or abstract page.** The introduction starts
immediately after the abstract on the same page.

## Core Workflow

1. **Establish paper scope** -- Identify event(s), detector network, analysis epoch.
   Determine measurable parameters (masses, spins, tides, location, inclination)
   and what is not measurable (postmerger signal).

2. **Structure the manuscript** -- Follow section hierarchy in
   `references/structure_contract.md`. Architecture: compact first page with
   abstract + intro -> Methods -> Results (by parameter class) -> Postmerger limits
   -> Conclusions -> Appendices -> Full author list.

3. **Write the Abstract** -- Single paragraph: detection statement (SNR, detectors,
   event name, source type), multimessenger context, key parameter constraints with
   numerical values, model comparison, postmerger upper limits.

4. **Write Methods** -- Bayesian framework, data (PSD, calibration), waveform models
   (comparison table in Table I), prior choices (high-spin vs low-spin).

5. **Present results by parameter class** -- Canonical order: Localization -> Masses
   -> Spins -> Tidal parameters -> Postmerger limits. Each class: physical motivation,
   posterior figures, numerical constraints, model comparison.

6. **Create figures and tables** -- Follow taxonomy and caption conventions in
   `references/observational_results_patterns.md`. Every results section must have
   figures. Tables use booktabs style. See the figure list below.

7. **Write conclusions and back matter** -- Summary, comparison to previous work,
   waveform systematics, future outlook. Follow with Acknowledgments, Appendices
   (additional model results + injection/recovery), and full author list with
   affiliations.

## Required Figures (15+ Total)

Every GW observational results paper must include figures. The reference contains
the following figure types. Even placeholder or simplified versions must be created.

| Fig # | Type | Content |
|-------|------|---------|
| 1 | PSD plot | Detector sensitivity curves (LIGO Hanford, Livingston, Virgo) |
| 2 | Model comparison | Relative amplitude and phase differences between waveform models |
| 3 | Sky map | Localization with 50%/90% credible regions and EM counterpart |
| 4 | 2D posterior | Inclination vs luminosity distance (GW-only and EM-informed) |
| 5 | 2D posterior | Component masses (m1-m2) for high-spin and low-spin priors |
| 6 | 1D PDF | Effective spin parameter for high-spin and low-spin priors |
| 7 | 2D posterior | Effective spin vs mass ratio (degeneracy illustration) |
| 8 | Polar plot + PDF | Spin orientations and precession parameter (high-spin) |
| 9 | Polar plot + PDF | Spin orientations and precession parameter (low-spin) |
| 10 | 2D posterior | Tidal deformability parameters with EOS curves (two panels) |
| 11 | 1D PDF | Combined tidal parameter with EOS predictions (two panels) |
| 12 | 2D posterior | Tidal parameter vs mass ratio (high-spin vs low-spin) |
| 13 | Upper limits | Postmerger strain and radiated energy (two panels) |
| 14-15 | Injection study | Parameter recovery validation plots (Appendix B) |

## Running Headers and Page Numbers

- **Even pages (left header)**: Shortened article title in small caps
  (e.g., "PROPERTIES OF THE BINARY NEUTRON STAR MERGER ...")
- **Odd pages (right header)**: Journal citation in small caps
  (e.g., "PHYS. REV. X 9, 011001 (2019)")
- **Page numbers**: Bottom center, format "011001-N" where N is sequential
- **Page 1 only**: Has journal header "PHYSICAL REVIEW X 9, 011001 (2019)"
  and article ID footer "2160-3308/19/9(1)/011001(32)" + "Published by the
  American Physical Society"

## Statistical Conventions

- **Uncertainty notation**: Median with asymmetric credible intervals:
  `x^{+upper}_{-lower}` (e.g., `2.73^{+0.04}_{-0.01} M_\odot`).
- **One-sided limits**: `x \in (lower, upper)` for 90% credible intervals bounded by priors.
- **HPD intervals**: Smallest interval containing 90% probability, for asymmetric posteriors.
- **Credible regions**: 50% (inner, dashed) and 90% (outer, solid) contours for 2D posteriors.
- **Bayes factors**: Evidence ratios between competing models.

## Font and Typography

- **Reference fonts**: Times-based serif family (Times-Roman, Times-Italic,
  Times-Bold from the journal), with Computer Modern math symbols.
- **Substitute font strategy**: When unavailable, use Times New Roman, TeX Gyre
  Termes, or STIX Two Text. For CJK content, use a CJK-capable serif font
  (SimSun, Noto Serif CJK) consistently across the entire document.
- **Section headings**: Small caps (e.g., "I. INTRODUCTION"), bold for main sections.
- **Subsection headings**: Bold title case (e.g., "A. Bayesian method").
- **Math typesetting**: Numbered display equations, key equations explicitly shown.

## Key Reference Files

| File | When to Read |
|------|-------------|
| `references/structure_contract.md` | When planning the paper outline and section hierarchy |
| `references/observational_results_patterns.md` | When writing specific sections, figures, tables, captions |
| `references/style_contract.md` | When formatting the final document or resolving layout questions |
