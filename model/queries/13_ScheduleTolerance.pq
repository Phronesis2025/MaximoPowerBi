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
