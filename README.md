# AI Lead Intelligence Platform & Marketing Agency — Project Plan

Planning and research workspace for a business that turns public records into sales opportunities for local businesses (starting with construction-related trades in the City of Chicago), paired with a marketing and sales agency.

This repo contains the plan, the evidence behind it, and the first pieces of the engine: a local warehouse of Chicago and Cook County records and historical backtests of lead formulas.

## Start here

0. `docs/HANDOFF.md` — how everything fits together, conventions, current state, next tasks (start here if you are continuing the work).
1. `docs/00-strategic-assessment.md` — the summary and the latest decisions.
2. `docs/11-lead-generation-strategy.md` — which lead signals actually work (backtested), the formulas, the homeowner-trade decision, and the revised first 90 days.
3. `research/findings/backtests-2026-11-16.md`, `research/findings/signal-lab-2026-11-16.md` and `research/findings/chicago-signal-probe-2026-11-14.md` — the measurements (each run writes a new dated file; use the newest).

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
| `docs/13-signal-lab.md` | Creative lead ideas tested against history: results, failures, next ideas |
| `docs/14-sales-playbook.md` | How to sell Brickline by cold outreach: ideal first customers, pilot offer, email and phone scripts, compliance, 30-day plan (pairs with the app's `/prospects` pages) |
| `docs/15-intelligence-engine.md` | Engine assessment, case studies, the 24-equation strategy matrix, source verification and roadmap |
| `docs/data-source-registry.md` | Data sources with coverage, cadence, access, verification status |
| `docs/feature-roadmap.md` | Features by status and justifying metric |
| `docs/decision-log.md` | Decisions, alternatives, evidence |

Evidence labels used throughout: **[V]** verified, **[V3]** third-party reported, **[E]** estimate, **[H]** hypothesis, **[S]** speculative.

## Client app (Brickline)

`web/` is the client-facing product: a Next.js app where a contractor picks a trade and neighborhoods and gets ranked leads (building violations, 311 building complaints, porch inspection requests, vacant buildings, and investor purchases, plus roofing block lists) with the evidence, historical chance of work, expected value, a drafted letter or email, and status tracking. It also has neighborhood trends, competitor share, and a commercial preview (pre-application projects and general contractors who rotate subs).

```bash
cd web
npm install
npm run dev          # http://localhost:4317
```

The app reads `web/data/snapshot.json`, `prospects.json`, `contacts.json` and `pest.json`, produced by the engine. Lead statuses, notes and settings are stored in Postgres when `DATABASE_URL` is set, otherwise in an in-memory database that resets on restart. Each signed-in user can run several workspaces (one per client they manage).

The **Assistant** answers questions about leads, neighborhoods, competitors and results by calling read-only tools over the same data (Claude via `ANTHROPIC_API_KEY`, model overridable with `ASSISTANT_MODEL`); without a key, its quick questions still answer directly from the data.

Sales kit: **Prospects** (`/prospects`) lists the contractors to pitch (from `web/data/prospects.json`, written by `engine/leads/prospects.py`; free contact suggestions come from `web/data/contacts.json`, written by `engine/enrich/contacts.py`), and each one has a printable one-page teaser plus a cold-email draft, computed from the same snapshot. See `docs/14-sales-playbook.md`.

Weekly operations: **Leads** exports a mail-merge CSV; **Weekly report** prints a client summary and one-letter-per-page mailings; **Results** turns won/lost leads into measured close rates that replace the default assumptions after 10 decided leads.

To refresh the data (several minutes, mostly downloads; the contact step adds about 2 minutes when the website cache is cold):

```bash
scripts/refresh-data.sh          # add --backtest to also re-run the signal lab, the backtests and the zoning parse check
```

It prints `git status` for the tracked outputs: commit `web/data/*.json` (snapshot, pest, prospects, contacts), `research/findings/` and `research/archive/manifest.json`, then republish.

## Building the warehouse and running backtests

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/) and internet access. The first sync downloads about 2 GB of public CSVs and Parquet into `data/raw/` (git-ignored) and takes several minutes; it resumes if interrupted.

```bash
uv sync
uv run python -m engine.warehouse sync     # City and County datasets (Socrata), NOAA storms and radar hail, HMDA, Overture places, City Clerk zoning ordinances
uv run python -m engine.warehouse build    # normalized tables in data/warehouse.duckdb (about 30 s)
uv run python research/backtests/run_backtests.py   # writes research/findings/backtests-<date>.md/.json (~10 s)
```

Signal lab (test new lead ideas, about 40 s for all 37): `uv run python research/signal_lab/lab.py` writes `research/findings/signal-lab-<date>.md/.json`; name hypotheses (`lab.py H29 H33`) to run a few and write only `*.partial.*` files. Dates are UTC today; `SIGNAL_LAB_DATE` and `BACKTEST_DATE` override them.

Our own prospect list (contractors to pitch): `uv run python -m engine.leads.prospects --trades porch masonry roofing` writes `data/prospects-<date>.csv` and `web/data/prospects.json`.

Code layout:

| Path | Contents |
| --- | --- |
| `engine/collect/` | Source collectors: `socrata.py` (bulk CSV export), `noaa.py`, `swdi.py`, `hmda.py`, `overture.py`, `clerk.py` (City Clerk zoning ordinances), `hfsrb.py` (certificate-of-need projects), `archive.py` (weekly snapshots of current-state-only sources), `http.py` (shared GET with retries) |
| `engine/classify/` | Rules-based trade tagging (regex flags for permits and violations) |
| `engine/warehouse.py`, `engine/db.py` | `sync` and `build` for `data/warehouse.duckdb` (tables and join keys); where the warehouse lives and how code opens it |
| `engine/score/` | Shared definitions: `signals.py` (parcel features, combination model), `food.py` (restaurant-inspection signals, H23-H26), `licenses.py` (business-license and big-permit signals, H29-H33) |
| `engine/leads/` | `snapshot.py` (app data), `pest.py` (pest-control pilot list), `prospects.py` (contractors to pitch) |
| `engine/enrich/` | Free contact enrichment: `contacts.py`, `names.py`, `web.py` |
| `research/backtests/`, `research/signal_lab/` | Historical validation (`run_backtests.py`) and creative hypothesis tests (`lab.py`, H01-H37) |
| `research/probes/` | Live-data probes: `chicago_signal_probe.py`, `source_check.py` (51 candidate sources), `clerk_parse_check.py` |
| `research/findings/`, `research/archive/` | Dated outputs of the above; the weekly source archive manifest |
| `scripts/refresh-data.sh` | The weekly refresh |

## Re-running the data probe

Requires Python 3.10+ and internet access; no third-party packages.

```bash
python3 research/probes/chicago_signal_probe.py            # permits: last 90 days; other signals: last 30
python3 research/probes/chicago_signal_probe.py --days 180 --signal-days 60
```

It writes `research/findings/chicago-signal-probe-<date>.md` (readable report) and `.json` (full numbers) using the City of Chicago Data Portal's public API. Runs in under a minute.
