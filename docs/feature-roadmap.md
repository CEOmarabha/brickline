# Feature Roadmap

*v1, 2026-11-14. Status values: **Done**, **In development**, **Validated** (evidence says build it), **Planned** (in the 90-day plan), **Proposed** (needs evidence), **Deferred**. Each feature lists the metric that justifies it.*

| Feature | Module | Status | Justifying metric | Notes |
| --- | --- | --- | --- | --- |
| Chicago signal probe (permits, violations, licenses, food inspections) | Research | **Done** | Answers timing/volume/coverage questions | `research/probes/chicago_signal_probe.py` |
| Bulk warehouse: permits, parties, violations, Cook County sales, food licenses (DuckDB) | M1–M2 | **Done** | Rebuild in ~15 s; enables backtests | `engine/warehouse.py` |
| Rules-based trade tagging v0 (permits + violations) | M4 | **Done** (v0) | Needs golden-set precision/recall | `engine/classify/trades.py` |
| Historical backtests of lead signals (BT0–BT6) | Research | **Done** | Validated 5 signals, rejected 1 | `research/backtests/run_backtests.py` |
| GC open-door score | M5 | **Validated** | 5–6x separation out of sample | Productize for Track 2 |
| Composite pre-application parcel score | M5 | **Validated** | 56x base at top 100/half-year | Productize for Track 2 |
| Weekly trigger lists (investor purchases, violations) | M7 | **Done** | Pilot reply/appointment rates | Client app, mail-merge CSV, print-ready letters, weekly report |
| 311 lead types: building complaints (cited weeks later), porch inspection requests, vacant-building reports | App / engine | **Done** | Historical rates computed in each snapshot (complaint → citation, request → porch permit, report → sale) | Signal lab H07/H08/H09; time-adjusted chance of work per trade |
| Masonry building-age split (walls built before 1910) on violation leads, Year built / Exterior walls evidence | Engine | **Done** | Rate computed per age segment in the snapshot | Signal lab H13 |
| Roofing block targeting (blocks with 2+ recent re-roofs) | App | **Done** | Neighbor lift computed in the snapshot | Signal lab H03; shown on Neighborhoods for roofing workspaces |
| Block-level solar target lists | App | Proposed | Signal lab H01 (2.4× for 2+ solar neighbors) | Confounded by income and canvassing |
| Client workspaces (one owner, many clients) | App | **Done** | Pilots run concurrently | Switcher in sidebar |
| Measured close rates replace assumptions | M8 | **Done** | Calibration vs expected jobs | After 10 decided leads per owner type |
| Contractor directory by trade from permits | M3 | Planned (wk 1–2) | Our own customer acquisition | Track 1 |
| Incremental Chicago permit collector + raw archive | M1 | Planned (wk 1) | Freshness ≤ 48h; completeness ≥ 99% | Daily updates on top of the bulk warehouse |
| Daily data health email | M1 | Planned (wk 1) | Zero silent failures | |
| Normalization (permits) | M2 | Planned (wk 2) | Parse success ≥ 99% | |
| Project clustering | M3 | Planned (wk 2) | Spot-check precision ≥ 90% | |
| Contractor entity resolution v0 + review export | M3 | Planned (wk 2) | Precision ≥ 95% on labeled pairs | Truncation/spelling issues confirmed |
| Rules-based trade tagging (confirmed vs inferred) | M4 | Planned (wk 3) | Per-trade precision/recall on golden set | |
| Golden set (200 permits) + eval runner | Eval | Planned (wk 3) | Regression protection | |
| Buyer-specific views (A/B/C) + sample reports | M7 | Planned (wk 4) | Interview reactions | |
| Apollo contact match test | M6 | Planned (wk 4) | Match rate ≥ 60% | |
| Scoring v0 with tiers and reasons | M5 | Planned (wk 5) | Acceptance by tier | |
| Drafted outreach (human-approved) | E | Planned (wk 6) | Draft edit rate; replies | |
| CRM sync + feedback capture | G / M8 | Planned (wk 7) | Feedback coverage ≥ 70% | HubSpot or HighLevel |
| Second signal pipeline (per chosen buyer) | M1–M4 | Planned (wk 8) | Relevance of new-signal items | |
| Pre-permit research spike | Research | Planned (wk 8) | Days earlier than permit | |
| Daily "call today" alert | M7 | Planned (wk 10) | Time to first touch | |
| AI assistant with read-only tools over leads, areas, competitors, pipeline, results | Assistant | **Done** (v1) | Questions answered from data; time per item | Needs ANTHROPIC_API_KEY; quick answers work without it |
| GC relationship graph view | M3/M7 | Proposed | Interview value for buyer A | High priority if A is chosen |
| Thin web app (opportunity list + feedback buttons) | UI | Deferred until day-90 gate | Customers retained ≥ 3 months | |
| Client logins not tied to Cursor | App | Planned | Pilots self-serve | Next build step |
| Predictive replacement scoring | C | Deferred | Requires outcome labels | |
| Suburban coverage | M1 | Deferred | Retained Chicago customers asking for it | Buy data first |
| Self-serve signup and billing | UI | Deferred | ≥ 80% automated report | |
| Industry dashboards | UI | Deferred | Validated workflows | Config-driven |
| Unified agency attribution view | Agency | Proposed | Agency + intelligence client exists | |
