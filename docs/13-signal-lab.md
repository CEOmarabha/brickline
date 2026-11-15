# Signal Lab — Testing Creative Lead Ideas Against History

*v2, 2026-11-15 (22 hypotheses). Results: `research/findings/signal-lab-2026-11-15.md` (reproducible and deterministic: `uv run python research/signal_lab/lab.py`, ~10 seconds; two runs produce byte-identical output).*

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

### Why the storm tests failed (and how to retest)

NOAA's Storm Events are spotter **points** with coordinates rounded to ~1 km, and hail damage is often repaired through insurance without a permit spike we can see. A fair retest needs **radar-derived hail swaths** (NOAA's Severe Weather Data Inventory "MESH" grids) and, ideally, a target beyond permits (e.g., a roofer client's own lead and job data). Until then, no "storm leads" in the product.

## Next ideas to test (ranked by value × ease)

Status after round 2: N1/N2 (H17), N3 (H18), N5 (H19), N6 (H20, partly), N7 (H21) are tested; the rest are open.

| # | Idea | Data | Who it's for | Ease | Status |
| --- | --- | --- | --- | --- | --- |
| N1 | 311 "building violation" complaint → *which* trade | 311, violations, assessor | All repair trades | Easy | Partly tested (H07, H17): citations that follow are masonry 11%, windows 11%, porch 9%, roofing 4%. Using complaint text (not in the warehouse) is still open |
| N2 | Chained score: complaint → citation → permit, with timing (when to mail) | 311, violations, permits | Porch, masonry | Easy | **Tested (H17, H22):** 33 days to citation, 172 more to permit, no seasonal pause |
| N3 | Repeat investors: which ones renovate fast, and which GCs they use | Sales, permits | Rehab GCs | Easy | **Tested (H18):** no speed or probability advantage; strong GC loyalty (56%). Next: map each repeat investor's go-to GC (relationship targeting for competing GCs) |
| N4 | Radar hail swaths (MESH) → reroof and siding permits | NOAA SWDI | Roofers | Medium | Open |
| N5 | Tree emergencies / storm debris (311) → tree service and roof repair | 311 | Tree services, roofers | Easy | **Tested (H19): no signal** |
| N6 | Rodent complaints (311) near restaurants → pest-control accounts | 311, food inspections | Pest control | Easy | Partly tested (H20, weak, address-level violations only). Needs the Food Inspections dataset to test the restaurant version |
| N7 | New business license in a space with no recent build-out permit → cleaning, security, signage | Licenses, permits | B2B services | Easy | **Tested (H21):** takeovers rarely pull permits (12% any, 4.6% sign). Needs a service-client pilot, not more permit data |
| N8 | Home-improvement mortgages by census tract (HMDA) → neighborhood demand index | CFPB HMDA | All residential trades | Medium | Open |
| N9 | Rooftop solar potential (Google Solar API / building footprints) × neighbors going solar | Google Solar API (key + cost), footprints | Solar | Medium, paid | Open |
| N10 | Street-level imagery of roof/porch condition (computer vision) | Street View API (paid, terms) | Roofers, porch | Hard; check terms first | Open |
| N11 | Tax-bill stress (appeals, tax sale lists) → distressed owners → sales | Cook County | Investors' contractors | Medium | Open |
| N12 | Contractor license or insurance lapses → GCs needing new subs | City/State licensing | Commercial subs | Medium | Open |

**How to propose an idea:** describe it in one line ("X happens → Y follows"), and the lab can usually test it the same day if the data is public.

## How winners reach the product

1. Add the signal to `engine/leads/snapshot.py` as a lead type with its historical rate and timing.
2. Add it to the backtests (`research/backtests`) so it's re-validated whenever data refreshes.
3. Show it in the client app with its evidence and the "why" sentence.
4. Measure real close rates in Results; drop it if pilots don't convert.

Round-1 winners in the product (2026-11-15): H07 (complaint leads), H08 (porch inspection request leads), H09 (vacant-building leads), H13 (masonry age split on violation leads), H03 (roofing block list). Still queued: H01 (solar block lists). Round 2 added no new lead types (H17 is a timing result for the existing complaint and violation leads; H18–H21 failed or are descriptive).
