"""Role-page figures (compliance lead / reliability engineer / planner). Source: MaximoPowerBi data CSVs, cut-off 29 Jul 2026."""
import json, pandas as pd, warnings; warnings.filterwarnings("ignore")
import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
D=_os.path.join(HERE, "..", "..", "data"); A=pd.Timestamp("2026-07-29"); S=["HOUSTON","AURORA","BEDFORD"]
wo=pd.read_csv(f"{D}/WORKORDER.csv",dtype=str,low_memory=False)
for c in ["REPORTDATE","TARGCOMPDATE","ACTFINISH","SCHEDSTART","ACTSTART"]: wo[c]=pd.to_datetime(wo[c],errors="coerce")
for c in ["ESTLABHRS","ACTLABHRS","ACTLABCOST","ACTMATCOST","ACTTOOLCOST","ACTSERVCOST","DOWNTIME"]: wo[c]=pd.to_numeric(wo[c],errors="coerce").fillna(0)
wo["cost"]=wo[["ACTLABCOST","ACTMATCOST","ACTTOOLCOST","ACTSERVCOST"]].sum(axis=1)
O={}
# ---- compliance lead: overdue NOW + due next 30 days (open, report-dated on/before cut-off)
op=wo[~wo.STATUS.isin(["COMP","CLOSE","CAN"])&(wo.REPORTDATE<=A)]
C={}
for key,wt in [("stat",["INSP","SAF"]),("pm",["PM"])]:
    x=op[op.WORKTYPE.isin(wt)]
    od=x[x.TARGCOMPDATE<A]; du=x[(x.TARGCOMPDATE>=A)&(x.TARGCOMPDATE<A+pd.Timedelta(days=30))]
    d=(A-od.TARGCOMPDATE).dt.days
    C[key]={"overdue":{s:int((od.SITEID==s).sum()) for s in S},"due30":{s:int((du.SITEID==s).sum()) for s in S},
            "overdue_buckets":{s:[int(((od.SITEID==s)&(d<=7)).sum()),int(((od.SITEID==s)&(d>7)&(d<=30)).sum()),int(((od.SITEID==s)&(d>30)).sum())] for s in S}}
    if key=="stat":
        od=od.assign(days=d)
        C["stat_list"]=[dict(wo=r.WONUM,site=r.SITEID,asset=r.ASSETNUM,type=r.WORKTYPE,desc=r.DESCRIPTION,days=int(r.days),status=r.STATUS)
                        for r in od.sort_values("days",ascending=False).head(8).itertuples()]
# monthly statutory on-time % by site (completed, by TARGCOMPDATE month), last 24 complete months
c=wo[wo.STATUS.isin(["COMP","CLOSE"])&wo.ACTFINISH.notna()&wo.WORKTYPE.isin(["INSP","SAF"])].copy()
c["ok"]=c.ACTFINISH.dt.normalize()<=c.TARGCOMPDATE.dt.normalize(); c["m"]=c.TARGCOMPDATE.dt.to_period("Q")
q=c[(c.TARGCOMPDATE>="2023-10-01")&(c.TARGCOMPDATE<"2026-07-01")]
C["stat_q_labels"]=[str(p) for p in sorted(q.m.unique())]
C["stat_q"]={s:[round(v*100,1) for v in q[q.SITEID==s].groupby("m").ok.mean().reindex(sorted(q.m.unique())).tolist()] for s in S}
O["comp"]=C
# ---- planner
P={}
P["status"]={s:op[op.SITEID==s].STATUS.value_counts().reindex(["APPR","WAPPR","INPRG"]).fillna(0).astype(int).tolist() for s in S}
P["status_hrs"]={s:op[op.SITEID==s].groupby("STATUS").ESTLABHRS.sum().reindex(["APPR","WAPPR","INPRG"]).fillna(0).round().astype(int).tolist() for s in S}
sc=wo[wo.STATUS.isin(["COMP","CLOSE"])&wo.SCHEDSTART.notna()&wo.ACTSTART.notna()].copy()
sc["ok"]=(sc.ACTSTART.dt.normalize()-sc.SCHEDSTART.dt.normalize()).dt.days<=2
sc["m"]=sc.SCHEDSTART.dt.to_period("M")
sc12=sc[(sc.SCHEDSTART>A-pd.Timedelta(days=365))&(sc.SCHEDSTART<=A)]
P["sched12"]={s:round(sc12[sc12.SITEID==s].ok.mean()*100,1) for s in S}; P["sched12"]["ALL"]=round(sc12.ok.mean()*100,1)
ms=sorted(sc[(sc.SCHEDSTART>="2023-08-01")&(sc.SCHEDSTART<"2026-07-01")].m.unique())
P["sched_months"]=[p.strftime("%b %y") for p in ms]
P["sched_m"]={s:[round(v*100,1) for v in sc[sc.SITEID==s].groupby("m").ok.mean().reindex(ms).tolist()] for s in S}
nc=wo[(wo.STATUS!="CAN")&(wo.REPORTDATE>A-pd.Timedelta(days=365))&(wo.REPORTDATE<=A)]
P["breakin"]={s:round(nc[(nc.SITEID==s)&(nc.WORKTYPE=="EM")].ACTLABHRS.sum()/nc[nc.SITEID==s].ACTLABHRS.sum()*100,1) for s in S}
O["plan"]=P
# ---- reliability engineer: bad actors ranked by cost of failure (reactive WO cost + downtime h)
R={}
re=wo[wo.WORKTYPE.isin(["EM","CM"])&(wo.STATUS!="CAN")&wo.ASSETNUM.notna()]
asset=pd.read_csv(f"{D}/ASSET.csv",dtype=str)
g=re.groupby("ASSETNUM").agg(n=("WONUM","size"),cost=("cost","sum"),site=("SITEID","first"))
dt=pd.read_csv(f"{D}/DOWNTIMEREPORT.csv",dtype=str); dt["DOWNTIME"]=pd.to_numeric(dt.DOWNTIME,errors="coerce").fillna(0)
g=g.join(dt.groupby("ASSETNUM").DOWNTIME.sum().rename("dt")).fillna({"dt":0})
ac=[c for c in asset.columns if c in ("ASSETTYPE","DESCRIPTION","PRIORITY","CRITICALITY")]
g=g.join(asset.set_index("ASSETNUM")[ac])
R["asset_cols"]=ac
R["by_cost"]=[dict(asset=i,**{k:(float(v) if isinstance(v,(int,float)) else v) for k,v in r.items()}) for i,r in g.sort_values("cost",ascending=False).head(10).iterrows()]
R["top10_cost_share"]=round(g.sort_values("cost",ascending=False).head(10).cost.sum()/g.cost.sum()*100,1)
R["top45_cost_share"]=round(g.sort_values("cost",ascending=False).head(45).cost.sum()/g.cost.sum()*100,1)
R["react_cost_total"]=round(g.cost.sum())
fr=pd.read_csv(f"{D}/FAILUREREPORT.csv",dtype=str)
R["fr_cols"]=fr.columns.tolist()
O["rel"]=R
json.dump(O,open(_os.path.join(HERE, "roles_numbers.json"),"w"),indent=1,default=str)
print(json.dumps({k:(v if k!="rel" else {kk:vv for kk,vv in v.items() if kk!="by_cost"}) for k,v in O.items()},indent=0,default=str)[:5000])
for r in R["by_cost"]: print(r)
# ---- additions: planner status over ALL open WOs (matches the 2,596 backlog on the page); per-asset reactive cost
opa=wo[~wo.STATUS.isin(["COMP","CLOSE","CAN"])]
P["status_all"]={s:opa[opa.SITEID==s].STATUS.value_counts().reindex(["APPR","WAPPR","INPRG"]).fillna(0).astype(int).tolist() for s in S}
P["status_all_hrs"]={s:opa[opa.SITEID==s].groupby("STATUS").ESTLABHRS.sum().reindex(["APPR","WAPPR","INPRG"]).fillna(0).round().astype(int).tolist() for s in S}
P["status_all_tot"]=opa.STATUS.value_counts().reindex(["APPR","WAPPR","INPRG"]).fillna(0).astype(int).tolist()
P["status_all_tot_hrs"]=opa.groupby("STATUS").ESTLABHRS.sum().reindex(["APPR","WAPPR","INPRG"]).round().astype(int).tolist()
R["cost_map"]={i:round(v) for i,v in g.cost.items() if v>40000}
json.dump(O,open(_os.path.join(HERE, "roles_numbers.json"),"w"),indent=1,default=str)
print(P["status_all"],P["status_all_hrs"],P["status_all_tot"],P["status_all_tot_hrs"],len(opa))
