-- Founder-only deal pipeline: buyers the founder finds and contacts personally, the partner vendors who do the
-- work, and the history of each deal. Every row is keyed by the signed-in owner (viewerId), never by client workspace.
--
-- Additive only. Works on PGlite (local, applied at startup) and Postgres (scripts/migrate.mjs, one transaction).

create table if not exists partner (
  id text primary key,
  owner_id text not null,
  name text not null,
  -- Comma-separated list, e.g. 'tent rental, tables and chairs'.
  services text not null default '',
  area text not null default '',
  contact_name text not null default '',
  phone text not null default '',
  email text not null default '',
  website text not null default '',
  -- How the partner pays or charges, e.g. '10% of booking' or '$75 per appointment'.
  fee_terms text not null default '',
  agreement_signed boolean not null default false,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists partner_owner on partner (owner_id, name);

create table if not exists deal (
  id text primary key,
  owner_id text not null,
  source text not null default 'other'
    constraint deal_source_known
      check (source in ('social', 'event_data', 'letter_callback', 'pilot_list', 'referral', 'other')),
  -- A link to the public post or page, or a Brickline lead id or event id.
  source_ref text not null default '',
  title text not null,
  buyer_name text not null default '',
  buyer_type text not null default 'person'
    constraint deal_buyer_type_known check (buyer_type in ('person', 'organization')),
  contact_channel text not null default 'other'
    constraint deal_contact_channel_known
      check (contact_channel in ('instagram', 'facebook', 'tiktok', 'email', 'phone', 'in_person', 'other')),
  contact_handle_or_info text not null default '',
  event_or_job_date date,
  guests_or_size integer
    constraint deal_guests_nonneg check (guests_or_size is null or guests_or_size >= 0),
  location text not null default '',
  needs text not null default '',
  budget_usd numeric(12,2)
    constraint deal_budget_nonneg check (budget_usd is null or budget_usd >= 0),
  status text not null default 'found'
    constraint deal_status_known
      check (status in ('found', 'contacted', 'replied', 'interested', 'quoted', 'booked', 'completed', 'lost', 'opted_out')),
  lost_reason text not null default '',
  partner_ids text[] not null default '{}',
  quote_usd numeric(12,2)
    constraint deal_quote_nonneg check (quote_usd is null or quote_usd >= 0),
  -- The founder's own fee on this deal.
  fee_usd numeric(12,2)
    constraint deal_fee_nonneg check (fee_usd is null or fee_usd >= 0),
  fee_model text not null default ''
    constraint deal_fee_model_known check (fee_model in ('', 'planning_fee', 'referral_fee', 'markup', 'none')),
  fee_collected boolean not null default false,
  next_follow_up date,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists deal_owner_status on deal (owner_id, status);
create index if not exists deal_owner_follow_up on deal (owner_id, next_follow_up);

create table if not exists deal_event (
  id bigserial primary key,
  owner_id text not null,
  deal_id text not null,
  status text not null,
  note text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists deal_event_deal on deal_event (owner_id, deal_id, created_at);
