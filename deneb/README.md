# Deneb visual library

Chart techniques catalogued for this report, with the Maximo question each one
answers and the data shape it needs. Sourced by reading the public Deneb /
Vega-Lite showcases listed at the bottom.

Status legend: **ported** = spec in this folder, wired to our model ·
**planned** = chosen for a page, not yet authored · **candidate** = catalogued
for later.

---

## Ported

Authored against this model. **Untested in Deneb** — there is no Vega runtime in
the build environment, so each spec is valid JSON and structurally sound but has
not been rendered. Paste, check, and fix field names against the actual dataset.

| Spec | Page | Dataset it needs |
|---|---|---|
| `p1-kpi-card-bullet-sparkline.json` | 1 | One row per month; Month, Series, Metric, ValueLabel, TargetLabel, DeltaLabel, Actual, Target, ScaleMax, StatusColour |
| `p1-pareto-downtime-by-mode.json` | 1 | Mode, DowntimeHours — rank, share and cumulative computed in-spec |
| `p1-site-scorecard-heatmap.json` | 1 | **Unpivoted**: SiteName, Metric, MetricOrder, ValueLabel, Status |
| `p2-pm-compliance-trend.json` | 2 | Month, SiteName, PMCompliance — feed with PM Compliance % (by Due Date) |
| `p2-statutory-by-discipline.json` | 2 | Discipline, Completed, OnTime |
| `p2-schedule-tolerance-curve.json` | 2 | ToleranceDays 0–10, Compliance — needs a disconnected day table |

## Planned — chosen for the Executive Overview options

| Chart | Source pattern | Answers | Data shape | Notes |
|---|---|---|---|---|
| **Bullet chart** | alexbadiu · Bullet Chart | How far is each KPI from target? | measure, target, qualitative bands | Replaces KPI cards entirely in Option B |
| **IBCS variance row** | HarshJoshi · IBCS Multi-Tier; alexbadiu · Variance Analysis | Actual vs target vs prior, with variance | actual, target, variance, 12-pt series | The business-standard look |
| **Sparkline** | thysvdw · Sparklines | 12-month shape of each KPI, inline | date, value, per metric | Embedded in the IBCS table |
| **Slope chart** | PowerBI-tips · Slope Chart with Labels | Which way is each site moving? | category, two periods, value | 3 sites, 2024 → 2026 |
| **Waterfall** | alexbadiu · Waterfall with Period Variance; PowerBI-tips · Enhanced Waterfall | Where does the maintenance spend go? | component, delta, running total | Labour / material / tool / service |
| **Quadrant scatter** | alexbadiu · Performance Quadrants | Where does each site sit on two KPIs at once? | x, y, size, colour, label | PM compliance × reactive %, bubble = volume |
| **Dumbbell** | PowerBI-tips · Fancy Dumb Bell | What changed between two periods? | category, value_start, value_end | Pairs with the slope chart |
| **Beeswarm** | PBI-David · S&P Beeswarm | How is failure concentrated across the asset base? | one row per asset, value, colour | Shows the 5% bad-actor tail |
| **Violin / box** | alexbadiu · Violin Plot with Box Plot | How long do repairs *actually* take? | one row per downtime event | MTTR mean hides a long tail |
| **Calendar heatmap** | PBI-David · Calendar Heatmap; thysvdw · Calendar View | When does work land? | date, value | Seasonality and weekend effects |

## Candidates — catalogued, not yet assigned

| Chart | Source | Possible use |
|---|---|---|
| Marimekko / Mekko | PBI-David | Work mix by site, bar width = work order volume |
| Gantt | PBI-David; PowerBI-tips `simple_gantt_chart` | Upcoming PM schedule |
| Sankey | PBI-David | Work order status flow — **needs a WOSTATUS history fact we do not model yet** |
| Bump chart | shadfrigui · Premier League Predictions | Site ranking over time |
| Comet / tadpole | PowerBI-tips · Comet Chart; thysvdw · Tadpole | Movement with a trail, alternative to slope |
| Lollipop | PowerBI-tips · Fanciful Lollipop | Lighter ranking than bars |
| Heatmap with marginal bars | alexbadiu; PowerBI-tips | Site × KPI scorecard with row/column totals |
| Trellis dot plot / small multiples | PowerBI-tips · Trellis Dot Plot | Site × KPI grid |
| Ridgeline | PowerBI-tips · Ridgeline Independent | Days-to-complete distribution by site |
| Waffle / unit chart | PBI-David | Reactive vs planned share, countable |
| Linear gauge with performance zones | alexbadiu | Compact alternative to bullet |
| Horizon chart | powerofbi | Dense multi-site trend in little vertical space |
| Burndown | thysvdw | Backlog burn-down against capacity |

## Techniques worth stealing regardless of chart type

| Technique | Source | Why it matters here |
|---|---|---|
| Grey track rail behind bars | EHS `Who leads on prevention` | Bars read against a fixed scale |
| Target rule drawn inside the plot | EHS `Where does each site earn its points` | Benchmark needs no legend |
| End-of-line value labels | EHS `How does this site trend` | Kills legend-hunting on multi-line charts |
| Secondary metric as a text column | EHS `Who leads on prevention` | Two numbers per row without a table |
| `luminance()` for label colour | Giammaria · luminance | Readable labels on graded cells |
| Dynamic data labels (hide/truncate on space) | Giammaria · dynamic-data-labels | Labels that survive resizing |
| Word wrapping via monospace transform | Giammaria · word-wrapping | Long asset descriptions |
| Light/dark mode via params | Giammaria · light-dark-mode | If we ever ship a dark theme |

---

## Sources read

- https://github.com/PBI-David/Deneb-Showcase — 29 visuals; calendar heatmap, beeswarm, mekko, sankey, gauge, waffle, variance
- https://github.com/alexbadiu-insightsinmotion/PBI-Documentation/tree/main/Components/Deneb — 17 business components; bullet, gauges, quadrants, violin, waterfall, IBCS
- https://github.com/PowerBI-tips/Deneb-Templates — 60 templates; slope, dumbbell, comet, lollipop, waterfall, ridgeline, trellis
- https://github.com/HarshJoshi1997/Deneb_Custom_Visualizations — 16 IBCS-style business charts
- https://github.com/Giammaria/Vega-Lite-Techniques — 9 technique demos (labels, luminance, wrapping, theming)
- https://github.com/Giammaria/Vega-Visuals — hierarchical gantt, radial combo, circle packing, brushing
- https://github.com/shadfrigui/vega-lite — waterfall, bump, variance, population pyramid, maps
- https://github.com/Flynnxx1/Deneb-Vega-Showcase — KPI cards, voronoi, maps
- https://github.com/PBI-DataVizzle/Deneb — ActualVsBudget, IBCS, heatmaps
- https://kerrykolosko.com/ — smoothed lines, lasagna plots, proportional data bars, SVG design
- https://thysvdw.github.io/ — sparklines, bullet, tadpole, calendar, burndown, rank chart
- https://data-vogue.com/ — waterfall, IBCS formatting, KPI cards, responsive tiles
- https://www.powerofbi.org/deneb-and-vega-in-power-bi/ — Vega vs Vega-Lite trade-offs, small multiples, interaction model
