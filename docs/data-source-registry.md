# Data Source Registry

*v3, 2026-11-15 (free contact-enrichment sources added). "Verified" means queried live from this project (see `research/probes/`) or read on the provider's own page. Update when a source is added, changes schema, or its access terms change.*

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

## Free contact-enrichment sources (ingested, verified 2026-11-15)

| ID | Source | Endpoint | Coverage | Cadence / lag | Key fields | Access & cost | Reliability notes | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OVERTURE-PLACES | Overture Maps Foundation, Places theme (`type=place`, GeoParquet) | `s3://overturemaps-us-west-2/release/<release>/theme=places/type=place/*` (anonymous; DuckDB `httpfs`, `SET s3_region='us-west-2'`); latest release listed at `https://overturemaps-us-west-2.s3.amazonaws.com/?list-type=2&prefix=release/&delimiter=/` | Release 2026-10-21.0: 493,243 places in the Chicago metro box (lat 41.45-42.30, lon -88.45--87.45), 472,635 not permanently closed; 197,539 in the city (Chicago bbox lat 41.64-42.03, lon -87.95--87.52 and locality Chicago or a 606xx ZIP). Of the metro rows 88% have a phone, 74% a website and 28% an email | Monthly releases (about 4 weeks apart) | name, taxonomy primary/alternates (this release has `taxonomy`, older ones `categories`), phones (E.164), websites, emails, socials (not used), address, operating status, confidence, lat/lon | **Free. License CDLA-Permissive-2.0 (open, commercial use allowed); attribution required: "Places data (c) Overture Maps Foundation"**, with the contributing sources (Meta, Microsoft and others) listed in each record's `sources` | Names are business listings, not legal names; phone and email quality varies by contributor; bbox filtering on the `bbox` struct reads only the matching row groups (about 3 s for the Chicago box; 40 MB subset) | **Verified** (synced to `data/raw/overture/places-<release>.parquet`, built as `places`; the app shows "Overture Maps" beside each value) |
| CHI-BIZ-ACTIVE | Chicago Business Licenses - Current Active | `data.cityofchicago.org/resource/uupf-x98q.json` | City of Chicago, all license types, 54,732 licenses for 36,676 accounts | Daily | account number, site number, legal name, DBA, address, ZIP, community area, license type, business activity, expiry | Free Socrata export, no key | Contractors licensed only through the Dept. of Buildings are largely absent, so few prospects match (187 of 3,216 entities matched by name) | **Verified** (`biz_licenses`) |
| CHI-BIZ-OWNERS | Chicago Business Owners | `.../resource/ezma-pppn.json` | 331,696 owner rows keyed by account number | Daily | account number, DBA, owner first/middle/last name, suffix, entity name, title | Free | Public records of business ownership; no legal-name column (join through the account number); titles include PRESIDENT, SECRETARY, SOLE PROPRIETOR, MANAGING MEMBER; used only as a contact-name suggestion for a matched business | **Verified** (`biz_owners`) |
| WEB-CONTACTS | Company websites of matched businesses (homepage plus up to 2 contact pages) | Fetched by `engine/enrich/web.py` | 273 matched sites on 2026-11-15: 207 readable (104 with an email, 172 with a phone), 10 blocked by robots.txt, 56 unreachable | On demand, cached 30 days in `data/raw/web_contacts/` (errors 3 days) | emails (own domain or common free-mail), US phone numbers | Free; User-Agent `BricklineResearchBot/0.1 (+contact: founder)`; robots.txt honored (401/403 means no crawl), 1 request/second/host, 10 s timeout, 300 KB per page | Only business contact details are kept; no social profiles; no pattern-guessed emails; JavaScript-rendered sites show nothing | **Verified** |

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
| APOLLO | Apollo contacts | Decision-makers, emails, phones | $49–$119/seat/mo; credits | Deferred: the founder declined paid providers; revisit only if the free match rates (research/findings/contact-enrichment-2026-11-13.md) are too low |
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
