# Native Word Charts — Reference

Read this when creating pie, bar, or line charts in Word. For matplotlib-based charts (heatmaps, radar, etc.), see `matplotlib-guide.md`.

## Visibility Checklist

A chart requires ALL of these. Missing any one → invisible or corrupt:

1. `mainPart.AddNewPart<ChartPart>()` — creates chart XML part
2. `mainPart.GetIdOfPart(chartPart)` — gets rId
3. `new C.ChartReference { Id = chartId }` in Drawing — binds document to chart
4. `GraphicData.Uri = "http://schemas.openxmlformats.org/drawingml/2006/chart"` — exact string
5. `Extent.Cx/Cy > 0` (EMU) — zero = invisible
6. `EffectExtent` present even if all zeros

## Drawing Wrapper

All chart types use the same inline Drawing structure:

```csharp
var chartPart = mainPart.AddNewPart<ChartPart>();
string chartId = mainPart.GetIdOfPart(chartPart);
chartPart.ChartSpace = CreateChartSpace();  // see below

var drawing = new Drawing(new DW.Inline(
    new DW.Extent { Cx = 4572000, Cy = 3429000 },      // ~12×9 cm
    new DW.EffectExtent { LeftEdge = 0, TopEdge = 0, RightEdge = 0, BottomEdge = 0 },
    new DW.DocProperties { Id = uniqueId, Name = "Chart" },
    new DW.NonVisualGraphicFrameDrawingProperties(new A.GraphicFrameLocks { NoChangeAspect = true }),
    new A.Graphic(new A.GraphicData(
        new C.ChartReference { Id = chartId }
    ) { Uri = "http://schemas.openxmlformats.org/drawingml/2006/chart" })
) { DistanceFromTop = 0, DistanceFromBottom = 0, DistanceFromLeft = 0, DistanceFromRight = 0 });
```

## Pie Chart

```csharp
var chartSpace = new C.ChartSpace();
chartSpace.AddNamespaceDeclaration("c", "http://schemas.openxmlformats.org/drawingml/2006/chart");
chartSpace.AddNamespaceDeclaration("a", "http://schemas.openxmlformats.org/drawingml/2006/main");
var chart = new C.Chart();
var plotArea = new C.PlotArea();

var pieChart = new C.PieChart(new C.VaryColors { Val = true });
var series = new C.PieChartSeries();
series.Append(new C.Index { Val = 0 }, new C.Order { Val = 0 });
series.Append(new C.SeriesText(new C.NumericValue("Label")));

// Per-slice colors
series.Append(new C.DataPoint(new C.Index { Val = 0 }, new C.Bubble3D { Val = false },
    new C.ChartShapeProperties(new A.SolidFill(new A.RgbColorModelHex { Val = "7C9885" }))));

// Categories: StringReference > StringCache > PointCount + StringPoint[]
var catData = new C.CategoryAxisData();
var strCache = new C.StringCache(new C.PointCount { Val = 3 });
strCache.Append(new C.StringPoint(new C.NumericValue("A")) { Index = 0 });
strCache.Append(new C.StringPoint(new C.NumericValue("B")) { Index = 1 });
strCache.Append(new C.StringPoint(new C.NumericValue("C")) { Index = 2 });
catData.Append(new C.StringReference(strCache));
series.Append(catData);

// Values: NumberReference > NumberingCache > FormatCode + PointCount + NumericPoint[]
var valData = new C.Values();
var numCache = new C.NumberingCache(new C.FormatCode("General"), new C.PointCount { Val = 3 });
numCache.Append(new C.NumericPoint(new C.NumericValue("35")) { Index = 0 });
numCache.Append(new C.NumericPoint(new C.NumericValue("25")) { Index = 1 });
numCache.Append(new C.NumericPoint(new C.NumericValue("40")) { Index = 2 });
valData.Append(new C.NumberReference(numCache));
series.Append(valData);

pieChart.Append(series);
plotArea.Append(pieChart);
chart.Append(plotArea);
chart.Append(new C.Legend(new C.LegendPosition { Val = C.LegendPositionValues.Right },
    new C.Overlay { Val = false }));
chart.Append(new C.PlotVisibleOnly { Val = true });
chartSpace.Append(chart);
```

TRAP: Pie charts have NO axes — adding AxisId/CategoryAxis/ValueAxis corrupts the file.

## Bar/Column Chart

Same as pie except: uses `C.BarChart` + requires axes.

```csharp
var barChart = new C.BarChart(
    new C.BarDirection { Val = C.BarDirectionValues.Column },  // Column=vertical, Bar=horizontal
    new C.BarGrouping { Val = C.BarGroupingValues.Clustered },
    new C.VaryColors { Val = false });

var series = new C.BarChartSeries();
series.Append(new C.Index { Val = 0 }, new C.Order { Val = 0 });
series.Append(new C.SeriesText(new C.NumericValue("2024")));
series.Append(new C.ChartShapeProperties(new A.SolidFill(new A.RgbColorModelHex { Val = "7C9885" })));
// Categories + Values same as pie chart
series.Append(catData);
series.Append(valData);
barChart.Append(series);

// Axis IDs must match between chart and axis definitions
barChart.Append(new C.AxisId { Val = 1 });
barChart.Append(new C.AxisId { Val = 2 });
plotArea.Append(barChart);

plotArea.Append(new C.CategoryAxis(
    new C.AxisId { Val = 1 }, new C.Scaling(new C.Orientation { Val = C.OrientationValues.MinMax }),
    new C.Delete { Val = false }, new C.AxisPosition { Val = C.AxisPositionValues.Bottom },
    new C.TickLabelPosition { Val = C.TickLabelPositionValues.NextTo },
    new C.CrossingAxis { Val = 2 }, new C.Crosses { Val = C.CrossesValues.AutoZero }));

plotArea.Append(new C.ValueAxis(
    new C.AxisId { Val = 2 }, new C.Scaling(new C.Orientation { Val = C.OrientationValues.MinMax }),
    new C.Delete { Val = false }, new C.AxisPosition { Val = C.AxisPositionValues.Left },
    new C.MajorGridlines(),
    new C.NumberingFormat { FormatCode = "General", SourceLinked = true },
    new C.TickLabelPosition { Val = C.TickLabelPositionValues.NextTo },
    new C.CrossingAxis { Val = 1 }, new C.Crosses { Val = C.CrossesValues.AutoZero }));
```

## Line Chart

Same Drawing wrapper and axis pattern as Bar. Key differences: `C.LineChart` + `C.Marker` for visible data points.

```csharp
var lineChart = new C.LineChart(
    new C.Grouping { Val = C.GroupingValues.Standard },
    new C.VaryColors { Val = false });

var series = new C.LineChartSeries();
series.Append(new C.Index { Val = 0 }, new C.Order { Val = 0 });
series.Append(new C.SeriesText(new C.NumericValue("Revenue")));
series.Append(new C.ChartShapeProperties(
    new A.Outline(new A.SolidFill(new A.RgbColorModelHex { Val = "7C9885" }),
                  new A.Round()) { Width = 28575 }));  // 2.25pt line

// Marker — REQUIRED for visible data points (without it, only line is drawn)
series.Append(new C.Marker(
    new C.Symbol { Val = C.MarkerStyleValues.Circle },
    new C.Size { Val = 5 },
    new C.ChartShapeProperties(
        new A.SolidFill(new A.RgbColorModelHex { Val = "7C9885" }))));

// Categories + Values same pattern as pie/bar
series.Append(catData);
series.Append(valData);
lineChart.Append(series);

// Axes — same as bar chart
lineChart.Append(new C.AxisId { Val = 1 });
lineChart.Append(new C.AxisId { Val = 2 });
plotArea.Append(lineChart);
// CategoryAxis + ValueAxis same as bar chart
```

TRAP: Line chart without `C.Marker` → data points invisible, only the connecting line shows.

## Common Traps

| Trap | Symptom | Fix |
|------|---------|-----|
| Chart XML exists but no Drawing refs it | Invisible | Create Drawing with ChartReference |
| `chartRelId` hardcoded as `"rId1"` | Corrupt if other parts exist | Use `GetIdOfPart()` |
| Missing/mismatched axis IDs | Corrupt | AxisId values must match between chart and axis defs |
| Pie chart with axes | Corrupt | Pie = no AxisId, no axis definitions |
| Line chart without markers | Dots invisible | Add `C.Marker` for visible points |

## Chart Type Quick Reference

| Type | Class | Axes | Direction |
|------|-------|------|-----------|
| Column | `C.BarChart` + `Column` | Cat + Val | Vertical bars |
| Bar | `C.BarChart` + `Bar` | Cat + Val | Horizontal bars |
| Line | `C.LineChart` + `Grouping.Standard` | Cat + Val | Add `C.Marker` |
| Pie | `C.PieChart` | **None** | `VaryColors=true` |

## EMU Sizes

| Size | Cx | Cy |
|------|----|----|
| Full width (~14.4 cm) | 5486400 | 2743200 |
| Medium (~12 cm) | 4572000 | 3429000 |
| Half (~7.2 cm) | 2743200 | 2743200 |

1 cm = 360000 EMU. 1 inch = 914400 EMU.
