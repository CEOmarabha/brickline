# Strategic Assessment — Read This First

*Status: v1, 2026-11-14. Owner: khaled. This is the summary; every other doc in `docs/` expands one part of it.*

Evidence labels used everywhere in this repo:

- **[V] Verified** — checked against a primary source or live data, with a link or a reproducible script.
- **[E] Estimate** — a reasoned number with stated assumptions; could be off by 2x.
- **[H] Hypothesis** — plausible, untested; must be validated before money is spent on it.
- **[S] Speculative** — interesting idea; not on the critical path.

---

## Update — 2026-11-14 (after founder answers and backtests)

Founder answers: building mostly with AI tools, full time, Chicago-based, no existing industry contacts, agrees with the reframe, wants the software to be the priority but generating real cash flow within a year.

Backtests on 20 years of Chicago records (`docs/11-lead-generation-strategy.md`, `research/findings/backtests-2026-11-15.md`) changed the plan:

- **Validated:** GC "open door" scoring for commercial subs (5–6x separation, out of sample); a composite pre-application score (top 100 parcels/half-year: 25% start a ≥$100k project within 180 days, 56x base); investor/company home purchases (30–38% pull permits within a year, 7–14x baseline); porch/masonry/plumbing/electrical violations (10–29% permitted repairs within a year, 7.6–14x); restaurant build-out permits (~90 days ahead of food-license applications).
- **Failed:** demolition permits as an early signal for new construction (they arrive together with the new-construction permit).
- **Decision:** two tracks on one engine — **Track 1 (cash flow):** trigger lists + done-for-you mail for owner-facing trades, starting with porch and masonry contractors; **Track 2 (software asset):** commercial relationship intelligence and pre-application predictions for subs and suppliers. Customers are found and contacted cold using our own permit data, which removes the need for prior relationships.
- §4 and §5 below are superseded where they conflict with `docs/11-lead-generation-strategy.md` §2 and §6.

---

## 1. The one-paragraph answer

The vision (one platform that finds opportunities, identifies the buyer, drafts outreach and tracks outcomes, with an agency on top) is sound as a *destination*. The plan as written has one load-bearing flaw and three serious risks. The flaw: **for the commercial trades named as the first market (electrical, HVAC, plumbing, concrete), an issued building permit is usually not a lead — it is a record of who already won the work.** Live Chicago data shows the general contractor is named on 99% of major permits at issue, the electrician on 92%, the plumber on 84% and HVAC on 74% [V]. The same data is, however, an excellent map of *which general contractors build what, and which subcontractors they use* — and that relationship intelligence, plus earlier pre-permit signals, is what commercial subcontractors actually need. The risks: raw permit leads are already a cheap commodity ($19–$129/month per market) [V]; "AI search/agent over permits" is already shipping at several competitors [V]; and running a SaaS company, a data company and an agency at once is three businesses. My recommendation is to keep the long-term vision, but start with **one data pipeline (City of Chicago), one buyer type to be chosen from customer interviews in the first four weeks, one deliverable (a weekly, human-reviewed intelligence report), sold as a managed service before any self-serve software exists.**

---

## 2. What the live data says (City of Chicago, last 90 days)

Source: `research/probes/chicago_signal_probe.py` → `research/findings/chicago-signal-probe-2026-11-14.md`. All [V].

| Measurement | Value | Why it matters |
| --- | --- | --- |
| Issued building permits | 8,731 (~679/week) | Plenty of raw volume. |
| Major projects (new construction or renovation ≥ $100k) | 1,082 (~84/week); 199 ≥ $1M; 50 ≥ $5M | A focused list of real projects each week — enough for a weekly report, not "thousands of leads". |
| Days from application to issue (major projects) | median 64, p75 130, p90 224 | The project existed for 2–7 months before it appears in the open dataset. The dataset publishes **only issued** permits (0 unissued rows). |
| GC already named on the permit at issue | 99.3% | The GC "lead" is gone by the time the permit appears. |
| Electrical / plumbing / HVAC / masonry sub named at issue | 92% / 84% / 74% / 41% | For MEP subs the specific job is usually already awarded. Masonry/concrete is less often named, so there is still some open work. |
| Distinct GCs on major permits | 627 | A finite, knowable set of GCs to build relationships with. |
| Distinct electrical / plumbing / HVAC subs | 353 / 312 / 411; top-10 hold only 15–25% of jobs | Highly fragmented trades → many potential customers, and each is fighting for GC relationships. |
| GC→sub loyalty | e.g. one GC used the same plumber on 11 of its 20 major permits | Winning work = getting on a GC's bid list, not answering one permit. |
| Contractor names | Truncated at ~30 chars, inconsistent spellings | Entity resolution (who is the *same company*) is real engineering and a defensible asset. |
| Open building violations (30 days) | 3,418 at 876 addresses; porch, masonry, window, roof, plumbing, heating subsets | A **compelled-demand** signal: the owner has been ordered to fix something. |
| New business licenses (30 days) | 621 issued, incl. 101 retail food establishments; median 13 days application→issue | A new-business signal for B2B service providers; arrives roughly when the business opens. |
| Restaurant "License" food inspections (30 days) | 221 | A restaurant about to open, typically days-to-weeks ahead of opening. |

Cook County (suburbs) [V]: the Assessor's permit dataset covers 113 municipalities but arrives **2–4 months late** and has no contractor fields; the parcel-sales dataset lags by months. Good for *history* (when was this roof last permitted), poor for *fresh* leads. Suburban municipalities publish permits inconsistently (Aurora has an ArcGIS service; Joliet's portal is login-only and data comes via monthly reports/FOIA). So **"Chicago metro" is not one data market; "City of Chicago" is.**

---

## 3. Where I disagree with the current plan, and what I'd do instead

### 3.1 "Identify potential jobs before competitors do" via permits — partly wrong

Commercial GCs solicit sub bids during permit review, not after issue (drawings, not permits, drive buyout) [V: industry buyout guides cited in `04-feasibility-assessment.md`]. Chicago's data confirms it: the subs are listed on the permit. So for commercial MEP/concrete subs:

| Instead of… | Sell… | Evidence |
| --- | --- | --- |
| "Here is a permitted $2.4M warehouse, go bid HVAC" | "Here are the 25 GCs who build $250k–$5M commercial jobs in your area, how often, which HVAC subs they use, and which ones rotate subs (= open door)" | GC/sub pairings computed directly from permit contacts [V] |
| Permit-issued alerts | **Pre-permit** signals: zoning/planned-development filings, plan commission/ZBA agendas, development announcements, public bid invitations | Not in Chicago's open data; must be collected or bought (Shovels "Decisions", Dodge, ConstructConnect) [V that they sell it; H on Chicago quality] |
| "Market is busy" | Competitor and market-share intelligence: "Your top 3 competitors did 58 major jobs this quarter; you did 4; here is who they work for" | Computable today [V] |

Permits **are** an early, actionable signal for other buyers — this is where the "lead" framing still works:

- **Suppliers, distributors, equipment rental** — the permit names the contractor who is about to buy materials and equipment. The buyer is on the record. [V that names are present; H that these buyers will pay.]
- **Downstream / post-construction services** not named on permits — commercial cleaning (post-construction + janitorial), low-voltage/AV/security, furniture/fixtures, signage (sometimes), landscaping maintenance, pest control, waste hauling, telecom, insurance, property management. [H]
- **Compelled-demand residential/small-commercial work** — porch, masonry/tuckpointing, windows, roofing, plumbing via violations. [V signal volume; H on conversion. Note outreach limits to individual owners — §3.6.]

### 3.2 Raw permit leads are a commodity — do not compete on data access

Published prices [V, Nov 2026]: Groundbreak Pro $27/mo all markets; PermitBoards $79/mo per county+trade; FieldClients $99–$499/mo (permits + violations + new business licenses + verified contacts — very close to this concept); ConstructConnect $129/mo per market; Construction Monitor $31–$1,250/mo per market; Shovels $0/$599/$999/mo nationwide API. Dodge and Building Radar are quote-only; Building Radar's agent "Jeane" already claims end-to-end discovery → scoring → contacts → outreach drafting → CRM updates, with a fully managed option.

So the defensible value must come from things a $27/month feed does not do:

1. **Relationship and market intelligence** built on resolved entities (who works with whom, win patterns, rotation).
2. **Local depth and earlier signals** (pre-permit sources that need human/AI collection per city).
3. **Done-for-you execution** — research, verified contact, drafted outreach, follow-up, CRM entry — measured by meetings booked. This is where the agency becomes an advantage instead of a distraction.
4. **Outcome data** — which signals actually produced meetings and wins for which trade. Competitors selling feeds don't see outcomes; a managed service does. Over time this becomes the scoring moat.

### 3.3 The AI Business Advisor is right long-term, wrong as an early differentiator

Natural-language search over permits is already table stakes (Shovels "Charlie", Dodge "AI Search Assist", Building Radar "Jeane") [V]. Build it early only as an **internal testing tool** (it's cheap: tool-calling over SQL views). Make it customer-facing once there is (a) reliable data, (b) company profiles, (c) CRM outcomes — otherwise it's an articulate interface to thin data. The daily briefing idea is good and cheap to deliver by email first.

### 3.4 Three businesses at once is the biggest execution risk

SaaS (product + support), data (pipelines that break when cities change systems) and agency (people-heavy delivery, high SMB churn [H]) each want a full team. Sequence them:

1. **Managed sales intelligence** first (the thing being validated; minimal software; $500–$1,500/mo) [H on price].
2. **Agency services** only where you already have delivery capacity, or white-label/partner for ads and social initially; bundle the intelligence report as the differentiator.
3. **Self-serve SaaS** only after the report is retained for 3+ months by paying customers.

### 3.5 Pricing — mostly reasonable, with two fixes

- **Ad management at a flat $350/platform** is at the low end of the market. Published 2026 small-business fees run $249–$599/mo under $1k spend and ~$500–$1,450 (median $775) at $5k spend [V, see `06-business-model.md`]. Keep $350 as an entry price, but **cap it at a spend band** (e.g. up to $1,500/mo spend) and switch to 12–15% above it. A flat fee with no cap loses money as clients scale.
- **Software at $149–$499/mo** is competing against $27–$129 feeds. It's only defensible if it delivers relationship intelligence + workflow + outcomes, not alerts. Don't launch self-serve at that price until the managed version proves value.

### 3.6 Compliance shapes the product (not a footnote)

[V, sources in `04-feasibility-assessment.md`] B2B cold email is legal under CAN-SPAM (opt-out regime, honor opt-outs within 10 business days, physical address, no deceptive subject lines). Autodialed, prerecorded or AI-voice calls/texts to cell phones need prior express written consent — **no B2B exception**; calls to numbers on the national DNC list (incl. wireless) are restricted; TCPA damages are $500–$1,500 per violation with a private right of action. Implications: email + human phone calls to business lines + direct mail are the outreach channels; **no automated texting/AI calling of leads**; residential owners from permits/violations → direct mail, not skip-traced phone calls. Violation-based outreach must never imply government affiliation.

### 3.7 Backend-first — agreed, with one modification

Agree: the intelligence engine is the product, the dashboard is the delivery mechanism. Modification: **customer discovery starts in week 1, in parallel with the first pipeline**, and the first "UI" is the deliverable itself (a weekly report/spreadsheet + a short call). The engine's roadmap should be driven by what pilots do with that report.

---

## 4. Recommendation

| Decision | Recommendation | Confidence |
| --- | --- | --- |
| Geography | **City of Chicago only** (free daily API, contractor names, history since 2006). Suburbs later via purchase (Shovels/others) or per-city collectors, only after validation. | High [V] |
| First buyer | Decide by week 4 from interviews among three candidates that share the same pipeline: **(A)** commercial subs (electrical/HVAC/plumbing/concrete) buying GC-relationship + market intelligence; **(B)** suppliers/distributors/equipment rental buying "contractor X just pulled a $1.2M permit"; **(C)** post-construction & new-business services (commercial cleaning, security/low-voltage, signage). My prior: B and A have the highest willingness to pay; C is the cleanest "lead" use-case. | Medium [H] |
| First product | A **weekly human-reviewed intelligence report** (20–50 well-sourced items, each with evidence, why it matters, who to contact, a drafted email) + monthly market brief. Delivered by email/Sheets, logged to a CRM. | High |
| Business model | Managed service, 3–5 design partners at a discounted pilot price, then $500–$1,500/mo. Agency upsell only where it fits. | Medium [H] |
| Build | Python + Postgres/PostGIS, scheduled ingestion, raw-record archive, entity resolution, project clustering, rules-first classification with cached LLM fallback, golden-set evaluation, CSV/Sheets/report output, thin API. No dashboard. | High |
| Kill/pivot criteria | By day 90: ≥3 paying pilots, ≥40% of delivered items rated "relevant", ≥1 meeting/month/pilot attributable to the report, ≥2 of 3 pilots renew. Miss two of four → change buyer or product, not just features. | — |

Details: `07-mvp-recommendation.md`, `08-90-day-plan.md`.

---

## 5. Questions back to you (these change the plan)

1. **Team and time.** Who builds the engine — you, a technical co-founder, contractors, or mainly AI coding agents? Hours per week? This determines Lean vs Growth architecture and whether the agency is realistic in year one.
2. **Agency status.** Is the agency already operating with clients, or is it planned? If you have clients, they are your first pilots and the sequencing in §3.4 changes.
3. **Industry access.** Do you have personal relationships with contractors, suppliers or GCs in Chicago? Any trade background? The first buyer should be whoever you can get 20 interviews with in 3 weeks.
4. **Location.** Are you in Chicago? In-person pilots matter for trades.
5. **Budget.** Bootstrapped or raising? Rough cash available for the first 6 months (data purchases, contact data, contractors)?
6. **The reframe.** Are you comfortable shifting the commercial-trade product from "permit leads" to "GC relationship + market intelligence + pre-permit signals"? This is the single biggest change I'm proposing.
7. **Residential.** Do you want to serve residential-facing trades (roofing, masonry, windows, HVAC replacement) where leads are individual homeowners? It's viable but changes outreach (direct mail, inbound ads) and compliance.
8. **Year-one priority.** Cash flow (agency first) or building the software asset (managed intelligence first)?

---

## 6. Map of this repo

| Doc | Contents |
| --- | --- |
| `01-product-vision.md` | Deliverable 1 — vision, customers, value proposition |
| `02-industry-opportunity-matrix.md` | Deliverable 2 — 30 industries scored, ranked launch candidates |
| `03-competitive-landscape.md` | Deliverable 3 — competitors, prices, gaps, partners |
| `04-feasibility-assessment.md` | Deliverable 4 — technical, data, legal, cost feasibility |
| `05-technical-architecture.md` | Deliverable 5 — engine modules, data model, evaluation, AI advisor, Lean/Growth/Scale |
| `06-business-model.md` | Deliverable 6 + Agency Service Catalog — pricing, unit economics |
| `07-mvp-recommendation.md` | Deliverable 7 — first buyer, market, sources, smallest useful feature set |
| `08-90-day-plan.md` | Deliverable 8 + Execution Roadmap — weekly plan, milestones, gates |
| `09-research-backlog.md` | Deliverable 9 — ranked open questions |
| `10-additional-opportunities.md` | Deliverable 10 — ideas beyond the core |
| `11-lead-generation-strategy.md` | Backtested lead formulas, homeowner-trade decision, revised 90 days |
| `12-build-order-and-budget.md` | Client vs admin versions, our own prospecting, budget |
| `13-signal-lab.md` | Creative signals tested against history; what works, what doesn't |
| `data-source-registry.md` | Every data source, coverage, access, cost, verification status |
| `feature-roadmap.md` | Features by status (planned/validated/in-dev/done) |
| `decision-log.md` | Decisions, alternatives, evidence |
