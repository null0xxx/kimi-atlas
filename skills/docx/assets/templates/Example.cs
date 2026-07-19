// Example.cs - Complete English business document example
// Color: Morandi Nordic (鼠尾草绿灰) — low saturation, calm, elegant
//
// TRAP comments explain common pitfalls. Copy structure freely.
// For native Word charts (pie/bar/line): see chart-reference.md
// For OMML math equations: see omml-reference.md

using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using System.Collections.Generic;
using DW = DocumentFormat.OpenXml.Drawing.Wordprocessing;
using A = DocumentFormat.OpenXml.Drawing;
using PIC = DocumentFormat.OpenXml.Drawing.Pictures;
using C = DocumentFormat.OpenXml.Drawing.Charts;

namespace Docx;

public static class Example
{
    // ========================================================================
    // Color Scheme — Morandi Nordic (低饱和绿灰)
    // Muted sage greens convey calm professionalism.
    // NEVER use pure #FF0000/#0000FF — they look cheap.
    // ========================================================================
    private static class Colors
    {
        public const string Primary = "7C9885";       // Sage green — headings
        public const string Secondary = "8B9DC3";     // Gray blue — accents
        public const string Accent = "9CAF88";        // Grass green — highlights
        public const string Dark = "2d3a35";           // Dark greenish gray — body text
        public const string Mid = "5a6b62";            // Medium — secondary text
        public const string Light = "8a9a90";          // Light — captions
        public const string Border = "d8e0dc";         // Table borders
        public const string TableHeader = "f0f4f2";    // Table header bg
    }

    private const int A4W = 11906;
    private const int A4H = 16838;
    private const long A4WE = 7560000L;
    private const long A4HE = 10692000L;

    public static void Generate(string outputPath, string bgDir)
    {
        using var doc = WordprocessingDocument.Create(outputPath, WordprocessingDocumentType.Document);
        var mainPart = doc.AddMainDocumentPart();
        mainPart.Document = new Document(new Body());
        var body = mainPart.Document.Body!;

        AddStyles(mainPart);
        AddNumbering(mainPart);

        var coverBgId = AddImage(mainPart, Path.Combine(bgDir, "cover_bg.png"));
        var backBgId = AddImage(mainPart, Path.Combine(bgDir, "backcover_bg.png"));

        uint prId = 1;
        AddCoverSection(body, coverBgId, ref prId);
        AddTocSection(body);
        AddContentSection(doc, body, mainPart, bgDir, ref prId);
        AddBackcoverSection(body, backBgId, ref prId);

        SetUpdateFieldsOnOpen(mainPart);
        doc.Save();
    }

    // ========================================================================
    // Styles
    // ========================================================================
    private static void AddStyles(MainDocumentPart mainPart)
    {
        var sp = mainPart.AddNewPart<StyleDefinitionsPart>();
        sp.Styles = new Styles();

        sp.Styles.Append(new Style(
            new StyleName { Val = "Normal" },
            new StyleParagraphProperties(
                new SpacingBetweenLines { After = "200", Line = "312", LineRule = LineSpacingRuleValues.Auto }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new FontSize { Val = "21" },
                new Color { Val = Colors.Dark })
        ) { Type = StyleValues.Paragraph, StyleId = "Normal", Default = true });

        sp.Styles.Append(CreateHeadingStyle("Heading1", "heading 1", 0, "36", Colors.Primary, "600", "240"));
        sp.Styles.Append(CreateHeadingStyle("Heading2", "heading 2", 1, "28", Colors.Dark, "400", "160"));
        sp.Styles.Append(CreateHeadingStyle("Heading3", "heading 3", 2, "24", Colors.Mid, "280", "120"));

        sp.Styles.Append(new Style(
            new StyleName { Val = "Caption" }, new BasedOn { Val = "Normal" },
            new StyleParagraphProperties(
                new Justification { Val = JustificationValues.Center },
                new SpacingBetweenLines { Before = "60", After = "320" }),
            new StyleRunProperties(new Color { Val = Colors.Light }, new FontSize { Val = "20" })
        ) { Type = StyleValues.Paragraph, StyleId = "Caption" });

        sp.Styles.Append(CreateTocStyle("TOC1", "toc 1", true, "0", "200"));
        sp.Styles.Append(CreateTocStyle("TOC2", "toc 2", false, "360", "60"));
    }

    private static Style CreateHeadingStyle(string id, string name, int level,
        string fontSize, string color, string spaceBefore, string spaceAfter)
    {
        return new Style(
            new StyleName { Val = name }, new BasedOn { Val = "Normal" },
            new StyleParagraphProperties(
                new KeepNext(), new KeepLines(),
                new SpacingBetweenLines { Before = spaceBefore, After = spaceAfter },
                new OutlineLevel { Val = level }),
            new StyleRunProperties(
                new Bold(), new FontSize { Val = fontSize },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new Color { Val = color })
        ) { Type = StyleValues.Paragraph, StyleId = id };
    }

    private static Style CreateTocStyle(string id, string name, bool bold, string indent, string before)
    {
        var rpr = new StyleRunProperties(new Color { Val = bold ? Colors.Dark : Colors.Mid });
        if (bold) rpr.Append(new Bold());
        return new Style(
            new StyleName { Val = name }, new BasedOn { Val = "Normal" },
            new StyleParagraphProperties(
                new Tabs(new TabStop { Val = TabStopValues.Right, Leader = TabStopLeaderCharValues.Dot, Position = 9350 }),
                new SpacingBetweenLines { Before = before, After = "60" },
                new Indentation { Left = indent }),
            rpr
        ) { Type = StyleValues.Paragraph, StyleId = id };
    }

    // ========================================================================
    // Cover — white text on dark background
    // ========================================================================
    private static void AddCoverSection(Body body, string coverBgId, ref uint prId)
    {
        body.Append(new Paragraph(new Run(CreateFloatingBackground(coverBgId, prId++, "CoverBg"))));
        body.Append(new Paragraph(new ParagraphProperties(new SpacingBetweenLines { Before = "6000" }), new Run()));

        body.Append(new Paragraph(
            new ParagraphProperties(
                new Justification { Val = JustificationValues.Left },
                new Indentation { Left = "1200", Right = "1200" },
                new SpacingBetweenLines { After = "400" }),
            new Run(new RunProperties(
                    new FontSize { Val = "96" },
                    new Color { Val = Colors.Dark },  // dark text on light Morandi background
                    new Spacing { Val = 40 }),
                new Text("Project Proposal"))));

        body.Append(new Paragraph(
            new ParagraphProperties(
                new Justification { Val = JustificationValues.Left },
                new Indentation { Left = "1200", Right = "1200" },
                new SpacingBetweenLines { After = "3000" }),
            new Run(new RunProperties(
                    new FontSize { Val = "24" },
                    new Color { Val = Colors.Mid },
                    new Spacing { Val = 40 }),
                new Text("Strategic Business Initiative"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new Indentation { Left = "1200" }),
            new Run(new RunProperties(new FontSize { Val = "20" }, new Color { Val = Colors.Light }),
                new Text("[Company Name]  |  2024.12"))));

        // TRAP: "DifferentFirstPage" does NOT exist — use TitlePage
        body.Append(new Paragraph(new ParagraphProperties(new SectionProperties(
            new TitlePage(),
            new SectionType { Val = SectionMarkValues.NextPage },
            new PageSize { Width = (UInt32Value)(uint)A4W, Height = (UInt32Value)(uint)A4H },
            new PageMargin { Top = 0, Right = 0, Bottom = 0, Left = 0, Header = 0, Footer = 0 }))));
    }

    // ========================================================================
    // TOC — with English placeholder entries + refresh hint
    // ========================================================================
    private static void AddTocSection(Body body)
    {
        body.Append(CreateHeading1("Table of Contents", "_Toc000"));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { After = "300" }),
            new Run(new RunProperties(new Color { Val = Colors.Light }, new FontSize { Val = "18" }),
                new Text("Right-click the TOC and select \"Update Field\" to refresh page numbers"))));

        body.Append(new Paragraph(
            new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }),
            new Run(new FieldCode(" TOC \\o \"1-3\" \\h \\z \\u ") { Space = SpaceProcessingModeValues.Preserve }),
            new Run(new FieldChar { FieldCharType = FieldCharValues.Separate })));

        string[,] toc = {
            { "Executive Summary", "1", "3" }, { "Market Analysis", "1", "5" },
            { "Quarterly Revenue", "2", "5" }, { "Market Share", "1", "7" },
            { "Product Breakdown", "2", "7" }, { "Detailed Metrics", "2", "8" },
            { "Strategic Outlook", "1", "9" },
        };
        for (int i = 0; i < toc.GetLength(0); i++)
            body.Append(new Paragraph(
                new ParagraphProperties(new ParagraphStyleId { Val = $"TOC{toc[i, 1]}" }),
                new Run(new Text(toc[i, 0])), new Run(new TabChar()), new Run(new Text(toc[i, 2]))));

        body.Append(new Paragraph(new Run(new FieldChar { FieldCharType = FieldCharValues.End })));

        body.Append(new Paragraph(new ParagraphProperties(new SectionProperties(
            new SectionType { Val = SectionMarkValues.NextPage },
            new PageSize { Width = (UInt32Value)(uint)A4W, Height = (UInt32Value)(uint)A4H },
            new PageMargin { Top = 1800, Right = 1440, Bottom = 1440, Left = 1440, Header = 720, Footer = 720 }))));
    }

    // ========================================================================
    // Content — header, footer, body, 2 matplotlib charts, table, footnote
    // For native Word charts (pie/bar/line), see chart-reference.md
    // ========================================================================
    private static void AddContentSection(WordprocessingDocument doc, Body body,
        MainDocumentPart mainPart, string bgDir, ref uint prId)
    {
        // Header — background image via HeaderPart (body pages can have bg this way)
        // TRAP: For body pages with margins, background goes in Header, not Body.
        //       Body-level floating images get clipped by page margins.
        var headerPart = mainPart.AddNewPart<HeaderPart>();
        var headerId = mainPart.GetIdOfPart(headerPart);
        var bodyBgPath = Path.Combine(bgDir, "body_bg.png");
        if (File.Exists(bodyBgPath))
        {
            var headerImagePart = headerPart.AddImagePart(ImagePartType.Png);
            using (var stream = new FileStream(bodyBgPath, FileMode.Open))
                headerImagePart.FeedData(stream);
            var headerImageId = headerPart.GetIdOfPart(headerImagePart);
            headerPart.Header = new Header(
                new Paragraph(new Run(CreateFloatingBackground(headerImageId, prId++, "BodyBg"))),
                new Paragraph(
                    new ParagraphProperties(new Justification { Val = JustificationValues.Right }),
                    new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
                        new Text("Project Proposal"))));
        }
        else
        {
            headerPart.Header = new Header(new Paragraph(
                new ParagraphProperties(new Justification { Val = JustificationValues.Right }),
                new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
                    new Text("Project Proposal"))));
        }

        // Footer — PAGE / NUMPAGES
        // TRAP: each Run needs its OWN RunProperties — never share instances
        var footerPart = mainPart.AddNewPart<FooterPart>();
        var footerId = mainPart.GetIdOfPart(footerPart);
        var fp = new Paragraph(new ParagraphProperties(new Justification { Val = JustificationValues.Center }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldChar { FieldCharType = FieldCharValues.Begin }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldCode(" PAGE ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldChar { FieldCharType = FieldCharValues.Separate }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new Text("1")));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldChar { FieldCharType = FieldCharValues.End }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new Text(" / ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldChar { FieldCharType = FieldCharValues.Begin }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldCode(" NUMPAGES ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldChar { FieldCharType = FieldCharValues.Separate }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new Text("1")));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light }),
            new FieldChar { FieldCharType = FieldCharValues.End }));
        footerPart.Footer = new Footer(fp);

        // --- Body ---
        body.Append(CreateHeading1("Executive Summary", "_Toc001"));
        body.Append(CreateParagraph("FY2025 was a landmark year. Total revenue grew 18.6% YoY, with Q4 setting a new quarterly record at $21M. Product A maintained market leadership at 35% share, while Product C emerged as the fastest-growing line (+50% YoY)."));
        var fnPara = CreateParagraph("This report analyzes revenue performance and market positioning across all product lines, providing data-driven recommendations for the FY2026 strategic plan.");
        AddFootnoteRef(doc, fnPara, mainPart, "Source: Finance Department FY2025 Annual Report (audited)");
        body.Append(fnPara);

        body.Append(CreateHeading1("Market Analysis", "_Toc002"));
        body.Append(CreateHeading2("Quarterly Revenue"));
        body.Append(CreateParagraph("The chart below compares quarterly revenue between FY2024 and FY2025. Every quarter showed positive YoY growth, with acceleration in H2."));

        // Matplotlib chart 1 (transparent bg, bar chart)
        // Charts should use: fig.savefig(path, dpi=300, transparent=True, bbox_inches='tight')
        AddInlineImage(body, mainPart, Path.Combine(bgDir, "chart1.png"), "Revenue", ref prId);
        body.Append(CreateCaption("Figure 1: FY2024 vs FY2025 Quarterly Revenue Comparison"));

        body.Append(CreateParagraph("Key growth drivers include: successful new product launch, channel expansion into tier-2/3 cities, and customer renewal rate improvement from 82% to 91%."));

        body.Append(CreateHeading1("Market Share", "_Toc003"));
        body.Append(CreateHeading2("Product Breakdown"));
        body.Append(CreateParagraph("Product A leads with 35% market share. Product C's rapid penetration in emerging markets pushed its share from 12% to 18%, making it the year's fastest-growing line."));

        // Matplotlib chart 2 (transparent bg, horizontal bar)
        AddInlineImage(body, mainPart, Path.Combine(bgDir, "chart2.png"), "MarketShare", ref prId);
        body.Append(CreateCaption("Figure 2: FY2025 Market Share by Product Line"));

        // Native Word pie chart (editable in Word, no external image needed)
        AddPieChart(body, mainPart, ref prId);
        body.Append(CreateCaption("Figure 3: Market Share Distribution"));

        body.Append(CreateHeading2("Detailed Metrics"));
        body.Append(CreateDataTable());

        body.Append(CreateHeading1("Strategic Outlook", "_Toc004"));
        body.Append(CreateParagraph("Three priorities for FY2026: accelerate Product C rollout ($50M R&D investment), deepen digital transformation (target 15%+ efficiency gain), and establish first Southeast Asia regional hub. Full-year revenue target: $85M."));

        body.Append(CreateNumberedItem("Accelerate Product C", "Invest $50M in R&D; target 25% market share within 3 years"));
        body.Append(CreateNumberedItem("Digital Transformation", "Target 15%+ improvement in operational efficiency"));
        body.Append(CreateNumberedItem("International Expansion", "Establish first regional operations center in Southeast Asia"));

        // Content section break
        body.Append(new Paragraph(new ParagraphProperties(new SectionProperties(
            new HeaderReference { Type = HeaderFooterValues.Default, Id = headerId },
            new FooterReference { Type = HeaderFooterValues.Default, Id = footerId },
            new PageSize { Width = (UInt32Value)(uint)A4W, Height = (UInt32Value)(uint)A4H },
            new PageMargin { Top = 1800, Right = 1440, Bottom = 1440, Left = 1440, Header = 720, Footer = 720 }))));
    }

    // ========================================================================
    // Backcover — white text on dark background
    // ========================================================================
    private static void AddBackcoverSection(Body body, string backBgId, ref uint prId)
    {
        body.Append(new Paragraph(new Run(CreateFloatingBackground(backBgId, prId++, "BackBg"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { Before = "7000" },
                new Justification { Val = JustificationValues.Center }),
            new Run(new RunProperties(new FontSize { Val = "48" }, new Bold(),
                new Color { Val = Colors.Primary }),
                new Text("Thank You"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { Before = "400" },
                new Justification { Val = JustificationValues.Center }),
            new Run(new RunProperties(new FontSize { Val = "20" }, new Color { Val = Colors.Light }),
                new Text("contact@company.com  ·  +1 (555) 123-4567"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { Before = "200" },
                new Justification { Val = JustificationValues.Center }),
            new Run(new RunProperties(new FontSize { Val = "16" }, new Color { Val = Colors.Light }),
                new Text("© 2024 [Company Name]"))));

        // Final SectionProperties on body
        body.Append(new SectionProperties(
            new PageSize { Width = (UInt32Value)(uint)A4W, Height = (UInt32Value)(uint)A4H },
            new PageMargin { Top = 0, Right = 0, Bottom = 0, Left = 0, Header = 0, Footer = 0 }));
    }

    // ========================================================================
    // Factory helpers — TRAP: never reuse OpenXmlElement instances
    // Each call creates NEW elements. Sharing one RunProperties across
    // multiple Runs throws: "Cannot insert element because it is part of a tree."
    // Use factory methods (like these) or CloneNode(true).
    // ========================================================================

    private static int _bookmarkId = 0;

    private static Paragraph CreateHeading1(string text, string bookmarkName)
    {
        int id = ++_bookmarkId;
        return new Paragraph(
            new ParagraphProperties(new ParagraphStyleId { Val = "Heading1" }),
            new BookmarkStart { Id = id.ToString(), Name = bookmarkName },
            new Run(new Text(text)),
            new BookmarkEnd { Id = id.ToString() });
    }

    private static Paragraph CreateHeading2(string text)
    {
        return new Paragraph(
            new ParagraphProperties(new ParagraphStyleId { Val = "Heading2" }),
            new Run(new Text(text)));
    }

    private static Paragraph CreateParagraph(string text)
    {
        return new Paragraph(new Run(new Text(text)));
    }

    private static Paragraph CreateCaption(string text)
    {
        return new Paragraph(
            new ParagraphProperties(new ParagraphStyleId { Val = "Caption" }),
            new Run(new Text(text)));
    }

    private static Paragraph CreateNumberedItem(string title, string description)
    {
        return new Paragraph(
            new ParagraphProperties(
                new NumberingProperties(new NumberingLevelReference { Val = 0 }, new NumberingId { Val = 1 })),
            new Run(new RunProperties(new Bold()), new Text(title + " — ")),
            new Run(new Text(description)));
    }

    // --- Footnote (attaches to existing paragraph) ---
    private static void AddFootnoteRef(WordprocessingDocument doc, Paragraph para, MainDocumentPart mp, string text)
    {
        var fnp = mp.FootnotesPart ?? mp.AddNewPart<FootnotesPart>();
        if (fnp.Footnotes == null)
            fnp.Footnotes = new Footnotes(
                new Footnote(new Paragraph(new Run(new SeparatorMark()))) { Type = FootnoteEndnoteValues.Separator, Id = -1 },
                new Footnote(new Paragraph(new Run(new ContinuationSeparatorMark()))) { Type = FootnoteEndnoteValues.ContinuationSeparator, Id = 0 });
        int fnId = (int)(fnp.Footnotes.Elements<Footnote>().Max(fn => fn.Id?.Value ?? 0) + 1);
        fnp.Footnotes.Append(new Footnote(new Paragraph(
            new Run(new RunProperties(new VerticalTextAlignment { Val = VerticalPositionValues.Superscript }), new FootnoteReferenceMark()),
            new Run(new RunProperties(new FontSize { Val = "18" }), new Text(" " + text) { Space = SpaceProcessingModeValues.Preserve }))) { Id = fnId });
        para.Append(new Run(new RunProperties(new VerticalTextAlignment { Val = VerticalPositionValues.Superscript }),
            new FootnoteReference { Id = fnId }));
    }

    // --- Image helpers ---
    private static string AddImage(MainDocumentPart mp, string path)
    {
        var ip = mp.AddImagePart(ImagePartType.Png);
        using var fs = new FileStream(path, FileMode.Open);
        ip.FeedData(fs); return mp.GetIdOfPart(ip);
    }

    private static Drawing CreateFloatingBackground(string imgId, uint prId, string name)
    {
        return new Drawing(new DW.Anchor(
            new DW.SimplePosition { X = 0, Y = 0 },
            new DW.HorizontalPosition(new DW.PositionOffset("0")) { RelativeFrom = DW.HorizontalRelativePositionValues.Page },
            new DW.VerticalPosition(new DW.PositionOffset("0")) { RelativeFrom = DW.VerticalRelativePositionValues.Page },
            new DW.Extent { Cx = A4WE, Cy = A4HE },
            new DW.EffectExtent { LeftEdge = 0, TopEdge = 0, RightEdge = 0, BottomEdge = 0 },
            new DW.WrapNone(),
            new DW.DocProperties { Id = prId, Name = name },
            new DW.NonVisualGraphicFrameDrawingProperties(new A.GraphicFrameLocks { NoChangeAspect = true }),
            new A.Graphic(new A.GraphicData(
                new PIC.Picture(
                    new PIC.NonVisualPictureProperties(
                        new PIC.NonVisualDrawingProperties { Id = 0, Name = $"{name}.png" },
                        new PIC.NonVisualPictureDrawingProperties()),
                    new PIC.BlipFill(new A.Blip { Embed = imgId }, new A.Stretch(new A.FillRectangle())),
                    new PIC.ShapeProperties(
                        new A.Transform2D(new A.Offset { X = 0, Y = 0 }, new A.Extents { Cx = A4WE, Cy = A4HE }),
                        new A.PresetGeometry { Preset = A.ShapeTypeValues.Rectangle })))
            { Uri = "http://schemas.openxmlformats.org/drawingml/2006/picture" }))
        { DistanceFromTop = 0, DistanceFromBottom = 0, DistanceFromLeft = 0, DistanceFromRight = 0,
          SimplePos = false, RelativeHeight = 251658240, BehindDoc = true,
          Locked = false, LayoutInCell = true, AllowOverlap = true });
    }

    private static void AddInlineImage(Body body, MainDocumentPart mainPart, string imagePath, string altText, ref uint docPrId, int maxWidthCm = 15)
    {
        if (!File.Exists(imagePath)) { Console.Error.WriteLine($"WARNING: Image not found: {imagePath}"); return; }
        var imagePart = mainPart.AddImagePart(ImagePartType.Png);
        byte[] imageBytes = File.ReadAllBytes(imagePath);
        using (var ms = new MemoryStream(imageBytes)) imagePart.FeedData(ms);
        var imageId = mainPart.GetIdOfPart(imagePart);

        // Read actual image dimensions from PNG header (bytes 16-23, big-endian)
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

        // Calculate display dimensions preserving aspect ratio
        long maxWidthEmu = maxWidthCm * 360000L;  // 1 cm = 360000 EMU
        long cx = maxWidthEmu;
        long cy = (long)(cx * ((double)imgHeight / imgWidth));
        var id = docPrId++;
        body.Append(new Paragraph(
            new ParagraphProperties(new KeepNext(), new Justification { Val = JustificationValues.Center },
                new SpacingBetweenLines { Before = "200", After = "80" }),
            new Run(new Drawing(new DW.Inline(
                new DW.Extent { Cx = cx, Cy = cy },
                new DW.EffectExtent { LeftEdge = 0, TopEdge = 0, RightEdge = 0, BottomEdge = 0 },
                new DW.DocProperties { Id = id, Name = altText },
                new DW.NonVisualGraphicFrameDrawingProperties(new A.GraphicFrameLocks { NoChangeAspect = true }),
                new A.Graphic(new A.GraphicData(
                    new PIC.Picture(
                        new PIC.NonVisualPictureProperties(
                            new PIC.NonVisualDrawingProperties { Id = 0, Name = $"{altText}.png" },
                            new PIC.NonVisualPictureDrawingProperties()),
                        new PIC.BlipFill(new A.Blip { Embed = imageId }, new A.Stretch(new A.FillRectangle())),
                        new PIC.ShapeProperties(
                            new A.Transform2D(new A.Offset { X = 0, Y = 0 }, new A.Extents { Cx = cx, Cy = cy }),
                            new A.PresetGeometry { Preset = A.ShapeTypeValues.Rectangle })))
                { Uri = "http://schemas.openxmlformats.org/drawingml/2006/picture" }))
            { DistanceFromTop = 0, DistanceFromBottom = 0, DistanceFromLeft = 0, DistanceFromRight = 0 }))));
    }

    // --- Table ---
    private static Table CreateDataTable()
    {
        var tbl = new Table(new TableProperties(
            new TableWidth { Width = "5000", Type = TableWidthUnitValues.Pct },
            new TableBorders(
                new TopBorder { Val = BorderValues.Single, Size = 12, Color = Colors.Primary },
                new BottomBorder { Val = BorderValues.Single, Size = 12, Color = Colors.Primary },
                new InsideHorizontalBorder { Val = BorderValues.Single, Size = 4, Color = Colors.Border })),
            new TableGrid(new GridColumn { Width = "2500" }, new GridColumn { Width = "2000" },
                new GridColumn { Width = "2000" }, new GridColumn { Width = "2500" }));
        tbl.Append(CreateTableRow(true, "Product", "Market Share", "YoY Growth", "Revenue ($K)"));
        tbl.Append(CreateTableRow(false, "Product A", "35%", "+2.1%", "3,150"));
        tbl.Append(CreateTableRow(false, "Product B", "25%", "+3.5%", "2,250"));
        tbl.Append(CreateTableRow(false, "Product C", "18%", "+6.0%", "1,620"));
        tbl.Append(CreateTableRow(false, "Others", "22%", "+1.2%", "1,980"));
        return tbl;
    }

    private static TableRow CreateTableRow(bool hdr, params string[] cells)
    {
        var row = new TableRow();
        if (hdr) row.Append(new TableRowProperties(new TableHeader()));
        foreach (var t in cells)
        {
            var tcp = new TableCellProperties(new TableCellWidth { Width = "0", Type = TableWidthUnitValues.Auto });
            if (hdr) tcp.Append(new Shading { Val = ShadingPatternValues.Clear, Fill = Colors.TableHeader });
            var rpr = new RunProperties(new FontSize { Val = "20" }, new Color { Val = hdr ? Colors.Dark : Colors.Mid });
            if (hdr) rpr.Append(new Bold());
            row.Append(new TableCell(tcp, new Paragraph(
                new ParagraphProperties(new Justification { Val = JustificationValues.Center },
                    new SpacingBetweenLines { Before = "40", After = "40" }),
                new Run(rpr, new Text(t)))));
        }
        return row;
    }

    // ========================================================================
    // Native Word Pie Chart — for bar/line charts see chart-reference.md
    // TRAP: Pie charts have NO axes — adding AxisId/CategoryAxis corrupts the file.
    // ========================================================================
    private static void AddPieChart(Body body, MainDocumentPart mainPart, ref uint docPrId)
    {
        var chartPart = mainPart.AddNewPart<ChartPart>();
        string chartId = mainPart.GetIdOfPart(chartPart);

        var chartSpace = new C.ChartSpace();
        chartSpace.AddNamespaceDeclaration("c", "http://schemas.openxmlformats.org/drawingml/2006/chart");
        chartSpace.AddNamespaceDeclaration("a", "http://schemas.openxmlformats.org/drawingml/2006/main");

        var chart = new C.Chart();
        var plotArea = new C.PlotArea();
        var pieChart = new C.PieChart(new C.VaryColors { Val = true });

        var series = new C.PieChartSeries();
        series.Append(new C.Index { Val = 0 });
        series.Append(new C.Order { Val = 0 });
        series.Append(new C.SeriesText(new C.NumericValue("Market Share")));

        // Per-slice colors — use document's palette, not rainbow
        string[] sliceColors = { Colors.Primary, Colors.Secondary, Colors.Accent, "B4A992", "C9A9A6" };
        string[] categories = { "Product A", "Product B", "Product C", "Product D", "Others" };
        double[] values = { 35, 25, 20, 12, 8 };

        for (uint i = 0; i < sliceColors.Length; i++)
        {
            series.Append(new C.DataPoint(
                new C.Index { Val = i },
                new C.Bubble3D { Val = false },
                new C.ChartShapeProperties(
                    new A.SolidFill(new A.RgbColorModelHex { Val = sliceColors[i] }))));
        }

        // Category data: StringReference > StringCache > PointCount + StringPoint[]
        var categoryData = new C.CategoryAxisData();
        var strCache = new C.StringCache(new C.PointCount { Val = (uint)categories.Length });
        for (int i = 0; i < categories.Length; i++)
            strCache.Append(new C.StringPoint(new C.NumericValue(categories[i])) { Index = (uint)i });
        categoryData.Append(new C.StringReference(strCache));
        series.Append(categoryData);

        // Values data: NumberReference > NumberingCache > FormatCode + PointCount + NumericPoint[]
        var valuesData = new C.Values();
        var numCache = new C.NumberingCache(
            new C.FormatCode("General"),
            new C.PointCount { Val = (uint)values.Length });
        for (int i = 0; i < values.Length; i++)
            numCache.Append(new C.NumericPoint(new C.NumericValue(values[i].ToString())) { Index = (uint)i });
        valuesData.Append(new C.NumberReference(numCache));
        series.Append(valuesData);

        pieChart.Append(series);
        plotArea.Append(pieChart);
        chart.Append(plotArea);
        chart.Append(new C.Legend(
            new C.LegendPosition { Val = C.LegendPositionValues.Right },
            new C.Overlay { Val = false }));
        chart.Append(new C.PlotVisibleOnly { Val = true });
        chartSpace.Append(chart);
        chartPart.ChartSpace = chartSpace;

        // Inline chart Drawing — same wrapper as images but with ChartReference
        var id = docPrId++;
        var drawing = new Drawing(
            new DW.Inline(
                new DW.Extent { Cx = 4572000, Cy = 3429000 },  // ~12x9 cm
                new DW.EffectExtent { LeftEdge = 0, TopEdge = 0, RightEdge = 0, BottomEdge = 0 },
                new DW.DocProperties { Id = id, Name = "PieChart" },
                new DW.NonVisualGraphicFrameDrawingProperties(new A.GraphicFrameLocks { NoChangeAspect = true }),
                new A.Graphic(new A.GraphicData(
                    new C.ChartReference { Id = chartId })
                { Uri = "http://schemas.openxmlformats.org/drawingml/2006/chart" }))
            { DistanceFromTop = 0, DistanceFromBottom = 0, DistanceFromLeft = 0, DistanceFromRight = 0 });

        body.Append(new Paragraph(
            new ParagraphProperties(new Justification { Val = JustificationValues.Center }),
            new Run(drawing)));
    }

    // ========================================================================
    // Cross-Reference — hyperlink to a bookmark via REF field
    // Usage: paragraph.Append(CreateCrossReference("Figure1", "Figure 1").ToArray());
    // ========================================================================
    private static IEnumerable<Run> CreateCrossReference(string bookmarkName, string displayText)
    {
        yield return new Run(new FieldChar { FieldCharType = FieldCharValues.Begin });
        yield return new Run(new FieldCode($" REF {bookmarkName} \\h ") { Space = SpaceProcessingModeValues.Preserve });
        yield return new Run(new FieldChar { FieldCharType = FieldCharValues.Separate });
        yield return new Run(new RunProperties(new Color { Val = Colors.Primary }), new Text(displayText));
        yield return new Run(new FieldChar { FieldCharType = FieldCharValues.End });
    }

    // --- Settings & Numbering ---
    private static void SetUpdateFieldsOnOpen(MainDocumentPart mp)
    {
        var sp = mp.DocumentSettingsPart ?? mp.AddNewPart<DocumentSettingsPart>();
        sp.Settings = new Settings(new UpdateFieldsOnOpen { Val = true }, new DisplayBackgroundShape());
    }

    private static void AddNumbering(MainDocumentPart mp)
    {
        var np = mp.AddNewPart<NumberingDefinitionsPart>();
        np.Numbering = new Numbering(
            new AbstractNum(new Level(
                new NumberingFormat { Val = NumberFormatValues.Decimal },
                new LevelText { Val = "%1." },
                new LevelJustification { Val = LevelJustificationValues.Left },
                new ParagraphProperties(new Indentation { Left = "720", Hanging = "360" })
            ) { LevelIndex = 0 }) { AbstractNumberId = 1 },
            new NumberingInstance(new AbstractNumId { Val = 1 }) { NumberID = 1 });
    }
}
