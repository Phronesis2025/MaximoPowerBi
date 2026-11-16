"""PM & Compliance, Reliability, Planning, Information mockups in the v6 dark style.
Reuses the v6 shell (CSS + sidebar) and helpers; every figure from pages_numbers.json / exec_numbers.json."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_v6 as g  # also regenerates executive_v6.html

P = json.load(open(os.path.join(HERE, "pages_numbers.json")))
D, F, R = g.D, g.F, g.R
SITE, NAME, FULL = g.SITE, g.NAME, g.FULLNAME
GREEN, AMBER, RED, MUT, FAINT, TXT, LINE, CARD = g.GREEN, g.AMBER, g.RED, g.MUT, g.FAINT, g.TXT, g.LINE, g.CARD
MONO, GLY = g.MONO, g.GLY
CSS = g.html.split("<style>")[1].split("</style>")[0]
ASIDE = g.html.split("<aside>")[1].split("</aside>")[0]
TOPR = '<div class="r"><div class="seg"><span class="on">All</span><span>2024</span><span>2025</span><span>2026</span></div><span class="asof">data as of 29 Jul 2026</span></div>'
SITES3 = ["HOUSTON", "AURORA", "BEDFORD"]

EXTRA = f"""
.g2{{display:grid;gap:14px;margin-top:14px}}
.col{{display:flex;flex-direction:column;gap:14px}}
.c{{background:{CARD};border:1px solid {LINE};border-radius:14px;padding:18px 22px;display:flex;flex-direction:column;overflow:hidden}}
.ch{{display:flex;justify-content:space-between;align-items:baseline}}
.cq{{font-size:17px;font-weight:600}}
.cs{{font-family:{MONO};font-size:12px;color:{FAINT};margin-top:3px}}
.lk{{font-size:13px;color:#93C5FD;margin-left:auto}}
.rl{{display:grid;align-items:center;column-gap:14px;padding:9px 0;border-bottom:1px solid #1C1C20;font-size:14px}}
.rl:last-child{{border-bottom:none}}
.rh{{font-family:{MONO};font-size:10.5px;color:{FAINT};letter-spacing:.4px;padding:14px 0 6px;border-bottom:1px solid {LINE}}}
.mono2{{font-family:{MONO};font-size:13px}}
.dim{{color:{MUT}}}
.share{{position:relative;height:3px;background:#222227;border-radius:2px;margin-top:5px}}
.share i{{position:absolute;left:0;top:0;bottom:0;border-radius:2px}}
.chip{{font-family:{MONO};font-size:10.5px;border:1px solid #33333A;color:#B4B4BC;border-radius:5px;padding:1px 6px}}
.stk{{display:flex;height:14px;border-radius:4px;overflow:hidden;gap:2px}}
.stk i{{display:block;height:100%}}
.kv{{font-family:{MONO};font-size:12px;color:{MUT}}}
.note{{font-family:{MONO};font-size:11.5px;color:{FAINT};margin-top:auto;padding-top:10px;line-height:1.5}}
.note b{{color:{AMBER};font-weight:400}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
"""

def kpi(label, num, target, bul, delta, dcol, vals, scol, hero=False, mr=10):
    """Like g.kpi, but vals=None means no sparkline (never borrow another metric's trend)."""
    sp = g.spark(vals, 260 if hero else 92, 70 if hero else 34, scol, minrange=mr) if vals else ""
    return f'''<div class="kpi{' hero' if hero else ''}">
 <div class="klabel">{label}</div>
 <div class="kmid"><div class="knum">{num}</div>{sp}</div>
 {bul}
 <div class="kfoot"><span style="color:{dcol}">{delta}</span><span class="ktarget">{target}</span></div>
</div>'''

def page(active, title, grey, sub, kpis_html, body, file):
    aside = ASIDE.replace('<div class="nav on">', '<div class="nav">')
    aside = aside.replace(f'<div class="nav">{g.I[active]}', f'<div class="nav on">{g.I[active]}')
    kp = f'<div class="kpis">{kpis_html}</div>' if kpis_html else ""
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{CSS}{EXTRA}</style></head><body>
<aside>{aside}</aside><main><div class="top">{g.I[active]}<span>{active}</span>{TOPR}</div>
<div class="body"><h1>{title} <span>{grey}</span></h1><div class="sub">{sub}</div>{kp}{body}</div></main></body></html>'''
    out = os.path.join(g.OUT, file)
    open(out, "w", encoding="utf-8").write(html)
    return out

def linechart(series, labels, dom, ticks, W, H, target=None, tlabel="", fmt="{:.1f}%", tick_every=6, endlab=True):
    L, Rr, T, B = 46, 130 if endlab else 20, 10, 26
    pw, ph = W - L - Rr, H - T - B
    X = lambda i: L + i * pw / (len(labels) - 1)
    Y = lambda v: T + (dom[1] - v) / (dom[1] - dom[0]) * ph
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for v in ticks:
        s.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#1D1D21"/>')
        s.append(f'<text x="{L - 10}" y="{Y(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for i, lab in enumerate(labels):
        if i % tick_every == 0 or i == len(labels) - 1:
            s.append(f'<text x="{X(i):.1f}" y="{H - 6}" class="ax" text-anchor="middle">{lab}</text>')
    if target is not None:
        s.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(target):.1f}" y2="{Y(target):.1f}" stroke="{AMBER}" stroke-width="1.3" stroke-dasharray="5 5"/>')
        s.append(f'<text x="{L + 6}" y="{Y(target) - 7:.1f}" class="tgtl">{tlabel}</text>')
    ends = []
    for name, col, vals, strong in series:
        pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
        path = g.monotone(pts)
        if strong:
            s.append(g.glow(path, col, 2.4))
        else:
            s.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="2" stroke-opacity=".7"/>')
        s.append(f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="{col}"/>')
        ends.append((pts[-1][1], name, col, vals[-1]))
    if endlab:
        last = -99
        for y, name, col, v in sorted(ends):
            y = max(y, last + 18); last = y
            s.append(f'<text x="{L + pw + 12}" y="{y + 4:.1f}" class="endl" fill="{col}">{name} <tspan class="endv">{fmt.format(v)}</tspan></text>')
    s.append("</svg>")
    return "".join(s)

EXTRA += f".tgtl{{font-family:{MONO};font-size:11px;fill:{AMBER}}}"

def bar(pct, col, glow=True):
    sh = f";box-shadow:0 0 8px {col}66" if glow else ""
    return f'<div class="share"><i style="width:{min(100, pct):.1f}%;background:{col}{sh}"></i></div>'

# =====================================================================
# PM & COMPLIANCE
# =====================================================================
pm, A = P["pm"], F["ALL"]
late_share = pm["pm_late"] / pm["pm_n"] * 100
pr = pm["pm_by_priority"]
k = "".join([
    kpi("PM compliance", f'{A["pm"]:.1f}%', "target 90%", g.bullet(A["pm"], 0, 100, 90, AMBER),
          f'{GLY[AMBER]} &minus;{90 - A["pm"]:.1f} pts vs target', AMBER, g.ser("ALL", "pm"), AMBER, hero=True),
    kpi("PMs finished late", f'{pm["pm_late"]:,}', f'of {pm["pm_n"]:,}', '<div class="bullet none"></div>',
          f'{late_share:.1f}% of completed', MUT, None, ""),
    kpi("Median days late", f'{pm["pm_late_median_days"]:.0f}<small>d</small>', "", '<div class="bullet none"></div>',
          "late PMs only", MUT, None, ""),
    kpi("Statutory compliance", f'{A["stat"]:.1f}%', "target 100%", g.bullet(A["stat"], 0, 100, 100, RED),
          f'{GLY[RED]} {A["stat_late"]} late', RED, g.ser("ALL", "stat"), RED),
    kpi("Schedules &lt; 80% on time", f'{pm["pm_sched_below_80"]}', f'of {pm["pm_sched_n"]}', '<div class="bullet none"></div>',
          "PM schedules, 12+ runs", MUT, None, ""),
])
# chart: rolling PM compliance by site
ser = [(NAME[s], SITE[s], g.ser(s, "pm"), True) for s in SITES3]
c1 = linechart(ser, D["months"], (60, 100), [60, 70, 80, 90, 100], 1030, 236, target=90, tlabel="target 90%")
# worst schedules
rows = '<div class="rl rh" style="grid-template-columns:96px 150px 1fr 90px 130px 80px"><span>PM</span><span>ASSET</span><span>TASK</span><span>EVERY</span><span>LATE</span><span style="text-align:right">MEDIAN</span></div>'
for w in pm["worst_pms"][:5]:
    rows += (f'<div class="rl" style="grid-template-columns:96px 150px 1fr 90px 130px 80px">'
             f'<span class="mono2">{w["pm"]}</span><span class="mono2"><span class="dot" style="background:{SITE[w["site"]]};margin-right:8px"></span>{w["asset"]}</span>'
             f'<span>{w["desc"]}</span><span class="dim">{w["freq"]}</span>'
             f'<span><span class="mono2" style="color:{RED}">{w["late"]} of {w["n"]}</span>{bar(w["late"] / w["n"] * 100, RED, False)}</span>'
             f'<span class="mono2 dim" style="text-align:right">{w["med"]:.0f} d</span></div>')
# late buckets
BK = ["#FDE68A", AMBER, RED]
lb = ""
maxt = max(sum(pm["late_buckets"][x][:3]) for x in SITES3)
for s in SITES3:
    v = pm["late_buckets"][s][:3]; t = sum(v)
    segs = "".join(f'<i style="width:{x / t * 100:.1f}%;background:{BK[j]}"></i>' for j, x in enumerate(v))
    lb += (f'<div style="margin-top:20px"><div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:8px">'
           f'<span><span class="dot" style="background:{SITE[s]};margin-right:8px"></span>{NAME[s]}</span>'
           f'<span class="kv">{t:,} late PMs &middot; <span style="color:{RED}">{v[2] / t * 100:.0f}% over a month</span></span></div>'
           f'<div class="stk" style="width:{t / maxt * 100:.1f}%">{segs}</div></div>')
lb += (f'<div class="kv" style="margin-top:18px;display:flex;gap:16px"><span><i class="sw" style="background:{BK[0]}"></i>1&ndash;7 days</span>'
       f'<span><i class="sw" style="background:{BK[1]}"></i>8&ndash;30 days</span><span><i class="sw" style="background:{BK[2]}"></i>31&ndash;90 days</span></div>')
# statutory
sb = ""
for s in SITES3:
    st = pm["stat_by_type"][s]; n = st["INSP"]["n"] + st["SAF"]["n"]; lt = st["INSP"]["late"] + st["SAF"]["late"]
    comp = (1 - lt / n) * 100
    sb += (f'<div style="margin-top:18px"><div style="display:flex;justify-content:space-between;font-size:14px">'
           f'<span><span class="dot" style="background:{SITE[s]};margin-right:8px"></span>{NAME[s]}</span>'
           f'<span class="mono2" style="color:{RED}">{GLY[RED]} {comp:.1f}%</span></div>'
           f'{g.bullet(comp, 60, 100, 100, RED)}'
           f'<div class="kv" style="margin-top:8px">{lt} late of {n:,} &middot; inspections {st["INSP"]["late"]} &middot; safety {st["SAF"]["late"]}</div></div>')
body = f'''<div class="g2" style="grid-template-columns:1fr 470px">
 <div class="col">
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Is PM compliance reaching 90%?</div><div class="cs">rolling 12 months, by site</div></div></div>{c1}</div>
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Which PM schedules slip most?</div><div class="cs">schedules with 12+ runs &middot; all at Houston</div></div><span class="lk">All {pm["pm_sched_below_80"]} schedules &#8594;</span></div>{rows}</div>
 </div>
 <div class="col">
  <div class="c" style="height:326px"><div class="cq">How late is late?</div><div class="cs">late PMs by days past target &middot; bar length = number late</div>{lb}</div>
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Statutory work</div><div class="cs">inspections + safety &middot; target 100%</div></div><span class="lk">Late list &#8594;</span></div>{sb}</div>
 </div></div>'''
o1 = page("PM &amp; Compliance", "PM &amp; Compliance", "Jul 2023 &ndash; Jul 2026",
          f'<b>Nearly 1 in 5 PMs finishes late.</b> Priority doesn&rsquo;t help: P2 {pr["2"]}% on time, P4 {pr["4"]}%.', k, body, "pm_compliance_v7.html")

# =====================================================================
# RELIABILITY
# =====================================================================
rl = P["rel"]
PA = json.load(open(os.path.join(HERE, "pareto.json")))
def pareto(W=300, H=84):
    L, B, T = 4, 16, 6
    X = lambda x: L + x / 100 * (W - L - 6)
    Y = lambda y: T + (100 - y) / 100 * (H - T - B)
    pts = [(X(x), Y(y)) for x, y in PA["pts"]]
    path = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    area = path + f" L{X(100):.1f},{Y(0):.1f} L{X(0):.1f},{Y(0):.1f} Z"
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<path d="{area}" fill="{RED}" fill-opacity=".07"/>',
         f'<line x1="{X(0)}" y1="{Y(0):.1f}" x2="{X(100):.1f}" y2="{Y(100):.1f}" stroke="#3F3F46" stroke-dasharray="3 4"/>',
         g.glow(path, RED, 1.8)]
    for x, y in [(5, 19.8), (20, 53.6)]:
        s.append(f'<line x1="{X(x):.1f}" y1="{Y(y):.1f}" x2="{X(x):.1f}" y2="{Y(0):.1f}" stroke="#52525B" stroke-dasharray="2 3"/>')
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3.5" fill="{RED}"/>')
        s.append(f'<text x="{X(x) + 7:.1f}" y="{Y(y) + 4:.1f}" class="ax" style="fill:#D4D4D8">{x}% &#8594; {y:.0f}%</text>')
    s.append(f'<text x="{X(0)}" y="{H - 2}" class="ax">assets, worst first &#8594;</text>')
    s.append(f'<text x="{X(100):.1f}" y="{H - 2}" class="ax" text-anchor="end">100%</text>')
    return "".join(s) + "</svg>"
k = "".join([
    kpi("Failures from 5% of assets", f'{rl["bad_share"]:.1f}%', f'{rl["bad_k"]} of {rl["n_assets"]} assets', '<div class="bullet none"></div>',
          f'{GLY[RED]} bad actors, all sites', RED, None, "", hero=True).replace('<div class="kmid"><div class="knum">' + f'{rl["bad_share"]:.1f}%' + '</div>', '<div class="kmid"><div class="knum">' + f'{rl["bad_share"]:.1f}%' + '</div>' + pareto()),
    kpi("Failure events", f'{rl["fail_total"]:,}', "3 years", '<div class="bullet none"></div>',
          f'Houston {rl["fails"]["HOUSTON"]:,}', MUT, None, ""),
    kpi("MTTR", f'{rl["mttr"]["ALL"]:.1f}<small>h</small>', "", '<div class="bullet none"></div>',
          f'Bedford {rl["mttr"]["BEDFORD"]:.1f} &middot; Houston {rl["mttr"]["HOUSTON"]:.1f}', MUT, None, ""),
    kpi("Downtime", f'{rl["dt_hours"]["ALL"] / 1000:.0f}k<small>h</small>', "", '<div class="bullet none"></div>',
          f'Houston {rl["dt_hours"]["HOUSTON"] / rl["dt_hours"]["ALL"] * 100:.0f}% of it', MUT, None, ""),
    kpi("MTBF", f'{A["mtbf"]:,.0f}<small>h</small>', "", '<div class="bullet none"></div>',
          "provisional", MUT, g.ser("ALL", "mtbf"), "#A1A1AA", mr=600),
])
dm = rl["drift_months"]
c1 = linechart([("Other assets", "#A1A1AA", rl["drift_rest"], False), ("Bad actors", RED, rl["drift_bad"], True)],
               dm, (80, 180), [80, 100, 120, 140, 160, 180], 1030, 240, target=100, tlabel="baseline = 100 (Jul&ndash;Sep 2023)", fmt="{:.0f}")
# criticality
cr = rl["crit"]; mx = max(v["fpa"] for v in cr.values())
cb = ""
for c in ["1", "2", "3", "4"]:
    v = cr[c]
    cb += (f'<div class="rl" style="grid-template-columns:70px 1fr 60px"><span class="chip">CRIT {c}</span>'
           f'<span>{bar(v["fpa"] / 20 * 100, "#A1A1AA", False)}<span class="kv">{v["assets"]} assets &middot; {v["bad"]} bad actors</span></span>'
           f'<span class="mono2" style="text-align:right">{v["fpa"]:.1f}</span></div>')
# problems
pb = ""; pmx = rl["problems"][0]["n"]
for p_ in rl["problems"][:6]:
    pb += (f'<div class="rl" style="grid-template-columns:120px 1fr 56px"><span>{p_["name"]}</span>{bar(p_["n"] / pmx * 100, "#A1A1AA", False)}'
           f'<span class="mono2" style="text-align:right">{p_["n"]:,}</span></div>')
# bad actors list
ba = '<div class="rl rh" style="grid-template-columns:minmax(0,1fr) 64px 92px 54px"><span>ASSET</span><span>CRIT</span><span>FAILURES / QTR</span><span style="text-align:right">TOTAL</span></div>'
fmx = rl["top"][0]["fails"]
for t in rl["top"]:
    ba += (f'<div class="rl" style="grid-template-columns:minmax(0,1fr) 64px 92px 54px;padding:10px 0">'
           f'<span><span class="mono2"><span class="dot" style="background:{SITE[t["site"]]};margin-right:8px"></span>{t["asset"]}</span>'
           f'<div class="kv" style="margin:3px 0 0 16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:230px">{t["desc"].rsplit(" ", 1)[0]} &middot; {t["dt"]:,.0f} h</div></span>'
           f'<span class="chip" style="justify-self:start">{t["crit"]}</span>'
           f'{g.spark(t["q"], 92, 30, RED, dom=(0, 17))}'
           f'<span class="mono2" style="text-align:right;color:{RED}">{t["fails"]}</span></div>')
body = f'''<div class="g2" style="grid-template-columns:1fr 470px">
 <div class="col">
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Can we see failures coming?</div><div class="cs">condition meter readings, indexed &middot; {rl["drift_bad_n"]} metered bad actors vs {rl["drift_rest_n"]} other assets</div></div></div>{c1}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
   <div class="c" style="height:326px"><div class="cq">Does criticality predict failure?</div><div class="cs">failures per asset, by criticality</div><div style="margin-top:10px">{cb}</div>
    <div class="note"><b>No.</b> Crit-1 assets fail as often as crit-4. The ranking isn&rsquo;t steering maintenance effort.</div></div>
   <div class="c" style="height:326px"><div class="cq">What fails?</div><div class="cs">top problem codes, all sites</div><div style="margin-top:10px">{pb}</div></div>
  </div>
 </div>
 <div class="c" style="height:666px"><div class="ch"><div><div class="cq">Top 10 bad actors</div><div class="cs">all ten at Houston &middot; quarterly failures, 3 yrs</div></div><span class="lk">All {rl["bad_k"]} &#8594;</span></div>{ba}</div>
</div>'''
o2 = page("Reliability", "Reliability", "Jul 2023 &ndash; Jul 2026",
          f'<b>{rl["bad_k"]} assets cause {rl["bad_share"]:.0f}% of failures</b> &mdash; and their condition meters have drifted {rl["drift_bad"][-1] - 100:.0f}% above baseline.',
          k, body, "reliability_v7.html")

# =====================================================================
# PLANNING
# =====================================================================
pl = P["plan"]
aged = pl["age"]["ALL"][2] + pl["age"]["ALL"][3]
k = "".join([
    kpi("Backlog", f'{pl["weeks"]["ALL"]:.1f}<small>wks</small>', "healthy 4&ndash;6 wks",
          g.bullet(pl["weeks"]["ALL"], 0, 12, 6, AMBER, band=(4, 6)).replace("#4ADE8040", "#4ADE8030"),
          f'{GLY[AMBER]} top of the healthy band', AMBER, None, "", hero=True),
    kpi("Open work orders", f'{pl["open"]["ALL"]:,}', "", '<div class="bullet none"></div>',
          f'{pl["open_status"]["WAPPR"]} awaiting approval', MUT, None, ""),
    kpi("Open labour hours", f'{pl["open_hrs"]["ALL"]:,.0f}<small>h</small>', "estimated", '<div class="bullet none"></div>',
          f'Houston {pl["open_hrs"]["HOUSTON"] / pl["open_hrs"]["ALL"] * 100:.0f}%', MUT, None, ""),
    kpi("Crew capacity", f'{pl["cap"]["ALL"]:,}<small>h/wk</small>', "", '<div class="bullet none"></div>',
          f'{pl["cap"]["ALL"] // 40} trades &times; 40 h &middot; assumed', MUT, None, ""),
    kpi("Open over 90 days", f'{aged}', f'of {pl["open"]["ALL"]:,}', '<div class="bullet none"></div>',
          f'{aged / pl["open"]["ALL"] * 100:.1f}% of backlog', MUT, None, ""),
])
# backlog weeks by site with band
AGEC = ["#3F3F46", "#71717A", AMBER, RED]
bw = ""
for s in SITES3:
    wv = pl["weeks"][s]
    col = GREEN if 4 <= wv <= 6 else AMBER if wv < 4 else RED
    word = "in band" if 4 <= wv <= 6 else "low" if wv < 4 else "over"
    a = pl["age"][s]; t = sum(a)
    segs = "".join(f'<i style="width:{x / t * 100:.1f}%;background:{AGEC[j]}"></i>' for j, x in enumerate(a) if x)
    bw += (f'<div style="display:grid;grid-template-columns:150px 1fr 140px;column-gap:20px;align-items:center;margin-top:22px">'
           f'<span style="font-size:15px"><span class="dot" style="background:{SITE[s]};margin-right:8px;box-shadow:0 0 6px {SITE[s]}"></span>{NAME[s]}</span>'
           f'<div>{g.bullet(wv, 0, 12, 6, col, band=(4, 6))}<div class="stk" style="height:6px;margin-top:12px">{segs}</div></div>'
           f'<span style="text-align:right"><span style="font-size:22px;font-weight:500;color:{col}">{wv:.1f}</span> <span class="kv">wks &middot; {word}</span>'
           f'<div class="kv">{pl["open"][s]:,} WOs &middot; {pl["cap"][s]:,} h/wk</div></span></div>')
bw += (f'<div class="kv" style="margin-top:20px;display:flex;gap:16px;padding-left:170px"><span>age of open work:</span>'
       + "".join(f'<span><i class="sw" style="background:{AGEC[j]}"></i>{l}</span>' for j, l in enumerate(["0&ndash;30 d", "31&ndash;90 d", "91&ndash;180 d"])) + "</div>")
# crafts
cf = '<div class="rl rh" style="grid-template-columns:110px 1fr 70px"><span>CRAFT</span><span>BOOKED HOURS vs CAPACITY &middot; last 12 mo</span><span style="text-align:right">UTIL.</span></div>'
CN = {"MECH": "Mechanic", "ELECT": "Electrician", "OPER": "Operator", "HVAC": "HVAC", "LUBE": "Lube tech", "INSTR": "Instrument", "MILLWR": "Millwright"}
for c in [x for x in pl["crafts"] if x["craft"] in CN]:
    col = RED if c["util"] > 100 else AMBER if c["util"] > 85 else "#A1A1AA"
    cf += (f'<div class="rl" style="grid-template-columns:110px 1fr 70px;padding:12px 0"><span>{CN[c["craft"]]}<div class="kv">{c["hc"]} people</div></span>'
           f'<div style="position:relative"><div class="share" style="height:8px;border-radius:4px"><i style="width:{min(c["util"], 150) / 150 * 100:.1f}%;background:{col};border-radius:4px{";box-shadow:0 0 10px " + col + "88" if col != "#A1A1AA" else ""}"></i></div>'
           f'<i style="position:absolute;left:{100 / 150 * 100:.1f}%;top:-2px;width:2px;height:16px;background:#E4E4E7"></i></div>'
           f'<span class="mono2" style="text-align:right;color:{col}">{c["util"]:.0f}%</span></div>')
cf += '<div class="note"><b>Data gap:</b> welders and pipefitters book &lt;1% of capacity &mdash; the synthetic labour data barely uses them. Tick = 100%.</div>'
# cost
cost = pl["cost"]; CC = [("labour", "#E4E4E7"), ("material", "#A1A1AA"), ("services", "#71717A"), ("tools", "#3F3F46")]
mxc = max(sum(v.values()) for v in cost.values())
cs = ""
for s in SITES3:
    t = sum(cost[s].values())
    segs = "".join(f'<i style="width:{cost[s][kk] / mxc * 100:.2f}%;background:{cc}"></i>' for kk, cc in CC)
    cs += (f'<div style="margin-top:18px"><div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:8px">'
           f'<span><span class="dot" style="background:{SITE[s]};margin-right:8px"></span>{NAME[s]}</span><span class="mono2">${t / 1e6:.1f}M</span></div>'
           f'<div class="stk" style="height:12px">{segs}</div></div>')
cs += (f'<div class="kv" style="margin-top:18px;display:flex;gap:16px">'
       + "".join(f'<span><i class="sw" style="background:{cc}"></i>{kk}</span>' for kk, cc in CC) + "</div>")
body = f'''<div class="g2" style="grid-template-columns:1fr 520px">
 <div class="col">
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">How many weeks of work is waiting?</div><div class="cs">open estimated hours &divide; crew capacity &middot; healthy band 4&ndash;6 weeks</div></div></div>{bw}</div>
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Where does the money go?</div><div class="cs">actual cost, 3 years &middot; excl. cancelled</div></div></div>{cs}</div>
 </div>
 <div class="c" style="height:666px"><div class="ch"><div><div class="cq">Which crafts are the bottleneck?</div><div class="cs">all sites</div></div></div>{cf}</div>
</div>'''
o3 = page("Planning", "Planning", "open work as of 29 Jul 2026",
          f'<b>Houston has {pl["weeks"]["HOUSTON"]:.0f} weeks of backlog.</b> Mechanics are booked at {pl["crafts"][0]["util"]:.0f}% of capacity.', k, body, "planning_v6.html")

# =====================================================================
# INFORMATION
# =====================================================================
KD = [("Reactive maintenance %", "(CM + EM) &divide; all non-cancelled work orders", "&lt; 20%"),
      ("PM compliance %", "PMs finished on or before target &divide; completed PMs", "&ge; 90%"),
      ("Statutory compliance %", "inspection + safety WOs finished on time &divide; completed", "100%"),
      ("MTBF", "operating hours &divide; failure events (operating-hours assumption)", "trend only"),
      ("MTTR", "elapsed downtime &divide; downtime events &mdash; not labour hours", "lower is better"),
      ("Backlog (weeks)", "open estimated labour hours &divide; (active trades &times; 40 h)", "4&ndash;6 weeks"),
      ("Cost % of RAV", "annual maintenance cost &divide; asset replacement value", "2&ndash;3%"),
      ("Bad actor", "top 5% of assets by failure count", "&mdash;")]
kd = '<div class="rl rh" style="grid-template-columns:200px 1fr 120px"><span>KPI</span><span>DEFINITION</span><span style="text-align:right">TARGET</span></div>'
for a_, b_, c_ in KD:
    kd += f'<div class="rl" style="grid-template-columns:200px 1fr 120px;padding:13px 0"><span style="font-weight:600">{a_}</span><span class="dim">{b_}</span><span class="mono2" style="text-align:right">{c_}</span></div>'
kd += '<div class="note">Targets follow SMRP best-practice benchmarks. Every KPI has a DAX test case in <span style="color:#B4B4BC">verify_measures.py</span>.</div>'
WT = [("EM", "Emergency", "Reactive"), ("CM", "Corrective", "Reactive"), ("SAF", "Safety", "Planned"), ("INSP", "Inspection", "Planned"),
      ("PM", "Preventive", "Planned"), ("PDM", "Predictive", "Planned"), ("PROJ", "Project", "Planned")]
wt = ""
for c_, n_, g_ in WT:
    col = RED if g_ == "Reactive" else "#A1A1AA"
    wt += (f'<div class="rl" style="grid-template-columns:60px 1fr 80px;padding:8px 0"><span class="chip" style="justify-self:start">{c_}</span>'
           f'<span>{n_}</span><span class="mono2" style="text-align:right;color:{col}">{g_.lower()}</span></div>')
NOTES = [("Synthetic data", "Generated 29 Jul 2026, seed 20260729. No real site, asset or person."),
         ("Recent months", "Recent work is left open on purpose, so the last ~3 months understate completions, failures and cost."),
         ("Provisional", "MTBF year-on-year is flagged until the end-of-window effect is ruled out."),
         ("Open work", f'{pl["future_reportdate"]} open WOs carry report dates after the cut-off and are counted in backlog.'),
         ("Capacity", "Not in Maximo. Assumed: active trades &times; 40 h/week.")]
nt = "".join(f'<div style="margin-top:14px"><div style="font-size:14px;font-weight:600">{a_}</div><div class="kv" style="margin-top:3px;line-height:1.5">{b_}</div></div>' for a_, b_ in NOTES)
keys = (f'<div class="c" style="height:150px"><div class="cq">Status</div><div style="display:flex;gap:26px;margin-top:16px;font-size:15px">'
        f'<span style="color:{GREEN}">&#10003; <span class="dim">on target</span></span><span style="color:{AMBER}">&#9679; <span class="dim">near</span></span>'
        f'<span style="color:{RED}">&#9650; <span class="dim">off target</span></span></div>'
        f'<div class="kv" style="margin-top:14px">Status colours only ever mean status.</div></div>'
        f'<div class="c" style="height:150px"><div class="cq">Sites</div><div style="display:flex;gap:26px;margin-top:16px;font-size:15px">'
        + "".join(f'<span><span class="dot" style="background:{SITE[s]};margin-right:8px;box-shadow:0 0 6px {SITE[s]}"></span>{NAME[s]}</span>' for s in ["BEDFORD", "AURORA", "HOUSTON"])
        + '</div><div class="kv" style="margin-top:14px">Site colours never signal good or bad.</div></div>'
        f'<div class="c" style="height:150px"><div class="cq">Data window</div><div style="font-size:22px;font-weight:500;margin-top:12px">Jul 2023 &ndash; Jul 2026</div>'
        f'<div class="kv" style="margin-top:6px">40,935 work orders &middot; 900 assets &middot; 3 sites</div></div>')
body = f'''<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-top:22px">{keys}</div>
<div class="g2" style="grid-template-columns:1fr 420px 400px">
 <div class="c" style="height:694px"><div class="cq">KPI definitions</div><div class="cs">as implemented in the semantic model</div>{kd}</div>
 <div class="c" style="height:694px"><div class="cq">Work types</div><div class="cs">reactive = unplanned; drives Reactive %</div><div style="margin-top:8px">{wt}</div>
  <div class="note">Definitions live in DimWorkType, so this list can&rsquo;t drift from the data.</div></div>
 <div class="c" style="height:694px"><div class="cq">Read before you quote a number</div>{nt}</div>
</div>'''
o4 = page("Information", "How to read this report", "", "Definitions, targets and the data&rsquo;s known limits.", "", body, "information_v6.html")
print(o1, o2, o3, o4, sep="\n")
