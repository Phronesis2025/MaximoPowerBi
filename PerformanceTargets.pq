/* ============================================================================
   QUERY: PerformanceTargets   (new - disconnected reference table)

   Every red/amber/green in this report grades against a target stored here,
   not against a number buried in a measure. Targets are stated with their
   source so a reviewer can argue with the standard rather than with the colour.

   Leave this table UNRELATED to everything. Same pattern as ScheduleTolerance
   and DimWorkType: policy as data.

   SCOPE
     Maximo's core market is asset-intensive operations - utilities, oil and
     gas, rail and transport, manufacturing, nuclear and civil infrastructure.
     These targets are written for that audience: reliability and planning
     benchmarks first, service-contract benchmarks where they genuinely apply.

   SOURCES
     SMRP   Society for Maintenance & Reliability Professionals,
            Best Practices 6th edition - the reliability benchmarks
     STAT   Statutory / regulatory - not a benchmark, a legal obligation
     CTR    Service-contract norm - the values written into hard-FM and
            outsourced-maintenance agreements and their credit regimes

   DIRECTION drives the colour logic:
     lower   green at or below Green, amber to Amber, red beyond
     higher  green at or above Green, amber down to Amber, red below
     band    green inside Green..Amber, red outside the wider tolerance

   MEASURABLE flags whether this dataset can currently compute the metric.
   Targets marked N are carried deliberately so the gap is visible rather
   than quietly dropped - see the notes on each row.
   ============================================================================ */
let
    Source = #table(
        type table [
            SortOrder = Int64.Type,
            Section = text,
            Metric = text,
            Direction = text,
            Target = number,
            GreenAt = number,
            AmberAt = number,
            TargetLabel = text,
            Basis = text,
            Measurable = text,
            Note = text
        ],
        {
            // ---- compliance -------------------------------------------------
            {1, "Compliance", "Statutory Compliance %", "higher", 1.00, 1.00, 0.98,
             "100%", "STAT", "Y",
             "A missed statutory inspection is a regulatory breach and can invalidate insurance. There is no acceptable shortfall - amber exists only to flag the near miss before it becomes one."},

            {2, "Compliance", "PM Compliance %", "higher", 0.90, 0.90, 0.80,
             "90% or above", "SMRP", "Y",
             "SMRP world-class is 90%. Below 80% the programme is not functioning. Critical A-class assets should be held to 95%."},

            {3, "Compliance", "PM Compliance % - critical assets", "higher", 0.95, 0.95, 0.90,
             "95% or above", "SMRP", "Y",
             "Applies to criticality 1 assets only. Tighter than the portfolio target because these are the failures the client feels."},

            {4, "Compliance", "Schedule Compliance %", "higher", 0.90, 0.90, 0.80,
             "90% or above", "SMRP", "Y",
             "World-class is 90%; industry average runs 75-80%. Highly sensitive to the tolerance window - state the tolerance on the report face."},

            // ---- work mix ---------------------------------------------------
            {5, "Work mix", "Reactive Maintenance %", "lower", 0.20, 0.20, 0.30,
             "under 20%", "SMRP", "Y",
             "SMRP best-in-class is under 20%, equivalent to a planned-maintenance percentage of 85% or better. Hard-FM contracts more commonly write the reactive ratio at under 30% - amber here reflects that looser contractual line."},

            {6, "Work mix", "Planned Maintenance %", "higher", 0.85, 0.85, 0.70,
             "85% or above", "SMRP", "Y",
             "The complement of reactive work. Stated separately because clients recognise PMP and contractors are usually measured on it."},

            // ---- responsiveness ---------------------------------------------
            {7, "Responsiveness", "P1 Emergency response within SLA %", "higher", 0.95, 0.95, 0.90,
             "95% within 4 hours", "CTR", "Y",
             "Baseline hard-FM P1: 4-hour response, 24-hour rectification for life-safety or building-critical failures. Response is derivable here as ACTSTART minus REPORTDATE on WOPRIORITY 1 work."},

            {8, "Responsiveness", "P2 Urgent response within SLA %", "higher", 0.95, 0.95, 0.90,
             "95% within 24 hours", "CTR", "Y",
             "Baseline P2: 24-hour response, 5-day rectification."},

            {9, "Responsiveness", "Reactive closed within SLA %", "higher", 0.90, 0.90, 0.85,
             "90% or above", "CTR", "Y",
             "The headline responsiveness number in most service agreements. Below 90% typically triggers a performance improvement plan."},

            {10, "Responsiveness", "Overdue critical work orders", "lower", 0, 0, 5,
             "zero", "CTR", "Y",
             "Open criticality-1 work past target completion. Contracts almost always write this as zero tolerance rather than a percentage."},

            // ---- reliability -------------------------------------------------
            {11, "Reliability", "Asset Availability %", "higher", 0.98, 0.98, 0.95,
             "98% or above", "CTR", "Y",
             "Applies to building-critical plant. Our figure assumes calendar hours less reported downtime; if the client has scheduled runtime, use that denominator and restate the target."},

            {12, "Reliability", "MTBF (Hours)", "higher", 0, 0, 0,
             "trend upward", "SMRP", "Y",
             "No absolute benchmark exists - the denominator depends on an operating-hours assumption. Grade on direction of travel against the contract baseline, never on an absolute value."},

            {13, "Reliability", "MTTR (Hours)", "lower", 0, 0, 0,
             "trend downward", "SMRP", "Y",
             "Contract-specific. Set the target from the mobilisation baseline. Report the distribution, not just the mean - the tail is where the client's pain lives."},

            // ---- backlog and cost --------------------------------------------
            {14, "Backlog", "Backlog Weeks", "band", 5.0, 4.0, 6.0,
             "4 to 6 weeks", "SMRP", "Y",
             "Two-sided. Under 2 weeks usually means over-resourcing or work not being captured in the system; over 8 means the crew cannot keep pace."},

            {15, "Backlog", "Work aged over 90 days", "lower", 0, 0, 50,
             "trend to zero", "CTR", "Y",
             "The aging tail. Work this old normally needs re-scoping or cancelling rather than scheduling."},

            {16, "Cost", "Maintenance Cost % of RAV", "lower", 0.03, 0.03, 0.05,
             "2% to 3% per year", "SMRP", "Y",
             "SMRP best-in-class is 2-3% of replacement asset value per year. Read alongside availability - cutting spend while availability falls is not a win."},

            // ---- carried but not computable on this dataset --------------------
            {17, "Not measured", "First-time fix %", "higher", 0.85, 0.85, 0.75,
             "85% or above", "CTR", "N",
             "Standard FM KPI - 85% routine, 70-80% accepted on complex HVAC and lift plant. NOT COMPUTABLE HERE: no repeat-visit linkage exists in the dataset."},

            {18, "Not measured", "Technician wrench time %", "higher", 0.35, 0.35, 0.25,
             "35% or above", "SMRP", "N",
             "Industry average runs 25-35%. NOT COMPUTABLE HERE: no attendance, leave or non-productive time, so any ratio would use two mismatched denominators."},

            {19, "Not measured", "Customer satisfaction score", "higher", 0.85, 0.85, 0.75,
             "85% or above", "CTR", "N",
             "Standard in FM service agreements. NOT COMPUTABLE HERE: no survey data. Named as a roadmap item rather than faked."}
        }
    )
in
    Source
