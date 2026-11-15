# Signal lab — 2026-11-15

Creative lead hypotheses tested against Chicago history. Reproduce with `uv run python research/signal_lab/lab.py`. Verdicts: **Strong** = lift ≥ 3 with ≥ 5 signals/week; **Useful** = lift ≥ 1.8; **Weak** = lift ≥ 1.25; otherwise **No signal**. Permits capture permitted work only, so conversion rates are floors.

## Leaderboard

| # | Hypothesis | Verdict | Lift | Conversion | Baseline | Signals/week | Who it's for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H08 | 311 porch inspection request → porch permit | **Strong** | 11.44× | 13.7% | 1.2% | 7.10 | Porch builders |
| H17 | Complaint chain: 311 complaint → porch/masonry citation → permit (when to mail) | **Strong** | 6.26× | 12.3% | 2.0% | 47.80 | Porch builders, masons and tuckpointers |
| H07 | 311 building complaint → city citation (earlier lead) | **Strong** | 5.85× | 31.6% | 5.4% | 255.40 | Porch, masonry, roofing, general repair contractors |
| H13 | Which buildings need masonry work: walls × age | **Useful** | 2.86× | 1.4% | 0.5% | — | Masons, tuckpointers |
| H09 | Vacant-building complaint → property sells | **Useful** | 2.49× | 19.4% | 7.8% | 20.50 | Investors' contractors, rehab GCs, property managers (and investors themselves) |
| H01 | Neighbors went solar → you go solar | **Useful** | 2.41× | 1.0% | 0.4% | 33.40 | Solar installers |
| H12 | Which houses re-roof: age × roof material | **Useful** | 2.37× | 2.2% | 0.9% | — | Roofers, solar installers |
| H10 | Complaint about unpermitted work → permit gets pulled | **Useful** | 2.17× | 18.9% | 8.7% | 70.60 | Expediters, architects, GCs who legalize work |
| H03 | Neighbors re-roofed → you re-roof | **Useful** | 2.16× | 0.7% | 0.3% | — | Roofers |
| H14 | Which homes pull HVAC permits: A/C × heat type | **Useful** | 2.16× | 0.3% | 0.1% | — | HVAC contractors |
| H15 | Assessor condition rating → renovation permits | **Weak** | 1.41× | 0.6% | 0.4% | — | General contractors, rehab crews |
| H20 | 311 rodent complaint → building/pest violation (pest-control demand proxy) | **Weak** | 1.31× | 1.9% | 1.5% | 545.50 | Pest control, sanitation and property-management services |
| H21 | New food license with no recent build-out permit (as-is takeover) → permits after opening | **Descriptive** | —× | 12.1% | 51.7% | 14.40 | Signage, cleaning, security, small-trade contractors serving new restaurants |
| H22 | Seasonality: when permits are pulled and how fast citations turn into permits, by month | **Descriptive** | —× | — | — | — | Porch, masonry and roofing contractors (mailing calendar) |
| H02 | New roof → solar within 2 years | **No signal** | 1.18× | 1.0% | 0.8% | 90.20 | Solar installers (and roofers partnering with them) |
| H16 | Poor energy score → mechanical/electrical upgrades | **No signal** | 1.08× | 17.7% | 16.4% | — | Commercial HVAC, electrical, lighting retrofit, energy services |
| H19 | 311 'tree emergency' → roofing or porch permit (storm-damage proxy) | **No signal** | 1.00× | 0.5% | 0.5% | 405.20 | Tree services, roofers, porch builders |
| H04 | Hail ≥ 1 inch → reroof wave | **No signal** | 0.98× | 1.14 | 1.17 | 0.10 | Roofers, gutter and siding contractors, restoration |
| H05 | Damaging wind (60+ kt) → reroof wave | **No signal** | 0.90× | 1.04 | 1.16 | 0.20 | Roofers, gutter and siding contractors, restoration |
| H18 | Repeat investors (3+ purchases in 24 months) renovate more and faster than one-off company buyers | **No signal** | 0.90× | 32.3% | 36.0% | 14.90 | Rehab GCs, subs working for investors, property managers |
| H06 | 311 'water in basement' → plumbing work | **No signal** | 0.74× | 0.5% | 0.6% | 271.40 | Plumbers, waterproofing and drain contractors |
| H11 | Lead test kit request → plumbing work | **No signal** | 0.70× | 0.6% | 0.9% | 273.30 | Plumbers |

## H08 — 311 porch inspection request → porch permit

- **Signal:** 'Porch Inspection Request' 311 call
- **Target:** Porch permit at the same address within 365 days
- **Data:** 311 service requests, permits
- **Verdict:** Strong
- Signals tested: 3,014; conversion 13.7% vs baseline 1.2%; median 149.5 days to target

| year | n | conversion |
| --- | --- | --- |
| 2018 | 2 | 0.0% |
| 2019 | 457 | 14.4% |
| 2020 | 440 | 10.7% |
| 2021 | 441 | 13.2% |
| 2022 | 498 | 16.5% |
| 2023 | 418 | 14.6% |
| 2024 | 429 | 14.9% |
| 2025 | 329 | 10.3% |

## H17 — Complaint chain: 311 complaint → porch/masonry citation → permit (when to mail)

- **Signal:** 'Building Violation' 311 complaint at an address that gets a porch or masonry citation within 120 days
- **Target:** Porch or masonry permit at the same address within 365 days of the complaint
- **Data:** 311 service requests, building violations, permits
- **Verdict:** Strong
- **Notes:** Cohort is selected on the citation (known only afterwards), so it describes the timeline of the chain, not a forecast available on the complaint day; at complaint time the usable rate is H07 (31.6% cited) times the porch/masonry share. 311 data starts mid-2018. The citation-to-permit step is the validated violation lead; lift against the address's own earlier year is inflated by the citation itself forcing a repair, so also read the complaint_basis table (complaints with no porch/masonry citation convert at a much lower rate). Permits undercount repairs, so rates are floors.
- Signals tested: 15,616; conversion 12.3% vs baseline 2.0%; median 197.0 days to target

| step | complaints | median_days_complaint_to_citation | conversion | permits | median_days_citation_to_permit | citation_to_permit_p25_days | citation_to_permit_p75_days | median_days_complaint_to_permit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Porch or masonry citation → porch or masonry permit | 15616 | 33.00 | 13.4% | 2085 | 172.00 | 97.00 | 257.00 | 215.00 |
| Porch citation → porch permit | 8693 | 32.00 | 11.8% | 1022 | 181.00 | 104.00 | 261.00 | 223.00 |
| Masonry citation → masonry permit | 11335 | 33.00 | 10.0% | 1133 | 173.00 | 93.00 | 261.00 | 213.00 |

| cohort | complaints | conversion | prior_window | median_days_complaint_to_permit |
| --- | --- | --- | --- | --- |
| Complaint followed by a porch/masonry citation within 120 days | 15616 | 12.3% | 2.0% | 197.00 |
| Complaint with NO porch/masonry citation within 120 days | 73031 | 4.5% | 2.4% | 174.00 |

| year | n | conversion |
| --- | --- | --- |
| 2018 | 52 | 23.1% |
| 2019 | 3391 | 11.4% |
| 2020 | 1855 | 6.0% |
| 2021 | 2565 | 13.1% |
| 2022 | 1642 | 14.7% |
| 2023 | 1846 | 15.6% |
| 2024 | 2048 | 13.7% |
| 2025 | 2217 | 12.0% |

## H07 — 311 building complaint → city citation (earlier lead)

- **Signal:** 'Building Violation' 311 complaint at an address
- **Target:** Building violation recorded at the same address within 120 days
- **Data:** 311 service requests, building violations
- **Verdict:** Strong
- **Notes:** If conversion is high, the complaint is an earlier version of the violation lead (median_days = head start).
- Signals tested: 96,864; conversion 31.6% vs baseline 5.4%; median 32.0 days to target

| porch_rate | masonry_rate | roofing_rate | windows_doors_rate | plumbing_rate | electrical_rate | hvac_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 8.8% | 11.4% | 3.8% | 11.2% | 1.3% | 1.2% | 1.0% |

| year | n | conversion |
| --- | --- | --- |
| 2018 | 217 | 53.9% |
| 2019 | 15001 | 49.6% |
| 2020 | 13125 | 29.5% |
| 2021 | 14881 | 33.1% |
| 2022 | 14294 | 20.4% |
| 2023 | 14033 | 22.5% |
| 2024 | 13725 | 28.6% |
| 2025 | 11588 | 36.4% |

## H13 — Which buildings need masonry work: walls × age

- **Signal:** Property group: Masonry / pre-1910
- **Target:** masonry permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Useful

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| Masonry / pre-1910 | 38759 | 1.4% | 2.86 |
| Masonry / 1910-39 | 71009 | 0.8% | 1.60 |
| Frame + Masonry / pre-1910 | 5219 | 0.7% | 1.48 |
| Frame + Masonry / 1910-39 | 9525 | 0.6% | 1.23 |
| Masonry / 1970+ | 20252 | 0.6% | 1.14 |
| Frame + Masonry / 1970+ | 4424 | 0.4% | 0.86 |
| Frame / 1970+ | 9229 | 0.4% | 0.85 |
| Frame + Masonry / 1940-69 | 11652 | 0.3% | 0.68 |
| Stucco / pre-1910 | 1116 | 0.3% | 0.55 |
| Frame / pre-1910 | 45816 | 0.2% | 0.38 |
| Frame / 1910-39 | 32018 | 0.2% | 0.33 |
| Masonry / 1940-69 | 72633 | 0.1% | 0.26 |
| Stucco / 1910-39 | 2200 | 0.1% | 0.22 |
| Frame / 1940-69 | 12941 | 0.1% | 0.18 |

## H09 — Vacant-building complaint → property sells

- **Signal:** 'Vacant/Abandoned Building' 311 complaint
- **Target:** Property sale within 365 days
- **Data:** 311 service requests, Cook County sales
- **Verdict:** Useful
- **Notes:** A sale after vacancy usually means a rehab: an early entry into the investor-purchase lead.
- Signals tested: 9,307; conversion 19.4% vs baseline 7.8%; median 167.0 days to target

| year | n | conversion |
| --- | --- | --- |
| 2018 | 83 | 24.1% |
| 2019 | 2052 | 18.2% |
| 2020 | 1426 | 20.3% |
| 2021 | 1377 | 18.4% |
| 2022 | 1345 | 19.7% |
| 2023 | 1176 | 18.4% |
| 2024 | 1347 | 20.3% |
| 2025 | 501 | 22.4% |

## H01 — Neighbors went solar → you go solar

- **Signal:** 2+ solar permits on the same block (~160 m cell) in the past 12 months
- **Target:** Solar permit at a house/2–6 flat in the next 12 months
- **Data:** Permits (solar), Assessor residential characteristics, geocoded addresses
- **Verdict:** Useful
- **Notes:** Cell-level exposure; confounded by neighborhood income and installer canvassing, so treat lift as an upper bound on true peer influence. Still directly usable for targeting.

| grp | parcels | rate |
| --- | --- | --- |
| 0 | 1778105 | 0.4% |
| 1 | 190629 | 0.6% |
| 2+ | 25279 | 1.0% |

## H12 — Which houses re-roof: age × roof material

- **Signal:** Property group: 2000+ / Other
- **Target:** roofing permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Useful

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| 2000+ / Other | 1189 | 2.2% | 2.37 |
| 2000+ / Tar + Gravel | 4907 | 1.5% | 1.61 |
| 2000+ / Shingle + Asphalt | 12117 | 1.4% | 1.53 |
| pre-1910 / Other | 1769 | 1.1% | 1.16 |
| 1940-69 / Shingle + Asphalt | 92289 | 1.0% | 1.15 |
| 1910-39 / Shingle + Asphalt | 88231 | 1.0% | 1.07 |
| 1970-99 / Shingle + Asphalt | 12546 | 0.8% | 0.92 |
| 1910-39 / Tile | 1258 | 0.8% | 0.84 |
| pre-1910 / Tar + Gravel | 24428 | 0.7% | 0.80 |
| 1940-69 / Tar + Gravel | 4045 | 0.7% | 0.80 |
| pre-1910 / Shingle + Asphalt | 64031 | 0.7% | 0.74 |
| 1910-39 / Tar + Gravel | 23994 | 0.6% | 0.70 |
| 1970-99 / Tar + Gravel | 3048 | 0.6% | 0.62 |

## H10 — Complaint about unpermitted work → permit gets pulled

- **Signal:** 'No Building Permit and Construction Violation' 311 complaint
- **Target:** Any permit at the same address within 180 days
- **Data:** 311 service requests, permits
- **Verdict:** Useful
- Signals tested: 26,245; conversion 18.9% vs baseline 8.7%; median 52.0 days to target

| year | n | conversion |
| --- | --- | --- |
| 2018 | 191 | 15.7% |
| 2019 | 3788 | 25.3% |
| 2020 | 3889 | 18.9% |
| 2021 | 3562 | 21.2% |
| 2022 | 3858 | 19.7% |
| 2023 | 3839 | 15.9% |
| 2024 | 3924 | 15.7% |
| 2025 | 3194 | 15.0% |

## H03 — Neighbors re-roofed → you re-roof

- **Signal:** 2+ reroof permits on the same block in the past 90 days
- **Target:** Reroof permit at a neighboring house in the next 180 days
- **Data:** Permits (reroof), Assessor residential characteristics
- **Verdict:** Useful
- **Notes:** Block-level targeting for door hangers and mail right after a cluster of permits.

| grp | parcels | rate |
| --- | --- | --- |
| 0 | 11893346 | 0.3% |
| 1 | 531783 | 0.5% |
| 2+ | 25928 | 0.7% |

## H14 — Which homes pull HVAC permits: A/C × heat type

- **Signal:** Property group: Central A/C / Hot Water Steam
- **Target:** hvac permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Useful
- **Notes:** The original idea (no central A/C → new A/C installs) is refuted: homes without central A/C are below average. Homes that already have it pull more permits, i.e. replacements. Most residential HVAC swaps aren't permitted, so rates are low.

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| Central A/C / Hot Water Steam | 8284 | 0.3% | 2.16 |
| Central A/C / Warm Air Furnace | 97143 | 0.2% | 1.57 |
| No Central A/C / Electric Heater | 1330 | 0.2% | 1.31 |
| No Central A/C / None | 1708 | 0.1% | 0.90 |
| No Central A/C / Hot Water Steam | 70382 | 0.1% | 0.83 |
| No Central A/C / Warm Air Furnace | 157508 | 0.1% | 0.66 |

## H15 — Assessor condition rating → renovation permits

- **Signal:** Property group: Above Average
- **Target:** interior buildout permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Weak

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| Above Average | 2273 | 0.6% | 1.41 |
| Below Average | 2530 | 0.5% | 1.24 |
| Average | 332210 | 0.4% | 1.00 |

## H20 — 311 rodent complaint → building/pest violation (pest-control demand proxy)

- **Signal:** 'Rodent Baiting/Rat Complaint' 311 request at an address
- **Target:** Any building violation at the same address within 180 days
- **Data:** 311 service requests, building violations
- **Verdict:** Weak
- **Notes:** Food inspections are not in the warehouse, so the restaurant idea (rodent complaints near restaurants -> failed inspections) is untested; add the Chicago Food Inspections dataset to test it directly. Rat complaints are filed against the address of the nearby problem (alleys, garbage), not necessarily the owner's building, and baiting is done by the City, so the complaint is demand evidence, not a work order.
- Signals tested: 220,172; conversion 1.9% vs baseline 1.5%; median 74.0 days to target

| target | conversion | baseline_rate |
| --- | --- | --- |
| pest/sanitation violation | 0.1% | 0.1% |

| year | n | conversion |
| --- | --- | --- |
| 2019 | 27850 | 2.9% |
| 2020 | 34559 | 1.3% |
| 2021 | 40881 | 1.9% |
| 2022 | 32267 | 1.8% |
| 2023 | 30923 | 1.7% |
| 2024 | 28368 | 2.0% |
| 2025 | 25324 | 2.0% |

## H21 — New food license with no recent build-out permit (as-is takeover) → permits after opening

- **Signal:** First food license for an account at an address, with no renovation/new-construction permit there in the prior 2 years
- **Target:** Any permit at the address within 365 days after the license
- **Data:** Retail food licenses, permits
- **Verdict:** Descriptive
- **Notes:** Descriptive: compares as-is takeovers with licenses that followed a build-out. The food license table has no license type, so renewals under a new account number (ownership changes) look like new businesses. Address matching depends on a normalized street address; units in a building share one address, so a permit for another tenant counts. A first-year permit is not necessarily a build-out; the sign/MEP/build-out columns separate what kind of permit follows.

| grp | licenses | any_permit_rate | sign_permit_rate | buildout_permit_rate | mep_permit_rate | median_days_to_first_permit |
| --- | --- | --- | --- | --- | --- | --- |
| As-is takeover (no build-out permit in prior 2 years) | 7534 | 12.1% | 4.6% | 2.4% | 5.5% | 132.00 |
| Build-out permit in prior 2 years | 3065 | 51.7% | 26.3% | 25.7% | 29.3% | 36.00 |

## H22 — Seasonality: when permits are pulled and how fast citations turn into permits, by month

- **Signal:** Calendar month of permit issue / of porch or masonry citation
- **Target:** Share of the year's porch, masonry and roofing permits; days from citation to permit
- **Data:** Permits (issue dates 2016-2025), building violations
- **Verdict:** Descriptive
- **Notes:** Descriptive. Permit shares are by issue month (when the job is cleared to start), which trails the decision by the permit-processing time; citation rows show, for citations issued in each month, how many got a porch/masonry permit within a year and the median days to it (only citations that converted, so the median is censored at 365). Weather, the City's inspection calendar and porch-season enforcement all move together here, so this is a calendar, not a causal effect of month.

| month | porch_share | masonry_share | roofing_share | citations | permit_within_365_share | median_days_citation_to_permit |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 7.1% | 5.3% | 5.1% | 3057 | 15.2% | 182.00 |
| 2 | 6.4% | 5.6% | 5.3% | 3298 | 14.2% | 182.00 |
| 3 | 7.9% | 8.6% | 8.0% | 4204 | 15.6% | 177.00 |
| 4 | 8.4% | 9.1% | 8.9% | 3684 | 14.9% | 178.00 |
| 5 | 8.9% | 9.5% | 9.2% | 4192 | 14.6% | 176.00 |
| 6 | 8.8% | 9.7% | 9.0% | 4115 | 14.8% | 170.00 |
| 7 | 9.0% | 9.5% | 9.2% | 3781 | 15.6% | 181.50 |
| 8 | 9.9% | 10.5% | 10.3% | 4576 | 14.2% | 192.00 |
| 9 | 9.0% | 9.5% | 9.2% | 3979 | 15.1% | 191.00 |
| 10 | 10.0% | 10.2% | 10.4% | 3691 | 14.4% | 203.00 |
| 11 | 8.3% | 7.1% | 8.4% | 2577 | 14.9% | 189.50 |
| 12 | 6.4% | 5.4% | 7.0% | 2288 | 13.7% | 187.00 |

## H02 — New roof → solar within 2 years

- **Signal:** Reroof permit in the past 12 months
- **Target:** Solar permit at the same parcel within 24 months
- **Data:** Permits (reroof, solar), Assessor residential characteristics
- **Verdict:** No signal

| reroofed | parcels | rate |
| --- | --- | --- |
| False | 1995690 | 0.8% |
| True | 6476 | 1.0% |

## H16 — Poor energy score → mechanical/electrical upgrades

- **Signal:** Building reports an ENERGY STAR score ≤ 40
- **Target:** HVAC or electrical permit in the following two years
- **Data:** Chicago Energy Benchmarking (buildings ≥ 50k sq ft), permits
- **Verdict:** No signal
- **Notes:** Large buildings; addresses matched by normalized street address.

| grp | building_years | rate |
| --- | --- | --- |
| 41-74 | 5997 | 20.7% |
| ENERGY STAR ≤ 40 | 4373 | 17.7% |
| ENERGY STAR ≥ 75 | 5616 | 16.4% |

## H19 — 311 'tree emergency' → roofing or porch permit (storm-damage proxy)

- **Signal:** 'Tree Emergency' 311 request (fallen/hazardous tree) at an address
- **Target:** Roofing or porch permit at the same address within 180 days
- **Data:** 311 service requests, permits
- **Verdict:** No signal
- **Notes:** Tree emergencies cluster in storm weeks and summer, and roofing permits are seasonal, so the default baseline (the 180 days before the prior window) can be season-shifted; 'seasonal_baseline' uses the same 180-day window one year earlier and is the fairer control. A tree on a roof is often repaired by insurance without a permit, and the 311 address is often the parkway tree in front of the house, not a damaged building.
- Signals tested: 110,980; conversion 0.5% vs baseline 0.5%; median 82.0 days to target

| target | conversion | seasonal_baseline_rate |
| --- | --- | --- |
| roofing | 0.3% | 0.3% |
| porch | 0.2% | 0.2% |

| year | n | conversion |
| --- | --- | --- |
| 2019 | 8883 | 0.5% |
| 2020 | 21662 | 0.5% |
| 2021 | 14497 | 0.4% |
| 2022 | 12043 | 0.5% |
| 2023 | 11346 | 0.5% |
| 2024 | 22634 | 0.5% |
| 2025 | 19915 | 0.6% |

## H04 — Hail ≥ 1 inch → reroof wave

- **Signal:** Hail report ≥ 1.0 in within ~3 km
- **Target:** Reroof permits on those blocks in the next 120 days (vs the same blocks a year earlier, vs all other blocks)
- **Data:** NOAA Storm Events (Cook County reports with coordinates), permits
- **Verdict:** No signal
- **Notes:** 'conversion' and 'baseline' here are after/before permit ratios near vs far from the storm; lift is their ratio (difference-in-ratios). Spotter reports are points, so 3 km is a rough footprint.
- Near storms: 2300 reroof permits in the 120 days after vs 2013 in the same window a year earlier; elsewhere: 80409 vs 68831; 97 storm reports.

## H05 — Damaging wind (60+ kt) → reroof wave

- **Signal:** Thunderstorm Wind report ≥ 60 kt within ~3 km
- **Target:** Reroof permits on those blocks in the next 120 days (vs the same blocks a year earlier, vs all other blocks)
- **Data:** NOAA Storm Events (Cook County reports with coordinates), permits
- **Verdict:** No signal
- **Notes:** 'conversion' and 'baseline' here are after/before permit ratios near vs far from the storm; lift is their ratio (difference-in-ratios). Spotter reports are points, so 3 km is a rough footprint.
- Near storms: 4332 reroof permits in the 120 days after vs 4169 in the same window a year earlier; elsewhere: 121374 vs 104722; 128 storm reports.

## H18 — Repeat investors (3+ purchases in 24 months) renovate more and faster than one-off company buyers

- **Signal:** Company buyer (not bank/agency/land trust) who bought on 3+ distinct dates in the 24 months up to and including this purchase
- **Target:** Any permit at the purchased parcel within 365 days of purchase (baseline: company buyers with exactly 1 purchase date in 24 months)
- **Data:** Cook County sales, permits, permit parties
- **Verdict:** No signal
- **Notes:** Buyers are identified by name string (the sales feed truncates names to ~25 characters and investors often use a new LLC per building), so portfolio operators are undercounted and 'repeat' means a repeat name. Units are single-parcel deeds (multi-parcel deeds are excluded as units but count as one purchase date). Repeat investors differ from one-off buyers in building mix (more multi-family/commercial and larger parcels that need permits for any reason), so this is a targeting comparison, not a causal effect. GC loyalty: of repeat buyers' permits naming a GC where the buyer already had an earlier permit with a named GC on a different property, the share naming one of those same GCs, against the chance a random GC (weighted by that year's citywide GC permit share) would match. Only buyers with prior permits can be measured, which favors buyers who renovate repeatedly.

| grp | purchases | buyers | conversion | median_days_to_first_permit |
| --- | --- | --- | --- | --- |
| 1 purchase | 34367 | 32497 | 36.0% | 96.00 |
| 2 purchases | 4423 | 3693 | 34.5% | 93.00 |
| 3-5 purchases | 3771 | 1506 | 34.6% | 92.00 |
| 6+ purchases | 4023 | 389 | 30.1% | 99.50 |

| measure | permits | buyers | share |
| --- | --- | --- | --- |
| Repeat buyers' permits naming a GC the buyer used before on another property | 2201 | 486 | 55.7% |
| Benchmark: chance a randomly drawn Chicago GC (same year) would be one of those GCs | 2201 | 486 | 0.3% |

## H06 — 311 'water in basement' → plumbing work

- **Signal:** Resident files a 'Water in Basement' 311 complaint
- **Target:** Plumbing permit at the same address within 365 days
- **Data:** 311 service requests, permits
- **Verdict:** No signal
- **Notes:** Permits undercount drain/waterproofing jobs (many need no permit), so this is a floor.
- Signals tested: 47,853; conversion 0.5% vs baseline 0.6%; median 153.0 days to target

| year | n | conversion |
| --- | --- | --- |
| 2018 | 3 | 0.0% |
| 2019 | 3611 | 0.7% |
| 2020 | 4871 | 0.5% |
| 2021 | 3284 | 0.6% |
| 2022 | 6171 | 0.6% |
| 2023 | 13149 | 0.4% |
| 2024 | 3070 | 0.7% |
| 2025 | 13694 | 0.3% |

## H11 — Lead test kit request → plumbing work

- **Signal:** Household requests a water lead test kit
- **Target:** Plumbing permit at the same address within 365 days
- **Data:** 311 service requests, permits
- **Verdict:** No signal
- **Notes:** Lead service line replacements are done under the Water Department, not building permits, so this measures only other plumbing work.
- Signals tested: 90,930; conversion 0.6% vs baseline 0.9%; median 155.5 days to target

| year | n | conversion |
| --- | --- | --- |
| 2018 | 443 | 1.1% |
| 2019 | 37098 | 0.4% |
| 2020 | 5085 | 0.6% |
| 2021 | 10894 | 0.6% |
| 2022 | 7128 | 0.8% |
| 2023 | 7843 | 0.7% |
| 2024 | 9492 | 1.0% |
| 2025 | 12947 | 0.7% |
