/*
================================================================================
POWER QUERY (M) TRANSFORMS - raw Maximo extracts to a star schema
================================================================================

HOW TO USE
  Each block below is one query. In Power BI Desktop:
    Home > Transform data > New Source > Blank Query > Advanced Editor
  Paste one block, name the query as shown in its header, repeat.

  Create the two PARAMETERS first, then fnLoadCsv, then dimensions, then facts.

DESIGN DECISION: NO FACT-TO-FACT RELATIONSHIPS
  It is tempting to relate FactWorkOrder[WONUM] to FactLabour[WONUM] as a
  header/detail pair. Do not. Combined with DimDate and DimSite reaching both
  tables, that creates two filter paths to the same rows and Power BI will
  either refuse the relationship or give you ambiguous results.

  Instead, every fact connects ONLY to shared dimensions, and the few work-order
  attributes needed on the transaction facts (WORKTYPE, ASSETNUM) are merged in
  here, in Power Query. Denormalising deliberately at load time is cheaper and
  far more predictable than fighting ambiguous paths in DAX.

DESIGN DECISION: BUSINESS RULES AS COLUMNS, NOT DAX BRANCHES
  IsPMOnTime, IsReactive, IsOpen, SchedStartVarianceDays and friends are
  computed here as 0/1 columns. The DAX measures then reduce to SUM and DIVIDE.
  This keeps the rules inspectable as data, makes them testable outside the
  model, and avoids nested IF logic buried inside measures.

CRITICAL: DATE VS DATETIME
  Every comparison of "did this finish by its target" uses DATE-ONLY columns.
  ACTFINISH 2026-06-30 14:00 is NOT <= TARGCOMPDATE 2026-06-30 12:00 at datetime
  precision, but the work WAS completed on the target day. On this dataset,
  comparing datetimes instead of dates understates PM compliance by 22.1
  percentage points (81.8% -> 59.7%, 4,290 work orders misclassified).
  This is the single most common silent bug in Maximo compliance reporting.

================================================================================
*/


/* ============================================================================
   PARAMETER: pSourceFolder        (Type: Text)
   Set this to the folder containing the CSVs. No trailing slash.
   ============================================================================ */
"C:\data\maximo-sample-data\data"


/* ============================================================================
   PARAMETER: pCulture             (Type: Text)
   Culture used for all date/number parsing. The CSVs are ISO-formatted, so
   en-US parses them correctly regardless of your machine locale. Setting this
   explicitly is what stops the model breaking when someone in Germany opens it.
   ============================================================================ */
"en-US"


/* ============================================================================
   QUERY: fnLoadCsv                (function)
   ============================================================================ */
let
    fnLoadCsv = (fileName as text) as table =>
        let
            Source = Csv.Document(
                File.Contents(pSourceFolder & "\" & fileName),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
        in
            Promoted
in
    fnLoadCsv


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


/* ============================================================================
   QUERY: DimWorkType
   A hand-built dimension. The planned/reactive split lives here as DATA, so
   changing the classification never means editing a measure.
   ============================================================================ */
let
    Source = #table(
        type table [
            WORKTYPE = text,
            WorkTypeName = text,
            WorkTypeGroup = text,
            SortOrder = Int64.Type
        ],
        {
            {"PM",   "Preventive",  "Planned",  1},
            {"PDM",  "Predictive",  "Planned",  2},
            {"INSP", "Inspection",  "Planned",  3},
            {"PROJ", "Project",     "Planned",  4},
            {"SAF",  "Safety",      "Planned",  5},
            {"CM",   "Corrective",  "Reactive", 6},
            {"EM",   "Emergency",   "Reactive", 7}
        }
    )
in
    Source


/* ============================================================================
   QUERY: DimStatus
   ============================================================================ */
let
    Source = #table(
        type table [
            STATUS = text,
            StatusName = text,
            StatusGroup = text,
            SortOrder = Int64.Type
        ],
        {
            {"WAPPR", "Waiting on Approval", "Open",      1},
            {"APPR",  "Approved",            "Open",      2},
            {"INPRG", "In Progress",         "Open",      3},
            {"COMP",  "Completed",           "Closed",    4},
            {"CLOSE", "Closed",              "Closed",    5},
            {"CAN",   "Cancelled",           "Cancelled", 6}
        }
    )
in
    Source


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


/* ============================================================================
   QUERY: FactLabour
   WORKTYPE is merged in from WORKORDER so labour can be split planned vs
   reactive WITHOUT a fact-to-fact relationship. See the header note.
   ============================================================================ */
let
    Source = fnLoadCsv("LABTRANS.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"LABTRANSID", Int64.Type}, {"WONUM", type text}, {"SITEID", type text},
         {"LABORCODE", type text}, {"CRAFT", type text}, {"TRANSDATE", type datetime},
         {"REGULARHRS", type number}, {"PREMIUMPAYHOURS", type number},
         {"PAYRATE", type number}, {"LINECOST", type number}, {"TRANSTYPE", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"LABTRANSID", "WONUM", "SITEID", "LABORCODE", "CRAFT", "TRANSDATE",
         "REGULARHRS", "PREMIUMPAYHOURS", "PAYRATE", "LINECOST", "TRANSTYPE"}),
    TransDate = Table.AddColumn(Kept, "TransDate",
        each Date.From([TRANSDATE]), type date),
    TotalHrs = Table.AddColumn(TransDate, "TotalHours",
        each [REGULARHRS] + [PREMIUMPAYHOURS], type number),
    // denormalise the work-order classification
    Joined = Table.NestedJoin(TotalHrs, {"WONUM"}, FactWorkOrder, {"WONUM"},
        "wo", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "wo",
        {"WORKTYPE", "ASSETNUM"}, {"WORKTYPE", "ASSETNUM"}),
    Final = Table.RemoveColumns(Expanded, {"TRANSDATE"})
in
    Final


/* ============================================================================
   QUERY: FactMaterial
   ============================================================================ */
let
    Source = fnLoadCsv("MATUSETRANS.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"MATUSETRANSID", Int64.Type}, {"WONUM", type text}, {"SITEID", type text},
         {"ITEMNUM", type text}, {"LOCATION", type text}, {"QUANTITY", type number},
         {"UNITCOST", type number}, {"LINECOST", type number},
         {"TRANSDATE", type datetime}, {"ISSUETYPE", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"MATUSETRANSID", "WONUM", "SITEID", "ITEMNUM", "LOCATION", "QUANTITY",
         "UNITCOST", "LINECOST", "TRANSDATE", "ISSUETYPE"}),
    TransDate = Table.AddColumn(Kept, "TransDate",
        each Date.From([TRANSDATE]), type date),
    Joined = Table.NestedJoin(TransDate, {"WONUM"}, FactWorkOrder, {"WONUM"},
        "wo", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "wo",
        {"WORKTYPE", "ASSETNUM"}, {"WORKTYPE", "ASSETNUM"}),
    Final = Table.RemoveColumns(Expanded, {"TRANSDATE"})
in
    Final


/* ============================================================================
   QUERY: FactDowntime
   DOWNTIME is ELAPSED wall-clock hours. Do not substitute ACTLABHRS - three
   technicians for four hours is 12 labour hours but 4 hours of downtime, and
   using labour hours inflates MTTR by roughly the crew size.
   ============================================================================ */
let
    Source = fnLoadCsv("DOWNTIMEREPORT.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"ASSETNUM", type text}, {"WONUM", type text}, {"SITEID", type text},
         {"DOWNTIMESTART", type datetime}, {"DOWNTIMEEND", type datetime},
         {"DOWNTIME", type number}, {"TYPE", type text}, {"PROBLEMCODE", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"ASSETNUM", "WONUM", "SITEID", "DOWNTIMESTART", "DOWNTIMEEND",
         "DOWNTIME", "TYPE", "PROBLEMCODE"}),
    DateCol = Table.AddColumn(Kept, "DowntimeStartDate",
        each Date.From([DOWNTIMESTART]), type date),
    Final = Table.RemoveColumns(DateCol, {"DOWNTIMESTART", "DOWNTIMEEND"})
in
    Final


/* ============================================================================
   QUERY: FactFailure
   ============================================================================ */
let
    Source = fnLoadCsv("FAILUREREPORT.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"WONUM", type text}, {"ASSETNUM", type text}, {"LOCATION", type text},
         {"SITEID", type text}, {"FAILURECODE", type text}, {"PROBLEMCODE", type text},
         {"CAUSECODE", type text}, {"REMEDYCODE", type text},
         {"REPORTDATE", type datetime}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"WONUM", "ASSETNUM", "SITEID", "FAILURECODE", "PROBLEMCODE",
         "CAUSECODE", "REMEDYCODE", "REPORTDATE"}),
    DateCol = Table.AddColumn(Kept, "FailureDate",
        each Date.From([REPORTDATE]), type date),
    Final = Table.RemoveColumns(DateCol, {"REPORTDATE"})
in
    Final


/* ============================================================================
   QUERY: FactMeterReading
   ============================================================================ */
let
    Source = fnLoadCsv("METERREADING.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {{"ASSETNUM", type text}, {"SITEID", type text}, {"METERNAME", type text},
         {"READINGDATE", type datetime}, {"READING", type number},
         {"MEASUREUNITID", type text}},
        pCulture
    ),
    Kept = Table.SelectColumns(Typed,
        {"ASSETNUM", "SITEID", "METERNAME", "READINGDATE", "READING", "MEASUREUNITID"}),
    DateCol = Table.AddColumn(Kept, "ReadingDate",
        each Date.From([READINGDATE]), type date),
    Final = Table.RemoveColumns(DateCol, {"READINGDATE"})
in
    Final


/* ============================================================================
   QUERY: ScheduleTolerance     (disconnected what-if table)
   Feeds the Schedule Compliance % measure. Leave it UNRELATED to everything.
   ============================================================================ */
let
    Source = #table(
        type table [Days = Int64.Type, ToleranceLabel = text],
        {
            {0, "Same day"},
            {1, "Within 1 day"},
            {2, "Within 2 days"},
            {3, "Within 3 days"},
            {7, "Within 1 week"}
        }
    )
in
    Source
