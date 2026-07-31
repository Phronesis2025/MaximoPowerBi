/* ============================================================================
   FactWorkOrder - AGING COLUMNS
   Insert these four steps into the existing FactWorkOrder query, immediately
   after the "Cycle" step (DaysToComplete) and before the "Final" step.
   Then update Final to reference BucketSort instead of Cycle.

   WHY IN POWER QUERY AND NOT DAX
   Age buckets as a DAX measure cannot be used as an axis - you would need a
   disconnected bucket table plus a SWITCH, which is slower and harder to read.
   As columns they slice, sort, and cross-filter natively. Same reasoning as the
   IsPMOnTime flags: business rules as data, not branches inside measures.

   THE ANCHOR IS DERIVED, NOT HARDCODED
   AsOf reads the last date flagged ISPASTORTODAY in DimDate, which is 2026-07-29.
   Change the generator's END_DATE and this follows automatically. Note this
   makes FactWorkOrder depend on DimDate in Power Query - no cycle, since DimDate
   depends on nothing.

   NEGATIVE AGE IS REAL, NOT AN ERROR
   Maximo generates PM work orders LEADTIME days before they come due, so 732
   open work orders are dated after the cutoff. They get their own "Not yet due"
   bucket rather than being folded into 0-30 days, where they would understate
   the true aging profile.
   ============================================================================ */

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

/* Then change the Final step from:
       Final = Table.RemoveColumns(Cycle, {...})
   to:
       Final = Table.RemoveColumns(BucketSort, {...})
   leaving the removed-column list exactly as it is.

   EXPECTED RESULT - open work orders by bucket, all sites
       Not yet due     732 work orders    1,151 est hours
       0-30 days       993                7,352
       31-60 days      485                4,033
       61-90 days      284                2,533
       91+ days        102                  733
                     -----                ------
                     2,596               15,802

   Houston holds 66 of the 102 work orders aged 91+ days.
*/
