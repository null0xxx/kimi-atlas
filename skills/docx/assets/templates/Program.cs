// Program.cs — Model replaces this file entirely.
// Read Example.cs (English) or CJKExample.cs (Chinese) for complete patterns.
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using DW = DocumentFormat.OpenXml.Drawing.Wordprocessing;
using A = DocumentFormat.OpenXml.Drawing;
using PIC = DocumentFormat.OpenXml.Drawing.Pictures;

string outputFile = args.Length > 0 ? args[0] : "./Document.docx";

using var doc = WordprocessingDocument.Create(outputFile, WordprocessingDocumentType.Document);
var mainPart = doc.AddMainDocumentPart();
mainPart.Document = new Document(new Body());
var body = mainPart.Document.Body!;

body.Append(new Paragraph(new Run(new Text("Replace this file with your document code."))));

doc.Save();
Console.WriteLine($"Saved: {outputFile}");
