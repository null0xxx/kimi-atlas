# OMML Math — Reference

Read this when the task involves math equations in Word.

## Namespace Traps

These do **NOT** exist in `DocumentFormat.OpenXml.Math`:

| Wrong | Correct |
|-------|---------|
| `M.Bold` | `Bold()` from Wordprocessing |
| `M.OfficeMathParagraph` | `OfficeMathParagraph` (top-level, not `M.`) |
| `M.Paragraph` | `Paragraph` from Wordprocessing |

## Placement

- **Display math**: `new Paragraph(new M.OfficeMathParagraph(new M.OfficeMath(...)))`
- **Inline math**: `OfficeMath` is a **sibling** of `Run` in Paragraph, never a child of Run

```csharp
// Inline: text + math + text in one paragraph
new Paragraph(
    new Run(new Text("The value ") { Space = SpaceProcessingModeValues.Preserve }),
    new M.OfficeMath(new M.Subscript(
        new M.Base(MathRun("x")), new M.SubArgument(MathRun("i")))),
    new Run(new Text(" is positive.") { Space = SpaceProcessingModeValues.Preserve }))
```

## MathRun Helper

```csharp
static M.Run MathRun(string text) =>
    new M.Run(new M.RunProperties(new M.Text { Text = text }));
```

## Code Patterns

### Fraction + Superscript + Radical

```csharp
// Display: a/b + x² = √y
new Paragraph(new M.OfficeMathParagraph(new M.OfficeMath(
    new M.Fraction(new M.Numerator(MathRun("a")), new M.Denominator(MathRun("b"))),
    MathRun("+"),
    new M.Superscript(new M.Base(MathRun("x")), new M.SuperArgument(MathRun("2"))),
    MathRun("="),
    new M.Radical(
        new M.RadicalProperties(new M.HideDegree { Val = OnOffValue.FromBoolean(true) }),
        new M.Degree(),     // TRAP: MUST exist even when hidden — omit → validation error
        new M.Base(MathRun("y")))
)))
```

### Summation (Nary)

```csharp
// ∑(i=1 to n) aᵢ = S
new M.Nary(
    new M.NaryProperties(new M.AccentChar { Val = "∑" }),
    new M.SubArgument(MathRun("i=1")),
    new M.SuperArgument(MathRun("n")),
    new M.Base(new M.Subscript(
        new M.Base(MathRun("a")), new M.SubArgument(MathRun("i")))))
```

### Matrix with Brackets

```csharp
// [a b; c d]
new M.Delimiter(
    new M.DelimiterProperties(new M.BeginChar { Val = "[" }, new M.EndChar { Val = "]" }),
    new M.Base(new M.Matrix(
        new M.MatrixRow(new M.Base(MathRun("a")), new M.Base(MathRun("b"))),
        new M.MatrixRow(new M.Base(MathRun("c")), new M.Base(MathRun("d"))))))
```

### System of Equations

```csharp
// { x+y=5, x-y=1 } with left brace only
new M.Delimiter(
    new M.DelimiterProperties(new M.BeginChar { Val = "{" }, new M.EndChar { Val = "" }),
    new M.Base(new M.EquationArray(
        new M.Base(MathRun("x + y = 5")),
        new M.Base(MathRun("x - y = 1")))))
```

## Required Children & Ordering

Properties element (first child) is always optional. Other children are required in order:

| Container | Class | Children in order |
|-----------|-------|-------------------|
| Fraction | `Fraction` | Numerator, Denominator |
| Subscript | `Subscript` | Base, SubArgument |
| Superscript | `Superscript` | Base, SuperArgument |
| SubSuperscript | `SubSuperscript` | Base, SubArgument, SuperArgument |
| PreSubSuper | `PreSubSuper` | SubArgument, SuperArgument, Base (Base LAST) |
| Radical | `Radical` | Degree, Base |
| Nary (∑∫) | `Nary` | SubArgument, SuperArgument, Base |
| Delimiter | `Delimiter` | Base (one or more) |
| MathFunction | `MathFunction` | FunctionName, Base |
| LimitLower | `LimitLower` | Base, Limit |
| LimitUpper | `LimitUpper` | Base, Limit |
| Matrix | `Matrix` | MatrixRow (one or more) |
| EqArray | `EquationArray` | Base (one or more) |

**"Hidden ≠ absent"**: `HideDegree=true` hides display but `Degree()` must exist. Same for `SubHide`/`SupHide` in Nary.

## XML Name ↔ C# Class

For reading validation errors (Word reports XML names):

| C# | XML | C# | XML |
|----|-----|----|-----|
| `Base` | `m:e` | `Numerator` | `m:num` |
| `SubArgument` | `m:sub` | `Denominator` | `m:den` |
| `SuperArgument` | `m:sup` | `FunctionName` | `m:fName` |
| `Degree` | `m:deg` | `Limit` | `m:lim` |
| `OfficeMath` | `m:oMath` | `OfficeMathParagraph` | `m:oMathPara` |
