/* ============================================================================
   QUERY: DimFailureCode
   Only PROBLEM-type codes are kept; this dimension joins to
   FactFailure[PROBLEMCODE]. Cause and remedy codes stay as fact attributes.

   PARENT (failure class) is deliberately dropped: 6 of 45 problem codes appear
   under two failure classes (e.g. OVERHEAT under both FC-PUMP and FC-MOTOR),
   so keeping it makes ProblemCode non-unique and Power BI rejects the one side
   of the relationship to FactFailure[PROBLEMCODE]. Duplicate codes carry
   identical descriptions, so the distinct on ProblemCode is lossless.
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
    Kept = Table.SelectColumns(Problems, {"FAILURECODE", "DESCRIPTION"}),
    Renamed = Table.RenameColumns(Kept,
        {{"FAILURECODE", "ProblemCode"}, {"DESCRIPTION", "ProblemName"}}),
    Distinct = Table.Distinct(Renamed, {"ProblemCode"})
in
    Distinct
