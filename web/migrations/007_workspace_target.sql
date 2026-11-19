-- What a workspace is looking for: a trade (porch, masonry, ...), event planning, or one of the commercial service
-- lists. An empty value means "use the workspace's trade", so every workspace created before this migration keeps
-- working unchanged. The app allow-lists the values (src/lib/targets.ts); the column stays plain text so a new target
-- never needs another migration.
--
-- Additive only. Works on PGlite (local, applied at startup) and Postgres (scripts/migrate.mjs, one transaction).

alter table workspace add column if not exists target text not null default '';
