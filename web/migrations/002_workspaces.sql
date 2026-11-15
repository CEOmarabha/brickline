-- A signed-in user can run several workspaces (one per client they manage).
alter table workspace add column if not exists owner_id text;
alter table workspace add column if not exists name text not null default '';
alter table workspace add column if not exists created_at timestamptz not null default now();

-- Workspaces created before this migration used the owner's id as the workspace id.
update workspace set owner_id = id where owner_id is null;

create index if not exists workspace_owner on workspace (owner_id, created_at);

create table if not exists viewer_state (
  owner_id text primary key,
  current_workspace text not null,
  updated_at timestamptz not null default now()
);
