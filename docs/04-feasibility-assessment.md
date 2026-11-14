# Deliverable 4 — Feasibility Assessment

*v1, 2026-11-14. Labels: [V] verified, [V3] third-party reported, [E] estimate, [H] hypothesis.*

## Bottom line

| Dimension | Verdict | Why |
| --- | --- | --- |
| Data availability (City of Chicago) | **Feasible now** | Free Socrata API, updated daily, 853k permits since 2006, contractors named by trade, 99% geocoded with parcel IDs [V] |
| Data availability (suburbs) | **Hard to collect, cheaper to buy** | Cook County Assessor permits cover 113 municipalities but lag 2–4 months and lack contractors [V]; municipal portals vary (ArcGIS in Aurora, login-only Munis in Joliet with FOIA'd monthly reports [V3]) |
| Timing for commercial subs | **Weak with permits alone** | Subs already named at issue (electrical 92%, plumbing 84%, HVAC 74%) [V]; GCs buy out subs during permit review [V, sources below] |
| AI classification and extraction | **Feasible and cheap** | Permit text is short and domain-specific; rules handle most cases, LLMs the remainder; cost is cents per thousand records [E] |
| Entity resolution (contractors) | **Feasible, real work** | Names truncated (~30 chars), inconsistent spellings [V]; needs fuzzy matching + license/address signals + a human review queue |
| Contact discovery | **Feasible for GCs/suppliers; uncertain for small trades** | Licensed providers (Apollo etc.) cover companies with web presence; coverage of small trade firms unknown [H] |
| Outreach compliance | **Feasible with constraints** | Email + manual business-line calls + direct mail are fine with rules; automated texts/AI calls to cells are not without written consent [V] |
| Unit economics | **Dominated by human review and sales, not AI or infrastructure** | [E] below |

---

## 1. Data feasibility

### 1.1 City of Chicago (measured)

See `research/findings/chicago-signal-probe-2026-11-14.md`. Key facts [V]:

- Building permits: ~679 issued/week; ~84 major projects/week (≥ $100k new construction/renovation).
- Only **issued** permits are published (no pending applications in the dataset). Median 64 days, p90 224 days from application to issue for major projects.
- Contacts: owner, GC, architect, and trade contractors by license type, with city/state/zip — **no phone, email or street address** (the portal posted a "contact columns removed" change notice in July 2019).
- Completeness on major permits: reported cost 100%, coordinates 99.2%, parcel PIN 99.2%, description ≥ 40 chars 99.9%.
- Known limitations: reported cost is applicant-declared and likely understated for some projects [H]; contractor names truncated.
- Other useful datasets, same API: building violations (daily), business licenses (daily; issued only, median 13 days application→issue), food inspections (daily), transportation/public-way permits, sign permits.

### 1.2 Cook County and suburbs

- **Assessor – Permits** (`6yjf-dfxs`): municipal permits reported to the Assessor, 113 municipalities, ~71k rows in 2026 so far; monthly counts fall off sharply after June → **2–4 month lag** [V]. Fields: PIN, amount, work description, applicant name, mailing address; no contractor fields.
- **Assessor – Parcel Sales** (`wvhk-k5uv`): sales since 1999; newest sale date in the data today is 2026-08-12 → **~3 month lag** [V]; includes buyer/seller names.
- Municipal portals: inconsistent. Aurora publishes an ArcGIS permit service [V3]; Naperville reportedly has downloadable reports [V3, unverified]; Joliet's portal is login-only, with data obtained via FOIA'd monthly reports [V3].
- Implication: suburban **fresh** leads require either per-city collectors (each a maintenance liability) or a vendor (Shovels coverage for collar counties must be verified with its free tier before buying). Suburban **history** (e.g., last roof permit per parcel) is available from the Assessor.

### 1.3 Pre-permit signals (the gap that matters for commercial trades)

Not in Chicago's open data portal [V: catalog search]. Candidates to research (`09-research-backlog.md`): City Council zoning map amendments and Planned Developments (Clerk legislative system), Chicago Plan Commission and Zoning Board of Appeals agendas (PDF), Community Development Commission, Department of Planning project announcements, public bid portals (City procurement, Public Building Commission, CPS, Park District, county, state, federal), news/press. Shovels sells "Decisions" (zoning/planning) data [V]; Chicago coverage unverified.

### 1.4 Why permit timing is late for subs — sources

- GC buyout guidance: "You do not need a permit to send bid invitations… Start buyout as soon as you have permit-ready drawings — ideally before the permit is submitted" ([Biddock, buyout timeline](https://trybiddock.com/blog/buyout-timeline)).
- Typical commercial sequence: competitive sub bidding happens during the permit "waiting" period; subs are contracted before or as the permit issues ([Lipps & Son typical timeline, PDF](http://lippsandson.com/pacific/documents/typical_timeline.pdf); [CBF Contracting phases](https://cbfcontractinginc.com/phases-of-commercial-construction/)).
- Chicago data corroborates: trade contractors are listed on 74–92% of major permits at issue [V].

---

## 2. Technical feasibility by module

| Module | Difficulty | Main challenges | Build vs buy |
| --- | --- | --- | --- |
| A. Collection (Chicago) | Low | Pagination, incremental pulls by `:updated_at`/issue date, schema changes (two column additions in the last year [V]) | Build (free API) |
| A. Collection (suburbs) | High | Dozens of systems, FOIA, PDFs, logins, ToS | Buy (Shovels) or defer |
| A. Normalization + raw archive | Low–med | Consistent schema across sources, immutable raw store, versioned records | Build |
| Project clustering | Medium | Many permits per building/project (main permit + electrical + signs + express permits); cluster by PIN + address + time window | Build — core asset |
| Entity resolution | Medium–high | Truncated/variant names, DBAs, shared addresses; precision matters more than recall | Build — core asset; human review queue |
| B. Opportunity classification | Low–med | Trade relevance, project type, stage; confirmed vs inferred | Rules first + LLM fallback with cached results |
| C. Predictive signals | Medium–high | Weak evidence (building age ≠ equipment age); missing permit ≠ no work | Defer beyond simple, explainable heuristics |
| D. Contacts | Medium | Coverage, freshness, cost, verification | Buy (Apollo/Shovels) + website lookup; never fabricate |
| E. Outreach drafting | Low | Grounding in sourced facts, tone, compliance footer | Build on LLM API; human approval |
| F. Scoring | Medium | Cold start; learning from feedback without overfitting | Transparent weighted rules first; learn weights later |
| G. CRM | Low (integration) | Field mapping, dedupe | Integrate HubSpot/HighLevel |
| AI assistant (internal) | Low–med | Tool design, tenant isolation, prompt injection from record text | Build thin, later |

---

## 3. Legal and compliance considerations

*Not legal advice; have counsel review before launching outbound services.*

### Outreach rules [V]

- **Email (CAN-SPAM):** no prior consent required, including B2B; accurate headers; non-deceptive subject; identify as an ad where applicable; valid postal address; working opt-out honored within 10 business days; liability extends to the company whose product is promoted *and* the sender — an agency sending on a client's behalf shares exposure ([FTC rules summarized](https://socialleadtools.com/guides/compliance/); [15 U.S.C. § 7704](https://texasdatalaw.com/guides/marketing-calls-texts-and-email/)).
- **Calls/texts (TCPA):** autodialed, prerecorded or artificial/AI-voice calls and texts to **cell phones** require prior express consent (written for advertising) — **no B2B exception**; numbers on the national DNC registry (including wireless) are off-limits for advertising calls without consent or an established relationship; manual calls to business landlines are generally allowed; damages $500–$1,500 per violation with a private right of action ([FCC](https://www.fcc.gov/enforcement/areas/unwanted-communications); [Federal Register, Aug 29 2025](https://www.govinfo.gov/content/pkg/FR-2025-08-29/html/2025-16641.htm); [2026 summary](https://fluxpayments.com/blog/2026-11-06-cold-calling-laws-tcpa-do-not-call-b2b/)). The FCC's "one-to-one consent" rule was vacated in 2025 and removed [V].
- **AI voice:** AI-generated voices count as "artificial" under the FCC's 2024 ruling [V3].

### Product consequences

1. Channels: email (B2B), human phone calls to business lines, direct mail, LinkedIn by hand, in-person visits.
2. No automated SMS or AI calling of prospects. Inbound-lead SMS follow-up (agency) only with captured written consent and A2P registration.
3. Residential owners (from permits/violations) → direct mail; no skip-traced phone campaigns.
4. Violation-based outreach must not imitate government notices or imply affiliation (deception risk).
5. Every drafted email includes sender identity, postal address and opt-out; suppression lists are global per client.

### Data use

- Chicago and Cook County data are published as open data [V]; keep source links and timestamps; respect API limits; prefer APIs/bulk downloads/FOIA over scraping; obey site terms where scraping is unavoidable.
- Contact data must come from licensed providers or public business sources; store provenance per field.
- State privacy laws: verify Illinois' current status and any data-broker registration obligations before storing consumer data at scale [H — open question].

---

## 4. Development and operating costs

### 4.1 AI inference is negligible at city scale [E]

Assumptions: ~700 permits/week (all Chicago issued permits), ~800 input + 150 output tokens per LLM classification, *all* records sent to an LLM (worst case; rules will handle most), priced at a premium-model assumption of $3 per million input / $15 per million output tokens.

- Weekly: 0.56M input → ~$1.70; 0.105M output → ~$1.60 → **~$3.30/week (~$15/month)**.
- Outreach drafting: 50 drafts/customer/week × ~2k tokens → still single-digit dollars per customer per month.
- Conclusion: model choice should be driven by **accuracy on the golden set**, not price, at this scale. Re-examine when processing multiple metros.

### 4.2 Infrastructure [E]

Lean: one managed Postgres (with PostGIS) + one small VM or scheduled jobs + object storage: **~$25–$150/month**.

### 4.3 Data purchases [V prices]

- Chicago: $0.
- Contacts: Apollo Basic $49/seat/mo (annual) — ~2,500 credits/month; ~$0.02 per verified email; phones cost 9× more.
- Suburbs (when justified): Shovels Basic $599/mo or Pro $999/mo.

### 4.4 The real cost: human time [E]

Human review and verification per delivered item: ~2–4 minutes (check record, sanity-check the match, verify contact, approve draft). For 50 items/week that's ~1.7–3.3 hours/week, **~7–14 hours/month per customer if nothing is shared** → $210–$420/month at a $30/hour blended rate.

Leverage: the same project or GC serves several customers in different trades, so research is shared; review time per customer should fall as the customer base grows within a cluster. This is the main reason to launch with **one cluster** (shared pipeline *and* shared research).

### 4.5 Build effort [E]

| Scope | Components | Complexity |
| --- | --- | --- |
| Engine v0 (Chicago permits → clustered projects → resolved parties → trade tags → weekly CSV) | Collector, raw archive, normalizer, clustering, entity resolution v0, rules classifier, golden set, report generator | ~2–4k lines of Python + SQL; one engineer with AI coding assistance |
| v1 (scores, contacts, drafts, CRM sync, metrics) | Scoring config, Apollo integration, draft generator, HubSpot/HighLevel sync, metrics tables | Moderate; mostly integration |
| v2 (pre-permit sources, second cluster, internal assistant) | Agenda/PDF parsers, licenses + inspections pipeline, tool-calling assistant | Moderate–high; pre-permit parsing is the hard part |

---

## 5. Top feasibility risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Buyers don't value permit-derived intelligence enough to pay | Medium | Fatal | Interviews + paid pilots before building v1 |
| Pre-permit sources too hard to collect reliably | Medium | High for commercial subs | Test Shovels Decisions; manual collection in pilots; pivot buyer to suppliers/services |
| Contact coverage poor for small firms | Medium | Medium | Measure match rate on 200 named contractors in week 3 |
| Chicago portal schema/API changes | Low–med | Medium | Schema checks + alerts; raw archive |
| Entity resolution errors cause embarrassing outreach | Medium | Medium | High-precision thresholds + review queue |
| Compliance mistakes in agency outreach | Low–med | High | Channel restrictions baked into product; counsel review |
