# OpenXML SDK Creation Reference

Creating new Word documents with C# + OpenXML SDK.

Workflow: Write `Program.cs` → `./scripts/docx build <output-path>` → deliver after validation passes.

## 1. Build Commands

```bash
./scripts/docx <command> [args]
```

| Command | Purpose |
|---------|---------|
| `build <output-path>` | Compile → run → auto-fix element order → OpenXML validate → business rules |
| `validate <file.docx>` | Validate existing docx |
| `init` | Install dependencies + workspace at `/tmp/docx-work/` |
| `env` | Show environment status |

`build` does everything. Do not manually `dotnet build && dotnet run` — that bypasses auto-fix and validation.

## Common Traps (read first)

**Element Reuse → InvalidOperationException**: Every OpenXmlElement instance belongs to ONE parent. Never Append the same RunProperties/ParagraphProperties to multiple Runs/Paragraphs. Use factory methods or `CloneNode(true)`.

**CJK Punctuation in C# Syntax → CS1056**: Chinese text is safe inside ASCII `"` delimiters. But Chinese `，；（）""` leaked into C# syntax positions (parameter lists, statement terminators, string delimiters) causes compilation failure. See `CJKExample.cs` header for full examples.

**Default Parameter with Enum → CS1736**: `JustificationValues.Left` is not a compile-time constant. Use nullable + null-coalesce: `void Foo(JustificationValues? align = null) { align ??= ...; }`

**TitlePage, not DifferentFirstPage**: `DifferentFirstPage` does NOT exist in the SDK. Use `new TitlePage()`.

**Hyperlinks**: Use `AddHyperlinkRelationship(uri, true)`, NOT `AddExternalRelationship`.

**Chinese Quotes Break String Boundaries → CS1003**: Use `\"` to escape double quotes inside strings. **Never use `\uXXXX` for any Chinese text.**

```csharp
// WRONG — quotes break the string:
P("遵循"统筹规划"的原则")          // CS1003!

// CORRECT — escape with \":
P("遵循\"统筹规划\"的原则")
```

**Parenthesis Nesting → CS1002/CS1026**: Closing `ParagraphProperties` too early orphans child elements. The most common bug in deep OpenXML constructors.

```csharp
// WRONG — Justification is OUTSIDE ParagraphProperties:
new Paragraph(
    new ParagraphProperties(
        new SpacingBetweenLines { Before = "200" }),     // ← closes ParagraphProperties!
        new Justification { Val = JustificationValues.Left }),  // ← orphaned!
    new Run(...))

// CORRECT — all children INSIDE ParagraphProperties:
new Paragraph(
    new ParagraphProperties(
        new SpacingBetweenLines { Before = "200" },
        new Justification { Val = JustificationValues.Left }),  // ← inside
    new Run(...))
```

Use helper methods (`MkPara`, `MkH1`) to flatten nesting — see Example.cs / CJKExample.cs.

**TableGrid Must Be Child of Table, NOT TableProperties → "missing tblGrid"**:

```csharp
// WRONG — TableGrid nested inside TableProperties:
new Table(new TableProperties(..., new TableGrid(...)))

// CORRECT — TableGrid is sibling of TableProperties:
new Table(
    new TableProperties(...)),  // ) closes Properties
    new TableGrid(...));        // sibling, child of Table
```

## Color & Typography

Pick ONE hue direction, stay within it. Build a 3-tier system: Primary (headings) / Dark (body text) / Light (captions). Cover/backcover text must visibly contrast with background — dark bg needs white or light text.

Anti-patterns: pure #FF0000/#0000FF/#00FF00, all-blue documents, rainbow charts, same color for text and background.

Valid hue directions (examples, not mandates):
- Warm earthy: #5D4037, #795548, #D4A574
- Cool slate: #37474F, #546E7A, #78909C
- Natural green: #4A6741, #7C9885, #9CAF88
- Neutral gray + one accent: #333, #666, #999 + any single hue
- Berry/plum: #6B3A5B, #8E6278, #C9A0B5
- Ink & gold: #263238, #455A64, #B8860B

Spacing (descriptive, not prescriptive): headings need generous space before (more than after) to visually separate sections. Body text needs comfortable line height (~1.3-1.5x) and modest paragraph spacing. CJK body text uses 2-character first-line indent. Large CJK titles benefit from letter-spacing to prevent cramped appearance. Table cells need small internal padding. Captions are tighter to their figures than to following text.

Default to including page header (document title) and page footer (page numbers) for formal documents.

## 2. Program.cs Setup

```csharp
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using DW = DocumentFormat.OpenXml.Drawing.Wordprocessing;
using A = DocumentFormat.OpenXml.Drawing;
using PIC = DocumentFormat.OpenXml.Drawing.Pictures;
using C = DocumentFormat.OpenXml.Drawing.Charts;  // if charts needed
using M = DocumentFormat.OpenXml.Math;             // if math needed

string outputFile = args.Length > 0 ? args[0] : "./output.docx";
using var doc = WordprocessingDocument.Create(outputFile, WordprocessingDocumentType.Document);
var mainPart = doc.AddMainDocumentPart();
mainPart.Document = new Document(new Body());
var body = mainPart.Document.Body!;
// ... build document ...
doc.Save();
```

**A4**: 11906 × 16838 twips = 7560000 × 10692000 EMU. Standard margins: 1440 twips (1 inch).

## 3. Document Architecture

Sections chain via `SectionProperties`. Each section ends with a Paragraph whose ParagraphProperties contains SectionProperties. The **last** section's SectionProperties goes directly on Body.

```
Cover   (TitlePage, zero margins)        → NextPage
→ TOC   (normal margins)                  → NextPage
→ Body  (HeaderRef + FooterRef, margins)  → NextPage
→ Back  (zero margins)                    → final SectionProperties on body
```

```csharp
// Mid-document section break
body.Append(new Paragraph(new ParagraphProperties(
    new SectionProperties(
        new SectionType { Val = SectionMarkValues.NextPage },
        new PageSize { Width = 11906, Height = 16838 },
        new PageMargin { Top = 1800, Right = 1440, Bottom = 1440, Left = 1440,
                         Header = 720, Footer = 720 }))));

// Final section (directly on body, not in paragraph)
body.Append(new SectionProperties(
    new PageSize { Width = 11906, Height = 16838 },
    new PageMargin { Top = 0, Right = 0, Bottom = 0, Left = 0, Header = 0, Footer = 0 }));
```

## 4. Patterns

### 4.1 Styles

```csharp
var stylesPart = mainPart.AddNewPart<StyleDefinitionsPart>();
stylesPart.Styles = new Styles();

stylesPart.Styles.Append(new Style(
    new StyleName { Val = "heading 1" },       // built-in name (lowercase)
    new BasedOn { Val = "Normal" },
    new StyleParagraphProperties(
        new KeepNext(), new KeepLines(),
        new SpacingBetweenLines { Before = "600", After = "240" },
        new OutlineLevel { Val = 0 }           // 0=H1, 1=H2, 2=H3
    ),
    new StyleRunProperties(
        new Bold(), new FontSize { Val = "36" },
        new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }
    )
) { Type = StyleValues.Paragraph, StyleId = "Heading1" });
```

- `StyleId` (code ref) ≠ `StyleName.Val` (Word display). Use `Heading1` in code, `heading 1` as name.
- `OutlineLevel` required for TOC recognition. TOC only sees built-in style names.
- Font size in half-points: 12pt = `Val="24"`.
- Always set `EastAsia` on RunFonts for CJK documents — without it CJK renders in Calibri.

### 4.2 Cover & Backcover

Not every document needs a cover — but when one is appropriate, generate the background from scratch (see §4.14). The background palette and cover text must use the same color scheme as the body, ensuring the cover feels like a cohesive part of the document rather than a mismatched add-on. Cover text must be readable against the background — sufficient contrast, large font, generous spacing.

Cover = floating background + title paragraphs + SectionProperties(TitlePage, zero margins).

```csharp
body.Append(new Paragraph(new Run(CreateFloatingBackground(coverImageId, 1, "CoverBg"))));
body.Append(new Paragraph(
    new ParagraphProperties(new SpacingBetweenLines { Before = "6000" }),  // push down
    new Run(new RunProperties(new FontSize { Val = "96" }), new Text("Title"))
));
// Cover section break
body.Append(new Paragraph(new ParagraphProperties(
    new SectionProperties(
        new TitlePage(),   // TRAP: "DifferentFirstPage" does NOT exist — use TitlePage
        new SectionType { Val = SectionMarkValues.NextPage },
        new PageSize { Width = 11906, Height = 16838 },
        new PageMargin { Top = 0, Right = 0, Bottom = 0, Left = 0, Header = 0, Footer = 0 }))));
```

Backcover: same pattern. Cover/backcover text must visibly contrast with background — use the document's color tiers (e.g., light text on dark bg, or dark text on light bg), significantly larger font, and generous vertical spacing.

### 4.3 TOC (Field Codes)

TOC must be field codes, not static text. Headings must use built-in styles. **Placeholder entries must mirror the document's actual heading structure 1:1** — every H1/H2/H3 in the body needs a corresponding fake TOC entry with matching text and level. An empty TOC is useless to the reader.

```csharp
// Begin
body.Append(new Paragraph(
    new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }),
    new Run(new FieldCode(" TOC \\o \"1-3\" \\h \\z \\u ") { Space = SpaceProcessingModeValues.Preserve }),
    new Run(new FieldChar { FieldCharType = FieldCharValues.Separate })));
// Placeholder entries (refreshed by Word on open)
body.Append(new Paragraph(
    new ParagraphProperties(new ParagraphStyleId { Val = "TOC1" }),
    new Run(new Text("Chapter")), new Run(new TabChar()), new Run(new Text("1"))));
// End
body.Append(new Paragraph(
    new Run(new FieldChar { FieldCharType = FieldCharValues.End })));
```

Auto-refresh on open: `new Settings(new UpdateFieldsOnOpen { Val = true })` in DocumentSettingsPart.

### 4.4 Header, Footer & Section Properties

```csharp
// Header part
var headerPart = mainPart.AddNewPart<HeaderPart>();
var headerId = mainPart.GetIdOfPart(headerPart);
headerPart.Header = new Header(new Paragraph(
    new Run(new RunProperties(new FontSize { Val = "18" }), new Text("Header"))));

// Footer with page number
var footerPart = mainPart.AddNewPart<FooterPart>();
var footerId = mainPart.GetIdOfPart(footerPart);
var footerPara = new Paragraph(new ParagraphProperties(
    new Justification { Val = JustificationValues.Center }));
// PAGE field: Begin → Code → Separate → Placeholder → End
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }));
footerPara.Append(new Run(new FieldCode(" PAGE ") { Space = SpaceProcessingModeValues.Preserve }));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.Separate }));
footerPara.Append(new Run(new Text("1")));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.End }));
footerPart.Footer = new Footer(footerPara);

// Section — refs MUST come before pgSz/pgMar
new SectionProperties(
    new HeaderReference { Type = HeaderFooterValues.Default, Id = headerId },
    new FooterReference { Type = HeaderFooterValues.Default, Id = footerId },
    new PageSize { Width = 11906, Height = 16838 },
    new PageMargin { Top = 1800, Right = 1440, Bottom = 1440, Left = 1440,
                     Header = 720, Footer = 720 })
```

Same field pattern for `NUMPAGES` (total pages) and `DATE`. To put background in header, add image to HeaderPart: `headerPart.AddImagePart()` → `CreateFloatingBackground()` in header paragraph.

### 4.5 DrawingML: Floating Background

Full-page image behind text. Copy this function — the 4-namespace nesting is error-prone.

```csharp
// Image setup (before calling this function):
// var imgPart = mainPart.AddImagePart(ImagePartType.Png);
// using (var fs = File.OpenRead(path)) imgPart.FeedData(fs);
// var imageId = mainPart.GetIdOfPart(imgPart);

static Drawing CreateFloatingBackground(string imageId, uint docPrId, string name,
    long cx = 7560000, long cy = 10692000)          // A4 EMU default
{
    return new Drawing(                               // Wordprocessing.Drawing (NO prefix)
        new DW.Anchor(                                // DW = Drawing.Wordprocessing
            new DW.SimplePosition { X = 0, Y = 0 },
            new DW.HorizontalPosition(new DW.PositionOffset("0"))
            { RelativeFrom = DW.HorizontalRelativePositionValues.Page },
            new DW.VerticalPosition(new DW.PositionOffset("0"))
            { RelativeFrom = DW.VerticalRelativePositionValues.Page },
            new DW.Extent { Cx = cx, Cy = cy },
            new DW.EffectExtent { LeftEdge = 0, TopEdge = 0, RightEdge = 0, BottomEdge = 0 },
            new DW.WrapNone(),
            new DW.DocProperties { Id = docPrId, Name = name },
            new DW.NonVisualGraphicFrameDrawingProperties(
                new A.GraphicFrameLocks { NoChangeAspect = true }),
            new A.Graphic(                            // A = Drawing
                new A.GraphicData(                    // Uri goes HERE, not on Graphic
                    new PIC.Picture(                  // PIC = Drawing.Pictures
                        new PIC.NonVisualPictureProperties(
                            new PIC.NonVisualDrawingProperties { Id = 0, Name = $"{name}.png" },
                            new PIC.NonVisualPictureDrawingProperties()),
                        new PIC.BlipFill(
                            new A.Blip { Embed = imageId },
                            new A.Stretch(new A.FillRectangle())),
                        new PIC.ShapeProperties(
                            new A.Transform2D(
                                new A.Offset { X = 0, Y = 0 },
                                new A.Extents { Cx = cx, Cy = cy }), // MUST match Extent above
                            new A.PresetGeometry { Preset = A.ShapeTypeValues.Rectangle })))
                { Uri = "http://schemas.openxmlformats.org/drawingml/2006/picture" }))
        {
            DistanceFromTop = 0, DistanceFromBottom = 0,
            DistanceFromLeft = 0, DistanceFromRight = 0,
            SimplePos = false, RelativeHeight = 251658240,
            BehindDoc = true, Locked = false,
            LayoutInCell = true, AllowOverlap = true
        });
}
```

### 4.6 DrawingML: Inline Image

Insert chart/photo at natural size with aspect ratio preserved. Copy this function — it handles PNG dimension reading, proportional scaling, and all required DrawingML nesting.

```csharp
static void AddInlineImage(Body body, MainDocumentPart mainPart,
    string imagePath, string altText, uint docPrId, int maxWidthCm = 15)
{
    if (!File.Exists(imagePath))
    { Console.Error.WriteLine($"WARNING: Image not found: {imagePath}"); return; }

    var imagePart = mainPart.AddImagePart(ImagePartType.Png);
    byte[] imageBytes = File.ReadAllBytes(imagePath);
    using (var ms = new MemoryStream(imageBytes)) imagePart.FeedData(ms);
    var imageId = mainPart.GetIdOfPart(imagePart);

    // PNG header: width at bytes 16-19, height at 20-23 (big-endian)
    int imgWidth, imgHeight;
    using (var ms = new MemoryStream(imageBytes))
    {
        ms.Seek(16, SeekOrigin.Begin);
        byte[] wb = new byte[4], hb = new byte[4];
        ms.Read(wb, 0, 4); ms.Read(hb, 0, 4);
        if (BitConverter.IsLittleEndian) { Array.Reverse(wb); Array.Reverse(hb); }
        imgWidth = BitConverter.ToInt32(wb, 0);
        imgHeight = BitConverter.ToInt32(hb, 0);
    }

    long maxWidthEmu = maxWidthCm * 360000L;           // 1 cm = 360000 EMU
    long cx = maxWidthEmu;
    long cy = (long)(cx * ((double)imgHeight / imgWidth));

    var drawing = new Drawing(
        new DW.Inline(
            new DW.Extent { Cx = cx, Cy = cy },
            new DW.EffectExtent { LeftEdge = 0, TopEdge = 0, RightEdge = 0, BottomEdge = 0 },
            new DW.DocProperties { Id = docPrId, Name = altText },
            new DW.NonVisualGraphicFrameDrawingProperties(
                new A.GraphicFrameLocks { NoChangeAspect = true }),
            new A.Graphic(
                new A.GraphicData(
                    new PIC.Picture(
                        new PIC.NonVisualPictureProperties(
                            new PIC.NonVisualDrawingProperties { Id = 0, Name = $"{altText}.png" },
                            new PIC.NonVisualPictureDrawingProperties()),
                        new PIC.BlipFill(
                            new A.Blip { Embed = imageId },
                            new A.Stretch(new A.FillRectangle())),
                        new PIC.ShapeProperties(
                            new A.Transform2D(
                                new A.Offset { X = 0, Y = 0 },
                                new A.Extents { Cx = cx, Cy = cy }),
                            new A.PresetGeometry { Preset = A.ShapeTypeValues.Rectangle })))
                { Uri = "http://schemas.openxmlformats.org/drawingml/2006/picture" }))
        { DistanceFromTop = 0, DistanceFromBottom = 0,
          DistanceFromLeft = 0, DistanceFromRight = 0 });

    body.Append(new Paragraph(
        new ParagraphProperties(new KeepNext(),
            new Justification { Val = JustificationValues.Center },
            new SpacingBetweenLines { Before = "200", After = "80" }),
        new Run(drawing)));
}
```

Usage: `AddInlineImage(body, mainPart, "/path/to/chart.png", "Revenue Chart", docPrId++);`

For different widths, pass `maxWidthCm`: `AddInlineImage(body, mainPart, path, "Pie", docPrId++, 11);`

### Image Width Guidelines

Not all images should be full-width. Choose `maxWidthCm` by content type:

| Content | maxWidthCm | Rationale |
|---------|------------|-----------|
| Wide bar/line charts | 15 | Full width, uses horizontal space well |
| Pie/donut charts | 10-11 | Circles look unnatural when stretched |
| Vertical bar charts | 12-13 | Moderate width |
| Photos/screenshots | contextual | Full-width only if high-res |

Anti-pattern: all images at the same width regardless of content.

### DrawingML Traps

- `Drawing` is **Wordprocessing** namespace (no prefix). `DW.Drawing` does NOT exist.
- `DW.RelativeHeight` and `DW.SizeRelativeFromValues` do NOT exist. `RelativeHeight` on `Anchor` is a plain `UInt32Value`.
- `GraphicData { Uri = "..." }` — the Uri goes on `A.GraphicData`, NOT on `A.Graphic`.
- `EffectExtent` is REQUIRED even when all values are 0.
- `Extent.Cx/Cy` and `Transform2D.Extents.Cx/Cy` MUST match — different values distort the image.
- `DocProperties.Id` must be unique across the entire document. Use an incrementing counter.

### 4.7 Tables

**Three-line table** (academic style — top/bottom thick, no vertical lines):

```csharp
var table = new Table();
table.Append(new TableProperties(
    new TableWidth { Width = "5000", Type = TableWidthUnitValues.Pct },
    new TableBorders(
        new TopBorder { Val = BorderValues.Single, Size = 12, Color = "7C9885" },
        new BottomBorder { Val = BorderValues.Single, Size = 12, Color = "7C9885" },
        new LeftBorder { Val = BorderValues.Nil }, new RightBorder { Val = BorderValues.Nil },
        new InsideHorizontalBorder { Val = BorderValues.Nil },
        new InsideVerticalBorder { Val = BorderValues.Nil })));
table.Append(new TableGrid(            // REQUIRED — missing = Word crashes
    new GridColumn { Width = "3000" },
    new GridColumn { Width = "7000" }));
```

- `GridColumn.Width` MUST match each cell's `TableCellWidth.Width`.
- Header row: `Shading { Fill = "f0f4f2" }` + `Bold()` + bottom `BorderValues.Single Size=6`.
- `TableHeader()` goes inside **`TableRowProperties`**, NOT as a direct child of `TableRow`:
  ```csharp
  new TableRow(new TableRowProperties(new TableHeader()), new TableCell(...), ...)
  ```

**Merged cells**:

```csharp
// Horizontal: Restart → Continue
new TableCellProperties(new HorizontalMerge { Val = MergedCellValues.Restart })
new TableCellProperties(new HorizontalMerge { Val = MergedCellValues.Continue })
// Vertical: Restart → empty VerticalMerge (no Val = continue)
new TableCellProperties(new VerticalMerge { Val = MergedCellValues.Restart })
new TableCellProperties(new VerticalMerge())   // no Val = continue
// Diagonal border
new TopLeftToBottomRightCellBorder { Val = BorderValues.Single, Size = 4 }
```

GridColumn count = total logical columns even when merged. Continuation cells need an empty `Paragraph`.

### 4.8 Footnotes

```csharp
// 1. Create part with REQUIRED separators
var fnPart = mainPart.AddNewPart<FootnotesPart>();
fnPart.Footnotes = new Footnotes(
    new Footnote(new Paragraph(new Run(new SeparatorMark())))
    { Type = FootnoteEndnoteValues.Separator, Id = -1 },
    new Footnote(new Paragraph(new Run(new ContinuationSeparatorMark())))
    { Type = FootnoteEndnoteValues.ContinuationSeparator, Id = 0 });

// 2. Add note (id starts from 1)
fnPart.Footnotes.Append(new Footnote(
    new Paragraph(
        new Run(new RunProperties(new VerticalTextAlignment { Val = VerticalPositionValues.Superscript }),
                new FootnoteReferenceMark()),
        new Run(new Text(" Note text") { Space = SpaceProcessingModeValues.Preserve }))
) { Id = 1 });

// 3. Reference in body
paragraph.Append(new Run(
    new RunProperties(new VerticalTextAlignment { Val = VerticalPositionValues.Superscript }),
    new FootnoteReference { Id = 1 }));
```

Missing separators (id=-1, id=0) = footnotes don't render. Same pattern for endnotes (EndnotesPart + EndnoteReference).

**TRAP**: The footnote reference Run must be appended to the end of an existing body paragraph — never as a standalone paragraph. An orphan superscript "1" on its own line is a layout defect.

### 4.9 Hyperlinks & Cross-References

**Hyperlink** — relationship first, then reference:

```csharp
var relId = mainPart.AddHyperlinkRelationship(new Uri("https://example.com"), true).Id;
new Hyperlink(new Run(
    new RunProperties(new Color { Val = "0563C1" }, new Underline { Val = UnderlineValues.Single }),
    new Text("link text"))) { Id = relId }
```

**Cross-reference** — bookmark + REF field:

```csharp
// At target: BookmarkStart/End with matching Id
new BookmarkStart { Id = "100", Name = "Figure1" }
new BookmarkEnd { Id = "100" }

// At reference: REF field (same Begin/Code/Separate/End pattern as PAGE)
new FieldCode($" REF Figure1 \\h ") { Space = SpaceProcessingModeValues.Preserve }
```

### 4.10 Numbering (Lists)

```csharp
var numPart = mainPart.AddNewPart<NumberingDefinitionsPart>();
numPart.Numbering = new Numbering(
    new AbstractNum(new Level(
        new NumberingFormat { Val = NumberFormatValues.Decimal },
        new LevelText { Val = "%1." },
        new LevelJustification { Val = LevelJustificationValues.Left },
        new ParagraphProperties(new Indentation { Left = "720", Hanging = "360" })
    ) { LevelIndex = 0 }) { AbstractNumberId = 1 },
    new NumberingInstance(new AbstractNumId { Val = 1 }) { NumberID = 1 });

// Use: new NumberingProperties(new NumberingLevelReference { Val = 0 }, new NumberingId { Val = 1 })
```

### 4.11 CJK Text

Write Chinese characters and punctuation directly in C# strings. Use `\"` for double quotes inside strings. **Never use `\uXXXX` for any Chinese text.** See `CJKExample.cs` header for the full trap list.

`RunFonts` MUST set `EastAsia` on every style (Normal, Heading1/2/3, Caption — not just Normal):
```csharp
new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }
```

CJK body text: use `Indentation { FirstLine = "480" }` (2-character indent) on the Normal style. Override to `FirstLine = "0"` on headings, captions, centered elements, and table cells.

CJK large titles: add `Spacing { Val = 20-60 }` (character spacing in twips) to prevent full-width glyphs from appearing cramped at large font sizes.

Available: SimSun (宋体), SimHei (黑体), KaiTi (楷体), FangSong (仿宋), Microsoft YaHei (微软雅黑).

### 4.12 RTL / BiDi Text

Minimal pattern for Arabic, Hebrew, or mixed LTR+RTL documents:

```csharp
// RTL paragraph
new ParagraphProperties(new BiDi())
// RTL run
new RunProperties(new RightToLeft(), new RunFonts { ComplexScript = "Arial" })
```

Mixed content: wrap RTL runs with `RightToLeft()`, LTR runs without. Set `Languages { Bidi = "ar-SA" }` for Arabic language tagging.

### 4.13 Shapes Limitation

Word shapes (rounded rectangles, callout boxes, text boxes) require complex VML or DrawingML that is extremely error-prone to generate programmatically. **Use tables with borders, shading, and cell padding as visual alternatives.** This produces more reliable results with far less code.

### 4.12 Pagination & Units

| Property | Class | Effect |
|----------|-------|--------|
| Page break before | `PageBreakBefore` | Force new page |
| Keep with next | `KeepNext` | Heading stays with following paragraph |
| Keep lines | `KeepLines` | Don't split paragraph across pages |
| Table row break | `CantSplit { Val = false }` | Allow row to break |
| Repeat header | `TableHeader()` | Header row repeats across pages |

| Unit | Conversion | Example |
|------|-----------|---------|
| Twips (dxa) | 1/20 pt, 1440/inch | A4 width = 11906 |
| Half-points | font × 2 | 12pt = `"24"` |
| EMU | 914400/inch, 360000/cm | A4 = 7560000 × 10692000 |

### 4.13 Letterhead

Different first-page header via `TitlePage`. TRAP: `DifferentFirstPage` does NOT exist.

```csharp
new SectionProperties(
    new TitlePage(),
    new HeaderReference { Type = HeaderFooterValues.First, Id = firstPageHeaderId },
    new HeaderReference { Type = HeaderFooterValues.Default, Id = defaultHeaderId }, ...)
```

### 4.14 Background Images

When a document includes a cover, generate the background via Playwright (HTML/SVG → 2× scale PNG → insert as floating anchor §4.5).

**You must create each background from scratch.** The scripts in `scripts/generate_*.py` are style references only — read one to learn the HTML/SVG + Playwright screenshot technique, then write your OWN unique design. **Never call `generate_*.py` directly, never `subprocess.run` them, never reuse their PNG output.** Also never use user-uploaded images, stock photos, or any pre-existing file as a cover background.

Design flow:
1. Define the document's Colors class first (same hex values used everywhere)
2. Read ONE `generate_*.py` script to learn the SVG technique (radial-gradient, curves, filters, etc.)
3. Write new HTML/SVG from scratch — use the SAME hex values from your Colors class for the background
4. Screenshot with Playwright at 2× scale: `page.screenshot(path=output, clip={...})` at 794×1123px
5. Insert the PNG as a floating background (§4.5 CreateFloatingBackground)
6. Cover text colors must come from the same Colors class — ensure contrast with the background you just generated

In IPython: `subprocess.run(["python3", your_script, output_dir])` — sync Playwright can't run in existing event loop.

Style references (read for technique inspiration, do NOT call or reuse output):

| Script | Style | Good starting point for |
|--------|-------|------------------------|
| `generate_backgrounds.py` | Morandi soft curves | Gentle, organic designs |
| `generate_inkwash_backgrounds.py` | Ink wash turbulence | CJK literary, gray-scale |
| `generate_swiss_backgrounds.py` | Precise thin lines | Grid-based, minimal |
| `generate_geometric_backgrounds.py` | Overlapping arcs | Bold geometric patterns |
| `generate_gradient_backgrounds.py` | Smooth gradient bands | Elegant color transitions |
| `generate_formal_backgrounds.py` | Double border + ornaments | Structured frame designs |

**Cover text must be visually distinct from body text.** Use significantly larger font size (48-96 half-points), different weight, and generous spacing (SpacingBetweenLines Before="4000-6000") to push the title away from the top edge. The cover should feel like a separate visual space, not just a bigger version of the first body paragraph.

## 5. Quality Gate

1. Document opens without errors
2. OpenXML + business rule validation passes
3. Headers, footers, TOC, page numbers, images correctly positioned
4. No placeholder text remains

## 6. Further References

- Routing: `../SKILL.md`
- Editing existing documents: `wir-reference.md`
- Math equations (OMML): `omml-reference.md`
- Native Word charts (pie, bar, line): `chart-reference.md`
- Matplotlib charts: `matplotlib-guide.md`
- English document demo: `../assets/templates/Example.cs` **(read before writing English Program.cs)**
- Chinese/CJK document demo: `../assets/templates/CJKExample.cs` **(read before writing CJK Program.cs)**
