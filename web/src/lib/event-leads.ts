import "server-only";

import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { sql } from "@/lib/db";
import { hasPostgres, readLocalReviews } from "@/lib/event-lead-reviews-file";
import {
  type EventDigestFile,
  type EventLead,
  type EventLeadCounts,
  type EventLeadsFile,
  type ReviewStatus,
  isReviewStatus,
} from "@/lib/event-lead-types";

export {
  REVIEW_STATUSES,
  REVIEW_STATUS_LABEL,
  isReviewStatus,
  leadTitle,
  leadWhen,
  type EventDigestFile,
  type EventLead,
  type EventLeadCounts,
  type EventLeadNote,
  type EventLeadsFile,
  type ReviewStatus,
} from "@/lib/event-lead-types";

const EMPTY_COUNTS: EventLeadCounts = { total: 0, new: 0, changed: 0, bySource: {}, byRegion: {} };

let leadsCache: { mtimeMs: number; file: EventLeadsFile } | undefined;
let digestCache: { mtimeMs: number; file: EventDigestFile } | undefined;

async function readJson<T>(rel: string): Promise<{ mtimeMs: number; data: T } | null> {
  const file = path.join(process.cwd(), "data", rel);
  try {
    const { mtimeMs } = await stat(file);
    const data = JSON.parse(await readFile(file, "utf8")) as T;
    return { mtimeMs, data };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

/** Snapshot written by engine.leads.event_scan, or null when the job has never run. */
export async function getEventLeadsFile(): Promise<EventLeadsFile | null> {
  const got = await readJson<EventLeadsFile>("event-leads.json");
  if (!got) return null;
  if (leadsCache?.mtimeMs !== got.mtimeMs) leadsCache = { mtimeMs: got.mtimeMs, file: got.data };
  return leadsCache.file;
}

export async function getEventDigestFile(): Promise<EventDigestFile | null> {
  const got = await readJson<EventDigestFile>("event-digest.json");
  if (!got) return null;
  if (digestCache?.mtimeMs !== got.mtimeMs) digestCache = { mtimeMs: got.mtimeMs, file: got.data };
  return digestCache.file;
}

async function reviewOverlay(): Promise<Map<string, ReviewStatus>> {
  if (!hasPostgres()) {
    try {
      return await readLocalReviews();
    } catch {
      return new Map();
    }
  }
  try {
    const rows = await sql<{ item_hash: string; review_status: string }>(
      "select item_hash, review_status from event_lead",
    );
    const overlay = new Map<string, ReviewStatus>();
    for (const row of rows) {
      if (isReviewStatus(row.review_status)) overlay.set(row.item_hash, row.review_status);
    }
    return overlay;
  } catch {
    return new Map();
  }
}

function normalizeLead(row: EventLead, overlay: Map<string, ReviewStatus>): EventLead {
  const status = overlay.get(row.item_hash) ?? (isReviewStatus(row.review_status) ? row.review_status : "new");
  return { ...row, review_status: status, score: Number(row.score) || 0 };
}

/** Leads with review_status overlaid from Postgres or local JSON. */
export async function getEventLeads(): Promise<EventLeadsFile> {
  const file = await getEventLeadsFile();
  const overlay = await reviewOverlay();
  if (!file) {
    return { asOf: null, generatedAt: null, counts: EMPTY_COUNTS, notes: [], items: [] };
  }
  const items = (file.items ?? []).map((row) => normalizeLead(row, overlay));
  return { ...file, items, counts: file.counts ?? EMPTY_COUNTS, notes: file.notes ?? [] };
}

export async function getEventDigest(): Promise<EventDigestFile> {
  const file = await getEventDigestFile();
  const overlay = await reviewOverlay();
  if (!file) {
    return {
      asOf: null,
      timezone: "America/Chicago",
      title: "Event leads digest",
      counts: EMPTY_COUNTS,
      top: [],
    };
  }
  const top = (file.top ?? []).map((row) => normalizeLead(row, overlay));
  return { ...file, top, counts: file.counts ?? EMPTY_COUNTS };
}
