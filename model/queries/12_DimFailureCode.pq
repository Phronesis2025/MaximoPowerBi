/* ============================================================================
   QUERY: DimFailureCode
   Only PROBLEM-type codes are kept; this dimension joins to
   FactFailure[PROBLEMCODE]. Cause and remedy codes stay as fact attributes.
   ============================================================================ */
let
    Source = fnLoadCsv("FAILURECODE.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"FAILURECODE", type text}, {"DESCRIPTION", type text},
         {"PARENT", type text}, {"TYPE", type text}},
        pCulture
    ),
    Problems = Table.SelectRows(Typed, each [TYPE] = "PROBLEM"),
    Kept = Table.SelectColumns(Problems, {"FAILURECODE", "DESCRIPTION", "PARENT"}),
    Renamed = Table.RenameColumns(Kept,
        {{"FAILURECODE", "ProblemCode"}, {"DESCRIPTION", "ProblemName"},
         {"PARENT", "FailureClass"}})
in
    Renamed
