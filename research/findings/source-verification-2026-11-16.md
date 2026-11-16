# Source verification, 2026-11-16 (Deliverable A)

Every source below was requested with a descriptive User-Agent (`BricklineResearchBot/0.1 (public-records research; +contact: founder)`), robots.txt checked first, at most one request per second per host (robots Crawl-delay honored), and only small samples (Socrata `$limit=5`, capped downloads, HTTP Range for bulk files). Nothing was bypassed: blocked requests are recorded as blocked. 'Verified' means the data was actually retrieved in this run; 'partial' means documents/portal only or only part of the chain was retrieved. In the JSON, the `probe` object of each source holds what was measured; every other field (coverage, effort, signal quality, uses, verdict reason) is the author's assessment, written from the probe results and the pages read.

Machine-readable catalog: `research/findings/source-verification-2026-11-16.json` (regenerate with `python3 research/probes/source_check.py`).

## Summary table

| Source | Name | Case | Verdict | Access | Cost | Records seen | Signal quality for Brickline |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `hfsrb-project-list` | Illinois HFSRB project search listing (CON + exemption projects) | 1 | VERIFIED | HTML page backed by a public JSON model endpoint | free | 1,692 | Medium as a list (names only); high once joined to the project pages and PDFs. |
| `hfsrb-project-pages` | Illinois HFSRB per-project pages (dates, status, document links) | 1 | PARTIAL | HTML | free | 5 | High: stage-by-stage dates (when populated) and the document trail. |
| `hfsrb-pdf-documents` | Illinois HFSRB PDFs: State Board staff reports and permit approval letters | 1 | PARTIAL | PDF documents linked from each project page | free | 5 | Highest content value (cost + equipment + dates), lowest structure. |
| `ga-dch-con-tracking` | Georgia DCH Certificate of Need weekly tracking report (PDF) | 1 | PARTIAL | Weekly PDF linked from one HTML page | free | 1 | High content, but Georgia only; history needs a self-built archive or the Wayback Machine. |
| `cms-pos` | CMS Provider of Services file (QIES), latest quarter | 1 | VERIFIED | data-api JSON + CSV download on data.cms.gov | free | 398 | Medium: capability flags, not purchase events; useful for qualification and territory sizing. |
| `cms-hospital-enrollments` | CMS Hospital Enrollments (PECOS) and Hospital All Owners, latest | 1,4 | VERIFIED | data-api JSON + CSV on data.cms.gov | free | 318 | Low-medium for contractors; medium for healthcare-sales. |
| `cms-hcris-hospital-cost-report` | CMS Hospital Provider Cost Report (HCRIS-derived), latest fiscal year | 1 | VERIFIED | data-api JSON + CSV on data.cms.gov | free | 205 | Medium: 1-2 year lag, hospital-level aggregates only. |
| `nppes-api` | NPPES NPI Registry API (v2.1) | 1,4 | VERIFIED | REST JSON API | free | 3 | Medium-high for healthcare B2B (new clinics register an NPI before they open); no cost or... |
| `nppes-monthly-file` | NPPES monthly full file and weekly delta files | 1,4 | VERIFIED | Bulk ZIP | free | n/a | Same as the API; better for backtests. |
| `idph-hospital-directory` | Illinois IDPH Hospital Directory (Illinois open data portal) | 1 | VERIFIED | Socrata API | free | 207 | Medium: master data, not events. |
| `idph-astc-directory` | Illinois IDPH Ambulatory Surgical Treatment Center Directory | 1 | VERIFIED | Socrata API | free | 156 | Medium: master data. |
| `openfda-device-registration` | openFDA device registration and listing | 1 | PARTIAL | REST JSON API | free | 10,409 | Low for Brickline's use cases: there is no public registry of installed MRI/CT units. |
| `seattle-building-permits` | Seattle Building Permits (SDCI), issued and in progress | 2 | VERIFIED | Socrata API | free | 194,311 | High as a method reference; not Chicago. |
| `chicago-building-permits` | Chicago Building Permits (already ingested): stage fields | 2 | VERIFIED | Socrata API | free | 853,111 | High for relationships and timing; no pre-issue stage. |
| `chicago-adu-preapproval` | Chicago Additional Dwelling Unit (ADU) preapproval applications | 2 | VERIFIED | Socrata API | free | 616 | Medium: small volume (hundreds) and owner-applicant data (names not stored here). |
| `chicago-doe-environmental-permits` | Chicago Department of Environment / CDPH environmental permits (air quality, demolition, etc.) | 2,3 | VERIFIED | Socrata API | free | 67,886 | Medium: narrow permit types; useful as a precursor for demolition and facade work. |
| `chicago-clerk-elms` | Chicago City Clerk eLMS API (ordinances: zoning reclassifications, Planned Developments, committee referrals) | 2 | VERIFIED | REST JSON API | free | 1,487 | High potential for Track 2 (pre-application projects); about 1,500 matters in 11 years, so... |
| `chicago-dob-performance-metrics` | Chicago DOB 'Time to Issue' performance-metric datasets | 2 | VERIFIED | Socrata API | free | 166 | Low |
| `chicago-gov-planning-pages` | chicago.gov pages: Plan Commission, Zoning Board of Appeals agendas, Dept. of Buildings permit pages | 2 | BLOCKED | Web pages and PDF agendas on chicago.gov | free | n/a | Unknown: not assessable from this client. |
| `tceq-central-registry` | TCEQ Central Registry files on data.texas.gov (Dallas / Fort Worth) | 3 | VERIFIED | Socrata API | free | 671,878 | Medium for Texas; not Chicago. |
| `tceq-air-permit-status` | TCEQ air permit status query (New Source Review, PBR, Title V) | 3 | PARTIAL | Web query application | free | n/a | High content; query-only access means scraping a form, which is not done here. |
| `rrc-data-downloads` | Texas Railroad Commission data sets available for download (drilling permits, production) | 3 | PARTIAL | Bulk files | free | 64 | High for oil and gas suppliers; irrelevant to Chicago. |
| `rrc-well-bottom-location` | RRC well bottom location (data.texas.gov) | 3 | VERIFIED | Socrata API | free | 1,397,402 | Low-medium. |
| `il-epa-air-permits` | Illinois EPA Bureau of Air permit applications and Document Explorer | 3 | PARTIAL | Web pages and a document-search web application | free | 0 | Medium-high if the application list can be obtained without form scraping. |
| `epa-echo-cook-air` | EPA ECHO facility search REST services (Cook County air-program facilities) | 3 | VERIFIED | REST JSON API and bulk downloads | free | 4,845 | Medium: current state only, but strong for B2B prospecting of industrial sites. |
| `fl-sunbiz-bulk` | Florida Division of Corporations (Sunbiz) data downloads | 4 | PARTIAL | Daily and quarterly bulk files | free | n/a | High for Florida; shows the model Chicago lacks (free bulk daily new-entity feed). |
| `il-sos-business-entities` | Illinois Secretary of State business entity search and bulk data | 4 | BLOCKED | Web search application | unknown (not verified) | n/a | High if obtainable; not obtainable here. |
| `chicago-business-licenses-history` | Chicago Business Licenses (full history; application type, dates, activity) | 4 | VERIFIED | Socrata API | free | 1,211,708 | High: richest Chicago new-business feed; already partly ingested as current-active only. |
| `il-idfpr-professional-licensing` | Illinois IDFPR Professional Licensing (Illinois open data portal) | 4 | VERIFIED | Socrata API | free | 4,462,647 | Medium: mostly individuals; practice address often missing. |
| `census-bfs` | Census Business Formation Statistics (BFS) monthly CSV | 4 | VERIFIED | Bulk CSV | free | 37,345 | Low for lead generation; useful for normalization. |
| `lever-public-postings` | Public applicant-tracking-system job APIs (Lever example) | 4 | PARTIAL | Per-company public JSON API | free | 2 | Low: no Chicago employer list is available; large job boards (Indeed, LinkedIn) were not... |
| `orlando-permit-applications` | City of Orlando Permit Applications (open data) | 5 | VERIFIED | Socrata API | free | 1,115,699 | High as a method reference; Orlando, not Chicago. |
| `fdor-property-rolls` | Florida Dept. of Revenue assessment roll files (NAL/SDF) incl. Orange County | 5 | PARTIAL | Bulk files per county from the state data portal | free | n/a | Medium. |
| `orange-county-property-appraiser` | Orange County (FL) Property Appraiser web site | 5 | NOT FOUND | Single-page web application | unknown | n/a | Not assessable: no data export endpoint found with plain requests. |
| `noaa-storm-events` | NOAA NCEI Storm Events Database (bulk CSV, already ingested) | 5 | VERIFIED | Bulk gzipped CSV per year | free | 77 | Low in Chicago (H04, H05 found no signal). |
| `noaa-swdi-hail` | NOAA SWDI NEXRAD Level-3 hail signatures (already ingested) | 5 | VERIFIED | REST CSV service | free | 5 | Low in Chicago. |
| `cook-assessor-residential-chars` | Cook County Assessor residential characteristics (roof construction, year built) | 5 | VERIFIED | Socrata API | free | 30,656,402 | Medium: roof construction code only (no roof age or replacement year). |
| `cook-assessor-commercial-valuation` | Cook County Assessor commercial valuation data | 5 | VERIFIED | Socrata API | free | 109,409 | Medium: no roof fields; annual snapshot. |
| `sam-opportunities-api` | SAM.gov Get Opportunities public API | 0 | BLOCKED | REST API | free (key) | 0 | Medium: federal work is a small share of Chicago contractor revenue. |
| `usaspending-api` | USAspending.gov API (awards by place of performance) | 0 | BLOCKED | REST API | free | 0 | Medium. |
| `sec-edgar` | SEC EDGAR submissions API and full-text search | 0 | VERIFIED | REST JSON APIs | free | 1,002 | Low-medium. |
| `census-cbp` | Census County Business Patterns (bulk county file) | 0 | VERIFIED | Bulk ZIP per year | free | n/a | Low for leads. |
| `fmcsa-company-census` | FMCSA Company Census File (data.transportation.gov) | 0 | VERIFIED | Socrata API | free | 20,715 | Medium-high for fleet B2B; current state only (no change history). |
| `chicago-contracts` | City of Chicago Contracts (data portal) | 0 | VERIFIED | Socrata API | free | 189,023 | Medium-high for public-work subcontractors. |
| `cook-procurement-awards` | Cook County Procurement: awarded contracts and amendments | 0 | VERIFIED | Socrata API | free | 8,342 | Medium. |
| `cook-procurement-bids` | Cook County Procurement: bid tabulations | 0 | VERIFIED | Socrata API | free | 5,689 | Medium-high for public-work subs. |
| `cook-procurement-buying-plan` | Cook County Procurement: Buying Plan FY2026 (forward-looking) | 0 | VERIFIED | Socrata API | free | 164 | Medium. |
| `il-future-solicitations` | State of Illinois Future Solicitations (open data portal) | 0 | VERIFIED | Socrata API | free | 47 | Medium. |
| `il-cdb-registered-vendors` | Illinois Capital Development Board registered vendors | 0,4 | VERIFIED | Socrata API | free | 2,880 | Medium for prospecting. |
| `chicago-food-inspections` | Chicago Food Inspections (already ingested): freshness | 0 | VERIFIED | Socrata API | free | 318,396 | High (backtested). |
| `chicago-311` | Chicago 311 Service Requests (already ingested): freshness | 0 | VERIFIED | Socrata API | free | 14,993,850 | High (backtested). |

Case 0 = cross-cutting. 'Records seen' is the dataset total where the API reports one, otherwise the sample size retrieved.

## What this means for Brickline

**The Chicago-focused answer to each case study**

| Case | What the original source does | Chicago / Illinois equivalent found | Verdict |
| --- | --- | --- | --- |
| 1. Georgia CON -> medical equipment | Weekly PDF lists letters of intent and applications with applicant, service, site, contact and estimated cost (the brief's 6-12 month lead-time premise was not measured here) | Illinois HFSRB lists every CON and exemption project (1,692 since 2011) with a per-project page; staff reports and permit approval letters carry cost, facility, permit holders and an equipment description. No weekly report and no API, but better history than Georgia. Equipment is only named in the description text, and the equipment threshold is high (FY2026 capital expenditure minimum $4,779,437, stated in the 26-032 staff report), so typical MRI/CT replacements below it never appear. | PARTIAL, usable |
| 2. Seattle permits/plan review -> trades | Seattle publishes applications, review-complete and ready-to-issue dates, and status for 194,311 permits | Chicago publishes only issued permits (`permit_status` holds ACTIVE/COMPLETE/EXPIRED...; no in-review values) but with `application_start_date` and `issue_date`, so the review duration is known after the fact. Pre-issue Chicago traces: Council zoning reclassifications (1,487), ADU preapprovals (616). Plan Commission/ZBA agendas on chicago.gov were not reachable. | PARTIAL: stage timing only at issue |
| 3. TCEQ/RRC -> oil and gas equipment | Pending air permits and drilling permits from small operators | Chicago DOE/CDPH environmental permits (67,886) and EPA ECHO (4,845 Cook County air-program facilities) are open; Illinois EPA air permit applications are a search application only. Texas sources themselves: RRC bulk files are public but served through a JSF download client; TCEQ's air permit status page is a query app that timed out (HTTP 522). | PARTIAL |
| 4. New businesses -> buyers | Florida Sunbiz free daily/quarterly bulk files | Chicago Business Licenses full history (1.21 million terms, ISSUE vs RENEW vs C_LOC) is the strong equivalent and is free. Illinois Secretary of State entity data could not be reached from our client (403, even for robots.txt). IDFPR licenses (4.46 million) are open under ODbL. | VERIFIED (city), BLOCKED (state entities) |
| 5. Orlando roofs + appraiser + storms | Permit applications with review stages, parcel data, storm data | Cook County residential characteristics carry year built and roof construction (not roof age), Chicago permits carry prior re-roof history, and the signal lab already found no storm signal (H04/H05/H28). Orange County's appraiser site is a script-only app; Florida's state roll files are documented. | VERIFIED data, weak expected lift |

**Three findings that change plans**

1. **Chicago's biggest early-signal gap is real but partly fillable.** The permit dataset has 853,111 issued permits and no review-stage rows. The two earlier traces we can actually fetch are the Council eLMS API (zoning, about 1,500 matters in 11 years) and the business-license history. Everything else early (Plan Commission, ZBA, Department of Buildings pages) sits on chicago.gov, which refuses our client.
2. **Several useful hosts block this cloud client** (chicago.gov, ilsos.gov, api.usaspending.gov, transportation.gov pages). They were not worked around. The founder's own network may not be blocked; retest there before concluding anything about those sources.
3. **Two sources need a key or a human step:** SAM.gov (API key tied to an account) and Illinois SOS bulk data (availability unknown). Neither is worth it before the cheaper ones above.

### Ranked: ingest next for Chicago

1. **chicago-business-licenses-history**: Already in our warehouse as the current-active file only. The full history (1.21 million license terms since 2002-01-02) separates ISSUE (271,166) from RENEW (921,838) and change-of-location (C_LOC, 16,443) applications, with application-created and issue dates. That is the one free Chicago feed that shows a new business before it opens, and the food-license backtest (restaurant build-out about 90 days ahead of the license) shows the method works. Effort: small (same Socrata exporter, one new table). First test: ISSUE-type license -> renovation permit or sign permit at the address within 365 days vs the same address's own earlier window; split by business activity.
2. **chicago-clerk-elms**: Zoning reclassification ordinances (1,487 since 2015-07, address and zoning application number in the title) are filed in Council months before a permit exists. This is the only machine-readable pre-permit trail for large Chicago projects that was reachable; the City's Plan Commission and ZBA web pages were not reachable from our client. Effort: medium (parse addresses from titles, join to permits by address/PIN). First test: Reclassification introduced -> new-construction or renovation permit >= $100k at the address; measure lead time vs permit issue date.
3. **hfsrb-project-list + hfsrb-project-pages (engine/collect/hfsrb.py)**: The Chicago-area analog of the Georgia case: 1,692 projects listed 2011-2026, staff reports and permit approval letters carry project cost, facility, city, permit holders and a description that names equipment. Volume is small (about 100 projects a year statewide) but costs in the sample run from $0.25 million to $645 million; buyers would be medical-equipment sellers and healthcare GCs, which we have no customer for yet. Needs one PDF library if cost is wanted. Effort: small for the CSV (done); medium to productize PDF header extraction. First test: Approved permits -> subcontractor/equipment-related permits at the facility address in the following 2 years (join approval letters to Chicago permits by address).
4. **cook-procurement-buying-plan + cook-procurement-bids + cook-procurement-awards + chicago-contracts**: The only forward-looking public-work pipeline found in the data: Cook County's Buying Plan (planned solicitations), then bid tabulations (who bid, what price), then awards; Chicago contracts add 189,023 vendor contracts. Directly feeds Track 2 (GC open-door scores, subcontractor intelligence) and costs nothing. Effort: small (Socrata). First test: Buying-plan item -> posted bid -> award; check lead time and whether bidders are repeat winners (relationship graph).
5. **fmcsa-company-census**: 20,715 FMCSA-registered carriers with a Chicago physical address, with power units, drivers, add_date (new carriers) and MCS-150 update date. A clean, current B2B list for fleet-service sellers; a separate market from contractors, so rank depends on the founder's buyer choice. Effort: small. First test: New carriers (add_date in last 90 days) with power_units >= 5 as a weekly list; no backtest possible (no history).
6. **chicago-doe-environmental-permits + epa-echo-cook-air**: Chicago's own air-permit analog of TCEQ: 67,886 City environmental permits (29,805 'AIR POLLUTION CONTROL PERMIT') plus 4,845 active Cook County air-program facilities in EPA ECHO. Useful as an industrial-site master list and a trigger for boiler/generator/spray-booth service; the Illinois EPA permit application list itself is only a search application. Effort: small (both are APIs). First test: New air-pollution-control permit -> mechanical/electrical permit at the address; ECHO NAICS to find industrial prospects.
7. **il-idfpr-professional-licensing + idph directories + nppes-api**: Healthcare and professional new-practice detection: IDFPR licenses (4.46 million rows with original issue dates; ODbL licence needs attribution and share-alike for derived databases), IDPH hospital/ASTC/dialysis directories (207 hospitals, 156 ASTCs), and NPPES enumeration dates. Medium signal for build-out and equipment sellers; mostly individuals, so match by practice address only. Effort: medium (entity matching to addresses). First test: New organizational NPI or dental/medical license with a Chicago practice address -> build-out permit within 180 days.
8. **chicago-adu-preapproval**: 616 ADU preapproval applications since 2026-03-31, the only Chicago application-stage permit data found; too small and too new to backtest, but it is a real pre-permit feed for residential GCs and is trivial to ingest. Effort: small. First test: Pre-certified ADU application -> building permit at the address; wait for 12 months of history.

**Not worth ingesting for Chicago:** Seattle and Orlando permits (method references only: stage-duration modelling), Georgia DCH and Texas sources (wrong state), Orange County appraiser (no usable endpoint), SEC EDGAR (large companies only, though the API works with our User-Agent), Census BFS and CBP (state/county aggregates, useful only to normalize counts), job-posting APIs (no Chicago employer list), SAM.gov and USAspending (blocked by key and WAF respectively; federal work is a small share).

## Proof of concept: Illinois HFSRB projects (Chicago analog of Case 1)

**Result: yes, Illinois project data can be retrieved for Chicago-area projects, with cost and equipment text for most non-exempt projects.** `engine/collect/hfsrb.py` fetches it politely (User-Agent `BricklineResearchBot/0.1`, robots.txt checked, 1 request/second) into `data/raw/hfsrb/` and writes `data/hfsrb-projects.csv` (deterministic: two runs gave the same md5; sorted by project number).

Where each field comes from (all verified in this run):

| Field | Source | Structured? |
| --- | --- | --- |
| project number, project name, year, status (Exempted / Non-Exempted), deemed-complete flag | listing JSON (one request, 1,692 rows) | yes |
| received date, hearing-request and comment deadlines, board meeting date, document links | per-project HTML page | yes where the page is filled in (185 of 505 pages fetched had a received date) |
| project cost, facility, city, address, permit holders, description (equipment named in prose), completion date | first page of the State Board staff report or the permit approval letter (PDF) | text PDFs with a fixed header; needs a PDF library (`pypdf`, not a project dependency; the collector skips this step if it is missing) |
| application contents | scanned application PDF | no (image-only on the sample) |

Counts from the run `--since 2022 --documents` (pages for 2022-2026, 505 project pages, 405 PDFs):

- Listing: 1,692 projects, project years 2011-2026 (one 2010 entry): 86-154 projects a year in 2012-2026 (2026 so far: 99); 233 names mention Chicago; 1,652 have a project number (the other 40 are mostly temporary-suspension notices).
- Page-level (505 project pages, 2022-2026): 445 application links, 182 staff-report links, 350 approval-letter links.
- Document-level (2022-2026): 195 projects with a project cost, 190 with a city, 198 with a description, 153 with permit holders, 36 with an equipment keyword (dialysis 19, cath lab 7, operating rooms 5, linear accelerator 3, MRI 2, CT 2). 193 of 244 non-exempt 2022-2026 projects (79%) have a cost; exemption (E-) approval letters carry no cost, so only 2 of 221 exemption projects do.
- Chicago-city projects with documents 2022-2026: 37 (27 with a non-zero cost, $2.95 billion in total); 17 of them are 2025 or later.
- How far back: the listing reaches 2011; project pages with application, staff report and approval letter links were seen for 2012, 2014, 2016, 2018, 2020 and 2022 projects; a 2015 staff report has the same header block as a 2026 one (checked on 14-061). PDFs were only bulk-read for 2022 onward.

Ten sample rows (Chicago city, 2025 or later, non-zero cost; from `data/hfsrb-projects.csv`):

| Project | Facility | Cost | Completion | Source doc | Equipment keywords |
| --- | --- | --- | --- | --- | --- |
| 25-003 | Advocate Trinity Hospital | $319,557,882 | n/a | staff report | none |
| 25-009 | TARGET Health Cooperative Medical Clinics | $34,190,180 | n/a | staff report | none |
| 25-017 | Shirley Ryan AbilityLab | $21,284,207 | n/a | staff report | none |
| 25-019 | Six Corners Same Day Surgery Center | $5,205,709 | July 1, 2026 | approval letter | none |
| 25-025 | Northwestern Memorial Hospital (master design) | $56,242,369 | September 30, 2027 | approval letter | none |
| 25-030 | Northwestern Memorial Hospital | $95,507,133 | n/a | approval letter | dialysis |
| 25-042 | University of Illinois Medical Center (ambulatory care building) | $208,455,373 | January 31, 2026 | approval letter | none |
| 25-050 | Mount Sinai Hospital Medical Center of Chicago | $250,000 | December 31, 2026 | approval letter | none |
| 26-003 | Northwestern Memorial Hospital (demolition) | $51,283,483 | July 31, 2026 | approval letter | none |
| 26-005 | Northwestern Memorial Hospital (surgical services) | $264,935,160 | June 30, 2028 | approval letter | none |

**Extraction accuracy (hand check against the source documents).** Two checks of 10 rows each. (1) Ten Chicago-city rows (every second or third of 23 candidates), read against the PDF first pages: cost, facility, city, description and completion date matched on 10 of 10 once the two blank cities were fixed; those two had a blank city because the approval-letter layout says 'Applicants:' instead of 'Permit Holders:' (fixed afterwards). (2) Every 38th document row of the final CSV: on the 6 non-exempt rows, cost, facility and completion date matched 6 of 6, city matched 5 of 6 (O'Fallon was read as 'Illinois' because of the curly apostrophe; fixed and re-run), and the 4 exemption rows returned blanks, which is correct because their letters hold no cost. Dates read from project pages were compared on 5 rows (received date 4 of 4 where present, meeting date 1 of 1). One source-side error was found by cross-checking: the HFSRB page for 23-023 (Rush North and Harlem MOB) links the permit letter of 22-023 (Lurie iMRI, $27,741,365). The collector now compares the project number inside each PDF with the row and leaves the fields blank on a mismatch (4 of the 389 rows with a document were mismatches). The equipment flags are keyword hits on the description, not a validated classification, and a $0 permit amount means a discontinuation, not a free project.

**Caveats.** (a) Illinois only reviews projects above statutory thresholds (the 26-032 staff report states a FY2026 capital expenditure minimum of $4,779,437 for major medical equipment), so most routine MRI/CT purchases never appear. (b) Names in the listing contain typos ('26-0321', 'Washington Lag'), and the project number from the link is used when the two disagree. (c) Pages for the newest projects are often blank for dates until staff fill them in. (d) 'name_mentions_chicago' is a name match; the city from the PDF (`doc_city`) is more reliable and covers only projects with documents.

## Quick feasibility: Georgia DCH weekly CON report

Verified. The page lists one PDF per week (`/document/report/11-10-2026-tracking-report/download`, 710,843 bytes, 32 pages, report period 2026-11-04 to 2026-11-10, file last modified 2026-11-12). With `pypdf` the text extracts cleanly in a regular layout: 2 letters of intent (each with received date and 'application must be submitted on' date) and 18 distinct application IDs across sections (applicant, service or project type, filed, deemed-complete and decision-deadline dates, site with county, contact name and phone; 9 'Estimated Cost' lines totalling $149.3 million). The current report has 5 pending-review applications, including MegaVoltage radiation therapy establishments and expansions ($13.87 and $6.99 million among them), none recently approved, and two recently denied 'Replacement of (Existing) MRI and CT Scanner(s)' applications ($3.9 million, denied 2026-10-23, opposition filed): exactly the equipment-demand signal described in the brief. Limits: only the current week is linked (the Wayback Machine CDX index returned no captures for the URL pattern), so history needs our own weekly archive; no API or CSV; no terms or reuse language was found on the pages read.

## Chicago stage fields for Case 2 (what the existing permit dataset can and cannot say)

`ydr8-5enu` has `application_start_date` (newest 2026-11-15) and `issue_date` (newest 2026-11-15), `processing_time`, `permit_status` and `permit_milestone`. Status values (counts): COMPLETE 487,036, ACTIVE 31,200, EXPIRED 16,877, SUSPENDED 13,248, PHASED PERMITTING 975, CANCELLED 401, REVOKED 292, null 303,082; milestones are post-issue (INSPECTIONS, CERTIFICATE OF OCCUPANCY ISSUED, INSPECTION ELIGIBLE, 'PERMIT ISSUED (FEE DUE)' 672). There are no in-review values, so Chicago does not publish applications before issue in this dataset; Seattle's equivalent (`76t5-zqzr`) has 12+ in-progress statuses (Additional Info Requested 10,336, Reviews In Process 562, Ready for Issuance 697) plus initial-review, plan-review-complete and ready-to-issue dates, and Orlando's (`ryhf-m453`) has under-review and pending-issuance dates. The nearest Chicago traces are the Council zoning reclassification API (1,487 matters since 2015-07) and ADU preapproval applications (616 since 2026-03-31).

## Catalog (one entry per source)

### `hfsrb-project-list`: Illinois HFSRB project search listing (CON + exemption projects)

- **Verdict: VERIFIED.** JSON listing retrieved with every project; contains no cost, equipment, applicant or dates.
- Official URL: https://hfsrb.illinois.gov/project/project-search.html
- Access method: HTML page backed by a public JSON model endpoint (the page's own data feed). Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 200; 1,692 sample rows/records retrieved; dataset total 1,692.
- Sample fields (5): `projectName`, `projectYear`, `projectStatus`, `projectDeemedComplete`, `meta.dynamicPageLink`
- Probe details: `{"by_status": {"Exempted": 769, "Non-Exempted": 870, "none": 53}, "by_year": {"2010": 1, "2011": 15, "2012": 112, "2013": 101, "2014": 119, "2015": 97, "2016": 128, "2017": 154, "2018": 121, "2019": 119, "2020": 118, "2021": 100, "2022": 137, "2023": 97, "2024": 86, "2025": 86, "2026": 99, "none": 2}, "first_by_name": ["12-002 - Rehabilitation Institute of Chicago, Chicago", "12-003 - Holy Family Villa, Palos Park"], "names_mentioning_chicago": 233, "note": "listing has no dates, costs, applicants or equipment; each project has a detail page with dates and PDFs"}`
- Coverage: Illinois-wide; project years 2011-2026 in the listing; Chicago-area projects identified only by name/city text. Update frequency: Whenever staff publish a project (the listing changed 2026-08-19 per its modifyDate).
- Terms: https://hfsrb.illinois.gov/robots.txt (robots.txt allows all paths for generic agents; no terms-of-use page for the data was found on the site (state-wide footer links only privacy/accessibility).)
- Ingestion effort: small. Lead uses: Weekly diff of new CON/exemption projects (project number, facility name, city); anchor for the PDF documents. Signal quality: Medium as a list (names only); high once joined to the project pages and PDFs.

### `hfsrb-project-pages`: Illinois HFSRB per-project pages (dates, status, document links)

- **Verdict: PARTIAL.** Pages and document links fetched; cost/equipment/applicant live only inside the linked PDFs.
- Official URL: https://hfsrb.illinois.gov/project.26-032-advanced-radiation-center-of-chicago.html
- Access method: HTML (server-rendered), one page per project. Auth or key: none. Cost: free.
- Probe: 5 request(s), HTTP status 200, 200, 200, 200, 200; 5 sample rows/records retrieved.
- Sample fields (7): `meetingDateForConsideration`, `pageContent`, `projectName`, `projectReceivedDate`, `projectRequestPublicHearingDate`, `projectWrittenCommentDate`, `title`
- Probe details: `{"pages_with_documents": 5}`
- Coverage: Same project set as the listing; dates are blank on some older or newer pages. Update frequency: As projects move through review.
- Terms: https://hfsrb.illinois.gov/robots.txt (Same as listing; terms not found.)
- Ingestion effort: medium. Lead uses: Received date, hearing/comment deadlines, board meeting date, and links to application, completeness letter, staff report, permit approval letter, progress reports. Signal quality: High: stage-by-stage dates (when populated) and the document trail.

### `hfsrb-pdf-documents`: Illinois HFSRB PDFs: State Board staff reports and permit approval letters

- **Verdict: PARTIAL.** First pages of staff reports and approval letters are text PDFs with a fixed header block; applications are image-only; no PDF library is a project dependency.
- Official URL: https://hfsrb.illinois.gov/project.26-032-advanced-radiation-center-of-chicago.html
- Access method: PDF documents linked from each project page (applications are scanned images). Auth or key: none. Cost: free.
- Probe: 10 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved.
- Sample fields (8): `project_no`, `cost`, `facility`, `city`, `board_meeting`, `permit_holders`, `description`, `completion`
- Probe details: `{"pdf_text_library_available": true}`
- Coverage: Staff reports exist for projects that reached a board meeting; approval letters for approved permits; application PDFs look like scanned images (the one application sampled by hand during exploration, 26-032, had 168 pages and no extractable text on pages 1-3; not part of the automated probe). The 26-032 staff report states the FY2026 Capital Expenditure Minimum for major medical equipment: $4,779,437. Update frequency: Per board meeting (monthly-ish) and per approval.
- Terms: https://hfsrb.illinois.gov/robots.txt (Same as listing; terms not found.)
- Ingestion effort: large. Lead uses: Project cost, applicant, facility address, project description (equipment named in prose), completion date: the supplier-facing facts. Signal quality: Highest content value (cost + equipment + dates), lowest structure.

### `ga-dch-con-tracking`: Georgia DCH Certificate of Need weekly tracking report (PDF)

- **Verdict: PARTIAL.** Current weekly PDF fetched and text-extracted (needs a PDF library); no history on the site.
- Official URL: https://dch.georgia.gov/divisionsoffices/office-health-planning/certificate-need-con/con-tracking-report
- Access method: Weekly PDF linked from one HTML page. Auth or key: none. Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 1 sample rows/records retrieved.
- Sample fields (10): `LOI id`, `application id`, `applicant`, `service/project type`, `filed`, `deemed complete`, `decision deadline`, `site (county)`, `contact + phone`, `estimated cost`
- Probe details: `{"file": "attachment; filename=\"11-10-2026 Tracking Report.pdf\"", "last_modified": "Thu, 12 Nov 2026 15:00:02 GMT", "pdf_text_library_available": true, "project_ids": {"applications": 18, "letters_of_intent": 2}, "records_with_contact": 11, "records_with_estimated_cost": 9, "records_with_site": 15, "report_links_on_page": ["/document/report/11-10-2026-tracking-report/download"], "report_period": "November 4, 2026 \u2013 November 10, 2026", "wayback_archived_report_urls": 0}`
- Coverage: Georgia statewide; the page holds only the current week's file; older weeks are not linked. Update frequency: Weekly (the 2026-11-10 file covers 2026-11-04 to 2026-11-10 and was posted by 2026-11-12).
- Terms: https://dch.georgia.gov/robots.txt (robots.txt does not disallow /document/ or this page; no data terms found. Contact names and phone numbers appear in the report (business contacts of applicants).)
- Ingestion effort: medium. Lead uses: Letters of intent (batching) and applications with service type, estimated cost, site and contact: a lead-time window for equipment sellers (length not measured; Georgia, not Chicago). Signal quality: High content, but Georgia only; history needs a self-built archive or the Wayback Machine.

### `cms-pos`: CMS Provider of Services file (QIES), latest quarter

- **Verdict: VERIFIED.** Illinois rows retrieved through the documented data API.
- Official URL: https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/provider-of-services-file-hospital-non-hospital-facilities
- Access method: data-api JSON + CSV download on data.cms.gov. Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 3 sample rows/records retrieved; dataset total 398.
- Sample fields (473): `ACPTBL_POC_SW`, `ACRDTN_EFCTV_DT`, `ACRDTN_EXPRTN_DT`, `ACRDTN_TYPE_CD`, `ACTVTY_OFSITE_RSDNT_SW`, `ACTVTY_ONST_NRSDNT_SW`, `ACTVTY_ONST_RSDNT_SW`, `ACTVTY_OTHR_OFSITE_RSDNT_SW`, `ACTVTY_OTHR_ONST_NRSDNT_SW`, `ACTVTY_OTHR_ONST_RSDNT_SW`, `ACTVTY_PROFNL_CNTRCT_CNT`, `ACTVTY_PROFNL_FLTM_CNT`, `ACTVTY_PROFNL_PRTM_CNT`, `ACTVTY_STF_OTHR_CNTRCT_CNT`, `ACTVTY_STF_OTHR_FLTM_CNT`, `ACTVTY_STF_OTHR_PRTM_CNT`, `ACUTE_RESP_CARE_CD`, `ACUTE_RNL_DLYS_SRVC_CD`, `AFLTD_PRVDR_CNT`, `AIDS_BED_CNT`, `ALCHL_DRUG_SRVC_CD`, `ALZHMR_BED_CNT`, `ANSTHSA_SRVC_CD`, `APLNC_EQUIP_SRVC_CD` ...
- Probe details: `{"dataset_rows_all_states": 13598, "field_count": 473, "note": "CT_SCAN_SRVC_CD and MGNTC_RSNC_IMG_SRVC_CD are service flags (MRI), CRDC_CTHRTZTN_PRCDR_ROOMS_CNT counts cath rooms"}`
- Coverage: National, one row per certified facility, ~470 fields incl. service flags (CT, MRI, cardiac cath, radiation therapy rooms, beds). Update frequency: Quarterly (latest 2026-07-01 file modified 2026-10-16).
- Terms: https://data.cms.gov/terms-of-use (Terms page is a JavaScript app (text not extractable by plain GET); data are federal. robots.txt sets Crawl-delay: 10 (honored).)
- Ingestion effort: small. Lead uses: Installed-base context for equipment sellers: which Illinois hospitals/ASCs report CT, MRI, cath labs, OR counts; ownership changes (CHOW). Signal quality: Medium: capability flags, not purchase events; useful for qualification and territory sizing.

### `cms-hospital-enrollments`: CMS Hospital Enrollments (PECOS) and Hospital All Owners, latest

- **Verdict: VERIFIED.** Illinois enrollment rows retrieved.
- Official URL: https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/hospital-enrollments
- Access method: data-api JSON + CSV on data.cms.gov. Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 3 sample rows/records retrieved; dataset total 318.
- Sample fields (39): `ADDRESS LINE 1`, `ADDRESS LINE 2`, `ASSOCIATE ID`, `CAH OR HOSPITAL CCN`, `CCN`, `CITY`, `DOING BUSINESS AS NAME`, `ENROLLMENT ID`, `ENROLLMENT STATE`, `INCORPORATION DATE`, `INCORPORATION STATE`, `LOCATION OTHER TYPE TEXT`, `MULTIPLE NPI FLAG`, `NPI`, `ORGANIZATION NAME`, `ORGANIZATION OTHER TYPE TEXT`, `ORGANIZATION TYPE STRUCTURE`, `PRACTICE LOCATION TYPE`, `PROPRIETARY NONPROFIT`, `PROVIDER TYPE CODE`, `PROVIDER TYPE TEXT`, `REH CONVERSION DATE`, `REH CONVERSION FLAG`, `STATE` ...
- Probe details: `{"dataset_rows_all_states": 9138, "field_count": 39, "note": "owners file is a separate dataset (029c119f-...)"}`
- Coverage: National; enrollment, practice location, organization names; the 'All Owners' companion lists owners (individuals and companies). Update frequency: Monthly (latest 2026-10-01).
- Terms: https://data.cms.gov/terms-of-use (Same as above (terms text not extractable; Crawl-delay 10).)
- Ingestion effort: small. Lead uses: Change of ownership and new-enrollment flags for hospitals; owner company names for B2B targeting. Signal quality: Low-medium for contractors; medium for healthcare-sales.

### `cms-hcris-hospital-cost-report`: CMS Hospital Provider Cost Report (HCRIS-derived), latest fiscal year

- **Verdict: VERIFIED.** Latest-year rows retrieved; Illinois filter used where the dataset exposes a state column.
- Official URL: https://data.cms.gov/provider-compliance/cost-report/hospital-provider-cost-report
- Access method: data-api JSON + CSV on data.cms.gov (one dataset per fiscal year). Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 3 sample rows/records retrieved; dataset total 205.
- Sample fields (117): `Accounts Payable`, `Accounts Receivable`, `Allowable DSH Percentage`, `Buildings`, `CCN Facility Type`, `Cash on Hand and in Banks`, `City`, `Combined Outpatient + Inpatient Total Charges`, `Contract Labor: Direct Patient Care`, `Cost To Charge Ratio`, `Cost of Charity Care`, `Cost of Uncompensated Care`, `County`, `DRG Amounts After October 1`, `DRG Amounts Before October 1`, `DRG Amounts Other Than Outlier Payments`, `Deferred Income`, `Depreciation Cost`, `Disproportionate Share Adjustment`, `FTE - Employees on Payroll`, `Fiscal Year Begin Date`, `Fiscal Year End Date`, `Fixed Equipment`, `General Fund Balance` ...
- Probe details: `{"dataset_rows_all_states": 6109, "field_count": 117, "note": "raw HCRIS worksheets are also on cms.gov (not probed)"}`
- Coverage: National, FY2011-FY2024 files (14 listed); one row per hospital cost report with beds, days, revenue and expense totals, capital cost lines. Update frequency: Annual (FY2024 file modified 2026-10-05).
- Terms: https://data.cms.gov/terms-of-use (Same as above.)
- Ingestion effort: medium. Lead uses: Capital spending trend and size of Illinois hospitals; identifies hospitals with rising capital cost lines before they file CON projects. Signal quality: Medium: 1-2 year lag, hospital-level aggregates only.

### `nppes-api`: NPPES NPI Registry API (v2.1)

- **Verdict: VERIFIED.** Chicago organizational NPIs returned.
- Official URL: https://npiregistry.cms.hhs.gov/api/
- Access method: REST JSON API. Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 200; 3 sample rows/records retrieved.
- Sample fields (22): `addresses`, `basic`, `created_epoch`, `endpoints`, `enumeration_type`, `identifiers`, `last_updated_epoch`, `number`, `other_names`, `practiceLocations`, `taxonomies`, `basic.authorized_official_first_name`, `basic.authorized_official_last_name`, `basic.authorized_official_name_prefix`, `basic.authorized_official_name_suffix`, `basic.authorized_official_telephone_number`, `basic.authorized_official_title_or_position`, `basic.enumeration_date`, `basic.last_updated`, `basic.organization_name`, `basic.organizational_subpart`, `basic.status`
- Probe details: `{"limits": "query used: state, city, organization type; paging limits not tested"}`
- Coverage: National, every NPI (organizations NPI-2 and individuals NPI-1) with taxonomy, addresses, phone, enumeration and last-update dates. Update frequency: Daily changes (API); monthly full file.
- Terms: https://npiregistry.cms.hhs.gov/api-page (Terms not found in the response; robots.txt has no rules. Result limits were not re-verified in this run.)
- Ingestion effort: small. Lead uses: New healthcare organizations (enumeration_date) in Chicago as a new-business signal; address and phone for outreach. Signal quality: Medium-high for healthcare B2B (new clinics register an NPI before they open); no cost or equipment data.

### `nppes-monthly-file`: NPPES monthly full file and weekly delta files

- **Verdict: VERIFIED.** Latest monthly ZIP exists and honors Range requests (only 200 bytes read).
- Official URL: https://download.cms.gov/nppes/NPI_Files.html
- Access method: Bulk ZIP (~1.1 GB monthly, weekly deltas, deactivation report). Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 206.
- Probe details: `{"file": "NPPES_Data_Dissemination_November_2026_V2.zip", "last_modified": "2026-11-03", "range_supported": true, "total_bytes": 1130479129}`
- Coverage: National, full history of enumerations. Update frequency: Monthly full file; weekly update file.
- Terms: https://download.cms.gov/nppes/NPI_Files.html (Page lists the files; no terms text found on the page.)
- Ingestion effort: medium. Lead uses: Bulk load for enumeration-date backtests (how long from NPI to first permit or license). Signal quality: Same as the API; better for backtests.

### `idph-hospital-directory`: Illinois IDPH Hospital Directory (Illinois open data portal)

- **Verdict: VERIFIED.** Rows retrieved via Socrata.
- Official URL: https://illinois-edp.data.socrata.com/d/53nt-jwqq
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 207; portal rows-updated 2026-11-13.
- Sample fields (9): `address`, `city`, `county`, `exp_date`, `facility_name`, `facility_type`, `license_number`, `phone`, `zip`
- Portal name: IDPH Hospital Directory
- Probe details: `{"column_count": 9}`
- Coverage: Illinois hospitals licensed by IDPH (address, license number, beds). Update frequency: Updated 2026-11-13 per portal.
- Terms: https://illinois-edp.data.socrata.com/api/views/53nt-jwqq.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Licensed facility master list to join with HFSRB project names and CMS POS. Signal quality: Medium: master data, not events.

### `idph-astc-directory`: Illinois IDPH Ambulatory Surgical Treatment Center Directory

- **Verdict: VERIFIED.** Rows retrieved via Socrata.
- Official URL: https://illinois-edp.data.socrata.com/d/79iq-26tb
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 156; portal rows-updated 2026-11-13.
- Sample fields (9): `address`, `city`, `contact_name`, `county`, `exp_date`, `facility_name`, `license_number`, `phone`, `zip`
- Portal name: IDPH Ambulatory Surgical Treatment Center Directory
- Probe details: `{"column_count": 9}`
- Coverage: Illinois ASTCs (licensed surgery centers). Update frequency: Updated 2026-11-13 per portal.
- Terms: https://illinois-edp.data.socrata.com/api/views/79iq-26tb.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Facility master list for surgery centers (a main buyer of equipment and buildouts). Signal quality: Medium: master data.

### `openfda-device-registration`: openFDA device registration and listing

- **Verdict: PARTIAL.** API works for makers and importers; it is not a demand-side registry.
- Official URL: https://open.fda.gov/apis/device/registrationlisting/
- Access method: REST JSON API. Auth or key: none (key optional, raises limits). Cost: free.
- Probe: 1 request(s), HTTP status 200; 1 sample rows/records retrieved; dataset total 10,409; newest record date 2026-11-02.
- Sample fields (6): `establishment_type`, `k_number`, `pma_number`, `products`, `proprietary_name`, `registration`
- Probe details: `{"note": "total = Illinois registration/listing rows (makers, importers, distributors)"}`
- Coverage: Registered device establishments (makers, importers); not hospitals' installed equipment. Update frequency: Weekly (last_updated 2026-11-02 in the response meta).
- Terms: https://open.fda.gov/terms/ (Terms page not fetched; the API response carries a 'do not rely on' disclaimer and says access may be restricted under its Terms of Service.)
- Ingestion effort: small. Lead uses: Prospect list of Illinois device makers/distributors (seller side), not demand signals from buyers. Signal quality: Low for Brickline's use cases: there is no public registry of installed MRI/CT units.

### `seattle-building-permits`: Seattle Building Permits (SDCI), issued and in progress

- **Verdict: VERIFIED.** Rows and stage fields retrieved.
- Official URL: https://data.seattle.gov/d/76t5-zqzr
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 9 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 194,311; newest record date 2026-11-13; earliest 1900-01-01; portal rows-updated 2026-11-15.
- Sample fields (26): `completeddate`, `contractorcompanyname`, `daysoutcorrections`, `dependentbuilding`, `description`, `estprojectcost`, `expiresdate`, `housingcategory`, `housingunits`, `issueddate`, `latitude`, `link`, `location1`, `longitude`, `numberreviewcycles`, `originaladdress1`, `originalcity`, `originalstate`, `originalzip`, `permitclass`, `permitclassmapped`, `permitnum`, `permittypedesc`, `permittypemapped` ...
- Portal name: Building Permits; license: Public Domain
- Probe details: `{"column_count": 41, "latest_by_field": {"issueddate": "2026-11-13", "planreviewcompletedate": "2026-11-12", "readytoissuedate": "2026-11-12"}, "top_statuscurrent": {"Additional Info Requested": 10336, "Application Completed": 715, "Canceled": 4580, "Closed": 8967, "Completed": 135072, "Corrections Required": 2159, "Expired": 13895, "Issued": 8204, "Ready for Issuance": 697, "Reviews In Process": 562, "Scheduled": 1882, "Withdrawn": 5256}}`
- Coverage: Seattle; includes permits applied for but not yet issued (earliest date in the data is a 1900-01-01 placeholder). Update frequency: Daily (rows updated 2026-11-15).
- Terms: https://data.seattle.gov/api/views/76t5-zqzr.json (Portal license field: Public Domain (from the dataset metadata).)
- Ingestion effort: small. Lead uses: Reference model for stage timing: applied, initial review complete, plan review complete, ready to issue, issued, completed; status shows where each application is. Signal quality: High as a method reference; not Chicago.

### `chicago-building-permits`: Chicago Building Permits (already ingested): stage fields

- **Verdict: VERIFIED.** Stage fields probed; issued permits only.
- Official URL: https://data.cityofchicago.org/d/ydr8-5enu
- Access method: Socrata API. Auth or key: none (app token recommended). Cost: free.
- Probe: 8 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 853,111; newest record date 2026-11-15; earliest 2006-01-03; portal rows-updated 2026-11-16.
- Sample fields (70): `application_start_date`, `building_fee_paid`, `building_fee_subtotal`, `building_fee_unpaid`, `building_fee_waived`, `census_tract`, `community_area`, `contact_1_city`, `contact_1_name`, `contact_1_state`, `contact_1_type`, `contact_1_zipcode`, `contact_2_city`, `contact_2_name`, `contact_2_state`, `contact_2_type`, `contact_2_zipcode`, `contact_3_city`, `contact_3_name`, `contact_3_state`, `contact_3_type`, `contact_3_zipcode`, `contact_4_city`, `contact_4_name` ...
- Portal name: Building Permits; license: See Terms of Use
- Probe details: `{"column_count": 123, "latest_by_field": {"application_start_date": "2026-11-15"}, "top_permit_milestone": {"CANCELLED": 340, "CERTIFICATE OF OCCUPANCY ISSUED": 11063, "CERTIFICATE OF OCCUPANCY PENDING (TEMPORARY OR PARTIAL OCCUPANCY APPROVED)": 1163, "COMPLETE": 475452, "EXPIRED": 282, "INSPECTION ELIGIBLE": 8414, "INSPECTIONS": 40340, "INSPECTIONS (CERTIFICATE OF OCCUPANCY REQUIRED)": 2694, "None": 303082, "PERMIT ISSUED (FEE DUE)": 672, "POST CONSTRUCTION FILING": 185, "SUSPENDED": 9069}, "top_permit_status": {"ACTIVE": 31200, "CANCELLED": 401, "COMPLETE": 487036, "EXPIRED": 16877, "None": 303082, "PHASED PERMITTING": 975, "REVOKED": 292, "SUSPENDED": 13248}}`
- Coverage: City of Chicago 2006-present. Update frequency: Daily.
- Terms: https://data.cityofchicago.org/api/views/ydr8-5enu.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small (done). Lead uses: application_start_date and issue_date give processing time; permit_status/milestone show only issued-stage values (see probe). Signal quality: High for relationships and timing; no pre-issue stage.

### `chicago-adu-preapproval`: Chicago Additional Dwelling Unit (ADU) preapproval applications

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://data.cityofchicago.org/d/j4h8-ug9m
- Access method: Socrata API. Auth or key: none. Cost: free.
- Probe: 6 request(s), HTTP status 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 616; newest record date 2026-11-13; earliest 2026-03-31; portal rows-updated 2026-11-14.
- Sample fields (43): `acknowledge_no_shared`, `acknowledge_will_require_affordable_adus`, `address`, `adu_applying_for`, `affidavit_yn`, `alderman`, `applicant_address`, `applicant_city`, `applicant_first_name`, `applicant_last_name`, `applicant_state`, `applicant_unit`, `applicant_zip`, `coach_house`, `conversion_unit`, `dwelling_units_in_lot`, `has_one_applied_previously`, `id`, `labor_requirement`, `latitude`, `location`, `longitude`, `max_number_coach_house_units_allowed`, `max_number_of_adu_allowed` ...
- Portal name: Additional Dwelling Unit Preapproval Applications; license: See Terms of Use
- Probe details: `{"column_count": 46, "top_status": {"Canceled": 17, "Denied": 5, "In Review": 1, "Pre-Certified": 563, "Pre-Certified: admin adjust": 13, "Request Additional Docs": 1, "Resubmitted": 2, "Submitted": 8, "Upload affordability receipt": 3, "Upload missing information": 3}}`
- Coverage: City of Chicago; preapproval step before a building permit for coach houses and basement/attic units; rows start 2026-03-31. Update frequency: Daily.
- Terms: https://data.cityofchicago.org/api/views/j4h8-ug9m.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small. Lead uses: One of the few Chicago datasets that shows an application before a permit: owner address, unit type, max units allowed, status. Signal quality: Medium: small volume (hundreds) and owner-applicant data (names not stored here).

### `chicago-doe-environmental-permits`: Chicago Department of Environment / CDPH environmental permits (air quality, demolition, etc.)

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://data.cityofchicago.org/d/ir7v-8mc8
- Access method: Socrata API. Auth or key: none. Cost: free.
- Probe: 7 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 67,886; newest record date 2026-11-13; earliest 1990-05-21; portal rows-updated 2026-11-16.
- Sample fields (16): `address`, `applicant`, `application_id`, `application_name`, `application_subtype`, `application_type`, `comment`, `data_source`, `direction`, `latitude`, `location`, `longitude`, `status`, `street_name`, `street_number_from`, `street_type`
- Portal name: DOE Environmental Permits; license: See Terms of Use
- Probe details: `{"column_count": 24, "top_application_type": {"ABOVEGROUND STORAGE TANK": 1261, "AIR POLLUTION CONTROL PERMIT": 29805, "DOE AST Installation": 677, "DOE Above Ground Storage Tanks": 144, "DOE Air Quality": 22463, "DOE Recycling Facility": 264, "DOE UST Abandon": 140, "DOE UST Green Decal": 814, "DOE UST Reline": 161, "DOE UST Removal": 1011, "DOE UST Upgrade": 575, "UNDERGROUND STORAGE TANK": 10229}, "top_status": {"CLOSED": 40939, "Closed": 20631, "Deleted": 1, "OPEN": 356, "Open": 5912, "STOP WORK": 20, "Stop Work": 27}}`
- Coverage: City of Chicago; DOE before 2012 and after April 2026, CDPH between. Update frequency: Daily.
- Terms: https://data.cityofchicago.org/api/views/ir7v-8mc8.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small. Lead uses: City-level air-permit analog: permits for air-quality-sensitive work (architectural surface, demolition, boilers) with applicant names; note hold/expiry dates. Signal quality: Medium: narrow permit types; useful as a precursor for demolition and facade work.

### `chicago-clerk-elms`: Chicago City Clerk eLMS API (ordinances: zoning reclassifications, Planned Developments, committee referrals)

- **Verdict: VERIFIED.** Zoning reclassification ordinances retrieved with addresses, status and dates; Planned Development ordinances are not separately tagged.
- Official URL: https://api.chicityclerkelms.chicago.gov/
- Access method: REST JSON API (Swagger UI at the root). Auth or key: none. Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 100 sample rows/records retrieved; dataset total 1,487; newest record date 2026-12-08.
- Sample fields (35): `actions`, `agreedCalendar`, `attachments`, `committeReferral`, `controllingBody`, `controllingBodyId`, `economicDisclosure`, `fileYear`, `filingOffice`, `filingSponsor`, `filingSponsorId`, `finalActionDate`, `introductionDate`, `introductionType`, `keyLegislation`, `lastPublicationDate`, `legacyRecordNumber`, `legacyStatus`, `matterCategory`, `matterId`, `nicknameAlias`, `originalRecordNumber`, `recordCreateDate`, `recordNumber` ...
- Probe details: `{"earliest_introduced": "2015-07-29", "free_text_search_planned_development_matches": 1983, "note": "introduction dates can be future council-meeting dates; the free-text search matches any text, so Planned Development ordinances are not isolated by it", "planned_development_in_newest_100_titles": 0, "query": "matterCategory = ZONING RECLASSIFICATIONS (Zoning Reclassification Map No. at <address> - App No. <zoning application number>)"}`
- Coverage: City Council legislative matters; zoning reclassification ordinances from 2015-07 (about 1,500 in the system), each with actions, sponsors, attachments. Update frequency: Live (introduced matters appear within days).
- Terms: https://api.chicityclerkelms.chicago.gov/ (No terms found on the API root page (Swagger UI only).)
- Ingestion effort: medium. Lead uses: Zoning reclassification ordinances (title carries the street address and zoning application number) are filed months before a building permit: the earliest public trace of rezoned or Planned Development projects; applicant and plans sit in attachments. Signal quality: High potential for Track 2 (pre-application projects); about 1,500 matters in 11 years, so few but large; needs address parsing of titles.

### `chicago-dob-performance-metrics`: Chicago DOB 'Time to Issue' performance-metric datasets

- **Verdict: VERIFIED.** Dataset exists but is stale and aggregate; confirms Chicago publishes no in-review applications.
- Official URL: https://data.cityofchicago.org/d/4ygs-9x34
- Access method: Socrata API. Auth or key: none. Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 166; portal rows-updated 2014-08-04.
- Sample fields (4): `average_days_to_permit`, `target`, `week`, `week_text`
- Portal name: Performance Metrics - Buildings - Time to Issue Standard Plan Review Program Permits
- Probe details: `{"column_count": 4}`
- Coverage: Aggregate turnaround by permit program; the portal shows last update in 2014. Update frequency: Stale.
- Terms: https://data.cityofchicago.org/api/views/4ygs-9x34.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small. Lead uses: None: aggregates, no application records. Signal quality: Low

### `chicago-gov-planning-pages`: chicago.gov pages: Plan Commission, Zoning Board of Appeals agendas, Dept. of Buildings permit pages

- **Verdict: BLOCKED.** chicago.gov denies this client at the CDN (403 including robots.txt); not worked around. Retry from another network or ask the City for an access exception.
- Official URL: https://www.chicago.gov/city/en/depts/dcd/supp_info/chicago_plan_commission.html
- Access method: Web pages and PDF agendas on chicago.gov. Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status None.
- Probe errors: skipped: robots.txt 403: treated as no-crawl (not bypassed)
- Probe details: `{"expected_patterns_found": {"plan commission": false}}`
- Coverage: Plan Commission, ZBA and Community Development Commission agendas (Chicago). Update frequency: Per meeting.
- Terms: https://www.chicago.gov/robots.txt (Not read: chicago.gov answered 403 to our client for robots.txt and pages, so everything on the host was treated as no-crawl.)
- Ingestion effort: large. Lead uses: Pre-permit agenda items (large developments, Planned Developments, variances) if the agendas could be fetched; the Council eLMS API above is the machine-readable route. Signal quality: Unknown: not assessable from this client.

### `tceq-central-registry`: TCEQ Central Registry files on data.texas.gov (Dallas / Fort Worth)

- **Verdict: VERIFIED.** Rows retrieved via Socrata.
- Official URL: https://data.texas.gov/d/t34q-qzi3
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 671,878; portal rows-updated 2026-11-16.
- Sample fields (29): `additional_id_status`, `additional_id_text`, `affil_begin_dt`, `affil_end_dt`, `ai_phys_loc_addr_line_1`, `ai_phys_loc_addr_state`, `ai_phys_loc_addr_zip_full`, `ai_phys_loc_city`, `ai_phys_loc_desc`, `indus_type_cd_name`, `name_txt`, `princ_legal_name`, `princ_name`, `princ_status_txt`, `program_code`, `re_phys_loc_addr_county`, `re_phys_loc_addr_line_1`, `re_phys_loc_addr_state`, `re_phys_loc_addr_zip`, `re_phys_loc_addr_zip_ext`, `re_phys_loc_city`, `re_phys_loc_desc`, `ref_num_txt`, `ref_num_txt_1` ...
- Portal name: Texas Commission on Environmental Quality - Central Registry Files - Dallas / Fort Worth
- Probe details: `{"column_count": 35}`
- Coverage: Regulated entities and their program IDs (air, water, waste) by TCEQ region. Update frequency: Updated 2026-11-16 per portal.
- Terms: https://data.texas.gov/api/views/t34q-qzi3.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Master list of Texas regulated sites; air permits themselves are not in this dataset. Signal quality: Medium for Texas; not Chicago.

### `tceq-air-permit-status`: TCEQ air permit status query (New Source Review, PBR, Title V)

- **Verdict: PARTIAL.** Documentation and query form are public, but the origin returned Cloudflare 522 (connection timed out) on every attempt in this session (four, spread over about an hour).
- Official URL: https://www2.tceq.texas.gov/airperm/index.cfm
- Access method: Web query application (no bulk download or API found). Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 522.
- Probe details: `{"content-length": "7260", "expected_patterns_found": {"air|permit": false}, "title": "tceq.texas.gov | 522: Connection timed out"}`
- Coverage: Texas NSR and federal operating permits and applications, pending and completed. Update frequency: Not stated.
- Terms: https://www.tceq.texas.gov/permitting/air/nav/air_status_permits.html (Terms not found; the TCEQ download page lists raw datasets for air emissions inventories but no NSR permit file.)
- Ingestion effort: large. Lead uses: Pending NSR applications from small operators are the Texas analog of CON: months of lead time before equipment purchase. Signal quality: High content; query-only access means scraping a form, which is not done here.

### `rrc-data-downloads`: Texas Railroad Commission data sets available for download (drilling permits, production)

- **Verdict: PARTIAL.** Page and share links verified; actual downloads go through a JSF web client and were not automated.
- Official URL: https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/
- Access method: Bulk files (ASCII/CSV/PDF) via anonymous managed-file-transfer share pages. Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 64 sample rows/records retrieved.
- Probe details: `{"first_link_prefix": "4e31c695", "mft_listing_probe": {"looks_like_file_listing": true, "needs_login": false, "status": 200}, "note": "downloads are served by a JSF web client (GoDrive) share page; not automated here"}`
- Coverage: Texas; drilling permit master since 1976, pending permits twice daily, production, wellbore. Update frequency: Nightly to monthly by file.
- Terms: https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/ (No terms text found on the page.)
- Ingestion effort: medium. Lead uses: Drilling permit applications by operator (W-1) are the Texas oil-and-gas lead event; small operators identified by operator number. Signal quality: High for oil and gas suppliers; irrelevant to Chicago.

### `rrc-well-bottom-location`: RRC well bottom location (data.texas.gov)

- **Verdict: VERIFIED.** Rows retrieved via Socrata.
- Official URL: https://data.texas.gov/d/uumf-5r4y
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 1,397,402; portal rows-updated 2026-11-16.
- Sample fields (5): `api`, `gis_lat27`, `gis_lat83`, `gis_long27`, `gis_long83`
- Portal name: RRC-Well Bottom Location
- Probe details: `{"column_count": 5}`
- Coverage: Texas wells (API number, coordinates). Update frequency: Updated 2026-11-16 per portal.
- Terms: https://data.texas.gov/api/views/uumf-5r4y.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Well locations; the drilling permit dataset itself was not found on data.texas.gov. Signal quality: Low-medium.

### `il-epa-air-permits`: Illinois EPA Bureau of Air permit applications and Document Explorer

- **Verdict: PARTIAL.** Pages reachable; no bulk file or API found, only a search application.
- Official URL: https://epa.illinois.gov/topics/air-quality/permits.html
- Access method: Web pages and a document-search web application. Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 0 sample rows/records retrieved.
- Probe details: `{"note": "search web applications only; no bulk or API endpoint was found on these pages"}`
- Coverage: Illinois air construction/operating permits. Update frequency: Not stated.
- Terms: https://epa.illinois.gov/ (Terms not found.)
- Ingestion effort: large. Lead uses: Illinois analog of TCEQ NSR: permit application receipts for new emission sources (boilers, generators, paint booths). Signal quality: Medium-high if the application list can be obtained without form scraping.

### `epa-echo-cook-air`: EPA ECHO facility search REST services (Cook County air-program facilities)

- **Verdict: VERIFIED.** Facility rows retrieved.
- Official URL: https://echo.epa.gov/tools/web-services
- Access method: REST JSON API and bulk downloads. Auth or key: none. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 5 sample rows/records retrieved; dataset total 4,845.
- Sample fields (9): `FacCity`, `FacDerivedReservationTribes`, `FacEPARegion`, `FacIndianCntryFlg`, `FacName`, `FacState`, `FacZip`, `NPDESIDs`, `RegistryID`
- Probe details: `{"note": "the get_qid page returns about 1 MB even with pagesize=5 (ignored by the service); only 5 rows are kept here; the get_facilities summary also reports inspection and violation counts", "query": "Cook County IL, active facilities with an air (CAA) program ID", "summary_counts": {"CVRows": "145", "FEARows": "155", "INSPRows": "452", "QueryRows": "4845", "TotalPenalties": "$40,863,175"}}`
- Coverage: National facilities; here Cook County IL active facilities with a Clean Air Act program ID. Update frequency: Facility ID weekly; compliance data refreshed regularly.
- Terms: https://echo.epa.gov/resources/echo-data/about-the-data (ECHO is a federal compliance database; the about page was reachable; no explicit reuse terms matched.)
- Ingestion effort: small. Lead uses: Inventory of permitted industrial sources with NAICS, inspections and violations; targets for environmental and equipment services. Signal quality: Medium: current state only, but strong for B2B prospecting of industrial sites.

### `fl-sunbiz-bulk`: Florida Division of Corporations (Sunbiz) data downloads

- **Verdict: PARTIAL.** Documentation verified; the SFTP site was not connected to (no SSH client in the standard library).
- Official URL: https://dos.fl.gov/sunbiz/other-services/data-downloads/
- Access method: Daily and quarterly bulk files via SFTP (credentials published on the agency page) or browser. Auth or key: published public login on the agency's own page. Cost: free.
- Probe: 1 request(s), HTTP status 200.
- Probe details: `{"expected_patterns_found": {"Daily files": true, "Quarterly files": true}, "title": "Data Downloads - Division of Corporations - Florida Department of State"}`
- Coverage: Florida corporations, LLCs, partnerships, fictitious names; quarterly snapshots plus daily filings. Update frequency: Daily and quarterly.
- Terms: https://dos.fl.gov/sunbiz/other-services/data-downloads/ (Page says: free downloads 'for informational purposes', offered as is, may change. No other terms found. The dos.sunbiz.org copy of the page is disallowed for crawlers by robots.txt and was not fetched.)
- Ingestion effort: medium. Lead uses: New-entity detection by filing date (file layout not inspected here). Signal quality: High for Florida; shows the model Chicago lacks (free bulk daily new-entity feed).

### `il-sos-business-entities`: Illinois Secretary of State business entity search and bulk data

- **Verdict: BLOCKED.** Access denied from this client (CDN block, including robots.txt); not worked around. Bulk availability and price must be confirmed with the Secretary of State by hand.
- Official URL: https://apps.ilsos.gov/corporatellc/
- Access method: Web search application (blocked to our client); whether bulk data exists could not be checked. Auth or key: none for search; bulk unknown. Cost: unknown (not verified).
- Probe: 1 request(s), HTTP status None.
- Probe errors: skipped: robots.txt 403: treated as no-crawl (not bypassed)
- Probe details: `{"expected_patterns_found": {"corporation|llc": false}}`
- Coverage: Illinois entities (corporations, LLCs, LPs). Update frequency: Live search; bulk file cadence not verified.
- Terms: https://www.ilsos.gov/ (Not read: the host returned 403 'Access Denied' to our client, including for robots.txt.)
- Ingestion effort: large. Lead uses: New Illinois entities by file date; registered agents. Signal quality: High if obtainable; not obtainable here.

### `chicago-business-licenses-history`: Chicago Business Licenses (full history; application type, dates, activity)

- **Verdict: VERIFIED.** Full-history dataset retrieved with application types and dates.
- Official URL: https://data.cityofchicago.org/d/r5kz-chrr
- Access method: Socrata API. Auth or key: none (app token recommended). Cost: free.
- Probe: 8 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 1,211,708; newest record date 2026-11-13; earliest 2002-01-02; portal rows-updated 2026-11-16.
- Sample fields (36): `account_number`, `address`, `application_created_date`, `application_requirements_complete`, `application_type`, `business_activity`, `business_activity_id`, `city`, `community_area`, `community_area_name`, `conditional_approval`, `date_issued`, `doing_business_as_name`, `expiration_date`, `id`, `latitude`, `legal_name`, `license_approved_for_issuance`, `license_code`, `license_description`, `license_id`, `license_number`, `license_start_date`, `license_status` ...
- Portal name: Business Licenses; license: See Terms of Use
- Probe details: `{"column_count": 42, "latest_by_field": {"application_created_date": "2026-11-13"}, "top_application_type": {"C_CAPA": 519, "C_EXPA": 942, "C_LOC": 16443, "C_SBA": 800, "ISSUE": 271166, "RENEW": 921838}, "top_license_status": {"AAC": 79139, "AAI": 1131084, "INQ": 1, "REA": 13, "REV": 1471}}`
- Coverage: City of Chicago; all license types, one row per license term. Update frequency: Daily.
- Terms: https://data.cityofchicago.org/api/views/r5kz-chrr.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small. Lead uses: ISSUE vs RENEW vs C_LOC (change of location) application types separate new businesses from renewals; account numbers link terms; address + activity + dates. Signal quality: High: richest Chicago new-business feed; already partly ingested as current-active only.

### `il-idfpr-professional-licensing`: Illinois IDFPR Professional Licensing (Illinois open data portal)

- **Verdict: VERIFIED.** Rows retrieved; personal fields redacted in the catalog.
- Official URL: https://illinois-edp.data.socrata.com/d/pzzh-kp68
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 8 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 4,462,647; newest record date 2025-12-31; earliest 1948-01-01; portal rows-updated 2026-11-16.
- Sample fields (22): `business`, `business_name`, `businessdba`, `city`, `controlled_substance_schedule`, `county`, `description`, `effective_date`, `ever_disciplined`, `expiration_date`, `first_name`, `last_name`, `lastmodifieddate`, `license_number`, `license_status`, `license_type`, `middle`, `prefix`, `state`, `suffix`, `title`, `zip`
- Portal name: Professional Licensing; license: Open Data Commons Open Database License; terms link: http://opendatacommons.org/licenses/odbl/1.0/
- Probe details: `{"column_count": 30, "latest_by_field": {"lastmodifieddate": "2025-12-31"}, "top_license_status": {"ACTIVE": 1419715, "CANCELLED": 159681, "CHANGE OF OWNERSHIP": 8989, "CLOSED": 21656, "DECEASED": 44275, "EXPIRED": 230746, "INACTIVE": 345132, "NOT RENEWED": 2089657, "REFUSE TO RENEW": 18754, "SUSPENDED": 16298, "TERMINATED": 37615, "TERMINATED CARD RETURNED": 43609}, "top_license_type": {"ADV PRACTICE NURSE": 194717, "COSMO": 484665, "DENTAL": 124540, "DETECTIVE BOARD": 714472, "MEDICAL BOARD": 403237, "NURSING BOARD": 645373, "PHARMACY": 367937, "PROF. COUNSELOR": 43690, "PROF. ENGINEER": 102792, "PUBLIC ACCOUNTANT": 98402, "REAL ESTATE": 638519, "SOCIAL WORKER": 70890}}`
- Coverage: Illinois professional licenses (individuals and some facilities). Update frequency: Updated 2026-11-16 per portal.
- Terms: https://illinois-edp.data.socrata.com/api/views/pzzh-kp68.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Original issue dates for licensed professions (e.g. dental, medical, contractors licensed by IDFPR); new-practice signal. Signal quality: Medium: mostly individuals; practice address often missing.

### `census-bfs`: Census Business Formation Statistics (BFS) monthly CSV

- **Verdict: VERIFIED.** CSV retrieved; Illinois present, no county or metro rows.
- Official URL: https://www.census.gov/econ/bfs/index.html
- Access method: Bulk CSV (state and national, monthly). Auth or key: none for the CSV. Cost: free.
- Probe: 1 request(s), HTTP status 200; 37,345 sample rows/records retrieved; newest record date 2026-10.
- Sample fields (17): `sa`, `naics_sector`, `series`, `geo`, `year`, `jan`, `feb`, `mar`, `apr`, `may`, `jun`, `jul`, `aug`, `sep`, `oct`, `nov`, `dec`
- Probe details: `{"file_truncated_at_cap": false, "geographies_in_file": 57, "has_county_or_metro": false, "has_il": true, "series": ["BA_BA", "BA_CBA", "BA_HBA", "BA_WBA", "BF_BF4Q", "BF_BF8Q", "BF_DUR4Q", "BF_DUR8Q", "BF_PBF4Q", "BF_PBF8Q", "BF_SBF4Q", "BF_SBF8Q"]}`
- Coverage: US and states (not metros or counties); business applications, high-propensity applications, formations by NAICS sector. Update frequency: Monthly (newest month in the file: 2026-10 on 2026-11-16).
- Terms: https://www.census.gov/data/developers/about/terms-of-service.html (API terms page read: attribution notice required for services using the API; no endorsement claims. The bulk CSV is not the API.)
- Ingestion effort: small. Lead uses: Macro baseline for 'new business' counts; does not identify individual businesses. Signal quality: Low for lead generation; useful for normalization.

### `lever-public-postings`: Public applicant-tracking-system job APIs (Lever example)

- **Verdict: PARTIAL.** API shape verified on a non-Chicago employer; no Chicago employer list exists in the public sources probed.
- Official URL: https://github.com/lever/postings-api
- Access method: Per-company public JSON API (Lever, Greenhouse); company slug required. Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 200; 2 sample rows/records retrieved; newest record date 2026-08-11.
- Sample fields (17): `additional`, `additionalPlain`, `applyUrl`, `categories`, `country`, `createdAt`, `description`, `descriptionBody`, `descriptionBodyPlain`, `descriptionPlain`, `hostedUrl`, `id`, `lists`, `opening`, `openingPlain`, `text`, `workplaceType`
- Probe details: `{"note": "public ATS endpoint keyed by company slug (here a non-Chicago company only to prove the API shape); a Chicago employer list would have to come from elsewhere"}`
- Coverage: One company per call; no geographic search. Update frequency: Live.
- Terms: https://github.com/lever/postings-api (Terms for third-party aggregation not found.)
- Ingestion effort: large. Lead uses: Hiring signal for companies already identified (e.g. new licensed businesses with career pages). Signal quality: Low: no Chicago employer list is available; large job boards (Indeed, LinkedIn) were not probed (no sanctioned public API for this use was found; scraping them is out of scope).

### `orlando-permit-applications`: City of Orlando Permit Applications (open data)

- **Verdict: VERIFIED.** Rows and stage dates retrieved.
- Official URL: https://data.cityoforlando.net/d/ryhf-m453
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 9 request(s), HTTP status 200, 200, 200, 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 1,115,699; newest record date 2026-11-16; earliest 1907-07-26; portal rows-updated 2026-11-16.
- Sample fields (22): `application_status`, `application_type`, `commissioner_district`, `contractor`, `contractor_address`, `contractor_name`, `contractor_phone_number`, `estimated_cost`, `neighborhood`, `of_cycles`, `of_pdoxwkflw`, `parcel_number`, `parcel_owner_name`, `permit_address`, `permit_number`, `plan_review_type`, `private_provider`, `private_provider_company_name`, `private_provider_qualifier_name`, `property_owner_name`, `square_footage`, `worktype`
- Portal name: Permit Applications
- Probe details: `{"column_count": 43, "latest_by_field": {"issue_permit_date": "2026-11-16", "under_review_date": "2026-11-16"}, "top_application_status": {"Closed": 386355, "Completed": 882, "Finaled": 648897, "HardHold": 436, "Hardhold": 78, "Hold": 6662, "None": 8, "Open": 72318, "Stop Work": 50, "Void": 13}, "top_application_type": {"Alcohol Beverage License": 4925, "Building Permit": 343360, "Demolition Permit": 5970, "Electrical": 212403, "Engineering": 70181, "Fire Permit": 55026, "GAS": 13918, "History": 111191, "Mechanical Permit": 110734, "Plumbing": 122026, "School Impact Fees": 6735, "Sewer Benefit Fees": 43598}}`
- Coverage: City of Orlando; applications with review stage dates through issuance and certificate dates. Update frequency: Daily.
- Terms: https://data.cityoforlando.net/api/views/ryhf-m453.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Reference model: application status plus under-review, pending-issuance and issue dates, contractor name and estimated cost. Signal quality: High as a method reference; Orlando, not Chicago.

### `fdor-property-rolls`: Florida Dept. of Revenue assessment roll files (NAL/SDF) incl. Orange County

- **Verdict: PARTIAL.** Documentation page verified; file downloads were not fetched.
- Official URL: https://floridarevenue.com/property/Pages/DataPortal_RequestAssessmentRollGISData.aspx
- Access method: Bulk files per county from the state data portal. Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 200.
- Probe details: `{"content-length": "60038", "expected_patterns_found": {"NAL": true, "Sale Data File": true}, "last-modified": "Mon, 16 Nov 2026 21:45:36 GMT", "title": "Florida Dept. of Revenue - Property Tax - Data Portal - Request Assessment Roll and GIS Data"}`
- Coverage: All 67 Florida counties; real property roll (NAL), sale data (SDF). Update frequency: Preliminary July, final October and after VAB.
- Terms: https://floridarevenue.com/property/Pages/DataPortal_RequestAssessmentRollGISData.aspx (Page read; no reuse terms found.)
- Ingestion effort: medium. Lead uses: Roof-age proxy: year built and effective year built per parcel to pair with permits. Signal quality: Medium.

### `orange-county-property-appraiser`: Orange County (FL) Property Appraiser web site

- **Verdict: NOT FOUND.** The site is a JavaScript app (Angular) that shows 'Please enable JavaScript'; no bulk or API link was found; Florida's state portal is the practical route.
- Official URL: https://ocpaweb.ocpafl.org/
- Access method: Single-page web application. Auth or key: none. Cost: unknown.
- Probe: 1 request(s), HTTP status 200.
- Probe details: `{"content-length": "5458", "expected_patterns_found": {"download|bulk data|csv export": false}, "last-modified": "Mon, 26 Oct 2026 12:32:14 GMT", "title": "Orange County Property Appraiser"}`
- Coverage: Orange County parcels. Update frequency: Not stated.
- Terms: https://ocpaweb.ocpafl.org/ (Terms not found.)
- Ingestion effort: large. Lead uses: Parcel records and sales by address. Signal quality: Not assessable: no data export endpoint found with plain requests.

### `noaa-storm-events`: NOAA NCEI Storm Events Database (bulk CSV, already ingested)

- **Verdict: VERIFIED.** Directory listing read; newest file compile date recorded.
- Official URL: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/
- Access method: Bulk gzipped CSV per year (details, locations, fatalities). Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 200; 77 sample rows/records retrieved; newest record date 2026-10-26.
- Probe details: `{"files_listed": 77, "years_with_details_file": "1950..2026"}`
- Coverage: United States, 1950-present; hail events with size at report points. Update frequency: Files recompiled monthly (newest details file compiled 2026-10-26).
- Terms: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/ (Directory listing only; NOAA data is federal; no terms text matched.)
- Ingestion effort: small (done). Lead uses: Hail/wind event dates and sizes for roofing triggers; spotter points, not footprints. Signal quality: Low in Chicago (H04, H05 found no signal).

### `noaa-swdi-hail`: NOAA SWDI NEXRAD Level-3 hail signatures (already ingested)

- **Verdict: VERIFIED.** Chicago-box query returned detections.
- Official URL: https://www.ncei.noaa.gov/swdiws/
- Access method: REST CSV service. Auth or key: none. Cost: free.
- Probe: 1 request(s), HTTP status 200; 5 sample rows/records retrieved.
- Sample fields (8): `ZTIME`, `WSR_ID`, `CELL_ID`, `PROB`, `SEVPROB`, `MAXSIZE`, `LAT`, `LON`
- Probe details: `{"first_detection_in_window": "2026-08-09", "query": "nx3hail, Chicago bbox, 2026-08-01..2026-08-30, limit 5 (the service returns the earliest 5 in the window)"}`
- Coverage: United States, radar-detected hail cells; the project pulls the Chicago box. Update frequency: Near real time.
- Terms: https://www.ncei.noaa.gov/swdiws/ (Service page only; no terms text matched.)
- Ingestion effort: small (done). Lead uses: Hail footprints for roofing; the signal lab found no lift (H28). Signal quality: Low in Chicago.

### `cook-assessor-residential-chars`: Cook County Assessor residential characteristics (roof construction, year built)

- **Verdict: VERIFIED.** Rows retrieved; roof field present.
- Official URL: https://datacatalog.cookcountyil.gov/d/x54s-btds
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 30,656,402; portal rows-updated 2026-11-15.
- Sample fields (42): `card`, `card_proration_rate`, `cdu`, `char_air`, `char_apts`, `char_attic_fnsh`, `char_attic_type`, `char_beds`, `char_bldg_sf`, `char_bsmt`, `char_bsmt_fin`, `char_cnst_qlty`, `char_ext_wall`, `char_fbath`, `char_frpl`, `char_gar1_area`, `char_gar1_att`, `char_gar1_cnst`, `char_gar1_size`, `char_hbath`, `char_heat`, `char_land_sf`, `char_ncu`, `char_porch` ...
- Portal name: Assessor - Residential Single and Multi-Family Improvement Characteristics
- Probe details: `{"column_count": 44}`
- Coverage: Cook County single- and multi-family improvements by tax year. Update frequency: Updated 2026-11-15 per portal.
- Terms: https://datacatalog.cookcountyil.gov/api/views/x54s-btds.json (See license_terms_link in the probe details.)
- Ingestion effort: small (already ingested as res_chars). Lead uses: char_yrblt and char_roof_cnst (roof construction code), char_repair_cnd; roof-age proxy for residential roofing. Signal quality: Medium: roof construction code only (no roof age or replacement year).

### `cook-assessor-commercial-valuation`: Cook County Assessor commercial valuation data

- **Verdict: VERIFIED.** Rows retrieved; no roof column exists.
- Official URL: https://datacatalog.cookcountyil.gov/d/csik-bsws
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 109,409; portal rows-updated 2025-12-30.
- Sample fields (23): `address`, `adj_rent_sf`, `bldgsf`, `caprate`, `class_es`, `excesslandval`, `exp`, `finalmarketvalue`, `finalmarketvalue_sf`, `incomemarketvalue`, `investmentrating`, `keypin`, `landsf`, `noi`, `pgi`, `pins`, `property_type_use`, `salecompmarketvalue_sf`, `sheet`, `township`, `vacancy`, `year`, `yearbuilt`
- Portal name: Assessor - Commercial Valuation Data
- Probe details: `{"column_count": 76}`
- Coverage: Cook County commercial and multifamily properties valued by the assessor (income-approach data). Update frequency: Updated 2025-12-30 per portal (annual).
- Terms: https://datacatalog.cookcountyil.gov/api/views/csik-bsws.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Building size, stories, use, owner and taxpayer, income and market value: qualifies commercial properties (no roof material field). Signal quality: Medium: no roof fields; annual snapshot.

### `sam-opportunities-api`: SAM.gov Get Opportunities public API

- **Verdict: BLOCKED.** Key required; no key available to this agent. Unauthenticated calls to api.sam.gov returned an empty 404.
- Official URL: https://open.gsa.gov/api/get-opportunities-public-api/
- Access method: REST API. Auth or key: API key tied to a SAM.gov account (required). Cost: free (key).
- Probe: 2 request(s), HTTP status 200, 404; 0 sample rows/records retrieved.
- Probe details: `{"docs_say_api_key_required": true, "unauthenticated_api_body_bytes": 0, "unauthenticated_api_status": 404}`
- Coverage: Federal solicitations nationally; filterable by place of performance. Update frequency: Live.
- Terms: https://open.gsa.gov/api/get-opportunities-public-api/ (Documentation page read: key required, daily request limits by role.)
- Ingestion effort: medium. Lead uses: Federal construction/IDIQ solicitations in Illinois for subcontractor prospecting. Signal quality: Medium: federal work is a small share of Chicago contractor revenue.

### `usaspending-api`: USAspending.gov API (awards by place of performance)

- **Verdict: BLOCKED.** Every request from this client was answered by a web-application-firewall block page (HTTP 500); not worked around. Retry from another network.
- Official URL: https://api.usaspending.gov/docs/endpoints
- Access method: REST API (POST for searches). Auth or key: none documented. Cost: free.
- Probe: 1 request(s), HTTP status 500; 0 sample rows/records retrieved.
- Probe details: `{"response_text": "The URL you requested has been blocked block Web Page Blocked! The page cannot be displayed. Please contact the administrator for additional information. URL: \u2026", "waf_block_page": true}`
- Coverage: Federal prime awards and subawards since 2008. Update frequency: Daily.
- Terms: https://www.usaspending.gov/about (About page reachable; no reuse terms extracted.)
- Ingestion effort: medium. Lead uses: Federal awards in Chicago with recipient names; incumbent contractors and subaward partners. Signal quality: Medium.

### `sec-edgar`: SEC EDGAR submissions API and full-text search

- **Verdict: VERIFIED.** Both endpoints answered with our declared research User-Agent; the founder's contact email should be added before volume use.
- Official URL: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Access method: REST JSON APIs (data.sec.gov, efts.sec.gov). Auth or key: none; declared User-Agent required. Cost: free.
- Probe: 2 request(s), HTTP status 200, 200; 1,002 sample rows/records retrieved; newest record date 2026-11-12.
- Sample fields (24): `addresses`, `category`, `cik`, `description`, `ein`, `entityType`, `exchanges`, `filings`, `fiscalYearEnd`, `flags`, `formerNames`, `insiderTransactionForIssuerExists`, `insiderTransactionForOwnerExists`, `investorWebsite`, `lei`, `name`, `ownerOrg`, `phone`, `sic`, `sicDescription`, `stateOfIncorporation`, `stateOfIncorporationDescription`, `tickers`, `website`
- Probe details: `{"full_text_query": "\"certificate of need\", 10-K, 2026-01-01..2026-11-01", "full_text_search_hits_for_query": 56, "ua_accepted": "request succeeded with our declared research User-Agent"}`
- Coverage: All SEC filers; the full-text query returned hits for 2026 filings. Update frequency: Real time.
- Terms: https://www.sec.gov/os/accessing-edgar-data (Read: fair-access limit 10 requests/second; declare a User-Agent with contact details (name and email).)
- Ingestion effort: medium. Lead uses: Capex disclosures and facility plans of public companies with Chicago operations; low volume for small contractors. Signal quality: Low-medium.

### `census-cbp`: Census County Business Patterns (bulk county file)

- **Verdict: VERIFIED.** 2023 county file present; unkeyed API call failed.
- Official URL: https://www.census.gov/programs-surveys/cbp.html
- Access method: Bulk ZIP per year; API needs a key. Auth or key: none for bulk; key for API (the unkeyed API call returned 'Missing Key'). Cost: free.
- Probe: 1 request(s), HTTP status 206.
- Probe details: `{"file": "cbp23co.zip", "last_modified": "2025-06-26", "range_supported": true, "total_bytes": 12919520}`
- Coverage: County x NAICS, establishments by employee-size class, to 2023. Update frequency: Annual (2023 file on the site 2026-11-16).
- Terms: https://www.census.gov/data/developers/about/terms-of-service.html (API terms read (attribution required). Bulk files: terms not found.)
- Ingestion effort: small. Lead uses: Market sizing: establishments per NAICS in Cook County for TAM and normalization. Signal quality: Low for leads.

### `fmcsa-company-census`: FMCSA Company Census File (data.transportation.gov)

- **Verdict: VERIFIED.** Chicago carriers retrieved.
- Official URL: https://data.transportation.gov/d/az4n-8mr2
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 6 request(s), HTTP status 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 20,715; newest record date 2026-11-13; earliest 1974-06-01; portal rows-updated 2026-11-16.
- Sample fields (48): `add_date`, `bus_units`, `carrier_mailing_city`, `carrier_mailing_cnty`, `carrier_mailing_country`, `carrier_mailing_state`, `carrier_mailing_street`, `carrier_mailing_zip`, `carrier_operation`, `carship`, `classdef`, `company_officer_1`, `crgo_beverages`, `crgo_coldfood`, `crgo_drivetow`, `crgo_genfreight`, `crgo_logpole`, `crgo_meat`, `crgo_paperprod`, `dot_number`, `driver_inter_total`, `dun_bradstreet_no`, `email_address`, `fleetsize` ...
- Portal name: Company Census File
- Probe details: `{"column_count": 147, "latest_by_field": {"mcs150_date": "2026-11-15"}}`
- Coverage: US motor carriers; Chicago carriers filtered by physical city. Update frequency: Daily snapshot.
- Terms: https://data.transportation.gov/api/views/az4n-8mr2.json (See license_terms_link in the probe details; the dot.gov data page is disallowed to our client (robots 403) and was not read.)
- Ingestion effort: small. Lead uses: Trucking/fleet prospects: power units, drivers, add_date (new carrier) and mcs150_date (last MCS-150 update); fleet-service and equipment sellers. Signal quality: Medium-high for fleet B2B; current state only (no change history).

### `chicago-contracts`: City of Chicago Contracts (data portal)

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://data.cityofchicago.org/d/rsxa-ify5
- Access method: Socrata API. Auth or key: none. Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 189,023; portal rows-updated 2026-11-16.
- Sample fields (17): `address_1`, `approval_date`, `award_amount`, `city`, `contract_type`, `department`, `end_date`, `procurement_type`, `purchase_order_contract_number`, `purchase_order_description`, `revision_number`, `specification_number`, `start_date`, `state`, `vendor_id`, `vendor_name`, `zip`
- Portal name: Contracts
- Probe details: `{"column_count": 19}`
- Coverage: City of Chicago contracts and amendments with vendors and amounts. Update frequency: Updated 2026-11-16 per portal.
- Terms: https://data.cityofchicago.org/api/views/rsxa-ify5.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small. Lead uses: Incumbent vendors, award values, and expiring contracts for rebid timing. Signal quality: Medium-high for public-work subcontractors.

### `cook-procurement-awards`: Cook County Procurement: awarded contracts and amendments

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://datacatalog.cookcountyil.gov/d/qh8j-6k63
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 8,342; portal rows-updated 2026-10-16.
- Sample fields (12): `amount`, `board_approval_1`, `category`, `commodity_type`, `contract_number`, `description`, `end_date`, `lead_department`, `start_date`, `system_release`, `vendor_name`, `vendor_number`
- Portal name: Procurement - Awarded Contracts & Amendments; license: Public Domain
- Probe details: `{"column_count": 12}`
- Coverage: Cook County Government contracts. Update frequency: Updated 2026-10-16 per portal.
- Terms: https://datacatalog.cookcountyil.gov/api/views/qh8j-6k63.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Awarded contractors and amounts for county work. Signal quality: Medium.

### `cook-procurement-bids`: Cook County Procurement: bid tabulations

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://datacatalog.cookcountyil.gov/d/32au-zaqn
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 5,689; portal rows-updated 2026-11-10.
- Sample fields (12): `bid_amount`, `bid_opening_date`, `city`, `company_name`, `contract_number`, `department_name`, `location_1`, `no_responses`, `procurement_contact`, `procurement_type`, `project_name`, `state`
- Portal name: Procurement - Bid Tabulations; license: Public Domain
- Probe details: `{"column_count": 13}`
- Coverage: Cook County bids with bidder names and prices. Update frequency: Updated 2026-11-10 per portal.
- Terms: https://datacatalog.cookcountyil.gov/api/views/32au-zaqn.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Who bids and at what price: competitor and GC intelligence for county work. Signal quality: Medium-high for public-work subs.

### `cook-procurement-buying-plan`: Cook County Procurement: Buying Plan FY2026 (forward-looking)

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://datacatalog.cookcountyil.gov/d/cbhc-xvrm
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 164; portal rows-updated 2026-02-13.
- Sample fields (9): `anticipated_advertise_date`, `buying_plan_number`, `contract_commodity_category`, `current_contract_number`, `department`, `estimated_contract_term`, `estimated_total_contract`, `project_description`, `proposed_procurement_method`
- Portal name: Procurement - Buying Plan - Fiscal Year 2026; license: Public Domain
- Probe details: `{"column_count": 9}`
- Coverage: County planned procurements for the fiscal year. Update frequency: Updated 2026-02-13 per portal (one dataset per fiscal year).
- Terms: https://datacatalog.cookcountyil.gov/api/views/cbhc-xvrm.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Forward-looking list of planned solicitations: the closest thing to a pre-bid pipeline in the public data. Signal quality: Medium.

### `il-future-solicitations`: State of Illinois Future Solicitations (open data portal)

- **Verdict: VERIFIED.** Rows retrieved.
- Official URL: https://illinois-edp.data.socrata.com/d/6rb8-ntpm
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 47; portal rows-updated 2026-11-16.
- Sample fields (7): `approximate_cost`, `architect_engineer`, `description`, `estimated_bid_date`, `location_name`, `project_manager`, `project_number`
- Portal name: Future Solicitations
- Probe details: `{"column_count": 7}`
- Coverage: State agencies' planned solicitations. Update frequency: Updated 2026-11-16 per portal.
- Terms: https://illinois-edp.data.socrata.com/api/views/6rb8-ntpm.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Forward-looking state bids (including construction through agencies), earlier than posted bids. Signal quality: Medium.

### `il-cdb-registered-vendors`: Illinois Capital Development Board registered vendors

- **Verdict: VERIFIED.** Rows retrieved; business contact fields redacted in the catalog.
- Official URL: https://illinois-edp.data.socrata.com/d/3dh9-yktq
- Access method: Socrata API. Auth or key: none (app token optional). Cost: free.
- Probe: 3 request(s), HTTP status 200, 200, 200; 5 sample rows/records retrieved; dataset total 2,880; portal rows-updated 2026-11-16.
- Sample fields (11): `city`, `county`, `expiration_date`, `phone_number`, `state`, `street_address`, `trades`, `types`, `vendor_id`, `vendor_name`, `zip_code`
- Portal name: CDB Registered Vendors
- Probe details: `{"column_count": 12}`
- Coverage: Contractors, architects and engineers registered for state capital projects. Update frequency: Updated 2026-11-16 per portal.
- Terms: https://illinois-edp.data.socrata.com/api/views/3dh9-yktq.json (See license_terms_link in the probe details.)
- Ingestion effort: small. Lead uses: Prospect list and trade categories for contractors that chase state work. Signal quality: Medium for prospecting.

### `chicago-food-inspections`: Chicago Food Inspections (already ingested): freshness

- **Verdict: VERIFIED.** Newest inspection date recorded.
- Official URL: https://data.cityofchicago.org/d/4ijn-s7e5
- Access method: Socrata API. Auth or key: none. Cost: free.
- Probe: 6 request(s), HTTP status 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 318,396; newest record date 2026-11-13; earliest 2010-01-04; portal rows-updated 2026-11-15.
- Sample fields (17): `address`, `aka_name`, `city`, `dba_name`, `facility_type`, `inspection_date`, `inspection_id`, `inspection_type`, `latitude`, `license_`, `location`, `longitude`, `results`, `risk`, `state`, `violations`, `zip`
- Portal name: Food Inspections; license: See Terms of Use
- Probe details: `{"column_count": 22, "top_results": {"Business Not Located": 96, "Fail": 61285, "No Entry": 14323, "Not Ready": 4662, "Out of Business": 26026, "Pass": 164867, "Pass w/ Conditions": 47137}}`
- Coverage: City of Chicago 2010-present. Update frequency: Daily.
- Terms: https://data.cityofchicago.org/api/views/4ijn-s7e5.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small (done). Lead uses: License inspections precede opening; Out of Business closure signal (H26). Signal quality: High (backtested).

### `chicago-311`: Chicago 311 Service Requests (already ingested): freshness

- **Verdict: VERIFIED.** Newest created date recorded.
- Official URL: https://data.cityofchicago.org/d/v6vf-nfxy
- Access method: Socrata API. Auth or key: none. Cost: free.
- Probe: 6 request(s), HTTP status 200, 200, 200, 200, 200, 200; 5 sample rows/records retrieved; dataset total 14,993,850; newest record date 2026-11-16; earliest 2018-07-01; portal rows-updated 2026-11-16.
- Sample fields (36): `city`, `closed_date`, `community_area`, `created_date`, `created_day_of_week`, `created_department`, `created_hour`, `created_month`, `duplicate`, `electrical_district`, `electricity_grid`, `last_modified_date`, `latitude`, `legacy_record`, `location`, `longitude`, `origin`, `owner_department`, `police_beat`, `police_district`, `police_sector`, `precinct`, `sr_number`, `sr_short_code` ...
- Portal name: 311 Service Requests; license: See Terms of Use
- Probe details: `{"column_count": 45, "top_sr_type": {"311 INFORMATION ONLY CALL": 5252417, "Abandoned Vehicle Complaint": 341111, "Aircraft Noise Complaint": 2664955, "Garbage Cart Maintenance": 398430, "Graffiti Removal Request": 732135, "Pothole in Street Complaint": 431429, "Rodent Baiting/Rat Complaint": 391544, "Street Light Out Complaint": 404482, "Traffic Signal Out Complaint": 192024, "Tree Debris Clean-Up Request": 228965, "Tree Trim Request (NO LONGER BEING ACCEPTED)": 303877, "Weed Removal Request": 199202}}`
- Coverage: City of Chicago 2018-present. Update frequency: Daily.
- Terms: https://data.cityofchicago.org/api/views/v6vf-nfxy.json (License field says 'See Terms of Use'; the chicago.gov terms page returned 403 to our client (robots.txt 403), so its text was not read.)
- Ingestion effort: small (done). Lead uses: Building complaint, porch inspection and vacant property signals (H07-H09). Signal quality: High (backtested).

