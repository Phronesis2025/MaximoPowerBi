/* ============================================================================
   QUERY: DimLocation
   ALL location types are kept, not just OPERATING, because FactMaterial
   references storeroom locations. IsOperating flags the difference.
   ============================================================================ */
let
    Source = fnLoadCsv("LOCATIONS.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"LOCATION", type text}, {"DESCRIPTION", type text}, {"SITEID", type text},
         {"TYPE", type text}, {"STATUS", type text}, {"PARENT", type text},
         {"GLACCOUNT", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"LOCATION", "DESCRIPTION", "SITEID", "TYPE", "STATUS", "PARENT", "GLACCOUNT"}),
    Flag = Table.AddColumn(Kept, "IsOperating",
        each if [TYPE] = "OPERATING" then 1 else 0, Int64.Type)
in
    Flag
