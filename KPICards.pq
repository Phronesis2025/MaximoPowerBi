/* ============================================================================
   QUERY: KPICards   (new - disconnected reference table)

   Drives the eight HTML KPI cards on the Executive Overview.

   One row per card. Place eight HTML Content visuals on the page, each filtered
   to a single CardKey, and put [KPI Card HTML] in each. One measure, one table,
   eight visuals - rather than eight near-identical measures.

   Leave this table UNRELATED to everything. Same pattern as ScheduleTolerance,
   DimWorkType and PerformanceTargets: layout and policy as data.

   ScaleMax is the right-hand end of the bullet bar, chosen so the bar and the
   target tick both sit in a sensible part of the track - it is a display
   decision, not a business one, which is why it lives here and not in a measure.

   Targets duplicated from PerformanceTargets so the card renders even before
   that table is loaded; once it is, point Target at it and delete these.
   ============================================================================ */
let
    Source = #table(
        type table [
            CardOrder = Int64.Type,
            CardKey = text,
            CardLabel = text,
            Target = number,
            ScaleMax = number,
            TargetLabel = text
        ],
        {
            {1, "AVAIL",     "Asset Availability %",       0.98,  1.00,  "target 98%"},
            {2, "PM",        "PM Compliance %",            0.90,  1.00,  "target 90%"},
            {3, "STAT",      "Statutory Compliance %",     1.00,  1.00,  "target 100%"},
            {4, "SCHED",     "Schedule Compliance %",      0.90,  1.00,  "target 90%"},
            {5, "REACTIVE",  "Reactive Maintenance %",     0.20,  0.50,  "target under 20%"},
            {6, "MTBF",      "MTBF (Hours)",            1810.00, 2200.00, "trend up"},
            {7, "MTTR",      "MTTR (Hours)",              12.90,   20.00, "trend down"},
            {8, "COSTRAV",   "Maintenance Cost % of RAV",  0.03,   0.08, "best-in-class 2–3%"}
        }
    )
in
    Source
