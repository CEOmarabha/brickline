# Deliverable 7 — MVP Recommendation

*v1, 2026-11-14. Labels: [V] verified, [E] estimate, [H] hypothesis.*

## The MVP in one sentence

**Every week, deliver 20–50 human-reviewed, source-linked opportunities from City of Chicago public data to 3–5 paying design partners in one buyer cluster, each with why it matters, who to contact and a drafted message, and log what happens next.**

The MVP is a *service backed by an engine*, not an app.

## First market: City of Chicago (not "Chicago metro")

| Why | Evidence |
| --- | --- |
| Free, daily, structured permit data with contractors named by trade and history since 2006 | [V] probe |
| Violations, business licenses, food inspections on the same API | [V] probe |
| ~84 major projects/week — enough for meaningful weekly reports without drowning | [V] probe |
| 627 GCs and 300–400 subs per trade active in 90 days — a large, local buyer pool | [V] probe |
| Suburbs: lagged (assessor) or fragmented (municipal portals, FOIA) | [V]/[V3] |

Expand to suburbs only by buying data (verify Shovels coverage on its free tier first) and only after the Chicago report retains customers.

## First buyer: choose by week 4 among three candidates

All three run on the **same pipeline** (permits + contacts + entity resolution + project clustering), so engineering work is not wasted whichever wins.

| Candidate | Product framing | Why it might win | Why it might lose |
| --- | --- | --- | --- |
| **A. Commercial subcontractors** (electrical, HVAC, plumbing, concrete/masonry, fire protection) | GC-relationship and market intelligence: which GCs build in your size range, who they use, who rotates subs, new GCs entering; competitor share; open masonry/concrete scopes; pre-permit items where found | Largest buyer pool; high job values; your original thesis; data is unique once entities are resolved | Value is indirect (relationships, not jobs); harder to attribute; subs may be skeptical of "intel" vs "leads" |
| **B. Suppliers, distributors, equipment rental** | Weekly list of contractors starting projects in your territory and category, with value, scope, location, contact and a reason to call | Buyer is named on the record; these firms have reps and sales budgets; easy to attribute (new account opened) | Fewer firms; reps may already know their contractors; national incumbents sell to them |
| **C. Post-construction & new-business services** (commercial cleaning, security/low-voltage, pest, food distribution) | New buildings nearing completion, new businesses and restaurants about to open, with contact | Signal is genuinely early (vendors not named); recurring revenue buyers | Lower deal values; FieldClients targets this at $99–$499/mo |

**My prior:** B then A for willingness to pay; C for the cleanest "lead" story. Let the interviews decide (decision rule in `08-90-day-plan.md`). If you have personal access to one of these groups, that likely trumps the scores.

## First data sources (all free, all verified)

| Source | Dataset | Use |
| --- | --- | --- |
| Chicago Building Permits | `ydr8-5enu` | Projects, values, stages, parties (owner/GC/subs/architect) |
| Chicago Building Violations | `22u3-xenr` | Compelled-demand signals; owner distress |
| Chicago Business Licenses | `r5kz-chrr` | New businesses (Cluster C) |
| Chicago Food Inspections | `4ijn-s7e5` | Restaurants about to open; failed inspections (pest) |
| Cook County Assessor Permits | `6yjf-dfxs` | Parcel permit history (context, not freshness) |
| Cook County Assessor Parcel Sales | `wvhk-k5uv` | Ownership changes (lagged) |
| Apollo (paid, small plan) | — | Contacts for GCs/suppliers; measure match rate |

Pre-permit sources (zoning, plan commission, public bids) are researched in parallel and added manually to pilot reports when found; automated only if pilots value them.

## Smallest useful feature set

### Must have (MVP)

1. Incremental Chicago permit collector + immutable raw archive + daily health check.
2. Normalization and **project clustering** (PIN + address + time window).
3. **Entity resolution v0** for contractors (normalized names, fuzzy match, manual review list) — needed for any relationship view.
4. Rules-based trade tagging with `confirmed` vs `inferred` + LLM fallback for ambiguous text, cached.
5. Buyer-specific views (as SQL + report templates):
   - A: GC profiles (volume, size band, sub partners, rotation rate), competitor share, open-scope projects.
   - B: contractors starting jobs in territory/category this week.
   - C: projects nearing completion; new licenses; license inspections.
6. Simple transparent score + tier (Call today / This week / Monitor / Low) with a one-line reason.
7. Contact lookup (Apollo or manual) with source and confidence; never guessed.
8. Drafted outreach per item (human-approved), CAN-SPAM compliant.
9. Weekly report generator (Google Sheet + PDF/email) with source links.
10. Feedback capture per item (relevant / not relevant / wrong trade / already awarded / bad contact / contacted / meeting / won / lost) — a column in the sheet or a CRM field.
11. Golden set (200 labeled permits) + metric tracking per module.

### Explicitly not in the MVP

Dashboard; self-serve signup; customer-facing chatbot; predictive replacement models; suburban collectors; automated sending; mobile; billing system (invoice manually).

## MVP success criteria (measured by day 90)

| Metric | Target | Why |
| --- | --- | --- |
| Paying pilots | ≥ 3 | Willingness to pay is the real test |
| Items rated relevant | ≥ 40% | Below this, reports are noise |
| Meetings attributable to report | ≥ 1 per pilot per month | Value beyond curiosity |
| Pilot renewals at month 3 | ≥ 2 of 3 | Retention |
| Contact match rate (named decision-maker + verified email) | ≥ 60% of delivered items | Actionability |
| Review time per item | ≤ 3 minutes and falling | Unit economics |
| Data freshness | Chicago records in report ≤ 48 hours after publication | Timeliness |
| Entity-resolution precision on labeled pairs | ≥ 95% | Avoid embarrassing mismatches |

Miss two or more → change buyer or framing before adding features.
