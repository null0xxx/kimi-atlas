# Figures, Tables & Equations Guidelines

Extracted from the ResNet paper and generalized for top-tier scientific publications.

## Table of Contents

1. [General Principles](#general-principles)
2. [Figures](#figures)
3. [Tables](#tables)
4. [Equations](#equations)
5. [Visual Asset Workflow](#visual-asset-workflow)
6. [Common Anti-Patterns](#common-anti-patterns)

---

## General Principles

1. **Every visual element must be referenced in the text BEFORE it appears**
2. **Captions must be self-contained** - understandable without reading the main text
3. **Use bold for best results** in comparison tables
4. **Keep figure fonts at >=8pt** for readability at conference poster size
5. **Prefer vector formats** (PDF, EPS, SVG) over raster (PNG, JPG)

**CRITICAL**: When reproducing a paper, create ALL figures and tables referenced
in the text. Do NOT skip any. The ResNet paper has 7 figures and 14 tables.

---

## Figures

### Figure Numbering and Caption Placement

| Element | Convention |
|---------|------------|
| Numbering | "Figure 1.", "Figure 2.", "Fig. 1" (after first mention) |
| Caption position | **BELOW** the figure |
| Caption format | Bold "Figure N.", followed by descriptive text |
| In-text reference | "Fig. 1", "Fig. 2 (left)", "Figs. 3 and 4" |
| First reference | Spell out "Figure 1"; abbreviate to "Fig." thereafter |

### Caption Writing Rules

**Structure**: `Figure N. [Dataset/Task]. [What is shown]. [Key takeaway].`

Example (from ResNet):
```
Figure 1. Training error (left) and test error (right) on CIFAR-10 with
20-layer and 56-layer "plain" networks. The deeper network has higher
training error, and thus test error. Similar phenomena on ImageNet is
presented in Fig. 4.
```

**Caption checklist**:
- [ ] States the dataset or experimental setting
- [ ] Describes what each subplot shows (Left/Middle/Right/Top/Bottom)
- [ ] States the key observation or conclusion
- [ ] References related figures when relevant
- [ ] Avoids repeating detailed numbers (save for text or tables)

### Figure Layout Specifications

| Parameter | Value |
|-----------|-------|
| Figure width (single column) | 3.25" (full column) |
| Figure width (double column) | 6.75" (spanning both columns) |
| Figure height | Proportional to width (typically 1.5-3") |
| Font size (labels) | 8-10pt |
| Font size (tick labels) | 8pt |
| Line width (curves) | 1.5-2pt |
| Line width (axes) | 0.5-1pt |
| Marker size | 4-6pt |
| Legend font size | 8pt |

### Figure Types and Styling

#### Type 1: Training Curves (Line Plots)

**Purpose**: Show convergence behavior over time/iterations

**Style rules**:
- X-axis: iterations, epochs, or steps
- Y-axis: loss, error rate, or accuracy
- Multiple curves distinguished by:
  - **Color**: Different methods (use colorblind-safe palette)
  - **Line style**: Solid (validation/test), dashed (training)
  - **Line thickness**: Bold for key result, thin for baselines
- Add horizontal reference lines for key thresholds
- Legend in corner or outside plot area

**Example** (ResNet Fig. 4):
```
Left: plain networks of 18 and 34 layers.
Right: ResNets of 18 and 34 layers.
Thin curves = training error; bold curves = validation error.
```

#### Type 2: Architecture Diagrams

**Purpose**: Illustrate network structure or method pipeline

**Style rules**:
- Use rectangular blocks for layers/modules
- Use arrows for data flow (left-to-right, top-to-bottom)
- Label each block with layer type and dimensions
- Use color sparingly: grayscale with 1 accent color
- Show input/output dimensions at each stage
- Group related blocks with brackets or boxes

**Example** (ResNet Fig. 3):
```
Three columns: VGG-19 | 34-layer plain | 34-layer residual
Each shows: input -> [conv blocks] -> [pool] -> ... -> output
Dotted shortcuts indicate dimension-matching operations
```

#### Type 3: Conceptual Diagrams

**Purpose**: Explain the core idea (e.g., residual block)

**Style rules**:
- Minimal, clean blocks and arrows
- Label inputs and outputs clearly
- Show mathematical operations (+, x, etc.)
- Use consistent block sizes and spacing
- Place equation reference near the diagram

**Example** (ResNet Fig. 2):
```
    x --> [weight layer] --> [relu] --> [weight layer] --> (circle plus) --> [relu] --> output
         |                                                   ^
         +----------------- [identity] ----------------------+

    F(x) + x
```

#### Type 4: Bar Charts / Comparison Plots

**Purpose**: Compare numerical results across methods

**Style rules**:
- Group bars by dataset or metric
- Use consistent color for each method across groups
- Add value labels on top of bars when space permits
- Sort bars by performance (best on left or right)
- Include error bars when showing variance

#### Type 5: Visualization / Qualitative Results

**Purpose**: Show model outputs, attention maps, feature visualizations

**Style rules**:
- Grid layout for multiple examples
- Label rows/columns (input, output, ground truth, baseline)
- Use high-resolution images (>=150 DPI)
- Add borders between examples for clarity
- Include zoom-in insets for detail regions

---

## Tables

### Table Numbering and Caption Placement

| Element | Convention |
|---------|------------|
| Numbering | "Table 1.", "Table 2." |
| Caption position | **ABOVE** the table |
| Caption format | Bold "Table N.", followed by descriptive text |
| In-text reference | "Table 1", "Tables 2 and 3" |

### Table Caption Writing Rules

**Structure**: `Table N. [Metric] on [Dataset]. [Additional context].`

Example (from ResNet):
```
Table 2. Top-1 error (%, 10-crop testing) on ImageNet validation.
Here the ResNets have no extra parameter compared to their plain counterparts.
Fig. 4 shows the training procedures.
```

**Caption checklist**:
- [ ] Metric name and unit (e.g., "error (%)", "mAP (%)")
- [ ] Dataset name
- [ ] Evaluation protocol (e.g., "10-crop testing", "single-model")
- [ ] Any important caveats or conditions
- [ ] Cross-reference to related figures

### Table Format Specifications

| Parameter | Value |
|-----------|-------|
| Width | Single column (3.25") or double column (6.75") |
| Font size | 8-9pt (smaller than body text) |
| Line spacing | 1.0x (compact) |
| Horizontal rules | Top, bottom, and header separator only |
| Vertical rules | Avoid (use spacing instead) |
| Header row | Bold, sometimes with light background shade |
| Alignment | Left (text), right (numbers), decimal-aligned |

### Table Structure Best Practices

**Comparison Table** (most common):
```
+-------------+---------+---------+---------+
| Method      | Metric1 | Metric2 | Metric3 |
+-------------+---------+---------+---------+
| Baseline A  | 28.54   | 10.02   | 5.71    |
| Baseline B  | 25.03   |  7.76   | 4.49    |
| Ours        | 21.43   |  5.71   | 3.57    |  <- best results in bold
+-------------+---------+---------+---------+
```

**Architecture Table**:
```
+----------+------------+-----------------------------+
| Layer    | Output     | Configuration               |
+----------+------------+-----------------------------+
| conv1    | 112x112    | 7x7, 64, stride 2           |
| pool     | 56x56      | 3x3 max pool, stride 2      |
| conv2_x  | 56x56      | [3x3, 64] x 3               |
| ...      | ...        | ...                         |
+----------+------------+-----------------------------+
```

**Multi-section Table** (for complex comparisons):
```
+----------+---------+---------+---------+---------+---------+
| layer    | output  | 18-lay  | 34-lay  | 50-lay  | 101-lay |
|   name   |  size   |         |         |         |         |
+----------+---------+---------+---------+---------+---------+
| conv1    | 112x112 | 7x7,64  | 7x7,64  | 7x7,64  | 7x7,64  |
| conv2_x  | 56x56   | [...]x2 | [...]x3 | [...]x3 | [...]x3 |
+----------+---------+---------+---------+---------+---------+
```

### Table Content Rules

1. **Best results in bold**: The highest-performing method for each metric
2. **Second-best in italics** (optional): For additional context
3. **Method naming**: Use paper name + year, or model name (ResNet-50, VGG-16)
4. **Footnotes in tables**: Use superscript letters (a, b, c) for table-specific notes
5. **Significance markers**: + for test set, * for p<0.05 (if applicable)

---

## Equations

### Equation Environment Rules

| Parameter | Convention |
|-----------|------------|
| Numbering | Arabic numerals, right-aligned in parentheses: `(1)` |
| Alignment | Centered on page/column |
| Spacing | 6pt above and below |
| Punctuation | End with period if part of a sentence; comma if followed by text |
| Multi-line | Align at relation symbols |

### Equation Punctuation

Equations are part of sentences and must be punctuated:

```
The residual mapping is defined as:

    y = F(x, {W_i}) + x.                                          (1)

Here x and y are the input and output vectors...
```

### Common Equation Patterns

**Definition/Introduction**:
```
We define the residual function as:
    F(x) := H(x) - x.                                             (5)
```

**Optimization Objective**:
```
The training objective is to minimize the loss:
    L(theta) = sum L_i(f(x_i; theta), y_i) + lambda*R(theta).    (6)
```

**Update Rule**:
```
The parameters are updated via gradient descent:
    theta_{t+1} = theta_t - eta * grad_theta L(theta_t).          (7)
```

---

## Visual Asset Workflow

When the user requests figure or table creation:

1. **Determine the figure/table type** based on the data being presented
2. **Select dimensions** based on column layout (single or double)
3. **Apply the color palette** from the style contract
4. **Write the caption first** - this clarifies what the visual must show
5. **Design for the caption** - ensure all elements mentioned in the caption are visible
6. **Add cross-references** in the surrounding text

---

## Common Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|-----------------|
| Figure caption above figure | Caption **BELOW** figure |
| Table caption below table | Caption **ABOVE** table |
| "The figure below shows..." | "Fig. 3 shows..." (reference before appearance) |
| Unexplained acronyms in captions | Spell out or define in caption |
| 3D bar charts | Use 2D bars or dot plots |
| Rainbow color maps | Use perceptually uniform colormaps (viridis, plasma) |
| Tiny fonts (<6pt) | Minimum 8pt for all labels |
| Raster images for line art | Use vector formats (PDF, EPS, SVG) |
| Missing units in axis labels | Always include units: "Error (%)", "Time (s)" |
| Overcrowded figures | Split into subfigures (a), (b), (c) |
