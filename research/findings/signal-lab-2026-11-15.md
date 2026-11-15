# Signal lab — 2026-11-15

Creative lead hypotheses tested against Chicago history. Reproduce with `uv run python research/signal_lab/lab.py`. Verdicts: **Strong** = lift ≥ 3 with ≥ 5 signals/week; **Useful** = lift ≥ 1.8; **Weak** = lift ≥ 1.25; otherwise **No signal**. Permits capture permitted work only, so conversion rates are floors.

## Leaderboard

| # | Hypothesis | Verdict | Lift | Conversion | Baseline | Signals/week | Who it's for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H08 | 311 porch inspection request → porch permit | **Strong** | 11.44× | 13.7% | 1.2% | 7.10 | Porch builders |
| H26 | Restaurant 'Out of Business' → new food license or renovation permit at the address within 365 days | **Strong** | 10.24× | 32.3% | 3.2% | 13.10 | Restaurant build-out contractors, equipment dealers, brokers, signage |
| H17 | Complaint chain: 311 complaint → porch/masonry citation → permit (when to mail) | **Strong** | 6.26× | 12.3% | 2.0% | 47.80 | Porch builders, masons and tuckpointers |
| H07 | 311 building complaint → city citation (earlier lead) | **Strong** | 5.85× | 31.6% | 5.4% | 255.40 | Porch, masonry, roofing, general repair contractors |
| H13 | Which buildings need masonry work: walls × age | **Useful** | 2.86× | 1.4% | 0.5% | — | Masons, tuckpointers |
| H09 | Vacant-building complaint → property sells | **Useful** | 2.49× | 19.4% | 7.8% | 20.50 | Investors' contractors, rehab GCs, property managers (and investors themselves) |
| H01 | Neighbors went solar → you go solar | **Useful** | 2.41× | 1.0% | 0.4% | 33.40 | Solar installers |
| H12 | Which houses re-roof: age × roof material | **Useful** | 2.37× | 2.2% | 0.9% | — | Roofers, solar installers |
| H10 | Complaint about unpermitted work → permit gets pulled | **Useful** | 2.17× | 18.9% | 8.7% | 70.60 | Expediters, architects, GCs who legalize work |
| H03 | Neighbors re-roofed → you re-roof | **Useful** | 2.16× | 0.7% | 0.3% | — | Roofers |
| H14 | Which homes pull HVAC permits: A/C × heat type | **Useful** | 2.16× | 0.3% | 0.1% | — | HVAC contractors |
| H23 | Restaurant pest violation → another pest violation within 180 days (recurring pest-control need) | **Weak** | 1.50× | 12.6% | 8.4% | 44.80 | Pest-control companies |
| H15 | Assessor condition rating → renovation permits | **Weak** | 1.41× | 0.6% | 0.4% | — | General contractors, rehab crews |
| H20 | 311 rodent complaint → building/pest violation (pest-control demand proxy) | **Weak** | 1.31× | 1.9% | 1.5% | 545.50 | Pest control, sanitation and property-management services |
| H21 | New food license with no recent build-out permit (as-is takeover) → permits after opening | **Descriptive** | —× | 12.1% | 51.7% | 14.40 | Signage, cleaning, security, small-trade contractors serving new restaurants |
| H22 | Seasonality: when permits are pulled and how fast citations turn into permits, by month | **Descriptive** | —× | — | — | — | Porch, masonry and roofing contractors (mailing calendar) |
| H02 | New roof → solar within 2 years | **No signal** | 1.18× | 1.0% | 0.8% | 90.20 | Solar installers (and roofers partnering with them) |
| H16 | Poor energy score → mechanical/electrical upgrades | **No signal** | 1.08× | 17.7% | 16.4% | — | Commercial HVAC, electrical, lighting retrofit, energy services |
| H27 | Home-improvement mortgage loans per tract (HMDA, year Y) → residential permits per parcel (year Y+1) | **No signal** | 1.05× | 3.8% | 3.6% | — | All residential trades (neighborhood demand index for mail targeting) |
| H28 | Radar-detected hail (NEXRAD) → reroof wave on blocks under the swath | **No signal** | 1.04× | 116.9% | 112.9% | 0.20 | Roofers, gutter and siding contractors, restoration |
| H19 | 311 'tree emergency' → roofing or porch permit (storm-damage proxy) | **No signal** | 1.00× | 0.5% | 0.5% | 405.20 | Tree services, roofers, porch builders |
| H04 | Hail ≥ 1 inch → reroof wave | **No signal** | 0.98× | 1.14 | 1.17 | 0.10 | Roofers, gutter and siding contractors, restoration |
| H24 | Restaurant plumbing violation → plumbing permit at the address within 365 days | **No signal** | 0.95× | 3.2% | 3.4% | 55.70 | Commercial plumbers, drain and grease-trap contractors |
| H05 | Damaging wind (60+ kt) → reroof wave | **No signal** | 0.90× | 1.04 | 1.16 | 0.20 | Roofers, gutter and siding contractors, restoration |
| H18 | Repeat investors (3+ purchases in 24 months) renovate more and faster than one-off company buyers | **No signal** | 0.90× | 32.3% | 36.0% | 14.90 | Rehab GCs, subs working for investors, property managers |
| H25 | Restaurant hood/ventilation violation → HVAC or mechanical permit at the address within 365 days | **No signal** | 0.86× | 1.8% | 2.0% | 18.00 | Commercial HVAC, hood and exhaust-cleaning contractors |
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

## H26 — Restaurant 'Out of Business' → new food license or renovation permit at the address within 365 days

- **Signal:** Inspection result 'Out of Business' for a restaurant (first one at the address in 365 days)
- **Target:** New retail food license issued at the same address to a differently named business within 365 days; also a renovation/build-out/new-construction permit
- **Data:** Chicago food inspections (2016+), retail food licenses, permits
- **Verdict:** Strong
- **Notes:** Space turnover. Control: ordinary restaurant inspections (Pass, Pass w/ Conditions, Fail) at an address, which also see turnover, so lift is the extra turnover after a closure. Closed spaces that re-let to a non-food tenant, or that reopen as the same name or a bar/cafe under another license class, are missed by the license test (the license table here is retail food establishments only), so conversion is a floor. Same-name matching drops ownership-transfer relicensing under the old trade name. The renovation permit view counts any renovation at the address, including unrelated tenants.
- Signals tested: 7,943; conversion 32.3% vs baseline 3.2%; median 19.0 days to target

| definition | signals | conversion | matched_control | lift | median_days | days_p25_p75 | share_converting_after_30_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New retail food license under a different business name (headline) | 7943 | 32.3% | 3.2% | 10.24 | 19.00 | 6-112 | 13.6% |
| New license (different name) issued 31+ days after the closure was recorded | 7943 | 15.0% | 3.0% | 5.03 | 154.00 | 82-252 | 15.0% |
| Any new retail food license, including the same name | 7943 | 43.0% | 4.8% | 9.02 | 15.00 | 5-84 | 16.2% |
| Renovation, build-out or new-construction permit | 7943 | 11.0% | 6.2% | 1.78 | 113.00 | 40-210 | 8.8% |

| year | n | conversion | control_conversion |
| --- | --- | --- | --- |
| 2016 | 932 | 32.2% | 4.2% |
| 2017 | 826 | 32.1% | 5.8% |
| 2018 | 726 | 36.6% | 4.9% |
| 2019 | 943 | 29.5% | 4.0% |
| 2020 | 668 | 31.9% | 2.6% |
| 2021 | 794 | 29.0% | 4.0% |
| 2022 | 787 | 31.3% | 3.3% |
| 2023 | 786 | 36.9% | 3.9% |
| 2024 | 886 | 31.2% | 3.2% |
| 2025 | 595 | 34.3% | 3.6% |

| strat | signals | signal_rate | controls | control_rate |
| --- | --- | --- | --- | --- |
| Canvass (routine) | 7834 | 32.4% | 24460 | 3.1% |
| Complaint | 41 | 34.1% | 3274 | 3.6% |
| License (pre-opening) | 1 | 0.0% | 3680 | 9.6% |
| Other | 27 | 22.2% | 50 | 2.0% |
| Re-inspection | 40 | 32.5% | 89 | 7.9% |

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
| Masonry / pre-1910 | 38758 | 1.4% | 2.86 |
| Masonry / 1910-39 | 71009 | 0.8% | 1.60 |
| Frame + Masonry / pre-1910 | 5219 | 0.7% | 1.48 |
| Frame + Masonry / 1910-39 | 9525 | 0.6% | 1.23 |
| Masonry / 1970+ | 20252 | 0.6% | 1.14 |
| Frame + Masonry / 1970+ | 4424 | 0.4% | 0.86 |
| Frame / 1970+ | 9229 | 0.4% | 0.85 |
| Frame + Masonry / 1940-69 | 11652 | 0.3% | 0.68 |
| Stucco / pre-1910 | 1116 | 0.3% | 0.55 |
| Frame / pre-1910 | 45817 | 0.2% | 0.38 |
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
| Central A/C / Warm Air Furnace | 97142 | 0.2% | 1.57 |
| No Central A/C / Electric Heater | 1330 | 0.2% | 1.31 |
| No Central A/C / None | 1708 | 0.1% | 0.90 |
| No Central A/C / Hot Water Steam | 70383 | 0.1% | 0.83 |
| No Central A/C / Warm Air Furnace | 157508 | 0.1% | 0.66 |

## H23 — Restaurant pest violation → another pest violation within 180 days (recurring pest-control need)

- **Signal:** Restaurant inspection (Pass, Pass w/ Conditions or Fail) citing rodents, mice, roaches, insects, pests or droppings, with none at that license in the prior 180 days
- **Target:** Another pest violation at the same license 15 to 180 days later, among restaurants re-inspected in that window (headline); other views in the table
- **Data:** Chicago food inspections (2016+, violation text flags)
- **Verdict:** Weak
- **Notes:** 'Conversion' is persistence of need (the restaurant still shows pests at a later inspection), not a purchase: nearly every restaurant is already required to keep pest control, so this identifies accounts with a problem, probably under contract with a competitor, and measures how long the need persists. The target can only be seen at a later inspection; failed restaurants are re-inspected quickly, which inflates the raw rate, so the control is ordinary inspections without pest violations (same license key, 180-day gap, inspection-type mix matched) and the table also shows 15+ day recurrence and rates among re-inspected restaurants. Violation text is classified by keywords (headings 'INSECTS, RODENTS & ANIMALS NOT PRESENT' and 'rodent proofed' count; the generic garbage-container heading does not). Weekly volume is episodes (first pest finding after 180 clean days) in the last 52 weeks of data.
- Signals tested: 17,076; conversion 12.6% vs baseline 8.4%; median 8.0 days to target

| measure | signal | matched_control | lift |
| --- | --- | --- | --- |
| Any later pest violation within 180 days | 22.3% | 2.6% | 8.46 |
| ...only counting violations 15+ days later (not a quick re-check) | 8.5% | 2.5% | 3.33 |
| Any later pest violation, among restaurants re-inspected within 180 days | 33.0% | 8.7% | 3.80 |
| ...among re-inspected, 15+ days later | 12.6% | 8.4% | 1.50 |
| Share of the inspections that were a Fail | 62.0% | 16.2% | 3.82 |
| Share re-inspected within 180 days | 67.5% | — | — |

| year | n | conversion | control_conversion |
| --- | --- | --- | --- |
| 2016 | 966 | 20.0% | 4.6% |
| 2017 | 1891 | 20.0% | 2.9% |
| 2018 | 1457 | 21.5% | 2.0% |
| 2019 | 1845 | 22.7% | 2.2% |
| 2020 | 1181 | 21.7% | 1.6% |
| 2021 | 1542 | 21.5% | 1.9% |
| 2022 | 1661 | 24.3% | 2.0% |
| 2023 | 1811 | 23.2% | 2.5% |
| 2024 | 2037 | 22.6% | 2.1% |
| 2025 | 2088 | 23.0% | 2.5% |
| 2026 | 597 | 25.3% | 1.8% |

| strat | signals | signal_rate | controls | control_rate |
| --- | --- | --- | --- | --- |
| Canvass (routine) | 11229 | 21.0% | 37315 | 2.2% |
| Complaint | 3631 | 28.3% | 5354 | 4.3% |
| License (pre-opening) | 2105 | 19.0% | 9479 | 1.9% |
| Other | 55 | 16.4% | 116 | 1.7% |
| Re-inspection | 56 | 19.6% | 93 | 8.6% |

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
- **Notes:** The restaurant-inspection version of the pest idea is H23 (food inspections, added in round 3). Rat complaints are filed against the address of the nearby problem (alleys, garbage), not necessarily the owner's building, and baiting is done by the City, so the complaint is demand evidence, not a work order.
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

## H27 — Home-improvement mortgage loans per tract (HMDA, year Y) → residential permits per parcel (year Y+1)

- **Signal:** Tract's home-improvement loans per 1,000 residential parcels in year Y (top quintile of Chicago tracts)
- **Target:** Share of the tract's residential parcels with any permit (excl. signs and demolition) in year Y+1 (top vs bottom loan quintile)
- **Data:** CFPB HMDA home-improvement loans 2018-2025 (Cook County, loan years 2018-2024 paired with next-year permits, originated, loan_purpose=2), Chicago census tracts, Assessor parcels, permits
- **Verdict:** No signal
- **Notes:** Area-level index, not a lead: HMDA covers only mortgage-financed work (about 2,000 Chicago loans a year, so most tracts have a handful), is reported on 2010 tracts through 2021 and 2020 tracts from 2022 (each year is matched to its own tract map), and wealthier, higher-equity neighborhoods have both more loans and more permits. Quintiles are drawn per loan year with ties kept together (the bottom quintile is mostly tracts with zero loans). The 2020 pairs overlap the pandemic. The lift is not controlled for income; compare it with same_year_lift (the same quintiles' permit rates in the loan year itself) and the partial rank correlation (rank correlation of loans with next-year permits once the tract's current permit rate is held fixed). Permits attach to parcels through PIN or address, so rates are floors.

| loan_quintile | tract_years | parcels | loans | permitted_parcels_next_year | permit_rate_next_year | permit_rate_same_year |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1263 | 431273 | 0 | 15681 | 3.6% | 3.7% |
| 2 | 647 | 440465 | 896 | 13955 | 3.2% | 3.3% |
| 3 | 953 | 550938 | 2130 | 17633 | 3.2% | 3.3% |
| 4 | 954 | 527043 | 3508 | 17356 | 3.3% | 3.4% |
| 5 | 956 | 377376 | 4938 | 14453 | 3.8% | 4.0% |

| loan_year | tracts | loans | rho_loans_next | rho_now_next | rho_loans_now | partial_rho |
| --- | --- | --- | --- | --- | --- | --- |
| 2018 | 684 | 2196 | 0.14 | 0.69 | 0.16 | 0.04 |
| 2019 | 684 | 1903 | 0.07 | 0.58 | 0.07 | 0.04 |
| 2020 | 684 | 1122 | 0.15 | 0.58 | 0.13 | 0.09 |
| 2021 | 684 | 1294 | 0.07 | 0.61 | 0.09 | 0.02 |
| 2022 | 679 | 1817 | 0.06 | 0.58 | 0.07 | 0.02 |
| 2023 | 679 | 1459 | 0.04 | 0.54 | 0.01 | 0.03 |
| 2024 | 679 | 1681 | -0.03 | 0.55 | -0.05 | -0.00 |

## H28 — Radar-detected hail (NEXRAD) → reroof wave on blocks under the swath

- **Signal:** NEXRAD hail detection of at least 1 inch within ~2.5 km of the block on the day (a centroid footprint, not a MESH grid)
- **Target:** Reroof permits on those blocks in the next 120 days (vs the same blocks a year earlier, vs blocks with no detection within ~8 km)
- **Data:** NOAA SWDI nx3hail radar hail detections 2016-2026 (Chicago area), permits
- **Verdict:** No signal
- **Notes:** Retest of H04 with radar instead of spotter points. nx3hail gives one centroid per tracked hail cell per scan (probability, severe probability, estimated max size); a block counts as under the swath when a centroid of that size was within ~2.5 km that day, a stand-in for the true footprint (MESH grids would need GRIB processing). Day granularity is local time (UTC-6 approximation); detections only come from a box around the city, so blocks at its edge can be near storms we did not fetch. 'conversion' and 'baseline' are after/before permit ratios near and far; lift is their ratio. Insurance-paid repairs and unpermitted patching are invisible, so a null here is about permitted work only. Events from the last 125 days of permit data are excluded so every window is complete.

| definition | event_days | near_cell_days | near_after | near_year_before | far_after | far_year_before | near_ratio | far_ratio | lift | raw_cell_day_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Radar hail cell of 1 inch or more within ~2.5 km (headline) | 88 | 161546 | 10448 | 8935 | 44837 | 39704 | 1.17 | 1.13 | 1.04 | 1.12 |
| 1 inch or more with severe-hail probability 30+ | 85 | 152509 | 9831 | 8438 | 43173 | 38477 | 1.17 | 1.12 | 1.04 | 1.13 |
| 1.75 inches (golf ball) or more | 23 | 29365 | 1994 | 1606 | 8156 | 7364 | 1.24 | 1.11 | 1.12 | 1.22 |
| 1 inch or more, 270-day window (slower insurance-driven repairs) | 81 | 154104 | 18260 | 16108 | 80851 | 71104 | 1.13 | 1.14 | 1.00 | 1.08 |

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

## H24 — Restaurant plumbing violation → plumbing permit at the address within 365 days

- **Signal:** Restaurant inspection citing plumbing, leaks, sewage, drains or hand sinks, none at that address in the prior 365 days
- **Target:** Plumbing permit (any permit tagged plumbing) at the same address within 365 days
- **Data:** Chicago food inspections (2016+), permits
- **Verdict:** No signal
- **Notes:** Matched control: ordinary restaurant inspections without a plumbing finding at the same kind of address (one per address per 365 days, inspection-type mix standardized). Permits are matched on street address, so a plumbing permit for another tenant or the landlord counts; the control has the same bias. Many fixes (faucets, traps, sinks) need no permit, so conversion is a floor. Hand-sink text is often about soap and towels rather than plumbing, hence the strict view. The headline is the broad flag.
- Signals tested: 21,677; conversion 3.2% vs baseline 3.4%; median 125.0 days to target

| definition | signals | conversion | matched_control | lift | median_days | days_p25_p75 | share_converting_after_30_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Plumbing, leak, sewage, drain or hand-sink text | 21677 | 3.2% | 3.4% | 0.95 | 125.00 | 50-243 | 2.6% |
| Strict: plumbing, leak, sewage, drain, backflow (no hand sinks) | 19504 | 3.2% | 3.3% | 0.96 | 130.00 | 48-242 | 2.6% |
| Strict and the inspection failed | 8971 | 3.2% | 3.2% | 0.99 | 142.50 | 50-254 | 2.6% |

| year | n | conversion | control_conversion |
| --- | --- | --- | --- |
| 2016 | 4004 | 4.1% | 3.9% |
| 2017 | 2367 | 3.4% | 3.1% |
| 2018 | 1848 | 3.7% | 5.1% |
| 2019 | 2518 | 3.3% | 2.9% |
| 2020 | 1523 | 2.0% | 2.3% |
| 2021 | 1925 | 2.0% | 3.0% |
| 2022 | 1849 | 3.1% | 4.0% |
| 2023 | 2008 | 2.8% | 3.3% |
| 2024 | 2017 | 3.1% | 3.1% |
| 2025 | 1618 | 2.8% | 2.5% |

| strat | signals | signal_rate | controls | control_rate |
| --- | --- | --- | --- | --- |
| Canvass (routine) | 15244 | 3.3% | 15149 | 3.3% |
| Complaint | 3324 | 2.9% | 2059 | 3.1% |
| License (pre-opening) | 2927 | 3.0% | 2861 | 3.9% |
| Other | 58 | 3.4% | 33 | 12.1% |
| Re-inspection | 124 | 0.8% | 139 | 5.8% |

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

## H25 — Restaurant hood/ventilation violation → HVAC or mechanical permit at the address within 365 days

- **Signal:** Restaurant inspection citing a hood, exhaust or duct, none at that address in the prior 365 days
- **Target:** HVAC/mechanical permit (permits tagged hvac) at the same address within 365 days
- **Data:** Chicago food inspections (2016+), permits
- **Verdict:** No signal
- **Notes:** Hood cleaning and filter swaps need no permit, so only replacements and new installs appear. Permits are matched on street address (a building's other tenants and landlord count; the control has the same bias). The broad ventilation heading (#56 'ventilation & lighting' and the older '#38 ventilation') is shown separately because it also covers lighting.
- Signals tested: 7,503; conversion 1.8% vs baseline 2.0%; median 127.0 days to target

| definition | signals | conversion | matched_control | lift | median_days | days_p25_p75 | share_converting_after_30_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hood, exhaust or duct text → HVAC/mechanical permit | 7503 | 1.8% | 2.0% | 0.86 | 127.00 | 70-229 | 1.5% |
| Any ventilation heading (includes lighting) → HVAC/mechanical permit | 16535 | 2.1% | 2.2% | 0.98 | 136.50 | 65-236 | 1.8% |
| Hood, exhaust or duct text → hood/exhaust/kitchen-vent permit | 7503 | 0.4% | 0.4% | 1.02 | 206.00 | 98-279 | 0.4% |

| year | n | conversion | control_conversion |
| --- | --- | --- | --- |
| 2016 | 1171 | 2.3% | 2.7% |
| 2017 | 954 | 2.1% | 2.4% |
| 2018 | 714 | 1.1% | 2.7% |
| 2019 | 811 | 2.1% | 2.3% |
| 2020 | 445 | 1.1% | 1.7% |
| 2021 | 730 | 1.4% | 1.8% |
| 2022 | 784 | 1.3% | 1.7% |
| 2023 | 658 | 2.1% | 1.6% |
| 2024 | 701 | 1.7% | 1.6% |
| 2025 | 535 | 1.5% | 1.2% |

| strat | signals | signal_rate | controls | control_rate |
| --- | --- | --- | --- | --- |
| Canvass (routine) | 5479 | 1.8% | 21830 | 2.0% |
| Complaint | 1311 | 1.4% | 2982 | 2.0% |
| License (pre-opening) | 636 | 2.0% | 4781 | 2.0% |
| Other | 28 | 3.6% | 43 | 7.0% |
| Re-inspection | 49 | 0.0% | 111 | 0.9% |

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
