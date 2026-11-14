#!/usr/bin/env python3
"""
pull_mockup_numbers.py - compute every figure the page mockups display, from the
source CSVs, so nothing on a mockup is invented.

Writes outputs/mockup_numbers.json and prints a readable summary.

    cd C:\\dev\\MaximoPowerBi
    py -3 scripts\\pull_mockup_numbers.py
"""
import json
import os
import sys

import pandas as pd

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
ANCHOR = pd.Timestamp("2026-07-29")          # data cutoff, per DimDate[ISPASTORTODAY]
WINDOW_DAYS = 1125
OPEN_STATUSES = ["WAPPR", "APPR", "INPRG"]
REACTIVE = ["CM", "EM"]

def load(name, dates=(), nums=()):
    df = pd.read_csv(os.path.join(D, f"{name}.csv"), dtype=str, low_memory=False)
    for c in dates:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in nums:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df

wo = load("WORKORDER",
          dates=["REPORTDATE", "TARGCOMPDATE", "SCHEDSTART", "ACTSTART", "ACTFINISH"],
          nums=["ESTLABHRS", "ACTLABHRS", "ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST",
                "ACTSERVCOST", "DOWNTIME"])
asset = load("ASSET", dates=["INSTALLDATE"], nums=["REPLACECOST", "CRITICALITY"])
dtr = load("DOWNTIMEREPORT", dates=["DOWNTIMESTART"], nums=["DOWNTIME"])
fal = load("FAILUREREPORT", dates=["REPORTDATE"])
fcode = load("FAILURECODE")
labor = load("LABOR")
meter = load("METERREADING", dates=["READINGDATE"], nums=["READING"])

# ---- derived work-order columns (mirrors the Power Query logic) -------------
wo["ActFinishDate"] = wo["ACTFINISH"].dt.normalize()
wo["TargCompDate"] = wo["TARGCOMPDATE"].dt.normalize()
wo["ActStartDate"] = wo["ACTSTART"].dt.normalize()
wo["SchedStartDate"] = wo["SCHEDSTART"].dt.normalize()
wo["ReportDate"] = wo["REPORTDATE"].dt.normalize()
wo["IsCancelled"] = (wo["STATUS"] == "CAN").astype(int)
wo["IsOpen"] = wo["STATUS"].isin(OPEN_STATUSES).astype(int)
wo["IsCompleted"] = wo["STATUS"].isin(["COMP", "CLOSE"]).astype(int)
wo["IsPM"] = (wo["WORKTYPE"] == "PM").astype(int)
wo["IsPMCompleted"] = ((wo["IsPM"] == 1) & (wo["IsCompleted"] == 1)
                       & wo["ActFinishDate"].notna()).astype(int)
wo["IsPMOnTime"] = ((wo["IsPMCompleted"] == 1)
                    & (wo["ActFinishDate"] <= wo["TargCompDate"])).astype(int)
wo["IsScheduled"] = (wo["SchedStartDate"].notna() & wo["ActStartDate"].notna()).astype(int)
wo["SchedVar"] = (wo["ActStartDate"] - wo["SchedStartDate"]).dt.days
wo["DaysOpen"] = (ANCHOR - wo["ReportDate"]).dt.days

R = {}

# ---- 1. downtime by failure mode (page 1 Pareto) ---------------------------
fc = fcode[fcode["TYPE"] == "PROBLEM"][["FAILURECODE", "DESCRIPTION"]].drop_duplicates("FAILURECODE")
dt_mode = (dtr.merge(fc, left_on="PROBLEMCODE", right_on="FAILURECODE", how="left")
              .groupby(dtr["PROBLEMCODE"].fillna("(none)"))["DOWNTIME"].sum()
              .sort_values(ascending=False))
lookup = dict(zip(fc["FAILURECODE"], fc["DESCRIPTION"]))
top_modes = [(lookup.get(k, k), round(v, 1)) for k, v in dt_mode.head(9).items()]
other = round(dt_mode.iloc[9:].sum(), 1)
R["downtime_by_mode"] = top_modes + [("Other", other)]
R["downtime_total"] = round(dtr["DOWNTIME"].sum(), 1)
R["downtime_top3_share"] = round(dt_mode.head(3).sum() / dtr["DOWNTIME"].sum() * 100, 1)

# ---- 2. bad actors (pages 3 and 5) -----------------------------------------
f_by_asset = fal.groupby("ASSETNUM").size().rename("failures")
d_by_asset = dtr.groupby("ASSETNUM")["DOWNTIME"].sum().rename("downtime")
a = asset.set_index("ASSETNUM")
bad = (pd.concat([f_by_asset, d_by_asset], axis=1).fillna(0)
         .join(a[["SITEID", "CRITICALITY", "REPLACECOST", "ASSETTYPE", "DESCRIPTION"]])
         .sort_values("failures", ascending=False))
bad["mtbf"] = (WINDOW_DAYS * 24 / bad["failures"]).round(0)
R["bad_actors"] = [
    dict(asset=i, failures=int(r.failures), downtime=round(r.downtime, 1),
         mtbf=int(r.mtbf), crit=int(r.CRITICALITY) if pd.notna(r.CRITICALITY) else None,
         rav=int(r.REPLACECOST), site=r.SITEID, atype=r.ASSETTYPE)
    for i, r in bad.head(10).iterrows()]
R["bad_actor_count"] = int((bad["failures"] >= 18).sum())

# ---- 3. PM compliance by month and site (due-date basis) -------------------
pm = wo[wo["IsPMCompleted"] == 1].copy()
pm["m"] = pm["TargCompDate"].dt.to_period("M")
g = pm.groupby(["SITEID", "m"]).agg(ontime=("IsPMOnTime", "sum"), done=("IsPMCompleted", "sum"))
g["pct"] = (g["ontime"] / g["done"] * 100).round(1)
last12 = sorted(pm["m"].dropna().unique())[-13:-1]
R["pm_monthly"] = {s: [float(g.loc[(s, m), "pct"]) if (s, m) in g.index else None for m in last12]
                   for s in sorted(wo["SITEID"].unique())}
R["pm_months"] = [str(m) for m in last12]

# ---- 4. schedule compliance by tolerance -----------------------------------
base = wo[(wo["IsCancelled"] == 0) & (wo["IsScheduled"] == 1)]
R["sched_by_tolerance"] = [(t, round((base["SchedVar"] <= t).mean() * 100, 1)) for t in range(0, 11)]

# ---- 5. due date vs report date, monthly -----------------------------------
pm_r = pm.copy(); pm_r["m"] = pm_r["ReportDate"].dt.to_period("M")
gr = pm_r.groupby("m").agg(ontime=("IsPMOnTime", "sum"), done=("IsPMCompleted", "sum"))
gd = pm.groupby("m").agg(ontime=("IsPMOnTime", "sum"), done=("IsPMCompleted", "sum"))
R["pm_due_vs_report"] = {
    "months": [str(m) for m in last12],
    "due": [round(float(gd.loc[m, "ontime"] / gd.loc[m, "done"] * 100), 1) if m in gd.index else None for m in last12],
    "report": [round(float(gr.loc[m, "ontime"] / gr.loc[m, "done"] * 100), 1) if m in gr.index else None for m in last12]}

# ---- 6. statutory / inspection compliance ----------------------------------
stat = wo[wo["WORKTYPE"].isin(["INSP", "SAF"])].copy()
stat_done = stat[(stat["IsCompleted"] == 1) & stat["ActFinishDate"].notna()]
stat_ontime = (stat_done["ActFinishDate"] <= stat_done["TargCompDate"])
R["statutory"] = dict(total=int(len(stat_done)), ontime=int(stat_ontime.sum()),
                      late=int((~stat_ontime).sum()),
                      pct=round(stat_ontime.mean() * 100, 1))
sd = stat_done.join(a[["ASSETTYPE"]], on="ASSETNUM")
sd["late"] = ~stat_ontime
by_type = sd.groupby(sd["ASSETTYPE"].fillna("(no asset)")).agg(
    total=("late", "size"), late=("late", "sum")).sort_values("total", ascending=False)
R["statutory_by_assettype"] = [dict(assettype=i, total=int(r.total), late=int(r.late))
                               for i, r in by_type.head(8).iterrows()]
late_rows = stat_done[~stat_ontime].copy()
late_rows["days"] = (late_rows["ActFinishDate"] - late_rows["TargCompDate"]).dt.days
R["statutory_worst"] = [dict(wonum=r.WONUM, asset=r.ASSETNUM, due=str(r.TargCompDate.date()), days=int(r.days))
                        for r in late_rows.nlargest(6, "days").itertuples()]

# ---- 7. meter drift candidates ---------------------------------------------
fail_assets = set(bad.head(30).index)
mm = meter[meter["ASSETNUM"].isin(fail_assets)]
cands = []
for an, grp in mm.groupby("ASSETNUM"):
    for mn, g2 in grp.groupby("METERNAME"):
        g2 = g2.sort_values("READINGDATE")
        if len(g2) < 12:
            continue
        first, last = g2["READING"].head(6).mean(), g2["READING"].tail(6).mean()
        if first > 0 and last / first > 1.25:
            fdates = fal[fal["ASSETNUM"] == an]["REPORTDATE"].dropna()
            cands.append(dict(asset=an, meter=mn, unit=g2["MEASUREUNITID"].iloc[0],
                              start=round(float(first), 2), end=round(float(last), 2),
                              rise_pct=round((last / first - 1) * 100, 1),
                              readings=int(len(g2)), failures=int(len(fdates))))
R["meter_drift_candidates"] = sorted(cands, key=lambda c: -c["rise_pct"])[:8]

# ---- 8. MTTR distribution ---------------------------------------------------
R["mttr"] = {}
for site, grp in dtr.groupby("SITEID"):
    q = grp["DOWNTIME"].quantile([.1, .25, .5, .75, .9, .95]).round(2)
    R["mttr"][site] = dict(mean=round(grp["DOWNTIME"].mean(), 2), p10=float(q[.1]),
                           p25=float(q[.25]), median=float(q[.5]), p75=float(q[.75]),
                           p90=float(q[.9]), p95=float(q[.95]), events=int(len(grp)))

# ---- 9. RAV and downtime share by criticality -------------------------------
a2 = asset[asset["ASSETNUM"] != "(none)"].copy()
a2["crit"] = a2["CRITICALITY"].fillna(4).astype(int)
rav = a2.groupby("crit")["REPLACECOST"].sum()
dt_by_crit = (dtr.join(a.set_index(a.index)["CRITICALITY"], on="ASSETNUM")
                 .assign(crit=lambda x: x["CRITICALITY"].fillna(4).astype(int))
                 .groupby("crit")["DOWNTIME"].sum())
R["by_criticality"] = [dict(crit=int(c), rav_m=round(rav.get(c, 0) / 1e6, 1),
                            downtime_pct=round(dt_by_crit.get(c, 0) / dt_by_crit.sum() * 100, 1))
                       for c in sorted(rav.index)]

# ---- 10. age profile --------------------------------------------------------
a2["age"] = (ANCHOR - a2["INSTALLDATE"]).dt.days / 365.25
bins = list(range(0, 30, 2))
hist = pd.cut(a2["age"].dropna(), bins=bins + [99], right=False).value_counts().sort_index()
R["age_profile"] = [int(v) for v in hist.values][:14]
R["age_median"] = round(float(a2["age"].median()), 1)
R["age_over_18"] = int((a2["age"] >= 18).sum())

# ---- 11. intake vs completion, monthly --------------------------------------
wo["rm"] = wo["ReportDate"].dt.to_period("M")
wo["fm"] = wo["ActFinishDate"].dt.to_period("M")
raised = wo[wo["IsCancelled"] == 0].groupby("rm").size()
done = wo[wo["IsCompleted"] == 1].groupby("fm").size()
R["intake_vs_completion"] = dict(
    months=[str(m) for m in last12],
    raised=[int(raised.get(m, 0)) for m in last12],
    completed=[int(done.get(m, 0)) for m in last12])

# ---- 12. capacity vs committed ----------------------------------------------
NON_WRENCH = ["SUPV", "PLAN"]
cap = (labor[(labor["STATUS"] == "ACTIVE") & (~labor["CRAFT"].isin(NON_WRENCH))]
       .groupby("SITEID").size() * 40)
comm = wo[wo["IsOpen"] == 1].groupby("SITEID")["ESTLABHRS"].sum().round(1)
R["capacity"] = {s: dict(capacity=int(cap.get(s, 0)), committed=float(comm.get(s, 0))) for s in cap.index}

# ---- 13. PM due next 14 days -------------------------------------------------
due = wo[(wo["IsOpen"] == 1) & (wo["IsPM"] == 1)
         & (wo["TargCompDate"] >= ANCHOR) & (wo["TargCompDate"] <= ANCHOR + pd.Timedelta(days=14))]
R["pm_due_14d"] = {s: int(n) for s, n in due.groupby("SITEID").size().items()}
R["pm_due_14d_total"] = int(len(due))

os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "mockup_numbers.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(R, fh, indent=2, default=str)

# ------------------------------------------------------------------ summary --
print("=" * 78)
print("REAL NUMBERS FOR THE MOCKUPS")
print("=" * 78)
print(f"\nDOWNTIME BY FAILURE MODE  (total {R['downtime_total']:,.0f} h, "
      f"top 3 = {R['downtime_top3_share']}%)")
for nm, v in R["downtime_by_mode"]:
    print(f"   {nm:<34} {v:>10,.0f} h")
print(f"\nTOP BAD ACTORS  ({R['bad_actor_count']} assets at 18+ failures)")
for b in R["bad_actors"]:
    print(f"   {b['asset']:<18} {b['failures']:>3} fail  {b['downtime']:>8,.0f} h  "
          f"MTBF {b['mtbf']:>6,} h  crit {b['crit']}  ${b['rav']:,}  {b['site']}")
print(f"\nSTATUTORY (INSP + SAF): {R['statutory']['ontime']:,} of {R['statutory']['total']:,} "
      f"on time = {R['statutory']['pct']}%  ({R['statutory']['late']} late)")
for r in R["statutory_by_assettype"]:
    print(f"   {r['assettype']:<28} {r['total']:>4} total  {r['late']:>3} late")
print("\n   worst late:")
for r in R["statutory_worst"]:
    print(f"     {r['asset']:<18} due {r['due']}  {r['days']:>3} days late")
print("\nSCHEDULE COMPLIANCE BY TOLERANCE")
print("   " + "  ".join(f"{t}d={v}%" for t, v in R["sched_by_tolerance"]))
print("\nPM COMPLIANCE, LAST 12 MONTHS (due-date basis)")
for s, vals in R["pm_monthly"].items():
    print(f"   {s:<10} " + " ".join(f"{v:5.1f}" if v else "    -" for v in vals))
print("\nPM DUE vs REPORT DATE (monthly)")
print("   due   : " + " ".join(f"{v:5.1f}" if v else "    -" for v in R["pm_due_vs_report"]["due"]))
print("   report: " + " ".join(f"{v:5.1f}" if v else "    -" for v in R["pm_due_vs_report"]["report"]))
print("\nMTTR DISTRIBUTION")
for s, m in R["mttr"].items():
    print(f"   {s:<10} mean {m['mean']:>6}  median {m['median']:>6}  "
          f"p75 {m['p75']:>6}  p90 {m['p90']:>6}  p95 {m['p95']:>6}  n={m['events']:,}")
print("\nBY CRITICALITY")
for c in R["by_criticality"]:
    print(f"   criticality {c['crit']}   RAV ${c['rav_m']}M   {c['downtime_pct']}% of downtime")
print(f"\nAGE PROFILE (median {R['age_median']} yrs, {R['age_over_18']} assets 18+ yrs)")
print("   " + " ".join(f"{v}" for v in R["age_profile"]))
print("\nINTAKE vs COMPLETION (last 12 months)")
print("   raised   : " + " ".join(f"{v:>5}" for v in R["intake_vs_completion"]["raised"]))
print("   completed: " + " ".join(f"{v:>5}" for v in R["intake_vs_completion"]["completed"]))
print("\nCAPACITY vs COMMITTED")
for s, c in R["capacity"].items():
    print(f"   {s:<10} capacity {c['capacity']:>6,} h   committed {c['committed']:>9,.1f} h")
print(f"\nPM DUE NEXT 14 DAYS: {R['pm_due_14d_total']}  {R['pm_due_14d']}")
print("\nMETER DRIFT CANDIDATES")
for c in R["meter_drift_candidates"]:
    print(f"   {c['asset']:<18} {c['meter']:<14} {c['start']:>8} -> {c['end']:>8} "
          f"{c['unit']:<8} +{c['rise_pct']}%  {c['failures']} failures")
print("\n" + "=" * 78)
print(f"written: {path}")
