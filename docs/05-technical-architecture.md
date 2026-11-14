# Deliverable 5 — Technical Architecture

*v1, 2026-11-14. Backend-first. The engine is a standalone, API-accessible system; every interface (report, CRM sync, email briefing, assistant, dashboard) is a consumer of it.*

## 1. Design principles

1. **Separate stages, each independently testable:** ingest → normalize → resolve → classify → score → deliver → learn.
2. **Raw is immutable.** Every source payload is stored as fetched, hashed and timestamped. Everything downstream can be rebuilt.
3. **Provenance on every field.** Each derived fact points to the raw record(s) and the rule/model version that produced it.
4. **Confirmed vs inferred is a column**, not prose: `assertion = confirmed | inferred | unknown`, plus `confidence`.
5. **Deterministic first, AI where it measurably helps.** Dates, addresses, dedupe, filters → code. Ambiguous descriptions, drafting, explanations → LLM, cached by input hash.
6. **Incremental by default.** Process only new/changed records (watermark on source `updated_at`/issue date + content hash).
7. **Evaluation before features.** Each module ships with metrics and a golden-set test; changes that regress the golden set don't merge.
8. **Tenant isolation from day one** in the data model, even while there's one internal user.

## 2. Pipeline and modules

```text
            ┌────────────── Sources ───────────────┐
            │ Chicago permits · violations ·        │
            │ licenses · food inspections ·         │
            │ Cook County assessor · (later) zoning,│
            │ bids, Shovels, contacts               │
            └──────────────────┬────────────────────┘
                               ▼
M1 Collect      fetchers per source → raw_record (immutable, hashed)
                               ▼
M2 Normalize    source adapters → permit / violation / license / inspection (versioned)
                               ▼
M3 Resolve      project clustering (PIN + address + time) · party entity resolution
                               ▼
M4 Classify     trade relevance · project type · stage · value band · assertion/confidence
                               ▼
M5 Score        tenant profile × signal → opportunity (score, tier, explanation, evidence)
                               ▼
M6 Enrich       decision-maker + contact (licensed providers) with provenance & confidence
                               ▼
M7 Deliver      weekly report (CSV/Sheets/PDF) · CRM sync · briefing email · API
                               ▼
M8 Learn        feedback + outcomes → metrics → proposed rule/weight changes → eval → deploy
```

| Module | Inputs → outputs | Key metrics |
| --- | --- | --- |
| M1 Collect | Source API → `raw_record` | Completeness vs source count; freshness lag (source time → ingested); failures/retries; schema drift alerts |
| M2 Normalize | `raw_record` → typed records | Parse success rate; null rates per field; duplicate rate |
| M3 Resolve | Records → `project`, `party`, `role` | Clustering precision; entity-resolution precision/recall on labeled pairs; review-queue size |
| M4 Classify | Project text/fields → trade tags, stage | Precision/recall per trade on golden set; % handled by rules vs LLM; cost per 1k records |
| M5 Score | Tags + tenant profile → opportunities | Customer acceptance rate by tier; "Call today" precision; rank correlation with outcomes |
| M6 Enrich | Party → contacts | Match rate; bounce rate; cost per verified contact; % with named decision-maker |
| M7 Deliver | Opportunities → artifacts | On-time delivery; items per report; time-to-review per item |
| M8 Learn | Feedback, outcomes | Feedback coverage; meetings and wins per 100 items; cost per accepted lead |

## 3. Data model (core tables)

```text
source(id, name, url, jurisdiction, cadence, access_method, terms_url, reliability_score)
raw_record(id, source_id, source_key, fetched_at, payload_json, content_hash)            -- immutable
permit(id, raw_record_id, permit_no, type, work_type, status, milestone, application_date,
       issue_date, reported_cost, description, pin, address_norm, geom, version, valid_from, valid_to)
violation(...), business_license(...), inspection(...)                                    -- same pattern
project(id, pin, address_norm, geom, first_seen, last_seen, stage, value_band, summary)
project_record(project_id, record_type, record_id)                                        -- many permits → one project
party(id, canonical_name, kind[company|person|agency], license_ids, website, hq_zip)
party_alias(party_id, raw_name, source_id, match_method, match_score, reviewed_by)
role(project_id, party_id, role[owner|gc|architect|electrical|plumbing|hvac|masonry|...],
     assertion[confirmed|inferred], source_record_id)
signal(id, kind[permit_issued|demolition|violation|new_license|license_inspection|...],
       project_id, party_id, occurred_at, source_record_id)
trade_tag(project_id, trade, relevance, assertion, confidence, method[rule|llm|human], method_version)
tenant(id, name) ; tenant_profile(tenant_id, industry, services[], geo, radius_mi, value_min,
       value_max, segments[], exclusions[], capacity, version, provided_vs_inferred)
opportunity(id, tenant_id, signal_id/project_id, score, tier[call_today|this_week|monitor|low],
            explanation_json, evidence_ids[], scoring_version, created_at)
contact(id, party_id, name, title, email, phone, source, retrieved_at, verification, confidence)
feedback(opportunity_id, tenant_id, label[relevant|not_relevant|wrong_trade|already_awarded|
         bad_contact|contacted|meeting|won|lost], note, at)
audit_log(actor, action, object, before, after, at)
metric_run(module, version, dataset, metrics_json, at)
```

Notes:

- `project` is the unit customers care about; a building may have a renovation permit, an electrical express permit, a sign permit and a violation — one project, many signals.
- `role.assertion = inferred` covers "this renovation likely needs HVAC" (inferred demand) vs "ADMIRAL HEATING is listed as ventilation contractor" (confirmed).
- `party_alias` lets entity resolution be reviewed and reversed without touching raw data.

## 4. Classification approach (M4)

1. **Rules layer** (versioned YAML per industry module): permit type, work type, contact license types, keyword patterns ("kitchen hood", "rooftop unit", "slab", "tenant build-out"), value thresholds. Each rule emits `trade`, `assertion`, `confidence`, `reason`.
2. **LLM layer** only for records where rules are ambiguous or silent: structured-output extraction (project type, trades implied, stage hints, unit counts) with the permit text treated strictly as data. Cache by `(content_hash, prompt_version, model)`.
3. **Human review** for low-confidence items that would otherwise reach a customer.
4. **Golden set:** start with 200 hand-labeled Chicago major permits (trades needed, trades already named, project type, stage), stratified by type and value; grow with every customer correction; keep a "hard cases" subset. Run on every change; track per-trade precision/recall so one vertical's improvement can't silently break another.

## 5. Scoring (M5)

Transparent weighted score, configurable per tenant, explained in plain language:

```text
score = Σ w_i · f_i     with f_i ∈ [0,1]
  service_fit       trade_tag relevance × tenant services match
  value_fit         project/trade value within tenant range
  distance          decay beyond tenant radius
  stage_timing      how close the project is to the tenant's buying window (per industry config)
  freshness         age of the triggering signal
  open_door         e.g. trade not yet named; GC rotates subs; new GC in tenant's size band
  contactability    verified decision-maker available
  history           prior outcomes for similar signals (0 until there is data)
tier = call_today | this_week | monitor | low   (thresholds per tenant, tuned on acceptance)
```

Learning: feedback adjusts *proposed* weights offline; a change ships only if it improves acceptance/meeting rate on held-out feedback and doesn't regress the golden set. No live self-modifying scores.

## 6. Industry modules as configuration

An industry module is a folder of data, not code:

```text
industries/hvac_commercial/
  taxonomy.yaml        # services, project types, terminology for this trade
  signals.yaml         # which signal kinds matter, buying window per stage
  rules.yaml           # classification rules
  scoring.yaml         # default weights and tier thresholds
  templates/           # outreach and report templates
  eval/golden.jsonl    # trade-specific labeled cases
```

Onboarding writes a `tenant_profile` that selects a module and overrides defaults. The "adaptive dashboard" later reads the same config, so the UI adapts for free.

## 7. AI assistant architecture (when it's time)

```text
user ─► auth + tenant scope ─► assistant (LLM with tool calling)
                                   │
              read tools (L1): search_opportunities, get_project, get_party_graph,
                               market_stats, get_profile, crm_search, explain_score
              prepare tools (L2): draft_email, draft_proposal, propose_crm_update,
                                  propose_filter  → saved as drafts needing approval
              execute tools (L3): apply_crm_update, schedule_followup  → explicit approval,
                                  rate limits, audit log
                                   │
              SQL views with row-level security per tenant · documents (RAG) for help content
```

Rules:

- Numbers come from the database via tools; the model explains them.
- Record text (permit descriptions, web pages, emails) is untrusted input — never instructions. Tools enforce scope regardless of what the model asks for (OWASP LLM risks: prompt injection, sensitive data exposure, excessive agency).
- Unsupported filter conditions are reported back ("I can't filter by 'already contacted' until your CRM is connected").
- Phasing: A internal test tool → B natural-language opportunity search → C personalized with profiles → D CRM + drafting → E market analysis → F customer-facing in dashboard.

## 8. Three architectures

| | **Lean MVP** (now → ~10 customers) | **Growth** (~10–200 customers, 1–3 metros) | **Scale** (1,000s of customers, many metros) |
| --- | --- | --- | --- |
| Language | Python | Python (+ TypeScript for web app) | Same; services split by stage |
| Storage | Postgres + PostGIS (managed); raw JSON in a table or object storage | Postgres + PostGIS; object storage for raw; read replicas | Lakehouse/warehouse for raw + history (Parquet), Postgres for serving, search index |
| Orchestration | Cron / scheduled jobs; one CLI per stage | Prefect or Dagster; retries, lineage | Dagster/Airflow + event bus for change-driven processing |
| AI | One LLM API, cached; rules first | Model routing by task; batch APIs; eval harness in CI | Same + fine-tuned small classifiers where volume justifies |
| Delivery | CSV / Google Sheets / emailed report; HubSpot or HighLevel sync | FastAPI + thin web app (auth, opportunity list, feedback buttons); briefing emails | Full multi-tenant app, public API, integrations marketplace |
| Auth/tenancy | Single internal user; tenant_id everywhere | Managed auth (e.g. Clerk/Auth0/Supabase), RLS | SSO, roles, audit, SOC 2 path |
| Billing | Invoices | Stripe subscriptions | Stripe + usage metering |
| Monitoring | Logs + daily health email (freshness, counts, failures) | Sentry + metrics dashboards + alerting | Full observability, on-call |
| Cost [E] | $25–$150/mo infra + $0–$100/mo data + LLM <$50/mo | $500–$3k/mo (incl. Shovels, contacts) | $10k+/mo |
| Team [E] | 1 engineer (with AI coding agents) + founder doing research/sales | 2–4 engineers + data ops + CS | Platform, data, ML, app teams |
| Main risk | Over-building before validation | Data ops load from many sources | Coverage economics, compliance at scale |

**Recommendation:** Lean MVP now. Move to Growth only when ≥5 paying customers retain for 3 months *and* manual work per customer is the bottleneck.

## 9. Repository layout (proposed for the engine)

```text
engine/
  collect/        # one fetcher per source, incremental, writes raw_record
  normalize/      # source adapters → typed records
  resolve/        # project clustering, entity resolution, review queue export
  classify/       # rules engine + LLM fallback + cache
  score/          # scoring + explanations
  enrich/         # contact providers
  deliver/        # report builders, CRM sync, email
  learn/          # feedback ingestion, metrics, offline weight proposals
industries/       # vertical configuration (see §6)
eval/             # golden sets, eval runner, metric history
research/         # probes and findings (exists today)
db/migrations/
```

## 10. Development controls

Version control with small reviewed changes; automated tests + golden-set eval in CI; database migrations under version control; staging before production for anything customer-facing; feature flags per tenant; rollback for rules/weights (they're versioned config); error monitoring; cost and latency logged per module run; documentation updated with each decision (`decision-log.md`).
