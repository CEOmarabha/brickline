# Signal Lab — Testing Creative Lead Ideas Against History

*v3, 2026-11-15 (28 hypotheses). Results: `research/findings/signal-lab-2026-11-15.md` (reproducible and deterministic: `uv run python research/signal_lab/lab.py`, ~10 seconds; two runs produce byte-identical output).*

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

## Round 2 results (6 hypotheses, same data)

Verdict rules are unchanged. H21 and H22 are descriptive (no single baseline), so they carry no verdict.

| # | Idea | Verdict | Result | What we do with it |
| --- | --- | --- | --- | --- |
| H17 | Complaint chain: 311 building complaint → porch/masonry citation → porch/masonry permit | **Strong** (see caveat) | Of 88,647 complaints (mid-2018 to Oct 2025), 17.6% got a porch or masonry citation within 120 days; those addresses pulled a porch/masonry permit within a year of the complaint 12.3% of the time (2.0% in the same address's earlier window, 6.3×) against **4.5%** for complaints with no such citation. Timing: complaint → citation median **33 days**; citation → permit median **172 days** (middle half 97–257); complaint → permit median 197 days. Porch citations convert 11.8%, masonry 10.0% | Confirms the chain is real and slow. The permit usually lands about 5½ months after the citation, so follow-ups need to extend past week 12 (see "Product implications"). The 6.3× is inflated because the cohort is chosen on the citation; the complaint-day view is that about 5.9% of all building complaints reach a porch/masonry permit within a year (2.2% through a citation, 3.7% without one) |
| H20 | 311 rodent complaint → any building violation at the same address within 180 days | Weak | 1.9% vs 1.5% (1.31×); ~545/week; pest/sanitation violations specifically: 0.11% vs 0.06% | Not a lead. Restaurant-inspection version untested: food inspections are not in the warehouse (add the Chicago Food Inspections dataset to test it) |
| H19 | 311 "tree emergency" → roofing or porch permit at the same address within 180 days | No signal | 0.51% vs 0.51% (1.00×); season-matched control (same 180 days a year earlier) 0.99×; roofing alone 0.31% vs 0.34%, porch 0.24% vs 0.22%; ~405/week | Drop. A storm-damage proxy at the address level does not produce permits (insurance repairs, parkway trees, unpermitted patching). Same conclusion as the hail and wind tests |
| H18 | Repeat investors (3+ purchase dates in 24 months) vs one-off company buyers: any permit within a year | No signal (0.90×) | 32.3% vs 36.0%; median days to first permit 96 vs 96; 1,513 repeat buyers, ~15 purchases/week. By size: 2 purchases 34.5%, 3–5 34.6%, 6+ 30.1%. Loyalty: **55.7%** of repeat buyers' permits (2,201, 486 buyers) named a GC the buyer had already used on another property, against 0.3% expected if GCs were picked at random | Repeat buyers are not faster or likelier to renovate, so repeat status does not raise a lead's probability. The loyalty is the finding: once a repeat investor has a GC, more than half of later jobs go back to the same GC, so the opening is the first or second job, not the fifth. Keep "repeat investor" as a *who to call* flag for rehab GCs (volume of future work), not a probability boost |
| H21 | New food license at an address with no renovation/new-construction permit in the prior 2 years ("as-is takeover") vs one with a recent build-out | Descriptive | As-is takeovers (7,534 licenses, ~14/week): any permit within a year **12.1%**, signs 4.6%, MEP trades 5.5%, build-out 2.4%, median 132 days. Licenses that followed a build-out (3,065): 51.7% any permit, signs 26.3%, build-out 25.7%, median 36 days | Takeovers rarely trigger a build-out (2.4% in a year) or even a sign permit (4.6%). Do not sell "new restaurant, no permit" as a build-out lead. The cleaning/security/service demand it implies is not visible in permits; it needs a pilot with a service client to measure |
| H22 | Seasonality: when permits are pulled, and citation → permit timing by month | Descriptive | Porch, masonry and roofing permits peak **Aug–Oct** (porch 9.9% / 9.0% / 10.0% of the year, masonry 10.5% / 9.5% / 10.2%, roofing 10.3% / 9.2% / 10.4%) and bottom out **Dec–Feb** (porch 6.4–7.1%, masonry 5.3–5.6%, roofing 5.1–7.0%). Citations convert to a permit within a year at 13.7–15.6% whatever the month; median days to permit: 170–182 for citations issued Jan–Jul, 187–203 for Aug–Dec | Mail every week; do not pause by season. Citations are issued all year and convert at the same rate, but jobs are *started* (permits issued) mostly Mar–Oct, so winter-cited owners are mostly a spring job: keep them on the follow-up schedule rather than assuming they went cold |

**Reading the caveats.** H17 selects complaints by what happened afterwards (a citation within 120 days), so its lift measures the chain, not a forecast made on complaint day. H18 identifies buyers by name string (the sales feed truncates names and investors use one LLC per building), so portfolio operators are undercounted; units are single-parcel deeds. H19 and H20 use the address on the 311 ticket, which is often the parkway or alley, not the building. H21's food-license table has no license type, so ownership changes look like new businesses. All permit rates are floors.

### Product implications

- **Follow-up cadence (adopted).** Citation → permit takes a median 172 days (middle half 97–257, i.e. weeks 14–37), so lead actions now say "follow up at weeks 6, 12 and 24", and owners with an open citation should stay on the list for up to a year.
- **Complaint-lead trade mix.** After a complaint, 17.6% reach a porch/masonry citation and about 6% a porch/masonry permit within a year, so complaint leads should keep being offered to repair trades generally (H07) and not be sold as porch/masonry-specific.
- **Drop storm-proxy and rodent leads.** H19 and H20 do not support any new lead type.
- **Repeat investors.** Show repeat-investor purchases as a relationship opportunity for rehab GCs (an investor tends to reuse its GC), not as higher-probability leads.
- **Seasonal capacity.** Contractors should expect most permitted starts between March and October; pitch winter pilots as "get on the spring schedule".

## Round 3 results (6 hypotheses, 4 new data sources)

New data added to the warehouse: Chicago Food Inspections since 2016 (199,317 inspections, 139,502 at restaurants, with keyword flags on the violation text for pests, plumbing, ventilation/hood and cleaning), CFPB HMDA home-improvement loans for Cook County 2018–2025 (39,104 loans, 15,596 in Chicago tracts), Chicago census tract boundaries (2010 and 2020 vintages), and NOAA SWDI NEXRAD hail detections for the Chicago area 2016–2026 (3,239 cell detections). All sources were reachable; see `docs/data-source-registry.md`.

**Method for the restaurant tests (H23–H26).** A signal is one restaurant inspection (Pass, Pass w/ Conditions or Fail; "Out of Business" for H26) showing the condition, with none at the same key in the previous window. The comparison group is ordinary restaurant inspections without the condition, one per key per window, with the conversion rate **standardized to the signal group's inspection-type mix** (routine canvass, complaint, pre-opening license, re-inspection), because pre-opening license inspections and complaints have very different starting points. Lift is signal conversion divided by that matched rate. Permits and licenses are matched on street address, so another tenant's or the landlord's work counts for both groups.

| # | Idea | Verdict | Result | What we do with it |
| --- | --- | --- | --- | --- |
| H26 | Restaurant "Out of Business" inspection result → new retail food license at the address (different business name) within 365 days | **Strong** | 32.3% vs 3.2% for ordinary inspections (**10.2×**); 7,943 closures, ~13/week; stable by year (29–37%). But the median is only **19 days** (middle half 6–112) and 58% of the conversions land inside 30 days, so the usable lead time is short. Counting only licenses issued 31+ days after the closure: **15.0% vs 3.0% (5.0×)**, median 154 days (82–252). Any new license including the same name: 43.0% vs 4.8% | Build a "closed restaurant space" list (about 13/week) for build-out contractors, equipment dealers, brokers and signage: an address that just lost its restaurant gets a new food business about one time in three and a build-out-window opportunity one time in seven. Pitch it as a pilot list, not a modelled chance of work (see the renovation row) |
| H26 (permit view) | Same closures → renovation, build-out or new-construction permit at the address within 365 days | Weak | 11.0% vs 6.2% (1.78×), median 113 days (middle half 40–210) | The permit follow-through is modest: most re-lets are as-is or use a license without a permit. Quote the license rate for turnover, not a permit rate, in any pitch |
| H23 | Restaurant pest violation → another pest violation at the same license within 180 days (recurring pest-control need) | **Weak** (conservative headline; see range) | 17,076 episodes, **~45/week**; **62.0% of those inspections were a Fail** (16.2% of ordinary inspections). Recurrence: any pest violation within 180 days 22.3% vs 2.6% matched (8.5×), but failed restaurants are re-inspected fast (68% within 180 days) and the median repeat is 8 days later, so that mostly measures re-checks. Counting only 15+ days later: 8.5% vs 2.5% (3.3×). Among restaurants re-inspected within 180 days (the same chance to be seen): 12.6% vs 8.4% (**1.5×**). The headline is the last, most conservative view | A pest finding means a restaurant under inspection pressure right now (6 in 10 fail) and about one in eight still shows pests at a re-inspection two weeks to six months later, only modestly above ordinary restaurants. It is a targeting list for pest-control sales, not a measured conversion: nearly every restaurant is already required to have a pest-control contract, so the realistic offer is "switch or add service." Needs a pest-control pilot client to learn the win rate; do not productize with a chance-of-work number |
| H24 | Restaurant plumbing violation (plumbing, leak, sewage, drain, hand sink) → plumbing permit at the address within 365 days | No signal | 3.2% vs 3.4% (0.95×); ~56/week. Strict definition (no hand sinks) 0.96×; failed inspections only 0.99× | Drop. Violations are fixed by the landlord or a plumber without a permit; a permit does not follow more often than at an ordinary restaurant |
| H25 | Restaurant hood/ventilation violation → HVAC/mechanical permit at the address within 365 days | No signal | 1.75% vs 2.0% (0.86×); ~18/week. Any ventilation heading (includes lighting) 0.98×. Permits that mention hood, exhaust or kitchen vent: 0.39% vs 0.38% (1.02×) | Drop. Hood cleaning and filter changes need no permit, and replacements are rare |
| H27 | Census-tract home-improvement loans per 1,000 residential parcels (HMDA, year Y) → share of the tract's residential parcels with a permit in year Y+1 | No signal | Top vs bottom loan quintile: 3.83% vs 3.64% (1.05×); mean rank correlation across the 7 loan years with a full following year (2018–2024) 0.07 (2024 is −0.03); holding the tract's current permit rate fixed it is 0.03. The top quintile's permit rate is already 1.07× in the loan year itself, so the loans add nothing. Loan counts are tiny (about 1,100–2,200 loans a year across the ~680 tracts used, mostly zero to three per tract) | Drop as a neighborhood demand index. Mortgage-financed home improvement is too sparse and too skewed to wealth to rank tracts; use the tract's own recent permit rate, which correlates 0.59 with next year's |
| H28 | Radar hail (NEXRAD `nx3hail` detections of 1+ inch within ~2.5 km) → reroof permits on those blocks in the next 120 days | No signal | 1.04× against blocks with no detection within ~8 km (88 event days, 10,448 reroofs near vs 44,837 far). 1.75+ inch storms: 1.12× (23 days). Severe-probability 30+: 1.04×. 270-day window: 1.00× | Radar footprints do not rescue the hail idea. Same verdict as H04 (spotter points): no storm leads. A real test needs an insurance or roofer-client dataset, not permits |

**Reading the caveats.**

- *H23.* "Conversion" is persistence of need seen at a later inspection, not a purchase. Pest-violating restaurants are inspected more often, which inflates the raw recurrence rate; the headline controls for that by looking only at restaurants that were re-inspected, but the control group there was re-inspected because something was wrong (selection that biases the lift down), so the truth lies between the 1.5× headline and the 3.3× "15+ days" view. Flags are keywords on free text whose item numbering changed over the years; two generic headings (rodent-proof garbage containers, hand-washing supplies) are removed before matching.
- *H24, H25.* Address-level permit matching, no contractor identity, and no way to see unpermitted repairs. The nulls are about permitted work only; a plumber or hood-cleaning vendor could still win these jobs without a permit.
- *H26.* The closure is recorded at an inspection, so some new licensees had already applied (the 19-day median). The license table covers retail food establishments only, so reopenings as a bar, caterer or non-food tenant are missed, and the same-name rule drops genuine ownership transfers under the old name. Both make the conversion a floor.
- *H27.* Area-level and not income-adjusted. HMDA tracts are 2010 through loan year 2021 and 2020 from 2022 (each year is matched to its own boundaries); the 2020 pair overlaps the pandemic; permits attach to parcels only where a PIN or address match exists.
- *H28.* nx3hail is a centroid per tracked hail cell per scan, not a MESH swath polygon: a block counts as under the swath when a centroid of that size was within about 2.5 km that day. Detections come from a box around the city, and days are UTC-6 approximations. Events in the last 125 days of permit data (including the 4-inch storm of 2026-07-27) are excluded so every window is complete.

### Product implications (round 3)

- **Build next: closed-restaurant space list (H26).** The only new winner. It is cheap to compute (inspection feed refreshes daily), the lift is large and stable by year, and the people who want it (build-out GCs, equipment dealers, signage, brokers, restaurant-supply sales) can act in the 12–36 week window in which most later licenses are issued. Report the 31+ day license rate (15%, 5×), not the 32% headline, when quoting a chance of new tenancy.
- **Pest-control list (H23):** offer to a pest-control prospect as a pilot (fresh pest findings, ~45/week, 62% fail) and measure their win rate; do not put a modelled probability in the app yet.
- **Drop:** plumbing and hood inspection leads (H24, H25), HMDA neighborhood index (H27), radar hail leads (H28).

### Why the storm tests failed (and how to retest)

**Round 3 update (H28):** the radar retest has now been run with NEXRAD hail detections (`nx3hail`) instead of spotter points and is also a null (1.04× for hail of 1+ inch within ~2.5 km; 1.12× for 1.75+ inch). The remaining untested piece is gridded MESH swaths (GRIB files, heavy processing) and a non-permit outcome. Original reasoning: NOAA's Storm Events are spotter **points** with coordinates rounded to ~1 km, and hail damage is often repaired through insurance without a permit spike we can see. A fair retest needs **radar-derived hail swaths** (NOAA's Severe Weather Data Inventory "MESH" grids) and, ideally, a target beyond permits (e.g., a roofer client's own lead and job data). Until then, no "storm leads" in the product.

## Next ideas to test (ranked by value × ease)

Status after round 3: N1/N2 (H17), N3 (H18), N4 (H28, radar centroids), N5 (H19), N6 (H20 and H23), N7 (H21), N8 (H27) are tested; N9–N12 are open, and round 3 adds N13–N15.

| # | Idea | Data | Who it's for | Ease | Status |
| --- | --- | --- | --- | --- | --- |
| N1 | 311 "building violation" complaint → *which* trade | 311, violations, assessor | All repair trades | Easy | Partly tested (H07, H17): citations that follow are masonry 11%, windows 11%, porch 9%, roofing 4%. Using complaint text (not in the warehouse) is still open |
| N2 | Chained score: complaint → citation → permit, with timing (when to mail) | 311, violations, permits | Porch, masonry | Easy | **Tested (H17, H22):** 33 days to citation, 172 more to permit, no seasonal pause |
| N3 | Repeat investors: which ones renovate fast, and which GCs they use | Sales, permits | Rehab GCs | Easy | **Tested (H18):** no speed or probability advantage; strong GC loyalty (56%). Next: map each repeat investor's go-to GC (relationship targeting for competing GCs) |
| N4 | Radar hail swaths (MESH) → reroof and siding permits | NOAA SWDI | Roofers | Medium | **Tested (H28, radar hail centroids): no signal** (1.04×; 1.12× at 1.75+ in). Gridded MESH swaths and an insurance/roofer-client outcome remain untested |
| N5 | Tree emergencies / storm debris (311) → tree service and roof repair | 311 | Tree services, roofers | Easy | **Tested (H19): no signal** |
| N6 | Rodent complaints (311) near restaurants → pest-control accounts | 311, food inspections | Pest control | Easy | **Tested (H20 weak; H23 weak by the conservative measure):** restaurants with a pest finding fail 62% of the time and 12.6% show pests again 15+ days later vs 8.4% (1.5×). Rodent complaints near restaurants (the 311-to-inspection link) are still untested. Next: a pest-control pilot client to measure win rate |
| N7 | New business license in a space with no recent build-out permit → cleaning, security, signage | Licenses, permits | B2B services | Easy | **Tested (H21):** takeovers rarely pull permits (12% any, 4.6% sign). Needs a service-client pilot, not more permit data |
| N8 | Home-improvement mortgages by census tract (HMDA) → neighborhood demand index | CFPB HMDA | All residential trades | Medium | **Tested (H27): no signal** (top vs bottom loan quintile 1.05×; rank correlation 0.07). Too sparse and wealth-skewed |
| N9 | Rooftop solar potential (Google Solar API / building footprints) × neighbors going solar | Google Solar API (key + cost), footprints | Solar | Medium, paid | Open |
| N10 | Street-level imagery of roof/porch condition (computer vision) | Street View API (paid, terms) | Roofers, porch | Hard; check terms first | Open |
| N11 | Tax-bill stress (appeals, tax sale lists) → distressed owners → sales | Cook County | Investors' contractors | Medium | Open |
| N12 | Contractor license or insurance lapses → GCs needing new subs | City/State licensing | Commercial subs | Medium | Open |
| N13 | Closed-restaurant spaces (inspection "Out of Business") → new food business and build-out | Food inspections, licenses, permits | Build-out GCs, equipment, signage, brokers | Easy | **Tested (H26): Strong** (10.2×; 5.0× for licenses 31+ days later). Queued for productization |
| N14 | Restaurant plumbing/hood violations → plumbing, HVAC permits | Food inspections, permits | Commercial plumbers, HVAC | Easy | **Tested (H24, H25): no signal** |
| N15 | Repeat or multi-location restaurant operators with pest or sanitation failures → account-level pest/cleaning sales | Food inspections (license, DBA) | Pest control, cleaning | Medium | Open (group licenses by operator name; needs a client pilot) |

**How to propose an idea:** describe it in one line ("X happens → Y follows"), and the lab can usually test it the same day if the data is public.

## How winners reach the product

1. Add the signal to `engine/leads/snapshot.py` as a lead type with its historical rate and timing.
2. Add it to the backtests (`research/backtests`) so it's re-validated whenever data refreshes.
3. Show it in the client app with its evidence and the "why" sentence.
4. Measure real close rates in Results; drop it if pilots don't convert.

Round-1 winners in the product (2026-11-15): H07 (complaint leads), H08 (porch inspection request leads), H09 (vacant-building leads), H13 (masonry age split on violation leads), H03 (roofing block list). Still queued: H01 (solar block lists). Round 2 added no new lead types (H17 is a timing result for the existing complaint and violation leads; H18–H21 failed or are descriptive). Round 3 produced one winner to productize (H26, closed-restaurant spaces) and one pilot candidate (H23, pest-control list); both are queued in `docs/HANDOFF.md`, not built in the app.
