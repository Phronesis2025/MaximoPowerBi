#!/usr/bin/env python3
"""
organise_measures_by_page.py - file every measure into a display folder named
for the report page it serves, and stamp each measure's description with the
pages that use it.

Structure, numbered so Power BI's alphabetical folder sort matches page order:

    00 Shared\\Headline KPIs      metrics that appear on more than one page
    00 Shared\\Trend              rolling-window variants
    01 Executive Overview         the HTML card measure
    01 Executive Overview\\...    card status colours and variance sentences
    02 PM & Compliance
    03 Reliability
    04 Planning                   plus its own status colours and variance text
    05 Asset Health
    06 Information

A measure can only live in one folder, so anything used on several pages goes to
00 Shared and carries a "Pages:" line naming every page it appears on. The folder
says where it primarily belongs; the description says everywhere it is used.

    cd C:\\dev\\MaximoPowerBi
    py -3 scripts\\organise_measures_by_page.py

Refuses to run while PBIDesktop.exe is alive - Desktop rewrites this folder on
save and would discard changes made underneath it.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMDL = os.path.join(ROOT, "MaximoPowerBI.SemanticModel", "definition", "tables", "_Measures.tmdl")

EXEC, PMC, REL, PLAN, ASSET, INFO = (
    "Executive Overview", "PM & Compliance", "Reliability", "Planning",
    "Asset Health", "Information")

SHARED_K = "00 Shared\\Headline KPIs"
SHARED_T = "00 Shared\\Trend"
EXEC_F = "01 Executive Overview"
EXEC_C = "01 Executive Overview\\Card status colours"
EXEC_V = "01 Executive Overview\\Card variance text"
PMC_F = "02 PM & Compliance"
REL_F = "03 Reliability"
PLAN_F = "04 Planning"
PLAN_C = "04 Planning\\Card status colours"
PLAN_V = "04 Planning\\Card variance text"
ASSET_F = "05 Asset Health"
INFO_F = "06 Information"

# measure -> (display folder, [pages it appears on])
MAP = {
    # ---- shared headline metrics -------------------------------------------
    "Work Orders":                        (SHARED_K, [EXEC, PMC, PLAN]),
    "Asset Availability %":               (SHARED_K, [EXEC, REL]),
    "PM Compliance %":                    (SHARED_K, [EXEC, PMC]),
    "Statutory Compliance %":             (SHARED_K, [EXEC, PMC]),
    "Schedule Compliance %":              (SHARED_K, [EXEC, PMC, PLAN]),
    "Reactive Maintenance %":             (SHARED_K, [EXEC, PMC]),
    "MTBF (Hours)":                       (SHARED_K, [EXEC, REL]),
    "MTTR (Hours)":                       (SHARED_K, [EXEC, REL]),
    "Total Maintenance Cost":             (SHARED_K, [EXEC, ASSET]),
    "Maintenance Cost % of RAV":          (SHARED_K, [EXEC, ASSET]),
    "Data As Of Date":                    (SHARED_K, [EXEC, PMC, REL, PLAN, ASSET]),
    "Analysis Days":                      (SHARED_K, [REL, ASSET]),
    "Reactive Maintenance % (12M Rolling)": (SHARED_T, [EXEC, REL]),
    "PM Compliance % (12M Rolling)":      (SHARED_T, [EXEC, PMC]),
    # ---- page 1 -------------------------------------------------------------
    "KPI Card HTML":                      (EXEC_F, [EXEC]),
    "Availability Status Colour":         (EXEC_C, [EXEC]),
    "PM Compliance Status Colour":        (EXEC_C, [EXEC]),
    "Statutory Status Colour":            (EXEC_C, [EXEC]),
    "Schedule Status Colour":             (EXEC_C, [EXEC]),
    "Reactive Status Colour":             (EXEC_C, [EXEC]),
    "MTBF Status Colour":                 (EXEC_C, [EXEC]),
    "MTTR Status Colour":                 (EXEC_C, [EXEC]),
    "Cost RAV Status Colour":             (EXEC_C, [EXEC]),
    "Availability vs Target":             (EXEC_V, [EXEC]),
    "PM Compliance vs Target":            (EXEC_V, [EXEC]),
    "Statutory vs Target":                (EXEC_V, [EXEC]),
    "Schedule vs Target":                 (EXEC_V, [EXEC]),
    "Reactive vs Target":                 (EXEC_V, [EXEC]),
    "Cost RAV vs Target":                 (EXEC_V, [EXEC]),
    # ---- page 2 -------------------------------------------------------------
    "PM Compliance % (by Due Date)":      (PMC_F, [PMC]),
    "PMs Completed":                      (PMC_F, [PMC]),
    "PM Due Next 14 Days":                (PMC_F, [PMC, PLAN]),
    "Statutory Inspections Completed":    (PMC_F, [PMC]),
    "Statutory Inspections On Time":      (PMC_F, [PMC]),
    "Statutory Inspections Late":         (PMC_F, [EXEC, PMC]),
    # ---- page 3 -------------------------------------------------------------
    "Failure Events":                     (REL_F, [REL, ASSET]),
    "Downtime Hours":                     (REL_F, [EXEC, REL, ASSET]),
    "Operating Asset Count":              (REL_F, [REL, ASSET]),
    "Scheduled Asset Hours":              (REL_F, [REL]),
    # ---- page 4 -------------------------------------------------------------
    "Backlog Hours":                      (PLAN_F, [PLAN]),
    "Backlog Weeks":                      (PLAN_F, [EXEC, PLAN]),
    "Weekly Craft Capacity (Hours)":      (PLAN_F, [PLAN]),
    "Backlog Hours per Technician":       (PLAN_F, [PLAN]),
    "Open Work Orders":                   (PLAN_F, [PLAN]),
    "Overdue Work Orders":                (PLAN_F, [PLAN]),
    "Overdue %":                          (PLAN_F, [PLAN]),
    "Avg Days Overdue":                   (PLAN_F, [PLAN]),
    "Oldest Open Work Order (Days)":      (PLAN_F, [PLAN]),
    "Open Emergency Work Orders":         (PLAN_F, [PLAN]),
    "Overdue Emergency Work Orders":      (PLAN_F, [PLAN]),
    "Aged Over 90 Days":                  (PLAN_F, [PLAN, ASSET]),
    "Avg Age of Open Work (Days)":        (PLAN_F, [PLAN]),
    "Backlog Hours Overdue":              (PLAN_F, [PLAN]),
    "Overdue Share of Backlog":           (PLAN_F, [PLAN]),
    "Work Orders Completed":              (PLAN_F, [PLAN]),
    "Work Orders Reported":               (PLAN_F, [PLAN]),
    "Net Backlog Change":                 (PLAN_F, [PLAN]),
    "Mean Days to Complete":              (PLAN_F, [PLAN]),
    "Actual Labour Hours":                (PLAN_F, [PLAN]),
    "Reactive Labour Hours":              (PLAN_F, [PLAN]),
    "Backlog Status Colour":              (PLAN_C, [PLAN]),
    "Backlog Age Status Colour":          (PLAN_C, [PLAN]),
    "Overdue Status Colour":              (PLAN_C, [PLAN]),
    "Backlog vs Target":                  (PLAN_V, [PLAN]),
    # ---- page 6 -------------------------------------------------------------
    "Cost Reconciliation Check":          (INFO_F, [INFO]),
}


def desktop_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq PBIDesktop.exe"],
                             capture_output=True, text=True).stdout
        return "PBIDesktop.exe" in out
    except Exception:
        return False


def main():
    if desktop_running():
        sys.exit("PBIDesktop.exe is running. Close Power BI Desktop first.")

    t = open(TMDL, encoding="utf-8", newline="").read()
    names = re.findall(r"(?m)^\tmeasure '([^']+)'", t)
    missing = [n for n in names if n not in MAP]
    extra = [n for n in MAP if n not in names]
    if missing or extra:
        if missing:
            print("NOT MAPPED (would be left unfiled):")
            for n in missing:
                print("   ", n)
        if extra:
            print("MAPPED BUT NOT IN THE MODEL:")
            for n in extra:
                print("   ", n)
        sys.exit("refusing to write - fix the map first")

    lines = t.split("\r\n")
    out, i, changed = [], 0, 0
    while i < len(lines):
        m = re.match(r"^\tmeasure '([^']+)'", lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue

        name = m.group(1)
        folder, pages = MAP[name]

        # strip any existing Pages: line from the description above this measure
        while out and out[-1].startswith("\t/// Pages:"):
            out.pop()
        # the description ends with a blank-ish separator; insert Pages last
        desc_tail = []
        while out and out[-1].startswith("\t///"):
            desc_tail.insert(0, out.pop())
        if desc_tail:
            desc_tail.append("\t///")
        desc_tail.append("\t/// Pages: " + ", ".join(pages))
        out.extend(desc_tail)

        # copy the measure block, replacing/inserting displayFolder before lineageTag
        out.append(lines[i]); i += 1
        while i < len(lines) and not re.match(r"^\t\tlineageTag:", lines[i]):
            if not re.match(r"^\t\tdisplayFolder:", lines[i]):
                out.append(lines[i])
            i += 1
        out.append(f"\t\tdisplayFolder: {folder}")
        changed += 1

    t2 = "\r\n".join(out)
    assert len(re.findall(r"(?m)^\tmeasure '", t2)) == len(names)
    assert t2.count("displayFolder:") == len(names)
    open(TMDL, "w", encoding="utf-8", newline="").write(t2)

    folders = {}
    for n in names:
        folders.setdefault(MAP[n][0], []).append(n)
    print(f"filed {changed} measures into {len(folders)} folders\n")
    for f in sorted(folders):
        print(f"  {f}   ({len(folders[f])})")
        for n in sorted(folders[f]):
            print(f"      {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
