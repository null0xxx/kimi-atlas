# Structure & Narrative Contract

Extracted from the ResNet (He et al., CVPR 2016 Best Paper) and generalized for
top-tier scientific venues.

## Table of Contents

1. [Complete Section Hierarchy](#complete-section-hierarchy)
2. [Section Budget Rules](#section-budget-rules)
3. [Narrative Logic - The "Funnel"](#narrative-logic)
4. [Paragraph-Level Patterns](#paragraph-level-patterns)
5. [Cross-Reference Conventions](#cross-reference-conventions)
6. [Content Completeness Checklist](#content-completeness-checklist)

---

## Complete Section Hierarchy

A standard conference paper follows this hierarchy. ALL sections must be present
in the final output:

```
Title (centered, 17pt bold)
├── Authors & Affiliations (centered)
├── Abstract (single-column, 1 paragraph, ~150 words)
├── 1. Introduction (1-1.5 pages, 5-7 paragraphs)
│   ├── P1: Domain context
│   ├── P2: Sub-domain & trend
│   ├── P3: The problem / gap
│   ├── P4: Empirical evidence of the gap
│   ├── P5: Proposed solution (high-level)
│   ├── P6: Contribution list (3-5 items)
│   └── P7: Paper roadmap (optional)
├── 2. Related Work (0.5-1 page)
│   └── Thematic subsections (e.g., "Residual Representations", "Shortcut Connections")
├── 3. Method / Approach (2-3 pages)     ← MUST HAVE ALL SUBSECTIONS
│   ├── 3.1. Core Formulation
│   ├── 3.2. Key Mechanism
│   ├── 3.3. Architecture / Design
│   └── 3.4. Implementation Details
├── 4. Experiments / Results (2.5-3.5 pages)  ← MUST HAVE ALL SUBSECTIONS
│   ├── 4.1. Main Benchmark
│   ├── 4.2. Secondary Benchmark & Analysis
│   └── 4.3. Extension / Application
├── 5. Conclusion (0.3-0.5 pages)
│   ├── Summary
│   ├── Limitations (required at many venues since 2022)
│   └── Future Work (optional)
├── References (1 page, numbered [1]-[N])
└── Supplementary / Appendix (optional, separate or at end)
    ├── A. Additional Experimental Details
    ├── B. Additional Results
    └── C. Derivation / Proof / Other
```

**CRITICAL**: When reproducing or drafting a paper, create ALL sections above.
Do NOT skip any subsection of Method (3.1-3.4) or Experiments (4.1-4.3).

### Section Budget Rules

| Section | Pages | % of Body | Purpose |
|---------|-------|-----------|---------|
| Introduction | 1-1.5 | 15-20% | Motivation + problem statement + contributions |
| Related Work | 0.5-1 | 8-12% | Positioning + differentiation |
| Method | 2-3 | 30-40% | Formulation + design + implementation |
| Experiments | 2.5-3.5 | 35-45% | Validation + analysis + ablation |
| Conclusion | 0.3-0.5 | 4-6% | Summary + limitations + future work |
| References | ~1 | - | Complete numbered bibliography |

---

## Narrative Logic

Each major section follows a **funnel structure**: broad -> narrow -> contribution.

### 1. Introduction Narrative Arc

The Introduction must execute this progression in exactly 5-7 paragraphs:

**Paragraph 1 - Domain Context**
- State the broad field (e.g., "Deep convolutional neural networks have led to
  breakthroughs for image classification")
- Cite 2-4 seminal works establishing the domain
- End with why the domain matters

**Paragraph 2 - Sub-Domain & Trend**
- Zoom into the specific trend or direction (e.g., "network depth is of crucial
  importance")
- Cite recent works (last 2-3 years) showing the trend
- Use quantitative evidence when possible (e.g., "depths of sixteen to thirty")

**Paragraph 3 - The Problem / Gap**
- Identify the obstacle or open question (e.g., "Is learning better networks as
  easy as stacking more layers?")
- Reference prior attempts to address it and why they are insufficient
- Use a rhetorical question or a surprising finding to create tension

**Paragraph 4 - Empirical Evidence of the Gap**
- Present a concrete observation (e.g., degradation problem with training curves)
- Reference your own preliminary result or a figure preview
- Show that the problem is real and non-trivial

**Paragraph 5 - Proposed Solution (High-Level)**
- State your core idea in 1-2 sentences (e.g., "we address the degradation problem
  by introducing a deep residual learning framework")
- Explain the intuition (e.g., "instead of hoping each few stacked layers directly
  fit a desired underlying mapping, we explicitly let these layers fit a residual
  mapping")
- Reference the key figure that illustrates the idea

**Paragraph 6 - Contribution List**
- Enumerate 3-5 specific contributions:
  1. A new formulation / framework / architecture
  2. Comprehensive empirical validation on benchmark X
  3. State-of-the-art results on task Y
  4. Analysis revealing insight Z
  5. Generalization to related tasks (detection, segmentation, etc.)

**Paragraph 7 - Paper Roadmap (optional)**
- Briefly state what each subsequent section covers (1 sentence each)

### 2. Related Work Narrative Arc

Organize by **theme**, not by chronology or by individual paper:

```
2. Related Work
    ├── Theme A (e.g., Residual Representations)
    │   └── 3-4 cited works + how your work differs
    ├── Theme B (e.g., Shortcut Connections)
    │   └── 3-4 cited works + how your work differs
    └── Theme C (optional)
        └── 3-4 cited works + how your work differs
```

**Key rules**:
- Start each theme with a bold paragraph heading (not a numbered subsection)
- First sentence defines the theme and cites the most representative work
- Subsequent sentences discuss related methods and their limitations
- Final sentence of each theme explicitly states the difference from your approach

### 3. Method Narrative Arc (ALL 4 subsections required)

**3.1 Core Formulation**
- Define the problem formally (e.g., "Let us consider H(x) as an underlying mapping")
- Introduce notation; define ALL symbols in surrounding text
- State the key equation (centered, numbered)
- Explain the reformulation / insight (e.g., F(x) := H(x) - x)
- Provide theoretical motivation or intuition

**3.2 Key Mechanism**
- Explain the building block with a figure reference (e.g., Fig. 2)
- Describe how the mechanism operates step-by-step
- Discuss variants or design choices (e.g., identity vs. projection shortcuts)
- Use inline math for simple expressions, numbered equations for key formulations

**3.3 Architecture / Design**
- Present the full architecture with a figure (e.g., Fig. 3)
- Describe design rules or principles (enumerated)
- Compare with baseline architectures (VGG, etc.)
- Discuss computational complexity (FLOPs, parameters)

**3.4 Implementation Details**
- Data preprocessing and augmentation
- Optimization hyperparameters (learning rate, batch size, weight decay)
- Hardware and training time
- Evaluation protocol

### 4. Experiments Narrative Arc (ALL 3 subsections required)

**4.1 Main Benchmark**
- Dataset description (size, classes, train/val/test split)
- Evaluation metrics (define each metric)
- Baseline methods (cite and explain why they are relevant)
- Main results table (Table 2 or 3)
- Result interpretation: what the numbers mean, why they matter

**4.2 Secondary Benchmark & Analysis**
- Additional dataset or task
- Ablation studies: systematically remove components to show their contribution
- Analysis figures (e.g., training curves, response distributions)
- Key observations stated as bold claims supported by data

**4.3 Extension / Application**
- Transfer to related tasks (detection, segmentation, etc.)
- Comparison with task-specific state-of-the-art
- Demonstrate generalization

### 5. Conclusion Narrative Arc

**Paragraph 1 - Summary**
- Restate the problem and solution in past tense
- Highlight the most significant empirical result

**Paragraph 2 - Limitations (required at many venues since 2022)**
- Acknowledge 1-2 genuine limitations
- Frame positively where possible (e.g., "This suggests that combining with
  stronger regularization may improve results, which we will study in the future")

**Paragraph 3 - Future Work (optional)**
- 1-2 concrete directions for follow-up research

---

## Paragraph-Level Patterns

### Claim-Evidence-Interpretation Pattern

Every experimental claim should follow this structure:

1. **Claim**: State what you found (e.g., "The 34-layer ResNet is better than the
   18-layer ResNet by 2.8%")
2. **Evidence**: Cite the table/figure (e.g., "Table 2 and Fig. 4")
3. **Interpretation**: Explain what it means (e.g., "This indicates that the
   degradation problem is well addressed in this setting")

### Forward Reference Pattern

Always reference figures and tables **before** they appear on the page:

- Correct: "Fig. 1 shows a typical example" -> [Figure appears later]
- Correct: "The results are presented in Table 2" -> [Table appears later]
- Incorrect: [Figure appears] -> "As shown in the figure above"

### Citation Density Rules

| Location | Density | Purpose |
|----------|---------|---------|
| Introduction paragraph 1 | 2-4 per sentence | Establish domain |
| Introduction paragraph 2 | 2-3 per sentence | Show trend |
| Method | 0-1 per paragraph | Own work, minimal citations |
| Experiments (baselines) | 1 per baseline method | Attribute prior work |
| Related Work | 1-2 per sentence | Comprehensive coverage |

---

## Cross-Reference Conventions

| Element | Format | Example |
|---------|--------|---------|
| Figures | "Fig. N" | "Fig. 1", "Fig. 2 (left)", "Figs. 3 and 4" |
| Tables | "Table N" | "Table 1", "Tables 2 and 3" |
| Sections | "Sec. N" | "Sec. 3.1", "Sec. 4" |
| Equations | "Eqn. (N)" | "Eqn. (1)", "Eqns. (2) and (3)" |
| Appendix | "See appendix" | "See Sec. A of the appendix" |

---

## Content Completeness Checklist

When producing a paper, verify ALL of the following are present:

### Sections
- [ ] Title, Authors, Affiliations
- [ ] Abstract (single paragraph, ~150 words)
- [ ] 1. Introduction (5-7 paragraphs)
- [ ] 2. Related Work (thematic subsections)
- [ ] 3. Method (ALL subsections: 3.1, 3.2, 3.3, 3.4)
- [ ] 4. Experiments (ALL subsections: 4.1, 4.2, 4.3)
- [ ] 5. Conclusion (summary + limitations)
- [ ] References (numbered [1]-[N])
- [ ] Appendix A/B/C (if applicable)

### Visual Elements
- [ ] ALL figures referenced in text before appearing
- [ ] Figure captions BELOW each figure
- [ ] ALL tables referenced in text before appearing
- [ ] Table captions ABOVE each table
- [ ] ALL equations numbered sequentially
- [ ] Best results in tables in **bold**

### Page Count
- [ ] Total page count matches target (8-12 pages for full paper)
- [ ] No section is unreasonably short or skipped
- [ ] Figures and tables distributed across pages, not crammed
