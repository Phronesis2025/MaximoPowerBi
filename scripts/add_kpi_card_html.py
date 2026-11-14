#!/usr/bin/env python3
"""
add_kpi_card_html.py - (re)install the 'KPI Card HTML' measure in _Measures.tmdl.

Kept as a script rather than a one-off because Power BI Desktop rewrites the
TMDL folder on save, and a measure added while Desktop is open is lost the next
time it saves. If the measure disappears, close Desktop and run this again.

    cd C:\\dev\\MaximoPowerBi
    py -3 scripts\\add_kpi_card_html.py

Refuses to run while PBIDesktop.exe is alive.
"""
import math
import os
import re
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMDL = os.path.join(ROOT, "MaximoPowerBI.SemanticModel", "definition", "tables", "_Measures.tmdl")


def desktop_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq PBIDesktop.exe"],
                             capture_output=True, text=True).stdout
        return "PBIDesktop.exe" in out
    except Exception:
        return False


def gear_svg():
    """gear-and-wrench status mark, 30px, colour injected as 'CLR'."""
    R = 15.0
    cx = cy = 15.0
    r_tip, r_body, r_hole = R, 0.78 * R, 0.40 * R
    teeth = []
    for i in range(8):
        a, half = math.radians(i * 45), math.radians(17)
        pts = []
        for rr, aa in ((r_body * .96, a - half), (r_tip, a - half * .68),
                       (r_tip, a + half * .68), (r_body * .96, a + half)):
            pts.append(f"{cx + rr * math.cos(aa):.1f},{cy + rr * math.sin(aa):.1f}")
        teeth.append(f"<polygon points='{' '.join(pts)}'/>")
    sw, rmid = r_body - r_hole, (r_body + r_hole) / 2
    ring = f"<circle cx='15' cy='15' r='{rmid:.1f}' fill='none' stroke='CLR' stroke-width='{sw:.1f}'/>"
    ux = uy = math.cos(math.radians(45))
    px, py = -uy, ux
    L = 1.15 * R
    ax, ay, bx, by = cx - ux * L, cy - uy * L, cx + ux * L, cy + uy * L
    hw, rj = .15 * R, .30 * R

    def bar(h, r):
        c = [f"{ax + px * h:.1f},{ay + py * h:.1f}", f"{bx + px * h:.1f},{by + py * h:.1f}",
             f"{bx - px * h:.1f},{by - py * h:.1f}", f"{ax - px * h:.1f},{ay - py * h:.1f}"]
        return (f"<polygon points='{' '.join(c)}'/>"
                f"<circle cx='{ax:.1f}' cy='{ay:.1f}' r='{r:.1f}'/>"
                f"<circle cx='{bx:.1f}' cy='{by:.1f}' r='{r:.1f}'/>")

    def notch(ex, ey, sx, sy):
        v1 = (ex + sx * rj * 1.7 + px * rj * .52, ey + sy * rj * 1.7 + py * rj * .52)
        v2 = (ex + sx * rj * 1.7 - px * rj * .52, ey + sy * rj * 1.7 - py * rj * .52)
        v3 = (ex + sx * rj * .02, ey + sy * rj * .02)
        return f"<polygon points='{' '.join(f'{p[0]:.1f},{p[1]:.1f}' for p in (v1, v2, v3))}'/>"

    return ("<svg viewBox='0 0 30 30' width='30' height='30' style='flex:0 0 auto'>"
            "<g fill='CLR'>" + "".join(teeth) + "</g>" + ring +
            "<g fill='#FFFFFF'>" + bar(hw + 1.7, rj + 1.7) + "</g>"
            "<g fill='CLR'>" + bar(hw, rj) + "</g>"
            "<g fill='#FFFFFF'>" + notch(ax, ay, -ux, -uy) + notch(bx, by, ux, uy) + "</g></svg>")


DESC = [
    "Renders one Executive Overview KPI card as HTML for the HTML Content visual.",
    "",
    "Place eight HTML Content visuals on the page, each filtered to a single",
    "KPICards[CardKey], and put this measure in each. One measure, one disconnected",
    "table, eight visuals - rather than eight near-identical measures.",
    "",
    "The card carries the gear status mark, the value, the target label, a bullet",
    "bar with a target tick, the variance sentence and a 12-month sparkline. Colour",
    "comes from the per-metric Status Colour measures, so a card can never disagree",
    "with the colour policy used everywhere else.",
    "",
    "The sparkline is an inline SVG polyline built with CONCATENATEX over the last",
    "twelve months - no image, no external dependency, no second visual.",
    "",
    "HTML Content is a certified custom visual and must be installed from AppSource",
    "before this renders. Attribute quoting is single-quote inside the SVG and",
    "doubled-double-quote in the DAX string literals; do not normalise them.",
]


def build_dax():
    g = [p.replace('"', "'") for p in gear_svg().split("CLR")]
    assert len(g) == 4, "gear placeholder count changed"
    return f'''
VAR _key = SELECTEDVALUE ( KPICards[CardKey] )
VAR _label = SELECTEDVALUE ( KPICards[CardLabel] )
VAR _targetLab = SELECTEDVALUE ( KPICards[TargetLabel] )
VAR _target = SELECTEDVALUE ( KPICards[Target] )
VAR _max = SELECTEDVALUE ( KPICards[ScaleMax] )
VAR _actual =
    SWITCH ( _key,
        "AVAIL", [Asset Availability %],
        "PM", [PM Compliance %],
        "STAT", [Statutory Compliance %],
        "SCHED", [Schedule Compliance %],
        "REACTIVE", [Reactive Maintenance %],
        "MTBF", [MTBF (Hours)],
        "MTTR", [MTTR (Hours)],
        "COSTRAV", [Maintenance Cost % of RAV]
    )
VAR _valueText =
    SWITCH ( _key,
        "MTBF", FORMAT ( _actual, "#,0" ),
        "MTTR", FORMAT ( _actual, "#,0.00" ),
        FORMAT ( _actual, "0.0%" )
    )
VAR _colour =
    SWITCH ( _key,
        "AVAIL", [Availability Status Colour],
        "PM", [PM Compliance Status Colour],
        "STAT", [Statutory Status Colour],
        "SCHED", [Schedule Status Colour],
        "REACTIVE", [Reactive Status Colour],
        "MTBF", [MTBF Status Colour],
        "MTTR", [MTTR Status Colour],
        "COSTRAV", [Cost RAV Status Colour]
    )
VAR _delta =
    SWITCH ( _key,
        "AVAIL", [Availability vs Target],
        "PM", [PM Compliance vs Target],
        "STAT", [Statutory vs Target],
        "SCHED", [Schedule vs Target],
        "REACTIVE", [Reactive vs Target],
        "MTBF", FORMAT ( [MTBF (Hours)] - _target, "+#,0;-#,0" ) & " h vs last year",
        "MTTR", FORMAT ( [MTTR (Hours)] - _target, "+#,0.00;-#,0.00" ) & " h vs last year",
        "COSTRAV", [Cost RAV vs Target]
    )
VAR _pct = MIN ( DIVIDE ( _actual, _max ), 1 ) * 100
VAR _tpct = MIN ( DIVIDE ( _target, _max ), 1 ) * 100
VAR _months =
    TOPN ( 12, ALLSELECTED ( DimDate[MonthSort] ), DimDate[MonthSort], DESC )
VAR _series =
    ADDCOLUMNS (
        _months,
        "@v",
            CALCULATE (
                SWITCH ( _key,
                    "AVAIL", [Asset Availability %],
                    "PM", [PM Compliance %],
                    "STAT", [Statutory Compliance %],
                    "SCHED", [Schedule Compliance %],
                    "REACTIVE", [Reactive Maintenance %],
                    "MTBF", [MTBF (Hours)],
                    "MTTR", [MTTR (Hours)],
                    "COSTRAV", [Maintenance Cost % of RAV]
                )
            )
    )
VAR _clean = FILTER ( _series, NOT ISBLANK ( [@v] ) )
VAR _lo = MINX ( _clean, [@v] )
VAR _hi = MAXX ( _clean, [@v] )
VAR _n = COUNTROWS ( _clean )
VAR _ranked =
    ADDCOLUMNS ( _clean, "@i", RANKX ( _clean, [MonthSort], , ASC, DENSE ) )
VAR _points =
    CONCATENATEX (
        _ranked,
        FORMAT ( DIVIDE ( [@i] - 1, MAX ( _n - 1, 1 ) ) * 120, "0.0" ) & ","
            & FORMAT ( 26 - DIVIDE ( [@v] - _lo, MAX ( _hi - _lo, 0.0000001 ) ) * 24, "0.0" ),
        " ",
        [@i], ASC
    )
VAR _spark =
    IF ( _n < 2, "",
        "<svg viewBox='0 0 120 30' width='120' height='30' style='flex:0 0 auto'>"
            & "<polyline points='" & _points & "' fill='none' stroke='" & _colour
            & "' stroke-width='2.2' stroke-linejoin='round' stroke-linecap='round'/></svg>" )
VAR _gear =
    "{g[0]}" & _colour & "{g[1]}" & _colour & "{g[2]}" & _colour & "{g[3]}"
RETURN
    "<div style=""box-sizing:border-box;width:100%;height:100%;background:#FFFFFF;"
        & "border:1px solid #E3E6EA;border-radius:12px;padding:18px 22px;"
        & "font-family:Segoe UI,Arial,sans-serif;display:flex;flex-direction:column;"
        & "justify-content:space-between"">"
        & "<div style=""display:flex;align-items:center;gap:10px"">"
            & _gear
            & "<span style=""font-size:18px;color:#5B6B80"">" & _label & "</span></div>"
        & "<div style=""display:flex;align-items:baseline;justify-content:space-between"">"
            & "<span style=""font-size:44px;font-weight:600;color:#16283F;line-height:1"">"
            & _valueText & "</span>"
            & "<span style=""font-size:16px;color:#5B6B80"">" & _targetLab & "</span></div>"
        & "<div style=""position:relative;height:14px;background:#E9EDF3;border-radius:4px"">"
            & "<div style=""position:absolute;left:0;top:0;height:14px;border-radius:4px;"
            & "width:" & FORMAT ( _pct, "0.0" ) & "%;background:" & _colour & """></div>"
            & "<div style=""position:absolute;top:-7px;height:28px;width:3px;background:#16283F;"
            & "left:calc(" & FORMAT ( _tpct, "0.0" ) & "% - 1px)""></div></div>"
        & "<div style=""display:flex;align-items:center;justify-content:space-between"">"
            & "<span style=""font-size:16px;font-weight:600;color:" & _colour & """>"
            & _delta & "</span>" & _spark & "</div>"
    & "</div>"
'''


def main():
    if desktop_running():
        sys.exit("PBIDesktop.exe is running. Close Power BI Desktop first - it "
                 "rewrites this folder on save and would discard the measure.")
    t = open(TMDL, encoding="utf-8", newline="").read()
    if "measure 'KPI Card HTML'" in t:
        print("already present - nothing to do")
        return 0
    b = [f"\t/// {d}".rstrip() for d in DESC]
    b.append("\tmeasure 'KPI Card HTML' =")
    b += [("\t\t\t" + ln).rstrip() if ln.strip() else "" for ln in build_dax().strip("\n").split("\n")]
    b.append(f"\t\tlineageTag: {uuid.uuid4()}")
    b.append("")
    anchor = "\tpartition _Measures = m\r\n"
    if t.count(anchor) != 1:
        sys.exit("could not find the _Measures partition anchor")
    t = t.replace(anchor, "\r\n".join(b) + "\r\n" + anchor)
    n = len(re.findall(r"(?m)^\tmeasure '", t))
    body = build_dax()
    if any(ln.count('"') % 2 for ln in body.split("\n")):
        sys.exit("unbalanced quote in generated DAX - refusing to write")
    if body.count("(") != body.count(")"):
        sys.exit("unbalanced parentheses in generated DAX - refusing to write")
    open(TMDL, "w", encoding="utf-8", newline="").write(t)
    print(f"KPI Card HTML installed; _Measures now declares {n} measures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
