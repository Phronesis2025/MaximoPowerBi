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
   QUERY: DimWorkType   (replaces the existing version)

   Definitions live here as DATA, not as a text box on the report. Three
   consequences worth the extra column:
     - the info panel is a table visual bound to this dimension, so it can
       never drift out of step with the work types actually in the model
     - adding a work type adds its definition automatically
     - the definitions are inspectable in the model, not buried in a shape

   SortOrder runs reactive first, then planned, each block by urgency. On a
   100% stacked bar only the segment anchored at x=0 is directly comparable
   across rows, so reactive work must sit at the left edge for site-to-site
   comparison of the headline metric to be visually honest.
   ============================================================================ */
let
    Source = #table(
        type table [
            WORKTYPE = text,
            WorkTypeName = text,
            WorkTypeGroup = text,
            SortOrder = Int64.Type,
            GroupSortOrder = Int64.Type,
            WorkTypeDefinition = text
        ],
        {
            {"EM", "Emergency", "Reactive", 1, 1,
             "Unplanned work requiring immediate response to restore safety or a critical function. Highest disruption and highest cost per hour; displaces scheduled work."},
            {"CM", "Corrective", "Reactive", 2, 1,
             "Unplanned repair of a failure that does not demand immediate response. Enters the backlog and is scheduled, but was not prevented."},
            {"SAF", "Safety", "Planned", 3, 2,
             "Work raised to correct a safety hazard or regulatory deficiency. Planned, but prioritised above routine preventive work."},
            {"INSP", "Inspection", "Planned", 4, 2,
             "Regulatory, insurance or statutory inspection on a fixed schedule. Compliance-driven rather than condition-driven."},
            {"PM", "Preventive", "Planned", 5, 2,
             "Time or usage based maintenance performed to prevent failure. The core of a planned programme and the basis of PM Compliance."},
            {"PDM", "Predictive", "Planned", 6, 2,
             "Condition-based work triggered by meter readings, vibration analysis or thermography. Performed because evidence suggests failure is approaching."},
            {"PROJ", "Project", "Planned", 7, 2,
             "Capital, modification or improvement work. Not failure-driven and not part of the maintenance programme; included for complete cost picture."}
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

    // as-of anchor, derived from the calendar
    AsOf = List.Max (
        Table.SelectRows ( DimDate, each [ISPASTORTODAY] = 1 )[Date]
    ),

    // days since the work order was raised; null for anything not open
    Aged = Table.AddColumn ( Cycle, "DaysOpen",
        each if [IsOpen] = 1 then Duration.Days ( AsOf - [ReportDate] ) else null,
        Int64.Type ),

    // days past target completion; null unless open AND past target
    Overdue = Table.AddColumn ( Aged, "DaysOverdue",
        each if [IsOpen] = 1 and [TargCompDate] <> null and [TargCompDate] < AsOf
             then Duration.Days ( AsOf - [TargCompDate] )
             else null,
        Int64.Type ),

    Bucket = Table.AddColumn ( Overdue, "AgeBucket",
        each if [DaysOpen] = null then null
             else if [DaysOpen] < 0 then "Not yet due"
             else if [DaysOpen] <= 30 then "0-30 days"
             else if [DaysOpen] <= 60 then "31-60 days"
             else if [DaysOpen] <= 90 then "61-90 days"
             else "91+ days",
        type text ),

    BucketSort = Table.AddColumn ( Bucket, "AgeBucketSort",
        each if [DaysOpen] = null then null
             else if [DaysOpen] < 0 then 0
             else if [DaysOpen] <= 30 then 1
             else if [DaysOpen] <= 60 then 2
             else if [DaysOpen] <= 90 then 3
             else 4,
        Int64.Type ),

    Final = Table.RemoveColumns(BucketSort,
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


/* ============================================================================
   QUERY: KPIDefinitions   (replaces the existing version)

   Now covers both the executive and backlog pages. One glossary serves every
   page - copy the info panel group from page to page with no filtering.
   A reader on any page can look up any metric in the report, which is more
   useful than a per-page panel that hides the rest.

   Leave this table UNRELATED to everything.
   ============================================================================ */
let
    Source = #table(
        type table [
            SortOrder = Int64.Type,
            Section = text,
            KPI = text,
            Definition = text,
            Benchmark = text
        ],
        {
            // ---- executive overview -------------------------------------------
            {1, "Performance", "Reactive Maintenance %",
             "Share of work orders that were emergency or corrective - work that was not planned. Calculated as emergency plus corrective divided by all non-cancelled work orders.",
             "Lower is better. SMRP best-in-class is under 20%."},

            {2, "Performance", "PM Compliance %",
             "Share of completed preventive work orders finished on or before their target completion date. Reported against the period the work was DUE, not the period it was raised.",
             "Higher is better. Common industry target is 90% or above."},

            {3, "Performance", "MTTR (Hours)",
             "Mean time to repair. Total elapsed downtime hours divided by the number of downtime events. Elapsed wall-clock time, not summed labour hours - three technicians for four hours is twelve labour hours but four hours of downtime.",
             "Lower is better. No neutral absolute target; compare across sites and over time."},

            {4, "Cost", "Total Maintenance Cost",
             "Labour, material, tool and contracted service cost on all non-cancelled work orders. Taken at work order level because tool and service cost have no transaction detail.",
             "No benchmark. Read alongside cost as a percent of RAV."},

            {5, "Cost", "Maintenance Cost % of RAV",
             "Annual maintenance spend as a percentage of replacement asset value - the installed cost to replace the asset base, not the original equipment invoice.",
             "Lower is better. SMRP best-in-class is 2% to 3% per year."},

            // ---- backlog and aging --------------------------------------------
            {6, "Backlog", "Open Work Orders",
             "Work orders currently awaiting approval, approved and waiting, or in progress. A current-state count taken at the data date - it does not change when you slice by month.",
             "No target. Read against crew capacity, not in isolation."},

            {7, "Backlog", "Backlog Weeks",
             "Estimated labour hours on all open work orders divided by weekly hands-on craft capacity. Answers how many weeks of work are waiting. Planners and supervisors are excluded from capacity as they do not burn down the backlog.",
             "4 to 6 weeks is generally healthy. Below 2 can indicate over-resourcing; above 8 means the crew cannot keep pace."},

            {8, "Backlog", "Overdue Work Orders",
             "Open work orders whose TARGET COMPLETION date has already passed. Distinct from aged work - a work order can be 50 days old and not overdue if it was given a 60-day target.",
             "Lower is better. Sustained levels above 20% of open work indicate a scheduling or capacity problem."},

            {9, "Backlog", "Avg Days Overdue",
             "Mean number of days past target, averaged across overdue work orders only. Work that is not yet late is excluded, so this measures how late the late work is - not how late work is on average.",
             "Lower is better. No published benchmark."},

            {10, "Backlog", "Age Bucket",
             "Days since the work order was raised, banded. 'Not yet due' is not an error - Maximo generates preventive work orders ahead of their due date, so those work orders are open but have not yet come due. They are separated out so they do not flatter the aging profile.",
             "The 91+ band is the one to watch. Work this old usually needs re-scoping or cancelling rather than scheduling."},

            {11, "Backlog", "Aged Over 90 Days",
             "Open work orders raised more than 90 days ago, regardless of whether they are overdue. The aging tail of the backlog.",
             "Lower is better. A growing tail means work is being raised and then abandoned."},

            {12, "Backlog", "Backlog Hours Overdue",
             "Estimated labour hours sitting on work that is already late. Total backlog includes work still inside its window, which is not yet a problem; this is the portion that is.",
             "Read as a share of total backlog. Above half means most of the queue is already late."},

            // ---- reliability ---------------------------------------------------
            {13, "Reliability", "MTBF (Hours)",
             "Mean time between failures. Operating asset hours divided by failure events. Operating hours are assumed as asset count multiplied by calendar hours, less reported downtime - a stated assumption, not a measured value.",
             "Higher is better. Compare across sites; the absolute value depends on the operating-hours assumption."},

            {14, "Reliability", "Asset Availability %",
             "Share of assumed operating hours during which assets were not down. Because the denominator assumes 24/7 calendar operation, this measure flatters every site - most assets do not run continuously.",
             "Higher is better, but read MTBF alongside it. Availability can look uniformly excellent while MTBF shows a four-fold gap between sites."}
        }
    )
in
    Source
