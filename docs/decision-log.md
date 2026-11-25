# Decision Log

*Each entry: decision, status (Proposed / Accepted / Superseded), alternatives considered, evidence, and what would reverse it. "Proposed" items are awaiting khaled's confirmation.*

### D-001 — Backend-first, with discovery from day 1
- **Status:** Accepted (from the brief), modified.
- **Decision:** Build the intelligence engine before any dashboard; the first "interface" is a weekly report. Customer discovery starts in week 1, not after the engine is done.
- **Alternatives:** Dashboard-first MVP; engine-first with validation at the end.
- **Evidence:** Value depends on data quality and timing, not UI; competitors already have UIs.
- **Reverse if:** Pilots can't use a report format at all.

### D-002 — City of Chicago as the only launch geography
- **Status:** Accepted 2026-11-14 (founder is Chicago-based).
- **Alternatives:** Chicago metro; collar counties; another metro.
- **Evidence:** Free daily permit data with named contractors since 2006; suburbs lagged (2–4 months via Cook County Assessor) or fragmented [V].
- **Reverse if:** Chosen buyer's demand is mostly suburban (e.g. warehouses) and Shovels coverage is good.

### D-003 — Reframe the commercial-trade product from "permit leads" to relationship/market intelligence + pre-permit signals
- **Status:** Accepted 2026-11-14. Backtests support it: GC open-door score separates 5–6x; composite pre-application score reaches 56x base rate at the top of the list.
- **Alternatives:** Permit-issued alerts for subs (as in the brief).
- **Evidence:** At issue, GC named on 99.3%, electrical 92.2%, plumbing 83.9%, HVAC 74.4%, masonry 41.4% of major permits; median 64 days application→issue; industry sources say sub buyout happens during permit review [V].
- **Reverse if:** Interviews show subs still win meaningful work from issued-permit alerts (e.g. change orders, late scopes).

### D-004 — Choose the first buyer by week 4 from three candidates on one pipeline
- **Status:** Superseded by D-011 (founder has no existing contacts; backtests favour owner-facing trades for the first revenue).
- **Alternatives:** Commit now to concrete/electrical/HVAC (brief); commit now to suppliers.
- **Evidence:** Same data pipeline serves A/B/C; willingness to pay unknown for all three.
- **Reverse if:** khaled has privileged access to one buyer group → pick it now.

### D-005 — Sell a managed service before self-serve software
- **Status:** Proposed.
- **Alternatives:** Self-serve SaaS at $149–$499; agency-first.
- **Evidence:** Permit feeds are priced $27–$129/mo [V]; managed service captures outcome data and justifies higher price [H].
- **Reverse if:** Pilots want self-serve and the report is mostly automated.

### D-006 — Integrate a CRM (HubSpot for pilots; HighLevel if the agency standardizes on it); don't build one
- **Status:** Proposed.
- **Evidence:** HubSpot free tier includes API; HighLevel $97–$497/mo covers CRM + agency tooling [V].
- **Reverse if:** CRM integration becomes the main source of customer friction.

### D-007 — Lean stack: Python + Postgres/PostGIS + scheduled jobs; rules-first classification with cached LLM fallback
- **Status:** Proposed.
- **Evidence:** Volume is ~700 permits/week; LLM cost ~$15/month even if every record went to a premium model [E].
- **Reverse if:** Multi-metro volume or team skills favor another stack.

### D-008 — Human approval for all outbound; no automated texting or AI calling of prospects
- **Status:** Accepted (from the brief) and reinforced.
- **Evidence:** TCPA: no B2B exception for autodialed/prerecorded/AI-voice calls or texts to cell phones; $500–$1,500 per violation [V].
- **Reverse if:** Never for prospects; inbound consented leads handled separately.

### D-009 — Customer-facing AI advisor deferred; internal assistant at week 11
- **Status:** Superseded 2026-11-14: the assistant shipped early because it is a thin, read-only tool layer over data the app already shows (numbers always come from tools), and it doubles as the operator's research tool for pilots. Free-form chat requires an API key; deterministic quick answers work without one.
- **Evidence:** NL search over permits is already offered by Shovels, Dodge, Building Radar [V]; the advisor is only as good as profiles + outcomes behind it.
- **Reverse if:** Pilots strongly prefer a chat interface over a report.

### D-010 — Ad management priced as fee + included spend cap + percentage above the cap
- **Status:** Proposed.
- **Evidence:** Market: $249–$599 under $1k spend; median ~$775 at $5k spend; 10–20% models common [V3].
- **Reverse if:** Prospects reject hybrid pricing in sales conversations.

### D-011 — Two tracks on one engine: owner-facing trigger service for cash flow, commercial intelligence as the software asset
- **Status:** Accepted 2026-11-14 (founder delegated the homeowner-trade decision).
- **Decision:** Track 1 sells weekly trigger lists + done-for-you mail to owner-facing trades, starting with porch and masonry contractors. Track 2 builds and sells GC open-door rankings, relationship maps and pre-application predictions to commercial subs and suppliers from month 3–4.
- **Alternatives:** Commercial-only (slower sales, no relationships); agency-only (no software asset); residential-only (lower ceiling).
- **Evidence:** Investor purchases 7–14x permit lift with B2B-reachable buyers; violations 7.6–14x; ~1,100 active porch/masonry contractors reachable cold from permit data; validated commercial formulas (`docs/11-lead-generation-strategy.md`).
- **Reverse if:** Pilots show close rates too low for F2 economics, or commercial pilots convert faster than expected.

### D-012 — Lead formulas are accepted only on time-split backtests and re-fit quarterly
- **Status:** Accepted.
- **Decision:** Train on past years, test on later years; report precision@K per week, lift, calibration; ship only if better than the current version on the latest held-out period.

### D-014 — Build the client version first; admin version later; our own prospecting runs on the engine now
- **Status:** Accepted 2026-11-14 (founder's preference, agreed).
- **Decision:** Ship the client app (Brickline) for pilots and demos. Our own lead generation uses `engine/leads/prospects.py` + a free CRM until there are ~10 clients; then build the admin version (client workspaces, our pipeline, agency management).
- **Evidence:** The client app doubles as the sales demo and the outcome-capture tool; admin needs mostly wrap existing tools (`12-build-order-and-budget.md`).
- **Reverse if:** Agency operations become the bottleneck before the client count does.

### D-015 — Productize round-1 signal-lab winners; no storm or "old house" leads
- **Status:** Accepted 2026-11-15.
- **Decision:** Add 311 building complaints (earliest step before a citation), porch inspection requests, vacant-building complaints, a masonry building-age filter, and block-level solar/roofing lists. Do not sell storm-based roofing leads (no signal with point reports), "old house = new roof", "no A/C = HVAC", basement-water or lead-kit plumbing leads.
- **Evidence:** `13-signal-lab.md` (H07 5.9×, 32-day head start; H08 11.4×; H09 2.5×; H13 2.9×; storms ~1.0×).
- **Reverse if:** Radar hail swaths or client job data show a storm effect.

### D-013 — Demolition permits are not used as an early new-construction signal in Chicago
- **Status:** Accepted.
- **Evidence:** Only 30% of demolitions lead to new construction within 2 years; when they do, the new-construction application usually precedes the demolition permit (median −8 days) and trades are already named (89–98%) [V].

### D-016 — Contact data comes from free public sources first; paid providers are deferred
- **Status:** Accepted 2026-11-15 (founder declined Apollo and similar for now).
- **Decision:** Enrich prospects and company owners with Overture Maps Places (open license, attribution shown), Chicago business licenses/owners (contact-name suggestion only) and the company's own website (robots.txt honored, 1 request/second/host, 30-day cache). Everything is a suggestion with a source and match confidence; the founder copies values into the pipeline form and saves. Business contacts only; nothing is pattern-guessed; no personal social profiles.
- **Evidence:** `research/findings/contact-enrichment-2026-11-13.md`: 28.4% of prospects (19.5% of best-fit) and 3.0% of company owners get at least one suggestion.
- **Reverse if:** Free coverage is too low for the weekly send volume (then test a paid provider on unmatched best-fit prospects), or Overture's terms or a site owner's objection require removing a source.

### D-017 — Closed-restaurant spaces ship as a lead kind and pilot list; pest control stays a pilot without a probability
- **Status:** Accepted 2026-11-15.
- **Decision:** H26 becomes the `closed_restaurant` lead kind (general-contracting trade, letter to the property owner) and a citywide pilot list on `/commercial`. The headline chance is a new differently named food license at the address (time-adjusted), and the trade chance is the weaker build-out permit rate, labelled weak. H23 ships only as a weekly targeting list for one pest-control pilot client (`/pilots/pest`), with descriptive counts and no chance of work, until that client's win rate is measured.
- **Evidence:** BT8 (`research/findings/backtests-2026-11-15.md`): new license 10.2× and 31+ days 5.0×, stable 2016–2020 vs 2021–2025; build-out permit only 1.78×. H23 is weak by the conservative measure (1.5×) and 37% of recent pest flags are a generic "pests" mention.
- **Reverse if:** No buyer pays for the closed-restaurant list after a fair pilot (then drop it from `/commercial` and the lead list), or a pest-control pilot shows a measurable win rate (then add a pest lead kind with that measured rate).

### D-018 — Strength words follow the signal lab's verdict cut-offs
- **Status:** Accepted 2026-11-15.
- **Decision:** Wherever the app or snapshot calls a lift weak, useful or strong, the word is computed from the lift with the lab's cut-offs (below 1.25× no real signal, below 1.8× weak, below 3× useful, otherwise strong). Copy never hardcodes a strength word that the data could contradict later.

### D-019 — Case-study claims are hypotheses; models add features only on out-of-time gain
- **Status:** Accepted 2026-11-16.
- **Decision:** The five AI lead-discovery demos (Georgia CON, Seattle permits, Texas TCEQ, new-business filings, Orlando roofs) are treated as hypotheses and tested on Chicago analogs. Ship H33 and H29 as pilot lists; reject the commercial reroof model (H30) and the new-business survival tag (H31). Scoring stays historical-rate based; extra features or ML only when an out-of-time ablation shows gain, and learning-to-rank only after real sales outcomes exist.
- **Evidence:** `docs/15-intelligence-engine.md`, `13-signal-lab.md` round 4, BT9, `research/findings/source-verification-2026-11-16.md`.
- **Reverse if:** Pilot outcomes show the historical proxies rank leads worse than a learned model.

### D-020 — No event vertical, no brokerage operation, no dumpster product (for now)
- **Status:** Accepted 2026-11-17.
- **Decision:** Do not build event intelligence, event coordination/brokerage, or a dumpster lead product. Keep the validated assets and sell them. Revisit events only if a rental company asks (recurring-series alerts from CDOT and Park District history), and brokerage only after ~10 paid outcomes show where a router would add value.
- **Evidence:** Signal lab round 6: new events surface days to weeks ahead (Park District median 3 days after start; CDOT ~31 days), organizers named on 0.6% of recurring series; dumpster market top-10 share 83% and 70% hauler reuse by GCs; brokerage adds liability and hours without solving customer acquisition (`docs/16-vision-and-plan.md`).
- **Reverse if:** A paying rental or hauler customer asks for these lists, or pilots show that buyers want coordination rather than leads.

### D-021 — Pilot offer: free sample, 30-day pilot, then subscription or a fee per won job
- **Status:** Accepted 2026-11-17 (pricing is a hypothesis to test).
- **Decision:** Every pitch offers a 5-row sample, then a 30-day pilot in exchange for recorded outcomes; afterwards either a subscription or a fee per won job, recorded as the prospect's fee model with its monthly value. No 3-day trials; no price tiers until 5 customers pay.
- **Evidence:** Leads take weeks to close, so short trials can't show value; job-value and deal-value tracking now make per-won-job pricing measurable.
- **Reverse if:** Buyers consistently prefer a flat subscription, or attribution of won jobs proves unreliable.

### D-022 — Test event services and brokered referrals; social media by hand only
- **Status:** Superseded 2026-11-25 by D-029 for *collection*. Outreach (one message at a time, no bulk DMs) is unchanged.
- **Decision:** Run two brokerage tests tracked in `/deals`: event planning/coordination with partner vendors (customers pay vendors directly; disclosed planning fee) and porch referrals (own-brand letters, partner contractors, fee per appointment or job). Social media is a manual source: find public announcements and requests and message people one at a time, with opt-outs honored; no scraping tools, bulk follows or bulk DMs. City event data covers organization events (2 months' notice for festivals), recurring series and block parties (flyers only).
- **Evidence:** Round 6 (new events surface weeks ahead; recurring series predictable; organizations named on 43% of festivals); `/deals` makes cost and conversion per source measurable within 30 days.
- **Reverse if:** After 30 days a source books nothing for its effort, a platform objects, or event-day liability outweighs fees (then stop coordination and keep referrals).

### D-023 — Investor leads use state transfer declarations; models stay on the Assessor history
- **Status:** Accepted 2026-11-18.
- **Decision:** Investor-purchase leads read the Cook County Assessor's sales plus the Illinois PTAX-203 declarations the Assessor has not loaded (matched by recorder document number, with the Assessor's own filters). Probabilities and every model keep using the Assessor history only.
- **Evidence:** `docs/15` §6b: identical sale dates on 78,366 matched sales; the Assessor skips whole recording weeks; newest lead 11 days old instead of 67; models byte-identical.
- **Reverse if:** The two feeds stop agreeing on overlapping months, or the Assessor starts publishing without gaps (then PTAX adds nothing).

### D-024 — Letters carry the not-a-bill box, the license number and a reply code; owners reach us, we never skip-trace them
- **Status:** Accepted 2026-11-18 (have a lawyer confirm the template).
- **Decision:** Every letter draft opens with the 815 ILCS 505/2PP disclosure (14-point bold, outlined box) and prints the contractor's Chicago license number; every draft carries a reference code, and owner replies are logged by code. Individual owners are reached only by mail and their own reply: no skip tracing, homeowner calls, texts or ad-audience matching. Business pages from Overture are stored as links for manual messages only.
- **Evidence:** `docs/18` (statute and code text read 2026-11-18; provider and platform terms).
- **Reverse if:** Counsel advises different wording, or the founder decides to research a paid, compliant provider (then measure it on the unmatched best-fit prospects first).

### D-025 — The scofflaw list is evidence, not a ranking signal
- **Status:** Accepted 2026-11-18.
- **Decision:** Show the Building Code Scofflaw List on leads at listed addresses; do not rank or score on it.
- **Evidence:** H42: 0.92× any-permit rate vs same-month cited addresses (387 listed addresses).
- **Reverse if:** A history of the list (archived snapshots) shows a clear lift for newly listed buildings.

### D-026 — Experiments run on hash-assigned arms; holdouts are opt-in per workspace
- **Status:** Accepted 2026-11-18.
- **Decision:** Every conversion experiment assigns arms by a hash of the experiment name and lead id (`docs/19`), so assignment is reproducible offline and nobody overrides it. The letter holdout is a per-workspace setting (default off), measured by permits at the address within 365 days.
- **Evidence:** Historical rates cannot show what a letter adds; sample sizes in `docs/19` (about 3,200 leads to see +5 points).
- **Reverse if:** Volume stays too low to read a result within a year (then drop the holdout and rely on reply rates).

### D-027 — Full pursuit down to the legal floor (supersedes the "free data only" decision and the owner-contact parts of D-024)
- **Status:** Accepted 2026-11-18 (founder decision).
- **Decision:** Every lead is pursued, including individual owners and private event hosts: letters, door hangers, hand-dialed calls and one-to-one texts; paid skip tracing and contact data from providers whose terms allow marketing; block-party applicants' names and mailing addresses are collected into private lists. Only legal and security limits remain: no autodialed, prerecorded or AI calls or bulk texts without written consent; Do Not Call scrub and opt-outs honored; 2PP box and license number on letters; CAN-SPAM; no scraping against terms or working around blocks; private persons' phones and emails kept out of git and shipped files (public-record names and mailing addresses may ship, as the snapshot's owner names do; the app stays private).
- **Evidence:** `docs/18` §5 (TCPA $500-$1,500 per call or text; provider terms); block-party backtest: 77.8% of blocks with a party in all three prior summers held one again (`research/findings/private-lists-2026-11-17.md`).
- **Reverse if:** A complaint, carrier block or legal advice shows a channel is costing more than it earns.

### D-028 — No names, mailing addresses or notes in AI tool results
- **Status:** Accepted 2026-11-18 (fixes the publish security review's privacy note).
- **Decision:** The assistant's tools send Anthropic yes/no flags and links instead of property owners', buyers' and sellers' names, owners' mailing addresses and the founder's lead notes (phones, emails and prospect notes were already excluded). Lead letter drafts and call briefs carry `[owner name]`, `[buyer company]` and `[owner company]` placeholders; the lead page shows the real values. Business names of contractors, competitors and prospects (the companies we sell to or partner with) still go through.
- **Evidence:** Cursor's security review of the brickline-83d7 publish (low severity): tool results included public-record owner and buyer names. A run of every lead tool on all six lead kinds found no owner, buyer or seller name and no note text in the output.
- **Reverse if:** The founder moves AI calls to a provider and terms he approves for personal data, or a feature needs a name the model cannot work without (then send it only for company owners).

### D-029 — Daily event-lead scanner; authenticated social with the team's own sessions
- **Status:** Accepted 2026-11-25 (Omar, this fork).
- **Decision:** Run a daily event-lead scanner for Chicagoland, Milwaukee/SE Wisconsin and NW Indiana. Widen Chicago Park District Socrata to tentative/pending and every upcoming wedding/social venue rental (never download requestor names). Add public HTTPS collectors (DCASE map, tourism RSS, CDOT from the warehouse). Milwaukee special-event permits and McCormick Place are documented, not scraped (no open dataset / captcha wall). Store incrementally (`item_hash`, first/last seen, review status). Optional Anthropic JSON extract that never invents contacts. Digest at 7 AM America/Chicago. Social collection uses licensed providers (Apify, SerpApi, Firecrawl) plus **logged-in Facebook (events, public and joined groups), Instagram and TikTok via the team's own session cookies** (Playwright storage_state or cookie JSON / Apify cookie fields). Rate limits, jitter and per-account caps apply; an expired session is a skip (`session_expired`), not a crash. No fake-account creation, no captcha solving, no bulk DMs. Secrets stay in env or gitignored `secrets/`.
- **Evidence:** Park District live probe 2026-11-25 (Approved 126,599; Tentative 16,265; upcoming 120d Tentative 137 + social/wedding slice); DCASE `xgse-8eg7` has no applicant names; RSS feeds allowed; `reddit.com/robots.txt` Disallow `/`; Omar accepted account risk after D-022's "by hand only" collection rule.
- **Reverse if:** A platform bans the team's accounts, counsel says stop, or the daily list books nothing after a measured stretch (then keep public calendars and drop authenticated social).
