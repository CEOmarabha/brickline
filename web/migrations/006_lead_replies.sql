-- Owner replies to letters and emails, matched by the reply code printed on every draft (web/src/lib/reply-code.ts
-- derives the code from the workspace and lead ids, so codes are not stored anywhere else). lead_id is '' when the
-- code no longer matches a current lead (the lead aged out of the snapshot); the code is kept so it can be traced.
--
-- contact_phone and contact_email are what the owner chose to give us. They are personal data: they live only in
-- this table, never in the app's shipped data files.
--
-- Additive only.

create table if not exists lead_reply (
  id bigserial primary key,
  workspace_id text not null,
  lead_id text not null default '',
  code text not null,
  channel text not null
    constraint lead_reply_channel_known check (channel in ('phone', 'email', 'mail', 'web', 'other')),
  received_on date not null,
  contact_phone text not null default '',
  contact_email text not null default '',
  message text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists lead_reply_workspace on lead_reply (workspace_id, received_on desc, id desc);
create index if not exists lead_reply_lead on lead_reply (workspace_id, lead_id);

-- Holdout experiment (docs/19): share of this workspace's letter leads kept unmailed to measure what the letters
-- add. 0 = off. Which leads are held out is derived from the lead id (web/src/lib/experiments.ts), so it is the
-- same in every workspace and can be recomputed offline.
alter table workspace
  add column if not exists holdout_pct integer not null default 0
    constraint workspace_holdout_pct_range check (holdout_pct between 0 and 30);
