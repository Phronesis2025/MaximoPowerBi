/* ============================================================================
   QUERY: FactWorkOrder
   The primary fact. All KPI business rules are materialised here as columns.
   ============================================================================ */
let
    Source = fnLoadCsv("WORKORDER.csv"),

    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"WONUM", type text},
            {"DESCRIPTION", type text},
            {"SITEID", type text},
            {"WORKTYPE", type text},
            {"STATUS", type text},
            {"ASSETNUM", type text},
            {"LOCATION", type text},
            {"PMNUM", type text},
            {"WOPRIORITY", Int64.Type},
            {"REPORTDATE", type datetime},
            {"TARGSTARTDATE", type datetime},
            {"TARGCOMPDATE", type datetime},
            {"SCHEDSTART", type datetime},
            {"ACTSTART", type datetime},
            {"ACTFINISH", type datetime},
            {"ESTLABHRS", type number},
            {"ACTLABHRS", type number},
            {"ACTLABCOST", type number},
            {"ACTMATCOST", type number},
            {"ACTTOOLCOST", type number},
            {"ACTSERVCOST", type number},
            {"PROBLEMCODE", type text},
            {"SUPERVISOR", type text},
            {"CREWID", type text}
        },
        pCulture
    ),

    Kept = Table.SelectColumns(Typed,
        {"WONUM", "DESCRIPTION", "SITEID", "WORKTYPE", "STATUS", "ASSETNUM",
         "LOCATION", "PMNUM", "WOPRIORITY", "REPORTDATE", "TARGSTARTDATE",
         "TARGCOMPDATE", "SCHEDSTART", "ACTSTART", "ACTFINISH", "ESTLABHRS",
         "ACTLABHRS", "ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST",
         "PROBLEMCODE", "SUPERVISOR", "CREWID"}),

    // unknown member so location-only work orders survive the asset join
    FixAsset = Table.TransformColumns(Kept,
        {{"ASSETNUM", each if _ = null or _ = "" then "(none)" else _, type text}}),

    // ---- DATE-ONLY columns. Every compliance comparison uses these, never the
    // ---- raw datetimes. See the header note on the 22.1-point error.
    DateCols = Table.AddColumn(FixAsset, "ReportDate",
                    each Date.From([REPORTDATE]), type date),
    DateCols2 = Table.AddColumn(DateCols, "TargCompDate",
                    each if [TARGCOMPDATE] = null then null else Date.From([TARGCOMPDATE]), type date),
    DateCols3 = Table.AddColumn(DateCols2, "ActStartDate",
                    each if [ACTSTART] = null then null else Date.From([ACTSTART]), type date),
    DateCols4 = Table.AddColumn(DateCols3, "ActFinishDate",
                    each if [ACTFINISH] = null then null else Date.From([ACTFINISH]), type date),
    DateCols5 = Table.AddColumn(DateCols4, "SchedStartDate",
                    each if [SCHEDSTART] = null then null else Date.From([SCHEDSTART]), type date),

    // ---- state flags
    F1 = Table.AddColumn(DateCols5, "IsCancelled",
            each if [STATUS] = "CAN" then 1 else 0, Int64.Type),
    F2 = Table.AddColumn(F1, "IsOpen",
            each if List.Contains({"WAPPR", "APPR", "INPRG"}, [STATUS]) then 1 else 0, Int64.Type),
    F3 = Table.AddColumn(F2, "IsCompleted",
            each if List.Contains({"COMP", "CLOSE"}, [STATUS]) then 1 else 0, Int64.Type),
    F4 = Table.AddColumn(F3, "IsReactive",
            each if List.Contains({"CM", "EM"}, [WORKTYPE]) then 1 else 0, Int64.Type),
    F5 = Table.AddColumn(F4, "IsPM",
            each if [WORKTYPE] = "PM" then 1 else 0, Int64.Type),

    // ---- PM compliance rules. Nested explicitly rather than using `and`, so a
    // ---- null date can never reach a comparison.
    F6 = Table.AddColumn(F5, "IsPMCompleted",
            each if [IsPM] = 1 and [IsCompleted] = 1 then
                     (if [ActFinishDate] = null then 0 else 1)
                 else 0, Int64.Type),
    F7 = Table.AddColumn(F6, "IsPMOnTime",
            each if [IsPMCompleted] = 1 then
                     (if [TargCompDate] = null then 0
                      else if [ActFinishDate] <= [TargCompDate] then 1 else 0)
                 else 0, Int64.Type),

    // ---- schedule compliance inputs
    F8 = Table.AddColumn(F7, "IsScheduled",
            each if [SchedStartDate] = null or [ActStartDate] = null then 0 else 1,
            Int64.Type),
    F9 = Table.AddColumn(F8, "SchedStartVarianceDays",
            each if [IsScheduled] = 1
                 then Duration.Days([ActStartDate] - [SchedStartDate])
                 else null, Int64.Type),

    // ---- cost roll-up. ACTTOOLCOST and ACTSERVCOST have no transaction table,
    // ---- so this work-order level total is the only complete cost figure.
    Cost = Table.AddColumn(F9, "ActualTotalCost",
            each [ACTLABCOST] + [ACTMATCOST] + [ACTTOOLCOST] + [ACTSERVCOST],
            type number),

    // ---- days to complete, for cycle-time analysis
    Cycle = Table.AddColumn(Cost, "DaysToComplete",
            each if [ActFinishDate] = null then null
                 else Duration.Days([ActFinishDate] - [ReportDate]), Int64.Type),

    Final = Table.RemoveColumns(Cycle,
        {"REPORTDATE", "TARGSTARTDATE", "TARGCOMPDATE", "SCHEDSTART", "ACTSTART", "ACTFINISH"})
in
    Final
