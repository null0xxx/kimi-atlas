# WIR Editing Reference

This document covers only **editing existing `.docx` files**. The public WIR workflow consists solely of:

1. `open`
2. `read`
3. `edit`
4. `save`

Do not discuss creating new documents here, do not introduce `python-docx`, and do not frame WIR as a tool-use mental model.

## Engine Interface

### Import Setup

The engine is at `docx/scripts/engine/`. Before importing, add `docx/scripts/` to Python path:

```python
import sys
sys.path.insert(0, '<path-to>/docx/scripts')  # same directory as ./scripts/docx
from engine import WIRSession
```

### Primary Interface — WIRSession (Recommended)

```python
from engine import WIRSession
from engine import TextEdit

session = WIRSession.open("/path/to/doc.docx")   # Open
w1, wir, next_cursor = session.read(part="document")  # Read
updated = session.edit(w1, [TextEdit(...)])        # Edit
session.save("/path/to/output.docx")               # Save
```

Context manager:
```python
with WIRSession.open("/path/to/doc.docx") as session:
    w1, wir, _ = session.read()
    session.edit(w1, [TextEdit(old_string="<r>original text</r>", new_string="<r>new text</r>")])
    session.save("/path/to/output.docx")
```

### Low-Level Functions

```python
from engine import (
    open_docx, read_wir, modify_wir, save_docx,
    TextEdit, validate_docx,
    CommentsManager, StyleManager, NumberingManager,
)
```

| Function | Purpose |
|------|------|
| `open_docx(path)` | Open an existing document, returns `DocxPackage` |
| `read_wir(package, part=..., cursor=..., limit=...)` | Read a WIR window |
| `modify_wir(package, base_wir=..., edits=[TextEdit(...)])` | Apply edits |
| `save_docx(package, output_path)` | Save the document |
| `validate_docx(package)` | Validate document structure |

**Namespace Issue Handling**:

Some source documents may have incomplete namespace declarations (e.g., using the `w14` prefix without declaring it in `mc:Ignorable`). If you encounter an `E_NAMESPACE_IGNORABLE_MISSING_USED_PREFIX` error on save, you can disable the namespace check:

```python
# Using WIRSession
session.package.save(output_path, namespace_guard_enabled=False)

# Using low-level functions
save_docx(package, output_path, namespace_guard_enabled=False)
```

**When to Disable**:
- The source document itself has namespace issues
- You are only editing content and not adding new namespaces
- Word can open the source document normally (indicating the issue is minor)

**When NOT to Disable**:
- You are adding new extension features (e.g., Word 2013+ features)
- You need to ensure the document opens correctly in all Word versions

---

## 1. WIR Overview

### Core Purpose

WIR (Word Intermediate Representation) is a simplified representation of OOXML, capable of efficiently handling the vast majority of editing, commenting, and revision tracking tasks. Through `WIRSession`, it preserves template fidelity and complex OOXML structures.

### Hard Rules

1. Do not bypass WIR for manual zip/xml editing on existing business documents
2. Do not perform ad-hoc XML surgery on `word/*.xml`
3. Use absolute paths
4. Preserve user intent and document structure
5. Use incremental window editing for large documents
6. Save after editing
7. On warnings or errors, stop, re-read, then continue

### Production Workflow

#### Phase 1: Open and Baseline Scan
```python
session = WIRSession.open(path)
w1, wir, next_cursor = session.read(part="document")
# Read additional parts as needed: comments, footnotes, endnotes, header:rIdX, footer:rIdX, prototypes, styles
```

#### Phase 2: Plan Edits by Window
- Batch A: Metadata / titles / headers & footers
- Batch B: Body paragraph rewrites
- Batch C: Tables
- Batch D: Footnotes / comments / TOC / hyperlinks

Per batch: select a cursor window -> prepare exact `old_string` -> apply 1-3 edits -> verify results

#### Phase 3: Execute WIR Edits Safely
```python
# Each edit call
updated = session.edit(w1, [TextEdit(old_string="...", new_string="...")])
# Re-read after structural operations
w1_new, wir_new, _ = session.read(part="document")
```

#### Phase 4: Validate Content Quality
- All requested changes have been applied
- Style continuity
- Numbering integrity
- No accidental deletions

#### Phase 5: Save and Run Quality Gates
```python
session.save(output_path)
```

### WIR Editing Guidelines

Follow these for each edit:
1. Default to reading `document` first; start with `<classes>` at the top of the window
2. Read `prototypes` when template fidelity is needed
3. Read `styles` only when class semantics are insufficient
4. Wrap text within paragraphs in `<r>...</r>`
5. Keep edits localized
6. Use stable anchors
7. One logical change per batch

### WIR Capability List
- Rich text paragraph/run formatting (`attr`)
- Table structure editing and merging
- TOC insertion/update
- Hyperlink insertion (external/internal)
- Footnote/endnote insertion
- Header/footer story editing
- Comment editing and anchor control
- LaTeX formula to OMML conversion
- Image insertion and geometry updates

---

## 2. Opening a Document

### Open an Existing Document

```python
session = WIRSession.open("/absolute/path/to/doc.docx")
# Or low-level:
package = open_docx("/absolute/path/to/doc.docx")
```

### Key Rules
- Use absolute paths
- After opening (or re-opening), call `read` first to obtain an active cursor
- Cursors are session-scoped; do not reuse cursors from previous sessions
- Default to reading `document` first
- `prototypes` is for high-fidelity reuse
- `styles` is an advanced/debug view only, for when class semantics are insufficient or legacy key tracing is needed

*Formulas* — Write in LaTeX: `$x^2$` (inline) or `$$E=mc^2$$` (display). The engine automatically converts to Word-native OMML.

---

## 3. Reading WIR Windows

### Usage

```python
w1, wir, next_cursor = session.read(part="document")
# Pagination:
if next_cursor:
    w2, wir2, next2 = session.read(part="document", cursor=next_cursor)
```

Low-level:
```python
content, next_cursor = read_wir(package, part="document", cursor=None, limit=50)
```

### Available Parts

| part | Description |
|------|------|
| `document` | Document body (supports windowed pagination) |
| `styles` | Styles, lists, and legacy key debug view |
| `prototypes` | Reusable proto fragments (read-only) |
| `comments` | Comments |
| `footnotes` | Footnotes |
| `endnotes` | Endnotes |
| `header:rIdX` | Header |
| `footer:rIdX` | Footer |

### Workflow
1. Open the document
2. Read the target window/part
3. Edit that window using the cursor
4. Save

### Tips
- Short cursor IDs are stable within the same open session
- Use new cursors after re-opening
- Use `next_cursor` for pagination
- Each WIR fragment is paired with its own cursor
- After edits that insert/delete/move top-level blocks, re-read affected windows
- An empty document under the class-first view typically looks like:
  ```xml
  <classes>
    <class hint="Normal" name="normal" on="p"></class>
  </classes>
  <p k="P1" class="normal"></p>
  ```
  So do not assume the anchor is always a bare `<p k="P1"></p>` on the first edit

### WIR Format Notes
- Root format: `<wfrag v="3" part="..." cursor="...">`
- WIR is normalized: no self-closing tags, stable attribute order, 2-space indentation
- Under the class-first view, `<classes>` appears at the top of story windows
- `document` top-level blocks: `<p>`, `<table>`, `<section>`, `<toc>`, `<keep>`
- `footnotes`/`endnotes` top-level blocks: `<note id="...">`
- `styles` is primarily for debugging and compatibility mapping, not the default first view
- `prototypes` returns `<proto id="...">` fragments

### `<classes>` Metadata

`<classes>` is the core of the class-first view. It describes the most reusable semantic classes in the current window.

Common form:

```xml
<classes>
  <class name="normal" on="p" hint="Normal"></class>
  <class name="heading_2" on="p" hint="Heading 2"></class>
  <class name="run_1" on="r"></class>
</classes>
```

Rules:

- `on="p"` indicates a paragraph class
- `on="r"` indicates an inline class
- `on="tbl"` indicates a table class
- `name` is a writable class name within the current document
- `hint` is a semantic hint; it may not always be present
- In some views, `<class>` may also carry `attr` / `runAttr` to indicate default block-level and default inline formatting

When editing, prefer reusing semantic classes listed here rather than looking for legacy `P/C/T/L` keys first.

### Inserting Structural Content Without Heading Classes

When `<classes>` has no heading class (common in flat-style contracts/forms), do not fake headings with body-text class + minimal spacing. Use `attr` overrides that create clear visual separation:

```xml
<p attr="spacing-before:360;font-size:28;b:true;outline-level:0"><r>Chapter Title</r></p>
<p attr="spacing-before:240;font-size:24;b:true;outline-level:1"><r>Section Title</r></p>
```

Spacing reference (half-point values for `spacing-before`):
- Body text: 60–120 (3–6pt)
- Section heading: 240–480 (12–24pt)
- Chapter heading: 360–600 (18–30pt)

`font-size` should be 2–4 half-points larger than body text. Set `outline-level` so TOC can pick up the heading. If prototypes exist, prefer `proto` over hand-crafted attr — always check `read(part="prototypes")` first.

### WIR Inline Elements
- `<r>` — Text run. May carry `attr`: `<r attr="b:true;color:#FF0000">text</r>`
- `<img>` / `<image>` — Embedded image
- `<omml>` — OMML math formula. `<omml latex="E=mc^2">`
- `<hyperlink>` — Hyperlink. `url` (external) or `anchor` (internal bookmark)
- `<footnote>` / `<endnote>` — Inline footnote/endnote reference
- `<field>` — Field code
- `<toc>` — Table of contents block
- `<table>` — Table
- `<keep>` — Preserved opaque content (charts, complex drawings)

### Run `attr` Keys
`b` (bold), `i` (italic), `strike`, `font-size` (half-points), `font-family`, `color` (#hex or `theme(accent1)`), `highlight`, `shd`, `u` (underline), `caps`, `smallCaps`, `char-spacing` (twips, see below), `vert`

`char-spacing`: character spacing in twips (1/20 pt). Positive = expand, negative = condense. CJK large titles: `char-spacing:20` to `char-spacing:60` prevents cramped appearance. Original documents may have extreme negative values (-30 to -66) to force-fit text in narrow cells — when editing such text with longer replacements, consider resetting or widening `char-spacing`.

### Paragraph `attr` Keys
`jc` (alignment), `class` (style), `list`/`list-level`, `ind-left`/`ind-right`/`ind-first`/`ind-hanging`, `spacing-before`/`spacing-after`, `line-spacing`, `spacing-line-rule`, `keep-next`, `page-break-before`, `shd`, `outline-level`, `border-*`

### Breaks

```xml
<p><r>first line</r><br /><r>second line</r></p>  <!-- line break -->
<p><br type="page" /></p>                           <!-- page break -->
<p><br type="column" /></p>                         <!-- column break -->
```

`type` supports: `page`, `column`. For layout changes (orientation, margins, columns, page numbering), use `<section>` instead.

### Section Properties

`<section>` controls page layout, pagination, and header/footer binding. It is a top-level story block.

```xml
<section sect="nextPage" pgW="11906" pgH="16838" orient="portrait"
         marTop="1440" marBottom="1440" marLeft="1800" marRight="1800" />
```

| Attribute | Purpose | Example |
|---|---|---|
| `sect` | Break type | `nextPage`, `continuous`, `evenPage`, `oddPage` |
| `pgW` / `pgH` | Page size (twips) | `11906` / `16838` (A4) |
| `orient` | Orientation | `portrait` / `landscape` |
| `marTop/Bottom/Left/Right` | Margins (twips) | `1440` (1 inch) |
| `pgNumFmt` | Page number format | `decimal`, `upperRoman`, `lowerLetter` |
| `pgNumStart` | Starting page number | `1` |
| `colNum` | Column count | `2` |
| `titlePg` | First page different | `1` |
| `hdrDefault` / `ftrDefault` | Header/footer binding | `rId10` |

Rules:
- Use `<br type="page" />` for simple page breaks — do not create `<section>` just to break pages
- Only use `<section>` when layout actually changes: orientation, margins, columns, page numbering, or header/footer binding

### Fields

```xml
<field kind="PAGE"></field>       <!-- current page number -->
<field kind="NUMPAGES"></field>   <!-- total page count -->
```

Use fields in headers/footers for page numbers — never hard-code page numbers as text:

```xml
<p><r>Page </r><field kind="PAGE"></field><r> of </r><field kind="NUMPAGES"></field></p>
```

---

## 4. Editing WIR Content

### Usage

```python
updated = session.edit(w1, [
    TextEdit(old_string="<r>original text</r>", new_string="<r>new text</r>")
])
```

Low-level:
```python
updated_wir = modify_wir(
    package,
    base_wir=wir_content,
    edits=[TextEdit(old_string="...", new_string="...")],
    source_part="word/document.xml",
)
```

### Window Scope Rules
- `edit` only modifies the cached WIR for the given cursor
- Keep edits within the window: one cursor + one localized intent
- `old_string` approximately 80-400 characters; replace complete localized blocks
- 1-3 edits per call
- Avoid single-character anchors or massive cross-page anchors
- Re-read affected windows after structural edits

### WIR Safety Rules
- `new_string` must be a valid XML fragment
- Text within `<p>` must be wrapped in `<r>...</r>`
- Allowed child elements of `<p>`: `<r>`, `<br>`, `<tab>`, `<keep>`, `<img>`, `<omml>`, `<hyperlink>`, `<textbox>`, `<group>`, `<shape>`, `<field>`, `<ins>`, `<del>`, `<footnote>`, `<endnote>`
- `<r>` is plain text: `<r>body text</r>`, do not nest tags inside
- Tags must be closed
- Do not explicitly set the `k` attribute on newly inserted nodes
- Must `save` after editing

### Run Formatting (`attr` on `<r>`)
```xml
<r attr="b:true;color:#FF0000">bold red text</r>
```
See Section 3 "Run `attr` Keys" for the full list of supported attributes.

### Paragraph Formatting (`attr` on `<p>`)
```xml
<p attr="jc:center;ind-first:420;spacing-before:120"><r>centered text</r></p>
```

### Edit Examples

Empty paragraph -> body text:
```
old: <p k="P1" class="normal"></p>
new: <p k="P1" class="normal"><r>body text</r></p>
```

Bold red:
```xml
<r attr="b:true;color:#FF0000">important content</r>
```

Centered paragraph:
```xml
<p attr="jc:center"><r>centered text</r></p>
```

Insert table:
```xml
<table><tr><td><p><r>A1</r></p></td><td><p><r>B1</r></p></td></tr></table>
```

Insert TOC:
```xml
<toc instr="TOC \o &quot;1-3&quot; \h \z \u"></toc>
```

Insert formula:
```xml
<omml latex="E=mc^2"></omml>
```

Insert image:
```xml
<image path="/path/to/img.png" width="400" height="300"></image>
```

Insert hyperlink:
```xml
<hyperlink url="https://example.com"><r>external link</r></hyperlink>
<hyperlink anchor="Section3"><r>internal bookmark link</r></hyperlink>
```

Insert footnote:
```xml
<p><r>statement text</r><footnote>supporting details.</footnote></p>
```

Delete a paragraph (replace with empty string):
```python
session.edit(w1, [TextEdit(
    old_string='<p k="P100" class="normal"><r>content to remove</r></p>',
    new_string=''
)])
```

Delete multiple consecutive paragraphs in one call:
```python
session.edit(w1, [
    TextEdit(old_string='<p k="P100" class="normal"><r>unwanted section title</r></p>', new_string=''),
    TextEdit(old_string='<p k="P101" class="normal"><r>unwanted body text</r></p>', new_string=''),
])
```
After deletion, re-read the window to get updated keys before further edits.

Insert list items (do not fake lists with `1.` / `•` text or `<list>` / `<item>` tags):
```xml
<p list="list_decimal" list-level="0"><r>First item</r></p>
<p list="list_decimal" list-level="0"><r>Second item</r></p>
<p list="list_bullet" list-level="1"><r>Sub-item</r></p>
```

Preserve opaque content (charts, complex drawings):
```xml
<keep k="K5" />
```

Clone a block-level keep:
```xml
<keep k="auto" proto="clone:K5" />
```

Reuse a prototype paragraph or table row:
```xml
<p proto="P123"><r>New text following template style</r></p>
<tr proto="R456">...</tr>
```

### Common Mistakes (Wrong → Right)

**Bare text in `<p>`** — text must be wrapped in `<r>`:
```xml
<!-- Wrong --> <p>text</p>
<!-- Right --> <p><r>text</r></p>
```

**Tags inside `<r>`** — inline elements are siblings of `<r>`, not children:
```xml
<!-- Wrong --> <r><hyperlink url="..."><r>link</r></hyperlink></r>
<!-- Right --> <hyperlink url="..."><r>link</r></hyperlink>
```

**Fake list** — use native list attributes, not text numbering:
```xml
<!-- Wrong --> <p><r>1. First item</r></p>
<!-- Right --> <p list="list_decimal" list-level="0"><r>First item</r></p>
```

**Bold body text pretending to be heading** — use heading class or attr overrides (see "Inserting Structural Content Without Heading Classes" in Section 3):
```xml
<!-- Wrong --> <p class="body"><r attr="b:true">Section Title</r></p>
<!-- Right --> <p class="heading_1"><r>Section Title</r></p>
```

**Hard-coded page number** — use fields in headers/footers:
```xml
<!-- Wrong --> <p><r>Page 1</r></p>
<!-- Right --> <p><r>Page </r><field kind="PAGE"></field></p>
```

### Error Handling
- `Unknown cursor id`: Re-`read` and use the new cursor
- `E_OLD_NOT_FOUND`: Re-read the window and use a more unique `old_string`
- `W_MULTI_MATCH_REPLACED_FIRST`: Use a more unique fragment or `replace_all=True`
- `E_XML_INVALID`: Narrow scope and ensure tags are closed

### Comment Editing Pattern

See Section 8 "Comments and Revisions" for full comment operations including adding, replying, resolving, deleting, precise text anchoring (`start_text`/`end_text`), and warning handling.

---

## 5. Saving the Document

```python
session.save("/path/to/output.docx")
# Or low-level:
save_docx(package, "/path/to/output.docx")
```

- Must save after editing
- Save may fail if class/list/proto/url references are invalid
- Omitting the output path overwrites the original file

---

## 6. WIR Editing Handbook

### Canonical Tool Sequence

Always follow: open -> read -> edit -> save. Never skip `read`.

### Structured Reading Strategy

Read `document` first and plan semantic classes from `<classes>` before editing. See Section 2 "Key Rules" and Section 3 "Available Parts" for detailed reading guidance and cursor discipline.

### Safe XML Patterns

See Section 4 "Edit Examples" and "Common Mistakes" for comprehensive examples. Additional pattern:

#### Mixed Formatting in One Paragraph
```xml
<p k="P200">
  <r>normal </r>
  <r attr="b:true;color:#C62828">highlighted</r>
  <r> trailing</r>
</p>
```

### Key Drift After Edits

After an `edit` call, paragraph keys (`k="..."`) within the affected window may change — the engine re-indexes blocks after structural modifications. This is normal behavior.

To minimize re-read overhead:
- Pack up to 3 related `TextEdit` operations into a single `edit` call rather than one-at-a-time
- For uniform changes across many paragraphs (e.g., applying the same style fix), use `replace_all=True` to handle all occurrences in one call
- Only re-read when you need fresh keys for the *next* batch of edits — not after every single edit

### High-Risk Operation Controls

#### Structural Insert/Delete
- One structural operation per batch
- Re-read immediately after the operation
- Verify downstream windows

#### Table Surgery
- Preserve table shape (unless a redesign is requested)
- Modify one table at a time
- Separate content edits from structural changes

#### Header/Footer Editing
- Identify the exact `header:rIdX` or `footer:rIdX`
- Only edit the target story part

#### Comment Workflow

See Section 8 "Comments and Revisions" for full details.

### Production Edit Recipes

#### Recipe A: Global Term Replacement
1. Read the target body window
2. Replace small-scope fragments
3. Re-read key windows to verify

#### Recipe B: Insert Contract Clauses
1. Read the target section window, start with `<classes>`
2. Find anchor paragraphs near the insertion point
3. Prefer reusing nearby clause classes; read `prototypes` or `styles` only if needed
4. Re-read to verify numbering/spacing
5. Save

#### Recipe C: Update Report Table Data
1. Read the window containing the table
2. Edit `<td>` content first
3. Handle schema changes in a separate batch
4. Re-read to verify
5. Save

#### Recipe D: Cover Page / Header Metadata Refresh
1. Read the document first page and `header:rIdX`
2. Apply updates to both content areas
3. Verify no field corruption
4. Save

### Pre-Save Re-Read Checklist

Minimum:
- All edited document windows
- All edited non-document parts

Recommended:
- One additional window before and after each edited structural region

### Post-Save Review

1. Save success message and path
2. Warning list is empty or understood
3. Requested sections exist and contain expected wording
4. Table content and numbering are coherent
5. Headers/footers/footnotes/comments are intact

---

## 7. Troubleshooting

### First-Response Protocol

When an error occurs:
1. Stop chaining new edits
2. Capture the error code/message
3. Re-read the affected part/window
4. Apply a minimal recovery edit
5. Continue with smaller batches

### Common Errors and Recovery

#### Unknown / Stale Cursor

Symptoms:
- "Unknown cursor id"
- Stale window behavior after structural edits

Recovery:
1. Re-`read` the same part
2. Use the newly returned cursor
3. Retry with a smaller, localized anchor

#### `E_OLD_NOT_FOUND`

Causes:
- `old_string` does not match the current cached window
- Text drift after previous edits

Recovery:
1. Re-read the cursor window
2. Copy the exact current fragment
3. Use a more unique anchor context

#### `E_XML_INVALID`

Causes:
- Malformed replacement XML
- Invalid paragraph/run structure

Recovery:
1. Replace only one complete localized block
2. Ensure `<p>` child elements are valid inline nodes
3. Wrap plain text in `<r>`
4. Close all tags

#### `E_STYLE_NOT_FOUND` / `E_LIST_INVALID` / `E_PROTO_NOT_FOUND`

Recovery: Re-read the relevant part (`document` for classes, `styles` for legacy keys, `prototypes` for proto IDs) and switch to a key that exists in the current document.

#### `E_URL_INVALID`

Recovery: Use an absolute `https://...` URL.

#### `E_READ_TOO_LARGE`

Recovery: Reduce scope using cursor-based pagination.

### Warning Handling Strategy

1. Structural risk warnings: investigate immediately
2. Cosmetic/normalization warnings: verify output and continue
3. Repeated warning patterns: reduce edit batch size and anchor scope

### Safe Recovery Patterns

#### Pattern A: Reset and Continue
1. Save current progress
2. Re-open the document
3. Re-read the target window
4. Continue with smaller batches

#### Pattern B: Isolate Risky Section
1. Complete the safe sections first
2. Isolate the problematic table/section/header/footer
3. Read and edit that part separately

#### Pattern C: Roll Forward, Do Not Blindly Overwrite
1. Re-anchor at the current state
2. Apply localized idempotent edits

### Save-Time Warning Triage

1. Classify: validation warnings, reference warnings, namespace/serialization warnings
2. Re-open and inspect edited parts
3. Non-blocking warnings with sound structure -> report transparently
4. Warnings suggesting corruption risk -> fix before delivery

### Escalation Criteria

Escalate (request the user to narrow scope or constraints) when:
1. Structural errors persist after two retries
2. The document has severe pre-existing corruption
3. User requests conflict with immutable template constraints

---

## 8. Comments and Revisions

### Comment Operations

#### Adding Comments

```python
wc, comments_wir, _ = session.read(part="comments")
session.edit(wc, [TextEdit(
    old_string='</comments>',
    new_string='<comment id="1" start="P10" end="P10" author="Agent" date="2026-03-11T00:00:00Z">comment text</comment>\n</comments>'
)])
```

**Important**: Comment content in WIR is a direct text node; do not include `<p>` or `<r>` child elements.

#### Precise Text Anchoring with `start_text` / `end_text`

By default, a comment anchors to **the entire paragraph**. To select specific text within a paragraph (like highlighting with a mouse), use `start_text` and `end_text`:

```python
wc, comments_wir, _ = session.read(part="comments")
session.edit(wc, [TextEdit(
    old_string='</comments>',
    new_string=(
        '<comment id="auto" start="P10" end="P10"'
        ' start_text="医疗服务价格改革"'
        ' end_text="区域分类路径"'
        ' author="Agent" date="2026-03-19T00:00:00Z">'
        'Comment anchored to specific text range'
        '</comment>\n</comments>'
    ),
)])
```

This selects from "医疗服务价格改革" to "区域分类路径" within paragraph P10.

**Cross-paragraph range**: Use different `start`/`end` keys with text anchors in each:

```python
'<comment id="auto" start="P10" end="P12"'
' start_text="beginning of selection"'
' end_text="end of selection"'
' author="Agent">Spans three paragraphs</comment>'
```

**Text matching behavior**:
- Exact substring match is tried first
- If exact match fails, normalized matching handles CJK punctuation differences (full-width ⇄ half-width, curly quotes ⇄ straight quotes, etc.)
- If both fail, the engine **falls back to whole-paragraph anchoring** and emits a `W_COMMENT_ANCHOR_FALLBACK` warning

**⚠ Verifying P-keys before anchoring**: The `text_only` read view omits paragraphs inside table cells but they still have P-keys. A paragraph you see as "P12" in `text_only` may actually be a different element in the document structure. Before adding comments:

1. Check `session.last_edit_warnings` after each comment edit — if you see `W_COMMENT_ANCHOR_FALLBACK`, your `start_text` did not match the paragraph content, meaning you likely targeted the wrong P-key
2. When the document contains tables, verify P-key content by reading the XML view, not just `text_only`
3. After adding comments, `re-read(part="comments")` — the response now includes `start_text`/`end_text` attributes showing the actual selected text, so you can confirm the anchor is correct

#### Replying to Comments

Omit `start`/`end` for replies — the engine inherits the parent's anchor.

```python
wc, comments_wir, _ = session.read(part="comments")
session.edit(wc, [TextEdit(
    old_string='</comments>',
    new_string='<comment id="auto" parent="1" author="Agent">reply content</comment>\n</comments>'
)])
```

#### Resolving Comments

Mark as resolved by setting `resolved="true"`.

#### Deleting Comments

Remove the corresponding `<comment>` element via an edit.

### Comment Rules

- Top-level comments must include `start`/`end` pointing to valid document block keys
- Replies: set `parent` to the parent comment ID, omit `start`/`end` (engine inherits parent's anchor)
- Do not use `parentId` or nest `<reply>` elements
- `start`/`end` must point to valid document block keys in the current session (typically paragraph keys)
- Do not insert comment marker tags in the document WIR; ranges/references are rebuilt from the comments part
- Appending by replacing `</comments>` is the safest pattern
- `start_text`/`end_text` anchor to specific text within start/end paragraphs (see "Precise Text Anchoring" above)
- After comment edits, document block keys may be rearranged; always re-read `comments` before appending more comments or replies
- Check `session.last_edit_warnings` after each comment edit — `W_COMMENT_ANCHOR_FALLBACK` means your text anchor missed and fell back to whole-paragraph anchoring
- If the body was just modified, re-read `document` first before working on comments

### Revision Marks

Revisions in WIR are represented using `<ins>` and `<del>` tags.

**Important**: `<ins>` and `<del>` must wrap complete `<r>` tags, not be placed inside `<r>`.

**Correct format**:
```xml
<!-- Insertion -->
<p k="P1" class="normal">
  <ins id="1" author="John Doe" date="2026-03-11T00:00:00Z">
    <r class="run_1">newly added content</r>
  </ins>
</p>

<!-- Deletion -->
<p k="P2" class="normal">
  <del id="2" author="John Doe" date="2026-03-11T00:00:00Z">
    <r class="run_1">deleted content</r>
  </del>
</p>
```

**Incorrect format** (will raise `E_XML_INVALID: <r> cannot contain child elements`):
```xml
<!-- Wrong: <ins> cannot be placed inside <r> -->
<p k="P1" class="normal">
  <r class="run_1"><ins>newly added content</ins></r>
</p>
```

### Verification

After saving, manually confirm at minimum:
- Comment anchors are correct
- Revision marks are accurately positioned
- `comments.xml` existing does not equal comments being visible (count mismatch = not saved)

---

## Reference Entry Points

- For overall routing: `../SKILL.md`
- For creating new documents: `openxml-sdk-reference.md`
- For matplotlib charts: `matplotlib-guide.md`
- For Markdown → Word conversion: `md2docx-reference.md`
