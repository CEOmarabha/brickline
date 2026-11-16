# City Clerk zoning reclassifications: table summary and parse check (2026-11-16)

Source: `https://api.chicityclerkelms.chicago.gov/matter` (phrase search "Zoning Reclassification Map No" by `fileYear` 2012 onward), parsed by `engine/collect/clerk.py` into the warehouse table `zoning_changes`. Reproduce: `uv run python -m engine.warehouse sync --only clerk adu_preapprovals zoning_districts`, `build`, then this script.

## Size and range

- Rows (one per matter and address): 8,668; matters: 6,227; distinct applications (App No., or the matter itself when there is none or it is TBD): 6,098.
- Introduction dates from 2012-01-18 (matters filed from 2012 on; a handful were introduced earlier and substituted later) to 2026-12-08 (the API lists future Council meeting dates for matters just filed); passage dates 2012-03-14 to 2026-10-14.
- **Parse rate:** 6,164 of 6,227 matters (99.0%) have at least one parsed street address (8,605 address rows; 1,230 matters list several addresses, up to 82). The rest are intersections, areas or free text (examples below).
- Titles that state districts ("RS3 to RT4"): 4 matters. Planned Development named in the title: 1. App No. with a T1 suffix: 1,954. District information is otherwise not in the title or the metadata; the ordinance PDFs are scanned images, so the lab reads the target district of passed ordinances from today's zoning map (15,051 polygons, 7,319 application numbers): 4,269 of 5,365 passed matters since 2012 (79.6%) match by application number or Clerk record number.

## Status and year

| Status (`subStatus`) | Matters |
| --- | --- |
| Passed | 4,987 |
| Council Introduction | 581 |
| Passed as Substitute | 381 |
| Referred | 244 |
| Withdrawn | 21 |
| Failed to Pass | 5 |
| Repealed | 3 |
| Recommended to Pass | 2 |
| 99-Withdrawn | 1 |
| Accepted | 1 |
| Deferred and Published | 1 |

| File year | Matters | With parsed address | Passed (incl. as substitute) |
| --- | --- | --- | --- |
| 2012 | 316 | 306 (96.8%) | 290 |
| 2013 | 360 | 348 (96.7%) | 314 |
| 2014 | 445 | 438 (98.4%) | 399 |
| 2015 | 461 | 456 (98.9%) | 406 |
| 2016 | 500 | 495 (99.0%) | 440 |
| 2017 | 505 | 495 (98.0%) | 444 |
| 2018 | 508 | 506 (99.6%) | 451 |
| 2019 | 431 | 431 (100.0%) | 376 |
| 2020 | 308 | 308 (100.0%) | 268 |
| 2021 | 373 | 371 (99.5%) | 334 |
| 2022 | 407 | 405 (99.5%) | 367 |
| 2023 | 479 | 474 (99.0%) | 292 |
| 2024 | 376 | 376 (100.0%) | 339 |
| 2025 | 456 | 455 (99.8%) | 420 |
| 2026 | 302 | 300 (99.3%) | 228 |

## Titles without a parsed address (12, deterministic sample)

- Zoning Reclassification Map No. 11-F at N Clarendon Ave and W Lakeside Pl
- Zoning Reclassification Map No. 2-F at W Taylor St and S Wells St
- Zoning Reclassification Map No. 4-H at S Allport St and W 18th St
- Zoning Reclassification Map No. 28-J at W 111th St and S Pulaski Rd
- Zoning Reclassification Map No. 4-G bounded by W 21st St, S Loomis St, W Cermak Rd and S Ashland Ave
- Zoning Reclassification Map No. 13-P at W Bryn Mawr Ave and N Delphia Ave
- Zoning Reclassification Map No. 1-F and 3-F at W Oak St and N Crosby St and W Oak St and N Kingsbury St - App No. A-7818
- Zoning Reclassification Map No. 12-F at W Garfield Blvd and Chicago Transit Authority Red Line right-of-way
- Zoning Reclassification Map No. 11-P at 4525-B N Delphia Ave - App No. 22716T1
- Zoning Reclassification Map No. 1-E at E Huron St, N Rush St, E Erie St and N Wabash Ave - App No. A8791
- Zoning Reclassification Map No. 11-H App No. 17688 at 2248 W Irving Park Rd
- Zoning Reclassification Map No. 9-K at W Henderson Ave and N Kildare Ave

## Hand-check samples (20 + 20 parsed matters ordered by md5 of the matter id)

Sample A (the first 20) was read before the final parser fixes and re-read after them; sample B (the next 20) was read only after. Results are in `docs/13-signal-lab.md`.

### Sample A

| # | Title | Parsed address keys (first number kept; range end in parentheses) | App No. | Introduced | Status | Final action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Zoning Reclassification Map No. 7-J at 2760-2778 N Milwaukee Ave - App No. 18154 | 2760 N MILWAUKEE AVE (to 2778) | 18154 | 2014-09-10 | Passed | 2014-11-05 |
| 2 | Zoning Reclassification Map No. 7-K at 4516 W Fullerton Ave - App No. 22775 | 4516 W FULLERTON AVE | 22775 | 2025-06-18 | Passed | 2025-07-16 |
| 3 | Zoning Reclassification Map No. 2-H at 1901-1933 W Adams St, 1941-1959 W Adams St, 201-249 S Damen Ave, 1800-1806 W Jackson Blvd, 1814-1960 W Jackson Blvd, 216-250 S Wood St and 208-212 S Honore St - App No. 17642 | 1901 W ADAMS ST (to 1933); 1941 W ADAMS ST (to 1959); 201 S DAMEN AVE (to 249); 1800 W JACKSON BLVD (to 1806); 1814 W JACKSON BLVD (to 1960); 216 S WOOD ST (to 250); 208 S HONORE ST (to 212) | 17642 | 2012-12-12 | Passed | 2013-06-05 |
| 4 | Zoning Reclassification Map No. 24-E at 744 E 103rd St | 744 E 103RD ST |  | 2012-02-15 | Council Introduction |  |
| 5 | Zoning Reclassification Map No. 7-K at 4417-4431 W Belmont Ave/3151 N Kenneth Ave - App No. 20601T1 | 4417 W BELMONT AVE (to 4431); 3151 N KENNETH AVE | 20601T1 | 2021-01-27 | Passed | 2021-02-26 |
| 6 | Zoning Reclassification Map No. 7-I at 2820-2830 N Elston Ave - App No. 21015T1 | 2820 N ELSTON AVE (to 2830) | 21015T1 | 2022-04-27 | Passed | 2022-05-25 |
| 7 | Zoning Reclassification Map No. 14-H at 5531, 5533, 5535 and 5537 S Oakley Ave - App No. 22811 | 5531 S OAKLEY AVE; 5533 S OAKLEY AVE; 5535 S OAKLEY AVE; 5537 S OAKLEY AVE | 22811 | 2025-07-16 | Passed | 2025-09-25 |
| 8 | Zoning Reclassification Map No. 11-L at 5201 W Cullom Ave - App No. 22296 | 5201 W CULLOM AVE | 22296 | 2023-11-01 | Passed | 2023-12-13 |
| 9 | Zoning Reclassification Map No. 14-H at 5623 S Damen Ave | 5623 S DAMEN AVE |  | 2018-04-18 | Passed | 2018-05-25 |
| 10 | Zoning Reclassification Map No. 8-G 3316-3318 S Morgan St - App No. 22189 | 3316 S MORGAN ST (to 3318) | 22189 | 2023-05-24 | Council Introduction |  |
| 11 | Zoning Reclassification Map No. 1-G at 1229-1233 W Lake St - App No. 19136T1 | 1229 W LAKE ST (to 1233) | 19136T1 | 2017-03-29 | Passed | 2017-05-24 |
| 12 | Zoning Reclassification Map No. 5-M at 6214 W North Ave - App No. 22159 | 6214 W NORTH AVE | 22159 | 2023-04-19 | Council Introduction |  |
| 13 | Zoning Reclassification Map No. 30-F at 12238 S Parnell Ave - App No. 18637 | 12238 S PARNELL AVE | 18637 | 2016-02-10 | Passed | 2016-03-16 |
| 14 | Zoning Reclassification Map No. 10-F at 4351-4401 S Halsted St - App No. A-8244 | 4351 S HALSTED ST (to 4401) | A-8244 | 2016-07-20 | Passed | 2018-09-20 |
| 15 | Zoning Reclassification Map No. 4-F at 2106-2124 S Canal St and 2116-2122 S Grove St - App No. 16992 | 2106 S CANAL ST (to 2124); 2116 S GROVE ST (to 2122) | 16992 | 2009-12-16 | Passed | 2013-01-17 |
| 16 | Zoning Reclassification Map No. 12-G at 4715-4759 S Bishop St and 1412-1424 W 48th St - App No. 22181 | 4715 S BISHOP ST (to 4759); 1412 W 48TH ST (to 1424) | 22181 | 2023-05-24 | Council Introduction |  |
| 17 | Zoning Reclassification Map No. 3-F at 330 W Chestnut St - App No. 22063 | 330 W CHESTNUT ST | 22063 | 2023-01-18 | Passed | 2023-04-19 |
| 18 | Zoning Reclassification Map No. 16-G at 1414-1416 W 69th St - App No. 22946T1 | 1414 W 69TH ST (to 1416) | 22946T1 | 2025-12-10 | Passed as Substitute | 2026-02-18 |
| 19 | Zoning Reclassification Map No. 1-G at 1057 W Grand Ave and 459 N Aberdeen St - App No. 17857T1 | 1057 W GRAND AVE; 459 N ABERDEEN ST | 17857T1 | 2013-10-16 | Passed | 2013-12-11 |
| 20 | Zoning Reclassification Map No.17-H at 6909-6919 N Western Ave and 2339-2349 W Morse Ave | 6909 N WESTERN AVE (to 6919); 2339 W MORSE AVE (to 2349) |  | 2012-04-24 | Passed | 2012-06-06 |

### Sample B

| # | Title | Parsed address keys (first number kept; range end in parentheses) | App No. | Introduced | Status | Final action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Zoning Reclassification Map No. 5-F at 1623-1631 N Halsted St - App No. 20404 | 1623 N HALSTED ST (to 1631) | 20404 | 2020-05-20 | Passed | 2020-12-16 |
| 2 | Zoning Reclassification Map No. 11-J at 3431-3445 W Montrose Ave - App No. 18134T1 | 3431 W MONTROSE AVE (to 3445) | 18134T1 | 2014-07-30 | Passed | 2014-09-10 |
| 3 | Zoning Reclassification Map No. 3-H at 1422-1426 N Milwaukee Ave - App No. 18210 | 1422 N MILWAUKEE AVE (to 1426) | 18210 | 2014-11-05 | Passed | 2015-03-18 |
| 4 | Zoning Reclassification Map No. 11-L at 4030 N Milwaukee Ave - App No. 20016 | 4030 N MILWAUKEE AVE | 20016 | 2019-04-10 | Passed | 2019-07-24 |
| 5 | Zoning Reclassification Map No. 1-H at 618-622 N Ashland Ave - App No. 18276T1 | 618 N ASHLAND AVE (to 622) | 18276T1 | 2015-01-21 | Passed | 2015-06-17 |
| 6 | Zoning Reclassification Map No. 11-I at 2442-2444 W Irving Park Rd - App No. 19307 | 2442 W IRVING PARK (to 2444) | 19307 | 2017-07-26 | Passed | 2017-10-11 |
| 7 | Zoning Reclassification Map No. 18-H at 7301-7311 S Western Ave - App No. 18359 | 7301 S WESTERN AVE (to 7311) | 18359 | 2015-05-06 | Passed | 2015-06-17 |
| 8 | Zoning Reclassification Map No. 11-I at 2934 W Irving Park Rd - App No. 22944T1 | 2934 W IRVING PARK | 22944T1 | 2025-12-10 | Passed | 2026-02-18 |
| 9 | Zoning Reclassification Map No. 24-B at 3203 E 100th St - App No. 19684 | 3203 E 100TH ST | 19684 | 2018-05-23 | Council Introduction |  |
| 10 | Zoning Reclassification Map No. 16-F at 6601 S Lowe Ave - App No. 17735 | 6601 S LOWE AVE | 17735 | 2013-05-08 | Passed | 2013-06-26 |
| 11 | Zoning Reclassification Map No. 8-H at 3300-3900 S Ashland Ave | 3300 S ASHLAND AVE (to 3900) |  | 2021-09-14 | Council Introduction |  |
| 12 | Zoning Reclassification Map No. 4-G at 1631 S Carpenter St - App No. 19504 | 1631 S CARPENTER ST | 19504 | 2018-01-17 | Council Introduction |  |
| 13 | Zoning Reclassification Map No. 10-F at 505-507 W Root St - App No. 20131 | 505 W ROOT ST (to 507) | 20131 | 2019-07-24 | Passed | 2021-10-14 |
| 14 | Zoning Reclassification Map No. 3-K at 4759 W North Ave and 1555 N Cicero Ave - App No. 18340T1 | 4759 W NORTH AVE; 1555 N CICERO AVE | 18340T1 | 2015-04-15 | Passed | 2015-06-17 |
| 15 | Zoning Reclassification Map No. 1-L at 4848 W Madison St - App No. 20366 | 4848 W MADISON ST | 20366 | 2020-04-22 | Passed | 2020-05-20 |
| 16 | Zoning Reclassification Map No. 7-H at 2530-2540 N Elston Ave and 2464-2498 N Leavitt Ave - App No. 17984T1 | 2530 N ELSTON AVE (to 2540); 2464 N LEAVITT AVE (to 2498) | 17984T1 | 2014-04-02 | Passed | 2015-11-18 |
| 17 | Zoning Reclassification Map No. 13-M at 5351-5391 N Milwaukee Ave - App No. 19102 | 5351 N MILWAUKEE AVE (to 5391) | 19102 | 2017-01-25 | Passed | 2017-03-29 |
| 18 | Zoning Reclassification Map No. 3-H at 1714-1722 W Division St - App No. 18544T1 | 1714 W DIVISION ST (to 1722) | 18544T1 | 2015-10-14 | Passed | 2016-06-22 |
| 19 | Zoning Reclassification Map No. 4-H at 2317-2357 W Roosevelt Rd, 2308-2370 S Ogden Ave, 2301-2369 S Ogden Ave, 1204-1246 S Oakley Ave, 2300-2346 W 13th St and 1201-1247 S Western Ave | 2317 W ROOSEVELT RD (to 2357); 2308 S OGDEN AVE (to 2370); 2301 S OGDEN AVE (to 2369); 1204 S OAKLEY AVE (to 1246); 2300 W 13TH ST (to 2346); 1201 S WESTERN AVE (to 1247) |  | 2014-11-12 | Passed | 2015-01-21 |
| 20 | Zoning Reclassification Map No. 8-F at 3257-3259 S Emerald Ave - App No. 22123 | 3257 S EMERALD AVE (to 3259) | 22123 | 2023-03-15 | Council Introduction |  |
