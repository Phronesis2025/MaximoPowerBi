/* ============================================================================
   QUERY: DimDate
   Mark as a date table on [Date] after loading.
   ============================================================================ */
let
    Source = fnLoadCsv("DIM_DATE.csv"),
    Renamed = Table.RenameColumns(Source, {{"DATE", "Date"}}),
    Typed = Table.TransformColumnTypes(
        Renamed,
        {
            {"Date", type date},
            {"YEAR", Int64.Type},
            {"QUARTER", type text},
            {"MONTHNUM", Int64.Type},
            {"MONTHSHORT", type text},
            {"YEARMONTH", type text},
            {"MONTHYEARLABEL", type text},
            {"ISOWEEK", Int64.Type},
            {"DAYOFWEEK", Int64.Type},
            {"DAYSHORT", type text},
            {"ISWEEKEND", Int64.Type},
            {"FISCALYEAR", Int64.Type},
            {"FISCALPERIOD", Int64.Type},
            {"ISPASTORTODAY", Int64.Type}
        },
        pCulture
    ),
    // sort keys so month names order chronologically, not alphabetically
    WithSort = Table.AddColumn(Typed, "MonthSort",
        each [YEAR] * 100 + [MONTHNUM], Int64.Type)
in
    WithSort
