#!/usr/bin/env python3
"""
tidy_model_layout.py
====================

Rewrites a Power BI PBIP diagramLayout.json into a clean, banded star-schema
layout, and optionally adds focused per-subject-area diagrams.

Power BI Desktop's model view has no auto-arrange. But in PBIP format the
layout is just JSON on disk, so it can be generated deterministically instead
of dragged by hand.

USAGE
    1. CLOSE Power BI Desktop. It caches this file and will overwrite you.
    2. python3 tidy_model_layout.py "C:/path/MaximoPowerBI.SemanticModel"
    3. Reopen the .pbip.

    Add --diagrams to also create the four focused diagrams.
    Add --dry-run to see what it would do without writing.

SAFETY
    Writes diagramLayout.json.bak before touching anything. If the file's schema
    is not what this script expects, it reports and exits WITHOUT writing,
    rather than guessing and corrupting your layout.
"""

import argparse
import json
import os
import shutil
import sys

# ---------------------------------------------------------------------------
# LAYOUT SPEC - edit this, not the coordinates
# ---------------------------------------------------------------------------
# Three bands, top to bottom:
#   band 0  conformed dimensions that feed several facts
#   band 1  the fact tables
#   band 2  dimensions that feed exactly one fact
# Within a band, tables are placed left to right in the order listed.
# Facts are positioned so their private dimensions sit directly beneath them,
# which is what keeps the relationship lines short and mostly vertical.

# band 0: conformed dimensions, shared across several facts
CONFORMED = ["DimDate", "DimAsset", "DimSite"]

# band 1: the facts, left to right
FACTS = ["FactLabour", "FactMaterial", "FactWorkOrder",
         "FactDowntime", "FactFailure", "FactMeterReading"]

# band 2+: private dimensions, anchored to the x of the fact they serve and
# stacked vertically beneath it. Stacking rather than spreading is what keeps
# every relationship line vertical and non-crossing.
PRIVATE = {
    "FactLabour":    ["DimCraft", "DimLabor"],
    "FactMaterial":  ["DimItem"],
    "FactWorkOrder": ["DimLocation", "DimWorkType", "DimStatus"],
    "FactFailure":   ["DimFailureCode"],
}

# Tables deliberately unrelated to everything. Parked well clear of the star so
# nobody mistakes a missing relationship for a mistake.
PARKED = ["_Measures", "ScheduleTolerance"]

# Focused diagrams. Keys become diagram names; numeric prefixes keep them ordered.
FOCUSED = {
    "01 Work Order Core": [
        "FactWorkOrder", "DimDate", "DimAsset", "DimLocation",
        "DimSite", "DimWorkType", "DimStatus",
    ],
    "02 Cost and Labour": [
        "FactLabour", "FactMaterial", "DimCraft", "DimLabor",
        "DimItem", "DimDate", "DimSite",
    ],
    "03 Reliability": [
        "FactDowntime", "FactFailure", "FactMeterReading",
        "DimAsset", "DimFailureCode", "DimDate", "DimSite",
    ],
}

ALL_DIAGRAM_NAME = "99 All Tables"

# geometry
COL_PITCH = 320      # horizontal distance between card centres
BAND_PITCH = 460     # vertical distance between bands
CARD_W = 240
CARD_H = 280
PARK_GAP = 420       # extra x offset for unrelated tables


# ---------------------------------------------------------------------------

def find_nodes(diagram):
    """Return the node list from a diagram dict, whatever it is called."""
    for key in ("nodes", "Nodes", "tables", "entities"):
        if isinstance(diagram.get(key), list):
            return key, diagram[key]
    return None, None


def node_name(node):
    """Return the table name a node refers to, whatever the key is called."""
    for key in ("nodeIndex", "NodeIndex", "name", "Name", "table", "entity"):
        v = node.get(key)
        if isinstance(v, str) and v:
            return key, v
    return None, None


def set_location(node, x, y):
    """Write x/y into whichever location shape the node uses. Returns True if set."""
    for key in ("location", "Location", "position"):
        loc = node.get(key)
        if isinstance(loc, dict):
            for xk, yk in (("x", "y"), ("X", "Y")):
                if xk in loc or yk in loc:
                    loc[xk] = x
                    loc[yk] = y
                    return True
            loc["x"] = x
            loc["y"] = y
            return True
    if "x" in node and "y" in node:
        node["x"] = x
        node["y"] = y
        return True
    return False


def set_size(node):
    for key in ("size", "Size"):
        s = node.get(key)
        if isinstance(s, dict):
            for wk, hk in (("width", "height"), ("Width", "Height")):
                if wk in s or hk in s:
                    s[wk] = CARD_W
                    s[hk] = CARD_H
                    return


def build_positions(tables_present):
    """table name -> (x, y). Unlisted tables go to a clearly separate row."""
    pos = {}
    listed = set()

    for i, name in enumerate(n for n in CONFORMED if n in tables_present):
        pos[name] = (i * COL_PITCH, 0)
        listed.add(name)

    fact_x = {}
    for i, name in enumerate(n for n in FACTS if n in tables_present):
        x = i * COL_PITCH
        pos[name] = (x, BAND_PITCH)
        fact_x[name] = x
        listed.add(name)

    max_stack = 0
    for fact, dims in PRIVATE.items():
        # if the fact is absent, fall back to a left-aligned column
        x = fact_x.get(fact, 0)
        j = 0
        for name in dims:
            if name not in tables_present:
                continue
            pos[name] = (x, 2 * BAND_PITCH + j * (CARD_H + 80))
            listed.add(name)
            j += 1
        max_stack = max(max_stack, j)

    n_cols = max(len([n for n in CONFORMED if n in tables_present]),
                 len([n for n in FACTS if n in tables_present]))
    park_x = n_cols * COL_PITCH + PARK_GAP
    for i, name in enumerate(n for n in PARKED if n in tables_present):
        pos[name] = (park_x, i * BAND_PITCH)
        listed.add(name)

    spill_y = 2 * BAND_PITCH + max(max_stack, 1) * (CARD_H + 80) + 200
    leftovers = sorted(t for t in tables_present if t not in listed)
    for i, name in enumerate(leftovers):
        pos[name] = (i * COL_PITCH, spill_y)
    return pos, leftovers


def make_diagram(template, name, ordinal, tables, positions):
    """Clone a diagram dict, keeping only the named tables."""
    d = json.loads(json.dumps(template))
    nkey, nodes = find_nodes(d)
    keep = []
    for node in nodes:
        _, tname = node_name(node)
        if tname in tables:
            set_location(node, *positions[tname])
            set_size(node)
            keep.append(node)
    d[nkey] = keep
    for k, v in (("name", name), ("Name", name)):
        if k in d:
            d[k] = v
    if "name" not in d and "Name" not in d:
        d["name"] = name
    for k in ("ordinal", "Ordinal"):
        if k in d:
            d[k] = ordinal
    for k in ("scrollPosition", "ScrollPosition"):
        if isinstance(d.get(k), dict):
            d[k] = {"x": 0, "y": 0}
    for k in ("zoomValue", "ZoomValue"):
        if k in d:
            d[k] = 80
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("semantic_model_folder",
                    help="the *.SemanticModel folder inside your PBIP")
    ap.add_argument("--diagrams", action="store_true",
                    help="also create the four focused diagrams")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # diagramLayout.json sits either at the folder root or under definition/
    candidates = [
        os.path.join(args.semantic_model_folder, "diagramLayout.json"),
        os.path.join(args.semantic_model_folder, "definition", "diagramLayout.json"),
    ]
    path = next((p for p in candidates if os.path.isfile(p)), None)
    if not path:
        sys.exit("diagramLayout.json not found. Looked in:\n  " +
                 "\n  ".join(candidates) +
                 "\nOpen the model view in Desktop once and save - the file is "
                 "only written after the diagram exists.")
    print(f"found  {path}")

    with open(path, encoding="utf-8-sig") as fh:
        doc = json.load(fh)

    dkey = next((k for k in ("diagrams", "Diagrams")
                 if isinstance(doc.get(k), list) and doc[k]), None)
    if not dkey:
        sys.exit("No diagrams array in this file - schema is not what this "
                 "script expects. Nothing written. Send me the file and I will "
                 "adjust the parser.")

    # re-runs: start from the all-tables diagram, not whichever focused one is first
    base = next((d for d in doc[dkey]
                 if d.get("name", d.get("Name")) == ALL_DIAGRAM_NAME), doc[dkey][0])
    nkey, nodes = find_nodes(base)
    if not nodes:
        sys.exit("Could not locate the node list inside the first diagram. "
                 "Nothing written.")

    present = []
    unnamed = 0
    for node in nodes:
        _, tname = node_name(node)
        if tname:
            present.append(tname)
        else:
            unnamed += 1
    if unnamed:
        sys.exit(f"{unnamed} nodes have no recognisable table name. "
                 "Nothing written.")

    print(f"tables in diagram: {len(present)}")
    positions, leftovers = build_positions(set(present))

    if leftovers:
        print("\n!! not in the layout spec - parked in a spillover row:")
        for t in leftovers:
            print(f"     {t}")
        print("   If these are raw Maximo tables (WORKORDER, ASSET, ...) then")
        print("   the Power Query star-schema transforms have not been applied.")
        print("   Fix that first - tidying positions will not help a wrong model.\n")

    # reposition the primary diagram
    for node in nodes:
        _, tname = node_name(node)
        if not set_location(node, *positions[tname]):
            sys.exit(f"Could not write a location for '{tname}'. Nothing written.")
        set_size(node)
    for k, v in (("name", ALL_DIAGRAM_NAME), ("Name", ALL_DIAGRAM_NAME)):
        if k in base:
            base[k] = v

    if args.diagrams:
        extra = []
        ordinal = 0
        for name, tables in FOCUSED.items():
            subset = [t for t in tables if t in present]
            if len(subset) < 2:
                print(f"skipping '{name}' - fewer than 2 of its tables exist")
                continue
            sub_pos, _ = build_positions(set(subset))
            extra.append(make_diagram(base, name, ordinal, set(subset), sub_pos))
            ordinal += 1
        for k in ("ordinal", "Ordinal"):
            if k in base:
                base[k] = ordinal
        doc[dkey] = extra + [base]
        for k in ("selectedDiagram", "SelectedDiagram",
                  "defaultDiagram", "DefaultDiagram"):
            if k in doc:
                doc[k] = ALL_DIAGRAM_NAME
        print(f"diagrams written: {len(doc[dkey])}")

    if args.dry_run:
        print("\n--dry-run: nothing written. Planned positions:")
        for t in sorted(positions, key=lambda k: (positions[k][1], positions[k][0])):
            x, y = positions[t]
            print(f"  {t:<22} x={x:>5}  y={y:>5}")
        return

    shutil.copy2(path, path + ".bak")
    print(f"backup {path}.bak")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    print("done - reopen the .pbip")


if __name__ == "__main__":
    main()
