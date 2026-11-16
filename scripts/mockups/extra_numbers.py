"""Overview money figures (vp_numbers.json) and the failure Pareto curve (pareto.json).
Source: data/*.csv. Same definitions as exec_numbers.py: non-cancelled WOs, cost = labour+material+tool+service,
1,125-day window annualised by 365.25, RAV = sum of asset REPLACECOST. Benchmark = Bedford's cost % of RAV."""
import json, os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "data")
SITES = ["BEDFORD", "AURORA", "HOUSTON"]
YRS = 1125 / 365.25

def rd(n, nums=()):
    df = pd.read_csv(os.path.join(D, f"{n}.csv"), dtype=str, low_memory=False)
    for c in nums: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df

wo = rd("WORKORDER", ["ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST"])
asset = rd("ASSET", ["REPLACECOST"])
dtr = rd("DOWNTIMEREPORT", ["DOWNTIME"])
fr = rd("FAILUREREPORT")
wo["cost"] = wo[["ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST", "ACTSERVCOST"]].sum(axis=1)
nc = wo[wo["STATUS"] != "CAN"]
react = nc["WORKTYPE"].isin(["CM", "EM"])
rav = asset[asset["ASSETNUM"] != "(none)"]

done = wo[wo["STATUS"].isin(["COMP", "CLOSE"])]  # cost per job: finished jobs only (open jobs carry partial cost)
V = {"cost_per_react": done.loc[done["WORKTYPE"].isin(["CM", "EM"]), "cost"].mean(),
     "cost_per_pm": done.loc[done["WORKTYPE"] == "PM", "cost"].mean()}
for s in SITES:
    w = nc[nc["SITEID"] == s]; r = w["WORKTYPE"].isin(["CM", "EM"])
    V[s] = dict(react=w.loc[r, "cost"].sum() / YRS, plan=w.loc[~r, "cost"].sum() / YRS,
                rav=rav.loc[rav["SITEID"] == s, "REPLACECOST"].sum(),
                dt_h=dtr.loc[dtr["SITEID"] == s, "DOWNTIME"].sum() / YRS)
    V[s]["total"] = V[s]["react"] + V[s]["plan"]
    V[s]["pct"] = V[s]["total"] / V[s]["rav"] * 100
bench_pct = V["BEDFORD"]["pct"]
for s in SITES:
    V[s]["bench"] = V[s]["rav"] * bench_pct / 100
    V[s]["gap"] = max(0.0, V[s]["total"] - V[s]["bench"])
    V[s]["best3"] = V[s]["rav"] * 0.03
V["tot"] = sum(V[s]["total"] for s in SITES)
V["gap"] = sum(V[s]["gap"] for s in SITES)
V["react"] = sum(V[s]["react"] for s in SITES)
json.dump(V, open(os.path.join(HERE, "vp_numbers.json"), "w"), indent=1)

# Pareto: cumulative share of failures by asset, worst first, every 3rd asset rank
fa = fr[fr["ASSETNUM"].notna() & (fr["ASSETNUM"] != "")]
cnt = fa.groupby("ASSETNUM").size().sort_values(ascending=False).tolist()
n = len(rav)
cnt += [0] * (n - len(cnt))
cum = pd.Series(cnt).cumsum().tolist()
pts = [[0, 0]] + [[round(i / n * 100, 2), round(cum[i - 1] / len(fr) * 100, 2)] for i in range(3, n + 1, 3)] + [[100.0, 100.0]]
json.dump({"pts": pts, "n": n}, open(os.path.join(HERE, "pareto.json"), "w"))
print("vp + pareto written", round(V["gap"]), len(pts))
