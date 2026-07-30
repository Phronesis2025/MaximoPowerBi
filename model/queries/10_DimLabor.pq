/* ============================================================================
   QUERY: DimLabor
   IsWrenchCraft excludes planners and supervisors - they do not burn down the
   work-order backlog, so they must not inflate the capacity denominator.
   ============================================================================ */
let
    Source = fnLoadCsv("LABOR.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"LABORCODE", type text}, {"PERSONID", type text}, {"DISPLAYNAME", type text},
         {"CRAFT", type text}, {"SITEID", type text}, {"STATUS", type text},
         {"HIREDATE", type date}, {"PAYRATE", type number}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"LABORCODE", "DISPLAYNAME", "CRAFT", "SITEID", "STATUS", "HIREDATE", "PAYRATE"}),
    Wrench = Table.AddColumn(Kept, "IsWrenchCraft",
        each if [STATUS] = "ACTIVE" and not List.Contains({"SUPV", "PLAN"}, [CRAFT])
        then 1 else 0, Int64.Type)
in
    Wrench
