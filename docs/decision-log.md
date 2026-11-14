# Decision Log

*Each entry: decision, status (Proposed / Accepted / Superseded), alternatives considered, evidence, and what would reverse it. "Proposed" items are awaiting khaled's confirmation.*

### D-001 — Backend-first, with discovery from day 1
- **Status:** Accepted (from the brief), modified.
- **Decision:** Build the intelligence engine before any dashboard; the first "interface" is a weekly report. Customer discovery starts in week 1, not after the engine is done.
- **Alternatives:** Dashboard-first MVP; engine-first with validation at the end.
- **Evidence:** Value depends on data quality and timing, not UI; competitors already have UIs.
- **Reverse if:** Pilots can't use a report format at all.

### D-002 — City of Chicago as the only launch geography
- **Status:** Proposed.
- **Alternatives:** Chicago metro; collar counties; another metro.
- **Evidence:** Free daily permit data with named contractors since 2006; suburbs lagged (2–4 months via Cook County Assessor) or fragmented [V].
- **Reverse if:** Chosen buyer's demand is mostly suburban (e.g. warehouses) and Shovels coverage is good.

### D-003 — Reframe the commercial-trade product from "permit leads" to relationship/market intelligence + pre-permit signals
- **Status:** Proposed (biggest change vs. the brief).
- **Alternatives:** Permit-issued alerts for subs (as in the brief).
- **Evidence:** At issue, GC named on 99.3%, electrical 92.2%, plumbing 83.9%, HVAC 74.4%, masonry 41.4% of major permits; median 64 days application→issue; industry sources say sub buyout happens during permit review [V].
- **Reverse if:** Interviews show subs still win meaningful work from issued-permit alerts (e.g. change orders, late scopes).

### D-004 — Choose the first buyer by week 4 from three candidates on one pipeline
- **Status:** Proposed.
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
- **Status:** Proposed.
- **Evidence:** NL search over permits is already offered by Shovels, Dodge, Building Radar [V]; the advisor is only as good as profiles + outcomes behind it.
- **Reverse if:** Pilots strongly prefer a chat interface over a report.

### D-010 — Ad management priced as fee + included spend cap + percentage above the cap
- **Status:** Proposed.
- **Evidence:** Market: $249–$599 under $1k spend; median ~$775 at $5k spend; 10–20% models common [V3].
- **Reverse if:** Prospects reject hybrid pricing in sales conversations.
