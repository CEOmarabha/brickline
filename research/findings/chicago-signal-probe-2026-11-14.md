# Chicago public-data signal probe — 2026-11-14

Window: permits last 90 days; other signals last 30 days. Source: City of Chicago Data Portal (Socrata). Re-run with `python3 research/probes/chicago_signal_probe.py`.

## Building permits

- All issued permits: **8,731** (~679.1/week)
- Major projects (PERMIT - NEW CONSTRUCTION / PERMIT - RENOVATION/ALTERATION with reported_cost >= $100,000): **1,082** (~84.2/week)
- Value buckets: >=100k: 1,082, >=500k: 429, >=1M: 199, >=5M: 50
- Days from application to issue (major): p25 27, median 64, p75 130, p90 224
- Distinct general contractors on major permits: 627

### Share of major permits where the party is already named at issue

| Party | % of major permits |
| --- | --- |
| owner | 100.0% |
| general_contractor | 99.3% |
| architect | 96.0% |
| electrical | 92.2% |
| plumbing | 83.9% |
| hvac | 74.4% |
| masonry | 41.4% |

### Field completeness (major permits)

| Field | % present |
| --- | --- |
| reported_cost | 100.0% |
| lat_long | 99.2% |
| pin | 99.2% |
| description_40_chars | 99.9% |

### Most active general contractors (major permits)

| GC | Permits | Reported value |
| --- | --- | --- |
| CENTRE CONSTRUCTION SERVICES LLC | 20 | $10,371,390 |
| MK CONSTRUCTION & BUILDERS, INC. | 19 | $6,837,340 |
| LEOPARDO CONSTRUCTION INC | 16 | $86,663,677 |
| JC ANDERSON INC | 16 | $15,528,807 |
| POWER CONSTRUCTION COMPANY, LLC | 15 | $39,360,877 |
| SKENDER CONSTRUCTION LLC | 14 | $244,804,232 |
| BEAR CONSTRUCTION COMPANY | 12 | $8,012,545 |
| REDMOND CONSTRUCTION CORP. | 11 | $56,679,287 |
| BULLEY & ANDREWS, L.L.C. | 11 | $53,650,864 |
| EXECUTIVE CONSTRUCTION , INC. | 10 | $21,385,400 |
| BURLING BUILDERS, INC | 8 | $43,250,000 |
| REED CONSTRUCTION LLC | 8 | $5,914,770 |
| PEPPER CONSTRUCTION COMPANY | 7 | $106,757,541 |
| CLUNE CONSTRUCTION COMPANY, L.P. | 7 | $38,166,278 |
| TORO CONSTRUCTION CORP | 7 | $19,900,000 |

### Subcontractor market structure (major permits)

| Trade | Distinct contractors | Top-10 share of jobs | Top 3 |
| --- | --- | --- | --- |
| electrical | 353 | 20.8% | CURRENT COMMUNICATIONS CORP. (28); BLUE LINE ELECTRICAL CONTRACTO (27); CHAVEZ ELECTRIC (25) |
| plumbing | 312 | 20.8% | GEHRETT PLUMBING, INC. (25); VJJ PLUMBING (24); GREAT LAKES PLUMBING & HEATING (24) |
| hvac | 411 | 14.5% | ADMIRAL HEATING & VENTILATING (16); INDOOR AIR MECHANICAL INC. (15); DUNRITE MECHANICAL, INC (14) |
| masonry | 210 | 25.3% | ALL CONCRETE CONTRACTORS INC (28); CRS CONCRETE LTD (17); DEXCO CORPORATION (16) |

### Which subcontractors the busiest GCs used (relationship map sample)

| GC | Electrical | Plumbing | HVAC |
| --- | --- | --- | --- |
| CENTRE CONSTRUCTION SERVICES LLC (20) | CURRENT COMMUNICATIONS CORP. (8); PROGRESS ELECTRIC COMPANY (3); S & M ELECTRIC, INC. (3) | JOHNS PLUMBING, INC. (11); AIR COMFORT, LLC. (2); SCHAAF PLUMBING SOLUTIONS LLC (2) | ENVIROMENTAL MECHANICAL SERV. (5); SHERMAN MECHANICAL INC (3); RAM MECHANICAL SERVICES, INC. (3) |
| MK CONSTRUCTION & BUILDERS, INC. (19) | FAST TREK ELECTRIC INC (10); RAFAL SZARWARK (4); DKB PRO SKILL INC (3) | STX CONSTRUCTION & PLUMBING (12); BUCZAK CORPORATION (3); ZRYW PLUMBING INC (2) | INDOOR AIR MECHANICAL INC. (15); INDOOR AIR MECHANICAL INC (3) |
| LEOPARDO CONSTRUCTION INC (16) | GRAND-KAHN, LLC (5); ROCHA ELECTRIC COMPANY (2); SHAMROCK ELECTRIC CO.INC (1) | HOGAN PLUMBING, INC. (3); R. CARROZZA PLUMBING CO (2); GREAT LAKES PLUMBING & HEATING (1) | AIR COMFORT, LLC (2); WESTSIDE MECHANCIAL DESIGN/BUI (2); MCCAULEY MECHANICAL CONSTRUCTI (2) |
| JC ANDERSON INC (16) | BLADE ELECTRIC & (4); LOMBARDI ELECTRIC, INC. (4); SKITCH ELECTRIC COMPANY (2) | GEHRETT PLUMBING, INC. (5); HAYES INDUSTRIES, INC. (1); JOHNS PLUMBING, INC. (1) | ENVIRONMENT MECHANICAL SERVICE (4); COMPETITIVE PIPING SYSTEMS INC (3); ENVIROMENTAL MECHANICAL SERV. (2) |
| POWER CONSTRUCTION COMPANY, LLC (15) | BLADE ELECTRIC & (5); CONNELLY ELECTRIC CO. (2); MARON ELECTRIC COMPANY (1) | DW MECHANICAL GROUP,INC. (6); ASHLAND PLUMBING & HEATING CO. (2); WARREN THOMAS PLUMBING (1) | ADMIRAL HEATING & VENTILATING (3); WESTSIDE MECHANICAL (1); SHERMAN MECHANICAL INC (1) |
| SKENDER CONSTRUCTION LLC (14) | MARON ELECTRIC COMPANY (7); TITAN ELECTRIC LLC (2); KELSO-BURNETT CO. (2) | DW MECHANICAL GROUP,INC. (4); GREAT LAKES PLUMBING & HEATING (3); EWING-DOHERTY MECHANICAL, INC (2) | ADMIRAL HEATING & VENTILATING (4); ATOMATIC MECHANICAL SERVICES (2); ADVANCED MECHANICAL (1) |
| BEAR CONSTRUCTION COMPANY (12) | CURRENT COMMUNICATIONS CORP. (6); BLOCK ELECTRIC COMPANY (2); CECO, INC. (2) | JOHNS PLUMBING, INC. (3); CARBONE PLUMBING, INC (1); ASHLAND PLUMBING & HEATING CO. (1) | ENVIRONMENT MECHANICAL SERVICE (3); COMPETITIVE PIPING SYSTEMS INC (2); COMPETITIVE PIPING SYSTEMS (2) |
| REDMOND CONSTRUCTION CORP. (11) | KELSO-BURNETT CO. (5); CECO, INC. (4); MARON ELECTRIC COMPANY (1) | GREAT LAKES PLUMBING & HEATING (3); GEHRETT PLUMBING, INC. (2); A+PLUS PLUMBING, INC. (1) | ADMIRAL HEATING & VENTILATING (5); HILL MECHANICAL (1); RAM MECHANICAL SERVICES, INC. (1) |

### Permits by work type (all permits)

| Work type | Count |
| --- | --- |
| (blank) | 2,994 |
| Electrical Work | 1,458 |
| Masonry Work | 627 |
| Small-Scale Solar PV System | 523 |
| Reroofing | 473 |
| Administrative Change | 466 |
| Nonstructural Interior Work | 276 |
| Fire Alarm System | 272 |
| Fence or Trash Enclosure | 256 |
| Porch,Deck,Balcony,or Fire Escape | 251 |
| Monthly Maintenance Permit | 215 |
| Detached Frame Garage | 187 |
| Plumbing Work | 176 |
| Mechanical Work | 119 |
| Scaffolding | 115 |
| Other Work | 103 |
| Communication Equipment | 93 |
| Exterior Windows/Doors Replacement | 86 |
| Storm Water Management Plan | 33 |
| Small Temporary Structure | 5 |
| Construction Trailer | 3 |

## Building violations (intent signal: owner is ordered to fix something)

- Violations recorded: **3,463**; open: **3,418** at 876 distinct addresses

| Trade (keyword match on open violations) | Violations | Distinct addresses |
| --- | --- | --- |
| windows_doors | 337 | 209 |
| porch_deck_stairs | 185 | 143 |
| smoke_co_detectors | 94 | 83 |
| masonry_tuckpointing | 93 | 81 |
| plumbing | 81 | 50 |
| heating_hvac | 58 | 42 |
| roofing | 51 | 46 |
| pest | 47 | 39 |
| electrical | 42 | 29 |

Top open violation descriptions:

- MAINTAIN OR REPAIR ELECT ELEVA — 376
- ARRANGE PREMISE INSPECTION — 230
- MAINTAIN OR REPAIR HYDRO ELEVA — 147
- REPAIR EXTERIOR WALL — 127
- REPAIR PORCH SYSTEM — 77
- REPAIR INTERIOR WALLS/CEILING — 62
- STOP/REMOVE NUISANCE — 62
- INSTALL SMOKE DETECTORS — 53
- PLANS & PERMITS REQ - CONTRCTR — 51
- REPAIR FENCE — 48
- MAINTAIN WINDOW — 47
- REPLCE WINDOW PANES, PLEXGLAS — 47

## New business licenses (new-business signal for B2B services)

- New licenses issued: **621**
- New applications still pending (filed in window, not yet issued): **0**
- Days from application to issue: median 13, p75 50

| License type (issued) | Count |
| --- | --- |
| Limited Business License | 138 |
| Retail Food Establishment | 101 |
| Pop-Up Retail User | 99 |
| Regulated Business License | 81 |
| Pharmaceutical Representative | 33 |
| Consumption on Premises - Incidental Activity | 21 |
| Video Gaming Location | 17 |
| Shared Kitchen User (Long Term) | 15 |
| Peddler License | 11 |
| Special Event Food | 10 |
| Commercial Garage | 10 |
| Animal Care License | 8 |

## Restaurant license inspections (a food business about to open)

- License-type food inspections: **221**

| Inspection type | Result | Count |
| --- | --- | --- |
| License | Pass | 104 |
| License Re-Inspection | Pass | 33 |
| License | Fail | 31 |
| License | Not Ready | 25 |
| License | Pass w/ Conditions | 21 |
| License | No Entry | 3 |
| License Re-Inspection | Pass w/ Conditions | 3 |
| License Re-Inspection | Fail | 1 |
