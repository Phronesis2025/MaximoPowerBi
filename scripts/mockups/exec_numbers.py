"""Every figure the Executive mockup shows, computed from the source CSVs."""
import json, sys
import pandas as pd
import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
D = _os.path.join(HERE, "..", "..", "data")
ANCHOR = pd.Timestamp("2026-07-29")
SITES = ["BEDFORD", "AURORA", "HOUSTON"]

def rd(n, dates=(), nums=()):
    df = pd.read_csv(f"{D}/{n}.csv", dtype=str, low_memory=False)
    for c in dates: df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in nums: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df

wo = rd("WORKORDER", ["REPORTDATE", "TARGCOMPDATE", "ACTFINISH"],
        ["ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST"])
asset = rd("ASSET", nums=["REPLACECOST"])
dtr = rd("DOWNTIMEREPORT", ["DOWNTIMESTART"], ["DOWNTIME"])
fal = rd("FAILUREREPORT", ["REPORTDATE"])

wo["rd"] = wo["REPORTDATE"].dt.normalize()
wo["tc"] = wo["TARGCOMPDATE"].dt.normalize()
wo["af"] = wo["ACTFINISH"].dt.normalize()
wo["canc"] = wo["STATUS"] == "CAN"
wo["react"] = wo["WORKTYPE"].isin(["CM", "EM"])
wo["comp"] = wo["STATUS"].isin(["COMP", "CLOSE"]) & wo["af"].notna()
wo["ontime"] = wo["comp"] & (wo["af"] <= wo["tc"])
wo["cost"] = wo[["ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST"]].sum(axis=1)
pm = wo[(wo["WORKTYPE"] == "PM") & wo["comp"]]
st = wo[wo["WORKTYPE"].isin(["INSP", "SAF"]) & wo["comp"]]
opa = asset[(asset["STATUS"] == "OPERATING") & (asset["ASSETNUM"] != "(none)")]
rav = asset[asset["ASSETNUM"] != "(none)"]

def sub(df, site): return df if site == "ALL" else df[df["SITEID"] == site]

def metrics(site, lo=None, hi=None, days=1125):
    w, p, s = sub(wo, site), sub(pm, site), sub(st, site)
    d, f = sub(dtr, site), sub(fal, site)
    if lo is not None:
        w = w[(w["rd"] > lo) & (w["rd"] <= hi)]
        p = p[(p["tc"] > lo) & (p["tc"] <= hi)]
        s = s[(s["tc"] > lo) & (s["tc"] <= hi)]
        d = d[(d["DOWNTIMESTART"] > lo) & (d["DOWNTIMESTART"] <= hi)]
        f = f[(f["REPORTDATE"] > lo) & (f["REPORTDATE"] <= hi)]
    nc = w[~w["canc"]]
    hours = len(sub(opa, site)) * days * 24
    yrs = days / 365.25
    return dict(
        reactive=nc["react"].mean() * 100,
        pm=p["ontime"].mean() * 100,
        stat=s["ontime"].mean() * 100, stat_late=int((~s["ontime"]).sum()), stat_n=len(s),
        mtbf=(hours - d["DOWNTIME"].sum()) / max(len(f), 1),
        costrav=nc["cost"].sum() / yrs / sub(rav, site)["REPLACECOST"].sum() * 100)

R = {"full": {s: metrics(s) for s in SITES + ["ALL"]}}

# 12-month rolling values, month-ends Jul 2024 .. Jul 2026 (anchor month uses the cutoff)
ends = list(pd.date_range("2024-07-31", "2026-06-30", freq="ME")) + [ANCHOR]
R["months"] = [e.strftime("%b %y") for e in ends]
R["rolling"] = {}
for s in SITES + ["ALL"]:
    R["rolling"][s] = [metrics(s, e - pd.DateOffset(months=12), e, 365) for e in ends]

# last-year comparison for the cards: window ending at anchor vs the one before
R["ly"] = metrics("ALL", ANCHOR - pd.DateOffset(months=24), ANCHOR - pd.DateOffset(months=12), 365)
R["ty"] = metrics("ALL", ANCHOR - pd.DateOffset(months=12), ANCHOR, 365)

out = _os.path.join(HERE, "exec_numbers.json")
json.dump(R, open(out, "w"), indent=1, default=float)

f = R["full"]
print("FULL PERIOD          React    PM   Stat (late/n)        MTBF  Cost%RAV")
for s in SITES + ["ALL"]:
    m = f[s]
    print(f"  {s:<9} {m['reactive']:7.1f} {m['pm']:6.1f} {m['stat']:6.1f} ({m['stat_late']}/{m['stat_n']}) {m['mtbf']:9.0f} {m['costrav']:8.1f}")
print("\nROLLING 12M REACTIVE % (first .. last):")
for s in SITES + ["ALL"]:
    v = [r["reactive"] for r in R["rolling"][s]]
    print(f"  {s:<9} {v[0]:.1f} -> {v[-1]:.1f}   ({v[-1]-v[0]:+.1f})")
print("\nROLLING 12M PM % (first .. last):")
for s in SITES + ["ALL"]:
    v = [r["pm"] for r in R["rolling"][s]]
    print(f"  {s:<9} {v[0]:.1f} -> {v[-1]:.1f}   ({v[-1]-v[0]:+.1f})")
print("\nLAST 12M vs PRIOR 12M (ALL):")
for k in ("reactive", "pm", "stat", "mtbf", "costrav"):
    print(f"  {k:<9} {R['ly'][k]:9.2f} -> {R['ty'][k]:9.2f}")
