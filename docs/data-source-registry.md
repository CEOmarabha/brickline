# Data Source Registry

*v2, 2026-11-15 (signal-lab round 3 sources added). "Verified" means queried live from this project (see `research/probes/`) or read on the provider's own page. Update when a source is added, changes schema, or its access terms change.*

## In scope for the MVP (City of Chicago + Cook County)

| ID | Source | Endpoint | Coverage | Cadence / lag | Key fields | Access & cost | Reliability notes | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHI-PERMITS | Chicago Building Permits | `https://data.cityofchicago.org/resource/ydr8-5enu.json` | City of Chicago, 2006–present, ~853k rows | Updated daily; issued permits only; last issue date = yesterday on 2026-11-14 | permit no., type, work type, status, milestone, application/issue dates, processing time, reported cost, description, PIN, lat/long, up to 15 contacts (type, name, city, state, zip), `permit_condition` (added 2025-10), `residential_unit_change` (added 2026-10) | Free Socrata API (app token recommended for volume) | Names truncated ~30 chars; cost self-reported; no contact phone/email/address | **Verified** |
| CHI-VIOLATIONS | Chicago Building Violations | `.../resource/22u3-xenr.json` | City of Chicago | Daily | violation date, code, status, description, inspector comments, inspection category/status, address, lat/long | Free | Elevator items dominate counts; keyword mapping to trades needed | **Verified** |
| CHI-LICENSES | Chicago Business Licenses | `.../resource/r5kz-chrr.json` | City of Chicago | Daily; issued only (no pending rows found) | legal name, DBA, address, license type, business activity, application created/approved/issued dates | Free | Median 13 days application → issue | **Verified** |
| CHI-FOOD | Chicago Food Inspections | `.../resource/4ijn-s7e5.json` | City of Chicago; warehouse holds 2016-01-04 to 2026-11-13, 199,317 inspections (139,502 restaurant) | Daily | DBA, license no., risk, facility type, address, inspection date/type (incl. "License"), results (Pass, Fail, Out of Business...), violations (free text) | Free Socrata export (~209 MB CSV for 2016+) | "License" inspections precede opening; violation text is "n. HEADING - Comments: ..." items joined by `|`, with item numbering that changed over time, so flags are keyword-based; ~0.6% of addresses (ranges like "5242-5244 W NORTH AVE") need the first number taken to parse | **Verified** (ingested as `food_inspections`, with pest, plumbing, ventilation, hood and cleaning flags) |
| CHI-CDOT | Transportation Dept. permits (public way: dumpsters, closures) | `.../resource/pubx-yq2d.json` | City | Daily | — | Free | Not yet profiled | Listed |
| CHI-SIGNS | Sign permits | `.../resource/yrm5-pjgu.json` | City | Daily | — | Free | Overlaps CHI-PERMITS sign type | Listed |
| COOK-PERMITS | Cook County Assessor – Permits | `https://datacatalog.cookcountyil.gov/resource/6yjf-dfxs.json` | 113 municipalities incl. Chicago | Semi-monthly; **2–4 month lag** (monthly counts drop after June 2026) | PIN, permit no., local permit no., date issued, amount, municipality, address, applicant, job/improvement codes, description | Free | No contractor fields; job codes unreliable per notes | **Verified** |
| COOK-SALES | Cook County Assessor – Parcel Sales | `.../resource/wvhk-k5uv.json` | Cook County, 1999–present | Semi-monthly; newest sale 2026-08-12 (**~3 month lag**) | PIN, sale date, price, deed type, buyer, seller, doc no. | Free | Includes some non-arm's-length sales | **Verified** |

## Signal-lab round 3 sources (ingested, verified 2026-11-15)

| ID | Source | Endpoint | Coverage | Cadence / lag | Key fields | Access & cost | Reliability notes | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CFPB-HMDA | CFPB / FFIEC HMDA Data Browser, home-improvement loans (loan_purpose=2, originated) | `https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?counties=17031&years=<Y>&loan_purposes=2&actions_taken=1` (redirects to a prebuilt CSV on `files.ffiec.cfpb.gov`; use a client that follows redirects) | Cook County, 2018–2025 loaded (5,808 / 5,362 / 3,284 / 3,829 / 5,535 / 4,581 / 5,023 / 5,682 loans; 15,596 of 39,104 fall in Chicago tracts, about 1,360–2,600 a year) | Annual; the 2025 file was already available in Nov 2026 | census tract, loan amount, occupancy, income, lien, open-end line of credit, business purpose, dwelling category (applicant demographic fields exist, not loaded) | Free, no key | Tracts are 2010 vintage through 2021 and 2020 vintage from 2022; loans are mortgage-financed work only, a few per tract per year; an `--compressed` curl without `-L` returns a redirect page, not data | **Verified** (ingested as `hmda_home_improvement`; no signal, H27) |
| CHI-TRACTS | Chicago Boundaries – Census Tracts 2010 (`74p9-q2aq`) and 2020 (`7qjk-677h`) | `data.cityofchicago.org/resource/<id>.csv` | 801 and 789 tracts with WKT geometry and community area | Static | geoid (2020 file: `tract_fips` + `tract_ce`), community area, geometry | Free | Needed to match each HMDA year to its own tract map | **Verified** (ingested as `tracts`) |
| NOAA-SWDI-HAIL | NOAA NCEI Severe Weather Data Inventory, NEXRAD Level-3 hail signatures (`nx3hail`) | `https://www.ncei.noaa.gov/swdiws/csv/nx3hail/<yyyymmdd>:<yyyymmdd>/<limit>?bbox=<minLon,minLat,maxLon,maxLat>` | Chicago box (-87.95,41.62,-87.50,42.05), pulled 2016-01 to 2026-11 (first detection 2016-03-15, last 2026-08-11); 3,239 detections, 105 days, 1,970 detections of at least 1 inch on 103 days | Near real time | scan time (UTC), radar id, cell id, probability of hail, probability of severe hail, estimated max size (inch), centroid lat/lon | Free, no key | One centroid per tracked cell per scan, not a swath polygon (no MESH grid); service rejects ranges over 744 hours, so the collector pulls one month at a time; coordinates are the cell centroid | **Verified** (ingested as `hail_cells`; no signal, H28) |

## Candidates (not yet verified)

| ID | Source | Use | Access | Next step |
| --- | --- | --- | --- | --- |
| CHI-ZONING | City Council zoning amendments / Planned Developments (City Clerk legislative system) | Pre-permit commercial projects | Web/PDF; API unknown | Backlog #3 |
| CHI-PLANCOMM | Chicago Plan Commission, ZBA, Community Development Commission agendas | Pre-permit | PDFs | Backlog #3 |
| CHI-PROCURE | City of Chicago, CPS, Park District, Public Building Commission bids | Public work | Portals | Backlog (Deliverable 10 #8) |
| AURORA | Aurora ArcGIS permit service | Suburban permits | ArcGIS REST | Profile when suburbs are in scope |
| NAPERVILLE | Naperville permit downloads | Suburban permits | Downloads (reported) | Verify |
| JOLIET | Joliet permits | Suburban permits | Login-only portal; monthly reports via FOIA (third-party report) | Buy or FOIA |
| SHOVELS | Shovels permits/contractors/decisions/properties | Suburbs, pre-permit decisions, contractor profiles | Free 500 credits; $599 / $999 per month | Free-tier coverage test (backlog #10) |
| APOLLO | Apollo contacts | Decision-makers, emails, phones | $49–$119/seat/mo; credits | Match-rate test (backlog #4) |
| NOAA-STORMS | NOAA storm events / hail | Roofing (residential cluster) | Free | Ingested in round 1 (`storms`); spotter points, no signal (H04, H05). Radar footprints now ingested (see SWDI below) |
| IL-SOS | Illinois business entity records | New businesses, registered agents | Web lookup; bulk availability unknown | Verify |

## Source reliability scoring (to apply per source)

| Factor | Measure |
| --- | --- |
| Freshness | Median hours from event to availability |
| Completeness | % of expected records present vs official counts |
| Field quality | Null rate and parse success on key fields |
| Stability | Schema changes per year; outages |
| Legal clarity | Explicit open-data terms vs ToS ambiguity |
