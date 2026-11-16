"""Role pages, rebuilt around each audience's top questions.
PM & Compliance v8 (compliance lead), Reliability v8 (reliability engineer), Planning v7 (planner).
Figures: pages_numbers.json, exec_numbers.json (via gen_pages) + roles_numbers.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pages as gp
g = gp.g
P, F, D = gp.P, gp.F, gp.D
RN = json.load(open(os.path.join(HERE, "roles_numbers.json")))
SITE, NAME = gp.SITE, gp.NAME
GREEN, AMBER, RED, MUT, FAINT, TXT, MONO, GLY = gp.GREEN, gp.AMBER, gp.RED, gp.MUT, gp.FAINT, gp.TXT, gp.MONO, gp.GLY
S3 = ["HOUSTON", "AURORA", "BEDFORD"]
kpi, page, linechart, bar = gp.kpi, gp.page, gp.linechart, gp.bar
NOB = '<div class="bullet none"></div>'

def split_bar(vals, tot):
    segs = "".join(f'<i style="width:{vals[s] / tot * 100:.1f}%;background:{SITE[s]}{";box-shadow:0 0 10px " + SITE[s] if i == 0 else ""}"></i>' for i, s in enumerate(S3))
    lab = " &middot; ".join(f'<span style="color:{SITE[s]}">{NAME[s]} {vals[s]}</span>' for s in S3)
    return f'<div class="stk" style="height:10px;margin-top:16px">{segs}</div><div class="kv" style="margin-top:8px">{lab}</div>'

def hero(label, num, extra):
    return f'<div class="kpi hero"><div class="klabel">{label}</div><div class="kmid"><div class="knum">{num}</div></div>{extra}</div>'

STATUS = {"WAPPR": ("awaiting approval", AMBER), "APPR": ("not started", "#A1A1AA"), "INPRG": ("in progress", "#93C5FD")}

# =====================================================================
# PM & COMPLIANCE v8 - compliance lead: what is overdue NOW, what is due next, is it improving, what keeps slipping
# =====================================================================
C, pm, A = RN["comp"], P["pm"], F["ALL"]
so, sd = C["stat"]["overdue"], C["stat"]["due30"]
so_t, sd_t = sum(so.values()), sum(sd.values())
po, pd_ = C["pm"]["overdue"], C["pm"]["due30"]
po_t = sum(po.values())
k = "".join([
    hero("Statutory jobs overdue today", f'{so_t}', split_bar(so, so_t)),
    kpi("Statutory due in next 30 days", f'{sd_t}', "", NOB, f'{GLY[AMBER]} Houston {sd["HOUSTON"]}', AMBER, None, ""),
    kpi("PMs overdue today", f'{po_t}', "", NOB, f'Houston {po["HOUSTON"]}', MUT, None, ""),
    kpi("Statutory on time", f'{A["stat"]:.1f}%', "target 100%", g.bullet(A["stat"], 0, 100, 100, RED),
        f'{GLY[RED]} {A["stat_late"]} finished late', RED, None, ""),
    kpi("PM compliance", f'{A["pm"]:.1f}%', "target 90%", g.bullet(A["pm"], 0, 100, 90, AMBER),
        f'{GLY[AMBER]} &minus;{90 - A["pm"]:.1f} pts', AMBER, None, ""),
])
# overdue list
cols = "86px 168px minmax(0,1fr) 54px 150px 110px"
ol = f'<div class="rl rh" style="grid-template-columns:{cols}"><span>WO</span><span>ASSET</span><span>TASK</span><span>TYPE</span><span>STATUS</span><span style="text-align:right">DAYS OVERDUE</span></div>'
mxd = C["stat_list"][0]["days"]
for r in C["stat_list"][:5]:
    stl, stc = STATUS[r["status"]]
    asset = r["asset"] if r["asset"] not in (None, "nan", "NaN") and r["asset"] == r["asset"] else "location only"
    ol += (f'<div class="rl" style="grid-template-columns:{cols}"><span class="mono2 dim">{r["wo"]}</span>'
           f'<span class="mono2"><span class="dot" style="background:{SITE[r["site"]]};margin-right:8px"></span>{asset}</span>'
           f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r["desc"]}</span>'
           f'<span class="chip" style="justify-self:start">{r["type"]}</span>'
           f'<span class="mono2" style="color:{stc}">{stl}</span>'
           f'<span style="text-align:right"><span class="mono2" style="color:{RED};font-weight:600">{r["days"]} d</span>{bar(r["days"] / mxd * 100, RED, False)}</span></div>')
# where is it piling up
BK = ["#FDE68A", AMBER, RED]
pile = ""
mxo = max(so.values())
for s in S3:
    b = C["stat"]["overdue_buckets"][s]
    segs = "".join(f'<i style="width:{x / so[s] * 100:.1f}%;background:{BK[j]}"></i>' for j, x in enumerate(b) if x)
    pile += (f'<div style="display:grid;grid-template-columns:96px 1fr 70px 70px;column-gap:14px;align-items:center;margin-top:20px">'
             f'<span style="font-size:15px"><span class="dot" style="background:{SITE[s]};margin-right:8px;box-shadow:0 0 6px {SITE[s]}"></span>{NAME[s]}</span>'
             f'<div class="stk" style="height:16px;width:{so[s] / mxo * 100:.1f}%">{segs}</div>'
             f'<span style="text-align:right;font-size:24px;font-weight:600;color:{RED}">{so[s]}</span>'
             f'<span style="text-align:right;font-size:24px;font-weight:600;color:{AMBER}">{sd[s]}</span></div>')
pile = (f'<div class="kv" style="display:grid;grid-template-columns:96px 1fr 70px 70px;column-gap:14px;margin-top:14px">'
        f'<span></span><span></span><span style="text-align:right">overdue</span><span style="text-align:right">due 30 d</span></div>' + pile
        + f'<div class="kv" style="margin-top:22px;display:flex;gap:16px"><span>days overdue:</span><span><i class="sw" style="background:{BK[0]}"></i>1&ndash;7</span>'
          f'<span><i class="sw" style="background:{BK[1]}"></i>8&ndash;30</span><span><i class="sw" style="background:{BK[2]}"></i>31+</span></div>')
# trend: statutory on-time by quarter
ql = [q.replace("20", "", 1).replace("Q", " Q") for q in C["stat_q_labels"]]
ser = [(NAME[s], SITE[s], C["stat_q"][s], True) for s in S3]
c1 = linechart(ser, ql, (60, 106), [60, 70, 80, 90, 100], 1030, 230, target=100, tlabel="target 100%", tick_every=2)
# slipping schedules, condensed
cols2 = "minmax(0,1fr) 120px"
ws = f'<div class="rl rh" style="grid-template-columns:{cols2}"><span>PM SCHEDULE</span><span>LATE</span></div>'
for w in pm["worst_pms"][:4]:
    ws += (f'<div class="rl" style="grid-template-columns:{cols2}"><span><span class="mono2"><span class="dot" style="background:{SITE[w["site"]]};margin-right:8px"></span>{w["pm"]} &middot; {w["asset"]}</span>'
           f'<div class="kv" style="margin:3px 0 0 16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{w["desc"]} &middot; every {w["freq"]}</div></span>'
           f'<span><span class="mono2" style="color:{RED}">{w["late"]} of {w["n"]}</span>{bar(w["late"] / w["n"] * 100, RED, False)}</span></div>')
body = f'''<div class="g2" style="grid-template-columns:1fr 470px">
 <div class="c" style="height:326px"><div class="ch"><div><div class="cq">What statutory work is overdue right now?</div><div class="cs">open inspection + safety jobs past target date &middot; oldest first</div></div><span class="lk">All {so_t} &#8594;</span></div>{ol}</div>
 <div class="c" style="height:326px"><div class="cq">Where is it piling up?</div><div class="cs">statutory jobs overdue today vs due in the next 30 days</div>{pile}</div>
</div>
<div class="g2" style="grid-template-columns:1fr 470px">
 <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Is statutory compliance improving?</div><div class="cs">inspection + safety jobs finished on time, by quarter</div></div></div>{c1}</div>
 <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Which PM schedules keep slipping?</div><div class="cs">schedules with 12+ runs &middot; all at Houston</div></div><span class="lk">All {pm["pm_sched_below_80"]} &#8594;</span></div>{ws}</div>
</div>'''
oldest = C["stat_list"][0]
o1 = page("PM &amp; Compliance", "PM &amp; Compliance", "open work as of 29 Jul 2026",
          f'<b>{so_t} statutory jobs are overdue today &mdash; {so["HOUSTON"]} at Houston.</b> The oldest, an emergency-stop repair, is {oldest["days"]} days late and still waiting for approval.',
          k, body, "pm_compliance_v8.html")

# =====================================================================
# RELIABILITY v8 - reliability engineer: light edit, bad actors carry their cost
# =====================================================================
rl, R = P["rel"], RN["rel"]
cm = R["cost_map"]
top45 = R["top45_cost_share"] / 100 * R["react_cost_total"]
k = "".join([
    kpi("Failures from 5% of assets", f'{rl["bad_share"]:.1f}%', f'{rl["bad_k"]} of {rl["n_assets"]} assets', NOB,
        f'{GLY[RED]} bad actors, all sites', RED, None, "", hero=True).replace(
        '<div class="kmid"><div class="knum">' + f'{rl["bad_share"]:.1f}%' + '</div>',
        '<div class="kmid"><div class="knum">' + f'{rl["bad_share"]:.1f}%' + '</div>' + gp.pareto()),
    kpi("Reactive cost, worst 45 assets", f'${top45 / 1e6:.1f}M', "3 years", NOB,
        f'{R["top45_cost_share"]:.0f}% of ${R["react_cost_total"] / 1e6:.1f}M', MUT, None, ""),
    kpi("MTTR", f'{rl["mttr"]["ALL"]:.1f}<small>h</small>', "", NOB,
        f'Bedford {rl["mttr"]["BEDFORD"]:.1f} &middot; Houston {rl["mttr"]["HOUSTON"]:.1f}', MUT, None, ""),
    kpi("Downtime", f'{rl["dt_hours"]["ALL"] / 1000:.0f}k<small>h</small>', "", NOB,
        f'Houston {rl["dt_hours"]["HOUSTON"] / rl["dt_hours"]["ALL"] * 100:.0f}% of it', MUT, None, ""),
    kpi("MTBF", f'{A["mtbf"]:,.0f}<small>h</small>', "", NOB, "provisional", MUT, g.ser("ALL", "mtbf"), "#A1A1AA", mr=600),
])
cols3 = "minmax(0,1fr) 44px 92px 64px"
ba = f'<div class="rl rh" style="grid-template-columns:{cols3}"><span>ASSET</span><span>CRIT</span><span>FAILS / QTR</span><span style="text-align:right">COST</span></div>'
for t in rl["top"]:
    c_ = cm.get(t["asset"], 0)
    ba += (f'<div class="rl" style="grid-template-columns:{cols3};padding:10px 0">'
           f'<span><span class="mono2"><span class="dot" style="background:{SITE[t["site"]]};margin-right:8px"></span>{t["asset"]}</span>'
           f'<div class="kv" style="margin:3px 0 0 16px;white-space:nowrap">{t["fails"]} failures &middot; {t["dt"]:,.0f} h down</div></span>'
           f'<span class="chip" style="justify-self:start">{t["crit"]}</span>'
           f'{g.spark(t["q"], 88, 30, RED, dom=(0, 17))}'
           f'<span class="mono2" style="text-align:right;color:{RED}">${c_ / 1000:.0f}k</span></div>')
# reuse the v7 reliability body, swapping only the bad-actor card and KPI row
v7 = open(os.path.join(g.OUT, "reliability_v7.html"), encoding="utf-8").read()
body_start = v7.index('<div class="g2"')
body = v7[body_start:v7.rindex("</div></main>")]
ba_old_start = body.index('<div class="rl rh" style="grid-template-columns:minmax(0,1fr) 64px 92px 54px">')
ba_old_end = body.rindex("</div>\n</div>")
body = body[:ba_old_start] + ba + body[ba_old_end:]
body = body.replace("quarterly failures, 3 yrs", "cost = reactive WOs, 3 yrs")
o2 = page("Reliability", "Reliability", "Jul 2023 &ndash; Jul 2026",
          f'<b>{rl["bad_k"]} assets cause {rl["bad_share"]:.0f}% of failures</b> &mdash; and their condition meters have drifted {rl["drift_bad"][-1] - 100:.0f}% above baseline.',
          k, body, "reliability_v8.html")

# =====================================================================
# PLANNING v7 - planner: is the work ready, are we hitting the schedule, can the crew keep up
# =====================================================================
pl, PN = P["plan"], RN["plan"]
tot, toth = PN["status_all_tot"], PN["status_all_tot_hrs"]
sc = PN["sched12"]
scol = GREEN if sc["ALL"] >= 90 else AMBER if sc["ALL"] >= 80 else RED
aged = pl["age"]["ALL"][2] + pl["age"]["ALL"][3]
k = "".join([
    kpi("Backlog", f'{pl["weeks"]["ALL"]:.1f}<small>wks</small>', "healthy 4&ndash;6 wks",
        g.bullet(pl["weeks"]["ALL"], 0, 12, 6, AMBER, band=(4, 6)).replace("#4ADE8040", "#4ADE8030"),
        f'{GLY[AMBER]} top of the healthy band', AMBER, None, "", hero=True),
    kpi("Jobs started on schedule", f'{sc["ALL"]:.1f}%', "target 90%", g.bullet(sc["ALL"], 0, 100, 90, scol),
        f'{GLY[scol]} Houston {sc["HOUSTON"]:.0f}%', scol, None, ""),
    kpi("Ready to schedule", f'{tot[0]:,}', "approved", NOB, f'{toth[0]:,} h of work', MUT, None, ""),
    kpi("Waiting for approval", f'{tot[1]:,}', "", NOB, f'{GLY[AMBER]} {toth[1]:,} h stuck', AMBER, None, ""),
    kpi("Open over 90 days", f'{aged}', f'of {pl["open"]["ALL"]:,}', NOB, f'{aged / pl["open"]["ALL"] * 100:.1f}% of backlog', MUT, None, ""),
])
STC = ["#D4D4D8", AMBER, "#60708A"]
bw = ""
for s in S3:
    wv = pl["weeks"][s]
    col = GREEN if 4 <= wv <= 6 else AMBER if wv < 4 else RED
    word = "in band" if 4 <= wv <= 6 else "low" if wv < 4 else "over"
    a = PN["status_all_hrs"][s]; t_ = sum(a)
    segs = "".join(f'<i style="width:{x / t_ * 100:.1f}%;background:{STC[j]}"></i>' for j, x in enumerate(a) if x)
    bw += (f'<div style="display:grid;grid-template-columns:150px 1fr 140px;column-gap:20px;align-items:center;margin-top:22px">'
           f'<span style="font-size:15px"><span class="dot" style="background:{SITE[s]};margin-right:8px;box-shadow:0 0 6px {SITE[s]}"></span>{NAME[s]}</span>'
           f'<div>{g.bullet(wv, 0, 12, 6, col, band=(4, 6))}<div class="stk" style="height:6px;margin-top:12px">{segs}</div></div>'
           f'<span style="text-align:right"><span style="font-size:22px;font-weight:500;color:{col}">{wv:.1f}</span> <span class="kv">wks &middot; {word}</span>'
           f'<div class="kv">{pl["open"][s]:,} WOs &middot; {pl["cap"][s]:,} h/wk</div></span></div>')
bw += (f'<div class="kv" style="margin-top:20px;display:flex;gap:16px;padding-left:170px"><span>open hours by status:</span>'
       + "".join(f'<span><i class="sw" style="background:{STC[j]}"></i>{l}</span>' for j, l in enumerate(["ready", "waiting for approval", "in progress"])) + "</div>")
roll = lambda v: [round(sum(v[max(0, i - 2):i + 1]) / len(v[max(0, i - 2):i + 1]), 1) for i in range(len(v))]
ser = [(NAME[s], SITE[s], roll(PN["sched_m"][s]), True) for s in S3]
c2 = linechart(ser, PN["sched_months"], (50, 100), [50, 60, 70, 80, 90, 100], 1000, 236, target=90, tlabel="target 90%", fmt="{:.0f}%")
body = f'''<div class="g2" style="grid-template-columns:1fr 520px">
 <div class="col">
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">How many weeks of work is waiting &mdash; and is it ready?</div><div class="cs">open estimated hours &divide; crew capacity (assumed) &middot; healthy band 4&ndash;6 weeks</div></div></div>{bw}</div>
  <div class="c" style="height:326px"><div class="ch"><div><div class="cq">Are we starting work when we planned?</div><div class="cs">planned jobs started within 2 days of scheduled start &middot; 3-month rolling average</div></div></div>{c2}</div>
 </div>
 <div class="c" style="height:666px"><div class="ch"><div><div class="cq">Which crafts are the bottleneck?</div><div class="cs">all sites</div></div></div>{gp.cf}</div>
</div>'''
o3 = page("Planning", "Planning", "open work as of 29 Jul 2026",
          f'<b>Houston starts only {sc["HOUSTON"]:.0f}% of its jobs on schedule</b> and carries {pl["weeks"]["HOUSTON"]:.0f} weeks of backlog. {tot[1]:,} jobs are still waiting for approval.',
          k, body, "planning_v7.html", years=False)
print(o1, o2, o3, sep="\n")
