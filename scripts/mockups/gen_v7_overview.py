"""Overview v7: dumbbell (direction), same-month-last-year small multiples, KPI dot plot."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pages as gp
g = gp.g
V, F = g.V, g.F
SITE, NAME = g.SITE, g.NAME
GREEN, AMBER, RED, MUT, FAINT, TXT = g.GREEN, g.AMBER, g.RED, g.MUT, g.FAINT, g.TXT
M = V["months"]; ix = {m: i for i, m in enumerate(M)}
LY = slice(ix["Jul 24"], ix["Jun 25"] + 1)
TY = slice(ix["Jul 25"], ix["Jun 26"] + 1)
ORDER = ["HOUSTON", "AURORA", "BEDFORD"]

# ---------- dumbbell: reactive share, prior 12 vs last 12 complete months ----------
def share(s, sl):
    r, p = sum(V["monthly"][s]["react"][sl]), sum(V["monthly"][s]["plan"][sl])
    return r / (r + p) * 100, r
W, H = 1030, 214
L, Rr, T = 150, 200, 34
X = lambda v: L + (v - 15) / (50 - 15) * (W - L - Rr)
rowh = 52
s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
for v in (20, 30, 40, 50):
    s.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T - 12}" y2="{T + 3 * rowh - 18}" stroke="#1D1D21"/>')
    s.append(f'<text x="{X(v):.1f}" y="{T + 3 * rowh}" class="ax" text-anchor="middle">{v}%</text>')
s.append(f'<line x1="{X(20):.1f}" x2="{X(20):.1f}" y1="{T - 14}" y2="{T + 3 * rowh - 16}" stroke="{AMBER}" stroke-width="1.4" stroke-dasharray="5 5"/>')
s.append(f'<text x="{X(20) + 6:.1f}" y="{T - 18}" class="tgtl">target &lt; 20%</text>')
s.append(f'<text x="{L + 6}" y="{T - 18}" class="axh" style="fill:{FAINT}" text-anchor="end"></text>')
for k, st in enumerate(ORDER):
    y = T + k * rowh + 8
    a, ra = share(st, LY); b, rb = share(st, TY)
    d = b - a
    col = GREEN if d <= -1 else RED if d >= 0.5 else MUT
    c = SITE[st]
    s.append(f'<text x="0" y="{y + 5}" style="font-size:15px;fill:{TXT}">{NAME[st]}</text>')
    s.append(f'<line x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="4" stroke-opacity=".35" stroke-linecap="round"/>')
    s.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="7" fill="{g.BG}" stroke="{c}" stroke-width="2" stroke-opacity=".6"/>')
    s.append(f'<circle cx="{X(b):.1f}" cy="{y}" r="14" fill="{c}" fill-opacity=".12"/>')
    s.append(f'<circle cx="{X(b):.1f}" cy="{y}" r="8" fill="{c}"/>')
    lo, hi = (a, b) if a < b else (b, a)
    if abs(d) < 1.5:
        right = X(hi) < (L + W - Rr) / 2
        xx, anc = (X(hi) + 22, "start") if right else (X(lo) - 22, "end")
        s.append(f'<text x="{xx:.1f}" y="{y + 4}" class="endv" text-anchor="{anc}" style="font-size:13px;fill:{MUT}">{a:.1f} &#8594; <tspan style="fill:{c}">{b:.1f}</tspan></text>')
    else:
        s.append(f'<text x="{X(lo) - 22:.1f}" y="{y + 4}" class="endv" text-anchor="end" style="font-size:13px;fill:{MUT if lo == a else c}">{lo:.1f}</text>')
        s.append(f'<text x="{X(hi) + 22:.1f}" y="{y + 4}" class="endv" style="font-size:13px;fill:{MUT if hi == a else c}">{hi:.1f}</text>')
    arrow = "&#9660;" if d < 0 else "&#9650;"
    s.append(f'<text x="{W - Rr + 40}" y="{y + 5}" style="font-family:{g.MONO};font-size:14px;font-weight:600;fill:{col}">{arrow} {d:+.1f} pts</text>')
    s.append(f'<text x="{W - Rr + 40}" y="{y + 22}" class="ax">{rb - ra:+,} reactive WOs</text>')
s.append("</svg>")
dumbbell = "".join(s)

# ---------- small multiples: this year vs same month last year ----------
MS = ["J", "A", "S", "O", "N", "D", "J", "F", "M", "A", "M", "J"]
def panel(st, W=318, H=262):
    ly, ty = V["monthly"][st]["react"][LY], V["monthly"][st]["react"][TY]
    top = max(ly + ty); step = 100 if top > 100 else 50; top = (int(top / step) + 1) * step
    L, R_, T, B = 30, 10, 38, 22
    X = lambda i: L + i * (W - L - R_) / 11
    Y = lambda v: T + (top - v) / top * (H - T - B)
    c = SITE[st]
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    o.append(f'<text x="0" y="16" style="font-size:15px;fill:{TXT}">{NAME[st]}</text>')
    ch = (sum(ty) / sum(ly) - 1) * 100
    col = GREEN if ch < -5 else RED if ch > 0 else MUT
    o.append(f'<text x="{W}" y="16" text-anchor="end" style="font-family:{g.MONO};font-size:13px;font-weight:600;fill:{col}">{"&#9660;" if ch < 0 else "&#9650;"} {ch:+.0f}%</text>')
    for v in (0, top // 2, top):
        o.append(f'<line x1="{L}" x2="{W - R_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#1D1D21"/>')
        o.append(f'<text x="{L - 6}" y="{Y(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    lp = g.monotone([(X(i), Y(v)) for i, v in enumerate(ly)])
    o.append(f'<path d="{lp}" fill="none" stroke="#71717A" stroke-width="1.6" stroke-dasharray="4 4"/>')
    tp = g.monotone([(X(i), Y(v)) for i, v in enumerate(ty)])
    area = tp + f" L{X(11):.1f},{Y(0):.1f} L{X(0):.1f},{Y(0):.1f} Z"
    o.append(f'<path d="{area}" fill="{c}" fill-opacity=".08"/>')
    o.append(g.glow(tp, c, 2.2))
    for i, m in enumerate(MS):
        o.append(f'<text x="{X(i):.1f}" y="{H - 4}" class="ax" text-anchor="middle">{m}</text>')
    return "".join(o) + "</svg>"
multiples = "".join(f'<div>{panel(st)}</div>' for st in ORDER)

# ---------- dot plot: every KPI, every site, against target ----------
ROWS = [("Reactive", "reactive", (0, 50), ("line", 20), "target < 20%", "{:.1f}%", "lower"),
        ("PM compliance", "pm", (60, 100), ("line", 90), "target 90%", "{:.1f}%", "higher"),
        ("Statutory", "stat", (60, 100), ("line", 100), "target 100%", "{:.1f}%", "higher"),
        ("MTBF", "mtbf", (0, 4500), None, "trend only", "{:,.0f}h", "higher"),
        ("Cost % of RAV", "costrav", (0, 8), ("band", (2, 3)), "best 2–3%", "{:.1f}%", "lower")]
def dotrow(lbl, key, dom, tgt, tl, fmt, better, W=420, H=58):
    L, R_ = 8, 12
    X = lambda v: L + (v - dom[0]) / (dom[1] - dom[0]) * (W - L - R_)
    y = 30
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    o.append(f'<line x1="{L}" x2="{W - R_}" y1="{y}" y2="{y}" stroke="#2A2A2F" stroke-width="2"/>')
    if tgt and tgt[0] == "line":
        o.append(f'<line x1="{X(tgt[1]):.1f}" x2="{X(tgt[1]):.1f}" y1="{y - 12}" y2="{y + 12}" stroke="{AMBER}" stroke-width="2"/>')
    if tgt and tgt[0] == "band":
        o.append(f'<rect x="{X(tgt[1][0]):.1f}" y="{y - 8}" width="{X(tgt[1][1]) - X(tgt[1][0]):.1f}" height="16" rx="3" fill="{AMBER}" fill-opacity=".25"/>')
    vals = sorted([(F[s][key], s) for s in ORDER])
    lastx, up = -99, True
    for v, s in vals:
        x = X(v)
        up = True if x - lastx > 46 else not up
        lastx = x
        o.append(f'<circle cx="{x:.1f}" cy="{y}" r="11" fill="{SITE[s]}" fill-opacity=".14"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y}" r="6.5" fill="{SITE[s]}"/>')
        ty = y - 15 if up else y + 25
        o.append(f'<text x="{x:.1f}" y="{ty}" text-anchor="middle" style="font-family:{g.MONO};font-size:12px;font-weight:600;fill:{SITE[s]}">{fmt.format(v)}</text>')
    xa = X(F["ALL"][key])
    o.append(f'<path d="M{xa:.1f},{y - 6} L{xa + 6:.1f},{y} L{xa:.1f},{y + 6} L{xa - 6:.1f},{y} Z" fill="{g.CARD}" stroke="#E4E4E7" stroke-width="1.6"/>')
    return "".join(o) + "</svg>"
dots = ""
for lbl, key, dom, tgt, tl, fmt, better in ROWS:
    dots += (f'<div style="margin-top:14px"><div style="display:flex;justify-content:space-between;align-items:baseline">'
             f'<span style="font-size:14px;font-weight:600">{lbl}</span><span class="kv">{tl} &middot; {better} is better</span></div>'
             f'{dotrow(lbl, key, dom, tgt, tl, fmt, better)}</div>')
PILL = {"HOUSTON": ("FIREFIGHTING", RED), "AURORA": ("IMPROVING", SITE["AURORA"]), "BEDFORD": ("BENCHMARK", GREEN)}
legend = "".join(f'<span style="display:flex;align-items:center;gap:7px"><span class="dot" style="background:{SITE[s]};box-shadow:0 0 6px {SITE[s]}"></span>{NAME[s]}'
                 f'<span class="pill" style="margin-left:2px;color:{PILL[s][1]};border-color:{PILL[s][1]}55">{PILL[s][0]}</span></span>' for s in ORDER)
legend += '<span style="display:flex;align-items:center;gap:7px"><svg width="12" height="12"><path d="M6,0.8 L11.2,6 L6,11.2 L0.8,6 Z" fill="none" stroke="#E4E4E7" stroke-width="1.5"/></svg>All</span>'

body = f'''<div class="g2" style="grid-template-columns:1fr 500px">
 <div class="c" style="height:666px">
  <div class="ch"><div><div class="cq">Is reactive work falling?</div><div class="cs">reactive share of work orders &middot; prior 12 months &#9675; &#8594; last 12 months &#9679;</div></div></div>
  <div style="margin-top:14px">{dumbbell}</div>
  <div style="border-top:1px solid #1E1E22;margin-top:6px;padding-top:16px" class="ch"><div><div class="cq" style="font-size:15px">Reactive work orders, month by month</div>
   <div class="cs">last 12 months (solid) vs the same month a year earlier (dashed) &middot; removes the summer peak</div></div></div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:12px">{multiples}</div>
 </div>
 <div class="c" style="height:666px">
  <div class="ch"><div><div class="cq">How does each site compare?</div><div class="cs">Jul 2023 &ndash; Jul 2026 &middot; amber = target</div></div><span class="lk">Site detail &#8594;</span></div>
  <div style="display:flex;flex-wrap:wrap;gap:12px 16px;margin-top:14px;font-size:13px">{legend}</div>
  {dots}
 </div>
</div>'''
out = gp.page("Overview", "Maintenance", "Jul 2023 &ndash; Jul 2026",
              '<b>Houston is running reactive.</b> Aurora cut its reactive work by a fifth in a year.', g.kpis, body, "executive_v7.html")
print(out)
