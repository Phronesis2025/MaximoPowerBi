#!/usr/bin/env python3
"""
check_model.py - validate a Power BI PBIP semantic model against the expected
state of the Maximo star schema.

Run it after each checkpoint instead of eyeballing the model view. Reads TMDL
text only; never opens or modifies anything.

    python3 check_model.py "path/to/MaximoPowerBI.SemanticModel"

Exit code 0 = all hard checks passed. 1 = at least one FAIL.

FAIL   things I am certain are wrong
WARN   things that are probably wrong but depend on your intent
INFO   reported for your judgement, not scored
"""

import os
import re
import sys
import glob

EXPECTED_TABLES = {
    "DimDate", "DimAsset", "DimLocation", "DimSite", "DimWorkType", "DimStatus",
    "DimCraft", "DimLabor", "DimItem", "DimFailureCode", "ScheduleTolerance",
    "FactWorkOrder", "FactLabour", "FactMaterial", "FactDowntime",
    "FactFailure", "FactMeterReading",
}

RAW_TABLES = {
    "WORKORDER", "WOSTATUS", "LABTRANS", "MATUSETRANS", "FAILUREREPORT",
    "DOWNTIMEREPORT", "METERREADING", "INVENTORY", "ASSET", "LOCATIONS", "PM",
    "JOBPLAN", "JOBTASK", "ASSETMETER", "LABOR", "PERSON", "CRAFT", "ITEM",
    "COMPANIES", "FAILURECODE", "SITE", "ORGANIZATION", "DIM_DATE",
}

# column -> required dataType on FactWorkOrder. These are the ones that break
# silently when Power BI is left to infer types from a CSV sample.
FACTWO_TYPES = {
    "WONUM": "string",          # alphanumeric in real Maximo; int64 breaks it
    "ReportDate": "dateTime",
    "TargCompDate": "dateTime",
    "ActFinishDate": "dateTime",
    "ActStartDate": "dateTime",
    "SchedStartDate": "dateTime",
    "ESTLABHRS": "double",
    "ACTLABCOST": "double",
    "ACTMATCOST": "double",
    "ACTTOOLCOST": "double",
    "ACTSERVCOST": "double",
    "ActualTotalCost": "double",
    "IsCancelled": "int64",
    "IsOpen": "int64",
    "IsReactive": "int64",
    "IsPM": "int64",
    "IsPMCompleted": "int64",
    "IsPMOnTime": "int64",
    "IsScheduled": "int64",
}

# Columns on the OTHER fact and dim tables that silently break a measure if
# mistyped. FactWorkOrder is not the only place type inference can bite:
#   FactDowntime[DOWNTIME]        -> MTTR
#   FactLabour/Material[WORKTYPE] -> proves the merge from FactWorkOrder worked
#   DimLabor[IsWrenchCraft]       -> backlog capacity denominator
#   ScheduleTolerance[Days]       -> schedule compliance tolerance
#   DimAsset[REPLACECOST]         -> cost as % of RAV
OTHER_TYPES = {
    "FactDowntime": {"DOWNTIME": "double", "DowntimeStartDate": "dateTime",
                     "ASSETNUM": "string", "SITEID": "string"},
    "FactLabour": {"LINECOST": "double", "TotalHours": "double",
                   "WORKTYPE": "string", "TransDate": "dateTime"},
    "FactMaterial": {"LINECOST": "double", "QUANTITY": "double",
                     "WORKTYPE": "string", "TransDate": "dateTime"},
    "FactFailure": {"FailureDate": "dateTime", "PROBLEMCODE": "string"},
    "FactMeterReading": {"READING": "double", "ReadingDate": "dateTime"},
    "DimLabor": {"IsWrenchCraft": "int64"},
    "ScheduleTolerance": {"Days": "int64"},
    "DimAsset": {"REPLACECOST": "double", "ASSETNUM": "string"},
    "DimDate": {"Date": "dateTime"},
}

REQUIRED_MEASURES = [
    "Work Orders", "Reactive Maintenance %", "PM Compliance %",
    "Schedule Compliance %", "MTTR (Hours)", "Total Maintenance Cost",
    "Backlog Hours", "Weekly Craft Capacity (Hours)", "Backlog Weeks",
    "Data As Of Date", "Overdue Work Orders", "Overdue %", "Avg Days Overdue",
    "Oldest Open Work Order (Days)", "Open Emergency Work Orders",
    "PM Due Next 14 Days", "Work Orders Completed", "Work Orders Reported",
    "Net Backlog Change", "Backlog Hours per Technician",
    "Reactive Maintenance % (12M Rolling)", "PM Compliance % (12M Rolling)",
    "Reactive Status Colour", "Reactive vs Target",
    "PM Compliance Status Colour", "PM Compliance vs Target",
    "Backlog Status Colour", "Backlog vs Target",
    "Cost RAV Status Colour", "Cost RAV vs Target",
    "Avg Age of Open Work (Days)", "Backlog Hours Overdue",
    "Overdue Emergency Work Orders", "Aged Over 90 Days",
    "Overdue Share of Backlog", "Backlog Age Status Colour",
    "Overdue Status Colour",
]

results = []


def add(level, msg):
    results.append((level, msg))


def read(path):
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def columns_of(tmdl_text):
    """column name -> dataType, from a TMDL table file."""
    out = {}
    cur = None
    for line in tmdl_text.splitlines():
        s = line.strip()
        m = re.match(r"^column\s+(?:'([^']+)'|(\S+))", s)
        if m:
            cur = m.group(1) or m.group(2)
            continue
        if cur:
            m2 = re.match(r"^dataType:\s*(\w+)", s)
            if m2:
                out[cur] = m2.group(1)
                cur = None
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    defn = os.path.join(root, "definition")
    if not os.path.isdir(defn):
        sys.exit(f"no definition/ folder under {root}")

    # ---------- tables ----------
    files = glob.glob(os.path.join(defn, "tables", "*.tmdl"))
    names = [os.path.splitext(os.path.basename(f))[0] for f in files]

    local_dates = [n for n in names if n.startswith("LocalDateTable_")]
    templates = [n for n in names if n.startswith("DateTableTemplate_")]
    if local_dates or templates:
        add("FAIL", f"Auto Date/Time is active: {len(local_dates)} LocalDateTable "
                    f"and {len(templates)} template table(s) present. Turn off "
                    f"Auto date/time (Options > Current File > Data Load).")
    else:
        add("PASS", "no Auto Date/Time tables")

    model = read(os.path.join(defn, "model.tmdl"))
    m = re.search(r"__PBI_TimeIntelligenceEnabled\s*=\s*(\d)", model)
    if m and m.group(1) != "0":
        add("FAIL", "__PBI_TimeIntelligenceEnabled = 1 in model.tmdl")
    else:
        add("PASS", "time intelligence annotation off or absent")

    real = {n for n in names
            if not n.startswith(("LocalDateTable_", "DateTableTemplate_"))}
    leftover_raw = sorted(real & RAW_TABLES)
    if leftover_raw:
        add("FAIL", f"{len(leftover_raw)} raw Maximo table(s) still loaded: "
                    f"{', '.join(leftover_raw[:6])}"
                    f"{' ...' if len(leftover_raw) > 6 else ''}. "
                    f"Uncheck Enable load on these.")
    else:
        add("PASS", "no raw Maximo tables loaded")

    missing = sorted(EXPECTED_TABLES - real)
    if missing:
        add("FAIL", f"{len(missing)} star table(s) missing: {', '.join(missing)}")
    else:
        add("PASS", f"all {len(EXPECTED_TABLES)} star tables present")

    unexpected = sorted(real - EXPECTED_TABLES - RAW_TABLES)
    for n in unexpected:
        add("INFO", f"extra table not in the spec: {n}")

    # ---------- relationships ----------
    rels = read(os.path.join(defn, "relationships.tmdl"))
    blocks = re.findall(r"^relationship\s+(\S+)(.*?)(?=^relationship|\Z)",
                        rels, re.S | re.M)
    auto = [b for b in blocks if b[0].startswith("AutoDetected")]
    localdate = [b for b in blocks if "LocalDateTable" in b[1]]
    bidi = [b for b in blocks if "bothDirections" in b[1]]
    inactive = [b for b in blocks if "isActive: false" in b[1]]
    active = len(blocks) - len(inactive)

    if auto:
        add("FAIL", f"{len(auto)} AutoDetected_* relationship(s) remain")
    if localdate:
        add("FAIL", f"{len(localdate)} relationship(s) point at LocalDateTable")
    if bidi:
        add("FAIL", f"{len(bidi)} bidirectional relationship(s) "
                    f"(crossFilteringBehavior: bothDirections)")
    if not (auto or localdate or bidi):
        add("PASS", "no auto-detected, hidden-date, or bidirectional relationships")

    if len(blocks) == 0:
        add("INFO", "0 relationships - expected at checkpoint 1, not at the end")
    elif active == 24 and len(inactive) == 2:
        add("PASS", "24 active + 2 inactive relationships, as specified")
    else:
        add("WARN", f"expected 24 active + 2 inactive, found "
                    f"{active} active + {len(inactive)} inactive")

    # ---------- FactWorkOrder column types ----------
    fwo = read(os.path.join(defn, "tables", "FactWorkOrder.tmdl"))
    if fwo:
        cols = columns_of(fwo)
        bad, absent = [], []
        for col, want in FACTWO_TYPES.items():
            got = cols.get(col)
            if got is None:
                absent.append(col)
            elif got != want:
                bad.append(f"{col} is {got}, expected {want}")
        if bad:
            add("FAIL", "wrong column types on FactWorkOrder: " + "; ".join(bad))
        if absent:
            add("FAIL", f"columns missing from FactWorkOrder: {', '.join(absent)}")
        if not bad and not absent:
            add("PASS", f"all {len(FACTWO_TYPES)} checked FactWorkOrder "
                        f"columns correctly typed")
    else:
        add("INFO", "FactWorkOrder.tmdl not found - skipped type checks")

    # ---------- other fact/dim column types ----------
    checked = wrong = 0
    for tbl, wants in OTHER_TYPES.items():
        txt = read(os.path.join(defn, "tables", f"{tbl}.tmdl"))
        if not txt:
            add("INFO", f"{tbl}.tmdl not found - skipped type checks")
            continue
        cols = columns_of(txt)
        for col, want in wants.items():
            checked += 1
            got = cols.get(col)
            if got is None:
                wrong += 1
                add("FAIL", f"{tbl}.{col} is missing")
            elif got != want:
                wrong += 1
                add("FAIL", f"{tbl}.{col} is {got}, expected {want}")
    if checked and not wrong:
        add("PASS", f"all {checked} checked columns on the other fact and dim "
                    f"tables correctly typed")

    # ---------- date table ----------
    dd = read(os.path.join(defn, "tables", "DimDate.tmdl"))
    if dd:
        if "dataCategory: Time" in dd:
            add("PASS", "DimDate carries dataCategory: Time (marked as date table)")
        else:
            add("WARN", "DimDate does not look marked as a date table "
                        "(no dataCategory: Time). Table tools > Mark as date table.")

    # ---------- measures ----------
    all_tmdl = "\n".join(read(f) for f in files)
    found = re.findall(r"^\s*measure\s+(?:'([^']+)'|(\S+))", all_tmdl, re.M)
    found = {a or b for a, b in found}
    if not found:
        add("INFO", "no measures defined yet")
    else:
        miss = [x for x in REQUIRED_MEASURES if x not in found]
        if miss:
            add("WARN", f"{len(miss)} core measure(s) not found: {', '.join(miss)}")
        else:
            add("PASS", f"all {len(REQUIRED_MEASURES)} core measures present "
                        f"({len(found)} total)")

    # ---------- repo hygiene ----------
    cache = os.path.join(root, ".pbi", "cache.abf")
    if os.path.isfile(cache):
        mb = os.path.getsize(cache) / 1048576
        add("INFO", f".pbi/cache.abf present ({mb:,.1f} MB) - gitignore this")

    # ---------- report ----------
    order = {"FAIL": 0, "WARN": 1, "PASS": 2, "INFO": 3}
    width = 78
    print("=" * width)
    print(f"MODEL CHECK  {root}")
    print("=" * width)
    for level in ("FAIL", "WARN", "PASS", "INFO"):
        for lv, msg in [r for r in results if r[0] == level]:
            print(f"[{lv:<4}] {msg}")
    fails = sum(1 for lv, _ in results if lv == "FAIL")
    warns = sum(1 for lv, _ in results if lv == "WARN")
    print("=" * width)
    print(f"{fails} FAIL   {warns} WARN   "
          f"{sum(1 for lv, _ in results if lv == 'PASS')} PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
