// CJKExample.cs - Complete Chinese business document example
// Color: Mocha & Cream (暖棕金) — warm, professional, distinctly NOT blue/purple
//
// CJK patterns marked with "// CJK:" comments explaining WHY
//
// ============================================================================
// CJK-TRAP #1: 中文引号 → 用 \" 转义，禁止 \uXXXX
// ============================================================================
//   WRONG:  new Text("请点击"确定"按钮")       // CS1003! 引号断裂字符串
//   RIGHT:  new Text("请点击\"确定\"按钮")      // \" 安全转义
//
//   ⚠️ 禁止使用 \uXXXX 写任何中文内容！中文必须直接写汉字。
//
// ============================================================================
// CJK-TRAP #2: 中文标点泄露到 C# 语法位置 → CS1056
// ============================================================================
//   WRONG (Chinese punctuation in C# syntax positions):
//     CreateParagraph("hello"，"world")   // Chinese ， in parameter list
//     body.Append(para)；         // Chinese ； as statement terminator
//     CreateHeading1("标题"（"_Toc"）       // Chinese （） as function parens
//
//   Rule: ASCII " ' , ; ( ) { } for C# SYNTAX. Chinese 、，；（）for TEXT CONTENT.
// ============================================================================

using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using DW = DocumentFormat.OpenXml.Drawing.Wordprocessing;
using A = DocumentFormat.OpenXml.Drawing;
using PIC = DocumentFormat.OpenXml.Drawing.Pictures;
using C = DocumentFormat.OpenXml.Drawing.Charts;

namespace Docx;

public static class CJKExample
{
    // ========================================================================
    // Color Scheme — Mocha & Cream (暖棕金)
    // Warm browns convey stability; gold accents add premium feel.
    // NEVER use #FF0000/#0000FF — they look cheap. NEVER all-blue — that's AI slop.
    // ========================================================================
    private static class Colors
    {
        public const string Primary = "5D4037";       // Mocha — headings
        public const string Secondary = "795548";     // Warm brown — secondary
        public const string Accent = "D4A574";        // Caramel gold — highlights
        public const string Dark = "3E2723";           // Dark coffee — body text
        public const string Mid = "6D4C41";            // Medium brown
        public const string Light = "A1887F";          // Light brown — captions
        public const string Border = "D7CCC8";         // Cream border
        public const string TableHeader = "EFEBE9";    // Light cream bg
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
    // Styles — CJK: EastAsia font on every style, FirstLine indent on body
    // ========================================================================
    private static void AddStyles(MainDocumentPart mainPart)
    {
        var sp = mainPart.AddNewPart<StyleDefinitionsPart>();
        sp.Styles = new Styles();

        // CJK: FirstLine="480" = standard 2-char indent for Chinese body text
        sp.Styles.Append(new Style(
            new StyleName { Val = "Normal" },
            new StyleParagraphProperties(
                new SpacingBetweenLines { After = "160", Line = "360", LineRule = LineSpacingRuleValues.Auto },
                new Indentation { FirstLine = "480" }
            ),
            new StyleRunProperties(
                // CJK: All THREE font channels required. Without EastAsia, CJK renders in Calibri.
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new FontSize { Val = "21" },
                new Color { Val = Colors.Dark }
            )
        ) { Type = StyleValues.Paragraph, StyleId = "Normal", Default = true });

        // CJK: Explicit EastAsia on every heading — some renderers ignore inheritance
        sp.Styles.Append(CreateHeadingStyle("Heading1", "heading 1", 0, "36", Colors.Primary, "600", "240"));
        sp.Styles.Append(CreateHeadingStyle("Heading2", "heading 2", 1, "28", Colors.Dark, "400", "160"));
        sp.Styles.Append(CreateHeadingStyle("Heading3", "heading 3", 2, "24", Colors.Mid, "280", "120"));

        sp.Styles.Append(new Style(
            new StyleName { Val = "Caption" }, new BasedOn { Val = "Normal" },
            new StyleParagraphProperties(
                new Justification { Val = JustificationValues.Center },
                new Indentation { FirstLine = "0" },
                new SpacingBetweenLines { Before = "60", After = "320" }),
            new StyleRunProperties(new Color { Val = Colors.Light }, new FontSize { Val = "20" },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" })
        ) { Type = StyleValues.Paragraph, StyleId = "Caption" });

        sp.Styles.Append(CreateTocStyle("TOC1", "toc 1", true, "0", "200"));
        sp.Styles.Append(CreateTocStyle("TOC2", "toc 2", false, "360", "60"));
    }

    private static Style CreateHeadingStyle(string id, string name, int lvl, string sz, string color, string before, string after)
    {
        return new Style(
            new StyleName { Val = name }, new BasedOn { Val = "Normal" },
            new StyleParagraphProperties(
                new KeepNext(), new KeepLines(),
                new SpacingBetweenLines { Before = before, After = after },
                new Indentation { FirstLine = "0" },
                new OutlineLevel { Val = lvl }),
            new StyleRunProperties(new Bold(), new FontSize { Val = sz },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new Color { Val = color })
        ) { Type = StyleValues.Paragraph, StyleId = id };
    }

    private static Style CreateTocStyle(string id, string name, bool bold, string indent, string before)
    {
        var rpr = new StyleRunProperties(
            new Color { Val = bold ? Colors.Dark : Colors.Mid },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" });
        if (bold) rpr.Append(new Bold());
        return new Style(
            new StyleName { Val = name }, new BasedOn { Val = "Normal" },
            new StyleParagraphProperties(
                new Tabs(new TabStop { Val = TabStopValues.Right, Leader = TabStopLeaderCharValues.Dot, Position = 9350 }),
                new SpacingBetweenLines { Before = before, After = "60" },
                new Indentation { Left = indent, FirstLine = "0" }),
            rpr
        ) { Type = StyleValues.Paragraph, StyleId = id };
    }

    // ========================================================================
    // Cover — white text on dark background
    // ========================================================================
    private static void AddCoverSection(Body body, string coverBgId, ref uint prId)
    {
        body.Append(new Paragraph(new Run(CreateFloatingBackground(coverBgId, prId++, "CoverBg"))));
        body.Append(new Paragraph(new ParagraphProperties(new SpacingBetweenLines { Before = "5000" }), new Run()));

        // CJK: Spacing { Val = 40 } prevents cramped CJK titles at large sizes
        body.Append(new Paragraph(
            new ParagraphProperties(
                new Indentation { Left = "1200", Right = "1200" },
                new SpacingBetweenLines { After = "300" }),
            new Run(new RunProperties(
                    new FontSize { Val = "72" }, new Bold(),
                    new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                    new Color { Val = Colors.Dark },  // dark text on light background
                    new Spacing { Val = 40 }),
                new Text("2025年度业务分析报告"))));

        body.Append(new Paragraph(
            new ParagraphProperties(
                new Indentation { Left = "1200", Right = "1200" },
                new SpacingBetweenLines { After = "3000" }),
            new Run(new RunProperties(
                    new FontSize { Val = "24" },
                    new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                    new Color { Val = Colors.Mid },  // medium brown subtitle
                    new Spacing { Val = 20 }),
                new Text("营收增长与市场份额深度洞察"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new Indentation { Left = "1200" }),
            new Run(new RunProperties(new FontSize { Val = "20" },
                    new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                    new Color { Val = Colors.Light }),  // lighter department text
                new Text("战略分析部 | 2025年4月"))));

        // TRAP: "DifferentFirstPage" does NOT exist — use TitlePage
        body.Append(new Paragraph(new ParagraphProperties(new SectionProperties(
            new TitlePage(),
            new SectionType { Val = SectionMarkValues.NextPage },
            new PageSize { Width = (UInt32Value)(uint)A4W, Height = (UInt32Value)(uint)A4H },
            new PageMargin { Top = 0, Right = 0, Bottom = 0, Left = 0, Header = 0, Footer = 0 }))));
    }

    // ========================================================================
    // TOC — Chinese placeholder entries + update hint
    // ========================================================================
    private static void AddTocSection(Body body)
    {
        body.Append(CreateHeading1("目录", "_Toc000"));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { After = "300" }),
            new Run(new RunProperties(new Color { Val = Colors.Light }, new FontSize { Val = "18" },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
                new Text("右键目录，选择\"更新域\"刷新页码"))));

        body.Append(new Paragraph(
            new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }),
            new Run(new FieldCode(" TOC \\o \"1-3\" \\h \\z \\u ") { Space = SpaceProcessingModeValues.Preserve }),
            new Run(new FieldChar { FieldCharType = FieldCharValues.Separate })));

        string[,] toc = {
            { "一、执行摘要", "1", "3" }, { "二、营收数据分析", "1", "5" },
            { "2.1 季度营收对比", "2", "5" }, { "三、市场份额分析", "1", "7" },
            { "3.1 产品线市场占有率", "2", "7" }, { "3.2 产品线详细数据", "2", "8" },
            { "四、未来展望", "1", "9" },
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
    // Content — header, footer, body, charts, table, footnote
    // ========================================================================
    private static void AddContentSection(WordprocessingDocument doc, Body body,
        MainDocumentPart mainPart, string bgDir, ref uint prId)
    {
        // Header — right-aligned title
        var headerPart = mainPart.AddNewPart<HeaderPart>();
        var headerId = mainPart.GetIdOfPart(headerPart);
        headerPart.Header = new Header(new Paragraph(
            new ParagraphProperties(new Justification { Val = JustificationValues.Right }),
            new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
                new Text("2025年度业务分析报告"))));

        // Footer — "第 X 页 / 共 Y 页"
        // TRAP: each Run needs its OWN RunProperties — never share instances
        var footerPart = mainPart.AddNewPart<FooterPart>();
        var footerId = mainPart.GetIdOfPart(footerPart);
        var fp = new Paragraph(new ParagraphProperties(new Justification { Val = JustificationValues.Center }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new Text("第 ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldChar { FieldCharType = FieldCharValues.Begin }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldCode(" PAGE ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldChar { FieldCharType = FieldCharValues.Separate }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new Text("1")));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldChar { FieldCharType = FieldCharValues.End }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new Text(" 页 / 共 ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldChar { FieldCharType = FieldCharValues.Begin }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldCode(" NUMPAGES ") { Space = SpaceProcessingModeValues.Preserve }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldChar { FieldCharType = FieldCharValues.Separate }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new Text("1")));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new FieldChar { FieldCharType = FieldCharValues.End }));
        fp.Append(new Run(new RunProperties(new FontSize { Val = "18" }, new Color { Val = Colors.Light },
            new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
            new Text(" 页") { Space = SpaceProcessingModeValues.Preserve }));
        footerPart.Footer = new Footer(fp);

        // --- Body ---
        body.Append(CreateHeading1("一、执行摘要", "_Toc001"));
        body.Append(CreateParagraph("2025年度，公司各项业务指标均实现稳健增长。全年营收同比增长18.6%，其中第四季度表现尤为突出，单季营收首次突破2,100万元大关，创下历史新高。"));
        body.Append(CreateParagraph("董事长在年度总结中评价\"增长强劲、势头良好\"，并指出\"2026年将是关键的战略布局之年\"。核心策略包括：产品创新、渠道下沉、数字化转型（详见第四章）。"));
        // CJK: Footnote ref attaches to END of preceding paragraph, not as separate paragraph
        var fnPara = CreateParagraph("市场份额方面，产品A以35%的市场占有率继续保持行业领先地位，品牌影响力进一步增强。");
        AddFootnoteRef(doc, fnPara, mainPart, "数据来源：公司财务部 2025年度报告（内部审计版）");
        body.Append(fnPara);

        body.Append(CreateHeading1("二、营收数据分析", "_Toc002"));
        body.Append(CreateHeading2("2.1 季度营收对比"));
        body.Append(CreateParagraph("下图展示了2024年与2025年各季度的营收对比。2025年每个季度均实现同比正增长，Q4增速达11.1%。"));

        // Matplotlib chart (transparent bg)
        AddInlineImage(body, mainPart, Path.Combine(bgDir, "chart1.png"), "Revenue", ref prId);
        body.Append(CreateCaption("图1：2024-2025年季度营收对比"));

        body.Append(CreateParagraph("核心增长驱动因素包括：新产品线成功推出、渠道下沉策略深化，以及客户续约率从82%提升至91%。"));

        body.Append(CreateHeading1("三、市场份额分析", "_Toc003"));
        body.Append(CreateHeading2("3.1 产品线市场占有率"));
        body.Append(CreateParagraph("产品A凭借技术优势，以35%的市场份额稳居行业第一。产品C在新兴市场快速渗透，份额从12%提升至18%。"));

        // Matplotlib chart 2 (horizontal bar, transparent bg)
        AddInlineImage(body, mainPart, Path.Combine(bgDir, "chart2.png"), "MarketShare", ref prId);
        body.Append(CreateCaption("图2：2025年产品线市场份额分布"));

        body.Append(CreateHeading2("3.2 产品线详细数据"));
        body.Append(CreateDataTable());

        body.Append(CreateHeading1("四、未来展望", "_Toc004"));
        body.Append(CreateParagraph("展望2026年，公司将从三个方面发力：加速产品C布局（投入5,000万元研发）、深化数字化转型（提效15%+）、拓展东南亚市场。预计全年营收突破8,500万元。"));

        body.Append(CreateNumberedItem("加速产品C布局", "投入研发资金5,000万元，三年内份额提升至25%"));
        body.Append(CreateNumberedItem("深化数字化转型", "提升运营效率15%以上"));
        body.Append(CreateNumberedItem("拓展海外市场", "在东南亚建立首个区域运营中心"));

        // Content section break (NOT the last section, so must be in Paragraph)
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
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new Color { Val = Colors.Primary }),
                new Text("感谢阅读"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { Before = "400" },
                new Justification { Val = JustificationValues.Center }),
            new Run(new RunProperties(new FontSize { Val = "20" },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new Color { Val = Colors.Light }),
                new Text("战略分析部 | strategy@example.com"))));

        // Final SectionProperties on body
        body.Append(new SectionProperties(
            new PageSize { Width = (UInt32Value)(uint)A4W, Height = (UInt32Value)(uint)A4H },
            new PageMargin { Top = 0, Right = 0, Bottom = 0, Left = 0, Header = 0, Footer = 0 }));
    }

    // ========================================================================
    // Factory helpers — TRAP: never reuse OpenXmlElement instances
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
                new NumberingProperties(new NumberingLevelReference { Val = 0 }, new NumberingId { Val = 1 }),
                new Indentation { FirstLine = "0" }),
            new Run(new RunProperties(new Bold()), new Text(title + "——")),
            new Run(new Text(description)));
    }

    // --- Footnote (attaches to existing paragraph, not standalone) ---
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
            new Run(new RunProperties(new FontSize { Val = "18" },
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" }),
                new Text(" " + text) { Space = SpaceProcessingModeValues.Preserve }))) { Id = fnId });
        // Append footnote reference to the EXISTING paragraph (not a new one)
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
                new Indentation { FirstLine = "0" }, new SpacingBetweenLines { Before = "200", After = "80" }),
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
        tbl.Append(CreateTableRow(true, "产品线", "市场份额", "同比增长", "营收（万元）"));
        tbl.Append(CreateTableRow(false, "产品A", "35%", "+2.1%", "3,150"));
        tbl.Append(CreateTableRow(false, "产品B", "25%", "+3.5%", "2,250"));
        tbl.Append(CreateTableRow(false, "产品C", "18%", "+6.0%", "1,620"));
        tbl.Append(CreateTableRow(false, "其他", "22%", "+1.2%", "1,980"));
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
            var rpr = new RunProperties(
                new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri", EastAsia = "Microsoft YaHei" },
                new FontSize { Val = "20" }, new Color { Val = hdr ? Colors.Dark : Colors.Mid });
            if (hdr) rpr.Append(new Bold());
            row.Append(new TableCell(tcp, new Paragraph(
                new ParagraphProperties(new Justification { Val = JustificationValues.Center },
                    new Indentation { FirstLine = "0" }, new SpacingBetweenLines { Before = "40", After = "40" }),
                new Run(rpr, new Text(t)))));
        }
        return row;
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
