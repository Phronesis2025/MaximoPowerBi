/* ============================================================================
   QUERY: FactMeterReading
   ============================================================================ */
let
    Source = fnLoadCsv("METERREADING.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"ASSETNUM", type text}, {"SITEID", type text}, {"METERNAME", type text},
         {"READINGDATE", type datetime}, {"READING", type number},
         {"MEASUREUNITID", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"ASSETNUM", "SITEID", "METERNAME", "READINGDATE", "READING", "MEASUREUNITID"}),
    DateCol = Table.AddColumn(Kept, "ReadingDate",
        each Date.From([READINGDATE]), type date),
    Final = Table.RemoveColumns(DateCol, {"READINGDATE"})
in
    Final
