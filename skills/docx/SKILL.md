---
name: docx
description: "Create and edit Word documents (.docx) — C# + OpenXML SDK for creation, WIR engine for editing/comments/tracked changes. Use for any .docx task including document creation, editing, comments, revisions, footnotes, TOC, and Markdown-to-Word conversion."
---

# Part 1: Routing

`read file` / `cat` only extracts plain text from `.docx` — all formatting is lost. If the task involves appearance or structure, use WIR engine's `session.read()` instead.

## Route = What You Have

**1. WIR** (`references/wir-reference.md`) — A .docx exists whose **format/style matters** to the output.

The user provides a template, a document to edit/modify/review/annotate, or any file whose formatting should be preserved or referenced. This file is your output foundation — read it, modify it, fill it.

If the .docx is merely a content/data source (e.g., reference papers, raw data exports) and its formatting is irrelevant, just `read file` to extract text — that is NOT a WIR case.

`.doc` format → convert first: `libreoffice --headless --convert-to docx`

**2. md2docx** (`references/md2docx-reference.md`) — When you are the Orchestrator (you have `create_subagent` and dispatch `task`) and your sub-agents have returned `.md` files. Convert their output to a formatted Word document using the md2docx pipeline.

If you do NOT have `create_subagent` / `task` tools, you are not an Orchestrator and md2docx does not apply. Do not write markdown yourself and convert with pandoc — the result is mediocre. Use Create (C#) for high-quality output.

**3. Create** (`references/openxml-sdk-reference.md`) — Neither of the above.

No target .docx, no upstream .md. Build the document from scratch using C# + OpenXML SDK via `./scripts/docx build`.

---

# Part 2: Execution

## File Structure

```
docx/
├── SKILL.md                       ← This file (routing + rules)
├── references/
│   ├── openxml-sdk-reference.md   → Creation: patterns, traps, all you need
│   ├── wir-reference.md           → WIR editing interface + patterns
│   ├── md2docx-reference.md       → Citation pipeline → Word conversion
│   ├── chart-reference.md         → Native Word charts (pie, bar, line)
│   ├── omml-reference.md          → OMML math equation patterns
│   └── matplotlib-guide.md        → Charts Word can't do natively
├── scripts/
│   ├── docx                       → Unified entry point (the only script to call)
│   ├── engine/                    → WIR engine (editing core)
│   ├── md2docx/                   → Citation → Word pipeline
│   ├── generate_backgrounds.py    → Style reference: Morandi curves (read for technique, don't call directly)
│   ├── generate_inkwash_backgrounds.py  → Style reference: ink wash
│   ├── generate_swiss_backgrounds.py    → Style reference: Swiss grid
│   ├── generate_geometric_backgrounds.py → Style reference: geometric blocks
│   ├── generate_gradient_backgrounds.py  → Style reference: gradient ribbons
│   └── generate_formal_backgrounds.py    → Style reference: formal double border
└── assets/templates/
    ├── Example.cs                 → English document demo (conditional required)
    └── CJKExample.cs              → Chinese/CJK document demo (conditional required)
```

## Validation

- **Creation**: `./scripts/docx build` runs the full pipeline (compile → generate → auto-fix element order → OpenXML validate → business rules)
- **Editing**: The engine validates internally; after saving, spot-check high-risk areas

## Hard Rules

1. **No manual markdown-to-docx.** Do not write markdown then convert with pandoc. If you are the Orchestrator with upstream .md from sub-agents, use md2docx. Otherwise, always Create (C#).
2. **Target .docx exists (template, document to edit, format reference) → always WIR**, never rewrite from scratch.
3. Clean up iteration artifacts — no `v1`/`v2`/`final` clutter in the output directory. Deliver clean, clearly named files only.
4. Name output files by topic and match the user's language (e.g., Chinese query → `储能电站分析报告.docx`, English query → `Energy_Storage_Report.docx`). Never `output.docx`.
5. Language consistency — user's conversation language across all elements (body, headings, headers/footers, TOC, chart labels, filenames).
6. Default to the skill's own toolchain; avoid external libraries unless necessary.
7. After choosing a route, read the corresponding reference file **in full** before writing any code. Do not skim or skip sections — traps and required patterns appear throughout.

## Quality Standards

**Low-saturation color palette.** Pick ONE hue direction, build 3 tiers: Primary (headings) / Dark (body text) / Light (captions). Never pure #FF0000/#0000FF. Cover text color must contrast with its background AND be visually distinct from body text (larger size, different weight, generous spacing).

**Cover/backcover backgrounds.** If the document needs a cover, generate a unique background from scratch — read one of the `generate_*.py` scripts to learn the Playwright + SVG technique, then write your own HTML/SVG with original shapes and colors matching the document's palette. Never reuse or directly call existing background scripts. Cover text must feel like a separate visual space from the body, not just a bigger first paragraph.

**Content constraints.** Word count target "X字左右" means ±20% is acceptable.

**Delivery checklist** (verify before delivering):
1. Document opens without errors
2. OpenXML + business rule validation passes
3. Headers, footers, page numbers present and correctly positioned
4. No placeholder text remains (`[Company Name]`, `TODO`, etc.)
5. All images render (build output shows `X images` — if 0, images were not inserted)
6. Cover/backcover text visibly contrasts with background
