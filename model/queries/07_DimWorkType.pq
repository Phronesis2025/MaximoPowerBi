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
