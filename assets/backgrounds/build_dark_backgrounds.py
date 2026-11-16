#!/usr/bin/env python3
"""
build_dark_backgrounds.py - page backgrounds for the dark redesign (Figma + Power BI).

Separate from build_backgrounds.py on purpose: that script draws the original light, header-band
layout; this one draws the dark sidebar layout from assets/mockups. Same conventions:
    dark/<page>.svg   editable master in 1920 x 1080 canvas units; imports into Figma as named layers
    dark/<page>.png   raster at 2x (3840 x 2160) for the Power BI page background

Geometry is not typed in by hand: each mockup page is opened in headless Edge and the frame
elements (sidebar, top bar rule, KPI cards, chart cards) are measured with getBoundingClientRect,
so the backgrounds always match the mockups they came from.

Baked in: page colour, sidebar panel, logo + product name, sidebar section labels, status legend,
"Synthetic data" note, the top-bar rule, and empty card frames.
Left out (Power BI draws these): page navigator, site slicer, page title/headline, year buttons,
"data as of" stamp, and everything inside the cards.

Run from anywhere:  py -3 assets/backgrounds/build_dark_backgrounds.py
Needs: Microsoft Edge (Windows default install path).
"""
import html, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
MOCKS = os.path.join(REPO, "assets", "mockups")
OUT_DIR = os.path.join(HERE, "dark")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
sys.path.insert(0, os.path.join(REPO, "scripts", "mockups"))
from gear import gear_wrench  # same logo the mockups use

# background name -> mockup it is measured from. Add a page = add an entry.
PAGES = {
    "overview": "executive_v10",
    "pm_compliance": "pm_compliance_v8",
    "reliability": "reliability_v9",
    "planning": "planning_v7",
    "information": "information_v6",
}
W, H, PNG_SCALE = 1920, 1080, 2
PAL = {"page_bg": "#0A0A0B", "sidebar": "#0E0E10", "card": "#131315", "line": "#232327", "logo": "#EDEDEF"}
CARD_RADIUS = 14

MEASURE_JS = r"""
<script>
(function(){
 const R=e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height].map(v=>Math.round(v*10)/10)};
 const q=s=>[...document.querySelectorAll(s)].map(R);
 // baseline = top of the text's content box + the font's ascent (works inside flex rows too)
 const ctx=document.createElement('canvas').getContext('2d');
 function baseline(top,cs){ctx.font=`${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
   return Math.round((top+ctx.measureText('Mg').fontBoundingBoxAscent)*10)/10}
 const texts=[];
 for(const sel of ['aside .brand','aside .lab','aside .legend','aside .foot']){
   for(const host of document.querySelectorAll(sel)){
     const w=document.createTreeWalker(host,NodeFilter.SHOW_TEXT);let n,i=0;
     while((n=w.nextNode())){ if(!n.textContent.trim()) continue;
       if(sel==='aside .foot' && i++>0) break;                     // keep "Synthetic data", drop the data-derived count
       const rg=document.createRange();rg.selectNodeContents(n);const r=rg.getBoundingClientRect();
       const cs=getComputedStyle(n.parentElement);
       texts.push({t:n.textContent.replace(/\s+/g,' '),x:Math.round(r.left*10)/10,y:baseline(r.top,cs),
                   fs:cs.fontSize,fw:cs.fontWeight,color:cs.color,ff:cs.fontFamily});}}}
 const o={aside:q('aside'),top:q('.top'),kpi:q('.kpi'),card:q('.c'),logo:q('aside .brand svg'),
          sep:q('aside .sep'),foot:q('aside .foot'),texts};
 const s=document.createElement('script');s.type='application/json';s.id='MEASURE';s.textContent=JSON.stringify(o);document.body.appendChild(s);
})();
</script>"""


def measure(mock):
    src = os.path.join(MOCKS, mock + ".html")
    page = open(src, encoding="utf-8").read().replace("</body>", MEASURE_JS + "</body>")
    fd, tmp = tempfile.mkstemp(suffix=".html", dir=MOCKS)  # same folder so relative paths still resolve
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(page)
    try:
        r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                            "--window-size=1920,1080", "--dump-dom", "file:///" + tmp.replace("\\", "/")],
                           capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=90)
    finally:
        os.remove(tmp)
    m = re.search(r'<script type="application/json" id="MEASURE">(.*?)</script>', r.stdout, re.S)
    if not m:
        sys.exit(f"measurement failed for {mock}: {r.stderr[-500:]}")
    return json.loads(html.unescape(m.group(1)))


def build_svg(name, M):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'  <rect id="page-bg" x="0" y="0" width="{W}" height="{H}" fill="{PAL["page_bg"]}"/>']
    ax, ay, aw, ah = M["aside"][0]
    p.append(f'  <g id="sidebar">')
    p.append(f'    <rect id="sidebar-panel" x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="{PAL["sidebar"]}"/>')
    p.append(f'    <rect id="sidebar-edge" x="{ax + aw - 1}" y="{ay}" width="1" height="{ah}" fill="{PAL["line"]}"/>')
    lx, ly, lw, lh = M["logo"][0]
    p.append(f'    <g id="logo" transform="translate({lx} {ly}) scale({lw / 26:.4f})">{"".join(gear_wrench(13, 13, 19, PAL["logo"], PAL["sidebar"]))}</g>')
    for i, (x, y, w, h) in enumerate(M["sep"]):
        p.append(f'    <rect id="sidebar-rule-{i + 1}" x="{x}" y="{y}" width="{w}" height="1" fill="{PAL["line"]}"/>')
    for x, y, w, h in M["foot"]:
        p.append(f'    <rect id="footnote-rule" x="{x}" y="{y}" width="{w}" height="1" fill="{PAL["line"]}"/>')
    for i, t in enumerate(M["texts"]):
        fam = html.escape(t["ff"], quote=True)
        p.append(f'    <text id="label-{i + 1}" x="{t["x"]}" y="{t["y"]}" font-family="{fam}" font-size="{t["fs"]}" '
                 f'font-weight="{t["fw"]}" fill="{t["color"]}" xml:space="preserve">{html.escape(t["t"])}</text>')
    p.append('  </g>')
    tx, ty, tw, th = M["top"][0]
    p.append(f'  <rect id="topbar-rule" x="{tx}" y="{ty + th - 1}" width="{tw}" height="1" fill="{PAL["line"]}"/>')
    for kind, rects in (("kpi-card", M["kpi"]), ("chart-card", M["card"])):
        if not rects:
            continue
        p.append(f'  <g id="{kind}s">')
        for i, (x, y, w, h) in enumerate(rects):
            p.append(f'    <rect id="{kind}-{i + 1}" x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="{CARD_RADIUS}" '
                     f'fill="{PAL["card"]}" stroke="{PAL["line"]}" stroke-width="1"/>')
        p.append('  </g>')
    p.append('</svg>')
    return "\n".join(p) + "\n"


def main():
    if not os.path.isfile(EDGE):
        sys.exit(f"Edge not found at {EDGE}")
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, mock in PAGES.items():
        M = measure(mock)
        frames = M["kpi"] + M["card"]
        right = max(x + w for x, y, w, h in frames); bottom = max(y + h for x, y, w, h in frames)
        print(f"{name:14s} from {mock}: {len(M['kpi'])} KPI cards, {len(M['card'])} chart cards, "
              f"right margin {W - right:.0f}px, bottom margin {H - bottom:.0f}px")
        svg_path, png_path = os.path.join(OUT_DIR, f"{name}.svg"), os.path.join(OUT_DIR, f"{name}.png")
        with open(svg_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build_svg(name, M))
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={PNG_SCALE}",
                        f"--window-size={W},{H}", f"--screenshot={png_path}", "file:///" + svg_path.replace("\\", "/")],
                       capture_output=True, stdin=subprocess.DEVNULL, timeout=90)
        from PIL import Image
        with Image.open(png_path) as im:
            ok = im.size == (W * PNG_SCALE, H * PNG_SCALE)
            print(f"   {png_path}  {im.width} x {im.height}  {'OK' if ok else 'WRONG SIZE'}")
            if not ok:
                sys.exit(1)


if __name__ == "__main__":
    main()
