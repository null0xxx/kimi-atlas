---
name: retro-tech-illustration
description: Create retro tech art style visual content including images, illustrations, and design documents. Covers Synthwave, Vaporwave, Cyberpunk, retro comics, and retro-futuristic aesthetics. Use for neon-grid landscapes, pixel art, vaporwave scenes, CRT and halftone effects, color palettes, and typography systems for nostalgic 80s/90s tech-noir projects.
---

# Retro Tech Art Creator

Create retro tech art style visual content and documents. Primary output is images; documents are secondary.

## Reference Source

- **Type**: Uploaded artifacts (DOCX + PDF + XLSX)
- **Reference artifact types**: DOCX, PDF, XLSX
- **Reference File Type**: PDF
- **Style contracts**: Extracted from concrete visual reference (PDF pages)

## Supported Outputs

| Output | Purpose |
|--------|---------|
| **Image (PNG/JPG)** | Primary output - retro art illustrations, concept art, comic panels |
| **PDF** | Styled design guides, reference documents |
| **DOCX** | Editable design guides, style manuals |
| **PPTX** | Presentation decks about retro art styles |

**Default output**: Image when user requests art; PDF when user requests a document/guide.

## Core Workflow

### 1. Determine Output Type

- User requests artwork/illustration/comic -> Generate image(s)
- User requests guide/document/reference -> Create PDF or DOCX
- User requests presentation -> Create PPTX

### 2. Identify Sub-Style

Read `references/style_contract.md` section "Sub-Styles" for detailed guidance. Quick reference:

| Sub-Style | Key Visual | Mood | Use For |
|-----------|-----------|------|---------|
| Synthwave | Neon grid, sunset, sports cars | Nostalgic energy | Music covers, game art |
| Vaporwave | Statues, glitch, consumer culture | Ironic melancholy | Art prints, album art |
| Cyberpunk | Neon rain, skyscrapers, noir | Dystopian | Comic panels, character art |
| Y2K Futurism | Transparent, metallic, organic | Tech optimism | UI mockups, product design |
| Frutiger Aero | Glossy, nature, blue-green | Fresh, friendly | Brand design, icons |
| Atom Punk | Atomic age, space optimism | Optimistic future | Posters, illustrations |
| Retro Comic | Halftone, bold lines, action | Dynamic, expressive | Comic panels, storyboards |

### 3. Apply Visual Style Contract

Read `references/style_contract.md` for full details. Key rules:

- **Dark backgrounds**: Use `#0b0b0f` (deep blue-black) or `#1a0f2e` (dark purple)
- **Neon accents**: Hot pink `#ff2aa3`, electric cyan `#00f5ff`, purple `#7b2cff`
- **Highlights**: Bright yellow `#ffe600`, orange `#ff7a00`
- **Text color**: Off-white `#e7e7ff` on dark backgrounds
- **Typography**: Bold sans-serif for headings; pixel/retro fonts for UI elements; brush/script for decorative accents
- **Textures**: CRT scanlines, VHS glitch, halftone dots, film grain, chrome/metallic
- **Graphic elements**: Laser grids, retro sun, wireframes, pixel art, palm silhouettes

### 4. Generate or Compose

**For images**: Use the image generation tool with detailed prompts incorporating:
- Sub-style identification
- Color palette (from style contract)
- Texture effects (CRT, halftone, grain)
- Specific graphic elements (grids, sun, wireframes)
- Aspect ratio appropriate to content

**For documents**: Follow `references/structure_contract.md` for section hierarchy and layout.

## Color Palette Quick Reference

### Synthwave Sunset
`#ffd319` -> `#ff901f` -> `#ff2975` -> `#f222ff` -> `#8c1eff`

### Neon Arcade
Hot pink `#ff2aa3`, electric cyan `#00f5ff`, purple `#7b2cff`, yellow `#ffe600`

### CRT Glow
Deep blue `#0b0b0f`, neon green `#00ff88`, blue `#00d2ff`

### Cyberpunk Noir
Black `#0a0a0a`, red `#ff003c`, cyan `#00f0ff`, purple `#7b00ff`, yellow `#fffc00`

## Typography Strategy

- **Reference font**: LiberationSerif (from PDF source)
- **CJK support**: Use Noto Sans CJK SC or system CJK fonts for Chinese content
- **Heading style**: Bold, large sans-serif (Commando, Hauser class) or serif with weight
- **Body style**: Clean sans-serif or serif for readability
- **Decorative**: Brush/script fonts (Streamster, Road Rage class) for accents
- **Retro UI**: Pixel fonts (VCR OSD Mono class) for tech/screen elements

For document output, always ensure CJK-capable font selection. Prefer a unified font strategy using Noto Sans CJK SC for all text when Chinese content is present.

## Asset Generation

When generating images, include these visual elements as appropriate:
- **Laser grid**: Glowing neon grid lines extending to vanishing point
- **Retro sun**: Large setting sun with horizontal stripes (yellow to magenta gradient)
- **Wireframe**: Low-polygon 3D rendered style
- **Pixel art**: 8-bit / 16-bit game style pixel patterns
- **Palm silhouettes**: Tropical Miami vibe
- **Chrome text**: High-reflection metallic surface with gradient shine
- **CRT overlay**: Scanlines, RGB phosphor dots, screen curvature, vignette

## Reference Files

| File | When to Read |
|------|-------------|
| `references/style_contract.md` | Full color, typography, texture, and element specifications |
| `references/structure_contract.md` | Document section hierarchy, table formats, heading levels, page layout rules |
| `references/sota_analysis.md` | How contracts were derived from reference artifacts |
