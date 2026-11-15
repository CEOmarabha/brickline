# Signal Lab — Testing Creative Lead Ideas Against History

*v1, 2026-11-15. Results: `research/findings/signal-lab-2026-11-15.md` (reproducible: `uv run python research/signal_lab/lab.py`, ~4 seconds).*

## Why this exists

Any idea for "who is about to need a contractor" can be checked against what actually happened in Chicago over the past 10–20 years before we build anything on it. The lab makes that cheap: one function per idea, a standard set of tests, and a leaderboard. Ideas that fail are just as valuable: they stop us from selling leads that don't work.

## How a test works

| Test type | Question | Control |
| --- | --- | --- |
| Same property | After signal X at a property, how often does job Y happen there within N days? | The same property's own earlier window (removes "busy address" bias) |
| Neighborhood (~160 m blocks) | Does activity next door predict yours? | Blocks with no such activity, same dates |
| Area before/after | After a storm, do nearby blocks pull more permits? | Same blocks a year earlier, and all other blocks over the same windows |
| Cohort | Which kinds of buildings generate the most demand? | All residential parcels |

Verdicts: **Strong** = at least 3× baseline with at least 5 signals per week; **Useful** = at least 1.8×; **Weak** = at least 1.25×; **No signal** below that. Permits only capture permitted work, so every conversion rate is a floor.

## Round 1 results (16 hypotheses, 5 new data sources)

New data added to the warehouse: Chicago 311 service requests (1.13M filtered requests since 2015), Chicago Energy Benchmarking (28k building-years), Cook County Assessor residential characteristics (434k Chicago homes: year built, walls, roof, A/C, heat, basement, condition), NOAA Storm Events (1,953 Cook County hail/wind/flood reports with coordinates).

| # | Idea | Verdict | Result | What we do with it |
| --- | --- | --- | --- | --- |
| H08 | 311 "porch inspection request" → porch permit | **Strong** | 13.7% within a year vs 1.2% baseline (11.4×); ~7/week | New porch lead type, earlier than a citation |
| H07 | 311 "building violation" complaint → city citation | **Strong** | 31.6% cited within 120 days (5.9×), **median 32 days before the citation**; ~255/week. Citations that follow: masonry 11%, windows 11%, porch 9%, roofing 4% | Earliest step in the violation chain: a "likely to be cited" lead, a month ahead of competitors watching violations |
| H09 | 311 "vacant/abandoned building" complaint → property sells | **Useful** | 19.4% sell within a year (2.5×); ~20/week | Early entry into the investor-purchase pipeline (rehab GCs, property managers) |
| H01 | 2+ neighbors went solar → you go solar | **Useful** | 1.0% vs 0.4% (2.4×); any solar neighbor: 1.7× | Block-level solar target lists (confounded by income/canvassing, still good for targeting) |
| H13 | Masonry buildings built before 1910 → masonry permits | **Useful** | 1.4%/yr vs 0.5% average (2.9×); 39k buildings | Filter that sharpens masonry mailers and the violation lead score |
| H10 | Complaint about unpermitted work → permit gets pulled | **Useful** | 18.9% within 180 days (2.2×); ~71/week | Niche: expediters, architects |
| H03 | 2+ neighbors re-roofed → you re-roof | **Useful** | 0.7% vs 0.3% per 180 days (2.2×) | Door-hanger blocks for roofers |
| H12 | Roof material × age → reroof | Useful (surprising) | Newest buildings with "other" (often flat) roofs re-roof most; old shingle houses are average | Building age alone is **not** a reroof predictor; don't sell "old house = new roof" |
| H14 | No central A/C → HVAC permits | Refuted | Homes *with* central A/C pull more permits (replacements, 2.2×); no-A/C homes are below average | Don't target "no A/C" homes for HVAC |
| H15 | Assessor condition rating → renovation | Weak | 1.4× | Not worth using |
| H02 | New roof → solar within 2 years | No signal | 1.2× | Drop |
| H16 | Low ENERGY STAR score → HVAC/electrical upgrades | No signal | 17.7% vs 16.4% | Drop for now (large buildings retrofit regardless of score) |
| H04 | Hail ≥ 1 inch → reroof wave | No signal | Near/far permit ratios equal | See "why the storm tests failed" |
| H05 | Damaging wind → reroof wave | No signal | Same | Same |
| H06 | 311 "water in basement" → plumbing permit | No signal | 0.5% vs 0.6% | Citywide sewer backups; repairs are mostly unpermitted |
| H11 | Lead test kit request → plumbing permit | No signal | 0.6% vs 0.9% | Lead lines are replaced under the Water Department, not building permits |

### Why the storm tests failed (and how to retest)

NOAA's Storm Events are spotter **points** with coordinates rounded to ~1 km, and hail damage is often repaired through insurance without a permit spike we can see. A fair retest needs **radar-derived hail swaths** (NOAA's Severe Weather Data Inventory "MESH" grids) and, ideally, a target beyond permits (e.g., a roofer client's own lead and job data). Until then, no "storm leads" in the product.

## Next ideas to test (ranked by value × ease)

| # | Idea | Data | Who it's for | Ease |
| --- | --- | --- | --- | --- |
| N1 | 311 "building violation" complaint → *which* trade (learn from complaint text where available, address history, building type) | 311, violations, assessor | All repair trades | Easy |
| N2 | Chained score: complaint → citation → permit, with timing (when to mail) | 311, violations, permits | Porch, masonry | Easy |
| N3 | Repeat investors: which ones renovate fast, and which GCs they use | Sales, permits | Rehab GCs | Easy |
| N4 | Radar hail swaths (MESH) → reroof and siding permits | NOAA SWDI | Roofers | Medium |
| N5 | Tree emergencies / storm debris (311) → tree service and roof repair | 311 | Tree services, roofers | Easy (data loaded) |
| N6 | Rodent complaints (311) near restaurants → pest-control accounts | 311, food inspections | Pest control | Easy (data loaded) |
| N7 | New business license in a space with no recent build-out permit → cleaning, security, signage | Licenses, permits | B2B services | Easy |
| N8 | Home-improvement mortgages by census tract (HMDA) → neighborhood demand index | CFPB HMDA | All residential trades | Medium |
| N9 | Rooftop solar potential (Google Solar API / building footprints) × neighbors going solar | Google Solar API (key + cost), footprints | Solar | Medium, paid |
| N10 | Street-level imagery of roof/porch condition (computer vision) | Street View API (paid, terms) | Roofers, porch | Hard; check terms first |
| N11 | Tax-bill stress (appeals, tax sale lists) → distressed owners → sales | Cook County | Investors' contractors | Medium |
| N12 | Contractor license or insurance lapses → GCs needing new subs | City/State licensing | Commercial subs | Medium |

**How to propose an idea:** describe it in one line ("X happens → Y follows"), and the lab can usually test it the same day if the data is public.

## How winners reach the product

1. Add the signal to `engine/leads/snapshot.py` as a lead type with its historical rate and timing.
2. Add it to the backtests (`research/backtests`) so it's re-validated whenever data refreshes.
3. Show it in the client app with its evidence and the "why" sentence.
4. Measure real close rates in Results; drop it if pilots don't convert.

Round-1 winners queued for the product: H07 (complaint → citation), H08 (porch inspection requests), H09 (vacant complaint → sale), H13 (masonry age filter), H01/H03 (block lists for solar and roofing).
