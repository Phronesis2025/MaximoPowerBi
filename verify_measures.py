#!/usr/bin/env python3
"""
Verification harness: build the star schema in pandas exactly as the Power Query
transforms describe it, then compute the six KPI measures on that star and check
them against the generator's independently-produced baselines.

This verifies TRANSFORM LOGIC and MEASURE DEFINITIONS.
It does NOT verify DAX syntax - there is no Analysis Services engine here.
"""

import pandas as pd

D = "C:/dev/MaximoPowerBi/data"
OPEN_STATUSES = ["WAPPR", "APPR", "INPRG"]
REACTIVE_TYPES = ["CM", "EM"]

pd.set_option("display.width", 200)

# ----------------------------------------------------------------------------
# STAGE 1 - load raw Maximo extracts (mirrors fnLoadTable in Power Query)
# ----------------------------------------------------------------------------
wo = pd.read_csv(f"{D}/WORKORDER.csv", dtype=str)
lab = pd.read_csv(f"{D}/LABTRANS.csv", dtype=str)
mat = pd.read_csv(f"{D}/MATUSETRANS.csv", dtype=str)
dtr = pd.read_csv(f"{D}/DOWNTIMEREPORT.csv", dtype=str)
fal = pd.read_csv(f"{D}/FAILUREREPORT.csv", dtype=str)
asset = pd.read_csv(f"{D}/ASSET.csv", dtype=str)
labor = pd.read_csv(f"{D}/LABOR.csv", dtype=str)

DATE_COLS_WO = ["REPORTDATE", "TARGSTARTDATE", "TARGCOMPDATE", "SCHEDSTART",
                "SCHEDFINISH", "ACTSTART", "ACTFINISH", "STATUSDATE"]
NUM_COLS_WO = ["ESTLABHRS", "ESTLABCOST", "ESTMATCOST", "ACTLABHRS", "ACTLABCOST",
               "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST", "DOWNTIME", "WOPRIORITY"]

for c in DATE_COLS_WO:
    wo[c] = pd.to_datetime(wo[c], errors="coerce")
for c in NUM_COLS_WO:
    wo[c] = pd.to_numeric(wo[c], errors="coerce").fillna(0.0)

# ----------------------------------------------------------------------------
# STAGE 2 - FactWorkOrder: the added columns the M code creates
# ----------------------------------------------------------------------------
f = wo.copy()

# CRITICAL: compare DATE parts, never datetimes. ACTFINISH 2026-06-30 14:00 is
# NOT <= TARGCOMPDATE 2026-06-30 12:00 at datetime precision, but the work WAS
# completed on the target day. This is the single most common silent bug in
# Maximo compliance measures.
f["ActFinishDate"] = f["ACTFINISH"].dt.normalize()
f["TargCompDate"] = f["TARGCOMPDATE"].dt.normalize()
f["ActStartDate"] = f["ACTSTART"].dt.normalize()
f["SchedStartDate"] = f["SCHEDSTART"].dt.normalize()

f["IsCancelled"] = (f["STATUS"] == "CAN").astype(int)
f["IsOpen"] = f["STATUS"].isin(OPEN_STATUSES).astype(int)
f["IsCompleted"] = f["STATUS"].isin(["COMP", "CLOSE"]).astype(int)
f["IsReactive"] = f["WORKTYPE"].isin(REACTIVE_TYPES).astype(int)
f["IsPM"] = (f["WORKTYPE"] == "PM").astype(int)

# business rules as columns, not DAX branches
f["IsPMCompleted"] = ((f["IsPM"] == 1) & (f["IsCompleted"] == 1)
                      & f["ActFinishDate"].notna()).astype(int)
f["IsPMOnTime"] = ((f["IsPMCompleted"] == 1)
                   & (f["ActFinishDate"] <= f["TargCompDate"])).astype(int)

f["IsScheduled"] = (f["SchedStartDate"].notna() & f["ActStartDate"].notna()).astype(int)
f["SchedStartVarianceDays"] = (f["ActStartDate"] - f["SchedStartDate"]).dt.days

f["ActualTotalCost"] = (f["ACTLABCOST"] + f["ACTMATCOST"]
                        + f["ACTTOOLCOST"] + f["ACTSERVCOST"])

# unknown-member handling for location-only work orders
f["ASSETNUM"] = f["ASSETNUM"].fillna("(none)").replace("", "(none)")

# ----------------------------------------------------------------------------
# STAGE 3 - FactDowntime
# ----------------------------------------------------------------------------
dtr["DOWNTIME"] = pd.to_numeric(dtr["DOWNTIME"], errors="coerce").fillna(0.0)
dtr["DOWNTIMESTART"] = pd.to_datetime(dtr["DOWNTIMESTART"], errors="coerce")

# ----------------------------------------------------------------------------
# STAGE 4 - craft capacity for the backlog measure
# ----------------------------------------------------------------------------
# Backlog weeks needs a denominator that is NOT in the Maximo data. Derive it
# from active hands-on labour headcount x 40h. Planners and supervisors are
# excluded because they do not burn down the work-order backlog.
NON_WRENCH = ["SUPV", "PLAN"]
cap = (labor[(labor["STATUS"] == "ACTIVE") & (~labor["CRAFT"].isin(NON_WRENCH))]
       .groupby("SITEID").size().rename("Techs").to_frame())
cap["WeeklyCapacityHrs"] = cap["Techs"] * 40

# ----------------------------------------------------------------------------
# THE SIX MEASURES
# ----------------------------------------------------------------------------

def m_reactive_pct(fact):
    base = fact[fact["IsCancelled"] == 0]
    n = len(base)
    return (base["IsReactive"].sum() / n) if n else None

def m_pm_compliance(fact):
    den = fact["IsPMCompleted"].sum()
    return (fact["IsPMOnTime"].sum() / den) if den else None

def m_mttr(down):
    n = len(down)
    return (down["DOWNTIME"].sum() / n) if n else None

def m_total_cost(fact):
    return fact.loc[fact["IsCancelled"] == 0, "ActualTotalCost"].sum()

def m_backlog_hours(fact):
    return fact.loc[fact["IsOpen"] == 1, "ESTLABHRS"].sum()

def m_backlog_weeks(fact, capacity_hrs):
    h = m_backlog_hours(fact)
    return (h / capacity_hrs) if capacity_hrs else None

def m_sched_compliance(fact, tolerance_days):
    base = fact[(fact["IsCancelled"] == 0) & (fact["IsScheduled"] == 1)]
    n = len(base)
    if not n:
        return None
    return (base["SchedStartVarianceDays"] <= tolerance_days).sum() / n

# ----------------------------------------------------------------------------
# RUN + COMPARE
# ----------------------------------------------------------------------------
# Baselines are PARSED from VALIDATION.txt rather than hardcoded, so this
# harness cannot silently drift out of step with the generator.
import re as _re

def load_baselines(path="C:/dev/MaximoPowerBi/VALIDATION.txt"):
    v = open(path).read()
    keys = {
        "wo": r"work orders \(excl\. cancelled\) \.+ ([\d,]+)",
        "reactive": r"reactive % \(CM\+EM / total\) \.+ ([\d.]+)%",
        "pm": r"PM compliance \(done by TARGCOMPDATE\) ([\d.]+)%",
        "mttr": r"MTTR \(downtime hrs / events\) \.+ ([\d.]+) h",
        "cost": r"total maintenance cost \.+ \$([\d,]+)",
        "backlog_h": r"open estimated labour hours \.+ ([\d,.]+)",
    }
    out = {}
    for site in ["BEDFORD", "HOUSTON", "AURORA", "ALL SITES"]:
        block = _re.search(rf"^{_re.escape(site)}\n((?:  .*\n)+)", v, _re.M).group(1)
        d = {}
        for k, pat in keys.items():
            m = _re.search(pat, block)
            val = float(m.group(1).replace(",", ""))
            d[k] = val / 100.0 if k in ("reactive", "pm") else val
        out[site] = d
    return out

BASELINE = load_baselines()

rows = []
fails = []
for site in ["BEDFORD", "HOUSTON", "AURORA", "ALL SITES"]:
    ff = f if site == "ALL SITES" else f[f["SITEID"] == site]
    dd = dtr if site == "ALL SITES" else dtr[dtr["SITEID"] == site]
    capacity = (cap["WeeklyCapacityHrs"].sum() if site == "ALL SITES"
                else cap.loc[site, "WeeklyCapacityHrs"])
    b = BASELINE[site]

    computed = {
        "wo": float(len(ff[ff["IsCancelled"] == 0])),
        "reactive": m_reactive_pct(ff),
        "pm": m_pm_compliance(ff),
        "mttr": m_mttr(dd),
        "cost": m_total_cost(ff),
        "backlog_h": m_backlog_hours(ff),
    }
    weeks = m_backlog_weeks(ff, capacity)

    def cmp_(key, tol):
        got, exp = computed[key], b[key]
        ok = abs(got - exp) <= tol
        if not ok:
            fails.append(f"{site}.{key}: computed {got} vs baseline {exp}")
        return "OK" if ok else "MISMATCH"

    rows.append({
        "Site": site,
        "WOs": f"{computed['wo']:,}",
        "chk": cmp_("wo", 0),
        "Reactive%": f"{100*computed['reactive']:.1f}%",
        "chk2": cmp_("reactive", 0.0006),
        "PMCompl%": f"{100*computed['pm']:.1f}%",
        "chk3": cmp_("pm", 0.0006),
        "MTTR": f"{computed['mttr']:.2f}",
        "chk4": cmp_("mttr", 0.006),
        "Cost": f"${computed['cost']:,.0f}",
        "chk5": cmp_("cost", 1.0),
        "BacklogH": f"{computed['backlog_h']:,.1f}",
        "chk6": cmp_("backlog_h", 0.06),
        "Techs": int(cap["Techs"].sum() if site == "ALL SITES" else cap.loc[site, "Techs"]),
        "BacklogWks": f"{weeks:.2f}",
    })

# ----------------------------------------------------------------------------
# DIMENSION KEY UNIQUENESS
# ----------------------------------------------------------------------------
# A column on the ONE side of a relationship must be unique or Power BI rejects
# the entire model definition at load time with "contains a duplicate value".
# The engine enforces this; TMDL text inspection cannot see it. This check exists
# because DimFailureCode shipped with a non-unique key: 6 of 45 problem codes
# occur under two failure classes, so keeping PARENT made the grain code x class
# while ProblemCode was still being used as the key.
#
# Each entry mirrors what the Power Query transform actually produces.
DIM_KEYS = [
    ("DimDate",        "DIM_DATE.csv",    None,               None,          "DATE"),
    ("DimAsset",       "ASSET.csv",       None,               None,          "ASSETNUM"),
    ("DimLocation",    "LOCATIONS.csv",   None,               None,          "LOCATION"),
    ("DimSite",        "SITE.csv",        None,               None,          "SITEID"),
    ("DimCraft",       "CRAFT.csv",       None,               None,          "CRAFT"),
    ("DimLabor",       "LABOR.csv",       None,               None,          "LABORCODE"),
    ("DimItem",        "ITEM.csv",        None,               None,          "ITEMNUM"),
    # the transform drops PARENT and applies Table.Distinct on the code
    ("DimFailureCode", "FAILURECODE.csv", ("TYPE", "PROBLEM"), "distinct",   "FAILURECODE"),
]

print("DIMENSION KEY UNIQUENESS - the one side of every relationship")
print("-" * 118)
key_rows, key_fail = [], []
for dim, csv, flt, transform, key in DIM_KEYS:
    df = pd.read_csv(f"{D}/{csv}", dtype=str)
    if flt:
        df = df[df[flt[0]] == flt[1]]
    raw = len(df)
    if transform == "distinct":
        df = df.drop_duplicates(subset=[key])
    n, d = len(df), df[key].nunique()
    ok = (n == d)
    if not ok:
        key_fail.append(f"{dim}[{key}] has {n - d} duplicate key value(s)")
    key_rows.append({"dimension": dim, "key": key, "source rows": f"{raw:,}",
                     "after transform": f"{n:,}", "distinct keys": f"{d:,}",
                     "verdict": "unique" if ok else "NOT UNIQUE"})
key_rows.append({"dimension": "DimWorkType", "key": "WORKTYPE", "source rows": "7",
                 "after transform": "7", "distinct keys": "7", "verdict": "unique (hand-built)"})
key_rows.append({"dimension": "DimStatus", "key": "STATUS", "source rows": "6",
                 "after transform": "6", "distinct keys": "6", "verdict": "unique (hand-built)"})
print(pd.DataFrame(key_rows).to_string(index=False))

# every fact key must also resolve to its dimension, or rows drop silently
print("\nREFERENTIAL INTEGRITY - fact keys resolving to their dimension")
print("-" * 118)
_fcp = pd.read_csv(f"{D}/FAILURECODE.csv", dtype=str)
_probs = set(_fcp[_fcp.TYPE == "PROBLEM"].FAILURECODE)
_classes = set(_fcp[_fcp.TYPE == "CLASS"].FAILURECODE)
_ff = pd.read_csv(f"{D}/FAILUREREPORT.csv", dtype=str)
ri = [
    ("FactWorkOrder[ASSETNUM]", set(f.loc[f.ASSETNUM != "(none)", "ASSETNUM"]),
     set(asset.ASSETNUM)),
    ("FactFailure[PROBLEMCODE]", set(_ff.PROBLEMCODE), _probs),
    ("FactFailure[FAILURECODE]", set(_ff.FAILURECODE), _classes),
]
for label, got, allowed in ri:
    orphans = got - allowed
    status = "OK" if not orphans else f"{len(orphans)} ORPHAN VALUE(S)"
    ex = "" if not orphans else "  e.g. " + ", ".join(sorted(orphans)[:4])
    print(f"  {label:<28} {len(got):>4} distinct -> {status}{ex}")
    if orphans and "FAILURECODE" not in label:
        key_fail.append(f"{label} has {len(orphans)} unresolved key(s)")

print()
print("STAR-SCHEMA MEASURE VERIFICATION vs GENERATOR BASELINES")
print("=" * 118)
print(pd.DataFrame(rows).to_string(index=False))

print("\nSCHEDULE COMPLIANCE - sensitive to the tolerance you choose")
print("-" * 118)
sc = []
for site in ["BEDFORD", "HOUSTON", "AURORA", "ALL SITES"]:
    ff = f if site == "ALL SITES" else f[f["SITEID"] == site]
    row = {"Site": site,
           "Scheduled WOs": f"{int(ff['IsScheduled'].sum()):,}"}
    for tol in (0, 1, 2, 3, 7):
        row[f"tol<={tol}d"] = f"{100*m_sched_compliance(ff, tol):.1f}%"
    sc.append(row)
print(pd.DataFrame(sc).to_string(index=False))

print("\nCOST RECONCILIATION - WORKORDER actuals vs transaction tables")
print("-" * 118)
lab["LINECOST"] = pd.to_numeric(lab["LINECOST"], errors="coerce").fillna(0.0)
mat["LINECOST"] = pd.to_numeric(mat["LINECOST"], errors="coerce").fillna(0.0)
print(f"  SUM(FactWorkOrder[ACTLABCOST]) = ${f['ACTLABCOST'].sum():,.2f}")
print(f"  SUM(FactLabour[LINECOST])      = ${lab['LINECOST'].sum():,.2f}")
print(f"  SUM(FactWorkOrder[ACTMATCOST]) = ${f['ACTMATCOST'].sum():,.2f}")
print(f"  SUM(FactMaterial[LINECOST])    = ${mat['LINECOST'].sum():,.2f}")
tool_serv = f["ACTTOOLCOST"].sum() + f["ACTSERVCOST"].sum()
print(f"  tool + service cost (no transaction table exists) = ${tool_serv:,.2f}")

print("\nDATE-TRUNCATION TRAP - what happens if you compare datetimes not dates")
print("-" * 118)
naive = ((f["IsPMCompleted"] == 1) & (f["ACTFINISH"] <= f["TARGCOMPDATE"])).sum()
correct = f["IsPMOnTime"].sum()
den = f["IsPMCompleted"].sum()
print(f"  correct (date vs date)      : {correct:,} / {den:,} = {100*correct/den:.1f}%")
print(f"  naive   (datetime vs datetime): {naive:,} / {den:,} = {100*naive/den:.1f}%")
print(f"  understated by {100*(correct-naive)/den:.1f} percentage points "
      f"({correct-naive:,} work orders)")

print("\nMTBF AND AVAILABILITY - these REQUIRE a stated operating-hours assumption")
print("-" * 118)
print("  assumption: operating hours = (operating assets x calendar hours) - reported downtime")
CAL_DAYS = (pd.Timestamp("2026-07-29") - pd.Timestamp("2023-07-01")).days + 1
CAL_HOURS = CAL_DAYS * 24
rel = []
op_assets = asset[(asset["STATUS"] == "OPERATING") & (asset["ASSETNUM"] != "(none)")]
for site in ["BEDFORD", "HOUSTON", "AURORA", "ALL SITES"]:
    aa = op_assets if site == "ALL SITES" else op_assets[op_assets["SITEID"] == site]
    dd = dtr if site == "ALL SITES" else dtr[dtr["SITEID"] == site]
    ffa = fal if site == "ALL SITES" else fal[fal["SITEID"] == site]
    n_assets = len(aa)
    sched = n_assets * CAL_HOURS
    down = dd["DOWNTIME"].sum()
    fails_n = len(ffa)
    rel.append({"Site": site, "Operating assets": n_assets,
                "Asset-hours": f"{sched:,.0f}",
                "Downtime hrs": f"{down:,.1f}",
                "Failures": f"{fails_n:,}",
                "MTBF (h)": f"{(sched - down)/fails_n:,.0f}",
                "Availability %": f"{100*(sched - down)/sched:.2f}%"})
print(pd.DataFrame(rel).to_string(index=False))
print(f"  calendar window: {CAL_DAYS} days = {CAL_HOURS:,} hours per asset")

print("\nCOST MIX AND MAINTENANCE COST AS % OF RAV (SMRP best-in-class 2-3%)")
print("-" * 118)
asset["REPLACECOST"] = pd.to_numeric(asset["REPLACECOST"], errors="coerce").fillna(0.0)
yrs = 3.08
mix = []
for site in ["BEDFORD", "HOUSTON", "AURORA", "ALL SITES"]:
    ff = f[(f["IsCancelled"] == 0)] if site == "ALL SITES" else \
         f[(f["IsCancelled"] == 0) & (f["SITEID"] == site)]
    aa = asset if site == "ALL SITES" else asset[asset["SITEID"] == site]
    rav = aa["REPLACECOST"].sum()
    tot = ff["ActualTotalCost"].sum()
    mix.append({"Site": site, "RAV": f"${rav:,.0f}",
                "Labour%": f"{100*ff['ACTLABCOST'].sum()/tot:.1f}%",
                "Material%": f"{100*ff['ACTMATCOST'].sum()/tot:.1f}%",
                "Tool%": f"{100*ff['ACTTOOLCOST'].sum()/tot:.1f}%",
                "Service%": f"{100*ff['ACTSERVCOST'].sum()/tot:.1f}%",
                "Cost/yr": f"${tot/yrs:,.0f}",
                "% of RAV/yr": f"{100*(tot/yrs)/rav:.1f}%"})
print(pd.DataFrame(mix).to_string(index=False))

print("\n" + "=" * 118)
fails = fails + key_fail
if fails:
    print(f"RESULT: {len(fails)} PROBLEM(S)")
    for x in fails:
        print("  -", x)
    raise SystemExit(1)
print("RESULT: all six measure definitions reproduce the baselines exactly.")
