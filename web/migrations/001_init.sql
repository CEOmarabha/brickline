create table if not exists workspace (
  id text primary key,
  business_name text not null default '',
  trade text not null default 'porch',
  areas integer[] not null default '{}',
  phone text not null default '',
  mailing_address text not null default '',
  updated_at timestamptz not null default now()
);

create table if not exists lead_status (
  workspace_id text not null,
  lead_id text not null,
  status text not null,
  note text not null default '',
  updated_at timestamptz not null default now(),
  primary key (workspace_id, lead_id)
);

create table if not exists lead_event (
  id bigserial primary key,
  workspace_id text not null,
  lead_id text not null,
  status text not null,
  note text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists lead_event_lead on lead_event (workspace_id, lead_id, created_at);
