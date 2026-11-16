"""Overview v10 - VP / portfolio view: money, risk, direction, where to intervene."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_v9_overview as v9
v8, v7, gp, g = v9.v8, v9.v7, v9.gp, v9.g
F = g.F
SITE, NAME = g.SITE, g.NAME
GREEN, AMBER, RED, MUT, FAINT, TXT, MONO, BG = g.GREEN, g.AMBER, g.RED, g.MUT, g.FAINT, g.TXT, g.MONO, g.BG
ORDER = ["HOUSTON", "AURORA", "BEDFORD"]
VP = json.load(open(os.path.join(HERE, "vp_numbers.json")))
P = json.load(open(os.path.join(HERE, "pages_numbers.json")))
ly, ty, t = v9.ly, v9.ty, v9.t
M = lambda v: f"${v / 1e6:.1f}M"
yoy = {s: (ty[s] / ly[s] - 1) * 100 for s in ORDER}

# ---------------- KPI cards (VP framing) ----------------
def card(label, num, foot_l, foot_r, col, extra="", hero=False):
    return (f'<div class="kpi{" hero" if hero else ""}"><div class="klabel">{label}</div>'
            f'<div class="kmid"><div class="knum">{num}</div></div>{extra}'
            f'<div class="kfoot"><span style="color:{col}">{foot_l}</span><span class="ktarget">{foot_r}</span></div></div>')
gapH, gapA = VP["HOUSTON"]["gap"], VP["AURORA"]["gap"]
hero_extra = (f'<div class="stk" style="height:10px;margin-top:16px">'
              f'<i style="width:{gapH / VP["gap"] * 100:.1f}%;background:{SITE["HOUSTON"]};box-shadow:0 0 10px {SITE["HOUSTON"]}"></i>'
              f'<i style="width:{gapA / VP["gap"] * 100:.1f}%;background:{SITE["AURORA"]}"></i></div>'
              f'<div class="kv" style="margin-top:8px"><span style="color:{SITE["HOUSTON"]}">Houston {M(gapH)}</span> &middot; '
              f'<span style="color:{SITE["AURORA"]}">Aurora {M(gapA)}</span> &middot; Bedford is the benchmark</div>')
dirs = "".join(f'<div style="display:flex;justify-content:space-between;font-size:14px;margin-top:5px"><span><span class="dot" style="background:{SITE[s]};margin-right:7px"></span>{NAME[s]}</span>'
               f'<span style="font-family:{MONO};font-weight:600;color:{GREEN if yoy[s] < -5 else RED if yoy[s] > 0 else "#A1A1AA"}">{"&#9660;" if yoy[s] < 0 else "&#9650;"} {yoy[s]:+.0f}%</span></div>' for s in ORDER)
kpis = "".join([
    card("Spend above our own benchmark", f'{M(VP["gap"])}<small>/yr</small>', "", "", RED, hero_extra, hero=True),
    card("Annual maintenance spend", f'{M(VP["tot"])}', f'{g.GLY[RED]} {F["ALL"]["costrav"]:.1f}% of asset value', "best 2&ndash;3%", RED,
         g.bullet(F["ALL"]["costrav"], 0, 10, 3, RED, band=(2, 3))),
    card("Spent on unplanned work", f'{VP["react"] / VP["tot"] * 100:.0f}%', f'{VP["cost_per_react"] / VP["cost_per_pm"]:.1f}&times; the cost of a PM', f'of {M(VP["tot"])}', AMBER,
         f'<div class="kv" style="margin-top:14px">${VP["cost_per_react"]:,.0f} per reactive job<br>${VP["cost_per_pm"]:,.0f} per PM</div>'),
    card("Statutory inspections late", f'{F["ALL"]["stat_late"]}', f'{g.GLY[RED]} 0 of 3 sites at 100%', "target 0", RED,
         f'<div class="kv" style="margin-top:14px">regulatory &amp; safety exposure</div>'),
    card("Reactive work, year on year", "", "", "last 12 vs prior 12 mo", MUT, f'<div style="margin-top:8px">{dirs}</div>'),
])

# ---------------- Where is the money going? ----------------
def money(W=720, H=236):
    L, R_ = 110, 150
    mx = 5.6e6
    X = lambda v: L + v / mx * (W - L - R_)
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for v in (0, 1e6, 2e6, 3e6, 4e6, 5e6):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="6" y2="{H - 22}" stroke="#1D1D21"/>')
        o.append(t(X(v), H - 6, f"${v / 1e6:.0f}M", 11, FAINT, 400, "middle"))
    for k, s in enumerate(ORDER):
        y = 14 + k * 68; d = VP[s]
        o.append(t(0, y + 22, NAME[s], 16, SITE[s], 600, "start", "sans"))
        o.append(t(0, y + 40, f'{d["pct"]:.1f}% of RAV', 11.5, MUT))
        o.append(f'<rect x="{X(0):.1f}" y="{y}" width="{X(d["plan"]) - X(0):.1f}" height="40" rx="6" fill="#A1A1AA" fill-opacity=".55"/>')
        o.append(f'<rect x="{X(d["plan"]):.1f}" y="{y}" width="{X(d["total"]) - X(d["plan"]):.1f}" height="40" rx="6" fill="{RED}" fill-opacity=".9" style="filter:drop-shadow(0 0 12px {RED}66)"/>')
        o.append(f'<line x1="{X(d["bench"]):.1f}" x2="{X(d["bench"]):.1f}" y1="{y - 6}" y2="{y + 46}" stroke="#F4F4F5" stroke-width="2.5"/>')
        o.append(t(X(d["total"]) + 12, y + 18, M(d["total"]), 17, TXT, 600, "start", "sans"))
        if d["gap"] > 1:
            o.append(t(X(d["total"]) + 12, y + 36, f'+{M(d["gap"])} over', 12.5, RED, 600))
        else:
            o.append(t(X(d["total"]) + 12, y + 36, "the benchmark", 12.5, GREEN, 600))
    return "".join(o) + "</svg>"
money_leg = (f'<div class="kv" style="display:flex;gap:18px;margin-top:6px"><span><i class="sw" style="background:#A1A1AA99"></i>planned work</span>'
             f'<span><i class="sw" style="background:{RED}"></i>reactive work</span>'
             f'<span><i class="sw" style="background:#F4F4F5;width:3px"></i>spend at Bedford&rsquo;s rate</span></div>')

# ---------------- Which sites need intervention? (2x2) ----------------
def quad(W=740, H=262):
    L, R_, T, B = 46, 16, 10, 34
    X = lambda v: L + v / 50 * (W - L - R_)
    Y = lambda v: T + (9 - v) / 9 * (H - T - B)
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    o.append(f'<rect x="{X(0)}" y="{Y(3):.1f}" width="{X(20) - X(0):.1f}" height="{Y(0) - Y(3):.1f}" fill="{GREEN}" fill-opacity=".10"/>')
    o.append(f'<rect x="{X(30):.1f}" y="{Y(9):.1f}" width="{X(50) - X(30):.1f}" height="{Y(5) - Y(9):.1f}" fill="{RED}" fill-opacity=".08"/>')
    o.append(t(X(1), Y(0.4), "WORLD-CLASS", 11, GREEN, 600))
    o.append(t(X(30.8), Y(8.5), "INTERVENE", 11, RED, 600, "start"))
    for v in (0, 3, 6, 9):
        o.append(f'<line x1="{L}" x2="{W - R_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#1D1D21"/>')
        o.append(t(L - 8, Y(v) + 4, f"{v}%", 11, FAINT, 400, "end"))
    for v in (0, 10, 20, 30, 40, 50):
        o.append(t(X(v), H - 16, f"{v}%", 11, FAINT, 400, "middle"))
    o.append(t((L + W) / 2, H - 1, "reactive share of work orders &#8594;", 11, MUT, 400, "middle"))
    o.append(f'<text x="12" y="{(T + H - B) / 2}" transform="rotate(-90 12 {(T + H - B) / 2})" text-anchor="middle" style="font-family:{MONO};font-size:11px;fill:{MUT}">cost % of asset value &#8594;</text>')
    for s in ORDER:
        x, y = X(F[s]["reactive"]), Y(F[s]["costrav"]); r = 9 + VP[s]["total"] / 5.0e6 * 16; c = SITE[s]
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 10:.1f}" fill="{c}" fill-opacity=".10"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{c}" fill-opacity=".85" style="filter:drop-shadow(0 0 14px {c})"/>')
        if s == "HOUSTON":
            lx, ly_, anc = x, y + r + 20, "middle"
        elif s == "AURORA":
            lx, ly_, anc = x - r - 12, y + 2, "end"
        else:
            lx, ly_, anc = x + r + 12, y + 2, "start"
        o.append(t(lx, ly_, NAME[s], 15, c, 600, anc, "sans"))
        o.append(t(lx, ly_ + 16, f'{M(VP[s]["total"])}/yr', 11.5, MUT, 400, anc))
    return "".join(o) + "</svg>"

# ---------------- compliance risk ----------------
st = P["pm"]["stat_by_type"]
mxl = max(st[s]["INSP"]["late"] + st[s]["SAF"]["late"] for s in ORDER)
risk = ""
for s in ORDER:
    late = st[s]["INSP"]["late"] + st[s]["SAF"]["late"]; n = st[s]["INSP"]["n"] + st[s]["SAF"]["n"]
    risk += (f'<div style="margin-top:16px"><div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:7px">'
             f'<span><span class="dot" style="background:{SITE[s]};margin-right:8px"></span>{NAME[s]}</span>'
             f'<span class="kv">{(1 - late / n) * 100:.1f}% on time</span></div>'
             f'<div style="display:flex;align-items:center;gap:12px"><div style="height:16px;width:{late / mxl * 78:.1f}%;background:{RED};border-radius:4px;box-shadow:0 0 12px {RED}66"></div>'
             f'<span style="font-size:20px;font-weight:600;color:{RED}">{late}</span></div></div>')

panels = "".join(
    f'<div><div style="display:flex;justify-content:space-between;font-size:14px;font-weight:600;margin-bottom:2px">'
    f'<span><span class="dot" style="background:{SITE[s]};box-shadow:0 0 6px {SITE[s]};margin-right:7px"></span>{NAME[s]}</span>'
    f'<span style="font-family:{MONO};color:{GREEN if yoy[s] < -5 else RED if yoy[s] > 0 else "#A1A1AA"}">{yoy[s]:+.0f}%</span></div>{v8.panel(s, 318, 232)}</div>'
    for s in ORDER)

body = f'''<div class="g2" style="grid-template-columns:1fr 1fr">
 <div class="c" style="height:330px"><div class="ch"><div><div class="cq">Where is the money going?</div><div class="cs">annual maintenance spend by site &middot; white tick = spend at Bedford&rsquo;s cost rate</div></div></div>
  <div style="margin-top:10px">{money()}</div>{money_leg}</div>
 <div class="c" style="height:330px"><div class="ch"><div><div class="cq">Which sites need intervention?</div><div class="cs">bubble size = annual spend &middot; green zone = &lt; 20% reactive and &le; 3% of asset value</div></div></div>
  <div style="margin-top:8px">{quad()}</div></div>
</div>
<div class="g2" style="grid-template-columns:1fr 470px">
 <div class="c" style="height:322px"><div class="ch"><div><div class="cq">Is it getting better?</div><div class="cs">reactive work orders by month &middot; solid = this year &middot; dashed = same month last year</div></div><span class="lk">Reliability &#8594;</span></div>
  <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;margin-top:10px">{panels}</div></div>
 <div class="c" style="height:322px"><div class="ch"><div><div class="cq">Where is our compliance risk?</div><div class="cs">statutory inspections finished late &middot; target 0</div></div><span class="lk">Late list &#8594;</span></div>{risk}</div>
</div>'''
out = gp.page("Overview", "Maintenance portfolio", "3 sites &middot; Jul 2023 &ndash; Jul 2026",
              f'<b>We spend {M(VP["gap"])} a year more than our own benchmark &mdash; {VP["HOUSTON"]["gap"] / VP["gap"] * 100:.0f}% of it at Houston.</b> Aurora shows it can be won back.',
              kpis, body, "executive_v10.html")
print(out)
