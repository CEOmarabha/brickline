import { readFile } from "node:fs/promises";
import pg from "pg";

const url = process.env.DATABASE_URL?.trim() ?? "";
if (url === "") {
  console.log("upsert-event-leads: skipped (no DATABASE_URL)");
  process.exit(0);
}

const raw = await readFile("data/event-leads.json", "utf8").catch(() => null);
if (!raw) {
  console.log("upsert-event-leads: no data/event-leads.json");
  process.exit(0);
}
const payload = JSON.parse(raw);
const items = Array.isArray(payload.items) ? payload.items : [];
const client = new pg.Client({ connectionString: url });
await client.connect();
try {
  let n = 0;
  for (const row of items) {
    if (!row?.item_hash) continue;
    await client.query(
      `insert into event_lead (
          item_hash, source, source_url, title, start_date, venue, city, region,
          status, host_org, score, content_hash, raw_json, first_seen, last_seen, changed_at
        ) values (
          $1, $2, $3, $4, $5::date, $6, $7, $8, $9, $10, $11, $12, $13::jsonb,
          $14::timestamptz, $15::timestamptz, $16::timestamptz
        )
        on conflict (item_hash) do update set
          source_url = excluded.source_url,
          title = excluded.title,
          start_date = excluded.start_date,
          venue = excluded.venue,
          city = excluded.city,
          region = excluded.region,
          status = excluded.status,
          host_org = excluded.host_org,
          score = excluded.score,
          content_hash = excluded.content_hash,
          raw_json = excluded.raw_json,
          last_seen = excluded.last_seen,
          changed_at = coalesce(excluded.changed_at, event_lead.changed_at)`,
      [
        row.item_hash,
        row.source ?? "unknown",
        row.source_url ?? "",
        row.event_name || row.title || null,
        row.start || row.date || null,
        row.venue ?? null,
        row.city ?? null,
        row.region ?? null,
        row.status ?? null,
        row.host_org ?? null,
        row.score ?? null,
        row.content_hash ?? null,
        JSON.stringify(row),
        row.first_seen ?? null,
        row.last_seen ?? null,
        row.changed_at ?? null,
      ],
    );
    n += 1;
  }
  console.log(`upsert-event-leads: upserted ${n}`);
} finally {
  await client.end();
}
