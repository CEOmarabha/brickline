-- Daily event-lead scanner rows (engine.leads.event_scan). item_hash is stable across runs.
-- review_status is owned by the UI; collectors upsert everything else and leave this column alone.
-- raw_json is the sanitized snapshot (no phones/emails). Additive only.

create table if not exists event_lead (
  item_hash text primary key,
  source text not null,
  source_url text not null default '',
  title text,
  start_date date,
  venue text,
  city text,
  region text,
  status text,
  host_org text,
  score double precision,
  content_hash text,
  review_status text not null default 'new'
    constraint event_lead_review_known check (review_status in ('new', 'approved', 'rejected', 'contacted')),
  raw_json jsonb not null default '{}'::jsonb,
  first_seen timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  changed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists event_lead_review on event_lead (review_status, last_seen desc);
create index if not exists event_lead_start on event_lead (start_date);
create index if not exists event_lead_source on event_lead (source, score desc);
