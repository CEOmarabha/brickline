# Lead-signal backtests — 2026-11-15

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
| porch | 44,569 | 61.2 | 2.0% | 6.3% | 13.4% | 1.1% | 12.0x | 189.0 |
| roofing | 17,664 | 24.3 | 0.4% | 1.0% | 2.1% | 0.5% | 4.2x | 181.0 |
| elevator | 15,334 | 21.1 | 5.7% | 9.9% | 15.5% | 10.7% | 1.5x | 133.0 |
| hvac | 10,023 | 13.8 | 0.5% | 0.9% | 1.8% | 0.9% | 2.0x | 189.5 |
| electrical | 9,026 | 12.4 | 11.3% | 19.5% | 28.7% | 3.8% | 7.6x | 120.0 |
| plumbing | 8,686 | 11.9 | 4.8% | 8.2% | 13.0% | 1.1% | 11.8x | 132.0 |

| Trade | Inspection category | Episodes | Permit ≤365d |
| --- | --- | --- | --- |
| masonry | COMPLAINT | 36,808 | 9.5% |
| masonry | PERIODIC | 10,363 | 13.6% |
| masonry | PERMIT | 2 | 0.0% |
| porch | COMPLAINT | 36,378 | 14.1% |
| porch | PERIODIC | 8,142 | 10.5% |
| porch | PERMIT | 49 | 8.2% |
| roofing | COMPLAINT | 14,663 | 2.0% |
| roofing | PERIODIC | 2,693 | 2.6% |
| roofing | PERMIT | 308 | 2.3% |
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
| porch | FRACKIEL BUILDERS | 131 |
| porch | MR PORCH | 54 |
| porch | GONZON CONSTRUCTION | 49 |
| porch | SOLID REMODELERS | 42 |
| porch | EMTRAC CONSTRUCTION | 20 |

## BT4 — GC “open door”: does past sub rotation predict a new sub on the next job?

Major permits (new construction/renovation ≥ $100k). Feature = share of a GC's prior jobs that used a sub new to that GC. Tested on jobs from 2022 on, GCs with ≥5 prior jobs.

**electrical** — 12,910 test jobs; base rate of a new sub: 14.8%

| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |
| --- | --- | --- | --- |
| 1 | 0.00–0.07 | 2,582 | 5.7% |
| 2 | 0.07–0.12 | 2,582 | 7.0% |
| 3 | 0.12–0.19 | 2,582 | 12.7% |
| 4 | 0.19–0.31 | 2,582 | 17.5% |
| 5 | 0.31–1.00 | 2,582 | 31.2% |

**plumbing** — 11,603 test jobs; base rate of a new sub: 13.8%

| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |
| --- | --- | --- | --- |
| 1 | 0.00–0.06 | 2,321 | 5.7% |
| 2 | 0.06–0.13 | 2,321 | 6.0% |
| 3 | 0.13–0.20 | 2,321 | 10.9% |
| 4 | 0.20–0.33 | 2,320 | 16.3% |
| 5 | 0.33–1.00 | 2,320 | 30.1% |

**hvac** — 11,119 test jobs; base rate of a new sub: 16.1%

| Quintile of prior rotation | Prior-rate range | Jobs | Observed new-sub rate |
| --- | --- | --- | --- |
| 1 | 0.00–0.08 | 2,224 | 5.7% |
| 2 | 0.08–0.12 | 2,224 | 7.4% |
| 3 | 0.12–0.21 | 2,224 | 13.1% |
| 4 | 0.21–0.34 | 2,224 | 20.4% |
| 5 | 0.34–1.00 | 2,223 | 34.1% |

## BT5 — Restaurant build-out permit → retail food license at the same address

- Restaurant-related permits (2012–mid 2025): **5,191**; followed by a new retail food license application within a year: **29.4%**
- Median days permit issue → license application: **90.0**; → license issue: **174.0**; permit *application* → license issue: **200.0**
- Recall: **11.8%** of 14,057 new food licenses had a restaurant-related permit at the address in the prior year

## BT6 — Composite parcel score (naive Bayes), trained 2016–2019, tested 2022–2024

Target: a major permit (new construction or renovation ≥ $100k) *applied for* at the parcel within 180 days of the snapshot. Universe: 371,410 Chicago parcels per snapshot; test base rate 0.5%.

| Signal | Weight if present | Train rate if present | Lift | Parcels with signal (train) |
| --- | --- | --- | --- | --- |
| recent sale (365d) | +1.21 | 1.5% | 3.3x | 239,205 |
| recent sale to company/investor buyer (365d) | +2.19 | 4.0% | 8.6x | 42,315 |
| demolition permit (365d) | +3.02 | 8.6% | 18.8x | 4,918 |
| any building violation (365d) | +1.76 | 2.6% | 5.7x | 111,421 |
| 3+ building violations (365d) | +1.79 | 2.7% | 5.9x | 66,357 |
| vacant-building / board-up violation (730d) | +1.52 | 2.1% | 4.5x | 24,634 |
| any non-major permit (180d) | +2.23 | 4.1% | 9.0x | 92,984 |
| major permit already in last 3 years | +2.55 | 5.6% | 12.2x | 64,626 |

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
