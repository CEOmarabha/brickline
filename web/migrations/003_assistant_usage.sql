create table if not exists assistant_usage (
  id bigserial primary key,
  owner_id text not null,
  created_at timestamptz not null default now()
);

create index if not exists assistant_usage_owner on assistant_usage (owner_id, created_at);
