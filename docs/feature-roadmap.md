# Feature Roadmap

*v1, 2026-11-14. Status values: **Done**, **In development**, **Validated** (evidence says build it), **Planned** (in the 90-day plan), **Proposed** (needs evidence), **Deferred**. Each feature lists the metric that justifies it.*

| Feature | Module | Status | Justifying metric | Notes |
| --- | --- | --- | --- | --- |
| Chicago signal probe (permits, violations, licenses, food inspections) | Research | **Done** | Answers timing/volume/coverage questions | `research/probes/chicago_signal_probe.py` |
| Incremental Chicago permit collector + raw archive | M1 | Planned (wk 1) | Freshness ≤ 48h; completeness ≥ 99% | |
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
| Internal AI assistant (read-only tools) | Assistant | Planned (wk 11) | Research time per item | Internal only |
| GC relationship graph view | M3/M7 | Proposed | Interview value for buyer A | High priority if A is chosen |
| Thin web app (opportunity list + feedback buttons) | UI | Deferred until day-90 gate | Customers retained ≥ 3 months | |
| Customer-facing AI advisor | Assistant | Deferred | Requires profiles + CRM outcomes | |
| Predictive replacement scoring | C | Deferred | Requires outcome labels | |
| Suburban coverage | M1 | Deferred | Retained Chicago customers asking for it | Buy data first |
| Self-serve signup and billing | UI | Deferred | ≥ 80% automated report | |
| Industry dashboards | UI | Deferred | Validated workflows | Config-driven |
| Unified agency attribution view | Agency | Proposed | Agency + intelligence client exists | |
