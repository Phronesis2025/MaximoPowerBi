"""Overview v9: A1 change bars + month-by-month panels (left), B3 status-coloured bars per KPI (right)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_v8_overview as v8
v7, gp, g = v8.v7, v8.gp, v8.g
V, F = g.V, g.F
SITE, NAME = g.SITE, g.NAME
GREEN, AMBER, RED, MUT, FAINT, TXT, MONO = g.GREEN, g.AMBER, g.RED, g.MUT, g.FAINT, g.TXT, g.MONO
LY, TY, ORDER = v7.LY, v7.TY, v7.ORDER
ly = {s: sum(V["monthly"][s]["react"][LY]) for s in ORDER}
ty = {s: sum(V["monthly"][s]["react"][TY]) for s in ORDER}
def t(x, y, s, size=13, fill=MUT, w=400, anchor="start", font="mono"):
    fam = MONO if font == "mono" else "Segoe UI"
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font-family:{fam};font-size:{size}px;font-weight:{w};fill:{fill}">{s}</text>'

# ---------- A1: change bars ----------
def change_bars(W=990, H=214):
    cx = W / 2; maxp = 25; sc = (W / 2 - 150) / maxp
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    o.append(t(cx - 12, 14, "&#9664; fewer reactive WOs = better", 12, GREEN, 400, "end"))
    o.append(t(cx + 12, 14, "more = worse &#9654;", 12, RED))
    for p in (-20, -10, 10, 20):
        x = cx + p * sc
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="26" y2="{H - 18}" stroke="#1D1D21"/>')
        o.append(t(x, H - 2, f"{p:+d}%", 11, FAINT, 400, "middle"))
    o.append(f'<line x1="{cx}" x2="{cx}" y1="24" y2="{H - 16}" stroke="#52525B" stroke-width="1.5"/>')
    for k, st in enumerate(ORDER):
        y = 40 + k * 54
        ch = (ty[st] / ly[st] - 1) * 100
        col = GREEN if ch < -5 else RED if ch > 0 else "#A1A1AA"
        w = max(abs(ch) * sc, 4)
        neg = ch < 0
        x0 = cx - w if neg else cx
        o.append(f'<rect x="{x0:.1f}" y="{y}" width="{w:.1f}" height="36" rx="7" fill="{col}" style="filter:drop-shadow(0 0 12px {col}88)"/>')
        vx = x0 - 12 if neg else x0 + w + 12
        o.append(t(vx, y + 29, f'{"&minus;" if neg else "+"}{abs(ch):.0f}%', 30, col, 600, "end" if neg else "start", "sans"))
        nx = cx + 14 if neg else cx - 14
        a = "start" if neg else "end"
        o.append(t(nx, y + 16, NAME[st], 16, SITE[st], 600, a, "sans"))
        o.append(t(nx, y + 32, f"{ly[st]:,} &#8594; {ty[st]:,} WOs", 11.5, MUT, 400, a))
    return "".join(o) + "</svg>"

# ---------- month-by-month panels (kept from v7/v8) ----------
panels = "".join(
    f'<div><div style="display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;margin-bottom:4px">'
    f'<span class="dot" style="background:{SITE[st]};box-shadow:0 0 6px {SITE[st]}"></span>{NAME[st]}</div>{v8.panel(st, 318, 268)}</div>'
    for st in ORDER)

# ---------- B3: bars per KPI, status colours ----------
def lower(v, tg, near): return GREEN if v <= tg else AMBER if v <= near else RED
def higher(v, tg, near): return GREEN if v >= tg else AMBER if v >= near else RED
KP = [("Reactive %", "reactive", 50, 20, lambda v: lower(v, 20, 22), "lower is better &middot; target &lt; 20"),
      ("PM compliance %", "pm", 100, 90, lambda v: higher(v, 90, 80), "higher is better &middot; target 90"),
      ("Statutory %", "stat", 100, 100, lambda v: higher(v, 100, 95), "higher is better &middot; target 100"),
      ("Cost % of RAV", "costrav", 8, 3, lambda v: lower(v, 3, 4.5), "lower is better &middot; best 2&ndash;3")]
BO = ["BEDFORD", "AURORA", "HOUSTON"]
def kpi_bars(W=460, H=596):
    o = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    pw, ph = 214, 284
    for i, (lbl, k, mx, tg, f, sub) in enumerate(KP):
        ox, oy = (i % 2) * (pw + 32), (i // 2) * (ph + 22)
        o.append(t(ox, oy + 16, lbl, 15, TXT, 600, "start", "sans"))
        o.append(t(ox, oy + 33, sub, 10.5, FAINT))
        T, B = oy + 74, oy + ph - 24
        Y = lambda v: B - v / mx * (B - T)
        bw = 46; gap = (pw - 3 * bw) / 4
        if k == "costrav":
            o.append(f'<rect x="{ox}" y="{Y(3):.1f}" width="{pw}" height="{Y(2) - Y(3):.1f}" fill="{AMBER}" fill-opacity=".14"/>')
        for j, st in enumerate(BO):
            v = F[st][k]; c = f(v); x = ox + gap + j * (bw + gap)
            o.append(f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw}" height="{B - Y(v):.1f}" rx="5" fill="{c}" fill-opacity=".88" style="filter:drop-shadow(0 0 10px {c}55)"/>')
            ly_ = Y(v) - 9
            if abs(ly_ - Y(tg)) < 13 or (Y(v) > Y(tg) and ly_ - 12 < Y(tg)):
                ly_ = min(ly_, Y(tg) - 9)
            o.append(t(x + bw / 2, ly_, f"{g.GLY[c]} {v:.1f}", 13, c, 600, "middle"))
            o.append(t(x + bw / 2, B + 17, NAME[st], 12, SITE[st], 400, "middle", "sans"))
        o.append(f'<line x1="{ox - 4}" x2="{ox + pw + 4}" y1="{Y(tg):.1f}" y2="{Y(tg):.1f}" stroke="#F4F4F5" stroke-width="2" stroke-dasharray="6 4"/>')
        o.append(f'<line x1="{ox}" x2="{ox + pw}" y1="{B}" y2="{B}" stroke="#3F3F46"/>')
    return "".join(o) + "</svg>"

body = f'''<div class="g2" style="grid-template-columns:1fr 520px">
 <div class="c" style="height:666px">
  <div class="ch"><div><div class="cq">Is reactive work falling?</div><div class="cs">reactive work orders, last 12 complete months vs the 12 before</div></div></div>
  <div style="margin-top:14px">{change_bars()}</div>
  <div style="border-top:1px solid #1E1E22;margin-top:12px;padding-top:14px">
   <div class="cs" style="margin:0 0 10px">month by month &middot; solid = this year &middot; dashed = same month last year</div>
   <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px">{panels}</div></div>
 </div>
 <div class="c" style="height:666px">
  <div class="ch"><div><div class="cq">How does each site compare?</div><div class="cs">Jul 2023 &ndash; Jul 2026 &middot; dashed line = target &middot; colour = status</div></div><span class="lk">Site detail &#8594;</span></div>
  <div style="margin-top:16px">{kpi_bars()}</div>
 </div>
</div>'''
out = gp.page("Overview", "Maintenance", "Jul 2023 &ndash; Jul 2026",
              '<b>Houston is running reactive.</b> Aurora cut its reactive work by a fifth in a year.', g.kpis, body, "executive_v9.html")
print(out)
