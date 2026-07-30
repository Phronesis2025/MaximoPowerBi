/* ============================================================================
   QUERY: FactFailure
   ============================================================================ */
let
    Source = fnLoadCsv("FAILUREREPORT.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"WONUM", type text}, {"ASSETNUM", type text}, {"LOCATION", type text},
         {"SITEID", type text}, {"FAILURECODE", type text}, {"PROBLEMCODE", type text},
         {"CAUSECODE", type text}, {"REMEDYCODE", type text},
         {"REPORTDATE", type datetime}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"WONUM", "ASSETNUM", "SITEID", "FAILURECODE", "PROBLEMCODE",
         "CAUSECODE", "REMEDYCODE", "REPORTDATE"}),
    DateCol = Table.AddColumn(Kept, "FailureDate",
        each Date.From([REPORTDATE]), type date),
    Final = Table.RemoveColumns(DateCol, {"REPORTDATE"})
in
    Final
