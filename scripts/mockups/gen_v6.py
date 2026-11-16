"""Executive Overview v6, dark style. Every figure from exec_numbers.json / v6_numbers.json / README counts."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "..", "..", "assets", "mockups")  # rendered HTML/PNG live here
from gear import gear_wrench

D = json.load(open(os.path.join(HERE, "exec_numbers.json")))
V = json.load(open(os.path.join(HERE, "v6_numbers.json")))
F, R = D["full"], D["rolling"]
A = F["ALL"]

# ---- tokens ----
BG, SIDE, CARD, LINE, SEL = "#0A0A0B", "#0E0E10", "#131315", "#232327", "#1C1C20"
TXT, MUT, FAINT = "#EDEDEF", "#8B8B93", "#5C5C66"
GREEN, AMBER, RED = "#4ADE80", "#FBBF24", "#F87171"
SITE = {"BEDFORD": "#60A5FA", "AURORA": "#22D3EE", "HOUSTON": "#C084FC", "ALL": "#A1A1AA"}
NAME = {"BEDFORD": "Bedford", "AURORA": "Aurora", "HOUSTON": "Houston"}
FULLNAME = {"BEDFORD": "Bedford Assembly Plant", "AURORA": "Aurora Distribution Center",
            "HOUSTON": "Houston Process Facility"}
WOS = {"BEDFORD": 10462, "AURORA": 10999, "HOUSTON": 19474}  # README: excl. cancelled
GLY = {RED: "&#9650;", AMBER: "&#9679;", GREEN: "&#10003;"}
MONO = "Consolas, 'SF Mono', Menlo, monospace"

def lower(v, t, near): return GREEN if v <= t else AMBER if v <= near else RED
def higher(v, t, near): return GREEN if v >= t else AMBER if v >= near else RED

def monotone(pts):
    """Fritsch-Carlson monotone cubic -> SVG path (same idea as Vega 'monotone')."""
    n = len(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / s ** .5; m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]
    p = f"M{xs[0]:.1f},{ys[0]:.1f}"
    for i in range(n - 1):
        h = (xs[i + 1] - xs[i]) / 3
        p += (f" C{xs[i] + h:.1f},{ys[i] + m[i] * h:.1f} {xs[i + 1] - h:.1f},{ys[i + 1] - m[i + 1] * h:.1f}"
              f" {xs[i + 1]:.1f},{ys[i + 1]:.1f}")
    return p

def glow(path, color, w=2.2, strength=1.0):
    """Buildable glow: the same path drawn three times (wide/faint -> thin/solid). Works in Deneb."""
    return (f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{w * 6}" stroke-opacity="{.06 * strength}" stroke-linecap="round"/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{w * 3}" stroke-opacity="{.16 * strength}" stroke-linecap="round"/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>')

def spark(vals, w, h, color, minrange=None, dom=None):
    if dom:
        lo, hi = dom
    else:
        lo, hi = min(vals), max(vals)
        if minrange and hi - lo < minrange:
            mid = (hi + lo) / 2; lo, hi = mid - minrange / 2, mid + minrange / 2
    pad = 6
    pts = [(pad + i * (w - 2 * pad) / (len(vals) - 1), pad + (hi - v) / (hi - lo) * (h - 2 * pad)) for i, v in enumerate(vals)]
    ex, ey = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{glow(monotone(pts), color, 1.6)}'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.8" fill="{color}"/></svg>')

def ser(site, k): return [p[k] for p in R[site]]

def bullet(val, lo, hi, target, color, band=None):
    pc = lambda v: max(0, min(100, (v - lo) / (hi - lo) * 100))
    b = f'<i class="band" style="left:{pc(band[0])}%;width:{pc(band[1]) - pc(band[0])}%"></i>' if band else ""
    return (f'<div class="bullet">{b}<i class="fill" style="width:{pc(val)}%;background:{color};box-shadow:0 0 10px {color}55"></i>'
            f'<i class="tick" style="left:calc({pc(target)}% - 1px)"></i></div>')

# ---- KPI cards ----
def kpi(label, num, target, bul, delta, dcol, vals, scol, hero=False, mr=10):
    sw, sh = (260, 70) if hero else (92, 34)
    return f'''<div class="kpi{' hero' if hero else ''}">
 <div class="klabel">{label}</div>
 <div class="kmid"><div class="knum">{num}</div>{spark(vals, sw, sh, scol, minrange=mr)}</div>
 {bul}
 <div class="kfoot"><span style="color:{dcol}">{delta}</span><span class="ktarget">{target}</span></div>
</div>'''

mtbf_d = (D["ty"]["mtbf"] / D["ly"]["mtbf"] - 1) * 100
kpis = "".join([
    kpi("Reactive maintenance", f'{A["reactive"]:.1f}%', "target &lt; 20%", bullet(A["reactive"], 0, 50, 20, RED),
        f'{GLY[RED]} +{A["reactive"] - 20:.1f} pts vs target', RED, ser("ALL", "reactive"), RED, hero=True),
    kpi("PM compliance", f'{A["pm"]:.1f}%', "target 90%", bullet(A["pm"], 0, 100, 90, AMBER),
        f'{GLY[AMBER]} &minus;{90 - A["pm"]:.1f} pts', AMBER, ser("ALL", "pm"), AMBER),
    kpi("Statutory compliance", f'{A["stat"]:.1f}%', "target 100%", bullet(A["stat"], 0, 100, 100, RED),
        f'{GLY[RED]} {A["stat_late"]} late', RED, ser("ALL", "stat"), RED),
    kpi("MTBF", f'{A["mtbf"]:,.0f}<small>h</small>', "", '<div class="bullet none"></div>',
        f'+{mtbf_d:.0f}% yoy &middot; provisional', MUT, ser("ALL", "mtbf"), "#A1A1AA", mr=600),
    kpi("Cost % of RAV", f'{A["costrav"]:.1f}%', "best 2&ndash;3%", bullet(A["costrav"], 0, 10, 3, RED, band=(2, 3)),
        f'{GLY[RED]} +{A["costrav"] - 3:.1f} pts', RED, ser("ALL", "costrav"), RED, mr=3),
])

# ---- mirrored chart: planned above, reactive below ----
M = V["months"]                       # Aug 23 .. Jun 26, complete months only
CW, CH = 1010, 512
L, Rr, T, B = 64, 112, 16, 16
pw = CW - L - Rr
mid = T + (CH - T - B) / 2
half = (CH - T - B) / 2 - 14
top = 350
X = lambda i: L + i * pw / (len(M) - 1)
Yp = lambda v: mid - 14 - v / top * half
Yr = lambda v: mid + 14 + v / top * half
svg = [f'<svg width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">']
for v in (100, 200, 300):
    for yy in (Yp(v), Yr(v)):
        svg.append(f'<line x1="{L}" x2="{L + pw}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#1D1D21"/>')
    svg.append(f'<text x="{L - 14}" y="{Yp(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    svg.append(f'<text x="{L - 14}" y="{Yr(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
svg.append(f'<line x1="{L}" x2="{L + pw}" y1="{Yp(0):.1f}" y2="{Yp(0):.1f}" stroke="#2A2A2F"/>')
svg.append(f'<line x1="{L}" x2="{L + pw}" y1="{Yr(0):.1f}" y2="{Yr(0):.1f}" stroke="#2A2A2F"/>')
for i, lab in enumerate(M):
    if lab.startswith(("Jan", "Jul")) or i == len(M) - 1:
        svg.append(f'<text x="{X(i):.1f}" y="{mid + 4:.1f}" class="ax" text-anchor="middle">{lab}</text>')
svg.append(f'<text x="{L}" y="{T + 2}" class="axh">PLANNED &#8593;  work orders / month</text>')
svg.append(f'<text x="{L}" y="{CH - 2}" class="axh">REACTIVE &#8595;  work orders / month</text>')
for s in ["HOUSTON", "AURORA", "BEDFORD"]:
    p = V["monthly"][s]["plan"]
    path = monotone([(X(i), Yp(v)) for i, v in enumerate(p)])
    svg.append(f'<path d="{path}" fill="none" stroke="{SITE[s]}" stroke-width="1.6" stroke-opacity=".45"/>')
for s in ["HOUSTON", "AURORA", "BEDFORD"]:
    r = V["monthly"][s]["react"]
    svg.append(glow(monotone([(X(i), Yr(v)) for i, v in enumerate(r)]), SITE[s], 2.4))
# end labels
ends = []
for s in ["HOUSTON", "AURORA", "BEDFORD"]:
    ends.append((Yp(V["monthly"][s]["plan"][-1]), s, V["monthly"][s]["plan"][-1], .55))
    ends.append((Yr(V["monthly"][s]["react"][-1]), s, V["monthly"][s]["react"][-1], 1))
ends.sort()
last = -99
for y, s, v, op in ends:
    y = max(y, last + 17); last = y
    svg.append(f'<text x="{L + pw + 12}" y="{y + 4:.1f}" class="endl" fill="{SITE[s]}" fill-opacity="{op}">{NAME[s]} <tspan class="endv">{v}</tspan></text>')
# annotation: Aurora June reactive, three years
ar = V["monthly"]["AURORA"]["react"]
jn = [i for i, m in enumerate(M) if m.startswith("Jun")]
for i in jn:
    svg.append(f'<circle cx="{X(i):.1f}" cy="{Yr(ar[i]):.1f}" r="4" fill="{BG}" stroke="{SITE["AURORA"]}" stroke-width="2"/>')
for i in jn[:-1]:
    svg.append(f'<text x="{X(i):.1f}" y="{Yr(ar[i]) + 22:.1f}" class="anno" text-anchor="middle" fill="{SITE["AURORA"]}">{ar[i]}</text>')
svg.append("</svg>")
chart = "".join(svg)

# headline numbers for the chart card: reactive WOs, last 12 complete months vs prior 12
idx = {m: i for i, m in enumerate(M)}
cur = sum(sum(V["monthly"][s]["react"][idx["Jul 25"]:idx["Jun 26"] + 1]) for s in WOS)
pri = sum(sum(V["monthly"][s]["react"][idx["Jul 24"]:idx["Jun 25"] + 1]) for s in WOS)
chg = (cur / pri - 1) * 100

YOY = ""
for s in ["BEDFORD", "AURORA", "HOUSTON"]:
    r = V["monthly"][s]["react"]; a_, b_ = sum(r[idx["Jul 24"]:idx["Jun 25"] + 1]), sum(r[idx["Jul 25"]:idx["Jun 26"] + 1])
    ch = (b_ / a_ - 1) * 100
    col = GREEN if ch < -5 else RED if ch > 0 else MUT
    YOY += f'<span><i style="background:{SITE[s]}"></i>{NAME[s]} <em style="color:{col}">{"&minus;" if ch < 0 else "+"}{abs(ch):.0f}%</em></span>'
# ---- site cards ----
PILL = {"BEDFORD": ("BENCHMARK", GREEN), "AURORA": ("IMPROVING", SITE["AURORA"]), "HOUSTON": ("FIREFIGHTING", RED)}
def metric(lbl, val, col):
    g = f'<span class="g">{GLY[col]}</span>' if col in GLY else ""
    return f'<div class="m"><div class="ml">{lbl}</div><div class="mv" style="color:{col}">{g}{val}</div></div>'
sites = ""
for s in ["HOUSTON", "AURORA", "BEDFORD"]:
    m = F[s]; p, pc = PILL[s]
    sites += f'''<div class="site">
 <div class="shead"><span class="dot" style="background:{SITE[s]};box-shadow:0 0 8px {SITE[s]}"></span>
  <span class="sname">{FULLNAME[s]}</span><span class="pill" style="color:{pc};border-color:{pc}55">{p}</span></div>
 <div class="srow">
  {metric("REACTIVE", f'{m["reactive"]:.1f}%', lower(m["reactive"], 20, 22))}
  {metric("PM", f'{m["pm"]:.1f}%', higher(m["pm"], 90, 80))}
  {metric("STATUTORY", f'{m["stat"]:.1f}%', higher(m["stat"], 100, 95))}
  {metric("MTBF", f'{m["mtbf"]:,.0f}h', TXT)}
  {metric("COST/RAV", f'{m["costrav"]:.1f}%', lower(m["costrav"], 3, 4.5))}
 </div>
 <div class="sfoot"><div class="ml">REACTIVE %, ROLLING 12 MO &nbsp;<span class="se">{ser(s, "reactive")[0]:.1f} &#8594; <b style="color:{SITE[s]}">{ser(s, "reactive")[-1]:.1f}</b></span></div>{spark(ser(s, "reactive"), 432, 58, SITE[s], dom=(18, 48))}</div>
</div>'''

# ---- sidebar icons (simple line icons) ----
def ico(d): return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{d}</svg>'
I = {
 "Overview": ico('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
 "PM &amp; Compliance": ico('<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>'),
 "Reliability": ico('<path d="M3 12h4l2.5-6 5 12 2.5-6H21"/>'),
 "Planning": ico('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
 "Information": ico('<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>'),
}
nav = "".join(f'<div class="nav{" on" if k == "Overview" else ""}">{v}<span>{k}</span></div>' for k, v in I.items())
sitelist = f'<div class="sl on"><span class="dot" style="background:#A1A1AA"></span>All sites<span class="cnt">{sum(WOS.values()):,}</span></div>'
for s in ["BEDFORD", "AURORA", "HOUSTON"]:
    sitelist += f'<div class="sl"><span class="dot" style="background:{SITE[s]};box-shadow:0 0 6px {SITE[s]}"></span>{NAME[s]}<span class="cnt">{WOS[s]:,}</span></div>'
logo = '<svg width="26" height="26" viewBox="0 0 26 26">' + "".join(gear_wrench(13, 13, 19, TXT, SIDE)) + "</svg>"

html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1920px;height:1080px;background:{BG};color:{TXT};font-family:"Segoe UI",system-ui,sans-serif;overflow:hidden;display:flex}}
.mono,.ml,.ax,.kfoot,.cnt,.lab{{font-family:{MONO}}}
aside{{width:272px;background:{SIDE};border-right:1px solid {LINE};padding:22px 16px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:600;padding:0 8px}}
.brand small{{color:{MUT};font-weight:400}}
.lab{{font-size:12px;color:{FAINT};margin:30px 10px 10px}}
.nav{{display:flex;align-items:center;gap:12px;font-size:15px;color:#B4B4BC;padding:9px 10px;border-radius:8px;margin-bottom:2px}}
.nav svg{{color:{MUT}}}
.nav.on{{background:{SEL};color:{TXT};box-shadow:inset 0 0 0 1px #2A2A30}}
.nav.on svg{{color:{TXT}}}
.sl{{display:flex;align-items:center;gap:12px;font-size:15px;color:#B4B4BC;padding:8px 10px;border-radius:8px}}
.sl.on{{background:{SEL};color:{TXT}}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}}
.cnt{{margin-left:auto;font-size:13px;color:{FAINT}}}
.sep{{height:1px;background:{LINE};margin:22px 0 0}}
.legend{{margin-top:auto;font-family:{MONO};font-size:12px;color:{MUT};padding:0 10px;line-height:1.9}}
.legend b{{font-weight:400}}
.foot{{font-family:{MONO};font-size:11px;color:{FAINT};padding:14px 10px 0;border-top:1px solid {LINE};margin-top:16px;line-height:1.6}}
main{{flex:1;display:flex;flex-direction:column}}
.top{{height:56px;border-bottom:1px solid {LINE};display:flex;align-items:center;padding:0 36px;gap:10px;font-size:15px;color:#C8C8CF}}
.top .r{{margin-left:auto;display:flex;align-items:center;gap:18px}}
.seg{{display:flex;border:1px solid {LINE};border-radius:8px;padding:3px;background:{CARD}}}
.seg span{{font-family:{MONO};font-size:12px;color:{MUT};padding:4px 11px;border-radius:5px}}
.seg span.on{{background:#26262B;color:{TXT}}}
.asof{{font-family:{MONO};font-size:12px;color:{FAINT}}}
.body{{padding:22px 36px 0}}
h1{{font-size:40px;font-weight:300;letter-spacing:-.5px}}
h1 span{{color:#6E6E78}}
.sub{{font-size:17px;color:#A1A1AA;margin-top:4px}}
.sub b{{color:{TXT};font-weight:600}}
.kpis{{display:grid;grid-template-columns:1.75fr 1fr 1fr 1fr 1fr;gap:14px;margin-top:22px}}
.kpi{{background:{CARD};border:1px solid {LINE};border-radius:14px;padding:18px 20px 16px;height:184px;display:flex;flex-direction:column}}
.kpi>*{{flex-shrink:0}}
.klabel{{font-size:15px;color:#A1A1AA}}
.kmid{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:8px}}
.knum{{font-size:38px;font-weight:500;letter-spacing:-.5px;line-height:1.05}}
.knum small{{font-size:20px;color:{MUT};margin-left:3px}}
.hero .knum{{font-size:64px;font-weight:500;letter-spacing:-1.5px}}
.bullet{{position:relative;height:4px;background:#222227;border-radius:2px;margin-top:16px}}
.bullet.none{{background:none}}
.bullet i{{position:absolute;top:0;bottom:0;border-radius:2px}}
.bullet .fill{{left:0}}
.bullet .band{{background:#4ADE8040}}
.bullet .tick{{top:-5px;bottom:-5px;width:2px;background:#E4E4E7}}
.kfoot{{display:flex;justify-content:space-between;margin-top:auto;font-size:13px}}
.ktarget{{color:{FAINT}}}
.grid2{{display:grid;grid-template-columns:1fr 470px;gap:14px;margin-top:14px}}
.card{{background:{CARD};border:1px solid {LINE};border-radius:14px}}
.chart{{height:666px;padding:20px 24px}}
.ct{{display:flex;justify-content:space-between;align-items:flex-start}}
.ctl{{font-size:15px;color:#A1A1AA}}
.big{{font-size:36px;font-weight:500;margin-top:4px;letter-spacing:-.5px}}
.delta{{font-family:{MONO};font-size:13px;margin-top:2px}}
.lg{{display:flex;gap:18px;font-size:13px;color:#B4B4BC;margin-top:6px}}
.lg span{{display:flex;align-items:center;gap:7px}}
.lg em{{font-style:normal;font-family:{MONO};font-size:12px}}
.lg i{{width:16px;height:2px;border-radius:1px;display:inline-block}}
.ax{{font-size:12px;fill:{FAINT}}}
.rt{{text-align:right}}
.june{{font-family:{MONO};font-size:12px;color:{MUT};margin-top:12px}}
.june b{{color:#22D3EE;font-weight:600}}
.axh{{font-family:{MONO};font-size:11px;fill:{MUT};letter-spacing:.5px}}
.endl{{font-size:13px;font-family:"Segoe UI"}}
.endv{{font-family:{MONO};font-weight:600}}
.anno{{font-family:{MONO};font-size:12px;font-weight:600}}
.sites{{display:flex;flex-direction:column;gap:14px}}
.site{{background:{CARD};border:1px solid {LINE};border-radius:14px;padding:16px 18px 12px;height:212px;display:flex;flex-direction:column}}
.shead{{display:flex;align-items:center;gap:10px}}
.sname{{font-size:16px;font-weight:600}}
.pill{{margin-left:auto;font-family:{MONO};font-size:10.5px;letter-spacing:.6px;border:1px solid;border-radius:6px;padding:2px 7px}}
.srow{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:16px}}
.ml{{font-size:10.5px;color:{FAINT};letter-spacing:.4px}}
.mv{{font-size:18px;font-weight:500;margin-top:4px;white-space:nowrap}}
.g{{font-size:9px;margin-right:4px;position:relative;top:-2px}}
.sfoot{{margin-top:auto;border-top:1px solid #1E1E22;padding-top:10px}}
.se{{color:{MUT}}}
.sfoot svg{{display:block;margin-top:2px}}
</style></head><body>
<aside>
 <div class="brand">{logo}Maximo <small>Analytics</small></div>
 <div class="lab">Pages</div>{nav}
 <div class="sep"></div>
 <div class="lab">Sites</div>{sitelist}
 <div class="legend"><b style="color:{GREEN}">&#10003;</b> on target<br><b style="color:{AMBER}">&#9679;</b> near target<br><b style="color:{RED}">&#9650;</b> off target</div>
 <div class="foot">Synthetic data<br>{sum(WOS.values()):,} work orders &middot; 3 sites</div>
</aside>
<main>
 <div class="top">{I["Overview"]}<span>Overview</span>
  <div class="r"><div class="seg"><span class="on">All</span><span>2024</span><span>2025</span><span>2026</span></div><span class="asof">data as of 29 Jul 2026</span></div></div>
 <div class="body">
  <h1>Maintenance <span>Jul 2023 &ndash; Jul 2026</span></h1>
  <div class="sub"><b>Houston is running reactive.</b> Aurora cut its reactive work by a fifth in a year.</div>
  <div class="kpis">{kpis}</div>
  <div class="grid2">
   <div class="card chart">
    <div class="ct"><div>
      <div class="ctl">Reactive work orders &middot; last 12 months</div>
      <div class="big">{cur:,}</div>
      <div class="delta" style="color:{GREEN}">{"&minus;" if chg < 0 else "+"}{abs(chg):.1f}% <span style="color:{FAINT}">vs prior 12 months</span></div>
     </div>
     <div class="rt"><div class="lg">{YOY}</div>
     <div class="june">&#9675; Aurora reactive, each June &nbsp;<b>{ar[jn[0]]} &#8594; {ar[jn[1]]} &#8594; {ar[jn[2]]}</b></div></div>
    </div>
    {chart}
   </div>
   <div class="sites">{sites}</div>
  </div>
 </div>
</main>
</body></html>'''
out = os.path.join(OUT, "executive_v6.html")
open(out, "w", encoding="utf-8").write(html)
print(out, "reactive last12", cur, "prior12", pri, f"{"&minus;" if chg < 0 else "+"}{abs(chg):.1f}%", "june aurora", [ar[i] for i in jn])
