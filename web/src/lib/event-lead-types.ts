export const REVIEW_STATUSES = ["new", "approved", "rejected", "contacted"] as const;
export type ReviewStatus = (typeof REVIEW_STATUSES)[number];

export const REVIEW_STATUS_LABEL: Record<ReviewStatus, string> = {
  new: "New",
  approved: "Approved",
  rejected: "Rejected",
  contacted: "Contacted",
};

export interface EventLead {
  item_hash: string;
  source: string;
  source_url: string;
  title: string | null;
  event_name?: string | null;
  start: string | null;
  date?: string | null;
  venue: string | null;
  city: string | null;
  region: string | null;
  host_org: string | null;
  est_size?: number | null;
  vendor_needs?: string[];
  evidence_quote?: string | null;
  confidence?: number;
  score: number;
  review_status: ReviewStatus;
  first_seen?: string | null;
  last_seen?: string | null;
  is_new?: boolean;
  changed?: boolean;
  extra?: Record<string, unknown>;
}

export interface EventLeadCounts {
  total: number;
  new: number;
  changed: number;
  bySource: Record<string, number>;
  byRegion: Record<string, number>;
}

export interface EventLeadNote {
  source?: string;
  status?: string;
  detail?: string;
  count?: number;
  note?: string;
  records_path?: string;
}

export interface EventLeadsFile {
  asOf: string | null;
  generatedAt: string | null;
  counts: EventLeadCounts;
  notes: EventLeadNote[];
  items: EventLead[];
}

export interface EventDigestFile {
  asOf: string | null;
  timezone: string;
  title: string;
  counts: EventLeadCounts;
  top: EventLead[];
}

export function isReviewStatus(value: unknown): value is ReviewStatus {
  return typeof value === "string" && (REVIEW_STATUSES as readonly string[]).includes(value);
}

export function leadTitle(row: EventLead): string {
  return (row.event_name || row.title || "Untitled event").trim() || "Untitled event";
}

export function leadWhen(row: EventLead): string | null {
  const raw = row.start || row.date;
  return raw ? raw.slice(0, 10) : null;
}
