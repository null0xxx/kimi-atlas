# Markdown → Word Citation Reference

Convert Markdown documents with citation markers into Word documents with footnotes, endnotes, or hyperlink cross-references.

## Quick Start

```bash
python3 scripts/md2docx/md2docx_convert.py <markdown_file> \
    --style <footnote|endnote|hyperlink> \
    --output-dir <output-dir>
```

## When to Use

Use this pipeline when you need to convert agent-produced Markdown (with citation markers) into a properly formatted Word document with clickable footnotes or endnotes. This is **not** for general Markdown→Word conversion — use Pandoc directly for that.

## Style Selection

| Style | Use Case | Citation Location |
|-------|----------|-------------------|
| **footnote** | Research reports, policy analysis, general reports | Page bottom (per page) |
| **endnote** | Academic papers, books, long scholarly documents | End of document (consolidated) |
| **hyperlink** | WPS compatibility only | Reference list at end of body |

**Default**: Use **footnote** for most scenarios. Use **endnote** for academic papers.

## Parameters

```
python3 scripts/md2docx/md2docx_convert.py <md_file> [options]

Required:
  md_file              Path to Markdown file

Optional:
  --style STYLE        footnote / endnote / hyperlink (default: footnote)
  --citation PATH      Path to citation.jsonl (environment-specific, specify explicitly)
  --output-dir DIR     Output directory (environment-specific, specify explicitly)
```

## Pre-Invocation Checklist

### 1. citation.jsonl

The citation.jsonl path varies by deployment environment. Always specify explicitly with `--citation <path>`.

**Typical location**: `/mnt/agents/.store/citation.jsonl` (container environments)

Each line is a JSON object:
```json
{"id": 123, "url": "https://example.com", "page": {"site_name": "Example Site"}}
```

### 2. Image Paths

Agent-produced MD may contain absolute paths (e.g., `/some/container/path/xxx.png`) that don't exist in the current environment. Check and fix before conversion:

```bash
grep -oE '!\[.*?\]\(.*?\)' document.md | head -10
# Replace absolute path prefix with relative — adjust prefix based on your environment
sed -i '' 's|/path/to/remove/||g' document.md
```

### 3. Citation Format

Three formats auto-detected (priority descending):

| Tier | Pattern | Confidence | Behavior |
|------|---------|------------|----------|
| T1 | `[^123^]` | High | Direct conversion |
| T2 | `[^123]` | Medium | Compat conversion |
| T3 | `[123]` | Low | DB cross-validation required (>50% hit rate, >5 matches) |

## Pipeline

```
Markdown + citation.jsonl
    │
    ├─ 1. Citation format detection (T1→T2→T3 tiered fallback)
    ├─ 2. Renumber by first-appearance order → ^N^ superscripts
    ├─ 3. Edge case detection (non-numeric citations → WARNING only)
    │
    ├─ 4. Pandoc → base.docx
    │
    └─ 5. OOXML post-processing (branched by style)
         ├─ footnote: first → footnote object, subsequent → NOTEREF
         ├─ endnote:  first → endnote object, subsequent → NOTEREF
         └─ hyperlink: REF field → bibliography bookmark
```

## Output Files

- `{name}.{style}.docx` — Final Word document
- `{name}.converted.md` — Intermediate Markdown (citations → `^N^` superscripts)
- `{name}.base.docx` — Pandoc raw output (intermediate)

## Technical Details

- **Dedup**: Same citation ID appearing multiple times → one note, subsequent uses NOTEREF
- **Clickable**: Superscript numbers link to corresponding footnote/endnote
- **Edge cases**: Non-numeric IDs (`[^Insight6^]`) → WARNING only, no modification
- **Missing**: Citation IDs not in DB → removed from body, logged

## Dependencies

- **Pandoc**: `apt install pandoc`
- **python-docx**: `pip install python-docx`
- **lxml**: `pip install lxml`

## Code Structure

```
scripts/md2docx/
├── md2docx_convert.py   # Main pipeline
├── citation_parser.py   # Citation detection (T1/T2/T3), renumbering, replacement
├── docx_footnote.py     # Footnote OOXML post-processing
├── docx_endnote.py      # Endnote OOXML post-processing
├── docx_postprocess.py  # Hyperlink post-processing (python-docx)
└── docx_utils.py        # Shared: rels/content_types updates
```

---

## Reference Entry Points

- For overall routing: `../SKILL.md`
- For creating new documents: `openxml-sdk-reference.md`
- For editing existing documents: `wir-reference.md`
- For matplotlib charts: `matplotlib-guide.md`
