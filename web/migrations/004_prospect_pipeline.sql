-- Founder-only sales pipeline for the prospects list. Keyed by the signed-in owner, never by client workspace.
create table if not exists prospect_status (
  owner_id text not null,
  prospect_id text not null,
  status text not null default 'not_contacted',
  contact_name text not null default '',
  email text not null default '',
  phone text not null default '',
  website text not null default '',
  notes text not null default '',
  sequence_step integer not null default 0,
  next_follow_up date,
  updated_at timestamptz not null default now(),
  primary key (owner_id, prospect_id)
);

create index if not exists prospect_status_due on prospect_status (owner_id, next_follow_up);

create table if not exists prospect_event (
  id bigserial primary key,
  owner_id text not null,
  prospect_id text not null,
  status text not null,
  note text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists prospect_event_prospect on prospect_event (owner_id, prospect_id, created_at);
