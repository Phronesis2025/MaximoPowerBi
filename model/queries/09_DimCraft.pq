/* ============================================================================
   QUERY: DimCraft
   ============================================================================ */
let
    Source = fnLoadCsv("CRAFT.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"CRAFT", type text}, {"DESCRIPTION", type text}, {"ORGID", type text},
         {"STDRATE", type number}, {"PREMIUMRATE", type number}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed, {"CRAFT", "DESCRIPTION", "STDRATE", "PREMIUMRATE"}),
    Renamed = Table.RenameColumns(Kept, {{"DESCRIPTION", "CraftName"}})
in
    Renamed
