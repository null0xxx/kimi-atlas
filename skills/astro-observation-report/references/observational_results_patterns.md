# Observational Results Presentation Patterns

## Table of Contents
1. [Abstract Pattern](#abstract-pattern)
2. [Physical Quantity Description Patterns](#physical-quantity-description-patterns)
3. [Presentation Order and Logical Connections](#presentation-order-and-logical-connections)
4. [Figure Taxonomy and Specifications](#figure-taxonomy-and-specifications)
5. [Figure Caption Patterns](#figure-caption-patterns)
6. [Table Patterns](#table-patterns)
7. [Model Comparison Conventions](#model-comparison-conventions)

---

## Abstract Pattern

The abstract is a **single paragraph** (~200-250 words) structured as:

1. **Detection statement**: Date, detectors, event name, source type, SNR
2. **Multimessenger context**: EM counterpart, host galaxy (if applicable)
3. **Key measurements** (with numerical values):
   - Sky localization area (90% credible region)
   - Mass constraints (component and total)
   - Spin constraints (effective spin, individual spin bounds)
   - Tidal deformability constraints (for BNS)
4. **Analysis improvements**: What is new/better in this paper
5. **Postmerger**: Upper limits on postmerger emission

Example structure:
> "On [date], the [detector network] observed [event name], [source type]
> with [SNR]. The initial sky localization allowed [EM follow-up]. In this
> work, we improve initial estimates of [parameter list] using [improvements].
> We extend the frequency range to [range]. We find [key result 1 with
> numbers], [key result 2 with numbers], and [key result 3 with numbers]."

---

## Physical Quantity Description Patterns

### Uncertainty Notation System

| Notation | Meaning | Example | When Used |
|----------|---------|---------|-----------|
| `x^{+a}_{-b}` | Median, 5% lower, 95% upper | `2.73^{+0.04}_{-0.01} M_\odot` | Two-sided constraints |
| `x^{+a}_{-b}` (symmetric) | Median with symmetric error | `1.186^{+0.001}_{-0.001} M_\odot` | High-precision measurements |
| `(lower, upper)` | One-sided 90% credible interval | `m_1 \in (1.36, 1.89) M_\odot` | Prior-bounded quantities |
| `x \in (a, b)` | 90% credible interval | `\chi_\text{eff} \in (-0.01, 0.02)` | Spin parameters |
| `(0, upper)` | 90% upper limit | `\tilde{\Lambda} \in (0, 630)` | Non-detection scenarios |
| HPD interval | Smallest 90% interval | `300^{+420}_{-230}` (90% HPD) | Asymmetric posteriors |

### Quantity Presentation Depth

**Primary parameters** (full detail -- figure, table, text discussion, model comparison):
- Chirp mass (detector-frame and source-frame)
- Component masses m1, m2
- Combined tidal parameter tilde-Lambda

**Secondary parameters** (value with uncertainty, table, brief interpretation):
- Mass ratio q, effective spin chi_eff, total mass
- Distance, inclination angle

**Tertiary parameters** (constraint or bound only):
- Individual spin magnitudes chi_1, chi_2
- Precession parameter chi_p
- Individual tidal deformabilities Lambda_1, Lambda_2

### Detector-Frame vs Source-Frame Convention

Always clarify which frame:
- **Detector-frame masses**: `m^det = (1+z)m` -- what the GW detector measures
- **Source-frame masses**: `m = m^det/(1+z)` -- astrophysically relevant
- Chirp mass is best measured in detector frame with subpercent precision
- Source-frame uncertainties dominated by redshift uncertainty

---

## Presentation Order and Logical Connections

### Canonical Parameter Presentation Order

Results presented in fixed order building physical understanding:

1. **Localization** -- Where is it? (sky position, distance, inclination)
2. **Masses** -- How massive? (most precisely measured intrinsic parameters)
3. **Spins** -- How fast spinning? (degenerate with mass ratio)
4. **Tides** -- How deformable? (matter effects, EOS probe)
5. **Postmerger** -- What happened after? (different analysis)

### Logical Connections Between Sections

Each section connects to the next:

- **Introduction -> Methods**: "We present improved constraints..." -> "Our analysis
  employs Bayesian parameter estimation with..."
- **Methods -> Results**: "The waveform models are..." -> "Using these models, we find..."
- **Localization -> Masses**: "With the known host galaxy distance..." -> "This
  distance prior breaks the mass-distance degeneracy..."
- **Masses -> Spins**: "The mass ratio is partially degenerate with..." -> "The
  effective spin chi_eff enters at 1.5PN order..."
- **Spins -> Tides**: "With spins constrained, the tidal parameters..." -> "The
  tidal deformability probes the internal structure..."
- **Tides -> Postmerger**: "The tidal measurement constrains the EOS..." -> "The
  postmerger signal would provide additional EOS information..."
- **Results -> Conclusions**: "Our constraints on..." -> "These results are
  consistent with..."

### Cross-Reference Density

GW results papers are heavily cross-referenced:
- Every figure referenced before it appears
- Every table referenced in the text
- Previous work cited frequently for comparison
- Waveform models cross-referenced between methods table and results figures

---

## Figure Taxonomy and Specifications

### Complete Figure List (15+ Required)

#### Fig. 1 -- PSD Plot
- **Content**: Power spectral density for each detector (LIGO Hanford, LIGO
  Livingston, Virgo)
- **Axes**: Frequency (Hz, log scale) vs PSD (strain^2/Hz, log scale)
- **Purpose**: Show detector sensitivity and noise levels
- **Size**: Single column or full width

#### Fig. 2 -- Waveform Model Comparison
- **Content**: Relative amplitude difference (top panel) and absolute phase
  difference (bottom panel) between models vs reference (PhenomPNRT)
- **Axes**: Frequency (Hz, log scale) vs fractional difference (linear)
- **Purpose**: Validate model agreement and identify largest differences
- **Size**: Single column, two stacked panels

#### Fig. 3 -- Sky Localization Map
- **Content**: Skymap with 50% (darker) and 90% (lighter) credible regions,
  EM counterpart location marked
- **Axes**: Right ascension vs declination (or similar sky coordinates)
- **Purpose**: Show improved localization and consistency with EM observations
- **Size**: Single column

#### Fig. 4 -- Distance-Inclination Posterior
- **Content**: 2D posterior for theta_JN vs D_L with 50%/90% contours,
  GW-only (blue) and EM-constrained (purple) priors, plus 1D marginals
- **Axes**: Inclination angle (deg) vs luminosity distance (Mpc)
- **Purpose**: Show distance-inclination degeneracy breaking with EM priors
- **Size**: Single column

#### Fig. 5 -- Component Mass Posteriors
- **Content**: 90% credible regions in m1-m2 plane for four waveform models,
  two panels: high-spin (top) and low-spin (bottom), with 1D marginals
- **Axes**: m2 vs m1 (solar masses)
- **Purpose**: Show mass constraints and model consistency
- **Size**: Single column, two stacked panels

#### Fig. 6 -- Effective Spin PDF
- **Content**: Posterior PDF for chi_eff, four waveform models + prior,
  two panels: high-spin (top, wide x-range) and low-spin (bottom, zoomed)
- **Axes**: chi_eff vs PDF
- **Purpose**: Show spin constraints and prior comparison
- **Size**: Single column, two stacked panels

#### Fig. 7 -- Spin-Mass Ratio Degeneracy
- **Content**: 2D posterior for chi_eff vs q, high-spin (blue) and low-spin
  (orange), with 50%/90% contours and 1D marginals
- **Axes**: q vs chi_eff
- **Purpose**: Illustrate degeneracy between spin and mass ratio
- **Size**: Single column

#### Fig. 8 -- Spin Orientations (High-Spin)
- **Content**: Top panel: polar plots showing probability density for spin
  components chi_1 and chi_2 relative to orbital angular momentum L,
  color-coded by probability per pixel. Bottom panel: posterior for
  precession parameter chi_p with prior overlay
- **Axes**: Polar coordinates (tilt angle vs magnitude), chi_p vs PDF
- **Purpose**: Show spin orientation constraints in high-spin case
- **Size**: Single column, two panels

#### Fig. 9 -- Spin Orientations (Low-Spin)
- **Content**: Same as Fig. 8 but for low-spin prior (chi < 0.05)
- **Purpose**: Show spin orientation constraints in low-spin case
- **Size**: Single column, two panels

#### Fig. 10 -- Tidal Deformability Parameters
- **Content**: 90% credible regions for Lambda_1-Lambda_2, four waveform
  models, with EOS model curves overlaid. Two panels: high-spin (top) and
  low-spin (bottom). Includes arrows indicating "More compact" / "Less compact"
- **Axes**: Lambda_2 vs Lambda_1
- **Purpose**: Show individual tidal deformability constraints with EOS comparison
- **Size**: Single column, two stacked panels

#### Fig. 11 -- Combined Tidal Parameter
- **Content**: PDFs of tilde-Lambda, four waveform models, with prior (dashed),
  two panels: high-spin (top) and low-spin (bottom). Gray PDFs show EOS
  predictions. Vertical lines mark 90% HPD intervals.
- **Axes**: tilde-Lambda vs PDF
- **Purpose**: Show combined tidal parameter constraints and EOS comparison
- **Size**: Single column, two stacked panels

#### Fig. 12 -- Tidal Parameter vs Mass Ratio
- **Content**: 2D posterior for tilde-Lambda vs q, high-spin (blue) and
  low-spin (orange), with 50%/90% contours and 1D marginals
- **Axes**: q vs tilde-Lambda
- **Purpose**: Show correlation between tidal parameter and mass ratio
- **Size**: Single column

#### Fig. 13 -- Postmerger Upper Limits
- **Content**: Top panel: 90% credible upper limits on GW strain in Hanford.
  Bottom panel: radiated energy upper limits. Both show detector noise ASDs,
  prior/posterior upper limits (shaded), and simulation results.
- **Axes**: Frequency (Hz) vs strain ASD (top), vs spectral energy density (bottom)
- **Purpose**: Show postmerger signal upper limits and comparison with simulations
- **Size**: Full column width or single column, two stacked panels

#### Figs. 14-15 -- Injection and Recovery (Appendix B)
- **Content**: Validation plots showing parameter recovery accuracy for
  injected simulated signals
- **Purpose**: Demonstrate pipeline reliability and systematic error assessment

### Figure Design Conventions

- **Color coding**: Consistent across all figures for each waveform model
  - TaylorF2 = red/pink
  - PhenomPNRT = blue
  - PhenomDNRT = teal/cyan
  - SEOBNRT = green
  - Prior = yellow/gray
- **Credible regions**: 50% dashed contours, 90% solid contours
- **1D PDFs**: Renormalized to have equal maxima when comparing multiple models
- **2D posteriors**: Shaded colored contours with boundary lines
- **Prior overlay**: Always shown for comparison (especially spins and tides)
- **EOS overlays**: Theoretical EOS predictions as black curves with labels

---

## Figure Caption Patterns

### Caption Structure

Three-part structure:

1. **Declarative title fragment** (not a full sentence):
   "The 90% credible regions for component masses..."
2. **Description of content**: What is plotted, what models, what statistics
3. **Methodological details**: Normalization, priors, analysis choices, reference
   frequency for spin quantities

### Caption Examples by Figure Type

**PSD plot (Fig. 1)**:
> "PSDs of the Advanced LIGO-Advanced Virgo network. Shown, for each detector,
> is the median PSD computed from a posterior distribution of PSDs as estimated
> by BAYESWAVE [39,47] using 128 s of data containing the signal GW170817."

**Model comparison (Fig. 2)**:
> "Relative amplitude and phase of the employed waveform models starting at
> 23 Hz (see Table I) with respect to PhenomPNRT after alignment within the
> frequency interval [30, 30.25] Hz. Note that, in particular, the alignment
> between SEOBNRT and PhenomPNRT is sensitive to the chosen interval due to
> the difference in the underlying BBH-baseline models at early frequencies.
> We show, as an example, an equal-mass, nonspinning system with a total mass
> of 2.706 M_\odot and a tidal deformability of tilde-Lambda = 400. In the
> bottom panel, we also show the tidal contribution to the phasing for the
> TaylorF2 and the NRTidal models."

**Sky map (Fig. 3)**:
> "The improved localization of GW170817, with the location of the associated
> counterpart SSS17a/AT 2017gfo. The darker and lighter green shaded regions
> correspond to 50% and 90% credible regions, respectively, and the gray
> dashed line encloses the previously derived 90% credible region presented
> in Ref. [3]."

**Credible region 2D (Fig. 5)**:
> "The 90% credible regions for component masses using the four waveform models
> for the high-spin prior (top panel) and low-spin prior (bottom panel). The
> true thickness of the contour, determined by the uncertainty in the chirp
> mass, is too small to show. The points mark the edge of the 90% credible
> regions. The 1D marginal distributions have been renormalized to have equal
> maxima, and the vertical and horizontal lines give the 90% upper and lower
> limits on m1 and m2, respectively."

**Posterior 1D (Fig. 6)**:
> "Posterior PDF for the effective spin parameter chi_eff using the high-spin
> prior (top panel) and low-spin prior (bottom panel). The four waveform
> models used are TaylorF2, PhenomDNRT, PhenomPNRT, and SEOBNRT."

**Spin orientations (Fig. 8)**:
> "Top panel: Inferred spin parameters using the PhenomPNRT model in the
> high-spin case, where the dimensionless component spin magnitudes chi < 0.89.
> Plotted are the probability densities for the dimensionless spin components
> chi_1 and chi_2 relative to the orbital angular momentum L, plotted at the
> reference gravitational-wave frequency of f = 100 Hz. A tilt angle of 0 deg
> indicates alignment with L. Each pixel has equal prior probability.
> Bottom panel: The posterior for the precession parameter chi_p, plotted
> together with its prior distribution, also plotted at the reference frequency
> of f = 100 Hz. The vertical lines represent the 90th percentile for each
> distribution."

**Tidal parameters (Fig. 10)**:
> "PDFs for the tidal deformability parameters Lambda_1 and Lambda_2 using the
> high-spin (top panel) and low-spin (bottom panel) priors. The blue shading
> is the PDF for the precessing waveform PhenomPNRT. The 50% (dashed lines)
> and 90% (solid lines) credible regions are shown for the four waveform
> models. The seven black curves are the tidal parameters for the seven
> representative EOS models using the masses estimated with the PhenomPNRT
> model, ending at the Lambda_1 = Lambda_2 boundary."

**Upper limits (Fig. 13)**:
> "The 90% credible upper limits on GW strain induced in the Hanford detector
> (top panel) and radiated energy (bottom panel). Both results are derived
> from a coherent analysis across the detector network. The noise ASDs for
> each instrument used in this analysis are shown for comparison (top panel).
> Results from selected numerical simulations are also shown."

### Caption Key Elements Checklist

Every caption must include:
- [ ] What quantity is shown (with symbol definition)
- [ ] What statistical regions are shown (50%, 90%)
- [ ] What models/priors are used
- [ ] Any normalization or reweighting conventions
- [ ] Reference frequency (for spin-related quantities)
- [ ] Number of waveform models compared

---

## Table Patterns

### Table I -- Waveform Model Comparison

Columns:
| Model name | Name in LALSuite | BBH baseline | Tidal effects |
| Spin-induced quadrupole | Precession |

Each row describes one model's physical content at a glance. Includes checkmarks
for precession support. Caption explains differences between models.

### Table II -- Source Properties (Main Results)

The primary results table organized as:
- **Rows**: Physical parameters (binary inclination, detector-frame chirp mass,
  chirp mass, primary mass, secondary mass, total mass, mass ratio, effective
  spin, primary spin, secondary spin, tidal deformability)
- **Columns**: Low-spin prior and High-spin prior, with and without EM distance
  constraints for inclination

**Error notation legend** (required in caption):
> "Errors quoted as x^{+z}_{-y} represent the median, 5% lower limit, and 95%
> upper limit. Errors quoted as (x, y) are one-sided 90% lower or upper limits,
> and they are used when one side is bounded by a prior. For the tidal
> parameter tilde-Lambda, we quote results using a constant (flat) prior in
> tilde-Lambda. In the high-spin case, we quote a 90% upper limit for
> tilde-Lambda, while in the low-spin case, we report both the symmetric 90%
> credible interval and the 90% highest posterior density (HPD) interval."

### Table III -- Postmerger Simulation Comparison

Columns: EOS, Simulation reference, peak frequency, SED value, 90% upper limit
Links numerical simulations to postmerger upper limits in Fig. 13.

### Table IV -- Additional Model Results (Appendix A)

Same format as Table II but for TaylorF2, SEOBNRT, and PhenomDNRT models,
enabling direct comparison and systematic error assessment.

### Table V -- RAPIDPE Results (Appendix A)

Same format for SEOBNRv4T and TEOBResumS models analyzed with RAPIDPE,
showing consistency with main LALINFERENCE results.

---

## Model Comparison Conventions

### Why Multiple Models?

GW papers always compare multiple waveform models:
- Different approximants may disagree at levels comparable to statistical errors
- Model differences bound systematic uncertainty from waveform modeling
- Consistency across models increases confidence in results

### Comparison Methodology

1. **Primary (reference) model**: Most complete physical model (PhenomPNRT for
   BNS -- includes tides, spin-induced quadrupole, precession)
2. **Alternative models**: Different physics approximations (TaylorF2, SEOBNRT,
   PhenomDNRT)
3. **Validation models**: More expensive EOB models for cross-check
   (SEOBNRv4T, TEOBResumS via RAPIDPE)
4. **Comparison scope**: Report all parameters for all models in appendix tables
5. **In-text comparison**: Highlight agreement and notable differences

### Reporting Model Differences

When models disagree:
- State the magnitude of the difference
- Identify the physical origin (e.g., "due to the underlying point-particle models")
- Assess whether differences are within statistical uncertainties
- If significant, discuss implications for the most uncertain parameters
