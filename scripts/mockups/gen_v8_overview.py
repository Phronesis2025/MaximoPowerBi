"""Overview v8: big year-on-year change per site on top of the month-by-month panels; glowing status scorecard."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_v7_overview as v7
gp, g = v7.gp, v7.g
V, F = g.V, g.F
SITE, NAME = g.SITE, g.NAME
GREEN, AMBER, RED, MUT, FAINT, TXT, MONO = g.GREEN, g.AMBER, g.RED, g.MUT, g.FAINT, g.TXT, g.MONO
LY, TY, ORDER = v7.LY, v7.TY, v7.ORDER
PILL = {"HOUSTON": ("FIREFIGHTING", RED), "AURORA": ("IMPROVING", SITE["AURORA"]), "BEDFORD": ("BENCHMARK", GREEN)}
MS = ["Jul", "", "", "Oct", "", "", "Jan", "", "", "Apr", "", "Jun"]

def panel(st, W=290, H=392):
    ly, ty = V["monthly"][st]["react"][LY], V["monthly"][st]["react"][TY]
    top = max(ly + ty); step = 100 if top > 100 else 50; top = (int(top / step) + 1) * step
    L, R_, T, B = 30, 16, 10, 22
    X = lambda i: L + i * (W - L - R_) / 11
    Y = lambda v: T + (top - v) / top * (H - T - B)
    c = SITE[st]
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for v in (0, top // 2, top):
        o.append(f'<line x1="{L}" x2="{W - R_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#1D1D21"/>')
        o.append(f'<text x="{L - 6}" y="{Y(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    lp = g.monotone([(X(i), Y(v)) for i, v in enumerate(ly)])
    o.append(f'<path d="{lp}" fill="none" stroke="#71717A" stroke-width="1.6" stroke-dasharray="4 4"/>')
    tp = g.monotone([(X(i), Y(v)) for i, v in enumerate(ty)])
    o.append(f'<path d="{tp} L{X(11):.1f},{Y(0):.1f} L{X(0):.1f},{Y(0):.1f} Z" fill="{c}" fill-opacity=".09"/>')
    o.append(g.glow(tp, c, 2.4))
    o.append(f'<circle cx="{X(11):.1f}" cy="{Y(ty[-1]):.1f}" r="4" fill="{c}"/>')
    for i, m in enumerate(MS):
        if m:
            o.append(f'<text x="{X(i):.1f}" y="{H - 4}" class="ax" text-anchor="middle">{m}</text>')
    return "".join(o) + "</svg>"

cols = ""
for st in ORDER:
    ly, ty = sum(V["monthly"][st]["react"][LY]), sum(V["monthly"][st]["react"][TY])
    ch = (ty / ly - 1) * 100
    col, word, arrow = (GREEN, "falling", "&#9660;") if ch < -5 else (RED, "rising", "&#9650;") if ch > 0 else ("#A1A1AA", "flat", "&#9660;")
    p, pc = PILL[st]
    cols += f'''<div class="sc" style="--c:{SITE[st]}">
  <div style="display:flex;align-items:center;gap:9px"><span class="dot" style="background:{SITE[st]};box-shadow:0 0 8px {SITE[st]}"></span>
   <span style="font-size:16px;font-weight:600">{NAME[st]}</span><span class="pill" style="color:{pc};border-color:{pc}55">{p}</span></div>
  <div class="big2" style="color:{col};text-shadow:0 0 28px {col}66">{"&minus;" if ch < 0 else "+"}{abs(ch):.0f}%</div>
  <div class="cap"><span style="color:{col}">{arrow} {word}</span> &middot; {ly:,} &#8594; {ty:,} reactive WOs</div>
  {panel(st)}
 </div>'''

# ---------- scorecard ----------
def lower(v, t, near): return GREEN if v <= t else AMBER if v <= near else RED
def higher(v, t, near): return GREEN if v >= t else AMBER if v >= near else RED
KP = [("Reactive", "&lt; 20%", "reactive", lambda v: lower(v, 20, 22), "{:.1f}%"),
      ("PM compliance", "90%", "pm", lambda v: higher(v, 90, 80), "{:.1f}%"),
      ("Statutory", "100%", "stat", lambda v: higher(v, 100, 95), "{:.1f}%"),
      ("Cost % RAV", "2&ndash;3%", "costrav", lambda v: lower(v, 3, 4.5), "{:.1f}%"),
      ("MTBF", "trend", "mtbf", lambda v: None, "{:,.0f}h")]
met = {st: sum(1 for _, _, k, f, _ in KP if f(F[st][k]) == GREEN) for st in ORDER}
graded = sum(1 for kp in KP if kp[3](1) is not None)
head = '<div></div>' + "".join(
    f'<div class="sh"><span class="dot" style="background:{SITE[st]};box-shadow:0 0 8px {SITE[st]}"></span>{NAME[st]}'
    f'<div class="met" style="color:{GREEN if met[st] else RED};text-shadow:0 0 18px {(GREEN if met[st] else RED)}55">{met[st]}<small>/{graded}</small></div>'
    f'<div class="kv">targets met</div></div>' for st in ORDER)
grid = head
for lbl, tgt, k, f, fmt in KP:
    grid += f'<div class="kl">{lbl}<div class="kv">{tgt}</div></div>'
    for st in ORDER:
        v = F[st][k]; c = f(v)
        if c is None:
            grid += f'<div class="cell" style="color:#D4D4D8">{fmt.format(v)}</div>'
        else:
            grid += (f'<div class="cell" style="color:{c};background:{c}14;border-color:{c}40;box-shadow:inset 0 0 18px {c}12">'
                     f'<span class="g">{g.GLY[c]}</span>{fmt.format(v)}</div>')

CSS = f"""
.sc{{position:relative;padding:16px 16px 6px;border-radius:12px;background:radial-gradient(120% 60% at 50% 0%, color-mix(in srgb, var(--c) 10%, transparent), transparent 70%);border:1px solid #1E1E22}}
.big2{{font-size:76px;font-weight:600;letter-spacing:-2px;line-height:1;margin-top:16px}}
.cap{{font-family:{MONO};font-size:12.5px;color:{MUT};margin:8px 0 14px}}
.scg{{display:grid;grid-template-columns:118px repeat(3,1fr);gap:8px;margin-top:16px}}
.sh{{text-align:center;font-size:14px;font-weight:600;display:flex;flex-direction:column;align-items:center;gap:2px}}
.sh .dot{{margin-bottom:4px}}
.met{{font-size:34px;font-weight:600;line-height:1.1;margin-top:6px}}
.met small{{font-size:16px;color:{FAINT}}}
.kl{{font-size:14px;font-weight:600;display:flex;flex-direction:column;justify-content:center}}
.cell{{height:86px;border:1px solid #232327;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:21px;font-weight:600;font-variant-numeric:tabular-nums}}
.cell .g{{font-size:10px;margin-right:6px}}
"""
gp.EXTRA += CSS
body = f'''<div class="g2" style="grid-template-columns:1fr 520px">
 <div class="c" style="height:666px">
  <div class="ch"><div><div class="cq">Is reactive work falling?</div>
   <div class="cs">reactive work orders, last 12 complete months vs the 12 before &middot; solid = this year, dashed = same month last year</div></div></div>
  <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:16px">{cols}</div>
 </div>
 <div class="c" style="height:666px">
  <div class="ch"><div><div class="cq">How does each site compare?</div><div class="cs">Jul 2023 &ndash; Jul 2026 &middot; graded against target</div></div><span class="lk">Site detail &#8594;</span></div>
  <div class="scg">{grid}</div>
 </div>
</div>'''
out = gp.page("Overview", "Maintenance", "Jul 2023 &ndash; Jul 2026",
              '<b>Houston is running reactive.</b> Aurora cut its reactive work by a fifth in a year.', g.kpis, body, "executive_v8.html")
print(out, met)
