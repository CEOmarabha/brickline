# AI Lead Intelligence Platform & Marketing Agency — Project Plan

Planning and research workspace for a business that turns public records into sales opportunities for local businesses (starting with construction-related trades in the City of Chicago), paired with a marketing and sales agency.

This repo contains the plan, the evidence behind it, and the first pieces of the engine: a local warehouse of Chicago and Cook County records and historical backtests of lead formulas.

## Start here

1. `docs/00-strategic-assessment.md` — the summary and the latest decisions.
2. `docs/11-lead-generation-strategy.md` — which lead signals actually work (backtested), the formulas, the homeowner-trade decision, and the revised first 90 days.
3. `research/findings/backtests-2026-11-15.md` and `research/findings/chicago-signal-probe-2026-11-14.md` — the measurements.

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
| `docs/11-lead-generation-strategy.md` | Backtested lead formulas, homeowner-trade decision, revised 90 days |
| `docs/12-build-order-and-budget.md` | Client vs admin versions, our own prospecting, first-six-months budget |
| `docs/data-source-registry.md` | Data sources with coverage, cadence, access, verification status |
| `docs/feature-roadmap.md` | Features by status and justifying metric |
| `docs/decision-log.md` | Decisions, alternatives, evidence |

Evidence labels used throughout: **[V]** verified, **[V3]** third-party reported, **[E]** estimate, **[H]** hypothesis, **[S]** speculative.

## Client app (Brickline)

`web/` is the client-facing product: a Next.js app where a contractor picks a trade and neighborhoods and gets ranked leads (violations and investor purchases) with the evidence, historical chance of work, expected value, a drafted letter or email, and status tracking. It also has neighborhood trends, competitor share, and a commercial preview (pre-application projects and general contractors who rotate subs).

```bash
cd web
npm install
npm run dev          # http://localhost:4317
```

The app reads `web/data/snapshot.json`, produced by the engine. Lead statuses, notes and settings are stored in Postgres when `DATABASE_URL` is set, otherwise in an in-memory database that resets on restart. To refresh the data:

```bash
uv run python -m engine.warehouse sync && uv run python -m engine.warehouse build
uv run python -m engine.leads.snapshot     # rewrites web/data/snapshot.json
```

## Building the warehouse and running backtests

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/) and internet access. The first sync downloads ~850 MB of public CSVs into `data/` (git-ignored) and takes a few minutes; it resumes if interrupted.

```bash
uv sync
uv run python -m engine.warehouse sync     # permits, violations, Cook County sales, food licenses
uv run python -m engine.warehouse build    # normalized tables in data/warehouse.duckdb (~15 s)
uv run python research/backtests/run_backtests.py   # writes research/findings/backtests-<date>.md/.json
```

Our own prospect list (contractors to pitch): `uv run python -m engine.leads.prospects --trades porch masonry roofing` writes `data/prospects-<date>.csv`.

Code layout: `engine/collect` (Socrata bulk export), `engine/classify` (rules-based trade tagging), `engine/warehouse.py` (tables and join keys), `research/backtests` (signal tests), `research/probes` (quick live-data checks).

## Re-running the data probe

Requires Python 3.10+ and internet access; no third-party packages.

```bash
python3 research/probes/chicago_signal_probe.py            # permits: last 90 days; other signals: last 30
python3 research/probes/chicago_signal_probe.py --days 180 --signal-days 60
```

It writes `research/findings/chicago-signal-probe-<date>.md` (readable report) and `.json` (full numbers) using the City of Chicago Data Portal's public API. Runs in under a minute.
