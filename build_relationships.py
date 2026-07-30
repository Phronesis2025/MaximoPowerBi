"""Generate relationships.tmdl for the star schema, and prove it has no
ambiguous filter paths before shipping it."""
import itertools, sys

# (dim_table, dim_col, fact_table, fact_col, active)
R = [
    ("DimDate","Date","FactWorkOrder","ReportDate",True),
    ("DimDate","Date","FactLabour","TransDate",True),
    ("DimDate","Date","FactMaterial","TransDate",True),
    ("DimDate","Date","FactDowntime","DowntimeStartDate",True),
    ("DimDate","Date","FactFailure","FailureDate",True),
    ("DimDate","Date","FactMeterReading","ReadingDate",True),
    ("DimAsset","ASSETNUM","FactWorkOrder","ASSETNUM",True),
    ("DimAsset","ASSETNUM","FactDowntime","ASSETNUM",True),
    ("DimAsset","ASSETNUM","FactFailure","ASSETNUM",True),
    ("DimAsset","ASSETNUM","FactMeterReading","ASSETNUM",True),
    ("DimLocation","LOCATION","FactWorkOrder","LOCATION",True),
    ("DimLocation","LOCATION","FactMaterial","LOCATION",True),
    ("DimSite","SITEID","FactWorkOrder","SITEID",True),
    ("DimSite","SITEID","FactLabour","SITEID",True),
    ("DimSite","SITEID","FactMaterial","SITEID",True),
    ("DimSite","SITEID","FactDowntime","SITEID",True),
    ("DimSite","SITEID","FactFailure","SITEID",True),
    ("DimSite","SITEID","FactMeterReading","SITEID",True),
    ("DimWorkType","WORKTYPE","FactWorkOrder","WORKTYPE",True),
    ("DimStatus","STATUS","FactWorkOrder","STATUS",True),
    ("DimCraft","CRAFT","FactLabour","CRAFT",True),
    ("DimLabor","LABORCODE","FactLabour","LABORCODE",True),
    ("DimItem","ITEMNUM","FactMaterial","ITEMNUM",True),
    ("DimFailureCode","ProblemCode","FactFailure","PROBLEMCODE",True),
    # inactive, reached with USERELATIONSHIP
    ("DimDate","Date","FactWorkOrder","TargCompDate",False),
    ("DimDate","Date","FactWorkOrder","ActFinishDate",False),
]

# ---- ambiguity check, done properly
# With single-direction relationships a filter propagates ONLY from the "one"
# side (dimension) to the "many" side (fact). So the graph is DIRECTED:
# dim -> fact. Ambiguity means a filter can reach a table by more than one
# ACTIVE directed route. A conformed dimension feeding six facts is not
# ambiguity - that is the whole point of a star.
active = [(d,f) for d,_,f,_,act in R if act]

# 1. more than one ACTIVE relationship between the same pair of tables
from collections import Counter
dupes = [(pair,n) for pair,n in Counter(active).items() if n > 1]

# 2. more than one directed route dim -> ... -> fact
dadj = {}
for d,f in active:
    dadj.setdefault(d,[]).append(f)
nodes = sorted({t for pair in active for t in pair})

def dpaths(a,b):
    out=[]
    def walk(n,seen,p):
        if n==b and len(p)>1: out.append(p); return
        for m in dadj.get(n,()):
            if m not in seen: walk(m,seen|{m},p+[m])
    walk(a,{a},[a]); return out

multi=[]
for a in nodes:
    for b in nodes:
        if a==b: continue
        n=len(dpaths(a,b))
        if n>1: multi.append((a,b,n))

# 3. structural sanity: no fact->fact and no dim->dim edges
facts={t for t in nodes if t.startswith("Fact")}
dims={t for t in nodes if t.startswith("Dim") or t=="ScheduleTolerance"}
f2f=[(d,f) for d,f in active if d in facts and f in facts]
d2d=[(d,f) for d,f in active if d in dims and f in dims]

print(f"tables: {len(nodes)}   active: {len(active)}   "
      f"inactive: {sum(1 for r in R if not r[4])}")
ok=True
for label,bad in (("duplicate ACTIVE relationship on a table pair",dupes),
                  ("multiple active directed routes",multi),
                  ("fact-to-fact relationship",f2f),
                  ("dim-to-dim relationship",d2d)):
    if bad:
        ok=False
        print(f"  FAIL  {label}: {bad}")
    else:
        print(f"  PASS  no {label}")

# inactive pairs are expected and legal - report them so they are deliberate
inact=[(f"{f}.{fc}",f"{d}.{dc}") for d,dc,f,fc,act in R if not act]
print(f"  note  {len(inact)} inactive relationship(s), reached via USERELATIONSHIP:")
for a,b in inact: print(f"          {a} -> {b}")
if not ok: sys.exit(1)
print()

lines=[]
for d,dc,f,fc,act in R:
    name = f"{f}_{fc}_to_{d}_{dc}"
    lines.append(f"relationship {name}")
    if not act: lines.append("\tisActive: false")
    lines.append(f"\tfromColumn: {f}.{fc}")
    lines.append(f"\ttoColumn: {d}.{dc}")
    lines.append("")
open("out/relationships.tmdl","w",newline="\r\n").write("\n".join(lines))
print("wrote out/relationships.tmdl")
