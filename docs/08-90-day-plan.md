# Deliverable 8 — 90-Day Action Plan (and Execution Roadmap)

*v1, 2026-11-14. Two tracks run in parallel from day 1: **Customer** (discovery → pilots → pricing) and **Engine** (pipeline → intelligence → delivery). Progress is gated by evidence, not by finished features.*

Assumed resources [E] — adjust after answering the questions in `00-strategic-assessment.md` §5:

- Founder: ~50% customer discovery/sales, ~50% research and report review.
- One engineer (or founder + AI coding agents): engine.
- Cash: ~$1–3k over 90 days excluding labor (infra $25–150/mo, Apollo ~$49–79/mo, optional Shovels free tier, direct mail tests, pilot incentives).

---

## Days 1–30 — Learn and build the pipeline

### Customer track

| Week | Work | Output |
| --- | --- | --- |
| 1 | Build target lists for buyer candidates A/B/C from the permit data itself (e.g. top-volume subs, supply houses, rental yards near active projects, commercial cleaners). Write the interview guide (below). | 60–90 named prospects; guide |
| 1–3 | **20 interviews** (≈8 A, 6 B, 6 C). In person where possible. Show a *real* sample: a one-page GC profile (A), a "contractors starting jobs near your branch" list (B), a new-building/new-business list (C). | Notes in a shared sheet; scored pains; WTP answers |
| 3 | Pick 3–5 design-partner candidates; offer pilot terms (discounted or free month 1 for weekly feedback + outcome data). | Signed pilot agreements or LOIs |
| 4 | **Decision: first buyer** (rule below). | Decision-log entry |

**Interview guide (core questions):** How do you find new work/accounts today? What did the last three wins come from? How do you get on GC bid lists (A) / open contractor accounts (B) / find new buildings (C)? What do you pay for today (Dodge, ConstructConnect, lists, ads, reps)? What's wrong with it? Walk me through what you'd do with this sample row. Which rows would you act on this week, and why not the others? What would make this worth $500/month? $1,000? Who else in your company would use it?

**Decision rule (week 4):** pick the buyer with the highest count of interviewees who (1) would act on ≥30% of sample rows, (2) state a price ≥ $500/month without prompting or accept it when asked, and (3) agree to a pilot. Ties → the buyer you can reach most easily.

### Engine track

| Week | Work | Output / metric |
| --- | --- | --- |
| 1 | Repo skeleton (`engine/`), Postgres + PostGIS, Chicago permit collector (incremental), raw archive, daily health email | Freshness lag, completeness vs portal count |
| 2 | Normalization; project clustering v0; contractor name normalization + fuzzy matching v0 with review export | Clustering spot-check on 100 projects; ER precision on 300 labeled pairs |
| 3 | Rules-based trade tagging (`confirmed`/`inferred`); golden set of 200 labeled major permits; eval runner | Per-trade precision/recall baseline |
| 4 | Buyer-specific views (A/B/C) as SQL + sample report generator; Apollo match-rate test on 200 contractors | Contact match rate; sample reports used in interviews |

**Gate at day 30:** ≥15 interviews done; first buyer chosen; ≥3 pilot commitments; pipeline producing a weekly report with ≥95% ER precision on the labeled set. If fewer than 2 pilots commit → rerun discovery with the next buyer candidate before building more.

---

## Days 31–60 — Pilot delivery

### Customer track

- Weekly report to each pilot (same weekday), 20–50 items, plus a 15-minute call every two weeks.
- Capture per-item feedback and outcomes in the CRM (HubSpot free or HighLevel sub-account).
- Track: relevance rate, items acted on, meetings, quotes, wins, time from report to first touch.
- Continue 1–2 interviews/week with the runner-up buyer (cheap insurance).

### Engine track

| Week | Work | Metric |
| --- | --- | --- |
| 5 | Scoring v0 (transparent weights, tiers, one-line reasons); tenant profiles for pilots | Acceptance rate by tier |
| 6 | Drafted outreach (LLM, grounded on project facts, CAN-SPAM footer, human approval) | Draft edit rate; time per item |
| 7 | CRM sync (opportunities, contacts, tasks); feedback ingestion | Feedback coverage ≥ 70% of items |
| 8 | Second signal pipeline relevant to the chosen buyer (e.g. licenses + inspections for C; demolition/new-construction early-stage view for A/B); pre-permit research spike (zoning/PD/plan commission; Shovels Decisions free tier) | Items from new signals rated relevant |

**Gate at day 60:** relevance ≥ 30% and rising; ≥1 attributable meeting across pilots; review time per item ≤ 4 min. If relevance is flat below 25% after 4 reports → change framing (e.g. from leads to GC intel) or buyer.

---

## Days 61–90 — Prove value and price

### Customer track

- Convert pilots to paid standard pricing (test $750 vs $1,000 vs $1,500 anchors across new prospects).
- Collect 2–3 written case notes (what was found, what happened).
- Recruit the next 3–5 customers in the same cluster (referrals from pilots, trade associations, supply houses).
- If agency services are in scope: offer one bundled package to one pilot (ads + GBP + intelligence) to test the combined offer and attribution.

### Engine track

| Week | Work | Metric |
| --- | --- | --- |
| 9 | Outcome-based review of scoring weights (offline proposal → eval → ship) | Meeting rate per 100 items by tier |
| 10 | Daily "call today" alert email; data health monitoring with alerts | On-time delivery 100% |
| 11 | Internal AI assistant (read-only tools over SQL views) to speed research and QA | Time per item; queries answered correctly on a 30-question test |
| 12 | Write-up: metrics vs targets, unit economics from time tracking, go/no-go and next-quarter plan | Decision-log entries |

**Gate at day 90 (from `07-mvp-recommendation.md`):** ≥3 paying, ≥40% relevance, ≥1 meeting/pilot/month, ≥2 of 3 renew. Meet them → build Growth-stage pieces (thin web app with feedback buttons, second cluster). Miss two → pivot buyer/framing, don't add features.

---

## Validation framework (ongoing)

| Method | When | Purpose |
| --- | --- | --- |
| Customer interviews | Weeks 1–4, then 1–2/week | Pains, current spend, WTP |
| Real-data samples in interviews | Weeks 1–4 | Reactions to actual rows, not concepts |
| Landing page + small ad test per buyer type | Week 3–6 (optional, ~$300) | Message resonance; inbound demo requests |
| Paid pilots | Weeks 5–12 | WTP + outcome data |
| Lead-quality audit | Every report | Relevance, duplicates, stale items, bad contacts |
| Retention test | Month 3 renewal | The only metric that really matters |

## Execution roadmap beyond 90 days (conditional)

| Phase (from the master brief) | Starts when | Notes |
| --- | --- | --- |
| 1 Research & validation | Now | Days 1–30 |
| 2 Data infrastructure (one city) | Now | Days 1–30, deliberately narrow |
| 3 Industry-specific intelligence | Day 30 | For the chosen buyer only |
| 4 CRM & sales automation | Day 45 | Integration, human-approved drafts |
| 5 Personalized dashboards | After day-90 gate passes | Thin app first; configuration-driven |
| 6 Agency integration | Opportunistically, or after gate | Attribution view across inbound/outbound |
| 7 Commercial launch | After 5+ retained customers | Pricing from pilot data |
| 8 Expansion | After unit economics are known | Second cluster, then suburbs (buy data), then second metro |
