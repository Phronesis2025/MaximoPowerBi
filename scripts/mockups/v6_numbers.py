"""Extra figures for v6: per-site WO counts and monthly planned vs reactive WO counts."""
import json, pandas as pd
import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
D = _os.path.join(HERE, "..", "..", "data")
wo = pd.read_csv(f"{D}/WORKORDER.csv", dtype=str, low_memory=False)
wo["rd"] = pd.to_datetime(wo["REPORTDATE"], errors="coerce")
print("total rows", len(wo), "by site", wo["SITEID"].value_counts().to_dict())
print("rd range", wo["rd"].min(), wo["rd"].max())
print("worktypes", wo["WORKTYPE"].value_counts().to_dict())
nc = wo[wo["STATUS"] != "CAN"].copy()
nc["m"] = nc["rd"].dt.to_period("M")
nc["grp"] = nc["WORKTYPE"].map(lambda w: "react" if w in ("CM", "EM") else "plan")
months = pd.period_range("2023-08", "2026-06", freq="M")
out = {"counts": wo["SITEID"].value_counts().to_dict(), "months": [m.strftime("%b %y") for m in months], "monthly": {}}
for s in ["BEDFORD", "AURORA", "HOUSTON"]:
    g = nc[nc["SITEID"] == s].groupby(["m", "grp"]).size().unstack(fill_value=0).reindex(months, fill_value=0)
    out["monthly"][s] = {"plan": g["plan"].tolist(), "react": g["react"].tolist()}
    print(s, "plan", g["plan"].tolist()[:6], "...", g["plan"].tolist()[-6:])
    print(s, "react", g["react"].tolist()[:6], "...", g["react"].tolist()[-6:])
json.dump(out, open(_os.path.join(HERE, "v6_numbers.json"), "w"), indent=1)
