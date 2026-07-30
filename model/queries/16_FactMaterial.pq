/* ============================================================================
   QUERY: FactMaterial
   ============================================================================ */
let
    Source = fnLoadCsv("MATUSETRANS.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"MATUSETRANSID", Int64.Type}, {"WONUM", type text}, {"SITEID", type text},
         {"ITEMNUM", type text}, {"LOCATION", type text}, {"QUANTITY", type number},
         {"UNITCOST", type number}, {"LINECOST", type number},
         {"TRANSDATE", type datetime}, {"ISSUETYPE", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"MATUSETRANSID", "WONUM", "SITEID", "ITEMNUM", "LOCATION", "QUANTITY",
         "UNITCOST", "LINECOST", "TRANSDATE", "ISSUETYPE"}),
    TransDate = Table.AddColumn(Kept, "TransDate",
        each Date.From([TRANSDATE]), type date),
    Joined = Table.NestedJoin(TransDate, {"WONUM"}, FactWorkOrder, {"WONUM"},
        "wo", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "wo",
        {"WORKTYPE", "ASSETNUM"}, {"WORKTYPE", "ASSETNUM"}),
    Final = Table.RemoveColumns(Expanded, {"TRANSDATE"})
in
    Final
