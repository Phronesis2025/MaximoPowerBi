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
