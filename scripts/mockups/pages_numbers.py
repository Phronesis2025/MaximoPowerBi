"""Figures for the PM & Compliance, Reliability, Planning pages. Source: data/*.csv."""
import json, os
import pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
ANCHOR = pd.Timestamp("2026-07-29")
SITES = ["BEDFORD", "AURORA", "HOUSTON"]
def rd(n, dates=(), nums=()):
    df = pd.read_csv(f"{D}/{n}.csv", dtype=str, low_memory=False)
    for c in dates: df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in nums: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df
wo = rd("WORKORDER", ["REPORTDATE", "TARGCOMPDATE", "ACTFINISH", "SCHEDSTART", "ACTSTART"],
        ["ESTLABHRS", "ACTLABHRS", "ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST"])
asset = rd("ASSET")
fr = rd("FAILUREREPORT", ["REPORTDATE"])
dt = rd("DOWNTIMEREPORT", ["DOWNTIMESTART"], ["DOWNTIME"])
mr = rd("METERREADING", ["READINGDATE"], ["READING"])
lab = rd("LABOR"); lt = rd("LABTRANS", ["TRANSDATE"], ["REGULARHRS", "PREMIUMPAYHOURS", "LINECOST"])
fc = rd("FAILURECODE"); pmd = rd("PM")
O = {}
wo["af"], wo["tc"] = wo["ACTFINISH"].dt.normalize(), wo["TARGCOMPDATE"].dt.normalize()
wo["comp"] = wo["STATUS"].isin(["COMP", "CLOSE"]) & wo["af"].notna()
wo["late_days"] = (wo["af"] - wo["tc"]).dt.days
nc = wo[wo["STATUS"] != "CAN"]

# ---------------- PM & Compliance ----------------
pm = wo[(wo["WORKTYPE"] == "PM") & wo["comp"]].copy()
pm["late"] = pm["late_days"] > 0
st = wo[wo["WORKTYPE"].isin(["INSP", "SAF"]) & wo["comp"]].copy()
st["late"] = st["late_days"] > 0
P = {}
P["pm_n"] = len(pm); P["pm_late"] = int(pm["late"].sum())
P["pm_late_median_days"] = float(pm.loc[pm["late"], "late_days"].median())
P["pm_late_mean_days"] = float(pm.loc[pm["late"], "late_days"].mean())
bins = [0, 7, 30, 90, 10**6]; labs = ["1-7 d", "8-30 d", "31-90 d", "90+ d"]
P["late_buckets"] = {}
for s in SITES:
    x = pm[(pm["SITEID"] == s) & pm["late"]]["late_days"]
    P["late_buckets"][s] = pd.cut(x, bins, labels=labs).value_counts().reindex(labs).astype(int).tolist()
P["stat_by_type"] = {s: {t: {"n": int(len(g)), "late": int(g["late"].sum())}
                         for t, g in st[st["SITEID"] == s].groupby("WORKTYPE")} for s in SITES}
P["stat_late_median_days"] = float(st.loc[st["late"], "late_days"].median())
# worst PM schedules (>= 12 completed WOs)
g = pm.groupby("PMNUM").agg(n=("late", "size"), late=("late", "sum"), site=("SITEID", "first"),
                            asset=("ASSETNUM", "first"), med=("late_days", lambda v: float(v[v > 0].median()) if (v > 0).any() else 0))
g = g[g["n"] >= 12]
g["ontime"] = (1 - g["late"] / g["n"]) * 100
g = g.join(pmd.set_index("PMNUM")[["DESCRIPTION", "FREQUENCY", "FREQUNIT"]])
w = g.sort_values(["ontime", "n"], ascending=[True, False]).head(8)
P["worst_pms"] = [dict(pm=i, site=r.site, asset=r.asset, desc=r.DESCRIPTION, freq=f"{r.FREQUENCY} {r.FREQUNIT.lower()}",
                       n=int(r.n), late=int(r.late), ontime=round(r.ontime, 1), med=r.med) for i, r in w.iterrows()]
P["pm_sched_n"] = int(len(g)); P["pm_sched_below_80"] = int((g["ontime"] < 80).sum())
# PM compliance by priority (all sites)
P["pm_by_priority"] = {p: round((1 - x["late"].mean()) * 100, 1) for p, x in pm.groupby("WOPRIORITY")}
O["pm"] = P

# ---------------- Reliability ----------------
Rl = {}
fa = fr[fr["ASSETNUM"].notna() & (fr["ASSETNUM"] != "")]
cnt = fa.groupby("ASSETNUM").size().sort_values(ascending=False)
nassets = len(asset[(asset["ASSETNUM"] != "(none)")])
k = max(1, round(nassets * 0.05))
Rl["n_assets"], Rl["bad_k"] = nassets, k
Rl["bad_share"] = round(cnt.head(k).sum() / len(fr) * 100, 1)
Rl["fail_total"] = len(fr)
bad = set(cnt.head(k).index)
dth = dt.groupby("ASSETNUM")["DOWNTIME"].sum()
A = asset.set_index("ASSETNUM")
fa = fa.copy(); fa["q"] = fa["REPORTDATE"].dt.to_period("Q")
qs = pd.period_range("2023Q3", "2026Q2", freq="Q")
top = []
for a in cnt.head(10).index:
    q = fa[fa["ASSETNUM"] == a].groupby("q").size().reindex(qs, fill_value=0).tolist()
    top.append(dict(asset=a, desc=A.loc[a, "DESCRIPTION"], site=A.loc[a, "SITEID"], crit=A.loc[a, "CRITICALITY"],
                    fails=int(cnt[a]), dt=round(float(dth.get(a, 0)), 0), q=q))
Rl["top"] = top
# MTTR / downtime by site
Rl["mttr"] = {s: round(dt[dt["SITEID"] == s]["DOWNTIME"].mean(), 2) for s in SITES}
Rl["mttr"]["ALL"] = round(dt["DOWNTIME"].mean(), 2)
Rl["dt_hours"] = {s: round(dt[dt["SITEID"] == s]["DOWNTIME"].sum(), 0) for s in SITES}
Rl["dt_hours"]["ALL"] = round(dt["DOWNTIME"].sum(), 0)
Rl["fails"] = {s: int((fr["SITEID"] == s).sum()) for s in SITES}
# MTTR rolling 12m quarterly by site
# problem codes
pc = fc[fc["TYPE"] == "PROBLEM"].drop_duplicates("FAILURECODE").set_index("FAILURECODE")["DESCRIPTION"]
p = fr["PROBLEMCODE"].value_counts().head(7)
Rl["problems"] = [dict(code=c, name=pc.get(c, c), n=int(v)) for c, v in p.items()]
# criticality
asset2 = asset[asset["ASSETNUM"] != "(none)"].copy()
asset2["f"] = asset2["ASSETNUM"].map(cnt).fillna(0)
Rl["crit"] = {c: dict(assets=int(len(x)), fpa=round(x["f"].mean(), 1), bad=int(x["ASSETNUM"].isin(bad).sum()))
              for c, x in asset2.groupby("CRITICALITY")}
# meter drift: index each asset-meter to its first 90 days, monthly mean, bad actors vs rest (gauges only)
g = mr[mr["METERNAME"] != "RUNHOURS"].copy()
g["key"] = g["ASSETNUM"] + "|" + g["METERNAME"]
base = g[g["READINGDATE"] < pd.Timestamp("2023-10-01")].groupby("key")["READING"].mean()
g = g[g["key"].isin(base.index)]
g["idx"] = g["READING"] / g["key"].map(base) * 100
g["m"] = g["READINGDATE"].dt.to_period("M")
g["bad"] = g["ASSETNUM"].isin(bad)
ms = pd.period_range("2023-07", "2026-06", freq="M")
Rl["drift_months"] = [m.strftime("%b %y") for m in ms]
Rl["drift_bad"] = [round(v, 1) for v in g[g["bad"]].groupby("m")["idx"].mean().reindex(ms).tolist()]
Rl["drift_rest"] = [round(v, 1) for v in g[~g["bad"]].groupby("m")["idx"].mean().reindex(ms).tolist()]
Rl["drift_bad_n"] = int(g[g["bad"]]["ASSETNUM"].nunique()); Rl["drift_rest_n"] = int(g[~g["bad"]]["ASSETNUM"].nunique())
O["rel"] = Rl

# ---------------- Planning ----------------
Pl = {}
op = nc[~nc["STATUS"].isin(["COMP", "CLOSE"])].copy()
op["age"] = (ANCHOR - op["REPORTDATE"]).dt.days
act = lab[lab["STATUS"] == "ACTIVE"]
trades = act[~act["CRAFT"].isin(["SUPV", "PLAN"])]
Pl["open"], Pl["open_hrs"], Pl["cap"], Pl["weeks"], Pl["age"] = {}, {}, {}, {}, {}
abins = [-10**6, 30, 90, 180, 10**6]; alabs = ["0-30 d", "31-90 d", "91-180 d", "180+ d"]
for s in SITES + ["ALL"]:
    o = op if s == "ALL" else op[op["SITEID"] == s]
    t = trades if s == "ALL" else trades[trades["SITEID"] == s]
    Pl["open"][s] = int(len(o)); Pl["open_hrs"][s] = round(o["ESTLABHRS"].sum(), 1)
    Pl["cap"][s] = int(len(t) * 40); Pl["weeks"][s] = round(o["ESTLABHRS"].sum() / (len(t) * 40), 1)
    Pl["age"][s] = pd.cut(o["age"], abins, labels=alabs).value_counts().reindex(alabs).astype(int).tolist()
Pl["open_status"] = op["STATUS"].value_counts().to_dict()
Pl["future_reportdate"] = int((op["REPORTDATE"] > ANCHOR).sum())
# overtime share last 12 months by site
l12 = lt[(lt["TRANSDATE"] > ANCHOR - pd.DateOffset(months=12)) & (lt["TRANSDATE"] <= ANCHOR)]
Pl["ot"] = {}
for s in SITES + ["ALL"]:
    x = l12 if s == "ALL" else l12[l12["SITEID"] == s]
    Pl["ot"][s] = round(x["PREMIUMPAYHOURS"].sum() / (x["REGULARHRS"].sum() + x["PREMIUMPAYHOURS"].sum()) * 100, 1)
# craft utilisation last 12 months: booked hours / (headcount * 40 * 52)
cr = []
for c, x in l12.groupby("CRAFT"):
    hc = int((trades["CRAFT"] == c).sum())
    if hc == 0: continue
    hrs = x["REGULARHRS"].sum() + x["PREMIUMPAYHOURS"].sum()
    cr.append(dict(craft=c, hc=hc, hrs=round(hrs, 0), util=round(hrs / (hc * 40 * 52) * 100, 1),
                   ot=round(x["PREMIUMPAYHOURS"].sum() / hrs * 100, 1)))
Pl["crafts"] = sorted(cr, key=lambda d: -d["util"])
# open by priority
Pl["open_prio"] = op["WOPRIORITY"].value_counts().sort_index().to_dict()
# cost split by site
nc2 = nc.copy()
Pl["cost"] = {s: {k: round(nc2[nc2["SITEID"] == s][c].sum(), 0) for k, c in
                  [("labour", "ACTLABCOST"), ("material", "ACTMATCOST"), ("tools", "ACTTOOLCOST"), ("services", "ACTSERVCOST")]} for s in SITES}
O["plan"] = Pl
json.dump(O, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages_numbers.json"), "w"), indent=1, default=float)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("drift_bad", "drift_rest", "drift_months")} for k, v in O.items()}, indent=1, default=float)[:9000])
print("drift bad", O["rel"]["drift_bad"][:3], O["rel"]["drift_bad"][-3:], "rest", O["rel"]["drift_rest"][:3], O["rel"]["drift_rest"][-3:])
