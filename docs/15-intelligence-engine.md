# 15 — Predictive Opportunity Engine: assessment, strategy matrix, results, roadmap

*v1, 2026-11-16. Companion to `13-signal-lab.md` (test results), `data-source-registry.md` and `research/findings/source-verification-2026-11-16.md` (sources). Every number below comes from those findings files; nothing here is an estimate unless labelled [E].*

## 1. What already exists (capability assessment)

The founder's brief asks for eleven engine components. Most exist in a lean form; the table says where, and what is missing.

| Component | Where it lives | State | Gap worth closing |
| --- | --- | --- | --- |
| Data source registry | `docs/data-source-registry.md`, `research/probes/source_check.py` (51 sources probed) | Working (document + repeatable probe) | Machine-readable freshness monitor in the weekly refresh |
| Ingestion | `engine/collect/*` (Socrata, NOAA, SWDI, HMDA, Overture, HFSRB), `engine/warehouse.py` sync/build → DuckDB | Working, resumable pages, full re-download weekly | Incremental pulls (`$where` on updated date) for the big Socrata tables |
| Document intelligence | `engine/collect/hfsrb.py` (PDF text via optional `pypdf`) | Proof of concept | Only needed if a healthcare buyer appears |
| Entity resolution | `address_key` + `pin10` joins (`engine/score/signals.py`), name normalization + token-set ratio (`engine/enrich/names.py`) | Working, conservative | Unit-level addresses; operator grouping across licenses |
| Event / signal detection | `engine/leads/snapshot.py`, `engine/score/food.py`, `engine/score/licenses.py` | Working | — |
| Opportunity inference | Lead kinds (who to mail, which trade), `commercial.*` lists, H29 per-trade "still open" table | Working for 10 signal types | Event → many sellers map is per-signal, not a general taxonomy (deliberately; see §5) |
| Scoring | Historical rates with matched controls, time-adjusted remaining probability, cell rate tables with back-off, expected value | Working, calibrated where tested | Learning-to-rank only after real outcome data exists |
| Enrichment | `engine/enrich/contacts.py` (Overture, Chicago licenses/owners, polite website crawl) | Working, free | Paid provider deferred (founder decision D-016) |
| Sales intelligence | Letters (`outreach.ts`), teasers + cold emails (`teaser.ts`), assistant `draft_email` and `call_brief` | Working, human-sent only | Slide decks: not built (no buyer has asked) |
| Feedback / learning | Lead statuses → `/results` measured close rates (calibrated after 10 decided leads); prospect pipeline events | Working, no data yet | Pilot outcomes are the missing input, not code |
| Business context | Client workspaces (trade, neighborhoods, contact details) | Working for contractor trades | Seller profiles for non-trade buyers (sign shops, equipment dealers) |

Validation discipline already in place: one episode per key per window, matched or own-earlier-window baselines, by-year stability, out-of-time splits (BT8, BT9), determinism (identical md5 across runs and under a low memory limit). This is the asset; it is why the case-study claims could be tested rather than repeated.

## 2. The five case studies: what we found

| Case | Claimed method | What we verified | Chicago analog | Result |
| --- | --- | --- | --- | --- |
| 1. Georgia CON → medical equipment | Weekly CON reports list projects, costs, applicants | Georgia's weekly PDF extracts cleanly (32 pages, 18 applications, $149.3M of estimated cost in one week, including MRI/CT replacements), but only the current week is online: history needs our own archive | Illinois HFSRB: 1,692 projects 2011–2026 retrievable; 2022–2026 PDFs give cost (79% of non-exempt), facility, city; 37 Chicago projects ≈ $2.95B | **Source verified, not tested.** Illinois reviews only big projects (equipment threshold ≈ $4.8M), so routine MRI/CT buys never appear; equipment words occur in 36 descriptions. Useful for a medical-equipment or healthcare-construction buyer; no such buyer yet |
| 2. Seattle permits → trade contractors | Applications in review show projects before subs are chosen | Seattle publishes application-stage data; Chicago publishes **issued permits only**, and trades are usually named at issue | Chicago follow-on permits after a $1M+ permit (H29) | **Tested (H29): useful.** 62.1% of big permits see a sign, elevator or electrical follow-on within 540 days (3.06× the same address's earlier window, 1.5× vs other busy addresses). Elevator, electrical, fire-alarm and sign follow-ons mostly go to contractors **not** named on the big permit; plumbing, HVAC and roofing are about half locked in. Productized as a `/commercial` table |
| 3. Texas TCEQ/RRC → oil & gas equipment | Small operators filing many permits | TCEQ query app timed out (Cloudflare 522) on every attempt; RRC bulk files sit behind a JSF download client | Chicago environmental permits (67,886) and EPA ECHO (4,845 Cook County air facilities) verified | **Not applicable to Chicago contractors.** Kept as a source note |
| 4. New businesses → supplier needs | Registration + license + build-out + hiring | Illinois SOS blocks automated access (403); Florida Sunbiz needs SFTP; Chicago's full business-license history (1.21M rows) is open | Chicago license history (ingested as `biz_license_history`, 433,174 rows since 2014) | **Tested (H31–H33).** Registration + build-out permit does **not** predict survival much (H31: 70.7% vs 58.6%, no signal). The strong signal runs the other way: a **build-out permit at an unlicensed commercial space predicts a new business license** (H33: 15.2% vs 1.5%, 10.3×, median 157 days, stable 2016–2020 vs 2021–2025 in BT9). Productized as the "New business coming" pilot list |
| 5. Orlando roofs → replacement cycle | Roof age + storms → replacement | Orlando permits verified; the Orange County appraiser has no export | Commercial/multifamily reroof model (H30) on Chicago permits, Assessor and NEXRAD hail | **Tested (H30): rejected as a model.** Out of time (2021–2023) the full model's precision@1000 is 3.6% vs 3.8% for the single feature "years since last roof permit"; hail adds nothing; there is no "old roof is due" curve, only repeat roofing at the same parcels. Building age exists for only 3.8% of commercial parcel-quarters. Storms tested earlier (H04, H05, H28) also failed |

Lesson: the demos describe real sources, but the claimed "predictions" were not validated. Two of five became product after testing (via their Chicago analogs), one is a verified source waiting for a buyer, two were rejected or don't apply.

## 3. Lead strategy matrix (24 equations)

Status uses the lifecycle PROPOSED → SOURCE_VERIFIED → TESTING → VALIDATED / REJECTED / INCONCLUSIVE → PILOT → PRODUCTION. Numbers are from `13-signal-lab.md` and the backtests. Priority: 1 = do next.

| # | Equation (signal → need) | Target seller | Sources | Window | Status / evidence | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Violation (porch, masonry, roof...) → repair permit | Owner-facing trades | Violations, permits | Months | PRODUCTION (porch 15.3%/14×, masonry 10%/8×) | — |
| E2 | 311 building complaint → citation → permit | Owner-facing trades | 311, violations, permits | 32 days ahead of citation | PRODUCTION (H07 5.8×) | — |
| E3 | Porch inspection request → porch permit | Porch builders | 311, permits | ~150 days | PRODUCTION (11.4×) | — |
| E4 | Vacant complaint → sale → rehab | GCs, wholesalers | 311, sales, permits | ~167 days | PRODUCTION (2.5×) | — |
| E5 | Investor purchase → renovation | GCs, all trades | Sales, permits | Months | PRODUCTION (30–38% any permit) | — |
| E6 | Restaurant closure → new food tenant / build-out | Build-out GCs, equipment, signage, brokers | Food inspections, licenses, permits | 82–252 days (31+ day view) | PILOT (H26 10.2×; 31+ days 5.0×; build-out permit 1.78× weak) | 2 (find a buyer) |
| E7 | **Build-out permit at unlicensed commercial space → new business** | Signage, POS, insurance, cleaning, security, furniture, brokers | Permits, license history, Assessor class | 92–238 days | PILOT (H33 10.3×; BT9 stable) | **1** |
| E8 | **$1M+ permit → follow-on trades still open** | Elevator, electrical, fire alarm, sign contractors | Permits, permit parties | 62–260 days | PILOT (H29; elevator 36%, electrical 35%, fire alarm 25%, signs 19% of big permits see a new contractor) | **1** |
| E9 | Composite pre-application score → $100k+ permit | Commercial subs, GCs | Permits, violations, sales, demolition | 180 days | VALIDATED (top 100 ≈ 26%, 56×) | 3 |
| E10 | GC "open door" (uses new subs) | Commercial subs | Permit parties | Ongoing | VALIDATED (5–6× separation) | 3 |
| E11 | Restaurant pest finding → pest-control account | Pest control | Food inspections | Weeks | PILOT, no probability (H23 weak 1.5×) | 2 (find a buyer) |
| E12 | Solar/reroof neighbors → same work nearby | Solar, roofers | Permits | Months | VALIDATED (H01/H03 ~2.2–2.4×); roofing blocks in product | 4 |
| E13 | Pre-1910 masonry + violation → tuckpointing | Masons | Violations, Assessor | Months | PRODUCTION (H13 2.9×) | — |
| E14 | Commercial roof age + hail → reroof | Commercial roofers | Permits, Assessor, NEXRAD | 1 year | REJECTED (H30: no gain over one feature; H28 hail 1.04×) | — |
| E15 | Storm reports → roofing demand | Roofers | NOAA | Weeks | REJECTED (H04/H05 ~1.0×) | — |
| E16 | New license + build-out → lasting business | Insurance, B2B services | License history, permits | 18–30 months | REJECTED (H31 1.21×) | — |
| E17 | Storefront turnover → build-out after the license | Build-out GCs | License history, permits | 365 days | REJECTED as framed (H32 1.38×; the permit comes first, which is E7) | — |
| E18 | HMDA home-improvement loans by tract → permits | Remodelers | HMDA, permits | 1 year | REJECTED (H27 1.05×) | — |
| E19 | Restaurant plumbing / hood violation → permit | Commercial plumbers, HVAC | Food inspections, permits | 1 year | REJECTED (H24, H25) | — |
| E20 | Illinois CON project → construction and equipment | Healthcare construction, medical equipment | HFSRB, Chicago permits | Months–years | SOURCE_VERIFIED; testable as "CON approval → building permit at the facility" | 3 (needs a buyer) |
| E21 | Council zoning reclassification → new construction permit | GCs, subs, suppliers | City Clerk API (1,487 since 2015), permits | 1–2 years | SOURCE_VERIFIED; testable on history | **1** (next lab test) |
| E22 | ADU preapproval → ADU construction | ADU builders, GCs | Chicago ADU preapprovals (616), permits | Months | SOURCE_VERIFIED | 2 |
| E23 | FMCSA carrier adds power units → fleet services | Fleet maintenance, insurance, parking | FMCSA census (20,715 Chicago carriers) | Months | SOURCE_VERIFIED, but no history in the open file (needs weekly snapshots of our own) | 4 |
| E24 | Cook County / City buying plan and awards → subcontracting | Subs, suppliers | Cook County procurement, Chicago contracts | Months | SOURCE_VERIFIED | 3 |

Also logged as sources without an equation yet: Illinois professional licenses (4.46M records, ODbL), IDPH facility directories (207 hospitals, 156 surgery centers), NPPES (new practice locations for dental/medical suppliers), Chicago environmental permits and ECHO (asbestos/demolition → abatement contractors). Blocked in this environment (recorded, not worked around): Illinois SOS, SAM.gov (needs a free API key), USAspending (firewall page), chicago.gov Plan Commission pages.

## 4. Scoring approach and what the tests say about models

- **What production uses:** the historical conversion rate of the same signal (matched control, one episode per key per window), adjusted for time already passed (`remaining_probability`), split into cells only when each cell has enough history (back-off). Expected value = chance × close rate (default until 10 decided outcomes, then measured) × job value × margin. Inferred vs observed is explicit on every lead.
- **Model complexity test (H30):** a multi-feature rate table beat baselines at precision@100 (7.4% vs 4.7%) and on log-loss, but not at precision@1000 (3.6% vs 3.8% for one feature). Ablation showed only the roof-permit feature mattered. Conclusion: add features only when an out-of-time ablation shows information gain; no gradient boosting or learning-to-rank until real sales outcomes exist (permits are proxies, not purchases).
- **Calibration:** H30's top decile predicted 3.9% vs 2.4% observed because the base rate fell between training and test years. Recalibrate on the most recent period before quoting any model probability.
- **Not done on purpose:** composite "opportunity scores" with hand-set weights for intent, urgency, competition and so on. Each lead shows the measured rate, timing, evidence and owner type instead; weights come later from `/results`.

## 5. One event, many sellers

H29 is the working version of "one event → many suppliers": after a $1M+ permit, the data says which follow-on trades appear, when (median 139 days), and whether the contractor is new (open) or already on the big permit (locked in). Elevator, electrical, fire-alarm and sign work are mostly open; plumbing, HVAC and roofing are about half locked in. H33's licensee mix (food & drink 56%, retail 16%, other 12%, health/fitness/childcare 10%, personal services 5%) does the same for new tenants. A general event-to-supplier taxonomy was not built: every edge should be measured like these two before it is shown to a buyer.

## 6. Experiment framework (how to add the next test)

1. Verify the source (`research/probes/source_check.py`; add a spec) and add the table to `engine/warehouse.py`.
2. Add `hNN_*` to `research/signal_lab/lab.py` with signal, target, window, matched or earlier-window baseline, by-year table; register it in `HYPOTHESES`. `lab.py HNN` writes `*.partial.*` only.
3. Run the full lab twice and once under a 1 GB memory limit; md5 must match.
4. Record the verdict (lab cut-offs: ≥3× and ≥5/week Strong, ≥1.8× Useful, ≥1.25× Weak) in `13-signal-lab.md`, including failures.
5. If it wins: move the definition into `engine/score/<topic>.py`, reproduce the lab exactly, add a backtest with a fixed period and an out-of-time split, then a snapshot list or lead kind. Pilot with a paying buyer before calling it production.

## 6b. Sales feed: PTAX-203 vs the Assessor (reconciled 2026-11-18)

The Assessor's parcel sales (`wvhk-k5uv`) are built from the state's PTAX-203 transfer declarations (`illinois-edp` `it54-y4c6`, public domain). Measured on the warehouse:

- **Same records.** On every one of 78,366 sales matched by recorder document number, the Assessor's `sale_date` is the declaration's instrument (deed) date. In 2024–2025 the Assessor holds 63,237 of 69,486 non-exempt Chicago-township declarations (91%), and almost none of the exempt ones (2 of 32,763 with code E; none with L, F, C, D or I). Its deed filter drops only quit-claim and executor deeds.
- **Not just late: gappy.** The Assessor loads declarations in batches by recording week and skips whole weeks. Coverage of non-exempt declarations by recording week was about 97% through 2026-06-07, then 57% (week of June 8), 0% (June 15 and 22), 98% (July 6), 0% (July 20 to August 2, August 17 to 30, and everything from September 21). So sales signed months ago can still be missing. The newest Assessor sale is 2026-09-15; the newest declaration was recorded 2026-11-13.
- **How the snapshot uses it.** Investor leads read the Assessor sales plus every declaration whose document number the Assessor lacks, with the Assessor's filters (under $10,000, quit-claim or executor deed, same parcel and price within 365 days), exempt declarations and suburban townships dropped, and the parcel's Assessor class (or the form's line 8 use when the parcel has none; condo units excluded). Lead ids stay parcel + date, so a lead keeps its status when the Assessor catches up. Every model stays on the Assessor history; on the same warehouse, all models and all non-investor leads are byte-identical with and without PTAX.
- **Result.** Investor leads per week by sale week: 75 from the Assessor alone vs 83 combined in March 23–April 27 (the extra deeds were recorded in the Assessor's skipped weeks); 22 vs 74 in June–September; 42–80 a week from PTAX alone since mid-September (the last weeks are lower because deeds are recorded a median 14 days, 90th percentile 54 days, after signing). The newest investor lead is 11 days old instead of 67.
- **Not in the form:** no buyer phone, email or mailing address (only the buyer's agent address, on about 7%). Line 10l means the buyer is a **real estate investment trust**, not "an investor" (2 of 8,507 declarations; the 2026-11-18 probe labelled it wrongly).

## 7. Roadmap (next, in order)

1. **Sell the two new pilot lists** (E7 "New business coming" and E8 "Trades still open"): a sign shop, an elevator or fire-alarm contractor, and a commercial cleaner/insurance broker are the natural first buyers. They need no new code; outcomes go in lead statuses or the CSV.
2. **Lab round 5: E21 zoning reclassification → permits** (earliest public pre-permit trail in Chicago), and **E20 HFSRB approval → building permit at the facility** (only if a healthcare buyer shows interest).
3. **Weekly archives for sources without history**: FMCSA carrier census and the Georgia-style weekly reports only become testable after we keep our own snapshots. Cheap to start (add to the weekly refresh), valuable in 6–12 months.
4. **Incremental ingestion and freshness checks** in `scripts/refresh-data.sh` (pull only updated rows; alert when a source stops updating, as scaffolding permits did in 2023).
5. **Learning from outcomes**: once pilots record 10+ decided leads per signal, compare measured close rates to the historical proxies and re-rank; only then consider learning-to-rank.
