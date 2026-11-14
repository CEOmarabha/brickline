# Data Source Registry

*v1, 2026-11-14. "Verified" means queried live from this project (see `research/probes/`) or read on the provider's own page. Update when a source is added, changes schema, or its access terms change.*

## In scope for the MVP (City of Chicago + Cook County)

| ID | Source | Endpoint | Coverage | Cadence / lag | Key fields | Access & cost | Reliability notes | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHI-PERMITS | Chicago Building Permits | `https://data.cityofchicago.org/resource/ydr8-5enu.json` | City of Chicago, 2006–present, ~853k rows | Updated daily; issued permits only; last issue date = yesterday on 2026-11-14 | permit no., type, work type, status, milestone, application/issue dates, processing time, reported cost, description, PIN, lat/long, up to 15 contacts (type, name, city, state, zip), `permit_condition` (added 2025-10), `residential_unit_change` (added 2026-10) | Free Socrata API (app token recommended for volume) | Names truncated ~30 chars; cost self-reported; no contact phone/email/address | **Verified** |
| CHI-VIOLATIONS | Chicago Building Violations | `.../resource/22u3-xenr.json` | City of Chicago | Daily | violation date, code, status, description, inspector comments, inspection category/status, address, lat/long | Free | Elevator items dominate counts; keyword mapping to trades needed | **Verified** |
| CHI-LICENSES | Chicago Business Licenses | `.../resource/r5kz-chrr.json` | City of Chicago | Daily; issued only (no pending rows found) | legal name, DBA, address, license type, business activity, application created/approved/issued dates | Free | Median 13 days application → issue | **Verified** |
| CHI-FOOD | Chicago Food Inspections | `.../resource/4ijn-s7e5.json` | City of Chicago | Daily | DBA, license no., risk, address, inspection date/type (incl. "License"), results, violations | Free | "License" inspections precede opening | **Verified** |
| CHI-CDOT | Transportation Dept. permits (public way: dumpsters, closures) | `.../resource/pubx-yq2d.json` | City | Daily | — | Free | Not yet profiled | Listed |
| CHI-SIGNS | Sign permits | `.../resource/yrm5-pjgu.json` | City | Daily | — | Free | Overlaps CHI-PERMITS sign type | Listed |
| COOK-PERMITS | Cook County Assessor – Permits | `https://datacatalog.cookcountyil.gov/resource/6yjf-dfxs.json` | 113 municipalities incl. Chicago | Semi-monthly; **2–4 month lag** (monthly counts drop after June 2026) | PIN, permit no., local permit no., date issued, amount, municipality, address, applicant, job/improvement codes, description | Free | No contractor fields; job codes unreliable per notes | **Verified** |
| COOK-SALES | Cook County Assessor – Parcel Sales | `.../resource/wvhk-k5uv.json` | Cook County, 1999–present | Semi-monthly; newest sale 2026-08-12 (**~3 month lag**) | PIN, sale date, price, deed type, buyer, seller, doc no. | Free | Includes some non-arm's-length sales | **Verified** |

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
| NOAA-STORMS | NOAA storm events / hail | Roofing (residential cluster) | Free | Only if residential cluster pursued |
| IL-SOS | Illinois business entity records | New businesses, registered agents | Web lookup; bulk availability unknown | Verify |

## Source reliability scoring (to apply per source)

| Factor | Measure |
| --- | --- |
| Freshness | Median hours from event to availability |
| Completeness | % of expected records present vs official counts |
| Field quality | Null rate and parse success on key fields |
| Stability | Schema changes per year; outages |
| Legal clarity | Explicit open-data terms vs ToS ambiguity |
