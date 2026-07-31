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
