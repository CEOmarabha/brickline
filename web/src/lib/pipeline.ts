import { UserError } from "@/lib/action-result";
import { multiLine, singleLine } from "@/lib/clean-text";
import { type MoneyAmount, parseMoney } from "@/lib/money-input";

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
export const PROSPECT_FOLLOW_UP_DAYS: Record<number, number | null> = { 1: 4, 2: 6, 3: null };

/** Statuses that never show up as "due": the conversation is finished or already a customer. */
export const CLOSED_STATUSES: readonly ProspectStatus[] = ["paying", "not_interested"];

/** How a prospect pays. Mirrors the check constraint on `prospect_status.fee_model`; "" means not set. */
export const FEE_MODELS = ["subscription", "per_lead", "per_won_job", "flat_pilot"] as const;
export type FeeModel = (typeof FEE_MODELS)[number];

export const FEE_MODEL_LABEL: Record<FeeModel, string> = {
  subscription: "Subscription (monthly fee)",
  per_lead: "Per lead",
  per_won_job: "Per won job",
  flat_pilot: "Flat pilot fee",
};

/** Only a prospect in one of these statuses has deal terms (monthly value, fee model). */
export const DEAL_STATUSES: readonly ProspectStatus[] = ["pilot", "paying"];

export const MAX_MONTHLY_VALUE = 1_000_000;

export interface ProspectFields {
  status?: ProspectStatus;
  contactName?: string;
  email?: string;
  phone?: string;
  website?: string;
  notes?: string;
  /** YYYY-MM-DD, or null/"" to clear. */
  nextFollowUp?: string | null;
  /** Dollars per month as typed ("1,500", "1500.50"); null/"" to clear. */
  monthlyValue?: string | number | null;
  /** One of FEE_MODELS, or "" to clear. */
  feeModel?: string;
}

export interface CleanFields extends Omit<ProspectFields, "monthlyValue" | "feeModel"> {
  monthlyValue?: MoneyAmount | null;
  feeModel?: FeeModel | "";
}

export interface DealSummary {
  /** Prospects at this status. */
  count: number;
  /** Of those, how many have a monthly value entered. */
  withValue: number;
  /** Sum of the monthly values entered, in dollars. */
  totalMonthlyUsd: number;
  byFeeModel: Record<FeeModel, number>;
}

/** Counts and entered monthly values of Pilot and Paying prospects. Computed, never estimated. */
export function summarizeDeals(
  rows: Iterable<{ status: ProspectStatus; monthlyValueUsd: number | null; feeModel: FeeModel | "" } | undefined>,
): Record<"paying" | "pilot", DealSummary> {
  const empty = (): DealSummary => ({
    count: 0,
    withValue: 0,
    totalMonthlyUsd: 0,
    byFeeModel: { subscription: 0, per_lead: 0, per_won_job: 0, flat_pilot: 0 },
  });
  const out = { paying: empty(), pilot: empty() };
  const cents = { paying: 0, pilot: 0 };
  for (const row of rows) {
    if (!row || (row.status !== "paying" && row.status !== "pilot")) continue;
    const s = out[row.status];
    s.count++;
    if (row.monthlyValueUsd !== null) {
      s.withValue++;
      cents[row.status] += Math.round(row.monthlyValueUsd * 100);
    }
    if (row.feeModel !== "") s.byFeeModel[row.feeModel]++;
  }
  out.paying.totalMonthlyUsd = cents.paying / 100;
  out.pilot.totalMonthlyUsd = cents.pilot / 100;
  return out;
}

const LIMITS = { contactName: 120, email: 200, phone: 40, website: 200, notes: 4000 } as const;

export const EMAIL = /^[^\s@<>(),;:"]+@[^\s@<>(),;:"]+\.[^\s@<>(),;:"]+$/;
const DANGEROUS_SCHEME = /^\s*(javascript|data|vbscript|file|blob|about):/i;
const EXPLICIT_SCHEME = /^[a-z][a-z0-9+.-]*:\/\//i;

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

/** Normalizes a website to an http(s) URL, or throws. Bare domains get https://. */
export function cleanWebsite(value: unknown): string {
  const raw = singleLine(value, LIMITS.website, "Website");
  if (raw === "") return "";
  if (DANGEROUS_SCHEME.test(raw)) throw new UserError("Website must be an http or https link");
  const withScheme = EXPLICIT_SCHEME.test(raw) ? raw : `https://${raw}`;
  let url: URL;
  try {
    url = new URL(withScheme);
  } catch {
    throw new UserError("Website is not a valid link");
  }
  if ((url.protocol !== "http:" && url.protocol !== "https:") || !url.hostname.includes(".")) {
    throw new UserError("Website must be an http or https link");
  }
  if (url.username || url.password) throw new UserError("Website must not contain a login");
  if (withScheme.length > LIMITS.website) throw new UserError(`Website is too long (max ${LIMITS.website} characters)`);
  return withScheme;
}

/** Validates and trims only the fields that are present. Throws a UserError with a user-readable message. */
export function cleanProspectFields(fields: ProspectFields): CleanFields {
  const out: CleanFields = {};
  if (fields.status !== undefined) {
    if (!PROSPECT_STATUSES.includes(fields.status)) throw new UserError("Unknown status");
    out.status = fields.status;
  }
  if (fields.contactName !== undefined) out.contactName = singleLine(fields.contactName, LIMITS.contactName, "Contact name");
  if (fields.email !== undefined) {
    const email = singleLine(fields.email, LIMITS.email, "Email");
    if (email !== "" && !EMAIL.test(email)) throw new UserError("Email doesn't look right");
    out.email = email;
  }
  if (fields.phone !== undefined) out.phone = singleLine(fields.phone, LIMITS.phone, "Phone");
  if (fields.website !== undefined) out.website = cleanWebsite(fields.website);
  if (fields.notes !== undefined) out.notes = multiLine(fields.notes, LIMITS.notes, "Notes");
  if (fields.nextFollowUp !== undefined) {
    const d = fields.nextFollowUp === null ? "" : String(fields.nextFollowUp).trim();
    if (d !== "" && !isValidDate(d)) throw new UserError("Follow-up date is not a valid date");
    out.nextFollowUp = d === "" ? null : d;
  }
  if (fields.monthlyValue !== undefined) {
    out.monthlyValue = parseMoney(fields.monthlyValue, { label: "Monthly value", max: MAX_MONTHLY_VALUE });
  }
  if (fields.feeModel !== undefined) {
    const model = typeof fields.feeModel === "string" ? fields.feeModel.trim() : null;
    if (model === null || (model !== "" && !FEE_MODELS.includes(model as FeeModel))) throw new UserError("Unknown fee model");
    out.feeModel = model as FeeModel | "";
  }
  return out;
}
