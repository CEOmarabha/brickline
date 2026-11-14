# AI Lead Intelligence Platform & Marketing Agency — Project Plan

Planning and research workspace for a business that turns public records into sales opportunities for local businesses (starting with construction-related trades in the City of Chicago), paired with a marketing and sales agency.

This repo currently contains **the plan and the evidence behind it**, not the product. The engine will be built here once the open questions in `docs/00-strategic-assessment.md` §5 are answered.

## Start here

1. `docs/00-strategic-assessment.md` — the summary: what the data says, where the original plan should change, the recommendation, and questions for the founder.
2. `research/findings/chicago-signal-probe-2026-11-14.md` — live measurements from Chicago's open data that the plan relies on.
3. `docs/07-mvp-recommendation.md` and `docs/08-90-day-plan.md` — what to build and do first.

## Documents

| File | Contents |
| --- | --- |
| `docs/00-strategic-assessment.md` | Strategic overview, key disagreements with the brief, recommendation, questions |
| `docs/01-product-vision.md` | Deliverable 1 — product vision |
| `docs/02-industry-opportunity-matrix.md` | Deliverable 2 — 35 industries scored and clustered |
| `docs/03-competitive-landscape.md` | Deliverable 3 — competitors, prices, gaps, partners |
| `docs/04-feasibility-assessment.md` | Deliverable 4 — data, technical, legal, cost feasibility |
| `docs/05-technical-architecture.md` | Deliverable 5 — engine modules, data model, evaluation, AI assistant, Lean/Growth/Scale |
| `docs/06-business-model.md` | Deliverable 6 — pricing, unit economics, agency service catalog |
| `docs/07-mvp-recommendation.md` | Deliverable 7 — first market, buyer, sources, feature set, success criteria |
| `docs/08-90-day-plan.md` | Deliverable 8 — 90-day plan, gates, execution roadmap |
| `docs/09-research-backlog.md` | Deliverable 9 — ranked open questions and assumptions |
| `docs/10-additional-opportunities.md` | Deliverable 10 — further opportunities and advantages |
| `docs/data-source-registry.md` | Data sources with coverage, cadence, access, verification status |
| `docs/feature-roadmap.md` | Features by status and justifying metric |
| `docs/decision-log.md` | Decisions, alternatives, evidence |

Evidence labels used throughout: **[V]** verified, **[V3]** third-party reported, **[E]** estimate, **[H]** hypothesis, **[S]** speculative.

## Re-running the data probe

Requires Python 3.10+ and internet access; no third-party packages.

```bash
python3 research/probes/chicago_signal_probe.py            # permits: last 90 days; other signals: last 30
python3 research/probes/chicago_signal_probe.py --days 180 --signal-days 60
```

It writes `research/findings/chicago-signal-probe-<date>.md` (readable report) and `.json` (full numbers) using the City of Chicago Data Portal's public API. Runs in under a minute.
