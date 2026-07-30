/* ============================================================================
   QUERY: FactDowntime
   DOWNTIME is ELAPSED wall-clock hours. Do not substitute ACTLABHRS - three
   technicians for four hours is 12 labour hours but 4 hours of downtime, and
   using labour hours inflates MTTR by roughly the crew size.
   ============================================================================ */
let
    Source = fnLoadCsv("DOWNTIMEREPORT.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"ASSETNUM", type text}, {"WONUM", type text}, {"SITEID", type text},
         {"DOWNTIMESTART", type datetime}, {"DOWNTIMEEND", type datetime},
         {"DOWNTIME", type number}, {"TYPE", type text}, {"PROBLEMCODE", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"ASSETNUM", "WONUM", "SITEID", "DOWNTIMESTART", "DOWNTIMEEND",
         "DOWNTIME", "TYPE", "PROBLEMCODE"}),
    DateCol = Table.AddColumn(Kept, "DowntimeStartDate",
        each Date.From([DOWNTIMESTART]), type date),
    Final = Table.RemoveColumns(DateCol, {"DOWNTIMESTART", "DOWNTIMEEND"})
in
    Final
