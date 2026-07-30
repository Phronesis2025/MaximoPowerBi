/* ============================================================================
   QUERY: DimSite
   ============================================================================ */
let
    Source = fnLoadCsv("SITE.csv"),
    Org = fnLoadCsv("ORGANIZATION.csv"),
    Merged = Table.NestedJoin(Source, {"ORGID"}, Org, {"ORGID"}, "org", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Merged, "org", {"DESCRIPTION"}, {"OrgDescription"}),
    Typed = Table.TransformColumnTypes(
        Expanded,
        {{"SITEID", type text}, {"ORGID", type text}, {"DESCRIPTION", type text},
         {"CITY", type text}, {"STATE", type text}, {"OrgDescription", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"SITEID", "DESCRIPTION", "ORGID", "OrgDescription", "CITY", "STATE"}),
    Renamed = Table.RenameColumns(Kept, {{"DESCRIPTION", "SiteName"}})
in
    Renamed
