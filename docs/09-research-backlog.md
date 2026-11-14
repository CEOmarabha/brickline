# Deliverable 9 — Research Backlog

*v1, 2026-11-14. Ranked by priority = impact × urgency ÷ effort. Status: Open / In progress / Answered (with link) / Parked. Update this file whenever research changes an assumption, and log decisions in `decision-log.md`.*

| # | Question | Priority | Impact | Difficulty | Status | How to answer |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Which buyer (A commercial subs / B suppliers & rental / C post-construction & new-business services) will pay ≥ $500/mo for the weekly report? | P0 | Fatal if wrong | Medium | Open | 20 interviews with real samples (`08-90-day-plan.md`) |
| 2 | Do commercial subs value GC-relationship intelligence as much as "leads"? | P0 | High | Medium | Open | Show a GC profile + relationship map in interviews |
| 3 | Is there a reliable Chicago **pre-permit** source (zoning amendments, PDs, plan commission, ZBA, plan-review status)? What's the lead time and format? | P0 | High for commercial trades | Medium–high | Open | Review City Clerk legislative system, Plan Commission/ZBA agendas; FOIA for permit applications in review; test Shovels Decisions coverage for Chicago |
| 4 | Contact match rate for contractors named on permits (Apollo vs Shovels vs website lookup) | P0 | High | Low | Open | Run 200 named contractors through each; measure verified email + named decision-maker |
| 5 | What review time per item is achievable, and how much research is shared across customers? | P1 | High (unit economics) | Low | Open | Time-track the first 4 weekly reports |
| 6 | Are Chicago permit names mostly the legal entity, DBA, or truncated variants, and what ER precision can rules + fuzzy matching reach? | P1 | High | Medium | In progress — truncation and spelling variants confirmed ([probe](../research/findings/chicago-signal-probe-2026-11-14.md)) | Label 300 name pairs; measure |
| 7 | How understated is `reported_cost`? Is it usable for value bands and trade-value estimates? | P1 | Medium | Medium | Open | Compare against assessor amounts, public project announcements; ask pilots |
| 8 | How often do GCs rotate subs (the "open door" signal), by GC size? | P1 | Medium–high (A) | Low | Open | Compute from 2019–2026 permit history |
| 9 | Do suppliers/rental reps already know about projects before permits issue? | P1 | High (B) | Low | Open | Interviews |
| 10 | Shovels coverage and freshness for collar counties (DuPage, Lake, Will, Kane, McHenry) | P2 | Medium | Low | Open | Free-tier queries; compare to known municipal data |
| 11 | Should the agency standardize on HighLevel (client portal, white-label) or HubSpot? | P2 | Medium | Low | Open | Depends on agency plans; trial both with one pilot |
| 12 | Illinois privacy / data-broker obligations if storing consumer (homeowner) data | P2 | Medium (residential) | Low | Open | Counsel review; only matters if residential cluster is pursued |
| 13 | Messaging norms for violation-based outreach (avoid looking like a government notice; tone) | P2 | Medium | Low | Open | Draft templates; counsel review; small direct-mail test |
| 14 | Which pre-opening signals are earliest for restaurants (renovation permit text vs license application vs license inspection)? | P2 | Medium (C) | Low | Open | Join permits ↔ licenses ↔ inspections by address over 2 years |
| 15 | Can permit history + sales predict commercial HVAC/roof replacement with useful precision? | P3 | Medium | High | Parked until outcomes exist | Requires outcome labels; avoid presenting as fact |
| 16 | What's a defensible moat beyond data access? | P1 | High | — | Partially answered: entity graph + pre-permit collection + outcome data + done-for-you service (`00-strategic-assessment.md` §3.2) | Validate with pilots |
| 17 | Agency package pricing sustainability with real time-tracking | P2 | Medium | Low | Open | Time-track first agency client |
| 18 | Flat vs hybrid ad-management pricing acceptance | P3 | Low–medium | Low | Proposed hybrid (`06-business-model.md`) | Test with first prospects |
| 19 | What can AI coding agents reliably build here? | P2 | Medium | Low | Open | Expect: collectors, normalizers, SQL views, report generators, integrations → good; entity resolution thresholds, scoring judgments, compliance → need human review |
| 20 | Security, privacy and customer-data handling for CRM connections | P2 | Medium | Medium | Open | Least-privilege OAuth scopes, tenant RLS, audit log; formal review before Growth stage |

## Assumptions register (things the plan currently assumes)

| Assumption | Label | What would falsify it |
| --- | --- | --- |
| Chicago data stays free and daily | [V] today | Portal policy change |
| Commercial subs are selected before permit issue | [V] data + sources | — |
| Suppliers/rental will pay for contractor start signals | [H] | <3 of 6 interviewees would act on sample rows |
| Human review can fall below 3 min/item | [H] | Time tracking |
| AI inference cost is negligible at city scale | [E] | Multi-metro processing or heavy agent use |
| Agency packages reach ≥ 45% gross margin | [E] | Time tracking on first clients |
