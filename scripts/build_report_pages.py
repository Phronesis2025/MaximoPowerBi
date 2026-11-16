"""Build the five pages of the dark redesign into the PBIP report.

    py -3 scripts/build_report_pages.py

Writes, under MaximoPowerBI.Report/definition, one folder per page (see PAGES):
    pages/overview/        Overview (VP)                      - assets/mockups/executive_v10
    pages/pm_compliance/   PM & Compliance (compliance lead)  - pm_compliance_v8
    pages/reliability/     Reliability (reliability engineer) - reliability_v9
    pages/planning/        Planning (planner)                 - planning_v7
    pages/information/     Information                        - information_v6
and registers the dark theme (assets/theme/maximo_dark.json) and the page backgrounds
(assets/backgrounds/dark/<page>.png) in report.json. The new pages go to the front
of the page order; existing pages are left as they are.

Visual positions come from the same measurement the backgrounds use
(assets/backgrounds/build_dark_backgrounds.py), so visuals sit inside the card frames.
Every card is an HTML Content visual showing one measure from the Report Cards folders of _Measures:
an SVG that draws the card exactly as the mockup does (rounded bars, glow, shaded areas).
The SVGs use the card frame as their viewBox, so they scale with the page. Slicers and the
page buttons stay native Power BI visuals.

Re-running replaces these pages wholesale. Close Power BI Desktop first.
Measures used: the HTML * measures in _Measures.tmdl.
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
DEF = os.path.join(REPO, "MaximoPowerBI.Report", "definition")
RES = os.path.join(REPO, "MaximoPowerBI.Report", "StaticResources", "RegisteredResources")
sys.path.insert(0, os.path.join(REPO, "assets", "backgrounds"))
import build_dark_backgrounds as bg  # noqa: E402

VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
THEME_FILE = "maximo_dark.json"
TXT, MUT, FAINT = "#EDEDEF", "#A1A1AA", "#71717A"
GREEN, AMBER, RED = "#4ADE80", "#FBBF24", "#F87171"
HTML_VISUAL = "htmlContent443BE3AD55E043BF878BED274D3A6865"  # HTML Content (already in publicCustomVisuals)


# ---------------------------------------------------------------- expression helpers
def lit(v):
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, (int, float)):
        s = f"{v}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def col(c):
    return {"solid": {"color": lit(c)}}


def measure(m):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": m}}


def column(t, c):
    return {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def ref(field):
    k = "Measure" if "Measure" in field else "Column"
    return f'{field[k]["Expression"]["SourceRef"]["Entity"]}.{field[k]["Property"]}'


def proj(field, name=None):
    p = {"field": field, "queryRef": ref(field), "nativeQueryRef": field[next(iter(field))]["Property"]}
    if name:
        p["displayName"] = name
    return p


def obj(props, selector=None):
    o = {"properties": {k: (v if isinstance(v, dict) and ("expr" in v or "solid" in v) else lit(v)) for k, v in props.items()}}
    if selector:
        o["selector"] = selector
    return o


# ---------------------------------------------------------------- visual builder
class Page:
    def __init__(self, name, display, background):
        self.name, self.display, self.background = name, display, background
        self.visuals = []

    def add(self, vtype, x, y, w, h, roles=None, objects=None, title=None, subtitle=None, sort=None, extra=None):
        n = f"{self.name}_{len(self.visuals):02d}"
        v = {"visualType": vtype}
        if roles:
            v["query"] = {"queryState": {r: {"projections": ps} for r, ps in roles.items()}}
            if sort:
                v["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort], "isDefaultSort": False}
        if objects:
            v["objects"] = {k: (vals if isinstance(vals, list) else [vals]) for k, vals in objects.items()}
        vco = {"background": [obj({"show": False})], "border": [obj({"show": False})],
               "visualHeader": [obj({"show": False})], "dropShadow": [obj({"show": False})]}
        if title:
            vco["title"] = [obj({"show": True, "text": title, "fontColor": col(TXT), "fontSize": 13, "bold": True})]
            if subtitle:
                vco["subTitle"] = [obj({"show": True, "text": subtitle, "fontColor": col(FAINT), "fontSize": 9})]
        else:
            vco["title"] = [obj({"show": False})]
        v["visualContainerObjects"] = vco
        v["drillFilterOtherVisuals"] = True
        if extra:
            v.update(extra)
        z = 1000 * (len(self.visuals) + 1)
        self.visuals.append({"$schema": VC_SCHEMA, "name": n,
                             "position": {"x": round(x, 1), "y": round(y, 1), "z": z, "height": round(h, 1),
                                          "width": round(w, 1), "tabOrder": z},
                             "visual": v})
        return n

    def html(self, frame, m):
        """HTML Content visual showing one SVG measure, sized to the card frame.
        2px taller than the SVG so a rounding pixel never brings up a scrollbar."""
        x, y, w, h = frame
        n = self.add(HTML_VISUAL, x, y, w, h + 2, roles={"content": [proj(measure(m))]})
        self.visuals[-1]["visual"]["visualContainerObjects"]["visualTooltip"] = [obj({"show": False})]
        return n

    def write(self):
        folder = os.path.join(DEF, "pages", self.name)
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        os.makedirs(os.path.join(folder, "visuals"))
        page = {"$schema": PAGE_SCHEMA, "name": self.name, "displayName": self.display, "displayOption": "FitToPage",
                "height": 1080, "width": 1920,
                "objects": {"background": [{"properties": {
                    "image": {"image": {"name": lit(self.background), "url": {"expr": {"ResourcePackageItem": {
                        "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": self.background}}},
                        "scaling": lit("Fit")}},
                    "transparency": lit(0)}}],
                    "outspace": [{"properties": {"color": col("#0A0A0B")}}]}}
        dump(os.path.join(folder, "page.json"), page)
        for v in self.visuals:
            os.makedirs(os.path.join(folder, "visuals", v["name"]))
            dump(os.path.join(folder, "visuals", v["name"], "visual.json"), v)


def dump(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------- pages
# page id -> (name, mockup, measure key, KPI measures, card measures); measures are "HTML <key> ..."
PAGES = {
    "overview": ("Overview", "executive_v10", "OV",
                 ["KPI Benchmark", "KPI Spend", "KPI Unplanned", "KPI Statutory", "KPI YoY"], ["Money", "Quad", "Trend", "Risk"]),
    "pm_compliance": ("PM & Compliance", "pm_compliance_v8", "PM",
                      ["KPI Overdue", "KPI Due", "KPI PMs", "KPI Statutory", "KPI Compliance"],
                      ["Overdue List", "Pile Up", "Quarterly", "Slipping"]),
    "reliability": ("Reliability", "reliability_v9", "REL",
                    ["KPI Bad Actors", "KPI Reactive Cost", "KPI MTTR", "KPI Downtime", "KPI MTBF"],
                    ["Drift", "Criticality", "What Fails", "Bad Actors"]),
    "planning": ("Planning", "planning_v7", "PLAN",
                 ["KPI Backlog", "KPI Schedule", "KPI Ready", "KPI Waiting", "KPI Aged"], ["Weeks", "Schedule", "Crafts"]),
    "information": ("Information", "information_v6", "INFO", [],
                    ["Status", "Sites", "Window", "KPI Definitions", "Work Types", "Notes"]),
}
# top bar and sidebar measures are named by page, not by key
CHROME = {"overview": "Overview", "pm_compliance": "PM", "reliability": "Reliability", "planning": "Planning", "information": "Information"}
# a slicer goes only on pages where it changes something: Planning is all "as of" or fixed
# rolling windows (no card reads the year), Information is static reference text
SITE_SLICER = {"overview", "pm_compliance", "reliability", "planning"}
YEAR_SLICER = {"overview", "pm_compliance", "reliability"}
NOT_BLANK_YEAR = {"filters": [{
    "name": "year_not_blank", "field": column("DimDate", "YEAR"), "type": "Advanced",
    "filter": {"Version": 2, "From": [{"Name": "d", "Entity": "DimDate", "Type": 0}],
               "Where": [{"Condition": {"Not": {"Expression": {"Comparison": {
                   "ComparisonKind": 0, "Left": {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "YEAR"}},
                   "Right": {"Literal": {"Value": "null"}}}}}}}]},
    "howCreated": "User"}]}


def build(pid):
    name, mock, key, kpis, cards = PAGES[pid]
    M = bg.measure(mock)
    x0 = (M["kpi"] or M["card"])[0][0]  # left edge of the page body
    p = Page(pid, name, pid + "_bg.png")
    p.html((x0 - 36, 0, 1648, 56), f"HTML Top Bar {CHROME[pid]}")
    p.html((16, 102, 239, 200), f"HTML Nav {CHROME[pid]}")
    for i, target in enumerate(PAGES):
        # invisible: "show" without a state selector applies to every state (as Desktop writes it)
        p.add("actionButton", 16, 102 + i * 40, 239, 38, objects={
            "text": obj({"show": False}), "fill": obj({"show": False}),
            "outline": obj({"show": False}), "icon": obj({"show": False}),
        })
        p.visuals[-1]["visual"]["visualContainerObjects"]["visualLink"] = [
            obj({"show": True, "type": "PageNavigation", "navigationSection": target})]
    if pid in SITE_SLICER:
        p.add("slicer", 16, 380, 239, 150, roles={"Values": [proj(column("DimSite", "CITY"), "Site")]}, objects={
            "data": obj({"mode": "Basic"}),
            "selection": obj({"selectAllCheckboxEnabled": True, "singleSelect": False}),
            "header": obj({"show": False}),
            "items": obj({"fontColor": col(TXT), "textSize": 11, "background": col("#0E0E10")}),
        })
    if pid in YEAR_SLICER:
        p.add("slicer", 1430, 12, 290, 32, roles={"Values": [proj(column("DimDate", "YEAR"), "Year")]}, objects={
            "data": obj({"mode": "Basic"}),
            "general": obj({"orientation": 1}),
            "selection": obj({"singleSelect": True}),
            "header": obj({"show": False}),
            "items": obj({"fontColor": col(MUT), "textSize": 9, "background": col("#0A0A0B")}),
        })
        p.visuals[-1]["filterConfig"] = NOT_BLANK_YEAR
    p.html((x0 - 8, 80, 1590, 88), f"HTML {key} Title")
    for frame, m in zip(M["kpi"], kpis):
        p.html(frame, f"HTML {key} {m}")
    for frame, m in zip(M["card"], cards):
        p.html(frame, f"HTML {key} {m}")
    return p


# ---------------------------------------------------------------- report-level registration
def register(pages):
    os.makedirs(RES, exist_ok=True)
    shutil.copyfile(os.path.join(REPO, "assets", "theme", THEME_FILE), os.path.join(RES, THEME_FILE))
    items = [(THEME_FILE, "CustomTheme")]
    for p in pages:
        shutil.copyfile(os.path.join(REPO, "assets", "backgrounds", "dark", p.name + ".png"), os.path.join(RES, p.background))
        items.append((p.background, "Image"))
    rp = os.path.join(DEF, "report.json")
    r = json.load(open(rp, encoding="utf-8"))
    r["themeCollection"]["customTheme"]["name"] = THEME_FILE
    pkg = next(x for x in r["resourcePackages"] if x["name"] == "RegisteredResources")
    # one custom theme only: the previous (light) theme file stays on disk but is no longer registered
    pkg["items"] = [i for i in pkg["items"] if i["type"] != "CustomTheme" or i["name"] == THEME_FILE]
    have = {i["name"] for i in pkg["items"]}
    for name, typ in items:
        if name not in have:
            pkg["items"].append({"name": name, "path": name, "type": typ})
    dump(rp, r)
    pp = os.path.join(DEF, "pages", "pages.json")
    po = json.load(open(pp, encoding="utf-8"))
    ids = [p.name for p in pages]
    po["pageOrder"] = ids + [x for x in po["pageOrder"] if x not in ids]
    po["activePageName"] = ids[0]
    dump(pp, po)


def main():
    pages = [build(pid) for pid in PAGES]
    for p in pages:
        p.write()
        print(f"{p.display:16s} {len(p.visuals):3d} visuals -> pages/{p.name}")
    register(pages)
    print("theme + backgrounds registered; page order:", json.load(open(os.path.join(DEF, "pages", "pages.json")))["pageOrder"])


if __name__ == "__main__":
    main()
