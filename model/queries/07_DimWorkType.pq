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
