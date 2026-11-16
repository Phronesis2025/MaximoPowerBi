"""Reliability v9 - reliability engineer, chart-first (user: 'more visuals, too much text')."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_roles as gr
gp, g = gr.gp, gr.g
P, F, RN = gr.P, gr.F, gr.RN
SITE, NAME, S3 = gr.SITE, gr.NAME, gr.S3
GREEN, AMBER, RED, MUT, FAINT, TXT, MONO, GLY = gr.GREEN, gr.AMBER, gr.RED, gr.MUT, gr.FAINT, gr.TXT, gr.MONO, gr.GLY
kpi, page, NOB = gr.kpi, gr.page, gr.NOB
rl, R = P["rel"], RN["rel"]
A = F["ALL"]
BO = ["BEDFORD", "AURORA", "HOUSTON"]

def t(x, y, s, size=12, fill=MUT, w=400, anchor="start", font="mono"):
    fam = MONO if font == "mono" else "Segoe UI"
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font-family:{fam};font-size:{size}px;font-weight:{w};fill:{fill}">{s}</text>'

def site_cols(vals, W=104, H=62):
    """three site columns, zero-based - sits beside the KPI number"""
    mx = max(vals[s] for s in BO)
    bw, gap = 22, 13
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for i, s in enumerate(BO):
        h = vals[s] / mx * (H - 16); x = 4 + i * (bw + gap)
        o.append(f'<rect x="{x}" y="{H - 14 - h:.1f}" width="{bw}" height="{h:.1f}" rx="3" fill="{SITE[s]}" fill-opacity=".85"/>')
        o.append(t(x + bw / 2, H - 2, NAME[s][0], 10, FAINT, 400, "middle"))
    return "".join(o) + "</svg>"

def kpi_c(label, num, cols, foot):
    return (f'<div class="kpi"><div class="klabel">{label}</div><div class="kmid"><div class="knum">{num}</div>{cols}</div>'
            f'<div class="kfoot"><span style="color:{MUT}">{foot}</span><span class="ktarget"></span></div></div>')

cm = R["cost_map"]
top45 = R["top45_cost_share"] / 100 * R["react_cost_total"]
# plain cards, same pattern as PM & Planning: one number, one bar at most, one short footer
hero_bar = (f'<div style="position:relative;height:10px;margin-top:16px;background:#222227;border-radius:5px">'
            f'<i style="position:absolute;left:0;top:0;bottom:0;width:{rl["bad_share"]:.1f}%;background:{RED};border-radius:5px;box-shadow:0 0 10px {RED}"></i></div>'
            f'<div class="kv" style="margin-top:8px"><span style="color:{RED}">{rl["bad_k"]} of {rl["n_assets"]} assets</span> &middot; the worst 5%</div>')
k = "".join([
    gr.hero("Failures from the worst 5% of assets", f'{rl["bad_share"]:.1f}%', hero_bar),
    kpi("Reactive cost, worst 45", f'${top45 / 1e6:.1f}M', "3 years", NOB, f'{R["top45_cost_share"]:.0f}% of reactive cost', MUT, None, ""),
    kpi("MTTR", f'{rl["mttr"]["ALL"]:.1f}<small>h</small>', "", NOB, f'Houston {rl["mttr"]["HOUSTON"]:.1f} h', MUT, None, ""),
    kpi("Downtime", f'{rl["dt_hours"]["ALL"] / 1000:.0f}k<small>h</small>', "3 years", NOB,
        f'{rl["dt_hours"]["HOUSTON"] / rl["dt_hours"]["ALL"] * 100:.0f}% at Houston', MUT, None, ""),
    kpi("MTBF", f'{A["mtbf"]:,.0f}<small>h</small>', "", NOB, "provisional", MUT, None, ""),
])

# ---------- drift chart (kept) ----------
dm = rl["drift_months"]
c1 = gp.linechart([("Other assets", "#A1A1AA", rl["drift_rest"], False), ("Bad actors", RED, rl["drift_bad"], True)],
                  dm, (80, 180), [80, 100, 120, 140, 160, 180], 1030, 240, target=100, tlabel="baseline = 100 (Jul&ndash;Sep 2023)", fmt="{:.0f}")

# ---------- criticality: four columns that come out level ----------
def crit_cols(W=490, H=236):
    cr = rl["crit"]; L, B, T = 34, 40, 26
    Y = lambda v: T + (20 - v) / 20 * (H - T - B)
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for v in (0, 10, 20):
        o.append(f'<line x1="{L}" x2="{W}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#1D1D21"/>')
        o.append(t(L - 8, Y(v) + 4, v, 11, FAINT, 400, "end"))
    cw = (W - L) / 4; bw = 64
    for i, c in enumerate(["1", "2", "3", "4"]):
        v = cr[c]["fpa"]; x = L + i * cw + (cw - bw) / 2
        o.append(f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw}" height="{Y(0) - Y(v):.1f}" rx="5" fill="#A1A1AA" fill-opacity=".75"/>')
        o.append(t(x + bw / 2, Y(v) - 8, f"{v:.1f}", 15, TXT, 600, "middle", "sans"))
        o.append(t(x + bw / 2, H - 20, f"CRIT {c}", 11.5, "#D4D4D8", 600, "middle"))
        o.append(t(x + bw / 2, H - 5, "most critical" if c == "1" else "least" if c == "4" else "", 10.5, FAINT, 400, "middle"))
    return "".join(o) + "</svg>"

# ---------- what fails: thick bars ----------
def fails(W=490, H=246):
    pr = rl["problems"][:6]; mx = pr[0]["n"]; L = 118; rh = 38
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for i, p in enumerate(pr):
        y = 10 + i * rh; w = p["n"] / mx * (W - L - 60)
        o.append(t(0, y + 15, p["name"], 13.5, "#D4D4D8", 400, "start", "sans"))
        o.append(f'<rect x="{L}" y="{y}" width="{w:.1f}" height="20" rx="4" fill="{"#D4D4D8" if i < 4 else "#A1A1AA"}" fill-opacity="{.85 if i < 4 else .45}"/>')
        o.append(t(L + w + 8, y + 15, f'{p["n"]:,}', 12.5, TXT, 600))
    return "".join(o) + "</svg>"

# ---------- bad actors: failures bar + downtime bar ----------
def actors(W=426, H=590):
    L = 150; mxf = rl["top"][0]["fails"]; mxd = max(x["dt"] for x in rl["top"]); rh = 57
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for i, a in enumerate(rl["top"]):
        y = 8 + i * rh
        o.append(f'<circle cx="5" cy="{y + 11}" r="4" fill="{SITE[a["site"]]}"/>')
        o.append(t(16, y + 15, a["asset"], 12.5, TXT, 600))
        o.append(t(16, y + 32, f'${cm.get(a["asset"], 0) / 1000:.0f}k', 11.5, FAINT))
        wf = a["fails"] / mxf * (W - L - 44)
        o.append(f'<rect x="{L}" y="{y + 2}" width="{wf:.1f}" height="16" rx="4" fill="{RED}" fill-opacity=".85" style="filter:drop-shadow(0 0 8px {RED}55)"/>')
        o.append(t(L + wf + 8, y + 15, a["fails"], 12.5, RED, 600))
        wd = a["dt"] / mxd * (W - L - 70)
        if wd > 0:
            o.append(f'<rect x="{L}" y="{y + 23}" width="{wd:.1f}" height="7" rx="3" fill="#A1A1AA" fill-opacity=".6"/>')
        o.append(t(L + max(wd, 0) + 8, y + 31, f'{a["dt"]:,.0f} h', 10.5, FAINT))
    return "".join(o) + "</svg>"
leg = (f'<div class="kv" style="display:flex;gap:16px;margin-top:12px"><span><i class="sw" style="background:{RED}"></i>failures</span>'
       f'<span><i class="sw" style="background:#A1A1AA99"></i>downtime hours</span><span>$ = reactive cost</span></div>')

body = f'''<div class="g2" style="grid-template-columns:1fr 470px">
 <div class="col">
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Can we see failures coming?</div><div class="cs">condition meter readings, indexed &middot; {rl["drift_bad_n"]} metered bad actors vs {rl["drift_rest_n"]} other assets</div></div></div>{c1}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
   <div class="c" style="height:326px"><div class="cq">Does criticality predict failure? <span style="color:{RED}">No.</span></div><div class="cs">failures per asset &middot; every level fails about as often</div><div style="margin-top:8px">{crit_cols()}</div></div>
   <div class="c" style="height:326px"><div class="cq">What fails?</div><div class="cs">failure reports by problem code, all sites</div><div style="margin-top:12px">{fails()}</div></div>
  </div>
 </div>
 <div class="c" style="height:666px"><div class="ch"><div><div class="cq">Top 10 bad actors</div><div class="cs">all ten at Houston &middot; 3 yrs</div></div><span class="lk">All {rl["bad_k"]} &#8594;</span></div>{leg}
  <div style="margin-top:12px">{actors()}</div></div>
</div>'''
out = page("Reliability", "Reliability", "Jul 2023 &ndash; Jul 2026",
           f'<b>{rl["bad_k"]} assets cause {rl["bad_share"]:.0f}% of failures</b> &mdash; and their condition meters have drifted {rl["drift_bad"][-1] - 100:.0f}% above baseline.',
           k, body, "reliability_v9.html")
print(out)
