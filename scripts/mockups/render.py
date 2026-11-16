"""Rebuild the report mockups (dark design) into assets/mockups/.

    py -3 scripts/mockups/render.py            # HTML + PNG from the cached *_numbers.json
    py -3 scripts/mockups/render.py --numbers  # recompute every figure from data/*.csv first

Figures:  exec_numbers.py, v6_numbers.py, pages_numbers.py, roles_numbers.py, extra_numbers.py -> *.json here
Pages:    gen_v10_overview.py (imports v9 -> v8 -> v7 -> gen_pages -> gen_v6) and gen_rel_v9.py (imports gen_roles)
Screens:  headless Microsoft Edge, 1920 x 1080 (the Power BI canvas size)
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "mockups"))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NUMBERS = ["exec_numbers.py", "v6_numbers.py", "pages_numbers.py", "roles_numbers.py", "extra_numbers.py"]
GENERATORS = ["gen_v10_overview.py", "gen_rel_v9.py"]
CURRENT = ["executive_v10", "pm_compliance_v8", "reliability_v9", "planning_v7", "information_v6"]

def run(script):
    print("->", script, flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-4000:]); sys.exit(f"{script} failed ({r.returncode})")

if "--numbers" in sys.argv:
    for s in NUMBERS: run(s)
for s in GENERATORS: run(s)
if not os.path.isfile(EDGE):
    sys.exit(f"Edge not found at {EDGE}; HTML written to {OUT}, PNGs skipped")
for name in CURRENT:
    html, png = os.path.join(OUT, name + ".html"), os.path.join(OUT, name + ".png")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1920,1080", f"--screenshot={png}", "file:///" + html.replace("\\", "/")],
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
    print("   ", png, "OK" if os.path.isfile(png) else "MISSING")
