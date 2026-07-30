/* ============================================================================
   QUERY: KPIDefinitions

   A disconnected reference table. Leave it UNRELATED to everything - it exists
   only to feed the info panel.

   Same reasoning as the definitions on DimWorkType: reference content lives in
   the model as data rather than as text boxes on a page. A text box drifts the
   moment a formula changes and nobody remembers to edit it. A table visual
   bound to this cannot.

   Benchmarks follow SMRP (Society for Maintenance & Reliability Professionals)
   published guidance where one exists. Where no neutral benchmark exists the
   Benchmark column says so rather than inventing a number.
   ============================================================================ */
let
    Source = #table(
        type table [
            SortOrder = Int64.Type,
            KPI = text,
            Definition = text,
            Benchmark = text
        ],
        {
            {1, "Reactive Maintenance %",
             "Share of work orders that were emergency or corrective - work that was not planned. Calculated as emergency plus corrective divided by all non-cancelled work orders.",
             "Lower is better. SMRP best-in-class is under 20%."},

            {2, "PM Compliance %",
             "Share of completed preventive work orders finished on or before their target completion date. Reported against the period the work was DUE, not the period it was raised.",
             "Higher is better. Common industry target is 90% or above."},

            {3, "Overdue %",
             "Share of currently open work orders whose target completion date has already passed. A current-state measure taken at the data date, not a measure of a time period.",
             "Lower is better. Sustained levels above 20% indicate a scheduling or capacity problem."},

            {4, "MTTR (Hours)",
             "Mean time to repair. Total elapsed downtime hours divided by the number of downtime events. Elapsed wall-clock time, not summed labour hours - three technicians for four hours is twelve labour hours but four hours of downtime.",
             "Lower is better. No neutral absolute target; compare across sites and over time."},

            {5, "Backlog Weeks",
             "Estimated labour hours on all open work orders divided by weekly hands-on craft capacity. Answers how many weeks of work are waiting. Planners and supervisors are excluded from capacity as they do not burn down the backlog.",
             "4 to 6 weeks is generally healthy. Below 2 can indicate over-resourcing; above 8 indicates the crew cannot keep pace."},

            {6, "Maintenance Cost % of RAV",
             "Annual maintenance spend as a percentage of replacement asset value - the installed cost to replace the asset base, not the original equipment invoice.",
             "Lower is better. SMRP best-in-class is 2% to 3% per year."}
        }
    )
in
    Source
