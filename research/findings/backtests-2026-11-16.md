# Lead-signal backtests — 2026-11-16

Source: City of Chicago permits (2006–present), building violations (2010–present), retail food licenses; Cook County Assessor parcel sales (Chicago townships, 2010–present). Reproduce with `uv run python research/backtests/run_backtests.py` after building the warehouse.

Reading guide: **conversion** = share of signals followed by the target event in the window; **baseline** = the same properties' rate in an earlier, signal-free window; **lift** = conversion ÷ baseline. Permits only capture *permitted* work, so all conversion rates are lower bounds on real jobs.

## BT1 — Demolition permit → new construction on the same property

- Demolitions tested (2010–Oct 2024): **15,488**; ~13.2 per week last year
- New-construction permit issued within 2 years: **30.6%**
- …and the new-construction application was filed *after* the demolition permit: **13.4%** of demolitions
- Median days demolition → new-construction application: **-8.0**; → issue: **16.0** (p25 -6, p75 63)
- Median reported cost of the follow-on new construction: $444,450
- Demolitions with *no* new-construction permit within 60 days: 11,965; of these, new construction issued 61–730 days later: **10.2%**
- Recall: **12.3%** of 22,595 new-construction permits (2012–2026) had a demolition permit at the property in the 2 years before their application

Parties named on the follow-on new-construction permits:

| Role | Share of follow-on permits naming it |
| --- | --- |
| gc | 97.9% |
| masonry | 93.2% |
| electrical | 92.5% |
| plumbing | 91.0% |
| architect | 90.9% |
| hvac | 89.4% |

| Year | Demolitions | New construction within 2y |
| --- | --- | --- |
| 2010 | 1,123 | 15.0% |
| 2011 | 1,114 | 18.0% |
| 2012 | 1,516 | 18.3% |
| 2013 | 1,395 | 32.0% |
| 2014 | 1,177 | 41.1% |
| 2015 | 1,170 | 45.6% |
| 2016 | 1,252 | 37.1% |
| 2017 | 1,176 | 36.2% |
| 2018 | 1,108 | 33.2% |
| 2019 | 1,046 | 30.2% |
| 2020 | 711 | 29.7% |
| 2021 | 848 | 29.0% |
| 2022 | 754 | 31.4% |
| 2023 | 581 | 31.0% |
| 2024 | 517 | 35.8% |

## BT2 — Property sale → permits in the following 12 months

Chicago arm's-length single-parcel sales, 2012–mid 2025 (~516 sales/week in 2024). Post = 12 months after sale; baseline = months 13–24 *before* the sale at the same parcel.

Each cell: post-sale rate (lift vs baseline).

| Segment | Sales | roofing | masonry | porch | windows_doors | electrical | plumbing | hvac | solar | interior_buildout | major | any_permit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-family | 164,400 | 1.9% (3.4x) | 1.8% (2.5x) | 2.6% (2.4x) | 1.8% (4.1x) | 4.2% (3.7x) | 2.8% (3.0x) | 1.1% (2.7x) | 0.4% (8.1x) | 2.8% (3.4x) | 2.2% (1.9x) | 12.0% (2.9x) |
| 2-6 unit flat | 75,066 | 3.1% (5.4x) | 6.5% (4.2x) | 8.4% (3.7x) | 2.8% (5.3x) | 7.7% (4.1x) | 5.4% (4.1x) | 2.3% (4.0x) | 0.1% (4.3x) | 5.4% (5.2x) | 5.5% (5.5x) | 21.9% (3.6x) |
| commercial/industrial | 7,621 | 4.4% (2.3x) | 8.5% (2.2x) | 1.8% (1.5x) | 3.3% (3.3x) | 10.8% (1.8x) | 5.9% (2.4x) | 3.1% (1.7x) | 0.1% (5.0x) | 8.9% (2.3x) | 9.9% (2.2x) | 28.6% (1.9x) |
| apartment 7+ | 5,891 | 2.5% (1.7x) | 12.7% (2.4x) | 9.3% (2.0x) | 3.4% (2.9x) | 11.4% (2.5x) | 9.0% (3.6x) | 3.1% (2.7x) | 0.0% (2.0x) | 6.6% (4.3x) | 6.0% (2.7x) | 31.3% (1.9x) |
| single-family / individual buyer | 141,213 | 1.4% (2.4x) | 1.1% (1.4x) | 1.7% (1.4x) | 1.1% (2.3x) | 3.4% (2.8x) | 1.8% (1.7x) | 0.7% (1.6x) | 0.5% (8.4x) | 1.8% (2.0x) | 1.3% (1.0x) | 9.1% (2.0x) |
| 2-6 unit flat / individual buyer | 56,422 | 1.9% (3.0x) | 4.2% (2.6x) | 5.5% (2.3x) | 2.0% (3.4x) | 6.5% (3.3x) | 3.8% (2.6x) | 1.7% (2.8x) | 0.1% (4.2x) | 3.7% (3.2x) | 2.9% (2.5x) | 16.5% (2.5x) |
| single-family / investor buyer | 23,187 | 4.8% (14.1x) | 5.7% (16.9x) | 8.2% (16.7x) | 6.1% (32.0x) | 9.0% (14.8x) | 8.9% (21.4x) | 3.4% (23.8x) | 0.2% (5.4x) | 8.7% (30.7x) | 7.7% (16.4x) | 29.6% (14.4x) |
| 2-6 unit flat / investor buyer | 18,644 | 6.5% (16.7x) | 13.5% (10.1x) | 17.2% (9.4x) | 5.4% (14.3x) | 11.3% (6.7x) | 10.2% (11.3x) | 4.2% (8.2x) | 0.0% (6.0x) | 10.6% (14.9x) | 13.3% (27.6x) | 38.4% (7.3x) |
| commercial/industrial / investor buyer | 4,621 | 5.0% (2.9x) | 9.0% (3.0x) | 1.8% (3.0x) | 3.4% (3.6x) | 11.3% (1.9x) | 6.2% (2.5x) | 3.2% (1.6x) | 0.0% (n/a) | 9.2% (2.5x) | 11.4% (3.3x) | 30.7% (2.0x) |
| apartment 7+ / investor buyer | 4,242 | 2.8% (2.9x) | 13.6% (2.7x) | 10.0% (2.5x) | 3.7% (2.9x) | 11.7% (3.1x) | 9.2% (4.7x) | 3.4% (3.9x) | 0.0% (0.0x) | 7.0% (5.1x) | 6.5% (5.1x) | 31.6% (2.3x) |
| commercial/industrial / individual buyer | 3,000 | 3.4% (1.6x) | 7.8% (1.6x) | 1.8% (0.9x) | 3.3% (2.8x) | 10.1% (1.7x) | 5.5% (2.2x) | 2.9% (2.0x) | 0.1% (4.0x) | 8.4% (2.0x) | 7.6% (1.2x) | 25.4% (1.7x) |
| apartment 7+ / individual buyer | 1,649 | 1.9% (0.7x) | 10.2% (1.6x) | 7.3% (1.2x) | 2.5% (2.8x) | 10.5% (1.7x) | 8.2% (2.2x) | 2.3% (1.3x) | 0.1% (n/a) | 5.5% (2.8x) | 4.5% (1.0x) | 30.5% (1.3x) |

| Segment | Median days sale → first permit | p25 | p75 |
| --- | --- | --- | --- |
| 2-6 unit flat | 96.0 | 42 | 187 |
| apartment 7+ | 115.0 | 50 | 200 |
| commercial/industrial | 116.0 | 49 | 218 |
| single-family | 93.0 | 38 | 187 |

## BT3 — Building violation → matching repair permit at the same address

Episodes = first violation of that trade at an address with none in the prior year (2012–Oct 2025).

| Trade | Episodes | Per week | Permit ≤90d | ≤180d | ≤365d | Baseline (prior year) | Lift | Median days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| windows_doors | 49,744 | 68.3 | 0.4% | 0.8% | 1.6% | 0.6% | 2.9x | 175.0 |
| masonry | 47,173 | 64.8 | 2.1% | 5.3% | 10.4% | 1.3% | 8.1x | 178.0 |
| porch | 38,091 | 52.3 | 2.3% | 7.2% | 15.3% | 1.1% | 14.2x | 188.0 |
| roofing | 16,231 | 22.3 | 0.5% | 1.1% | 2.1% | 0.3% | 6.4x | 174.0 |
| elevator | 15,334 | 21.1 | 5.7% | 9.9% | 15.5% | 10.7% | 1.5x | 133.0 |
| hvac | 10,023 | 13.8 | 0.5% | 0.9% | 1.8% | 0.9% | 2.0x | 189.5 |
| electrical | 9,026 | 12.4 | 11.3% | 19.5% | 28.7% | 3.8% | 7.6x | 120.0 |
| plumbing | 8,686 | 11.9 | 4.8% | 8.2% | 13.0% | 1.1% | 11.8x | 132.0 |

| Trade | Inspection category | Episodes | Permit ≤365d |
| --- | --- | --- | --- |
| masonry | COMPLAINT | 36,808 | 9.5% |
| masonry | PERIODIC | 10,363 | 13.6% |
| masonry | PERMIT | 2 | 0.0% |
| porch | COMPLAINT | 32,932 | 15.3% |
| porch | PERIODIC | 5,115 | 15.8% |
| porch | PERMIT | 44 | 6.8% |
| roofing | COMPLAINT | 14,592 | 2.0% |
| roofing | PERIODIC | 1,639 | 3.2% |
| windows_doors | COMPLAINT | 39,063 | 1.4% |
| windows_doors | PERIODIC | 10,676 | 2.3% |
| windows_doors | PERMIT | 5 | 40.0% |

Top contractors on permits that followed porch/masonry violations (2022+):

| Trade | Contractor | Permits |
| --- | --- | --- |
| masonry | BATISTE MASONRY | 84 |
| masonry | RONALD L WALTERS GENERAL AND | 53 |
| masonry | MAGDIEL PILLADO | 45 |
| masonry | EDMAR | 28 |
| masonry | CHICAGO CONCRETE CREATIONS | 23 |
| porch | FRACKIEL BUILDERS | 129 |
| porch | MR PORCH | 51 |
| porch | GONZON CONSTRUCTION | 49 |
| porch | SOLID REMODELERS | 41 |
| porch | EMTRAC CONSTRUCTION | 20 |

## BT4 — GC “open door”: does past sub rotation predict a new sub on the next job?

Major permits (new construction/renovation ≥ $100k). Feature = share of a GC's prior jobs that used a sub new to that GC. Tested on jobs from 2022 on, GCs with ≥5 prior jobs.

**electrical** — 12,910 test jobs; base rate of a new sub: 14.1%

| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |
| --- | --- | --- | --- |
| 1 | 0.00–0.06 | 2,582 | 5.6% |
| 2 | 0.06–0.11 | 2,582 | 6.0% |
| 3 | 0.11–0.18 | 2,582 | 11.9% |
| 4 | 0.18–0.29 | 2,582 | 16.9% |
| 5 | 0.29–1.00 | 2,582 | 29.9% |

**plumbing** — 11,603 test jobs; base rate of a new sub: 13.3%

| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |
| --- | --- | --- | --- |
| 1 | 0.00–0.06 | 2,321 | 5.6% |
| 2 | 0.06–0.12 | 2,321 | 5.4% |
| 3 | 0.12–0.18 | 2,321 | 10.4% |
| 4 | 0.18–0.30 | 2,320 | 15.6% |
| 5 | 0.30–1.00 | 2,320 | 29.5% |

**hvac** — 11,119 test jobs; base rate of a new sub: 15.6%

| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |
| --- | --- | --- | --- |
| 1 | 0.00–0.07 | 2,224 | 5.6% |
| 2 | 0.07–0.12 | 2,224 | 6.6% |
| 3 | 0.12–0.20 | 2,224 | 12.5% |
| 4 | 0.20–0.33 | 2,224 | 20.0% |
| 5 | 0.33–1.00 | 2,223 | 33.3% |

## BT5 — Restaurant build-out permit → retail food license at the same address

- Restaurant-related permits (2012–mid 2025): **5,191**; followed by a new retail food license application within a year: **29.4%**
- Median days permit issue → license application: **90.0**; → license issue: **174.0**; permit *application* → license issue: **200.0**
- Recall: **11.8%** of 14,057 new food licenses had a restaurant-related permit at the address in the prior year

## BT6 — Composite parcel score (naive Bayes), trained 2016–2019, tested 2022–2024

Target: a major permit (new construction or renovation ≥ $100k) *applied for* at the parcel within 180 days of the snapshot. Universe: 371,616 Chicago parcels per snapshot; test base rate 0.5%.

| Signal | Weight if present | Train rate if present | Lift | Parcels with signal (train) |
| --- | --- | --- | --- | --- |
| recent sale (365d) | +1.21 | 1.5% | 3.3x | 239,205 |
| recent sale to company/investor buyer (365d) | +2.19 | 4.0% | 8.6x | 42,315 |
| demolition permit (365d) | +3.02 | 8.6% | 18.8x | 4,918 |
| any building violation (365d) | +1.77 | 2.6% | 5.7x | 111,421 |
| 3+ building violations (365d) | +1.79 | 2.7% | 5.9x | 66,357 |
| vacant-building / board-up violation (730d) | +1.52 | 2.1% | 4.5x | 24,634 |
| any non-major permit (180d) | +2.23 | 4.1% | 9.0x | 92,984 |
| major permit already in last 3 years | +2.56 | 5.6% | 12.2x | 64,626 |

Precision of the top-K parcels per half-year snapshot (test years):

| Top-K per snapshot | ≈ per week | Naive Bayes precision | Combination-model precision | Combination lift |
| --- | --- | --- | --- | --- |
| 100 | 4 | 4.8% | 25.7% | 56x |
| 500 | 19 | 13.0% | 18.6% | 41x |
| 2,000 | 77 | 7.4% | 12.4% | 27x |
| 10,000 | 385 | — | 5.0% | 11x |

Best single signal (demolition in last 365d) precision on test: 7.0%.

Highest-converting signal combinations (train rate, then out-of-sample test rate):

| Signals present | Train parcels | Train rate | Test parcels | Test rate |
| --- | --- | --- | --- | --- |
| any building violation (365d), 3+ building violations (365d), any non-major permit (180d), major permit already in last 3 years | 2,809 | 24.2% | 979 | 24.8% |
| any building violation (365d), any non-major permit (180d), major permit already in last 3 years | 2,596 | 15.3% | 1,085 | 16.5% |
| any non-major permit (180d), major permit already in last 3 years | 6,290 | 13.3% | 5,882 | 12.6% |
| demolition permit (365d), any non-major permit (180d) | 545 | 10.9% | 317 | 12.6% |
| recent sale (365d), recent sale to company/investor buyer (365d), any non-major permit (180d), major permit already in last 3 years | 637 | 7.9% | 535 | 9.3% |
| recent sale (365d), any non-major permit (180d), major permit already in last 3 years | 1,033 | 7.0% | 716 | 6.8% |
| recent sale (365d), recent sale to company/investor buyer (365d), any building violation (365d), 3+ building violations (365d), vacant-building / board-up violation (730d) | 374 | 6.6% | 19 | 21.1% |
| recent sale (365d), recent sale to company/investor buyer (365d), any building violation (365d), vacant-building / board-up violation (730d) | 324 | 6.3% | 2 | 50.0% |
| recent sale (365d), recent sale to company/investor buyer (365d), major permit already in last 3 years | 1,082 | 5.3% | 1,189 | 4.0% |
| recent sale (365d), any building violation (365d), any non-major permit (180d), major permit already in last 3 years | 402 | 5.1% | 96 | 6.2% |
| any building violation (365d), 3+ building violations (365d), major permit already in last 3 years | 2,721 | 5.1% | 1,271 | 6.5% |
| demolition permit (365d), any non-major permit (180d), major permit already in last 3 years | 573 | 4.3% | 263 | 6.5% |

## BT7 — 311 lead types (re-validation of signal-lab H07–H09)

Same within-property method as the signal lab: one episode per key per window; **baseline** = share of the same keys that already had the target in the equally long window *before* the signal. 311 data starts mid-2018, so these cover 2018 onward. Duplicates are excluded.

| Signal → target | Key | Window | Signals | Conversion | Baseline | Lift | Median days | Signals/week (last year) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 'Building Violation' 311 complaint → building violation | address | 120d | 96,864 | 31.6% | 5.4% | 5.8x | 32.0 | 255.4 |
| 'Porch Inspection Request' 311 call → porch permit | address | 365d | 3,014 | 13.7% | 1.2% | 11.4x | 149.5 | 7.1 |
| 'Vacant/Abandoned Building Complaint' → property sale | parcel (pin10) | 365d | 9,307 | 19.4% | 7.8% | 2.5x | 167.0 | 20.5 |

Conversion by year of the signal (signals / conversion within the window):

| Year | 'Building Violation' 311 complaint (signals / conversion) | 'Porch Inspection Request' 311 call (signals / conversion) | 'Vacant/Abandoned Building Complaint' (signals / conversion) |
| --- | --- | --- | --- |
| 2018 | 217 / 53.9% | 2 / 0.0% | 83 / 24.1% |
| 2019 | 15,001 / 49.6% | 457 / 14.4% | 2,052 / 18.2% |
| 2020 | 13,125 / 29.5% | 440 / 10.7% | 1,426 / 20.3% |
| 2021 | 14,881 / 33.1% | 441 / 13.2% | 1,377 / 18.4% |
| 2022 | 14,294 / 20.4% | 498 / 16.5% | 1,345 / 19.7% |
| 2023 | 14,033 / 22.5% | 418 / 14.6% | 1,176 / 18.4% |
| 2024 | 13,725 / 28.6% | 429 / 14.9% | 1,347 / 20.3% |
| 2025 | 11,588 / 36.4% | 329 / 10.3% | 501 / 22.4% |

## BT8 — Closed restaurant spaces (signal-lab H26)

Signal: a restaurant inspection with result 'Out of Business' (first at the street address in 365 days). Matched baseline: ordinary restaurant inspections (Pass, Pass w/ Conditions, Fail) at an address with no closure in the prior 365 days, one per address per 365 days, standardized to the closures' inspection-type mix. Closures 2016-01-01 to 2025-11-01; every window is complete. Matching is by street address, so another tenant's or the landlord's license or permit counts for both groups. The license table holds retail food establishments only, so reopenings as a bar, caterer or non-food tenant are missed and conversion is a floor. The permit view is weak: most re-lets use the space as-is or a license without a permit. Same definitions and period as signal-lab H26 (all four rows reproduce its numbers on the same warehouse); 2025 closures run to the period end only. Closures/week counts episodes (first closure at an address in 365 days) in the 52 weeks to the newest inspection on file.

| Outcome within 365 days | Closures | Conversion | Matched baseline | Lift | Median days | Middle half (days) | Closures/week (last 52 weeks) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New retail food license, different business name (headline) | 7,943 | 32.3% | 3.2% | 10.24x | 19 | 6–112 | 12.1 |
| ...issued 31+ days after the closure was recorded | 7,943 | 15.0% | 3.0% | 5.03x | 154 | 82–252 | 12.1 |
| Any new retail food license, including the same name | 7,943 | 43.0% | 4.8% | 9.02x | 15 | 5–84 | 12.1 |
| Renovation, build-out or new-construction permit | 7,943 | 11.0% | 6.2% | 1.78x | 113 | 40–210 | 12.1 |

Conversion by year of the closure (closure vs the raw rate after ordinary inspections that year, not standardized to the inspection-type mix; pre-opening inspections lift the raw 'any license' rate):

| Year | Closures | Different-name license | License 31+ days later | Any license | Renovation permit |
| --- | --- | --- | --- | --- | --- |
| 2016 | 932 | 32.2% vs 4.2% | 16.2% vs 3.6% | 43.6% vs 10.5% | 11.7% vs 8.3% |
| 2017 | 826 | 32.1% vs 5.8% | 13.7% vs 4.3% | 45.0% vs 20.2% | 12.3% vs 7.9% |
| 2018 | 726 | 36.6% vs 4.9% | 15.3% vs 3.4% | 49.7% vs 18.7% | 12.0% vs 8.5% |
| 2019 | 943 | 29.5% vs 4.0% | 14.7% vs 3.0% | 38.7% vs 12.3% | 12.8% vs 6.8% |
| 2020 | 668 | 31.9% vs 2.6% | 16.8% vs 2.1% | 38.9% vs 14.0% | 8.5% vs 4.0% |
| 2021 | 794 | 29.0% vs 4.0% | 13.7% vs 3.3% | 37.4% vs 13.6% | 11.6% vs 5.7% |
| 2022 | 787 | 31.3% vs 3.3% | 13.9% vs 2.9% | 42.2% vs 11.6% | 10.7% vs 5.8% |
| 2023 | 786 | 36.9% vs 3.9% | 16.0% vs 3.0% | 46.1% vs 13.5% | 9.9% vs 5.8% |
| 2024 | 886 | 31.1% vs 3.2% | 13.7% vs 2.8% | 42.3% vs 12.7% | 9.5% vs 5.1% |
| 2025 | 595 | 34.3% vs 3.6% | 17.5% vs 3.2% | 47.7% vs 15.2% | 10.2% vs 4.4% |

Out-of-time stability (2016-01-01 to 2020-12-31 vs 2021-01-01 to 2025-11-01): conversion vs matched baseline (lift).

| Outcome | Closures (early / late) | Early period | Late period |
| --- | --- | --- | --- |
| New retail food license, different business name (headline) | 4,095 / 3,848 | 32.3% vs 3.2% (10.23x) | 32.4% vs 3.1% (10.32x) |
| ...issued 31+ days after the closure was recorded | 4,095 / 3,848 | 15.3% vs 3.0% (5.09x) | 14.8% vs 3.0% (5.00x) |
| Any new retail food license, including the same name | 4,095 / 3,848 | 43.1% vs 4.8% (8.90x) | 42.9% vs 4.7% (9.20x) |
| Renovation, build-out or new-construction permit | 4,095 / 3,848 | 11.6% vs 7.0% (1.65x) | 10.4% vs 5.2% (2.00x) |

## BT0 — Market size: contractors active in owner-facing trades (last 12 months, non-major permits)

| Trade | Permits | Median reported cost | Distinct contractors | With 5+ jobs | Top-10 share |
| --- | --- | --- | --- | --- | --- |
| roofing | 4,192 | $23,810 | 817 | 110 | 42.2% |
| porch | 1,727 | $20,000 | 677 | 34 | 35.0% |
| windows_doors | 606 | $9,000 | 321 | 16 | 19.4% |
| solar | 1,708 | $20,390 | 56 | 27 | 86.7% |
| fence | 1,059 | $5,416 | 242 | 14 | 57.6% |
| garage | 1,911 | $20,000 | 455 | 42 | 40.0% |
| concrete_flatwork | 540 | $37,772 | 339 | 21 | 22.8% |
| masonry | 2,987 | $20,000 | 444 | 117 | 19.3% |
| hvac | 792 | $37,000 | 135 | 1 | 19.4% |
| plumbing | 2,434 | $20,000 | 521 | 111 | 23.6% |
| electrical | 6,402 | $5,000 | 848 | 231 | 26.1% |
