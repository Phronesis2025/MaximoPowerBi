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
            SortOrder = Int64.Type,
            GroupSortOrder = Int64.Type
        ],
        {
            {"EM",   "Emergency",   "Reactive", 1, 1},
            {"CM",   "Corrective",  "Reactive", 2, 1},
            {"SAF",  "Safety",      "Planned",  3, 2},
            {"INSP", "Inspection",  "Planned",  4, 2},
            {"PM",   "Preventive",  "Planned",  5, 2},
            {"PDM",  "Predictive",  "Planned",  6, 2},
            {"PROJ", "Project",     "Planned",  7, 2}
        }
    )
in
    Source
