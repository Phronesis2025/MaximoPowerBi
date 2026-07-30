/* ============================================================================
   QUERY: FactLabour
   WORKTYPE is merged in from WORKORDER so labour can be split planned vs
   reactive WITHOUT a fact-to-fact relationship. See the header note.
   ============================================================================ */
let
    Source = fnLoadCsv("LABTRANS.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"LABTRANSID", Int64.Type}, {"WONUM", type text}, {"SITEID", type text},
         {"LABORCODE", type text}, {"CRAFT", type text}, {"TRANSDATE", type datetime},
         {"REGULARHRS", type number}, {"PREMIUMPAYHOURS", type number},
         {"PAYRATE", type number}, {"LINECOST", type number}, {"TRANSTYPE", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"LABTRANSID", "WONUM", "SITEID", "LABORCODE", "CRAFT", "TRANSDATE",
         "REGULARHRS", "PREMIUMPAYHOURS", "PAYRATE", "LINECOST", "TRANSTYPE"}),
    TransDate = Table.AddColumn(Kept, "TransDate",
        each Date.From([TRANSDATE]), type date),
    TotalHrs = Table.AddColumn(TransDate, "TotalHours",
        each [REGULARHRS] + [PREMIUMPAYHOURS], type number),
    // denormalise the work-order classification
    Joined = Table.NestedJoin(TotalHrs, {"WONUM"}, FactWorkOrder, {"WONUM"},
        "wo", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "wo",
        {"WORKTYPE", "ASSETNUM"}, {"WORKTYPE", "ASSETNUM"}),
    Final = Table.RemoveColumns(Expanded, {"TRANSDATE"})
in
    Final
