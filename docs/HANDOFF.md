# Handoff — read this first if you are picking up the work

*Last updated 2026-11-15. Keep this file current: update "Current state" and "Next tasks" whenever a task lands.*

## The business in five lines

- Founder: khaled, Chicago-based, building mostly with AI tools, no existing industry contacts, a few thousand dollars of budget, wants real cash flow within a year.
- Product: **Brickline**, lead intelligence for Chicago contractors built on public records. Every lead shows evidence, a historical "chance of work", an expected value, and a drafted letter or email.
- Go-to-market: **Track 1 (cash flow)**: owner-facing trades (start with porch and masonry) get weekly trigger lists plus done-for-you mail; khaled runs pilots himself from client workspaces. **Track 2 (software asset)**: commercial subcontractor intelligence (GC "open door" scores, pre-application project predictions).
- Rules that never bend: numbers come from data, never guesses; confirmed vs inferred is explicit; humans approve all outreach; no autodialed/AI calls or texts; letters never imitate the City.
- Strategy docs: `docs/00-strategic-assessment.md` (top), `docs/11-lead-generation-strategy.md` (validated formulas), `docs/13-signal-lab.md` (creative signals), `docs/decision-log.md` (why).

## Repository map

| Path | What it is |
| --- | --- |
| `engine/collect/` | Socrata bulk export (`socrata.py`), NOAA storm events (`noaa.py`) |
| `engine/warehouse.py` | `sync` downloads raw CSV pages to `data/raw/` (gitignored); `build` creates `data/warehouse.duckdb` (~15 s) |
| `engine/classify/trades.py` | Regex trade flags for permits and violations (RE2 syntax: no lookarounds) |
| `engine/score/signals.py` | Shared definitions: `prepare_base` (temp tables `addr_pin`, `p`), parcel features, combination model |
| `engine/leads/snapshot.py` | Builds `web/data/snapshot.json` (the app's data): leads, areas, competitors, GC targets, pre-application projects |
| `engine/leads/prospects.py` | Our own prospect list: contractors to pitch → `data/prospects-<date>.csv` |
| `research/backtests/run_backtests.py` | Historical validation of core signals → `research/findings/backtests-<date>.md` |
| `research/signal_lab/lab.py` | Creative hypothesis tests + leaderboard → `research/findings/signal-lab-<date>.md` |
| `web/` | Next.js 16 client app (Brickline) |
| `scripts/refresh-data.sh` | Weekly refresh (sync → build → snapshot → prospects; `--backtest` re-runs lab and backtests) |

Warehouse tables: `permits`, `permit_parties` (role, name_key), `violations`, `sales`, `parcels` (owner, mailing), `food_licenses`, `community_areas` (with WKT geometry), `sr311`, `benchmarking`, `res_chars`, `storms`. Join keys: `pin10` (first 10 digits of the Cook County PIN) and `address_key` (normalized "NUMBER DIR STREET SUFFIX").

## Web app essentials (`web/`)

- **Next.js 16.4 with Cache Components.** Read `web/node_modules/next/dist/docs/` before using an API you're unsure of. Anything reading request data or the DB must sit inside `<Suspense>`; DB/identity reads call `connection()` (already done in `src/lib/workspace.ts`). Server actions refresh with `refresh()` from `next/cache`.
- **shadcn/ui "base-nova" style = Base UI, not Radix.** Use the `render` prop (not `asChild`); `Select` takes an `items` map so `SelectValue` shows labels; style links with `buttonVariants()` on `next/link`.
- **Data:** `src/lib/snapshot.ts` loads `data/snapshot.json` (types live there). Lead selection/sorting: `src/lib/lead-query.ts` (shared by list, CSV export, report, assistant). Expected value and close rates: `snapshot.ts` (`expectedValue`, `closeRateFor`) and `src/lib/outcomes.ts` (measured, calibrated rates after 10 decided leads).
- **DB:** Postgres via `DATABASE_URL` in production, in-memory PGlite locally (`src/lib/db.ts`). Migrations in `web/migrations/NNN_*.sql`, **additive only**, never edit a published one.
- **Identity:** `web/cursor/identity.ts` (never edit; regenerate with the `add-app-identity` tool). Workspace owner id is `<stage>:<sub>`; one owner can run many client workspaces (`workspace.owner_id`, `viewer_state.current_workspace`). Every server action and API route checks the viewer.
- **Assistant:** `src/lib/assistant.ts` (Messages API loop, model `claude-sonnet-5-5` unless `ASSISTANT_MODEL`), tools in `src/lib/assistant-tools.ts` (read-only), route `src/app/api/assistant/route.ts` (auth, Origin check, rate limit). `ANTHROPIC_API_KEY` is a bound app secret; quick answers work without it.
- **Turbopack alias** in `next.config.ts` maps `./identity.dev.js` → `./cursor/identity.dev.ts`; keep it.
- Dev server: `cd web && env -u DATABASE_URL npm run dev` → http://127.0.0.1:4317 (tmux session `brickline-dev`).
- Checks before committing: `npm run typecheck && npm run lint && env -u DATABASE_URL npm run build`.

## Python essentials

- `uv` at `~/.local/bin/uv` (`export PATH="$HOME/.local/bin:$PATH"`). Run modules from the repo root: `uv run python -m engine.leads.snapshot`.
- Lint: `uv run ruff check engine research && uv run ruff format engine research` (SQL-heavy modules are exempt from E501 in `pyproject.toml`).
- DuckDB quirks: lambdas use `lambda x: ...`; `QUALIFY` can't combine with `GROUP BY ALL`; break ties explicitly (`ORDER BY ..., id`) so results are deterministic; use `first(x ORDER BY ...)` over `arg_max` when ties matter.
- Verify determinism after changing research code: run twice and compare `md5sum` of the findings file.

## Data facts that bite

- Chicago permits publish **only issued** permits; trade subcontractors are already named on most big permits at issue.
- Cook County sales lag ~3 months; the parcel tax roll lags sales (owner/mailing may still be the seller; `same_entity` handles this in the snapshot).
- Only ~50% of pre-2024 permits carry a PIN; `prepare_base` fills parcels from addresses.
- Permits undercount real work (windows, HVAC swaps, small repairs are often unpermitted): every rate is a floor.
- Community areas for leads come from point-in-polygon (DuckDB `spatial` extension, installed at runtime).

## Current state (2026-11-15)

- Strategy and research docs complete (`docs/00`–`13`), decisions D-001…D-015.
- Validated signals (backtests): violations → permits (porch 15.3%/14×, masonry 10%/8×), investor purchases (30–38% any permit), GC open-door (5–6× separation), composite pre-application score (top 100 ≈ 26%, 56×), restaurant build-out → food license (~90 days ahead).
- Signal lab round 1 (`docs/13-signal-lab.md`): winners H07 (311 building complaint → citation, 32-day head start), H08 (porch inspection request, 11×), H09 (vacant complaint → sale, 2.5×), H13 (pre-1910 masonry, 2.9×), H01/H03 (solar/reroof neighbors ~2.2–2.4×); storms, basement water, lead kits, energy score, no-A/C failed.
- Productized signal-lab winners (snapshot kinds `complaint`, `porch_request`, `vacant`; masonry pre-1910 split on violation leads; `blocks.roofing` + `blocks.roofingModel`). Every probability and case count is computed in `engine/leads/snapshot.py` and cited in `snap.models` (`complaint`, `porchRequest`, `vacant`, `masonryAge`); 311 data starts mid-2018, so those models cover 2018 onward. Letters for these kinds never mention the 311 report.
- App (`web/`): dashboard + suggested moves, leads (filters, CSV/mail-merge export), lead detail (evidence, draft, status), neighborhoods, market, commercial preview, results (measured close rates), weekly report + print-ready letters, assistant, settings, client workspaces.
- Publish: proposed as "brickline", **awaiting khaled's confirmation** (recommend Private). After it's live, republish after each change.

## Next tasks (in order)

1. **Client logins not tied to Cursor** so pilots self-serve (security-sensitive: a public app must not expose `data/snapshot.json`, now ~8 MB; consider moving lead data behind authenticated routes or into the DB; magic-link email needs a provider secret).
2. **Automated weekly refresh** (scheduled job running `scripts/refresh-data.sh`, committing the snapshot, republishing).
3. **Contact enrichment** for company owners/investors (Apollo or similar; bind the API key as a secret; cache results; never fabricate).
4. **Signal lab round 2** (`docs/13-signal-lab.md` "Next ideas"); also block-level solar lists (H01) and adding the 311 lead types to `research/backtests` so they re-validate on refresh.

## Working agreements

- Commit each logical change with a descriptive message; push to `main` after checks pass.
- Don't create pull requests (new-project flow). Don't edit `web/cursor/identity.ts`.
- Report outcomes plainly; label estimates vs verified; prefer deleting a weak signal over shipping it.
