# Signal lab — 2026-11-15

Creative lead hypotheses tested against Chicago history. Reproduce with `uv run python research/signal_lab/lab.py`. Verdicts: **Strong** = lift ≥ 3 with ≥ 5 signals/week; **Useful** = lift ≥ 1.8; **Weak** = lift ≥ 1.25; otherwise **No signal**. Permits capture permitted work only, so conversion rates are floors.

## Leaderboard

| # | Hypothesis | Verdict | Lift | Conversion | Baseline | Signals/week | Who it's for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H08 | 311 porch inspection request → porch permit | **Strong** | 11.44× | 13.7% | 1.2% | 7.10 | Porch builders |
| H07 | 311 building complaint → city citation (earlier lead) | **Strong** | 5.85× | 31.6% | 5.4% | 255.40 | Porch, masonry, roofing, general repair contractors |
| H13 | Which buildings need masonry work: walls × age | **Useful** | 2.86× | 1.4% | 0.5% | — | Masons, tuckpointers |
| H09 | Vacant-building complaint → property sells | **Useful** | 2.49× | 19.4% | 7.8% | 20.50 | Investors' contractors, rehab GCs, property managers (and investors themselves) |
| H01 | Neighbors went solar → you go solar | **Useful** | 2.41× | 1.0% | 0.4% | 33.40 | Solar installers |
| H12 | Which houses re-roof: age × roof material | **Useful** | 2.37× | 2.2% | 0.9% | — | Roofers, solar installers |
| H10 | Complaint about unpermitted work → permit gets pulled | **Useful** | 2.17× | 18.9% | 8.7% | 70.60 | Expediters, architects, GCs who legalize work |
| H03 | Neighbors re-roofed → you re-roof | **Useful** | 2.16× | 0.7% | 0.3% | — | Roofers |
| H14 | Which homes pull HVAC permits: A/C × heat type | **Useful** | 2.16× | 0.3% | 0.1% | — | HVAC contractors |
| H15 | Assessor condition rating → renovation permits | **Weak** | 1.41× | 0.6% | 0.4% | — | General contractors, rehab crews |
| H02 | New roof → solar within 2 years | **No signal** | 1.18× | 1.0% | 0.8% | 90.20 | Solar installers (and roofers partnering with them) |
| H16 | Poor energy score → mechanical/electrical upgrades | **No signal** | 1.08× | 17.7% | 16.4% | — | Commercial HVAC, electrical, lighting retrofit, energy services |
| H04 | Hail ≥ 1 inch → reroof wave | **No signal** | 0.98× | 1.14 | 1.17 | 0.10 | Roofers, gutter and siding contractors, restoration |
| H05 | Damaging wind (60+ kt) → reroof wave | **No signal** | 0.90× | 1.04 | 1.16 | 0.20 | Roofers, gutter and siding contractors, restoration |
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
