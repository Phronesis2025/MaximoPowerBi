#!/usr/bin/env python3
"""
Synthetic IBM Maximo dataset generator
======================================

Produces Maximo-authentic, referentially-consistent CSV extracts for use as the
source data behind a Power BI semantic model.

WHY THIS EXISTS
---------------
There is no free, open sample Maximo dataset. This generator creates one that is
safe to publish (no client data of any kind) while preserving the things that
make Maximo modelling hard and interesting:

  * OLTP-shaped tables that must be denormalised into a star schema
  * Multi-site / multi-org keys (SITEID + ORGID on nearly every table)
  * Work-order status lifecycle history in a separate table (WOSTATUS)
  * Nulls exactly where Maximo has nulls (no ACTFINISH on open work,
    no FAILURECODE on preventive work, no ASSETNUM on location-only work)
  * Asset and location hierarchies (PARENT self-references)
  * Cost roll-ups that reconcile between WORKORDER and the transaction tables

DESIGN CHOICE: THE DATA HAS DELIBERATE SIGNAL
---------------------------------------------
Uniformly random data makes a dashboard that says nothing. Each site is given a
distinct maintenance "personality" so that KPI visuals reveal a real story:

  BEDFORD  - mature program. Low reactive %, high PM compliance, stable.
  HOUSTON  - under strain. High reactive %, poor PM compliance, growing backlog.
  AURORA   - improving. Starts poor, trends toward good across the window.

Roughly 5% of assets are "bad actors" with elevated failure rates, so a
top-10-worst-assets visual returns something meaningful.

REPRODUCIBILITY
---------------
Everything derives from a single SEED. Re-running with the same SEED and config
produces byte-identical CSVs. Change SEED for a different-but-equally-valid
dataset. All volume and date parameters are in CONFIG below.

ALL DATA IS FABRICATED. Company names, people, assets, and vendors are invented.
Any resemblance to a real organisation is coincidental.
"""

import csv
import math
import os
import random
from datetime import date, datetime, timedelta

# ----------------------------------------------------------------------------
# CONFIG - every assumption a reader might question lives here
# ----------------------------------------------------------------------------

SEED = 20260729

START_DATE = date(2023, 7, 1)   # first work-order report date
END_DATE = date(2026, 7, 29)    # "today" for the dataset
CALENDAR_START = date(2023, 1, 1)
CALENDAR_END = date(2026, 12, 31)

ORGID = "MAINCO"
ITEMSETID = "ITEMSET1"
COMPANYSETID = "COMPSET1"
BASECURRENCY = "USD"

OUTDIR = "/home/claude/out/data"

# Site personalities. Values are targets the generator aims at, not hard rules.
#   reactive_share    : fraction of corrective+emergency work in total work
#   pm_compliance     : fraction of PM work orders completed by TARGCOMPDATE
#   sched_compliance  : fraction of scheduled work started on schedule
#   drift             : linear change applied across the window (+ = improving)
#   asset_count       : assets at the site
#   backlog_pressure  : multiplier on open-work volume at END_DATE
SITES = {
    "BEDFORD": {
        "desc": "Bedford Assembly Plant",
        "kind": "manufacturing",
        "reactive_share": 0.22,
        "pm_compliance": 0.92,
        "sched_compliance": 0.85,
        "drift": 0.01,
        "asset_count": 340,
        "backlog_pressure": 0.8,
        "city": "Bedford",
        "state": "IN",
    },
    "HOUSTON": {
        "desc": "Houston Process Facility",
        "kind": "process",
        "reactive_share": 0.44,
        "pm_compliance": 0.71,
        "sched_compliance": 0.58,
        "drift": -0.03,
        "asset_count": 300,
        "backlog_pressure": 1.9,
        "city": "Houston",
        "state": "TX",
    },
    "AURORA": {
        "desc": "Aurora Distribution Center",
        "kind": "facilities",
        "reactive_share": 0.38,
        "pm_compliance": 0.78,
        "sched_compliance": 0.66,
        "drift": 0.14,
        "asset_count": 260,
        "backlog_pressure": 1.1,
        "city": "Aurora",
        "state": "CO",
    },
}

# Asset classes by site kind. failrate = expected failures per year.
ASSET_CLASSES = {
    "manufacturing": [
        ("CONVEYOR", "Belt Conveyor", 0.9, 18000, 12),
        ("ROBOT", "Articulated Robot Cell", 0.6, 145000, 15),
        ("PRESS", "Hydraulic Press", 0.7, 210000, 20),
        ("MOTOR", "AC Induction Motor", 0.5, 4200, 15),
        ("PUMP", "Centrifugal Pump", 1.1, 7800, 12),
        ("COMPRESSOR", "Rotary Screw Air Compressor", 0.8, 46000, 15),
        ("AHU", "Air Handling Unit", 0.7, 38000, 20),
        ("WELDER", "Robotic Welding Station", 0.9, 62000, 12),
        ("PANEL", "Motor Control Center", 0.3, 27000, 25),
        ("FORKLIFT", "Electric Forklift", 1.3, 34000, 10),
    ],
    "process": [
        ("PUMP", "Centrifugal Process Pump", 1.6, 14500, 10),
        ("VALVE", "Control Valve", 1.2, 6400, 12),
        ("HEATEXCH", "Shell and Tube Heat Exchanger", 0.6, 88000, 25),
        ("COMPRESSOR", "Reciprocating Compressor", 1.4, 165000, 15),
        ("TANK", "Storage Tank", 0.2, 240000, 30),
        ("MIXER", "Agitator Mixer", 0.9, 41000, 15),
        ("BOILER", "Package Boiler", 0.8, 320000, 25),
        ("MOTOR", "AC Induction Motor", 0.7, 5600, 15),
        ("XFMR", "Dry Type Transformer", 0.2, 52000, 30),
        ("ANALYZER", "Inline Process Analyzer", 1.5, 29000, 8),
    ],
    "facilities": [
        ("AHU", "Air Handling Unit", 0.9, 42000, 20),
        ("CHILLER", "Centrifugal Chiller", 0.7, 275000, 22),
        ("CONVEYOR", "Sortation Conveyor", 1.2, 26000, 12),
        ("DOCKLEVEL", "Dock Leveler", 1.0, 9400, 15),
        ("FORKLIFT", "Electric Forklift", 1.4, 34000, 10),
        ("RTU", "Rooftop HVAC Unit", 1.0, 31000, 18),
        ("LIGHTING", "High Bay Lighting Circuit", 0.4, 12000, 20),
        ("GENSET", "Diesel Generator", 0.5, 118000, 25),
        ("SPRINKLER", "Fire Sprinkler Riser", 0.2, 24000, 30),
        ("BALER", "Cardboard Baler", 1.1, 38000, 12),
    ],
}

# Failure taxonomy: asset class -> list of (problem, cause, remedy)
FAILURE_TAXONOMY = {
    "PUMP": [
        ("SEAL-LEAK", "SEAL-WEAR", "SEAL-REPL"),
        ("BEARING-NOISE", "LUBE-FAIL", "BRG-REPL"),
        ("LOW-FLOW", "IMPELLER-WEAR", "IMPELLER-REPL"),
        ("VIBRATION", "MISALIGN", "REALIGN"),
        ("OVERHEAT", "CAVITATION", "ADJUST-SUCTION"),
    ],
    "MOTOR": [
        ("WONT-START", "WINDING-SHORT", "REWIND"),
        ("OVERHEAT", "VENT-BLOCKED", "CLEAN-VENT"),
        ("BEARING-NOISE", "LUBE-FAIL", "BRG-REPL"),
        ("HIGH-AMPS", "LOAD-BIND", "CLEAR-BIND"),
    ],
    "CONVEYOR": [
        ("BELT-TEAR", "FOREIGN-OBJ", "BELT-REPL"),
        ("BELT-TRACKING", "MISALIGN", "REALIGN"),
        ("ROLLER-SEIZED", "BRG-FAIL", "ROLLER-REPL"),
        ("GEARBOX-LEAK", "SEAL-WEAR", "SEAL-REPL"),
        ("JAM", "PRODUCT-MISFEED", "CLEAR-JAM"),
    ],
    "AHU": [
        ("NO-AIRFLOW", "BELT-BROKEN", "BELT-REPL"),
        ("HIGH-DP", "FILTER-FOULED", "FILTER-REPL"),
        ("COIL-FROST", "LOW-CHARGE", "RECHARGE"),
        ("FAN-VIBRATION", "BRG-FAIL", "BRG-REPL"),
        ("CONTROL-FAULT", "SENSOR-DRIFT", "CALIBRATE"),
    ],
    "RTU": [
        ("NO-COOLING", "COMP-FAIL", "COMP-REPL"),
        ("HIGH-DP", "FILTER-FOULED", "FILTER-REPL"),
        ("CONTROL-FAULT", "SENSOR-DRIFT", "CALIBRATE"),
    ],
    "CHILLER": [
        ("LOW-CAPACITY", "TUBE-FOULED", "TUBE-CLEAN"),
        ("HIGH-PRESSURE", "COND-FOULED", "COND-CLEAN"),
        ("COMP-TRIP", "OIL-LOW", "OIL-ADD"),
    ],
    "COMPRESSOR": [
        ("LOW-PRESSURE", "VALVE-LEAK", "VALVE-REPL"),
        ("OIL-CARRYOVER", "SEPARATOR-FOULED", "SEP-REPL"),
        ("HIGH-TEMP", "COOLER-FOULED", "COOLER-CLEAN"),
        ("UNLOADER-FAULT", "SOLENOID-FAIL", "SOLENOID-REPL"),
    ],
    "VALVE": [
        ("WONT-STROKE", "ACTUATOR-FAIL", "ACTUATOR-REPL"),
        ("PACKING-LEAK", "PACKING-WEAR", "REPACK"),
        ("SEAT-LEAK", "EROSION", "TRIM-REPL"),
    ],
    "XFMR": [
        ("HIGH-TEMP", "VENT-BLOCKED", "CLEAN-VENT"),
        ("INSUL-RESISTANCE", "MOISTURE", "DRY-OUT"),
    ],
    "PANEL": [
        ("BREAKER-TRIP", "OVERLOAD", "RESET-INVESTIGATE"),
        ("HOT-CONNECTION", "LOOSE-LUG", "TORQUE-LUG"),
    ],
    "FORKLIFT": [
        ("WONT-LIFT", "HYD-LEAK", "HOSE-REPL"),
        ("BATTERY-LOW", "CELL-FAIL", "BATTERY-REPL"),
        ("BRAKE-SOFT", "PAD-WEAR", "PAD-REPL"),
    ],
    "GENSET": [
        ("WONT-START", "BATTERY-FAIL", "BATTERY-REPL"),
        ("LOW-OUTPUT", "FUEL-FILTER", "FILTER-REPL"),
    ],
    "DEFAULT": [
        ("NOT-OPERATING", "COMPONENT-FAIL", "COMPONENT-REPL"),
        ("DEGRADED", "WEAR", "REBUILD"),
        ("LEAK", "SEAL-WEAR", "SEAL-REPL"),
        ("ALARM", "SENSOR-DRIFT", "CALIBRATE"),
    ],
}

CRAFTS = [
    ("ELECT", "Electrician", 48.50),
    ("MECH", "Mechanic", 44.00),
    ("INSTR", "Instrument Technician", 52.25),
    ("HVAC", "HVAC Technician", 46.75),
    ("MILLWR", "Millwright", 47.50),
    ("WELD", "Welder", 45.00),
    ("PIPE", "Pipefitter", 46.00),
    ("OPER", "Operator", 38.00),
    ("PLAN", "Maintenance Planner", 55.00),
    ("SUPV", "Maintenance Supervisor", 62.00),
    ("LUBE", "Lubrication Technician", 39.50),
    ("PDM", "Predictive Maintenance Analyst", 58.00),
]

FIRST_NAMES = [
    "Marcus", "Dana", "Ravi", "Elena", "Tobias", "Priya", "Grant", "Lorna",
    "Desmond", "Ingrid", "Omar", "Cecilia", "Hollis", "Neve", "Rafael",
    "Bethany", "Quentin", "Marisol", "Ewan", "Tamsin", "Cyrus", "Delphine",
    "Roland", "Anika", "Kofi", "Sabine", "Malachi", "Freya", "Emeka", "Lucia",
    "Bartholomew", "Nadia", "Silas", "Yvette", "Ronan", "Isadora", "Dmitri",
    "Callista", "Fenton", "Marguerite", "Hugo", "Selina", "Aurelio", "Brenna",
]
LAST_NAMES = [
    "Okonkwo", "Vandermeer", "Castellanos", "Brightwater", "Nakashima",
    "Ferreira", "Lindqvist", "Achterberg", "Mbeki", "Sorrentino", "Whitcombe",
    "Dziedzic", "Rasmussen", "Fontaine", "Adeyemi", "Kowalczyk", "Beauchamp",
    "Tsvangirai", "Halloran", "Petrosyan", "Marchetti", "Oyelaran", "Bergström",
    "Villanueva", "Thackeray", "Nwachukwu", "Delacroix", "Radulescu",
    "Amankwah", "Strindberg", "Cavanaugh", "Bhattacharya", "Lindgren",
    "Moshoeshoe", "Kaczmarek", "Fitzwilliam", "Andrade", "Wojciechowski",
]

VENDORS = [
    ("FLOWTEK", "Flowtek Industrial Supply", "V"),
    ("BEARCO", "Bearing & Drive Company", "V"),
    ("ELECSRC", "ElecSource Distribution", "V"),
    ("HVACPRO", "HVAC Pro Wholesale", "V"),
    ("SEALMAS", "SealMaster Gaskets", "V"),
    ("NORTHPT", "Northpoint Fasteners", "V"),
    ("APEXCAL", "Apex Calibration Services", "C"),
    ("RELIAVIB", "ReliaVib Condition Monitoring", "C"),
    ("TURBOSVC", "Turbo Machinery Services", "C"),
    ("GRIDPWR", "GridPower Electrical Contractors", "C"),
    ("MOTORWKS", "MotorWorks Rebuild Shop", "C"),
    ("HYDRALIN", "Hydraline Hose & Fitting", "V"),
    ("PUMPMFG", "Meridian Pump Manufacturing", "M"),
    ("CONVMFG", "LinearFlow Conveyor Systems", "M"),
    ("CHILLMFG", "ArcticCore Chiller Corp", "M"),
    ("ROBOMFG", "AxisSix Robotics", "M"),
    ("COMPMFG", "PressureLine Compressors", "M"),
    ("VALVMFG", "TrimTight Valve Works", "M"),
]

SPARE_PARTS = [
    ("Mechanical seal, 2in shaft", "SEALS", "EA", 340.00),
    ("Deep groove ball bearing 6210", "BEARINGS", "EA", 78.50),
    ("V-belt, B-section, 62in", "BELTS", "EA", 24.75),
    ("Pleated air filter 24x24x2", "FILTERS", "EA", 18.90),
    ("Hydraulic hose assembly 1/2in", "HOSES", "EA", 96.00),
    ("Contactor, 3-pole, 40A", "ELECTRICAL", "EA", 142.00),
    ("Motor, 10HP TEFC 1800RPM", "MOTORS", "EA", 1480.00),
    ("Coupling insert, elastomeric", "COUPLINGS", "EA", 63.25),
    ("Pressure transmitter 0-100psi", "INSTRUMENTS", "EA", 620.00),
    ("Gearbox oil, ISO 220, 5gal", "LUBRICANTS", "GAL", 148.00),
    ("Conveyor belt, 24in x 10ft", "BELTS", "FT", 87.00),
    ("Roller, idler, 24in", "ROLLERS", "EA", 54.00),
    ("Control valve trim kit", "VALVES", "EA", 890.00),
    ("Packing set, graphite", "SEALS", "EA", 112.00),
    ("Fuse, 600V 30A class J", "ELECTRICAL", "EA", 31.40),
    ("Grease, EP2 lithium complex", "LUBRICANTS", "LB", 9.85),
    ("Solenoid valve, 24VDC", "VALVES", "EA", 178.00),
    ("Battery, 36V forklift cell", "BATTERIES", "EA", 2250.00),
    ("Thermocouple, type K, 12in", "INSTRUMENTS", "EA", 88.00),
    ("Gasket, spiral wound 4in", "SEALS", "EA", 47.50),
    ("Chain, roller, ANSI 80, 10ft", "CHAINS", "FT", 39.00),
    ("Sheave, 2-groove, 8in", "DRIVES", "EA", 134.00),
    ("Lamp, LED high bay 150W", "LIGHTING", "EA", 168.00),
    ("Filter element, oil, spin-on", "FILTERS", "EA", 42.30),
]

# Work order types. Reactive = CM + EM.
WORKTYPES = ["PM", "CM", "EM", "PDM", "INSP", "PROJ", "SAF"]

rng = random.Random(SEED)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def dt(d, hour=None, minute=None):
    """date -> Maximo-style datetime string."""
    if d is None:
        return ""
    if hour is None:
        hour = rng.randint(6, 17)
    if minute is None:
        minute = rng.choice([0, 7, 12, 15, 23, 30, 38, 45, 52])
    return datetime(d.year, d.month, d.day, hour, minute).strftime("%Y-%m-%d %H:%M:%S")


def dstr(d):
    return "" if d is None else d.strftime("%Y-%m-%d")


def money(x):
    return f"{round(x, 2):.2f}"


def lerp_factor(d):
    """0.0 at START_DATE, 1.0 at END_DATE - used to apply site drift."""
    span = (END_DATE - START_DATE).days
    return max(0.0, min(1.0, (d - START_DATE).days / span))


def seasonal_multiplier(d, kind):
    """Summer HVAC/cooling stress, winter heating stress."""
    m = d.month
    if kind == "facilities":
        return 1.0 + 0.45 * math.sin((m - 4) / 12.0 * 2 * math.pi)
    if kind == "process":
        return 1.0 + 0.20 * math.sin((m - 6) / 12.0 * 2 * math.pi)
    return 1.0 + 0.12 * math.sin((m - 5) / 12.0 * 2 * math.pi)


def write_csv(name, header, rows):
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        w.writerows(rows)
    return path, len(rows)


MANIFEST = []


def emit(name, header, rows, grain):
    path, n = write_csv(name, header, rows)
    size_kb = os.path.getsize(path) / 1024.0
    MANIFEST.append((name, n, len(header), size_kb, grain))
    print(f"  {name:<24} {n:>8,} rows  {len(header):>3} cols  {size_kb:>9,.0f} KB")


# ----------------------------------------------------------------------------
# 1. ORGANIZATION / SITE
# ----------------------------------------------------------------------------

def build_org_site():
    emit("ORGANIZATION.csv",
         ["ORGID", "DESCRIPTION", "BASECURRENCY1", "ITEMSETID", "COMPANYSETID", "ACTIVE"],
         [[ORGID, "Maintenance Holdings Inc", BASECURRENCY, ITEMSETID, COMPANYSETID, 1]],
         "one row per organization")

    rows = []
    for sid, cfg in SITES.items():
        rows.append([sid, ORGID, cfg["desc"], 1, cfg["city"], cfg["state"]])
    emit("SITE.csv",
         ["SITEID", "ORGID", "DESCRIPTION", "ACTIVE", "CITY", "STATE"],
         rows, "one row per site")


# ----------------------------------------------------------------------------
# 2. LOCATIONS (with hierarchy via PARENT)
# ----------------------------------------------------------------------------

AREA_NAMES = {
    "manufacturing": ["BODY-SHOP", "PAINT", "FINAL-ASSY", "STAMPING", "UTILITIES", "WAREHOUSE"],
    "process": ["REACTION", "DISTILL", "TANKFARM", "UTILITIES", "LOADING", "LAB"],
    "facilities": ["INBOUND", "SORT-HALL", "OUTBOUND", "MEZZANINE", "UTILITIES", "OFFICE"],
}

LOCATIONS = {}   # siteid -> list of operating location codes


def build_locations():
    rows = []
    for sid, cfg in SITES.items():
        top = f"{sid}-PLANT"
        rows.append([top, f"{cfg['desc']} - Site Root", sid, ORGID, "OPERATING",
                     "OPERATING", "", f"6000-{sid[:3]}-000", 1, dt(START_DATE), "MAXADMIN"])
        ops = []
        for area in AREA_NAMES[cfg["kind"]]:
            acode = f"{sid}-{area}"
            rows.append([acode, f"{area.replace('-', ' ').title()} Area", sid, ORGID,
                         "OPERATING", "OPERATING", top, f"6000-{sid[:3]}-100", 1,
                         dt(START_DATE), "MAXADMIN"])
            n_sub = rng.randint(3, 6)
            for i in range(1, n_sub + 1):
                scode = f"{acode}-{i:02d}"
                rows.append([scode, f"{area.replace('-', ' ').title()} System {i:02d}",
                             sid, ORGID, "OPERATING", "OPERATING", acode,
                             f"6000-{sid[:3]}-1{i:02d}", 1, dt(START_DATE), "MAXADMIN"])
                ops.append(scode)
        # storeroom + repair + salvage (non-operating types Maximo requires)
        rows.append([f"{sid}-STORE", "Main Storeroom", sid, ORGID, "STOREROOM",
                     "ACTIVE", top, f"6100-{sid[:3]}-000", 1, dt(START_DATE), "MAXADMIN"])
        rows.append([f"{sid}-REPAIR", "Repair Shop", sid, ORGID, "REPAIR",
                     "ACTIVE", top, f"6200-{sid[:3]}-000", 1, dt(START_DATE), "MAXADMIN"])
        rows.append([f"{sid}-SALVAGE", "Salvage Holding", sid, ORGID, "SALVAGE",
                     "ACTIVE", top, f"6300-{sid[:3]}-000", 1, dt(START_DATE), "MAXADMIN"])
        LOCATIONS[sid] = ops

    emit("LOCATIONS.csv",
         ["LOCATION", "DESCRIPTION", "SITEID", "ORGID", "TYPE", "STATUS", "PARENT",
          "GLACCOUNT", "ISRUNNING", "CHANGEDATE", "CHANGEBY"],
         rows, "one row per location; PARENT self-references LOCATION")


# ----------------------------------------------------------------------------
# 3. CRAFT / LABOR / PERSON
# ----------------------------------------------------------------------------

LABOR = []        # dicts
LABOR_BY_SITE = {}
SUPERVISORS = {}  # siteid -> list of laborcodes


def build_labor():
    craft_rows = []
    for code, desc, rate in CRAFTS:
        craft_rows.append([code, desc, ORGID, money(rate), money(rate * 1.5), 1])
    emit("CRAFT.csv",
         ["CRAFT", "DESCRIPTION", "ORGID", "STDRATE", "PREMIUMRATE", "ACTIVE"],
         craft_rows, "one row per craft; rate flattened from CRAFTRATE")

    labor_rows = []
    person_rows = []
    used = set()
    seq = 0
    for sid, cfg in SITES.items():
        LABOR_BY_SITE[sid] = []
        SUPERVISORS[sid] = []
        # headcount scales with asset count
        headcount = max(14, int(cfg["asset_count"] / 11))
        for i in range(headcount):
            while True:
                fn = rng.choice(FIRST_NAMES)
                ln = rng.choice(LAST_NAMES)
                if (fn, ln) not in used:
                    used.add((fn, ln))
                    break
            seq += 1
            pid = f"P{seq:05d}"
            lcode = f"L{seq:05d}"
            # craft mix: mostly hands-on, a few planners/supervisors
            if i == 0:
                craft = "SUPV"
            elif i == 1:
                craft = "PLAN"
            elif i == 2 and cfg["kind"] != "facilities":
                craft = "PDM"
            else:
                craft = rng.choice(["ELECT", "MECH", "INSTR", "HVAC", "MILLWR",
                                    "WELD", "PIPE", "OPER", "LUBE"])
            hire = START_DATE - timedelta(days=rng.randint(200, 5200))
            status = "ACTIVE" if rng.random() > 0.06 else "INACTIVE"
            rate = dict((c, r) for c, _, r in CRAFTS)[craft]
            rate = round(rate * rng.uniform(0.94, 1.09), 2)

            labor_rows.append([lcode, pid, f"{fn} {ln}", craft, sid, ORGID,
                               status, dstr(hire), money(rate)])
            person_rows.append([pid, f"{fn} {ln}", fn, ln, status, sid,
                                f"{fn[0].lower()}{ln.lower()}@example.invalid"])
            rec = {"laborcode": lcode, "craft": craft, "rate": rate,
                   "site": sid, "name": f"{fn} {ln}", "status": status}
            LABOR.append(rec)
            LABOR_BY_SITE[sid].append(rec)
            if craft == "SUPV":
                SUPERVISORS[sid].append(lcode)
        if not SUPERVISORS[sid]:
            SUPERVISORS[sid].append(LABOR_BY_SITE[sid][0]["laborcode"])

    emit("LABOR.csv",
         ["LABORCODE", "PERSONID", "DISPLAYNAME", "CRAFT", "SITEID", "ORGID",
          "STATUS", "HIREDATE", "PAYRATE"],
         labor_rows, "one row per labor record; primary CRAFT flattened from LABORCRAFTRATE")
    emit("PERSON.csv",
         ["PERSONID", "DISPLAYNAME", "FIRSTNAME", "LASTNAME", "STATUS",
          "LOCATIONSITE", "PRIMARYEMAIL"],
         person_rows, "one row per person")


# ----------------------------------------------------------------------------
# 4. COMPANIES / ITEM / INVENTORY
# ----------------------------------------------------------------------------

ITEMS = []


def build_items():
    comp_rows = []
    for code, name, ctype in VENDORS:
        comp_rows.append([code, name, ctype, ORGID, COMPANYSETID,
                          rng.choice(["Net 30", "Net 45", "Net 60"]), 1])
    emit("COMPANIES.csv",
         ["COMPANY", "NAME", "TYPE", "ORGID", "COMPANYSETID", "PAYMENTTERMS", "ACTIVE"],
         comp_rows, "one row per vendor/manufacturer/courier; TYPE V=vendor M=manufacturer C=courier")

    item_rows = []
    for i, (desc, cgroup, unit, cost) in enumerate(SPARE_PARTS, start=1):
        inum = f"ITM-{i:04d}"
        rotating = 1 if cgroup in ("MOTORS", "BATTERIES") else 0
        ITEMS.append({"itemnum": inum, "desc": desc, "unit": unit,
                      "cost": cost, "group": cgroup, "rotating": rotating})
        item_rows.append([inum, desc, ITEMSETID, unit, unit, rotating,
                          cgroup, "ACTIVE"])
    emit("ITEM.csv",
         ["ITEMNUM", "DESCRIPTION", "ITEMSETID", "ISSUEUNIT", "ORDERUNIT",
          "ROTATING", "COMMODITYGROUP", "STATUS"],
         item_rows, "one row per item master record")

    inv_rows = []
    for sid in SITES:
        store = f"{sid}-STORE"
        for it in ITEMS:
            avg = round(it["cost"] * rng.uniform(0.92, 1.08), 2)
            minl = rng.choice([1, 2, 2, 4, 6, 10])
            maxl = minl * rng.choice([3, 4, 5])
            cur = max(0, int(rng.triangular(0, maxl, maxl * 0.55)))
            abc = "A" if it["cost"] > 500 else ("B" if it["cost"] > 100 else "C")
            last_issue = END_DATE - timedelta(days=rng.randint(1, 240))
            inv_rows.append([it["itemnum"], store, sid, ORGID, ITEMSETID,
                             cur, minl, maxl, minl, money(avg), money(it["cost"]),
                             it["unit"], abc, rng.randint(0, 60), dstr(last_issue)])
    emit("INVENTORY.csv",
         ["ITEMNUM", "LOCATION", "SITEID", "ORGID", "ITEMSETID", "CURBAL",
          "MINLEVEL", "MAXLEVEL", "REORDERPOINT", "AVGCOST", "STDCOST",
          "ISSUEUNIT", "ABCTYPE", "ISSUEYTD", "LASTISSUEDATE"],
         inv_rows, "one row per item per storeroom (ITEMNUM + LOCATION + SITEID)")


# ----------------------------------------------------------------------------
# 5. FAILURECODE hierarchy
# ----------------------------------------------------------------------------

def build_failurecodes():
    rows = []
    seen = set()
    for cls, entries in FAILURE_TAXONOMY.items():
        parent = f"FC-{cls}"
        if parent not in seen:
            rows.append([parent, f"{cls} failure class", ORGID, "", "CLASS"])
            seen.add(parent)
        for prob, cause, remedy in entries:
            for code, kind in ((prob, "PROBLEM"), (cause, "CAUSE"), (remedy, "REMEDY")):
                key = (parent, code)
                if key in seen:
                    continue
                seen.add(key)
                rows.append([code, code.replace("-", " ").title(), ORGID, parent, kind])
    emit("FAILURECODE.csv",
         ["FAILURECODE", "DESCRIPTION", "ORGID", "PARENT", "TYPE"],
         rows, "failure taxonomy; PARENT links problem/cause/remedy to a failure class")


# ----------------------------------------------------------------------------
# 6. ASSET (with hierarchy + criticality + bad actors)
# ----------------------------------------------------------------------------

ASSETS = []
ASSETS_BY_SITE = {}


def build_assets():
    rows = []
    meter_rows = []
    seq = 0
    for sid, cfg in SITES.items():
        ASSETS_BY_SITE[sid] = []
        classes = ASSET_CLASSES[cfg["kind"]]
        ops = LOCATIONS[sid]
        n = cfg["asset_count"]
        # ~18% are parent assets (systems), the rest children
        parents_made = []
        for i in range(n):
            seq += 1
            cls, cdesc, failrate, cost, life = rng.choice(classes)
            anum = f"{cls}-{seq:05d}"
            loc = rng.choice(ops)
            install = START_DATE - timedelta(days=rng.randint(120, int(life * 365 * 0.75)))
            age_yrs = (END_DATE - install).days / 365.25

            is_parent = (i % 6 == 0)
            parent = ""
            if not is_parent and parents_made:
                cand = [p for p in parents_made if p[1] == loc]
                if cand and rng.random() < 0.55:
                    parent = rng.choice(cand)[0]

            criticality = rng.choices([1, 2, 3, 4], weights=[8, 22, 46, 24])[0]
            bad_actor = rng.random() < 0.05
            # failure propensity: base rate, aged up, criticality-neutral, bad actors x2.6
            propensity = failrate * (1.0 + 0.045 * age_yrs) * (2.6 if bad_actor else 1.0)
            propensity *= rng.uniform(0.7, 1.35)

            status = "OPERATING"
            r = rng.random()
            if r < 0.035:
                status = "NOT READY"
            elif r < 0.055:
                status = "DECOMMISSIONED"

            pprice = round(cost * rng.uniform(0.82, 1.22), 2)
            mfr = rng.choice([v[0] for v in VENDORS if v[2] == "M"])
            vend = rng.choice([v[0] for v in VENDORS if v[2] == "V"])

            rec = {
                "assetnum": anum, "site": sid, "loc": loc, "cls": cls,
                "propensity": propensity, "criticality": criticality,
                "bad_actor": bad_actor, "status": status, "install": install,
                "replcost": pprice, "parent": parent, "kind": cfg["kind"],
            }
            ASSETS.append(rec)
            ASSETS_BY_SITE[sid].append(rec)
            if is_parent:
                parents_made.append((anum, loc))

            # RAV basis: installed replacement value, not the equipment invoice
            installed = pprice * rng.uniform(2.2, 3.0)
            rows.append([anum, f"{cdesc} {seq:05d}", sid, ORGID, loc, parent, status,
                         cls, "", f"SN{rng.randint(10**7, 10**8 - 1)}", mfr, vend,
                         dstr(install), money(pprice), money(installed),
                         "0.00", "0.00", "0.00", criticality, criticality,
                         1 if status == "OPERATING" else 0,
                         f"CS-{cls}", dt(install), "MAXADMIN"])

            # meters on ~45% of assets
            if rng.random() < 0.45 and status == "OPERATING":
                mname, unit = rng.choice([("RUNHOURS", "HOURS"), ("VIBRATION", "IN/S"),
                                          ("TEMP-BRG", "DEGF"), ("PRESSURE", "PSI"),
                                          ("AMPS", "AMP")])
                rec["meter"] = (mname, unit)
                meter_rows.append([anum, sid, mname, unit, "", "", 1,
                                   "GAUGE" if mname != "RUNHOURS" else "CONTINUOUS"])

    emit("ASSET.csv",
         ["ASSETNUM", "DESCRIPTION", "SITEID", "ORGID", "LOCATION", "PARENT", "STATUS",
          "ASSETTYPE", "ITEMNUM", "SERIALNUM", "MANUFACTURER", "VENDOR", "INSTALLDATE",
          "PURCHASEPRICE", "REPLACECOST", "TOTDOWNTIME", "TOTALCOST", "YTDCOST",
          "PRIORITY", "CRITICALITY", "ISRUNNING", "CLASSSTRUCTUREID",
          "CHANGEDATE", "CHANGEBY"],
         rows, "one row per asset; PARENT self-references ASSETNUM")
    emit("ASSETMETER.csv",
         ["ASSETNUM", "SITEID", "METERNAME", "MEASUREUNITID", "LASTREADING",
          "LASTREADINGDATE", "ACTIVE", "METERTYPE"],
         meter_rows, "one row per asset per meter (ASSETNUM + METERNAME + SITEID)")


# ----------------------------------------------------------------------------
# 7. JOBPLAN + PM
# ----------------------------------------------------------------------------

PMS = []

PM_TEMPLATES = [
    ("Monthly inspection and lubrication", 1, "MONTHS", 1.5, ["LUBE", "MECH"]),
    ("Quarterly mechanical inspection", 3, "MONTHS", 3.0, ["MECH", "MILLWR"]),
    ("Semi-annual electrical inspection", 6, "MONTHS", 4.0, ["ELECT"]),
    ("Annual overhaul and calibration", 12, "MONTHS", 12.0, ["MECH", "INSTR"]),
    ("Weekly operator round", 1, "WEEKS", 0.5, ["OPER"]),
    ("Quarterly vibration analysis route", 3, "MONTHS", 2.0, ["PDM"]),
    ("Annual thermographic survey", 12, "MONTHS", 3.5, ["ELECT", "PDM"]),
    ("Semi-annual filter and belt change", 6, "MONTHS", 2.5, ["HVAC", "MECH"]),
]


def build_jobplans_pms():
    jp_rows = []
    jt_rows = []
    jp_index = []
    for i, (desc, freq, unit, dur, crafts) in enumerate(PM_TEMPLATES, start=1):
        for sid in SITES:
            jpnum = f"JP-{sid[:3]}-{i:03d}"
            jp_rows.append([jpnum, desc, sid, ORGID, "ACTIVE", money(dur),
                            "ITEM", rng.choice(crafts)])
            jp_index.append({"jpnum": jpnum, "site": sid, "desc": desc,
                             "freq": freq, "unit": unit, "dur": dur, "crafts": crafts})
            for t in range(1, rng.randint(3, 6)):
                jt_rows.append([jpnum, sid, t * 10,
                                rng.choice(["Isolate and lock out equipment",
                                            "Inspect for leaks and abnormal wear",
                                            "Check and record operating parameters",
                                            "Lubricate per manufacturer schedule",
                                            "Verify guarding and safety devices",
                                            "Clean and restore to service",
                                            "Record readings in Maximo"]),
                                money(round(dur / 4, 2))])
    emit("JOBPLAN.csv",
         ["JPNUM", "DESCRIPTION", "SITEID", "ORGID", "STATUS", "JPDURATION",
          "TEMPLATETYPE", "PRIMARYCRAFT"],
         jp_rows, "one row per job plan")
    emit("JOBTASK.csv",
         ["JPNUM", "SITEID", "JPTASKID", "DESCRIPTION", "ESTDUR"],
         jt_rows, "one row per job plan task (JPNUM + JPTASKID)")

    pm_rows = []
    seq = 0
    for sid, cfg in SITES.items():
        eligible = [a for a in ASSETS_BY_SITE[sid] if a["status"] == "OPERATING"]
        site_jps = [j for j in jp_index if j["site"] == sid]
        # ~62% of operating assets carry at least one PM
        for a in eligible:
            if rng.random() > 0.62:
                continue
            n_pm = 1 if rng.random() < 0.72 else 2
            for _ in range(n_pm):
                seq += 1
                jp = rng.choice(site_jps)
                pmnum = f"PM-{seq:05d}"
                # stagger first due date across the window start
                first = START_DATE + timedelta(days=rng.randint(0, 90))
                leadtime = rng.choice([3, 5, 7, 14])
                rec = {"pmnum": pmnum, "site": sid, "assetnum": a["assetnum"],
                       "loc": a["loc"], "jpnum": jp["jpnum"], "freq": jp["freq"],
                       "unit": jp["unit"], "dur": jp["dur"], "desc": jp["desc"],
                       "crafts": jp["crafts"], "first": first,
                       "crit": a["criticality"], "leadtime": leadtime}
                PMS.append(rec)
                pm_rows.append([pmnum, jp["desc"], sid, ORGID, a["assetnum"], a["loc"],
                                jp["jpnum"], jp["freq"], jp["unit"], "", "", "",
                                "ACTIVE", a["criticality"],
                                leadtime, "APPR", 1, ""])
    emit("PM.csv",
         ["PMNUM", "DESCRIPTION", "SITEID", "ORGID", "ASSETNUM", "LOCATION", "JPNUM",
          "FREQUENCY", "FREQUNIT", "NEXTDATE", "LASTSTARTDATE", "LASTCOMPDATE",
          "STATUS", "PRIORITY", "LEADTIME", "WOSTATUS", "USEFREQUENCY", "ROUTE"],
         pm_rows, "one row per PM schedule")
    return pm_rows


# ----------------------------------------------------------------------------
# 8. WORK ORDER ENGINE
# ----------------------------------------------------------------------------

WO_HEADER = [
    "WONUM", "DESCRIPTION", "SITEID", "ORGID", "WOCLASS", "WORKTYPE", "STATUS",
    "STATUSDATE", "ASSETNUM", "LOCATION", "PARENT", "PMNUM", "JPNUM", "WOPRIORITY",
    "REPORTDATE", "REPORTEDBY", "TARGSTARTDATE", "TARGCOMPDATE", "SCHEDSTART",
    "SCHEDFINISH", "ACTSTART", "ACTFINISH", "ESTDUR", "ESTLABHRS", "ESTLABCOST",
    "ESTMATCOST", "ACTLABHRS", "ACTLABCOST", "ACTMATCOST", "ACTTOOLCOST",
    "ACTSERVCOST", "DOWNTIME", "FAILURECODE", "PROBLEMCODE", "SUPERVISOR",
    "LEAD", "CREWID", "OWNERGROUP", "GLACCOUNT", "ISTASK", "HISTORYFLAG",
    "CHANGEBY", "CHANGEDATE",
]

CM_DESCRIPTIONS = {
    "SEAL-LEAK": "Repair seal leak", "BEARING-NOISE": "Replace noisy bearing",
    "LOW-FLOW": "Investigate low flow condition", "VIBRATION": "Correct excessive vibration",
    "OVERHEAT": "Investigate overheating", "WONT-START": "Equipment will not start",
    "HIGH-AMPS": "Investigate high amp draw", "BELT-TEAR": "Replace torn belt",
    "BELT-TRACKING": "Correct belt tracking", "ROLLER-SEIZED": "Replace seized roller",
    "GEARBOX-LEAK": "Repair gearbox leak", "JAM": "Clear equipment jam",
    "NO-AIRFLOW": "Restore airflow", "HIGH-DP": "High differential pressure",
    "COIL-FROST": "Coil frosting condition", "FAN-VIBRATION": "Correct fan vibration",
    "CONTROL-FAULT": "Diagnose control fault", "NO-COOLING": "Restore cooling",
    "LOW-CAPACITY": "Investigate loss of capacity", "HIGH-PRESSURE": "High pressure alarm",
    "COMP-TRIP": "Compressor tripped", "LOW-PRESSURE": "Low discharge pressure",
    "OIL-CARRYOVER": "Excessive oil carryover", "HIGH-TEMP": "High temperature alarm",
    "UNLOADER-FAULT": "Unloader not functioning", "WONT-STROKE": "Valve will not stroke",
    "PACKING-LEAK": "Repack leaking valve", "SEAT-LEAK": "Valve seat passing",
    "INSUL-RESISTANCE": "Low insulation resistance", "BREAKER-TRIP": "Breaker tripped",
    "HOT-CONNECTION": "Hot electrical connection", "WONT-LIFT": "Unit will not lift",
    "BATTERY-LOW": "Battery will not hold charge", "BRAKE-SOFT": "Soft brake pedal",
    "NOT-OPERATING": "Equipment not operating", "DEGRADED": "Degraded performance",
    "LEAK": "Repair leak", "ALARM": "Investigate alarm condition",
}

PROJ_DESCRIPTIONS = [
    "Install additional lighting circuit", "Relocate control panel",
    "Upgrade motor starter to VFD", "Replace obsolete instrumentation",
    "Add guarding to drive assembly", "Install remote monitoring sensors",
    "Reroute compressed air header", "Replace roof-mounted exhaust fan",
]
SAF_DESCRIPTIONS = [
    "Correct machine guarding deficiency", "Repair damaged handrail",
    "Replace missing lockout point label", "Repair eyewash station",
    "Address slip hazard from equipment leak", "Replace faulty emergency stop",
    "Correct blocked egress path", "Repair damaged electrical cover",
]
INSP_DESCRIPTIONS = [
    "Regulatory pressure vessel inspection", "Annual fire system inspection",
    "Crane and hoist inspection", "Electrical safety compliance inspection",
    "Insurance boiler inspection", "Fall protection anchor inspection",
]

WO_ROWS = []
WOSTATUS_ROWS = []
LABTRANS_ROWS = []
MATUSE_ROWS = []
FAILREP_ROWS = []
DOWNTIME_ROWS = []

_wo_seq = [1000000]
_lt_seq = [0]
_mu_seq = [0]
_ws_seq = [0]


def next_wonum():
    _wo_seq[0] += 1
    return str(_wo_seq[0])


def pick_failure(cls):
    return rng.choice(FAILURE_TAXONOMY.get(cls, FAILURE_TAXONOMY["DEFAULT"]))


def add_status_history(wonum, sid, chain):
    """chain = list of (status, date, memo)."""
    for status, when, memo in chain:
        _ws_seq[0] += 1
        WOSTATUS_ROWS.append([_ws_seq[0], wonum, sid, status, dt(when), "MAXADMIN", memo])


def build_labtrans(wonum, sid, crafts_wanted, hours, start, finish):
    """Split hours across 1-3 workers of the wanted craft; return (hours, cost)."""
    pool = [l for l in LABOR_BY_SITE[sid]
            if l["craft"] in crafts_wanted and l["status"] == "ACTIVE"]
    if not pool:
        pool = [l for l in LABOR_BY_SITE[sid] if l["status"] == "ACTIVE"]
    n = 1 if hours <= 4 else (2 if hours <= 12 else 3)
    n = min(max(1, n), len(pool))
    workers = rng.sample(pool, n)
    total_h = 0.0
    total_c = 0.0
    remaining = hours
    for i, w in enumerate(workers):
        share = remaining if i == n - 1 else round(remaining * rng.uniform(0.35, 0.6), 2)
        share = max(0.25, round(share, 2))
        remaining = max(0.0, round(remaining - share, 2))
        # a slice of work lands on premium (overtime) time
        prem = 0.0
        if rng.random() < 0.16:
            prem = round(share * rng.uniform(0.15, 0.5), 2)
        reg = round(max(0.0, share - prem), 2)
        cost = round(reg * w["rate"] + prem * w["rate"] * 1.5, 2)
        _lt_seq[0] += 1
        LABTRANS_ROWS.append([
            _lt_seq[0], wonum, sid, ORGID, w["laborcode"], w["craft"],
            dt(finish or start), dt(start), dt(finish or start),
            f"{reg:.2f}", f"{prem:.2f}", money(w["rate"]), money(cost),
            "WORK", "",
        ])
        total_h += reg + prem
        total_c += cost
        if remaining <= 0:
            break
    return round(total_h, 2), round(total_c, 2), max(1, len(workers))


def build_matuse(wonum, sid, worktype, asset_cls, when, est_hours=0.0):
    """Issue 0-4 parts. Returns material cost."""
    if worktype == "PM":
        # a 30-minute operator round does not draw stock; an annual overhaul does
        p_any, maxn = (0.12, 1) if est_hours < 1.5 else (0.45, 2)
    elif worktype in ("CM", "EM"):
        p_any, maxn = 0.78, 4
    elif worktype == "PROJ":
        p_any, maxn = 0.85, 4
    else:
        p_any, maxn = 0.25, 2
    if rng.random() > p_any:
        return 0.0
    total = 0.0
    # cheap consumables dominate real part issues; big-ticket spares are rare
    weights = [1.0 / (1.0 + it["cost"] / 120.0) for it in ITEMS]
    for _ in range(rng.randint(1, maxn)):
        it = rng.choices(ITEMS, weights=weights, k=1)[0]
        qty = rng.choice([1, 1, 1, 2, 2, 3]) if it["cost"] > 400 else \
            rng.choice([1, 1, 2, 2, 3, 4, 6, 8])
        unit = round(it["cost"] * rng.uniform(0.93, 1.1), 2)
        line = round(qty * unit, 2)
        _mu_seq[0] += 1
        MATUSE_ROWS.append([
            _mu_seq[0], wonum, sid, ORGID, it["itemnum"], ITEMSETID,
            f"{sid}-STORE", f"BIN-{rng.randint(1, 60):03d}", qty,
            money(unit), money(line), dt(when), "ISSUE",
        ])
        total += line
    return round(total, 2)


def _finish_hour(a_start, a_finish, start_h, act_hrs, crew):
    """Keep ACTFINISH after ACTSTART when both land on the same calendar day."""
    if a_start is None or a_finish is None:
        return None
    if a_start == a_finish:
        span = max(1, int(math.ceil(act_hrs / max(1, crew))))
        return min(23, start_h + span)
    return None


def make_wo(sid, worktype, report_d, asset=None, loc=None, pm=None,
            est_hours=None, crafts=None, desc=None, force_open=False,
            compliance=None, targ_start_in=None):
    """Create one work order plus its child transactions."""
    cfg = SITES[sid]
    wonum = next_wonum()
    supervisor = rng.choice(SUPERVISORS[sid])
    if asset is None and loc is None:
        loc = rng.choice(LOCATIONS[sid])
    if asset is not None:
        loc = asset["loc"]

    reactive = worktype in ("CM", "EM")
    prio = 1 if worktype == "EM" else (
        2 if reactive and asset and asset["criticality"] <= 2 else
        rng.choices([2, 3, 4], weights=[25, 50, 25])[0])

    problem = cause = remedy = ""
    if reactive and asset is not None:
        problem, cause, remedy = pick_failure(asset["cls"])
        desc = desc or CM_DESCRIPTIONS.get(problem, "Corrective repair")
    elif worktype == "PM":
        desc = desc or (pm["desc"] if pm else "Preventive maintenance")
    elif worktype == "PROJ":
        desc = desc or rng.choice(PROJ_DESCRIPTIONS)
    elif worktype == "SAF":
        desc = desc or rng.choice(SAF_DESCRIPTIONS)
    elif worktype == "INSP":
        desc = desc or rng.choice(INSP_DESCRIPTIONS)
    elif worktype == "PDM":
        desc = desc or "Predictive maintenance follow-up"

    # ---- estimates
    if est_hours is None:
        if worktype == "EM":
            est_hours = round(rng.triangular(1.0, 16.0, 4.0), 2)
        elif worktype == "CM":
            est_hours = round(rng.triangular(0.5, 24.0, 3.5), 2)
        elif worktype == "PROJ":
            est_hours = round(rng.triangular(8.0, 120.0, 32.0), 2)
        elif worktype == "SAF":
            est_hours = round(rng.triangular(1.0, 12.0, 3.0), 2)
        elif worktype == "INSP":
            est_hours = round(rng.triangular(2.0, 16.0, 6.0), 2)
        else:
            est_hours = round(rng.triangular(1.0, 8.0, 2.5), 2)
    crafts = crafts or (["MECH", "ELECT", "MILLWR", "INSTR", "HVAC"] if reactive
                        else ["MECH", "LUBE", "ELECT", "OPER"])
    est_rate = 47.0
    est_lab_cost = round(est_hours * est_rate, 2)
    est_mat_cost = round(est_hours * rng.uniform(12, 90), 2)

    # ---- target dates
    if worktype == "PM" and pm is not None:
        # Maximo generates the PM work order LEADTIME days before it comes due,
        # so REPORTDATE precedes TARGSTARTDATE (the due date).
        targ_start = targ_start_in or report_d
        window = {1: 7, 3: 14, 6: 21, 12: 30}.get(pm["freq"], 14)
        if pm["unit"] == "WEEKS":
            window = 3
        targ_comp = targ_start + timedelta(days=window)
    elif worktype == "EM":
        targ_start = report_d
        targ_comp = report_d + timedelta(days=1)
    elif reactive:
        targ_start = report_d + timedelta(days=rng.randint(0, 3))
        targ_comp = targ_start + timedelta(days=rng.randint(2, 21))
    else:
        targ_start = report_d + timedelta(days=rng.randint(1, 21))
        targ_comp = targ_start + timedelta(days=rng.randint(5, 60))

    # ---- schedule dates (planned work only)
    sched_start = sched_finish = None
    if worktype in ("PM", "PDM", "INSP", "PROJ") or (reactive and rng.random() < 0.45):
        sched_start = targ_start + timedelta(days=rng.randint(-2, 2))
        sched_finish = sched_start + timedelta(days=max(1, int(est_hours / 8) + 1))

    # ---- did it get done, and when
    lf = lerp_factor(report_d)
    if compliance is None:
        compliance = max(0.35, min(0.99, cfg["pm_compliance"] + cfg["drift"] * lf))
    sched_comp = max(0.30, min(0.97, cfg["sched_compliance"] + cfg["drift"] * lf))

    open_now = force_open or report_d > END_DATE - timedelta(days=3)
    if not open_now:
        # backlog pressure -> more recent work left open
        days_old = (END_DATE - report_d).days
        p_open = 0.0
        if days_old < 120:
            p_open = (1 - days_old / 120.0) * 0.55 * cfg["backlog_pressure"]
            if worktype == "EM":
                p_open *= 0.10
            if worktype == "PROJ":
                p_open = min(0.9, p_open * 2.2)
        open_now = rng.random() < p_open

    act_start = act_finish = None
    status = "WAPPR"
    hist = [("WAPPR", report_d, "Work request created")]
    appr_d = report_d + timedelta(days=0 if worktype == "EM" else rng.randint(0, 4))

    if worktype == "EM":
        appr_d = report_d

    if open_now:
        future_dated = force_open or report_d > END_DATE
        r = rng.random() * (0.62 if future_dated else 1.0)
        if r < 0.18:
            status = "WAPPR"
        elif r < 0.62:
            status = "APPR"
            hist.append(("APPR", appr_d, "Approved for scheduling"))
        else:
            status = "INPRG"
            hist.append(("APPR", appr_d, "Approved for scheduling"))
            act_start = min(END_DATE, appr_d + timedelta(days=rng.randint(0, 10)))
            hist.append(("INPRG", act_start, "Work started"))
    else:
        hist.append(("APPR", appr_d, "Approved for scheduling"))
        # on-time or late
        on_time = rng.random() < compliance
        if worktype == "EM":
            act_start = report_d
        elif sched_start is not None:
            jitter = rng.randint(0, 2) if rng.random() < sched_comp else rng.randint(3, 25)
            act_start = sched_start + timedelta(days=jitter)
        else:
            act_start = targ_start + timedelta(days=rng.randint(0, 6))
        if act_start < appr_d:
            act_start = appr_d
        work_days = max(0, int(est_hours / 8))
        if on_time:
            # an on-time job finishes on or before target; if the start drifted
            # past target, pull the start back rather than silently miss target
            act_finish = min(targ_comp, act_start + timedelta(days=work_days + rng.randint(0, 2)))
            if act_finish < act_start:
                act_start = max(appr_d, act_finish - timedelta(days=work_days))
                if act_start > act_finish:
                    act_start = act_finish
        else:
            act_finish = targ_comp + timedelta(days=rng.randint(1, 45))
            if act_finish < act_start:
                act_finish = act_start + timedelta(days=work_days + 1)
        if act_finish > END_DATE:
            act_finish = None
            status = "INPRG"
            hist.append(("INPRG", act_start, "Work started"))
        else:
            hist.append(("INPRG", act_start, "Work started"))
            hist.append(("COMP", act_finish, "Work complete"))
            status = "COMP"
            close_d = act_finish + timedelta(days=rng.randint(2, 25))
            if close_d <= END_DATE and rng.random() < 0.86:
                hist.append(("CLOSE", close_d, "Financially closed"))
                status = "CLOSE"

    # a small share of work is cancelled
    if status in ("WAPPR", "APPR") and rng.random() < 0.035:
        status = "CAN"
        hist.append(("CAN", report_d + timedelta(days=rng.randint(3, 40)),
                     "Cancelled - duplicate or no longer required"))
        act_start = act_finish = None

    # ---- datetime ordering: REPORTDATE <= ACTSTART <= ACTFINISH always holds
    rep_h = rng.randint(6, 9)
    start_h = rng.randint(10, 15)
    act_hrs = act_lab_cost = act_mat_cost = 0.0
    act_tool = act_serv = 0.0
    downtime = 0.0
    crew = 1
    if status in ("COMP", "CLOSE") or (status == "INPRG" and rng.random() < 0.7):
        frac = 1.0 if status in ("COMP", "CLOSE") else rng.uniform(0.15, 0.75)
        variance = rng.uniform(0.75, 1.35) if not reactive else rng.uniform(0.6, 2.1)
        target_hrs = round(est_hours * variance * frac, 2)
        act_hrs, act_lab_cost, crew = build_labtrans(
            wonum, sid, crafts, max(0.25, target_hrs), act_start, act_finish)
        act_mat_cost = build_matuse(wonum, sid, worktype, asset["cls"] if asset else "",
                                    act_finish or act_start, est_hours)
        if rng.random() < 0.10:
            act_tool = round(rng.uniform(15, 350), 2)
        if rng.random() < 0.04:
            act_serv = round(rng.uniform(250, 3500), 2)

        # ---- failure + downtime reporting on reactive work against an asset
        if reactive and asset is not None and status in ("COMP", "CLOSE"):
            FAILREP_ROWS.append([
                wonum, asset["assetnum"], loc, sid, ORGID, f"FC-{asset['cls']}",
                problem, cause, remedy, "ASSET", dt(report_d),
            ])
            if asset["criticality"] <= 3 and rng.random() < 0.72:
                # elapsed repair time = labour hours spread across the crew,
                # plus a wait for parts/access. HOUSTON recovers more slowly.
                elapsed = act_hrs / crew
                wait = rng.triangular(0.0, 26.0, 2.0) if rng.random() < 0.45 else 0.0
                site_factor = {"BEDFORD": 0.85, "HOUSTON": 1.45, "AURORA": 1.05}[sid]
                dt_hours = round(max(0.4, (elapsed * rng.uniform(1.0, 1.7) + wait)
                                     * site_factor), 2)
                dstart = act_start or report_d
                dend = act_finish or dstart
                downtime = dt_hours
                DOWNTIME_ROWS.append([
                    asset["assetnum"], wonum, sid, ORGID, dt(dstart), dt(dend),
                    f"{dt_hours:.2f}",
                    "OUTAGE" if worktype == "EM" else "OPERATIONAL",
                    dt(report_d), rng.choice(LABOR_BY_SITE[sid])["laborcode"], problem,
                ])

    add_status_history(wonum, sid, hist)
    status_date = hist[-1][1]

    WO_ROWS.append([
        wonum, desc, sid, ORGID, "WORKORDER", worktype, status, dt(status_date),
        asset["assetnum"] if asset else "", loc, "",
        pm["pmnum"] if pm else "", pm["jpnum"] if pm else "", prio,
        dt(report_d, rep_h), rng.choice(LABOR_BY_SITE[sid])["laborcode"],
        dt(targ_start), dt(targ_comp), dt(sched_start), dt(sched_finish),
        dt(act_start, start_h),
        dt(act_finish, _finish_hour(act_start, act_finish, start_h, act_hrs, crew)),
        money(est_hours), money(est_hours), money(est_lab_cost), money(est_mat_cost),
        money(act_hrs), money(act_lab_cost), money(act_mat_cost),
        money(act_tool), money(act_serv), money(downtime),
        f"FC-{asset['cls']}" if (reactive and asset) else "", problem,
        supervisor, rng.choice(LABOR_BY_SITE[sid])["laborcode"],
        f"CREW-{sid[:3]}-{rng.randint(1, 3)}",
        f"MAINT-{sid[:3]}", f"6400-{sid[:3]}-{rng.randint(100, 199)}",
        0, 1 if status == "CLOSE" else 0, "MAXADMIN", dt(status_date),
    ])


def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def add_freq(d, freq, unit, n):
    if unit == "WEEKS":
        return d + timedelta(weeks=freq * n)
    if unit == "DAYS":
        return d + timedelta(days=freq * n)
    # MONTHS
    total = (d.month - 1) + freq * n
    y = d.year + total // 12
    m = total % 12 + 1
    day = min(d.day, 28)
    return date(y, m, day)


def generate_work_orders():
    """PM work from schedules, reactive work from asset failure propensity,
    then the remaining work types to hit each site's reactive-share target."""
    pm_by_site_month = {}

    # ---- 1. PM work orders straight off the PM schedules
    for pm in PMS:
        n = 0
        while True:
            due = add_freq(pm["first"], pm["freq"], pm["unit"], n)
            n += 1
            if due > END_DATE + timedelta(days=45):
                break
            if due < START_DATE:
                continue
            future = due > END_DATE
            report_d = max(START_DATE, due - timedelta(days=pm["leadtime"]))
            make_wo(pm["site"], "PM", report_d, targ_start_in=due,
                    asset=next(a for a in ASSETS_BY_SITE[pm["site"]]
                               if a["assetnum"] == pm["assetnum"]),
                    pm=pm, est_hours=round(pm["dur"] * rng.uniform(0.85, 1.2), 2),
                    crafts=pm["crafts"], force_open=future)
            if not future:
                key = (pm["site"], due.year, due.month)
                pm_by_site_month[key] = pm_by_site_month.get(key, 0) + 1

    # ---- 2. reactive + other work, month by month, hitting share targets
    for sid, cfg in SITES.items():
        assets = [a for a in ASSETS_BY_SITE[sid] if a["status"] == "OPERATING"]
        weights = [a["propensity"] for a in assets]
        cur = date(START_DATE.year, START_DATE.month, 1)
        while cur <= END_DATE:
            month_end = add_freq(cur, 1, "MONTHS", 1) - timedelta(days=1)
            npm = pm_by_site_month.get((sid, cur.year, cur.month), 0)
            if npm == 0:
                cur = add_freq(cur, 1, "MONTHS", 1)
                continue
            lf = lerp_factor(cur)
            r_eff = max(0.10, min(0.62, cfg["reactive_share"] - cfg["drift"] * lf))
            season = seasonal_multiplier(cur, cfg["kind"])
            other_share = 0.14
            denom = max(0.15, 1.0 - r_eff - other_share)
            total = npm / denom
            n_react = int(round(total * r_eff * season))
            n_other = int(round(total * other_share))

            for _ in range(n_react):
                d = cur + timedelta(days=rng.randint(0, (month_end - cur).days))
                if d > END_DATE:
                    d = END_DATE
                a = rng.choices(assets, weights=weights, k=1)[0]
                # emergencies skew to critical assets
                emg = rng.random() < (0.30 if a["criticality"] <= 2 else 0.11)
                make_wo(sid, "EM" if emg else "CM", d, asset=a)

            for _ in range(n_other):
                d = cur + timedelta(days=rng.randint(0, (month_end - cur).days))
                if d > END_DATE:
                    d = END_DATE
                wt = rng.choices(["PDM", "INSP", "PROJ", "SAF"],
                                 weights=[30, 22, 26, 22])[0]
                a = rng.choice(assets) if rng.random() < 0.72 else None
                make_wo(sid, wt, d, asset=a)
            cur = add_freq(cur, 1, "MONTHS", 1)


# ----------------------------------------------------------------------------
# 9. METER READINGS
# ----------------------------------------------------------------------------

def build_meter_readings():
    rows = []
    for a in ASSETS:
        if "meter" not in a:
            continue
        mname, unit = a["meter"]
        step_days = 30 if mname == "RUNHOURS" else 14
        cur = START_DATE + timedelta(days=rng.randint(0, step_days))
        cumulative = rng.randint(2000, 60000)
        # bad actors drift upward on condition meters - gives PdM signal
        drift_per_read = (0.9 if a["bad_actor"] else 0.18)
        i = 0
        while cur <= END_DATE:
            if mname == "RUNHOURS":
                inc = rng.randint(380, 720)
                cumulative += inc
                reading = cumulative
            elif mname == "VIBRATION":
                reading = round(0.08 + i * drift_per_read * 0.004 + rng.uniform(-0.01, 0.02), 3)
            elif mname == "TEMP-BRG":
                reading = round(118 + i * drift_per_read * 0.09 + rng.uniform(-4, 6), 1)
            elif mname == "PRESSURE":
                reading = round(92 + rng.uniform(-8, 8) - i * drift_per_read * 0.02, 1)
            else:  # AMPS
                reading = round(24 + i * drift_per_read * 0.01 + rng.uniform(-1.5, 2.0), 2)
            rows.append([a["assetnum"], a["site"], mname, dt(cur), reading,
                         reading, unit,
                         "ACTUAL", rng.choice(LABOR_BY_SITE[a["site"]])["laborcode"]])
            cur += timedelta(days=step_days)
            i += 1
    emit("METERREADING.csv",
         ["ASSETNUM", "SITEID", "METERNAME", "READINGDATE", "READING", "NEWREADING",
          "MEASUREUNITID", "READINGTYPE", "INSPECTOR"],
         rows, "one row per asset per meter per reading date")


# ----------------------------------------------------------------------------
# 10. DIM_DATE  (NOT a Maximo table - a modelling convenience)
# ----------------------------------------------------------------------------

def build_calendar():
    rows = []
    d = CALENDAR_START
    while d <= CALENDAR_END:
        iso_year, iso_week, iso_dow = d.isocalendar()
        # fiscal year starts 1 October
        fy = d.year + 1 if d.month >= 10 else d.year
        fp = ((d.month - 10) % 12) + 1
        rows.append([
            d.strftime("%Y-%m-%d"), d.year, f"Q{(d.month - 1) // 3 + 1}", d.month,
            d.strftime("%b"), d.strftime("%Y-%m"), f"{d.strftime('%b')} {d.year}",
            iso_week, iso_dow, d.strftime("%a"),
            1 if iso_dow >= 6 else 0, fy, fp,
            1 if d <= END_DATE else 0,
        ])
        d += timedelta(days=1)
    emit("DIM_DATE.csv",
         ["DATE", "YEAR", "QUARTER", "MONTHNUM", "MONTHSHORT", "YEARMONTH",
          "MONTHYEARLABEL", "ISOWEEK", "DAYOFWEEK", "DAYSHORT", "ISWEEKEND",
          "FISCALYEAR", "FISCALPERIOD", "ISPASTORTODAY"],
         rows, "one row per calendar day - NOT a Maximo table, added for the model")


# ----------------------------------------------------------------------------
# 11. VALIDATION - integrity checks and KPI baselines
# ----------------------------------------------------------------------------

def validate():
    import collections
    lines = []
    ok = True

    def chk(label, condition, detail=""):
        nonlocal ok
        mark = "PASS" if condition else "FAIL"
        if not condition:
            ok = False
        lines.append(f"[{mark}] {label}{(' - ' + detail) if detail else ''}")

    wo_idx = {r[0]: r for r in WO_ROWS}
    asset_idx = {a["assetnum"] for a in ASSETS}

    chk("every LABTRANS.WONUM exists in WORKORDER",
        all(r[1] in wo_idx for r in LABTRANS_ROWS))
    chk("every MATUSETRANS.WONUM exists in WORKORDER",
        all(r[1] in wo_idx for r in MATUSE_ROWS))
    chk("every WOSTATUS.WONUM exists in WORKORDER",
        all(r[1] in wo_idx for r in WOSTATUS_ROWS))
    chk("every FAILUREREPORT.WONUM exists in WORKORDER",
        all(r[0] in wo_idx for r in FAILREP_ROWS))
    chk("every DOWNTIMEREPORT.ASSETNUM exists in ASSET",
        all(r[0] in asset_idx for r in DOWNTIME_ROWS))
    chk("every WORKORDER.ASSETNUM (where populated) exists in ASSET",
        all((r[8] == "" or r[8] in asset_idx) for r in WO_ROWS))

    # lifecycle integrity
    bad_dates = [r[0] for r in WO_ROWS
                 if r[20] and r[21] and r[21] < r[20]]
    chk("no work order finishes before it starts", not bad_dates,
        f"{len(bad_dates)} offenders" if bad_dates else "")

    bad_report = [r[0] for r in WO_ROWS if r[20] and r[20] < r[14]]
    chk("no work order starts before it was reported", not bad_report,
        f"{len(bad_report)} offenders" if bad_report else "")

    open_with_finish = [r[0] for r in WO_ROWS
                        if r[6] in ("WAPPR", "APPR", "INPRG") and r[21] != ""]
    chk("no open work order carries an ACTFINISH", not open_with_finish,
        f"{len(open_with_finish)} offenders" if open_with_finish else "")

    pm_with_failure = [r[0] for r in WO_ROWS if r[5] == "PM" and r[33] != ""]
    chk("no PM work order carries a PROBLEMCODE", not pm_with_failure,
        f"{len(pm_with_failure)} offenders" if pm_with_failure else "")

    # cost reconciliation: WORKORDER actuals vs transaction sums
    lab_by_wo = collections.defaultdict(float)
    for r in LABTRANS_ROWS:
        lab_by_wo[r[1]] += float(r[12])
    mat_by_wo = collections.defaultdict(float)
    for r in MATUSE_ROWS:
        mat_by_wo[r[1]] += float(r[10])
    lab_bad = sum(1 for w, r in wo_idx.items()
                  if abs(float(r[27]) - lab_by_wo.get(w, 0.0)) > 0.05)
    mat_bad = sum(1 for w, r in wo_idx.items()
                  if abs(float(r[28]) - mat_by_wo.get(w, 0.0)) > 0.05)
    chk("WORKORDER.ACTLABCOST reconciles to LABTRANS", lab_bad == 0,
        f"{lab_bad} mismatches" if lab_bad else "")
    chk("WORKORDER.ACTMATCOST reconciles to MATUSETRANS", mat_bad == 0,
        f"{mat_bad} mismatches" if mat_bad else "")

    # ---- KPI baselines (use these as DAX test cases)
    lines.append("")
    lines.append("KPI BASELINES - expected values for your DAX to reproduce")
    lines.append("=" * 62)

    def fmt_pct(x):
        return f"{100 * x:.1f}%"

    for sid in list(SITES) + ["ALL SITES"]:
        sel = [r for r in WO_ROWS if (sid == "ALL SITES" or r[2] == sid)]
        sel = [r for r in sel if r[6] != "CAN"]
        total = len(sel)
        reactive = sum(1 for r in sel if r[5] in ("CM", "EM"))
        pms = [r for r in sel if r[5] == "PM"]
        pm_done = [r for r in pms if r[6] in ("COMP", "CLOSE") and r[21]]
        pm_ontime = sum(1 for r in pm_done if r[21][:10] <= r[17][:10])
        open_wo = [r for r in sel if r[6] in ("WAPPR", "APPR", "INPRG")]
        backlog_hrs = sum(float(r[23]) for r in open_wo)
        tot_cost = sum(float(r[27]) + float(r[28]) + float(r[29]) + float(r[30])
                       for r in sel)
        dtr = [r for r in DOWNTIME_ROWS if (sid == "ALL SITES" or r[2] == sid)]
        dt_hours = sum(float(r[6]) for r in dtr)
        fails = len([r for r in FAILREP_ROWS if (sid == "ALL SITES" or r[3] == sid)])
        mttr = (dt_hours / len(dtr)) if dtr else 0.0

        lines.append(f"\n{sid}")
        lines.append(f"  work orders (excl. cancelled) ....... {total:,}")
        lines.append(f"  reactive % (CM+EM / total) ......... {fmt_pct(reactive / total) if total else 'n/a'}")
        lines.append(f"  PM work orders ..................... {len(pms):,}")
        lines.append(f"  PM compliance (done by TARGCOMPDATE) {fmt_pct(pm_ontime / len(pm_done)) if pm_done else 'n/a'}")
        lines.append(f"  open work orders ................... {len(open_wo):,}")
        lines.append(f"  open estimated labour hours ........ {backlog_hrs:,.1f}")
        lines.append(f"  total maintenance cost ............. ${tot_cost:,.0f}")
        lines.append(f"  failure events (FAILUREREPORT) ..... {fails:,}")
        lines.append(f"  downtime events .................... {len(dtr):,}")
        lines.append(f"  downtime hours ..................... {dt_hours:,.1f}")
        lines.append(f"  MTTR (downtime hrs / events) ....... {mttr:.2f} h")

    # bad actors
    cnt = collections.Counter(r[1] for r in FAILREP_ROWS)
    lines.append("\nTOP 10 BAD ACTORS (failure events, all sites)")
    for anum, c in cnt.most_common(10):
        lines.append(f"  {anum:<18} {c:>4} failures")

    lines.append("")
    lines.append(f"OVERALL INTEGRITY: {'ALL CHECKS PASSED' if ok else 'FAILURES PRESENT'}")
    return "\n".join(lines), ok


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    print(f"Synthetic Maximo dataset  |  SEED={SEED}  |  "
          f"{START_DATE} -> {END_DATE}\n")
    build_org_site()
    build_locations()
    build_labor()
    build_items()
    build_failurecodes()
    build_assets()
    build_jobplans_pms()
    print("  generating work orders and transactions ...")
    generate_work_orders()

    emit("WORKORDER.csv", WO_HEADER, WO_ROWS,
         "one row per work order (WONUM); the primary fact table")
    emit("WOSTATUS.csv",
         ["WOSTATUSID", "WONUM", "SITEID", "STATUS", "CHANGEDATE", "CHANGEBY", "MEMO"],
         WOSTATUS_ROWS, "one row per work order status change")
    emit("LABTRANS.csv",
         ["LABTRANSID", "WONUM", "SITEID", "ORGID", "LABORCODE", "CRAFT", "TRANSDATE",
          "STARTDATE", "FINISHDATE", "REGULARHRS", "PREMIUMPAYHOURS", "PAYRATE",
          "LINECOST", "TRANSTYPE", "TASKID"],
         LABTRANS_ROWS, "one row per labour transaction against a work order")
    emit("MATUSETRANS.csv",
         ["MATUSETRANSID", "WONUM", "SITEID", "ORGID", "ITEMNUM", "ITEMSETID",
          "LOCATION", "BINNUM", "QUANTITY", "UNITCOST", "LINECOST", "TRANSDATE",
          "ISSUETYPE"],
         MATUSE_ROWS, "one row per material issue against a work order")
    emit("FAILUREREPORT.csv",
         ["WONUM", "ASSETNUM", "LOCATION", "SITEID", "ORGID", "FAILURECODE",
          "PROBLEMCODE", "CAUSECODE", "REMEDYCODE", "TYPE", "REPORTDATE"],
         FAILREP_ROWS, "one row per reported failure against a work order")
    emit("DOWNTIMEREPORT.csv",
         ["ASSETNUM", "WONUM", "SITEID", "ORGID", "DOWNTIMESTART", "DOWNTIMEEND",
          "DOWNTIME", "TYPE", "REPORTDATE", "REPORTEDBY", "PROBLEMCODE"],
         DOWNTIME_ROWS, "one row per downtime event")
    build_meter_readings()
    build_calendar()

    report, ok = validate()
    print("\n" + report)

    os.makedirs("/home/claude/out", exist_ok=True)
    with open("/home/claude/out/VALIDATION.txt", "w", encoding="utf-8") as fh:
        fh.write(f"Synthetic Maximo dataset validation\n"
                 f"SEED={SEED}  window {START_DATE} -> {END_DATE}\n"
                 f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        fh.write("TABLE MANIFEST\n" + "=" * 62 + "\n")
        for name, n, cols, kb, grain in MANIFEST:
            fh.write(f"{name:<24} {n:>9,} rows  {cols:>3} cols  {kb:>9,.0f} KB  {grain}\n")
        fh.write("\nINTEGRITY CHECKS\n" + "=" * 62 + "\n")
        fh.write(report + "\n")

    total_kb = sum(m[3] for m in MANIFEST)
    print(f"\n  {len(MANIFEST)} tables, {total_kb / 1024:.1f} MB total")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
