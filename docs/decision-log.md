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

