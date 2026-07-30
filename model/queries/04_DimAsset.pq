/* ============================================================================
   QUERY: DimAsset
   Includes an "(none)" unknown member so location-only work orders are not
   silently dropped from asset-sliced visuals.
   ============================================================================ */
let
    Source = fnLoadCsv("ASSET.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"ASSETNUM", type text},
            {"DESCRIPTION", type text},
            {"SITEID", type text},
            {"LOCATION", type text},
            {"PARENT", type text},
            {"STATUS", type text},
            {"ASSETTYPE", type text},
            {"MANUFACTURER", type text},
            {"INSTALLDATE", type date},
            {"REPLACECOST", type number},
            {"CRITICALITY", Int64.Type}
        },
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"ASSETNUM", "DESCRIPTION", "SITEID", "LOCATION", "PARENT", "STATUS",
         "ASSETTYPE", "MANUFACTURER", "INSTALLDATE", "REPLACECOST", "CRITICALITY"}),
    // blank PARENT means top of the hierarchy, not missing data
    CleanParent = Table.TransformColumns(Kept,
        {{"PARENT", each if _ = null or _ = "" then null else _, type text}}),
    Label = Table.AddColumn(CleanParent, "CriticalityLabel",
        each if [CRITICALITY] = 1 then "1 - Critical"
        else if [CRITICALITY] = 2 then "2 - High"
        else if [CRITICALITY] = 3 then "3 - Medium"
        else "4 - Low", type text),
    Age = Table.AddColumn(Label, "AssetAgeYears",
        each if [INSTALLDATE] = null then null
        else Number.Round(Duration.Days(Date.From(DateTime.LocalNow()) - [INSTALLDATE]) / 365.25, 1),
        type number),
    // unknown member for location-only work
    WithUnknown = Table.InsertRows(Age, 0, {[
        ASSETNUM = "(none)",
        DESCRIPTION = "No asset - location-only work order",
        SITEID = null,
        LOCATION = null,
        PARENT = null,
        STATUS = "N/A",
        ASSETTYPE = "N/A",
        MANUFACTURER = null,
        INSTALLDATE = null,
        REPLACECOST = 0,
        CRITICALITY = null,
        CriticalityLabel = "Not applicable",
        AssetAgeYears = null
    ]})
in
    WithUnknown
