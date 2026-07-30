/* ============================================================================
   QUERY: DimItem
   ============================================================================ */
let
    Source = fnLoadCsv("ITEM.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"ITEMNUM", type text}, {"DESCRIPTION", type text}, {"ISSUEUNIT", type text},
         {"COMMODITYGROUP", type text}, {"ROTATING", Int64.Type}, {"STATUS", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"ITEMNUM", "DESCRIPTION", "ISSUEUNIT", "COMMODITYGROUP", "ROTATING", "STATUS"}),
    Renamed = Table.RenameColumns(Kept, {{"DESCRIPTION", "ItemName"}})
in
    Renamed
