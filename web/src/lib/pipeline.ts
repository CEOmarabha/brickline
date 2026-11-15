export const PROSPECT_STATUSES = [
  "not_contacted",
  "emailed",
  "replied",
  "meeting",
  "pilot",
  "paying",
  "not_interested",
] as const;
export type ProspectStatus = (typeof PROSPECT_STATUSES)[number];

export const PROSPECT_STATUS_LABEL: Record<ProspectStatus, string> = {
  not_contacted: "Not contacted",
  emailed: "Emailed",
  replied: "Replied",
  meeting: "Meeting",
  pilot: "Pilot",
  paying: "Paying",
  not_interested: "Not interested",
};

export const MAX_SEQUENCE_STEP = 3;

/** Days until the next touch after sending email N (playbook section 3: day 0, 4, 10). Null after the last one. */
export const FOLLOW_UP_DAYS: Record<number, number | null> = { 1: 4, 2: 6, 3: null };

/** Statuses that never show up as "due": the conversation is finished or already a customer. */
export const CLOSED_STATUSES: readonly ProspectStatus[] = ["paying", "not_interested"];

export interface ProspectFields {
  status?: ProspectStatus;
  contactName?: string;
  email?: string;
  phone?: string;
  website?: string;
  notes?: string;
  /** YYYY-MM-DD, or null/"" to clear. */
  nextFollowUp?: string | null;
}

export interface CleanFields {
  status?: ProspectStatus;
  contactName?: string;
  email?: string;
  phone?: string;
  website?: string;
  notes?: string;
  nextFollowUp?: string | null;
}

const LIMITS = { contactName: 120, email: 200, phone: 40, website: 200, notes: 4000 } as const;

const CONTROL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;
const EMAIL = /^[^\s@<>(),;:"]+@[^\s@<>(),;:"]+\.[^\s@<>(),;:"]+$/;
const DANGEROUS_SCHEME = /^\s*(javascript|data|vbscript|file|blob|about):/i;
const EXPLICIT_SCHEME = /^[a-z][a-z0-9+.-]*:\/\//i;

export function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

/** Today's date in Chicago as YYYY-MM-DD (the app's business timezone). */
export function todayChicago(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Chicago",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function isValidDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === value;
}

export function isDue(row: { status: ProspectStatus; nextFollowUp: string | null }, today: string): boolean {
  return row.nextFollowUp !== null && row.nextFollowUp <= today && !CLOSED_STATUSES.includes(row.status);
}

function singleLine(value: unknown, max: number, label: string): string {
  const s = String(value ?? "")
    .replace(CONTROL, "")
    .replace(/\s+/g, " ")
    .trim();
  if (s.length > max) throw new Error(`${label} is too long (max ${max} characters)`);
  return s;
}

/** Normalizes a website to an http(s) URL, or throws. Bare domains get https://. */
export function cleanWebsite(value: unknown): string {
  const raw = singleLine(value, LIMITS.website, "Website");
  if (raw === "") return "";
  if (DANGEROUS_SCHEME.test(raw)) throw new Error("Website must be an http or https link");
  const withScheme = EXPLICIT_SCHEME.test(raw) ? raw : `https://${raw}`;
  let url: URL;
  try {
    url = new URL(withScheme);
  } catch {
    throw new Error("Website is not a valid link");
  }
  if ((url.protocol !== "http:" && url.protocol !== "https:") || !url.hostname.includes(".")) {
    throw new Error("Website must be an http or https link");
  }
  if (url.username || url.password) throw new Error("Website must not contain a login");
  if (withScheme.length > LIMITS.website) throw new Error(`Website is too long (max ${LIMITS.website} characters)`);
  return withScheme;
}

/** Validates and trims only the fields that are present. Throws an Error with a user-readable message. */
export function cleanProspectFields(fields: ProspectFields): CleanFields {
  const out: CleanFields = {};
  if (fields.status !== undefined) {
    if (!PROSPECT_STATUSES.includes(fields.status)) throw new Error("Unknown status");
    out.status = fields.status;
  }
  if (fields.contactName !== undefined) out.contactName = singleLine(fields.contactName, LIMITS.contactName, "Contact name");
  if (fields.email !== undefined) {
    const email = singleLine(fields.email, LIMITS.email, "Email");
    if (email !== "" && !EMAIL.test(email)) throw new Error("Email doesn't look right");
    out.email = email;
  }
  if (fields.phone !== undefined) out.phone = singleLine(fields.phone, LIMITS.phone, "Phone");
  if (fields.website !== undefined) out.website = cleanWebsite(fields.website);
  if (fields.notes !== undefined) {
    const notes = String(fields.notes ?? "")
      .replace(CONTROL, "")
      .replace(/\r\n?/g, "\n")
      .trim();
    if (notes.length > LIMITS.notes) throw new Error(`Notes are too long (max ${LIMITS.notes} characters)`);
    out.notes = notes;
  }
  if (fields.nextFollowUp !== undefined) {
    const d = fields.nextFollowUp === null ? "" : String(fields.nextFollowUp).trim();
    if (d !== "" && !isValidDate(d)) throw new Error("Follow-up date is not a valid date");
    out.nextFollowUp = d === "" ? null : d;
  }
  return out;
}
