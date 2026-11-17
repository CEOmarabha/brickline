# Signal lab — 2026-11-16

Creative lead hypotheses tested against Chicago history. Reproduce with `uv run python research/signal_lab/lab.py`. Verdicts: **Strong** = lift ≥ 3 with ≥ 5 signals/week; **Useful** = lift ≥ 1.8; **Weak** = lift ≥ 1.25; otherwise **No signal**. Permits capture permitted work only, so conversion rates are floors.

## Leaderboard

| # | Hypothesis | Verdict | Lift | Conversion | Baseline | Signals/week | Who it's for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H08 | 311 porch inspection request → porch permit | **Strong** | 11.44× | 13.7% | 1.2% | 7.10 | Porch builders |
| H33 | Build-out permit at a space with no licensee → a new business registers there within 365 days | **Strong** | 10.25× | 15.2% | 1.5% | 17.70 | Sellers to brand-new businesses: signage, POS/payments, insurance, cleaning, security, furniture, telecom, accountants, and the brokers and GCs that serve them |
| H26 | Restaurant 'Out of Business' → new food license or renovation permit at the address within 365 days | **Strong** | 10.24× | 32.3% | 3.2% | 13.10 | Restaurant build-out contractors, equipment dealers, brokers, signage |
| H34 | Council zoning reclassification introduced at an address → new-construction permit there within 730 days | **Strong** | 9.69× | 17.1% | 0.9% | 8.60 | GCs, commercial subcontractors, suppliers and brokers who want the earliest public trace of a project |
| H35 | Council zoning reclassification at an address → $1M+ new construction or renovation permit within 730 days | **Strong** | 7.39× | 11.8% | 0.7% | 8.60 | Commercial subcontractors and GCs (the project is public before any permit or GC is) |
| H17 | Complaint chain: 311 complaint → porch/masonry citation → permit (when to mail) | **Strong** | 6.26× | 12.3% | 2.0% | 47.80 | Porch builders, masons and tuckpointers |
| H07 | 311 building complaint → city citation (earlier lead) | **Strong** | 5.85× | 31.6% | 5.4% | 255.40 | Porch, masonry, roofing, general repair contractors |
| H30 | Commercial and multifamily reroof cycle model (as-of quarters 2016-2023, time-split validation) | **Strong** | 4.59× | 3.6% | 0.8% | 76.90 | Commercial roofers, roof-coating and sheet-metal contractors, roof inspection and consulting firms |
| H36 | ADU preapproval application → ADU-related or any new construction/renovation permit at the address | **Strong (provisional)** | 4.14× | 7.7% | 0.3% | 12.30 | ADU builders, architects and GCs; lenders and suppliers for coach houses and basement or attic units |
| H29 | Which trades are still open after a $1M+ commercial/multifamily permit (signs, elevator, electrical, ...) | **Strong** | 3.06× | 62.1% | 20.3% | 8.70 | Sign shops, elevator service, electricians and other trade subcontractors; suppliers selling to them |
| H40 | Renovation, new-construction or demolition permit at an address → a dumpster permit on the public way there within 180 days | **Strong** | 3.03× | 9.6% | 3.2% | 116.50 | Roll-off dumpster haulers (and their sales reps); GCs only as the buyers the haulers serve |
| H38 | Event series held in each of the last 2 years → held again next year at the same time of year | **Useful** | 2.89× | 53.4% | 18.5% | 4.10 | Event-service sellers (rentals, staging, security, catering, porta-potties, insurance) and the venues and sponsors around recurring events |
| H13 | Which buildings need masonry work: walls × age | **Useful** | 2.85× | 1.4% | 0.5% | — | Masons, tuckpointers |
| H09 | Vacant-building complaint → property sells | **Useful** | 2.49× | 19.4% | 7.8% | 20.50 | Investors' contractors, rehab GCs, property managers (and investors themselves) |
| H01 | Neighbors went solar → you go solar | **Useful** | 2.41× | 1.0% | 0.4% | 33.40 | Solar installers |
| H12 | Which houses re-roof: age × roof material | **Useful** | 2.37× | 2.1% | 0.9% | — | Roofers, solar installers |
| H14 | Which homes pull HVAC permits: A/C × heat type | **Useful** | 2.17× | 0.3% | 0.1% | — | HVAC contractors |
| H10 | Complaint about unpermitted work → permit gets pulled | **Useful** | 2.17× | 18.9% | 8.7% | 70.60 | Expediters, architects, GCs who legalize work |
| H03 | Neighbors re-roofed → you re-roof | **Useful** | 2.16× | 0.7% | 0.3% | — | Roofers |
| H37 | Zoning reclassification + sale of the parcel in the prior year vs zoning alone → new construction | **Weak** | 1.50× | 31.4% | 20.9% | 2.00 | Same as H34 (does adding a recent sale sharpen the zoning list?) |
| H23 | Restaurant pest violation → another pest violation within 180 days (recurring pest-control need) | **Weak** | 1.50× | 12.6% | 8.4% | 44.80 | Pest-control companies |
| H15 | Assessor condition rating → renovation permits | **Weak** | 1.48× | 0.6% | 0.4% | — | General contractors, rehab crews |
| H32 | Storefront turnover (new licensee after the previous one lapsed) → build-out permit at the address | **Weak** | 1.38× | 3.3% | 2.4% | 10.70 | Build-out contractors, signage, equipment and fixtures suppliers, brokers, cleaning and security vendors |
| H20 | 311 rodent complaint → building/pest violation (pest-control demand proxy) | **Weak** | 1.31× | 1.9% | 1.5% | 545.50 | Pest control, sanitation and property-management services |
| H21 | New food license with no recent build-out permit (as-is takeover) → permits after opening | **Descriptive** | —× | 12.1% | 51.7% | 14.40 | Signage, cleaning, security, small-trade contractors serving new restaurants |
| H22 | Seasonality: when permits are pulled and how fast citations turn into permits, by month | **Descriptive** | —× | — | — | — | Porch, masonry and roofing contractors (mailing calendar) |
| H39 | How far ahead do event permits become visible? (Park District feed, CDOT street-event permits) | **Descriptive** | —× | — | — | — | Event-service sellers deciding whether permits can find NEW events 3-9 months ahead |
| H41 | Commercial cleaning: when is a space 'built out, about to open'? Build-out permit, pre-opening inspection, license | **Descriptive** | —× | — | — | — | Commercial (post-construction and janitorial) cleaning companies; also signage, POS, security sellers |
| H31 | New business license + build-out permit before it → business still operating 18-30 months later | **No signal** | 1.21× | 70.7% | 58.6% | 10.90 | B2B sellers to new businesses (insurance, payments/POS, signage, cleaning, security, accounting) who want to know which registrations are real and lasting |
| H02 | New roof → solar within 2 years | **No signal** | 1.18× | 1.0% | 0.8% | 90.20 | Solar installers (and roofers partnering with them) |
| H16 | Poor energy score → mechanical/electrical upgrades | **No signal** | 1.08× | 17.7% | 16.4% | — | Commercial HVAC, electrical, lighting retrofit, energy services |
| H27 | Home-improvement mortgage loans per tract (HMDA, year Y) → residential permits per parcel (year Y+1) | **No signal** | 1.05× | 3.8% | 3.6% | — | All residential trades (neighborhood demand index for mail targeting) |
| H28 | Radar-detected hail (NEXRAD) → reroof wave on blocks under the swath | **No signal** | 1.04× | 116.9% | 112.9% | 0.20 | Roofers, gutter and siding contractors, restoration |
| H19 | 311 'tree emergency' → roofing or porch permit (storm-damage proxy) | **No signal** | 1.00× | 0.5% | 0.5% | 405.20 | Tree services, roofers, porch builders |
| H04 | Hail ≥ 1 inch → reroof wave | **No signal** | 0.98× | 1.14 | 1.17 | 0.10 | Roofers, gutter and siding contractors, restoration |
| H24 | Restaurant plumbing violation → plumbing permit at the address within 365 days | **No signal** | 0.95× | 3.2% | 3.4% | 55.70 | Commercial plumbers, drain and grease-trap contractors |
| H05 | Damaging wind (60+ kt) → reroof wave | **No signal** | 0.90× | 1.04 | 1.16 | 0.20 | Roofers, gutter and siding contractors, restoration |
| H18 | Repeat investors (3+ purchases in 24 months) renovate more and faster than one-off company buyers | **No signal** | 0.88× | 31.7% | 36.0% | 16.40 | Rehab GCs, subs working for investors, property managers |
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

## H33 — Build-out permit at a space with no licensee → a new business registers there within 365 days

- **Signal:** Renovation/alteration, interior build-out or new-construction permit at an address of class commercial/industrial (5xx), mixed-use (212) or multifamily 7+ (3xx) with no business license in force at that date (one per address per 365 days)
- **Target:** A new account's first (ISSUE) premises license at the address within 365 days after the permit; control = same-class address-quarters with no licensee in force and no renovation permit within a year either side, matched on class and year
- **Data:** Permits (renovation, build-out text, new construction), Chicago business licenses 2014+, parcel classes from sales
- **Verdict:** Strong
- **Notes:** Reasoning: H32 shows build-outs mostly precede the new license, and the permit is public the day it is issued while the license only appears when issued, so the permit is the earlier, observable signal for anyone selling to a new business. Class comes from the latest sale or residential file, so addresses with no sale since 2010 are not in the universe. 'In force' uses license terms and cancellations known on the permit date. The license group of the first new licensee is a result, not something the permit tells you in advance. Premises-based licenses only (same filter as H31); unlicensed businesses, professional offices without a license and licenses under 2014 history are invisible, so conversion is a floor. Addresses are by street address without unit, so a permit for one tenant counts for the whole building. Signals stop 365 days before the newest license record.
- Signals tested: 9,011; conversion 15.2% vs baseline 1.5%; median 157.0 days to target

| year | signals | new_license_rate | control_rate | lift |
| --- | --- | --- | --- | --- |
| 2016 | 1033 | 17.7% | 1.6% | 11.31 |
| 2017 | 1046 | 16.5% | 1.6% | 10.60 |
| 2018 | 1041 | 16.4% | 1.5% | 11.30 |
| 2019 | 941 | 13.8% | 1.4% | 9.82 |
| 2020 | 890 | 10.7% | 1.2% | 9.00 |
| 2021 | 820 | 14.6% | 1.5% | 9.99 |
| 2022 | 927 | 13.6% | 1.5% | 9.31 |
| 2023 | 834 | 13.9% | 1.5% | 9.03 |
| 2024 | 805 | 16.9% | 1.5% | 11.04 |
| 2025 | 674 | 17.4% | 1.7% | 10.49 |

| class | signals | new_license_rate | control_rate | lift |
| --- | --- | --- | --- | --- |
| commercial/industrial (5xx) | 4028 | 21.3% | 1.2% | 17.28 |
| mixed-use up to 6 units (212) | 2047 | 16.2% | 3.2% | 5.10 |
| multifamily 7+ (3xx) | 2936 | 6.0% | 0.6% | 9.55 |

| permit_cost | signals | new_license_rate | control_rate | lift | busy_control_rate | lift_vs_busy |
| --- | --- | --- | --- | --- | --- | --- |
| no cost reported | 13 | 15.4% | 1.2% | 12.57 | 5.6% | 2.74 |
| under $25k | 2300 | 11.1% | 1.6% | 6.73 | 6.2% | 1.79 |
| $25k-$100k | 2740 | 15.3% | 1.5% | 10.43 | 5.8% | 2.61 |
| $100k+ | 3958 | 17.5% | 1.4% | 12.54 | 6.2% | 2.80 |

| license_group | new_licenses | median_days | p25_days | p75_days | share_of_conversions |
| --- | --- | --- | --- | --- | --- |
| food & drink | 760 | 165.00 | 105.75 | 240.00 | 55.6% |
| retail | 214 | 120.00 | 72.00 | 207.00 | 15.7% |
| other | 159 | 153.00 | 85.00 | 255.50 | 11.6% |
| health/fitness/childcare | 136 | 165.50 | 90.75 | 255.50 | 9.9% |
| personal services/beauty | 75 | 127.00 | 72.00 | 211.00 | 5.5% |
| auto | 23 | 163.00 | 80.00 | 339.00 | 1.7% |

- Key numbers (rates are fractions): signals = 9011; conversion = 0.15; baseline = 0.01; lift = 10.25; signals_per_week = 17.67; control_events = 1294317; control_raw_rate = 0.01; busy_control_events = 12012; busy_control_rate = 0.06; lift_vs_busy_control = 2.48; own_earlier_window = 0.00; lift_vs_own_earlier = 39.06; median_days = 157.00; days_p25 = 92.50; days_p75 = 238.50; within_90_days_share = 0.24; within_180_days_share = 0.59; converted_after_30_days = 0.94; rate_if_license_31_plus_days_later = 0.14

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

## H34 — Council zoning reclassification introduced at an address → new-construction permit there within 730 days

- **Signal:** A zoning reclassification ordinance introduced in Council at a parsed street address (one signal per address per 730 days; address ranges also match permits at same-side addresses inside the range). Second view: passed ordinances measured from the passage date
- **Target:** PERMIT - NEW CONSTRUCTION at the address or inside its range within 730 days after the signal date; baselines = the same addresses' earlier 730-day window, comparable addresses (same community area, same class bucket, same year) with no zoning change within 730 days either side, and the subset of those with a permit in the prior year
- **Data:** City Clerk eLMS zoning reclassification ordinances 2012+ (title addresses), Chicago permits, parcel classes from sales and the residential file, today's zoning map (target district of passed ordinances)
- **Verdict:** Strong
- **Notes:** Headline lift is the smaller of the two baselines named first (own earlier window, comparable addresses). Signals stop 730 days before the newest permit. Introduction dates since 2012-01-01; one application (App No.) is one project even when an original and a substitute ordinance exist (earliest introduction, earliest passage). Class comes from the latest sale or residential file, so addresses with neither are 'unknown class'. The target district of a passed ordinance is read from today's zoning map (matched by application number or Clerk record number, so ordinances later superseded are 'no map match'); titles state from/to districts for only a handful of matters. 'Never passed' is hindsight, not a filter available at introduction. Permit addresses are by street address without unit; multi-address titles give one signal per address.
- Signals tested: 6,869; conversion 17.1% vs baseline 0.9%; median 313.0 days to target

| split | signals | conversion | exact_address_rate | own_earlier_rate | control_rate | lift_vs_control | lift_vs_own | median_days | share_before_intro |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all introduced (known at introduction) | 6869 | 17.1% | 10.3% | 1.8% | 0.9% | 11.26 | 9.69 | 313.00 | 7.7% |
| introduced, later passed (hindsight) | 6121 | 18.0% | 10.9% | 1.7% | 0.9% | 11.91 | 10.48 | 311.50 | 7.4% |
| introduced, never passed (hindsight) | 748 | 9.6% | 5.9% | 2.1% | 1.0% | 6.17 | 4.50 | 332.50 | 10.0% |

| split | signals | conversion | exact_address_rate | own_earlier_rate | control_rate | lift_vs_control | lift_vs_own | median_days | share_before_intro |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all passed (from passage date) | 6005 | 19.4% | 11.5% | 1.8% | 0.9% | 12.58 | 10.81 | 237.00 | 7.4% |
| target district: business/commercial (B/C) | 1883 | 17.3% | 10.9% | 1.0% | 0.9% | 11.74 | 18.06 | 271.00 | 5.5% |
| target district: no map match (unknown) | 1437 | 16.2% | 9.3% | 2.4% | 1.0% | 9.11 | 6.66 | 288.00 | 8.4% |
| target district: residential (RS/RT/RM) | 1331 | 26.1% | 21.0% | 0.8% | 0.9% | 23.93 | 34.70 | 175.00 | 4.2% |
| target district: planned development (PD) | 1093 | 21.7% | 6.3% | 3.9% | 0.9% | 7.40 | 5.51 | 238.00 | 14.1% |
| target district: downtown (D) | 106 | 17.9% | 5.7% | 0.9% | 1.1% | 4.95 | 19.00 | 309.00 | 6.6% |
| target district: manufacturing (M/PMD) | 106 | 2.8% | 0.0% | 0.9% | 0.5% | 0.00 | 3.00 | 34.00 | 2.8% |
| target district: other (open space/transport) | 49 | 6.1% | 0.0% | 0.0% | 0.5% | 0.00 | — | 492.00 | 4.1% |
| App No. with T1 suffix (Type 1) | 1547 | 27.0% | 18.8% | 0.6% | 1.2% | 15.98 | 41.70 | 243.00 | 4.7% |
| App No. without T1 suffix | 4458 | 16.8% | 9.0% | 2.2% | 0.8% | 10.90 | 7.65 | 230.00 | 8.4% |

| target | signals | conversion | exact_address_rate | own_earlier_rate | control_rate | lift_vs_control | lift_vs_own |
| --- | --- | --- | --- | --- | --- | --- | --- |
| new construction (headline) | 6869 | 17.1% | 10.3% | 1.8% | 0.9% | 11.26 | 9.69 |
| new construction or renovation, cost $100k+ | 6869 | 27.6% | 18.0% | 4.2% | 2.4% | 7.46 | 6.51 |

| year | signals | conversion | own_earlier_rate | control_rate | lift_vs_control | lift_vs_own |
| --- | --- | --- | --- | --- | --- | --- |
| 2012 | 471 | 13.6% | 3.0% | 0.9% | 7.99 | 4.57 |
| 2013 | 444 | 18.2% | 0.7% | 1.1% | 11.01 | 27.00 |
| 2014 | 586 | 22.5% | 0.7% | 1.2% | 12.33 | 33.00 |
| 2015 | 639 | 21.0% | 1.3% | 1.0% | 11.27 | 16.75 |
| 2016 | 604 | 22.7% | 0.7% | 1.0% | 14.70 | 34.25 |
| 2017 | 633 | 22.6% | 1.7% | 1.0% | 12.46 | 13.00 |
| 2018 | 606 | 21.3% | 1.7% | 0.9% | 16.55 | 12.90 |
| 2019 | 557 | 12.7% | 3.2% | 0.8% | 10.59 | 3.94 |
| 2020 | 421 | 15.0% | 1.7% | 0.8% | 10.25 | 9.00 |
| 2021 | 499 | 11.4% | 2.6% | 1.1% | 4.92 | 4.38 |
| 2022 | 524 | 11.5% | 1.5% | 0.6% | 9.88 | 7.50 |
| 2023 | 388 | 11.9% | 2.6% | 0.6% | 11.97 | 4.60 |
| 2024 | 497 | 11.1% | 2.2% | 0.7% | 9.17 | 5.00 |

- Key numbers (rates are fractions): signals = 6869; projects = 4957; project_conversion = 0.23; conversion = 0.17; baseline = 0.01; lift = 9.69; lift_vs_control = 11.26; conversion_exact_address = 0.10; lift_vs_control_site_vs_exact_control = 18.63; nc_permits_since_2014 = 20088; nc_permits_with_zoning_signal_before = 1849; nc_permit_coverage_share = 0.09; control_matched_share = 1.00; own_earlier_window = 0.02; lift_vs_own_earlier = 9.69; busy_control_rate = 0.02; lift_vs_busy_control = 7.68; signals_per_week = 8.60; projects_per_week_recent = 6.50; median_days = 313.00; days_p25 = 189.00; days_p75 = 454.00; permitted_before_intro_730 = 0.02; permitted_before_intro_ever = 0.08; passed_signals = 6005; passed_conversion = 0.19; passed_control_rate = 0.01; passed_conversion_exact_address = 0.12; passed_lift_vs_control = 12.58; passed_own_earlier_window = 0.02; passed_lift_vs_own_earlier = 10.81; passed_busy_control_rate = 0.02; passed_lift_vs_busy_control = 8.25; passed_median_days = 237.00; passed_days_p25 = 133.50; passed_days_p75 = 403.00; passed_permitted_before_intro = 0.07; passed_permitted_between_intro_and_passage = 0.01; passed_permitted_before_passage_730 = 0.02

## H35 — Council zoning reclassification at an address → $1M+ new construction or renovation permit within 730 days

- **Signal:** Same signals as H34 (introduction; passed ordinances from the passage date)
- **Target:** PERMIT - NEW CONSTRUCTION or RENOVATION/ALTERATION with reported cost of $1,000,000+ at the address or inside its range within 730 days; GC opportunity = share of those permits whose named general contractor appears on no earlier permit at the site
- **Data:** City Clerk eLMS zoning reclassification ordinances 2012+, Chicago permits and permit parties
- **Verdict:** Strong
- **Notes:** Same controls and caveats as H34 (headline lift is the smaller of own-earlier-window and comparable-address lifts). 'GC new to the address' uses the contractor name key on the first $1M+ permit after the signal against every earlier permit at the site's addresses (role 'general contractor' only; owner-as-GC and blank GCs are counted separately as 'no GC named'). Names are cut at 30 characters, so spelling variants count as new (a ceiling on 'open'). Permit contractor names are known only once the permit is issued, so the opening for a GC is the time between the zoning signal and that permit.
- Signals tested: 6,869; conversion 11.8% vs baseline 0.7%; median 351.0 days to target

| split | signals | conversion | exact_address_rate | own_earlier_rate | control_rate | lift_vs_control | lift_vs_own | median_days | share_before_intro |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all passed (from passage date) | 6005 | 13.9% | 6.7% | 1.5% | 0.6% | 10.32 | 9.14 | 279.00 | 5.9% |
| target district: business/commercial (B/C) | 1883 | 13.8% | 7.8% | 0.9% | 0.6% | 13.78 | 16.25 | 286.50 | 3.5% |
| target district: no map match (unknown) | 1437 | 13.4% | 6.8% | 1.9% | 0.7% | 9.23 | 6.89 | 307.00 | 6.8% |
| target district: residential (RS/RT/RM) | 1331 | 6.9% | 5.0% | 0.2% | 0.3% | 19.74 | 30.67 | 270.00 | 1.6% |
| target district: planned development (PD) | 1093 | 23.1% | 7.0% | 3.8% | 1.0% | 6.79 | 6.00 | 232.00 | 14.7% |
| target district: downtown (D) | 106 | 27.4% | 12.3% | 0.9% | 2.3% | 5.33 | 29.00 | 303.00 | 4.7% |
| target district: manufacturing (M/PMD) | 106 | 0.9% | 0.0% | 0.9% | 0.3% | 0.00 | 1.00 | 306.00 | 1.9% |
| target district: other (open space/transport) | 49 | 10.2% | 2.0% | 0.0% | 0.4% | 5.35 | — | 210.00 | 6.1% |

| year | first_big_permits | gc_new_share |
| --- | --- | --- |
| 2012 | 49 | 77.1% |
| 2013 | 54 | 72.2% |
| 2014 | 100 | 78.8% |
| 2015 | 99 | 75.5% |
| 2016 | 86 | 82.6% |
| 2017 | 93 | 81.7% |
| 2018 | 69 | 85.5% |
| 2019 | 49 | 67.3% |
| 2020 | 36 | 71.4% |
| 2021 | 45 | 77.8% |
| 2022 | 50 | 89.8% |
| 2023 | 35 | 65.7% |
| 2024 | 48 | 72.9% |

| year | signals | conversion | own_earlier_rate | control_rate | lift_vs_control | lift_vs_own |
| --- | --- | --- | --- | --- | --- | --- |
| 2012 | 471 | 10.4% | 3.2% | 0.5% | 8.96 | 3.27 |
| 2013 | 444 | 12.2% | 0.7% | 0.6% | 11.09 | 18.00 |
| 2014 | 586 | 17.1% | 1.4% | 0.7% | 12.06 | 12.50 |
| 2015 | 639 | 15.5% | 0.9% | 0.7% | 11.14 | 16.50 |
| 2016 | 604 | 14.2% | 0.5% | 0.6% | 13.06 | 28.67 |
| 2017 | 633 | 14.7% | 1.3% | 0.6% | 9.70 | 11.62 |
| 2018 | 606 | 11.4% | 1.7% | 0.7% | 8.10 | 6.90 |
| 2019 | 557 | 8.8% | 1.8% | 0.7% | 6.52 | 4.90 |
| 2020 | 421 | 8.6% | 1.2% | 0.5% | 7.16 | 7.20 |
| 2021 | 499 | 9.0% | 2.2% | 0.8% | 4.73 | 4.09 |
| 2022 | 524 | 9.5% | 2.3% | 0.6% | 8.30 | 4.17 |
| 2023 | 388 | 9.0% | 2.3% | 0.7% | 5.31 | 3.89 |
| 2024 | 497 | 9.7% | 2.0% | 0.8% | 7.89 | 4.80 |

- Key numbers (rates are fractions): signals = 6869; projects = 4957; project_conversion = 0.16; conversion = 0.12; baseline = 0.01; lift = 7.39; lift_vs_control = 8.91; conversion_exact_address = 0.06; own_earlier_window = 0.02; lift_vs_own_earlier = 7.39; busy_control_rate = 0.02; lift_vs_busy_control = 3.79; signals_per_week = 8.60; median_days = 351.00; days_p25 = 229.00; days_p75 = 496.00; permitted_big_before_intro_730 = 0.02; permitted_big_before_intro_ever = 0.06; passed_signals = 6005; passed_conversion = 0.14; passed_control_rate = 0.01; passed_conversion_exact_address = 0.07; passed_lift_vs_control = 10.32; passed_own_earlier_window = 0.02; passed_lift_vs_own_earlier = 9.14; passed_median_days = 279.00; passed_days_p25 = 154.00; passed_days_p75 = 434.00; big_permits_since_2014 = 10237; big_permits_with_zoning_signal_before = 1133; big_permit_coverage_share = 0.11; first_big_permits = 813; big_permit_with_gc_share = 0.99; big_permit_no_gc_named_share = 0.01; gc_new_to_address_share = 0.78; gc_new_to_address_share_passed = 0.78; no_gc_at_address_before_share = 0.47; any_permit_at_address_before_share = 0.76

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

## H30 — Commercial and multifamily reroof cycle model (as-of quarters 2016-2023, time-split validation)

- **Signal:** Parcel-quarter features known at the as-of date: years since the last roof permit, class code, building age, roofing violation in the prior 2 years, hail detection within ~1 km in the prior 3 years
- **Target:** A roof permit issued at the parcel in the 365 days after the as-of date. Train: as-of dates 2016-2019; test: 2021-2023 (precision among the top 100 / 1,000 parcels per quarter, pooled over 12 quarters)
- **Data:** Permits (roofing flag), violations (roofing), Cook County sales (class), residential characteristics and energy benchmarking (year built), NEXRAD hail detections, geocoded addresses
- **Verdict:** Strong
- **Notes:** Universe at each as-of date: parcels whose class (latest sale on or before the date) is 5xx commercial or 3xx multifamily 7+ ('main', parcels with no sale since 2010 are absent), and, separately, every 2-6 unit flat or mixed-use parcel of class 211/212 in the Assessor residential file ('flats'). A sale entering the universe is a known-at-date fact but sales are also a renovation trigger, so main-segment rates include newly sold buildings. Rates come from back-off cell tables (full cell, then dropping hail, violation, age, class in that order) with a minimum cell size chosen on a time-split validation (fit on as-of dates through 2017-01-01, validate 2018-01-01 to 2019-10-01) and shrunk toward the base rate with 100 pseudo-observations. Ties in predicted rate are broken by a hash of parcel and date, so the top lists are deterministic. 'none on record' for the last roof permit is left-censored: permits start in 2006, so it means no roof permit in the last 10 years at the 2016 as-of dates and 17 years at the 2023 ones. Building age comes from the residential file or energy benchmarking (buildings of 50k+ sq ft) and is 'unknown' for most commercial parcels, so it carries little signal there; the 2025-2026 assessor snapshot describes today's building, and buildings built after the as-of year are treated as unknown. Hail detections start in March 2016, so the 3-year lookback is short for the 2016-2018 training dates. Parcel coordinates come from geocoded permits, violations, 311 requests and business licenses at the parcel's address, so parcels with no such record have 'no location'. The target is a permit, not a roof: commercial reroofs are often unpermitted or filed with other work, so every rate is a floor; roofing violation and roof-permit history only attach to a parcel through PIN or address.

| seg | rows | parcels | train_rate | test_rate | test_rows | age_known_share | hail_located_share | roof_on_record_test_share | roof_violation_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flats | 4119200 | 128725 | 0.4% | 0.4% | 1544700 | 99.4% | 43.0% | 5.4% | 0.7% |
| main | 774848 | 31787 | 1.1% | 0.8% | 347238 | 3.8% | 44.4% | 10.3% | 0.5% |

| seg | roof_bucket | train_rows | train_rate | test_rows | test_rate |
| --- | --- | --- | --- | --- | --- |
| flats | 12y+ | 2022 | 1.5% | 18410 | 0.6% |
| flats | 3-7y | 26583 | 0.5% | 21558 | 0.5% |
| flats | 7-12y | 26764 | 0.7% | 24390 | 0.4% |
| flats | <3y | 21336 | 1.2% | 19299 | 1.2% |
| flats | none on record | 1982895 | 0.4% | 1461043 | 0.4% |
| main | 12y+ | 454 | 4.0% | 4807 | 1.9% |
| main | 3-7y | 9866 | 2.8% | 11891 | 1.9% |
| main | 7-12y | 5952 | 3.7% | 10404 | 1.7% |
| main | <3y | 10458 | 5.3% | 8591 | 4.5% |
| main | none on record | 296494 | 0.8% | 311545 | 0.6% |

| model | rows | base_rate | p_at_100_rate | hits_at_100 | lift_at_100 | p_at_100_low_rate | p_at_100_high_rate | p_at_1000_rate | hits_at_1000 | lift_at_1000 | p_at_1000_low_rate | p_at_1000_high_rate | top10_capture_share | log_loss_skill_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full model | 347238 | 0.8% | 7.4% | 89 | 9.57 | 6.1% | 9.0% | 3.6% | 427 | 4.59 | 3.2% | 3.9% | 30.5% | 5.3% |
| years since last roof permit only | 347238 | 0.8% | 4.7% | 56 | 6.02 | 3.6% | 6.0% | 3.8% | 452 | 4.86 | 3.4% | 4.1% | 32.2% | 2.3% |
| building age only | 347238 | 0.8% | 6.2% | 75 | 8.06 | 5.0% | 7.8% | 3.2% | 382 | 4.11 | 2.9% | 3.5% | 20.7% | 0.9% |
| class code only | 347238 | 0.8% | 2.7% | 32 | 3.44 | 1.9% | 3.7% | 2.2% | 260 | 2.79 | 1.9% | 2.4% | 20.7% | 1.8% |
| random (expected) | 347238 | 0.8% | 0.8% | — | 1.00 | — | — | 0.8% | — | 1.00 | — | — | 10.0% | 0.0% |

| variant | p_at_100_rate | p_at_1000_rate | lift_at_1000 | top10_capture_share | log_loss_skill_share | lift_change_vs_full | skill_change_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| drop roof (years since last roof permit) | 5.5% | 2.8% | 3.57 | 28.8% | 4.6% | -1.02 | -0.7% |
| drop cls (class code) | 7.7% | 3.3% | 4.21 | 33.0% | 5.4% | -0.38 | 0.1% |
| drop age (building age) | 7.0% | 3.5% | 4.55 | 30.5% | 5.1% | -0.04 | -0.3% |
| drop viol (roofing violation in prior 2 years) | 7.4% | 3.5% | 4.48 | 29.9% | 5.3% | -0.11 | -0.1% |
| drop hail (hail detection within ~1 km in prior 3 years) | 7.4% | 3.8% | 4.87 | 30.8% | 4.4% | 0.28 | -0.9% |
| hail kept but without its 'no location' flag (merged into 0) | 8.5% | 3.4% | 4.44 | 30.8% | 4.7% | -0.15 | -0.7% |

| decile | rows | predicted_rate | observed_rate | hits |
| --- | --- | --- | --- | --- |
| 1 | 34724 | 0.1% | 0.1% | 49 |
| 2 | 34724 | 0.2% | 0.1% | 52 |
| 3 | 34724 | 0.3% | 0.4% | 152 |
| 4 | 34724 | 0.4% | 0.4% | 122 |
| 5 | 34724 | 0.4% | 0.4% | 131 |
| 6 | 34724 | 0.6% | 0.4% | 145 |
| 7 | 34724 | 0.9% | 0.7% | 250 |
| 8 | 34724 | 1.3% | 1.3% | 442 |
| 9 | 34723 | 1.9% | 1.5% | 520 |
| 10 | 34723 | 3.9% | 2.4% | 829 |

| model | rows | base_rate | p_at_100_rate | hits_at_100 | lift_at_100 | p_at_100_low_rate | p_at_100_high_rate | p_at_1000_rate | hits_at_1000 | lift_at_1000 | p_at_1000_low_rate | p_at_1000_high_rate | top10_capture_share | log_loss_skill_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full model | 1544700 | 0.4% | 1.6% | 19 | 3.58 | 1.0% | 2.5% | 1.5% | 175 | 3.30 | 1.3% | 1.7% | 16.9% | -0.0% |
| years since last roof permit only | 1544700 | 0.4% | 1.5% | 18 | 3.39 | 1.0% | 2.4% | 1.2% | 150 | 2.83 | 1.1% | 1.5% | 12.8% | -0.0% |
| building age only | 1544700 | 0.4% | 2.0% | 24 | 4.52 | 1.3% | 3.0% | 1.3% | 157 | 2.96 | 1.1% | 1.5% | 11.3% | -0.0% |
| class code only | 1544700 | 0.4% | 0.8% | 10 | 1.88 | 0.5% | 1.5% | 0.6% | 74 | 1.39 | 0.5% | 0.8% | 13.2% | -0.1% |
| random (expected) | 1544700 | 0.4% | 0.4% | — | 1.00 | — | — | 0.4% | — | 1.00 | — | — | 10.0% | 0.0% |

| variant | p_at_100_rate | p_at_1000_rate | lift_at_1000 | top10_capture_share | log_loss_skill_share | lift_change_vs_full | skill_change_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| drop roof (years since last roof permit) | 1.1% | 1.0% | 2.32 | 15.4% | -0.1% | -0.98 | -0.1% |
| drop cls (class code) | 1.2% | 1.4% | 3.22 | 14.9% | 0.0% | -0.08 | 0.0% |
| drop age (building age) | 1.6% | 1.5% | 3.28 | 15.8% | -0.1% | -0.02 | -0.1% |
| drop viol (roofing violation in prior 2 years) | 1.6% | 1.3% | 3.03 | 16.3% | -0.0% | -0.26 | -0.0% |
| drop hail (hail detection within ~1 km in prior 3 years) | 1.6% | 1.2% | 2.64 | 16.3% | 0.2% | -0.66 | 0.2% |
| hail kept but without its 'no location' flag (merged into 0) | 1.6% | 1.1% | 2.39 | 16.7% | 0.0% | -0.90 | 0.0% |

| decile | rows | predicted_rate | observed_rate | hits |
| --- | --- | --- | --- | --- |
| 1 | 154470 | 0.2% | 0.3% | 499 |
| 2 | 154470 | 0.3% | 0.4% | 585 |
| 3 | 154470 | 0.3% | 0.4% | 563 |
| 4 | 154470 | 0.3% | 0.4% | 625 |
| 5 | 154470 | 0.3% | 0.4% | 612 |
| 6 | 154470 | 0.3% | 0.4% | 686 |
| 7 | 154470 | 0.4% | 0.5% | 720 |
| 8 | 154470 | 0.4% | 0.4% | 651 |
| 9 | 154470 | 0.5% | 0.5% | 722 |
| 10 | 154470 | 0.8% | 0.8% | 1166 |

- Key numbers (rates are fractions): signals = 347238; conversion = 0.04; baseline = 0.01; lift = 4.59; signals_per_week = 76.92; p_at_100_rate = 0.07; lift_at_100 = 9.57; hits_at_1000 = 427; best_baseline_lift_at_1000 = 4.86; lift_vs_best_baseline = 0.94; flats_p_at_1000_rate = 0.01; flats_base_rate = 0.00; flats_lift_at_1000 = 3.30
- Tuning (time-split validation): {"flats": {"min_cell_size": 3000, "validation_log_loss_skill": {"1000": 0.00491, "300": 0.00492, "3000": 0.00571}}, "main": {"min_cell_size": 300, "validation_log_loss_skill": {"1000": 0.07214, "300": 0.07726, "3000": 0.0376}}}

## H36 — ADU preapproval application → ADU-related or any new construction/renovation permit at the address

- **Signal:** One ADU preapproval submission per address per 365 days (any status; Pre-Certified is hindsight)
- **Target:** A permit at the address after the submission whose description mentions an ADU/coach house/accessory unit, or any PERMIT - NEW CONSTRUCTION or RENOVATION/ALTERATION, within 120 days (the 365-day target cannot be observed: the feed starts 2026-03-31); baseline = same residential addresses' earlier window and residential addresses (same class bucket, same half-month) with no preapproval
- **Data:** Chicago ADU preapproval applications (since 2026-03-31; applicant names not stored), Chicago permits (description text), parcel classes
- **Verdict:** Strong (provisional)
- **Notes:** PROVISIONAL: the feed has about 7.5 months of history, so only submissions up to 120 days before the newest permit have a full 120-day window and none has a full 365-day window. Headline lift is the smaller of own-earlier-window and comparable-address lifts. Baseline uses the same regex for ADU text, which only exists in permits since the 2021 pilot, so the own-earlier window is mostly renovation. Status is as of today. Preapproval is a required step before an ADU permit, so a high conversion is expected by construction; the open questions are lead time (the time between submission and permit) and how many owners never proceed.
- Signals tested: 378; conversion 7.7% vs baseline 0.3%; median 75.0 days to target

| status_group | signals | adu_permit_so_far_rate | median_days_so_far |
| --- | --- | --- | --- |
| Pre-Certified | 560 | 5.7% | 119.00 |
| Other (in progress) | 16 | 0.0% | — |
| Canceled or denied | 13 | 15.4% | 122.50 |

| horizon_days | signals_observed | any_permit_rate | any_permit_control_rate | any_permit_lift_vs_control | any_permit_own_earlier_rate | adu_permit_rate | adu_permit_control_rate | adu_permit_lift_vs_control | median_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 120 | 378 | 7.7% | 0.3% | 24.14 | 1.9% | 4.2% | 0.0% | 385.17 | 75.00 |
| 180 | 256 | 14.8% | 0.5% | 31.15 | 4.7% | 7.4% | 0.0% | 469.07 | 125.50 |
| 365 | 0 | — | — | — | — | — | — | — | — |

- Key numbers (rates are fractions): signals = 378; signals_total = 589; submissions_total = 616; precertified_signals = 560; horizon_days = 120; conversion = 0.08; baseline = 0.00; lift = 4.14; lift_vs_control = 24.14; own_earlier_window = 0.02; lift_vs_own_earlier = 4.14; adu_only_conversion = 0.04; adu_only_control_rate = 0.00; adu_only_lift_vs_control = 385.17; adu_permit_before_submission_share = 0.00; any_permit_before_submission_share = 0.06; median_days = 75.00; days_p25 = 47.00; days_p75 = 96.00; signals_per_week = 12.31; adu_permit_so_far_all_signals_rate = 0.06; adu_permit_so_far_precertified_rate = 0.06; median_days_so_far = 119.00; adu_text_permit_since_2021_before_submission = 0.01

## H29 — Which trades are still open after a $1M+ commercial/multifamily permit (signs, elevator, electrical, ...)

- **Signal:** New-construction or renovation/alteration permit with reported cost of at least $1,000,000 at an address whose parcel class is commercial/industrial, 7+ unit multifamily, mixed-use, 2-6 flats or exempt (first one at the address in 540 days)
- **Target:** A follow-on permit at the same address within 540 days for a sign, an elevator or electrical work (headline; other trades in the table), and whether its contractor was already named on the big permit
- **Data:** Permits (types: NEW CONSTRUCTION, RENOVATION/ALTERATION, SIGNS, ELEVATOR EQUIPMENT, SCAFFOLDING, WRECKING/DEMOLITION, EXPRESS PERMIT PROGRAM, EASY PERMIT PROCESS), permit parties, parcel classes from sales
- **Verdict:** Strong
- **Notes:** Class comes from the latest Cook County sale or the residential characteristics file, so addresses with no sale since 2010 have no class (reported separately, no matched control). 'matched_control_rate' = same-window rate at addresses of the same class bucket with no major permit within +-540 days, standardized to the signals' class mix; 'busy_control_rate' = same for addresses with a $100k-$1M renovation/new-construction permit in the prior 90 days and no major permit; 'own_earlier_rate' = the same address in the window 540-1,080 days before. The feed has no 'electric wiring' permit type: electrical, plumbing, HVAC, fire-alarm and roofing follow-ons are permits (express/easy/renovation) whose text names that work. 'locked in' = a contractor on the follow-on permit has the same normalized name as a contractor on any big permit at that address that day (names are cut at 30 characters, so variants count as new); 'unnamed' = no contractor on the follow-on permit; shares are per permit, rates are per signal. Follow-ons issued the same day as the big permit are excluded. The scaffolding permit type disappears from the feed after 2023-11-17, so its cohort ends 540 days before that. Permits capture permitted work only.
- Signals tested: 2,330; conversion 62.1% vs baseline 20.3%; median 139.0 days to target

| year | n | conversion |
| --- | --- | --- |
| 2016 | 271 | 63.8% |
| 2017 | 255 | 65.5% |
| 2018 | 289 | 72.0% |
| 2019 | 223 | 70.4% |
| 2020 | 224 | 58.0% |
| 2021 | 202 | 62.4% |
| 2022 | 250 | 60.0% |
| 2023 | 272 | 58.5% |
| 2024 | 247 | 50.6% |
| 2025 | 97 | 53.6% |

| trade | permit_types | signals | followon_rate | own_earlier_rate | lift_vs_own | matched_control_rate | lift_vs_matched | busy_control_rate | lift_vs_busy | median_days | p25_days | p75_days | new_contractor_rate | locked_in_rate | permits | new_share | locked_share | unnamed_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| signs | PERMIT - SIGNS | 2330 | 21.4% | 4.5% | 4.79 | 1.3% | 15.97 | 17.7% | 1.21 | 246.50 | 135.25 | 385.75 | 19.0% | 3.0% | 1763 | 86.8% | 11.7% | 1.5% |
| elevator | PERMIT - ELEVATOR EQUIPMENT | 2330 | 36.1% | 8.5% | 4.25 | 0.6% | 59.87 | 8.2% | 4.38 | 226.00 | 132.00 | 328.00 | 36.1% | 0.0% | 1288 | 100.0% | 0.0% | 0.0% |
| electrical | EXPRESS/EASY/RENOVATION text mentions electrical wiring | 2330 | 41.5% | 17.0% | 2.45 | 2.8% | 14.78 | 28.8% | 1.44 | 126.00 | 51.75 | 258.00 | 35.5% | 11.9% | 2933 | 84.1% | 15.9% | 0.0% |
| scaffolding | PERMIT - SCAFFOLDING (feed ends 2023-11-17) | 1550 | 7.2% | 5.3% | 1.37 | 0.2% | 34.32 | 3.7% | 1.97 | 190.50 | 97.75 | 324.50 | 4.1% | 0.1% | 147 | 55.1% | 0.7% | 44.2% |
| plumbing | text mentions plumbing | 2330 | 31.7% | 10.5% | 3.01 | 1.3% | 24.73 | 19.9% | 1.59 | 130.50 | 57.00 | 249.75 | 14.8% | 21.6% | 1544 | 49.2% | 50.3% | 0.5% |
| hvac | text mentions mechanical/HVAC | 2330 | 19.5% | 7.3% | 2.69 | 0.7% | 26.46 | 12.3% | 1.59 | 158.00 | 73.00 | 277.00 | 9.8% | 12.1% | 812 | 50.4% | 49.4% | 0.2% |
| fire_alarm | text mentions fire alarm/sprinkler | 2330 | 33.7% | 9.3% | 3.62 | 0.4% | 82.68 | 13.3% | 2.53 | 152.00 | 73.00 | 296.00 | 25.1% | 13.9% | 2025 | 76.3% | 23.6% | 0.0% |
| roofing | text mentions roofing | 2330 | 10.3% | 4.7% | 2.20 | 0.9% | 11.87 | 5.1% | 2.02 | 235.50 | 123.75 | 349.25 | 4.6% | 6.0% | 296 | 40.9% | 54.1% | 5.1% |
| demolition | PERMIT - WRECKING/DEMOLITION | 2330 | 3.1% | 1.4% | 2.18 | 0.3% | 10.87 | 0.5% | 6.14 | 59.00 | 31.00 | 171.75 | 2.7% | 0.3% | 75 | 88.0% | 12.0% | 0.0% |
| renovation | PERMIT - RENOVATION/ALTERATION or interior build-out text | 2330 | 42.4% | 18.0% | 2.36 | 3.1% | 13.70 | 28.2% | 1.50 | 145.50 | 61.75 | 293.25 | 20.5% | 33.9% | 3425 | 50.2% | 49.8% | 0.0% |

| class | signals | followon_rate | matched_control_rate | lift_vs_matched |
| --- | --- | --- | --- | --- |
| 2-6 unit flats (211) | 226 | 19.0% | 1.8% | 10.75 |
| commercial/industrial (5xx) | 1204 | 77.4% | 5.5% | 14.00 |
| exempt/other | 407 | 53.8% | 2.1% | 25.55 |
| mixed-use up to 6 units (212) | 100 | 62.0% | 4.3% | 14.44 |
| multifamily 7+ (3xx) | 393 | 48.6% | 4.2% | 11.53 |

- Key numbers (rates are fractions): signals = 2330; conversion = 0.62; baseline = 0.20; lift = 3.06; matched_control_rate = 0.04; lift_vs_matched_control = 14.47; busy_control_rate = 0.41; lift_vs_busy = 1.53; signals_per_week_class_known = 4.71; median_days = 139.00; days_p25 = 62.00; days_p75 = 260.00; signals_per_week = 8.67; unknown_class_signals = 2425; unknown_class_followon_rate = 0.53

## H40 — Renovation, new-construction or demolition permit at an address → a dumpster permit on the public way there within 180 days

- **Signal:** Renovation/alteration, new-construction or wrecking/demolition permit at an address with no such permit in the previous 180 days (one per address per 180 days), 2017 to 180 days before the newest dumpster permit
- **Target:** An issued, not-cancelled CDOT dumpster permit (street-sweeping notes excluded) starting at the same address within 180 days after the building permit; baseline = the same address's own earlier window (181-360 days before); control = address-quarters of addresses that have had such a permit at some time, with none within a year either side, year-standardized
- **Data:** Chicago building permits, CDOT dumpster permits 2016+ (pubx-yq2d, applicant = the hauler, not the customer; 241,343 location rows)
- **Verdict:** Strong
- **Notes:** The applicant on a CDOT dumpster permit is the hauler (67 companies, 8 permit rows name an individual); the customer, the project and the GC are not in the data, so the GC link goes through the building permit at the address. Only dumpsters placed on the public way (curb lane or alley) need this permit: dumpsters on private property or in a driveway are invisible, so conversion is a floor and most building permits will never show one. A dumpster permit is issued for the day it is placed (median 0 days before start), so its date is the placement date. The dumpster permit comes first in a large share of address pairs (dumpster_first_share_of_near): a permit is not an early trigger for those. 'Repeat partner' = the hauler on the project's first dumpster permit is a hauler this GC used on an earlier linked project; chance = the market share, in the project's year, of the haulers the GC used before. Permit statuses are as of today (a later cancellation is known only now). Address matching is by street address, not unit or lot.
- Signals tested: 73,204; conversion 9.6% vs baseline 3.2%; median 44.0 days to target

| stratum | signals | conversion | own_earlier_window_rate | control_rate | lift_vs_control | lift_vs_own_earlier | median_days | p25_days | p75_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | 9709 | 12.5% | 3.8% | 0.8% | 14.71 | 3.30 | 43.00 | 17.00 | 91.25 |
| 2018 | 9478 | 10.0% | 3.4% | 0.8% | 13.05 | 2.95 | 40.00 | 17.00 | 91.00 |
| 2019 | 9172 | 10.8% | 3.2% | 0.7% | 14.92 | 3.41 | 47.00 | 17.00 | 104.00 |
| 2020 | 7481 | 10.2% | 3.3% | 0.8% | 13.21 | 3.08 | 42.00 | 16.00 | 98.00 |
| 2021 | 7882 | 8.4% | 2.9% | 0.7% | 11.83 | 2.94 | 44.50 | 18.00 | 99.00 |
| 2022 | 8064 | 9.5% | 3.0% | 0.7% | 14.39 | 3.16 | 46.00 | 17.00 | 100.00 |
| 2023 | 6584 | 8.1% | 3.4% | 0.6% | 13.01 | 2.40 | 42.00 | 18.00 | 91.00 |
| 2024 | 6518 | 8.0% | 2.9% | 0.6% | 13.73 | 2.80 | 51.00 | 18.00 | 109.00 |
| 2025 | 6023 | 7.2% | 2.4% | 0.6% | 11.94 | 2.99 | 48.00 | 21.00 | 100.00 |
| 2026 | 2293 | 8.2% | 2.9% | 0.6% | 13.87 | 2.82 | 46.00 | 22.00 | 94.00 |

| stratum | signals | conversion | own_earlier_window_rate | control_rate | lift_vs_control | lift_vs_own_earlier | median_days | p25_days | p75_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| under $10k | 12189 | 5.2% | 2.4% | 0.7% | 7.08 | 2.14 | 70.00 | 27.00 | 119.75 |
| $10k-$50k | 23752 | 6.4% | 3.2% | 0.7% | 9.03 | 2.00 | 38.00 | 15.00 | 91.00 |
| $50k-$250k | 22380 | 13.6% | 4.2% | 0.7% | 19.47 | 3.25 | 35.00 | 14.00 | 79.00 |
| $250k+ | 14863 | 12.1% | 2.2% | 0.7% | 17.68 | 5.63 | 62.00 | 25.25 | 116.00 |
| no cost reported | 20 | 20.0% | 0.0% | 0.7% | 27.00 | — | 59.00 | 50.25 | 87.00 |

| prior_permit | dumpster_permits | with_prior_permit | with_prior_permit_share |
| --- | --- | --- | --- |
| renovation, new construction or demolition permit | 174962 | 18660 | 10.7% |
| express or easy permit (roofs, porches, small repairs) | 174962 | 17592 | 10.1% |
| any building permit | 174962 | 31361 | 17.9% |

| year | permits | haulers | haulers_20_plus | top1_share | top5_share | top10_share |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 25513 | 40 | 36 | 20.3% | 58.0% | 74.6% |
| 2017 | 24810 | 42 | 36 | 20.3% | 60.0% | 75.6% |
| 2018 | 22508 | 41 | 37 | 16.1% | 54.2% | 71.5% |
| 2019 | 21403 | 43 | 36 | 20.7% | 55.4% | 73.8% |
| 2020 | 18441 | 42 | 33 | 14.9% | 55.9% | 76.3% |
| 2021 | 17068 | 41 | 28 | 15.0% | 56.0% | 77.1% |
| 2022 | 16522 | 40 | 31 | 15.3% | 57.5% | 76.6% |
| 2023 | 15189 | 40 | 29 | 21.8% | 61.7% | 80.7% |
| 2024 | 14723 | 35 | 27 | 27.7% | 64.7% | 83.3% |
| 2025 | 14709 | 32 | 27 | 26.6% | 62.0% | 85.1% |
| 2026 | 13806 | 31 | 28 | 27.1% | 60.6% | 83.9% |

- Key numbers (rates are fractions): signals = 73204; conversion = 0.10; baseline = 0.03; lift = 3.03; signals_per_week = 116.48; converted_per_week = 8.79; control_rate = 0.01; lift_vs_control = 13.57; median_days = 44.00; days_p25 = 18.00; days_p75 = 98.00; dumpster_first_share_of_near = 0.38; dumpster_30_days_first_share_of_near = 0.32; with_dumpster_within_180_days_either_side = 9010; control_address_quarters = 4223345; market_permits = 204692; market_haulers = 63; market_top1_share = 0.16; market_top5_share = 0.58; market_top10_share = 0.74; market_hhi = 0.08; market_last_52_weeks_permits = 15151; market_last_52_weeks_haulers = 32; market_last_52_weeks_haulers_20_plus = 29; market_last_52_weeks_top5_share = 0.60; market_last_52_weeks_top10_share = 0.83; market_haulers_first_seen_after_2016 = 23; market_haulers_first_seen_last_3_years = 5; partner_linked_projects = 6309; partner_gcs = 2393; partner_with_earlier_project = 3886; partner_repeat_partner_share = 0.70; partner_expected_by_chance_share = 0.14; partner_mean_haulers_used_before = 2.08; partner_self_hauled_share = 0.00; partner_repeat_vs_chance = 4.86; partner_gcs_with_5_plus_projects = 310; partner_median_top_hauler_share = 0.67; partner_gcs_80_percent_one_hauler_share = 0.40; partner_median_haulers_per_gc = 3.00

## H38 — Event series held in each of the last 2 years → held again next year at the same time of year

- **Signal:** A series = normalized event name at the same park (Park District, only the real-event tiers 'Permit - Event N', Festival/Performance, Corporate, Promotions, civic/corporate/philanthropic venues) held (approved reservation) in each of the two years up to the prediction year; features use only years up to the prediction year, prediction date 31 December
- **Target:** Any reservation of the same series within +/- 31 days of the same date one year later; baseline = series in their debut year (no history), standardized to the held-2-years group mix. Prediction years 2019-2021 are left out of the pooled figures (pandemic); the CDOT table is the same test on street events keyed by name and ward
- **Data:** Chicago Park District outdoor event permits and reservations 2012+ (pk66-w54g, requestor names not downloaded), CDOT festival/parade/athletic/assembly street-event permits 2013+ (pubx-yq2d), Overture places, Chicago business licenses (organization name matching only)
- **Verdict:** Useful
- **Notes:** Not a lead source for NEW events: it only re-finds events that already ran. A series needs a usable name (Park District event_description or organization, CDOT project name), so one-off unnamed events cannot recur by construction. The Park District reorganized its permit types in 2020 ('Event N Cluster' tiers replace Corporate/Picnic levels) and the number of real-event rows doubled after 2021, so groups are not comparable across eras and the by-period table is the fair reading. Event 1 includes private birthday parties and picnics. Organization names are matched by normalized name only; a name match is not a contact. Private requestors' names are not stored; event names and organizations never appear in this report. Reservations are final statuses today (Approved/Completed/Issued); a reservation cancelled before the event disappears from the feed, so history is of events that were held or kept. The Park District has no attendance field (the 'Event N' tier is the only size hint).

| year | recurring_series | recurring_3_years | evaluated | hits | debut_n | debut_hits | held2_rate | debut_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2014 | 31 | 16 | 31 | 18 | 108 | 23 | 58.1% | 21.3% |
| 2015 | 46 | 18 | 46 | 29 | 124 | 17 | 63.0% | 13.7% |
| 2016 | 51 | 29 | 51 | 31 | 142 | 16 | 60.8% | 11.3% |
| 2017 | 50 | 32 | 50 | 31 | 166 | 15 | 62.0% | 9.0% |
| 2018 | 55 | 31 | 55 | 23 | 146 | 13 | 41.8% | 8.9% |
| 2019 | 42 | 24 | 42 | 3 | 154 | 0 | 7.1% | 0.0% |
| 2020 | 5 | 4 | 5 | 2 | 129 | 7 | — | 5.4% |
| 2021 | 11 | 2 | 11 | 5 | 758 | 72 | 45.5% | 9.5% |
| 2022 | 101 | 6 | 101 | 58 | 816 | 108 | 57.4% | 13.2% |
| 2023 | 182 | 61 | 182 | 91 | 828 | 88 | 50.0% | 10.6% |
| 2024 | 204 | 93 | 204 | 110 | 742 | 98 | 53.9% | 13.2% |
| 2025 | 247 | 111 | 232 | 117 | 609 | 98 | 50.4% | 16.1% |

| group | debut_n | debut_hits | held2_n | held2_hits | held3_n | held3_hits | debut_rate | held2_rate | held3_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Event 1 | 2039 | 208 | 323 | 132 | 94 | 49 | 10.2% | 40.9% | 52.1% |
| Event 2 | 449 | 93 | 185 | 112 | 81 | 59 | 20.7% | 60.5% | 72.8% |
| Event 3 | 144 | 34 | 68 | 41 | 27 | 17 | 23.6% | 60.3% | 63.0% |
| Event 4 | 134 | 26 | 71 | 42 | 33 | 21 | 19.4% | 59.2% | 63.6% |
| Event 5 | 99 | 25 | 43 | 25 | 14 | 11 | 25.3% | 58.1% | — |
| Event 6 / Festival | 68 | 21 | 90 | 63 | 51 | 38 | 30.9% | 70.0% | 74.5% |
| Corporate | 279 | 61 | 165 | 93 | 91 | 53 | 21.9% | 56.4% | 58.2% |
| Promotions | 212 | 2 | 2 | 0 | 0 | 0 | 0.9% | — | — |
| Venue (civic/corporate/philanthropic) | 257 | 6 | 5 | 0 | 0 | 0 | 2.3% | — | — |

| rule | series_years | hits | precision_rate |
| --- | --- | --- | --- |
| every series held in the year (no history needed) | 4867 | 1089 | 22.4% |
| debut year (not seen in any earlier year) | 3681 | 476 | 12.9% |
| held in each of the last 2 years | 952 | 508 | 53.4% |
| held in each of the last 3 years | 391 | 248 | 63.4% |
| held in each of the last 2 years, organization named | 26 | 13 | 50.0% |

| period | held2_n | held2_hits | held3_n | held3_hits | debut_n | debut_hits | all_series_n | all_series_hits | held2_rate | held3_rate | debut_rate | all_series_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2014-2018 (before the pandemic) | 233 | 132 | 126 | 77 | 686 | 84 | 962 | 237 | 56.7% | 61.1% | 12.2% | 24.6% |
| 2022-2025 (after) | 719 | 376 | 265 | 171 | 2995 | 392 | 3905 | 852 | 52.3% | 64.5% | 13.1% | 21.8% |

| group | predicted_3_to_9_months_per_year | hits_in_window | evaluated_in_window | hit_rate |
| --- | --- | --- | --- | --- |
| Event 1 | 83.33 | 99 | 250 | 39.6% |
| Event 2 | 43.33 | 69 | 130 | 53.1% |
| Event 3 | 17.00 | 34 | 51 | 66.7% |
| Event 4 | 17.00 | 30 | 51 | 58.8% |
| Event 5 | 10.00 | 20 | 30 | 66.7% |
| Event 6 / Festival | 7.00 | 16 | 21 | 76.2% |
| Corporate | 0.00 | 0 | 0 | — |
| Promotions | 0.00 | 0 | 0 | — |
| Venue (civic/corporate/philanthropic) | 0.00 | 0 | 0 | — |

| rule | series_years | hits | precision_rate |
| --- | --- | --- | --- |
| every series held in the year (no history needed) | 3752 | 1587 | 42.3% |
| debut year (not seen in any earlier year) | 2247 | 602 | 26.8% |
| held in each of the last 2 years | 1279 | 842 | 65.8% |
| held in each of the last 3 years | 552 | 404 | 73.2% |
| held in each of the last 2 years, organization named | 854 | 567 | 66.4% |

| period | held2_n | held2_hits | held3_n | held3_hits | debut_n | debut_hits | all_series_n | all_series_hits | held2_rate | held3_rate | debut_rate | all_series_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2014-2018 (before the pandemic) | 309 | 166 | 87 | 56 | 1060 | 263 | 1400 | 449 | 53.7% | 64.4% | 24.8% | 32.1% |
| 2022-2025 (after) | 970 | 676 | 465 | 348 | 1187 | 339 | 2352 | 1138 | 69.7% | 74.8% | 28.6% | 48.4% |

| group | debut_n | debut_hits | held2_n | held2_hits | held3_n | held3_hits | debut_rate | held2_rate | held3_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Assembly | 8 | 0 | 0 | 0 | 0 | 0 | — | — | — |
| Athletic | 530 | 159 | 322 | 204 | 134 | 91 | 30.0% | 63.4% | 67.9% |
| Festival | 1653 | 442 | 956 | 638 | 418 | 313 | 26.7% | 66.7% | 74.9% |
| Parade | 56 | 1 | 1 | 0 | 0 | 0 | 1.8% | — | — |

- Key numbers (rates are fractions): signals = 952; conversion = 0.53; baseline = 0.18; lift = 2.89; signals_per_week = 4.06; recurring_series_per_year_last3 = 211.00; date_n = 399; date_median_shift_days = 2.00; date_p75_shift_days = 6.00; date_within_7_days_share = 0.82; date_within_31_days_share = 0.97; lead_n = 508; lead_median_lead_days = 198.00; lead_p25_lead_days = 157.00; lead_p75_lead_days = 243.25; park_series_years = 3041; park_organization_named_share = 0.01; park_recurring_series_years = 633; park_recurring_organization_named_share = 0.01; park_org_organizations = 203; park_org_place_exact = 60; park_org_place_any = 78; park_org_license_exact = 54; park_org_license_any = 62; park_org_any_match = 105; park_org_place_exact_share = 0.30; park_org_place_any_share = 0.38; park_org_license_exact_share = 0.27; park_org_license_any_share = 0.31; park_org_any_match_share = 0.52; cdot_conversion = 0.66; cdot_baseline = 0.28; cdot_lift = 2.39; cdot_recurring_per_year_last3 = 293.00; cdot_date_n = 659; cdot_date_median_shift_days = 2.00; cdot_date_p75_shift_days = 6.00; cdot_date_within_7_days_share = 0.83; cdot_date_within_31_days_share = 0.97; cdot_lead_n = 842; cdot_lead_median_lead_days = 206.50; cdot_lead_p25_lead_days = 160.25; cdot_lead_p75_lead_days = 252.00; cdot_series_years = 1892; cdot_organization_named_share = 0.53; cdot_recurring_series_years = 879; cdot_recurring_organization_named_share = 0.57; cdot_org_organizations = 2878; cdot_org_place_exact = 574; cdot_org_place_any = 730; cdot_org_license_exact = 550; cdot_org_license_any = 676; cdot_org_any_match = 1045; cdot_org_place_exact_share = 0.20; cdot_org_place_any_share = 0.25; cdot_org_license_exact_share = 0.19; cdot_org_license_any_share = 0.23; cdot_org_any_match_share = 0.36

## H13 — Which buildings need masonry work: walls × age

- **Signal:** Property group: Masonry / pre-1910
- **Target:** masonry permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Useful

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| Masonry / pre-1910 | 38409 | 1.4% | 2.85 |
| Masonry / 1910-39 | 70950 | 0.8% | 1.60 |
| Frame + Masonry / pre-1910 | 5258 | 0.8% | 1.54 |
| Frame + Masonry / 1910-39 | 9542 | 0.6% | 1.25 |
| Masonry / 1970+ | 20252 | 0.6% | 1.14 |
| Frame + Masonry / 1970+ | 4423 | 0.4% | 0.86 |
| Frame / 1970+ | 9230 | 0.4% | 0.85 |
| Frame + Masonry / 1940-69 | 11656 | 0.3% | 0.68 |
| Stucco / pre-1910 | 1095 | 0.2% | 0.43 |
| Frame / pre-1910 | 46149 | 0.2% | 0.40 |
| Frame / 1910-39 | 32071 | 0.2% | 0.33 |
| Masonry / 1940-69 | 72659 | 0.1% | 0.26 |
| Stucco / 1910-39 | 2195 | 0.1% | 0.22 |
| Frame / 1940-69 | 12923 | 0.1% | 0.18 |

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
| 0 | 1778124 | 0.4% |
| 1 | 190640 | 0.6% |
| 2+ | 25279 | 1.0% |

## H12 — Which houses re-roof: age × roof material

- **Signal:** Property group: 2000+ / Other
- **Target:** roofing permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Useful

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| 2000+ / Other | 1192 | 2.2% | 2.37 |
| 2000+ / Tar + Gravel | 4901 | 1.5% | 1.60 |
| 2000+ / Shingle + Asphalt | 12121 | 1.4% | 1.53 |
| 1940-69 / Shingle + Asphalt | 92301 | 1.0% | 1.15 |
| pre-1910 / Other | 1813 | 1.0% | 1.13 |
| 1910-39 / Shingle + Asphalt | 88293 | 1.0% | 1.07 |
| 1970-99 / Shingle + Asphalt | 12549 | 0.8% | 0.92 |
| 1910-39 / Tile | 1256 | 0.8% | 0.85 |
| pre-1910 / Tar + Gravel | 24072 | 0.7% | 0.80 |
| 1940-69 / Tar + Gravel | 4044 | 0.7% | 0.79 |
| pre-1910 / Shingle + Asphalt | 64345 | 0.7% | 0.74 |
| 1910-39 / Tar + Gravel | 23938 | 0.6% | 0.69 |
| 1970-99 / Tar + Gravel | 3044 | 0.6% | 0.63 |

## H14 — Which homes pull HVAC permits: A/C × heat type

- **Signal:** Property group: Central A/C / Hot Water Steam
- **Target:** hvac permit per year
- **Data:** Cook County Assessor residential characteristics, permits
- **Verdict:** Useful
- **Notes:** The original idea (no central A/C → new A/C installs) is refuted: homes without central A/C are below average. Homes that already have it pull more permits, i.e. replacements. Most residential HVAC swaps aren't permitted, so rates are low.

| grp | parcels | annual_rate | lift |
| --- | --- | --- | --- |
| Central A/C / Hot Water Steam | 8532 | 0.3% | 2.17 |
| Central A/C / Warm Air Furnace | 97369 | 0.2% | 1.58 |
| No Central A/C / Electric Heater | 1347 | 0.2% | 1.30 |
| No Central A/C / None | 1683 | 0.1% | 0.91 |
| No Central A/C / Hot Water Steam | 70727 | 0.1% | 0.82 |
| No Central A/C / Warm Air Furnace | 156667 | 0.1% | 0.65 |

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
| 0 | 11893502 | 0.3% |
| 1 | 531810 | 0.5% |
| 2+ | 25930 | 0.7% |

## H37 — Zoning reclassification + sale of the parcel in the prior year vs zoning alone → new construction

- **Signal:** Zoning reclassification introduced at an address whose parcel (PIN matched through permits or the tax roll) had a non-filtered sale in the 365 days before the introduction
- **Target:** PERMIT - NEW CONSTRUCTION at the address or range within 730 days; baseline = zoning signals at PIN-matched addresses with no such sale, standardized to the same class bucket and year
- **Data:** City Clerk zoning reclassifications, Cook County sales (arm's-length filter as elsewhere), permits
- **Verdict:** Weak
- **Notes:** An ablation, not a stand-alone signal: lift is conversion with a prior-year sale divided by conversion without (class-bucket and year standardized). Only addresses whose PIN is known are compared. A sale after the introduction is never used. Sale prices are not used; investor buyers are a regex on the buyer name.

| year | signals_with_sale | conversion | zoning_alone_rate | lift_vs_alone |
| --- | --- | --- | --- | --- |
| 2012 | 43 | 34.9% | 15.8% | 2.20 |
| 2013 | 86 | 36.0% | 17.8% | 2.03 |
| 2014 | 116 | 38.8% | 24.9% | 1.56 |
| 2015 | 113 | 31.9% | 25.2% | 1.26 |
| 2016 | 141 | 43.3% | 21.7% | 2.00 |
| 2017 | 130 | 33.8% | 25.8% | 1.31 |
| 2018 | 125 | 42.4% | 20.5% | 2.06 |
| 2019 | 88 | 22.7% | 13.9% | 1.64 |
| 2020 | 57 | 14.0% | 20.0% | 0.70 |
| 2021 | 69 | 20.3% | 13.6% | 1.50 |
| 2022 | 82 | 22.0% | 12.5% | 1.76 |
| 2023 | 50 | 14.0% | 14.8% | 0.94 |
| 2024 | 78 | 23.1% | 10.1% | 2.30 |

- Key numbers (rates are fractions): signals = 1178; signals_zoning_alone = 4353; conversion = 0.31; baseline = 0.21; zoning_alone_raw_rate = 0.18; lift = 1.50; lift_raw = 1.71; difference_points = 13.01; difference_ci95_low_points = 10.12; difference_ci95_high_points = 15.90; hits_with_sale = 370; hits_zoning_alone = 801; investor_buyer_signals = 686; investor_buyer_conversion = 0.36; signals_per_week = 1.98

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
| Above Average | 2327 | 0.6% | 1.48 |
| Below Average | 2427 | 0.5% | 1.13 |
| Average | 332266 | 0.4% | 1.00 |

## H32 — Storefront turnover (new licensee after the previous one lapsed) → build-out permit at the address

- **Signal:** First license (ISSUE) of an account at an address whose previous licensee's last license (expiration or cancellation known on that date) ended within the prior 365 days, with no other licensee in force (one per address per 365 days)
- **Target:** Renovation/build-out/new-construction permit at the address within 365 days after the license; control = same-account renewals at addresses with no other licensee in force and no new account in the prior 365 days, matched on license group and year; also the signed timing of the permit around the license and application dates
- **Data:** Chicago business licenses 2014+ (biz_license_history), permits (same renovation predicate as H26/food.py)
- **Verdict:** Weak
- **Notes:** Premises-based licenses only (same filter as H31). Addresses are street addresses without unit, so a permit for another tenant or the landlord counts for both groups; requiring no other licensee in force keeps the test to storefront-like addresses but cannot see unlicensed tenants. A turnover cannot be told from an owner who re-registers under a new account number, and a previous licensee that never renewed may simply have closed years earlier (hence the 365-day lapse limit). Cancellations use the status date only once it has happened. The feed lists a license only when it is issued (no row has an empty issue date), so 'application created' is a back-dated field known only after issue: the application date gives the median extra days shown under timing, but it is not observable before the license. 'median_days' is days from license issue to the first permit among turnovers that converted; 'permit_before' counts a permit in the 365 days up to the license date (the build-out that precedes opening). The renewal control has fewer build-outs by construction (an operating tenant), so lift also partly measures 'new tenant vs continuing tenant'; compare the before and after rows.
- Signals tested: 6,016; conversion 3.3% vs baseline 2.4%; median 135.0 days to target

| definition | events | turnover_rate | control_rate | lift |
| --- | --- | --- | --- | --- |
| Renovation/build-out/new-construction permit within 365 days AFTER the new license (headline) | 6016 | 3.3% | 2.4% | 1.38 |
| Same permit within 365 days BEFORE the new license | 6016 | 7.3% | 2.5% | 2.88 |
| Application-date view: permit within 365 days after the application was created | 6003 | 5.0% | — | — |
| Same events measured from the license issue date (comparison for the row above) | 6003 | 3.3% | — | — |

| year | turnover_events | permit_after_rate | control_rate | lift |
| --- | --- | --- | --- | --- |
| 2016 | 595 | 2.9% | 2.6% | 1.09 |
| 2017 | 817 | 2.9% | 2.8% | 1.05 |
| 2018 | 763 | 4.5% | 2.4% | 1.83 |
| 2019 | 659 | 2.4% | 2.5% | 0.95 |
| 2020 | 344 | 2.6% | 2.4% | 1.10 |
| 2021 | 476 | 3.8% | 2.1% | 1.76 |
| 2022 | 656 | 3.0% | 2.1% | 1.43 |
| 2023 | 588 | 3.7% | 2.2% | 1.67 |
| 2024 | 614 | 3.3% | 2.2% | 1.46 |
| 2025 | 504 | 3.6% | 2.1% | 1.66 |

| group | turnover_events | permit_after_rate | control_events | control_rate | lift | permit_before_rate |
| --- | --- | --- | --- | --- | --- | --- |
| food & drink | 2249 | 3.0% | 36365 | 3.3% | 0.90 | 11.1% |
| personal services/beauty | 923 | 3.6% | 8620 | 1.1% | 3.11 | 3.1% |
| health/fitness/childcare | 297 | 4.7% | 5283 | 2.5% | 1.91 | 10.8% |
| retail | 1429 | 3.0% | 14027 | 2.0% | 1.49 | 5.0% |
| auto | 296 | 2.4% | 9144 | 2.5% | 0.94 | 2.0% |
| other | 822 | 4.1% | 44885 | 1.8% | 2.26 | 6.1% |

| reference_date | events | with_permit_within_365_either_way | permit_before_share | permit_on_or_after_share | median_signed_days | p25_signed_days | p75_signed_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| license issue date (turnover events) | 6016 | 587 | 70.4% | 29.6% | -77.00 | -160.50 | 31.50 |
| renewal issue date (control events) | 118324 | 4930 | 50.1% | 49.9% | -1.00 | -165.00 | 157.00 |
| application created date (turnover events with an application date) | 6003 | 600 | 56.2% | 43.8% | -16.50 | -108.25 | 83.00 |

- Key numbers (rates are fractions): signals = 6016; conversion = 0.03; baseline = 0.02; lift = 1.38; signals_per_week = 10.65; control_events = 118324; control_raw_rate = 0.02; own_earlier_window = 0.03; permit_before_rate = 0.07; permit_before_control_rate = 0.03; permit_before_lift = 2.88; median_days = 135.00; days_p25 = 59.25; days_p75 = 244.75; converted_after_30_days = 0.87; gap_days_median = 82.50; gap_days_p25 = 16.75; gap_days_p75 = 196.00; application_to_license_days_median = 14.00; application_to_license_days_p90 = 128.00

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

## H39 — How far ahead do event permits become visible? (Park District feed, CDOT street-event permits)

- **Signal:** Park District: the date a reservation first appeared in the open feed (Socrata row-creation date; the dataset itself has no application date). CDOT: the date review of the application began, against the event start date; large formal events = festival, parade, athletic, assembly
- **Target:** Descriptive: share of events visible at least T days before they start (T = 14 ... 180)
- **Data:** Chicago Park District outdoor event permits (pk66-w54g incl. Socrata :created_at), CDOT permits (pubx-yq2d, review-start date), both as ingested
- **Verdict:** Descriptive
- **Notes:** Park District: the feed was reloaded in bulk on the baseline date, so rows created then have unknown true listing times; the threshold table counts only events starting at least T days after the baseline, which is exact (nothing is left-censored for those). New rows appear in weekly batches, so a row's listing date can trail the reservation by up to a week or more and is an upper bound on when it could be seen. The latest event listed is the last day of the current year, consistent with a calendar-year horizon (not verified). CDOT: review start is the earliest application date in the data (the application may have been submitted earlier), so leads are lower bounds; permits cancelled or denied are excluded and only events whose date has passed are in the lead statistics. Large-event lead times jump around 2021-22 (median 5-9 days before, 36-46 days since; possibly a permit-system change, not verified), so use the recent years.

| item | value |
| --- | --- |
| Park District feed: bulk reload date (row-creation date of the baseline rows) | 2026-03-23 |
| Park District feed: newest row-creation date | 2026-11-16 |
| Park District feed: latest event date listed | 2026-12-31 |
| CDOT permit feed: newest review-start date | 2026-11-16 |

| days_ahead | rows_in_scope | rows_listed_that_early | listed_early_share |
| --- | --- | --- | --- |
| 14 | 3391 | 552 | 16.3% |
| 30 | 3375 | 444 | 13.2% |
| 60 | 3008 | 278 | 9.2% |
| 90 | 2389 | 173 | 7.2% |
| 120 | 1794 | 101 | 5.6% |
| 180 | 502 | 23 | 4.6% |

| group | rows_in_scope | rows_listed_90_days_ahead | listed_90_days_ahead_share |
| --- | --- | --- | --- |
| Event 1 | 864 | 34 | 3.9% |
| Event 2 | 429 | 48 | 11.2% |
| Event 3 | 140 | 32 | 22.9% |
| Event 4 | 151 | 51 | 33.8% |
| Event 5 | 125 | 0 | 0.0% |
| Event 6 / Festival | 625 | 0 | 0.0% |
| Promotions | 33 | 0 | 0.0% |
| Venue (civic/corporate/philanthropic) | 22 | 8 | 36.4% |

| worktype | permits | median_lead_days | p25_days | p75_days | p90_days | ahead_90_days_share | ahead_180_days_share | ahead_270_days_share | organization_applicant_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BlockParty | 39971 | 29.00 | 11.00 | 58.00 | 96.00 | 11.8% | 0.6% | 0.1% | 13.4% |
| Festival | 4135 | 31.00 | 9.00 | 67.00 | 137.00 | 17.8% | 3.3% | 3.0% | 60.5% |
| Parade | 2510 | 11.00 | 5.00 | 21.00 | 40.00 | 2.8% | 0.4% | 0.0% | 98.8% |
| Athletic | 1214 | 31.00 | 5.00 | 69.00 | 129.00 | 17.5% | 4.0% | 3.8% | 69.9% |
| Assembly | 497 | 6.00 | 3.00 | 16.00 | 39.40 | 1.8% | 1.0% | 0.2% | 99.2% |
| SideSale | 314 | 10.00 | 3.00 | 31.00 | 84.00 | 8.9% | 2.5% | 2.5% | 93.0% |

| year | permits | median_lead_days | ahead_90_days_share | permits_90_days_ahead | organization_applicant_share |
| --- | --- | --- | --- | --- | --- |
| 2016 | 941 | 5.00 | 1.1% | 10 | 74.0% |
| 2017 | 881 | 5.00 | 2.6% | 23 | 96.9% |
| 2018 | 803 | 9.00 | 2.6% | 21 | 97.9% |
| 2019 | 802 | 8.00 | 3.5% | 28 | 98.5% |
| 2020 | 67 | 14.00 | 6.0% | 4 | 91.0% |
| 2021 | 412 | 22.00 | 2.4% | 10 | 60.4% |
| 2022 | 775 | 36.00 | 14.7% | 114 | 65.8% |
| 2023 | 862 | 38.00 | 18.8% | 162 | 66.9% |
| 2024 | 909 | 44.00 | 24.5% | 223 | 65.9% |
| 2025 | 929 | 46.00 | 23.3% | 216 | 63.4% |
| 2026 | 975 | 40.00 | 22.3% | 217 | 62.6% |

| worktype | next_30_days | days_31_to_90 | days_91_to_180 | days_181_to_365 | org_applicant_91_to_365 |
| --- | --- | --- | --- | --- | --- |
| Assembly | 1 | 0 | 0 | 0 | 0 |
| Athletic | 7 | 1 | 3 | 0 | 0 |
| Festival | 21 | 9 | 13 | 0 | 7 |
| Parade | 10 | 1 | 0 | 0 | 0 |

| license_type | licenses | median_days | p25_days | p75_days | ahead_30_days_share | ahead_90_days_share |
| --- | --- | --- | --- | --- | --- | --- |
| Special Event Food | 5149 | 3.00 | 1.00 | 9.00 | 7.4% | 2.6% |
| Special Event Liquor | 2192 | 1.00 | 0.00 | 4.00 | 5.4% | 4.2% |
| Indoor Special Event | 262 | 17.00 | 10.00 | 28.75 | 23.3% | 1.5% |

- Key numbers (rates are fractions): park_total_rows = 143133; park_baseline_rows = 132701; park_load_dates = 32; park_new_real_rows_since_baseline = 4144; park_new_real_series_since_baseline = 1245; park_new_real_rows_median_lead_days = -3.00; park_new_real_rows_p25_lead_days = -17.00; park_new_real_rows_p75_lead_days = 2.00; park_new_real_rows_listed_before_event_share = 0.31; park_new_real_rows_listed_30_days_ahead_share = 0.10; park_new_rows_per_week_weeks_observed = 34.00; park_all_new_rows_since_baseline = 3222; park_all_new_rows_median_lead_days = 22.00; park_all_new_rows_listed_90_days_ahead_share = 0.18; park_real_rows_listed_after_today = 10; park_all_rows_listed_after_today = 366; cdot_weekly_applications_per_week = 19.33; cdot_weekly_applications_3_to_9_months_ahead_per_week = 3.90; cdot_weekly_org_applicants_3_to_9_months_per_week = 2.06

## H41 — Commercial cleaning: when is a space 'built out, about to open'? Build-out permit, pre-opening inspection, license

- **Signal:** Descriptive timing of three public markers: build-out permit at an unlicensed commercial space (H33), a restaurant's pre-opening 'License' inspection, the business license issue
- **Target:** Descriptive: days between the markers and weekly volumes; no outcome test (cleaning contracts and janitorial vendors are not public)
- **Data:** Chicago building permits, business license history 2014+, food inspections 2016+ ('License' = pre-opening), H33
- **Verdict:** Descriptive
- **Notes:** What cannot be known: whether a space needs cleaning, who the janitorial vendor is, contract value or term; no public dataset records cleaning purchases. The permit has no completion date, so 'construction complete' is only bracketed: the pre-opening inspection is the end of construction (a restaurant must be clean to pass), and it precedes the license by a median of two weeks, so a seller who reacts to the inspection or the license arrives after the post-construction clean; only the build-out permit (H33) arrives before it. Pre-opening 'License' inspections cover new licenses including ownership changes of existing restaurants (no build-out), and about a third of them have a renovation permit at the address in the prior year. Weekly inspection volumes carry the posting lag of the newest week. Restaurants are one license group (56% of H33 conversions); offices and retail have no pre-opening inspection.

| stage | cases | median_days | p25_days | p75_days |
| --- | --- | --- | --- | --- |
| Build-out permit (no licensee) → new business license issued (H33) | 1367 | 157.00 | 92.50 | 238.50 |
| Build-out/renovation permit → restaurant pre-opening ('License') inspection (permit in prior 365 days) | 4232 | 106.00 | 42.00 | 186.25 |
| Pre-opening inspection → business license issued | 10304 | 14.00 | 6.00 | 38.00 |
| Pre-opening inspection → License re-inspection (after a fail or conditions) | 2989 | 10.00 | — | — |
| Pre-opening inspection → first routine (Canvass) inspection | 7164 | 404.00 | 291.00 | 616.00 |

- Key numbers (rates are fractions): h33_signals = 9011; h33_conversion = 0.15; h33_baseline = 0.01; h33_lift = 10.25; h33_signals_per_week = 17.67; h33_median_days = 157.00; restaurant_license_inspections = 12946; inspections_matched_to_issue_license = 10304; inspected_before_issue_share = 1.00; first_inspection_pass_share = 0.56; reinspected_share = 0.29; buildout_inspections_with_permit_share = 0.33; preopening_restaurant_inspections_per_week = 28.62; preopening_all_facilities_per_week = 48.19; preopening_restaurant_fail_share = 0.18; new_business_sites_per_week = 66.08; new_food_sites_per_week = 19.31

## H31 — New business license + build-out permit before it → business still operating 18-30 months later

- **Signal:** First license issued (application type ISSUE) to an account at a site, for a premises-based license, with a renovation/build-out/new-construction permit at the address in the prior 365 days (vs the same without a permit, and vs a re-let space)
- **Target:** Same account and site still licensed 18-30 months later: a RENEW record issued in that window, or a license term in force on the day 24 months after the first license that was not cancelled or revoked before then
- **Data:** Chicago business licenses 2014+ (biz_license_history), permits
- **Verdict:** No signal
- **Notes:** Premises-based licenses only (peddlers, special events, pop-ups, valet, mobile food, home-based businesses, add-on permits such as outdoor patio and late hour are excluded). A site is an account number plus site number whose first record in the data is an ISSUE; sites that began before 2014 only show renewals, so signals start in 2016. Groups come from the license description and business activity text with this precedence: auto, food & drink, personal services/beauty, health/fitness/childcare, retail, other. 'conversion' = survival of the build-out group; 'baseline' = survival of the alone group standardized to the build-out group's license group by year mix. A tenant that is renamed or changes account number counts as closed, and a license cancelled after renewal still counts as renewed, so survival is a proxy for 'operating', not a measurement. The 'earlier licensee' test is by street address without unit, so large multi-tenant buildings look re-let; the multi-tenant rows show the effect. Signals stop 30 months before the newest license record. Do not add current Overture presence as a feature: it describes the business after the outcome (survivor bias).

| year | new_licenses | alive_rate | build_out_signals | build_out_alive_rate | no_build_out_alive_rate | build_out_lift |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 4310 | 58.7% | 955 | 71.9% | 55.0% | 1.30 |
| 2017 | 4853 | 57.6% | 1041 | 67.8% | 54.9% | 1.24 |
| 2018 | 2795 | 72.2% | 637 | 80.5% | 69.8% | 1.15 |
| 2019 | 2731 | 62.8% | 649 | 69.5% | 60.8% | 1.13 |
| 2020 | 3378 | 61.3% | 606 | 64.7% | 60.5% | 1.07 |
| 2021 | 3657 | 57.1% | 593 | 68.0% | 55.0% | 1.21 |
| 2022 | 3687 | 59.0% | 626 | 70.4% | 56.6% | 1.21 |
| 2023 | 3659 | 59.5% | 610 | 72.3% | 56.9% | 1.26 |
| 2024 | 1365 | 59.3% | 230 | 73.0% | 56.6% | 1.29 |

| group | new_licenses | no_build_out_alive_rate | build_out_signals | build_out_alive_rate | build_out_lift | relet_signals | relet_alive_rate | relet_lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| food & drink | 8054 | 62.0% | 2195 | 79.9% | 1.27 | 4894 | 61.4% | 0.92 |
| personal services/beauty | 2604 | 63.7% | 298 | 69.1% | 1.08 | 1841 | 62.8% | 0.94 |
| health/fitness/childcare | 1831 | 59.3% | 410 | 70.5% | 1.21 | 875 | 59.1% | 0.99 |
| retail | 7350 | 51.6% | 899 | 66.3% | 1.31 | 4988 | 51.9% | 1.03 |
| auto | 1255 | 74.6% | 137 | 87.6% | 1.18 | 790 | 74.6% | 0.99 |
| other | 9341 | 55.5% | 2008 | 61.7% | 1.11 | 3937 | 55.3% | 0.99 |

| cell | signals | alive_rate | renewed_in_window_rate | renewed_term_covering_24m_rate |
| --- | --- | --- | --- | --- |
| all new licenses | 30435 | 60.4% | 51.4% | 18.6% |
| A: new license alone (no build-out permit, no earlier licensee at the address) | 7163 | 57.9% | 48.2% | 20.8% |
| B: build-out permit in prior 365 days, no earlier licensee | 1287 | 78.2% | 64.6% | 30.2% |
| C: re-let (earlier licensee of another account), no build-out permit | 17325 | 57.9% | 50.9% | 14.4% |
| D: re-let with build-out permit | 4660 | 68.6% | 54.9% | 27.3% |
| any build-out permit (B + D) | 5947 | 70.7% | 57.0% | 27.9% |
| any re-let (C + D) | 21985 | 60.2% | 51.7% | 17.1% |

- Key numbers (rates are fractions): signals = 5947; conversion = 0.71; baseline = 0.59; lift = 1.21; signals_per_week = 10.88; new_licenses_per_week = 66.37; all_signals = 30435; excluded_not_yet_due = 3548; all_alive_rate = 0.60; no_build_out_raw_rate = 0.58; alone_raw_rate = 0.58; build_out_vs_alone_lift = 1.17; b_vs_a_lift = 1.25; d_vs_c_lift = 1.19; relet_vs_alone_lift = 0.97; single_tenant_build_out_signals = 2748; single_tenant_build_out_rate = 0.77; single_tenant_baseline = 0.62; single_tenant_lift = 1.25

## H02 — New roof → solar within 2 years

- **Signal:** Reroof permit in the past 12 months
- **Target:** Solar permit at the same parcel within 24 months
- **Data:** Permits (reroof, solar), Assessor residential characteristics
- **Verdict:** No signal

| reroofed | parcels | rate |
| --- | --- | --- |
| False | 1995720 | 0.8% |
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
| 1 | 1263 | 431281 | 0 | 15682 | 3.6% | 3.7% |
| 2 | 647 | 440473 | 896 | 13955 | 3.2% | 3.3% |
| 3 | 953 | 550938 | 2130 | 17632 | 3.2% | 3.3% |
| 4 | 954 | 527059 | 3508 | 17356 | 3.3% | 3.4% |
| 5 | 956 | 377379 | 4938 | 14453 | 3.8% | 4.0% |

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
| 1 purchase | 37433 | 35427 | 36.0% | 95.00 |
| 2 purchases | 5051 | 4207 | 34.2% | 93.00 |
| 3-5 purchases | 4336 | 1759 | 34.2% | 92.00 |
| 6+ purchases | 4562 | 447 | 29.4% | 101.00 |

| measure | permits | buyers | share |
| --- | --- | --- | --- |
| Repeat buyers' permits naming a GC the buyer used before on another property | 2454 | 556 | 55.1% |
| Benchmark: chance a randomly drawn Chicago GC (same year) would be one of those GCs | 2454 | 556 | 0.3% |

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
