# Structure Contract: GW Observational Results Paper

## Document Section Hierarchy

The canonical structure follows this hierarchy. Each level is mandatory unless noted.

### Compact First Page (All on Page 1)

The first page of the paper must contain ALL of the following, with NO separate
title page or abstract page:

1. **Journal header**: "PHYSICAL REVIEW X 9, 011001 (2019)" (centered)
2. **Title**: Descriptive, includes event name
   (e.g., "Properties of the Binary Neutron Star Merger GW170817")
3. **Author line**: "B. P. Abbott et al.*" with footnote marker
4. **Collaboration**: "(LIGO Scientific Collaboration and Virgo Collaboration)"
5. **Dates**: "(Received 6 June 2018; revised manuscript received 20 September 2018;
   published 2 January 2019)"
6. **Abstract**: Single paragraph, ~200-250 words. See patterns document.
7. **DOI**: "DOI: 10.1103/PhysRevX.9.011001"
8. **Subject Areas**: "Subject Areas: Astrophysics, Gravitation"
9. **License note**: "Published by the American Physical Society under the terms
   of the Creative Commons Attribution 4.0 International license."
10. **I. INTRODUCTION** heading + start of introduction text (two-column layout)

### Level 1: Main Body (Continues from Page 1)

#### I. Introduction
- Historical context of the detection (date, detectors, SNR)
- Initial sky localization and multimessenger context
- Gamma-ray burst observation (GRB 170817A)
- Kilonova identification (SSS17a/AT 2017gfo) and host galaxy (NGC 4993)
- Theoretical background relevant to source type:
  - For BNS: chirp mass, tidal interactions, matter effects, EOS implications
  - For BBH: spin-precession, higher modes, remnant properties
- Improvements over previous analyses (this paper's contributions):
  - Recalibrated data, broader frequency band, more waveform models,
    known source location
- Paper organization paragraph mapping sections to content

#### II. Methods
- **A. Bayesian method**: Bayes' theorem, posterior via MCMC, credible intervals
- **B. Data**: Noise model (Gaussian, stationary), PSD estimation (Fig. 1),
  calibration model (amplitude/phase uncertainty, Eq. 1), data quality,
  glitch subtraction, Anderson-Darling tests
- **C. Waveform models**: Table I comparing all models. Description of each
  model (PN order, tidal effects, spin treatment, precession). Model
  comparison figure (Fig. 2: amplitude/phase differences). Reference model
  selection (PhenomPNRT as standard).
- **D. Source parameters and choice of priors**: Intrinsic parameters (masses
  m1>=m2, spins, tidal deformability), extrinsic parameters (sky location,
  distance, inclination), detector-frame vs source-frame, prior choices
  (high-spin chi<=0.89 vs low-spin chi<=0.05), distance prior
  (uniform-in-volume), tidal parameter priors

#### III. Properties Inferred from the Signal

Subsections follow a **canonical order** across all GW results papers:

1. **A. Localization**
   - Sky map with 50% and 90% credible regions (Fig. 3)
   - Improved 90% region: 16 deg^2 (from 28 deg^2)
   - Luminosity distance from GW data alone
   - Hubble constant measurement (H0 ~ 70 km/s/Mpc)
   - Inclination angle constraints with EM distance priors (Fig. 4)

2. **B. Masses**
   - Physical context: chirp mass enters at lowest PN order, best measured
   - Chirp mass: detector-frame with subpercent precision
   - Component masses: 90% credible intervals, source-frame
   - Mass ratio and degeneracy with spins
   - Comparison of detector-frame vs source-frame
   - Joint posterior figure (Fig. 5) with 1D marginals
   - Main results table (Table II)

3. **C. Spins**
   - Physical context: two effects (aligned-spin phasing, precession)
   - Effective spin parameter chi_eff: definition (Eq. 3), enters at 1.5PN
   - q-chi_eff degeneracy (Fig. 7)
   - Precession parameter chi_p: definition (Eq. 4)
   - Spin orientations: polar plots showing tilt angles (Figs. 8-9)
   - Prior comparison always shown
   - Constraints from precessing model only

4. **D. Tidal parameters** (for BNS events)
   - Physical context: tidal deformability definition, enters at 5PN
   - Individual tidal deformabilities Lambda_1, Lambda_2 (Fig. 10)
   - Combined tidal parameter tilde-Lambda: definition (Eq. 5)
   - Prior reweighting procedure for tilde-Lambda (explained in detail)
   - EOS model comparison: 7 representative EOS curves overlaid (Figs. 10-11)
   - Two-sided vs one-sided constraints, HPD intervals
   - Model comparison with EOB waveforms and RAPIDPE validation

#### IV. Limits on Postmerger Signal
- Physical context: remnant types (prompt collapse, hypermassive NS,
  supramassive NS, stable NS)
- BAYESWAVE analysis method (morphology-agnostic)
- Bayes factor: Gaussian noise strongly preferred
- 90% credible upper limits on strain amplitude and radiated energy (Fig. 13)
- Comparison with numerical simulations (different EOSs, Table III)
- Sensitivity improvement factors needed for detection

#### V. Conclusions
- Summary of key measurements with specific numerical values
- Comparison to previous work (initial GW170817 analysis)
- Waveform systematics assessment (agreement across models)
- Implications for astrophysics (EOS constraints, GR tests, cosmology)
- Future outlook (design sensitivity, additional events, improved waveform models)
- Connection to companion paper(s)

### Level 1: Back Matter

- **Acknowledgments**: Funding agencies (NSF, STFC, MPS, INFN, CNRS, etc.),
  computational resources, LIGO Open Science Center, document number
- **Appendix A: Source Properties from Additional Waveform Models**
  - Table IV: Same parameters as Table II for TaylorF2, SEOBNRT, PhenomDNRT
  - Table V: RAPIDPE results for SEOBNRv4T and TEOBResumS
  - Discussion of agreement and exceptions across models
- **Appendix B: Injection and Recovery Studies**
  - Validation of parameter estimation pipeline
  - Systematic error assessment for waveform models
  - Figures showing recovery accuracy
- **References**: 150-200 numbered references in Physical Review format
- **Full Author List**: Complete list of all collaboration members with
  affiliations (typically 10-15 pages)

## Figure and Table Numbering

- **Figures**: Sequential Arabic numerals: Fig. 1, Fig. 2, ... (15+ figures)
- **Tables**: Sequential Roman numerals: Table I, Table II, ...
- **Equations**: Sequential Arabic numerals in parentheses: (1), (2), ...
- **Cross-references**: "Fig. 1", "Table I", "Sec. III A", "Eq. (3)", "Ref. [3]"

## Page Break and Section Break Rules

- NO explicit page breaks between sections; continuous flow throughout
- Figures placed at top of column or page (floating)
- Wide tables may span full page width
- New sections start immediately after previous section ends
- Section headings use Roman numerals for main sections, capital letters for
  subsections (e.g., "III. A. Localization")

## Content Depth Requirements

- **Total page count**: 30-35 pages for a full BNS results paper
  (including 10-15 pages of author list)
- **Reference count**: 150-200 references
- **Introduction**: 3-4 pages (two-column)
- **Methods**: 4-5 pages with waveform model descriptions, equations, Table I
- **Results**: 10-12 pages with detailed discussion, 12+ figures, Table II
- **Postmerger**: 3-4 pages with analysis description, Fig. 13, Table III
- **Conclusions**: 1-2 pages
- **Appendices**: 3-4 pages with Tables IV-V and validation figures
