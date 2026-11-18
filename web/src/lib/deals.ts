import { UserError } from "@/lib/action-result";
import { multiLine, singleLine } from "@/lib/clean-text";
import { isHttpUrl } from "@/lib/links";
import { type MoneyAmount, parseMoney } from "@/lib/money-input";
import { cleanWebsite, EMAIL, isValidDate } from "@/lib/pipeline";

/*
 * The founder's own deal pipeline: buyers he finds and contacts personally, partner vendors who do the work, and the
 * fee he earns. Shared constants, types and validation (used by server actions and client forms); the database reads
 * live in deal-store.ts and the metrics in deal-metrics.ts.
 */

export const DEAL_SOURCES = ["social", "event_data", "letter_callback", "pilot_list", "referral", "other"] as const;
export type DealSource = (typeof DEAL_SOURCES)[number];
export const DEAL_SOURCE_LABEL: Record<DealSource, string> = {
  social: "Social media",
  event_data: "City event data",
  letter_callback: "Letter callback",
  pilot_list: "Pilot list",
  referral: "Referral",
  other: "Other",
};

export const BUYER_TYPES = ["person", "organization"] as const;
export type BuyerType = (typeof BUYER_TYPES)[number];
export const BUYER_TYPE_LABEL: Record<BuyerType, string> = { person: "Person", organization: "Organization" };

export const CONTACT_CHANNELS = ["instagram", "facebook", "tiktok", "email", "phone", "in_person", "other"] as const;
export type ContactChannel = (typeof CONTACT_CHANNELS)[number];
export const CHANNEL_LABEL: Record<ContactChannel, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  email: "Email",
  phone: "Phone",
  in_person: "In person",
  other: "Other",
};

export const DEAL_STATUS_VALUES = [
  "found",
  "contacted",
  "replied",
  "interested",
  "quoted",
  "booked",
  "completed",
  "lost",
  "opted_out",
] as const;
export type DealStatus = (typeof DEAL_STATUS_VALUES)[number];
export const DEAL_STATUS_LABEL: Record<DealStatus, string> = {
  found: "Found",
  contacted: "Contacted",
  replied: "Replied",
  interested: "Interested",
  quoted: "Quoted",
  booked: "Booked",
  completed: "Completed",
  lost: "Lost",
  opted_out: "Opted out",
};

/** The forward path of a deal; Lost and Opted out are side exits and have no rank. */
export const FUNNEL_ORDER: readonly DealStatus[] = [
  "found",
  "contacted",
  "replied",
  "interested",
  "quoted",
  "booked",
  "completed",
];

/** Position on the forward path (0 = found), or -1 for Lost and Opted out. */
export function stageRank(status: DealStatus): number {
  return FUNNEL_ORDER.indexOf(status);
}

export const FEE_MODEL_VALUES = ["planning_fee", "referral_fee", "markup", "none"] as const;
export type DealFeeModel = (typeof FEE_MODEL_VALUES)[number];
export const DEAL_FEE_MODEL_LABEL: Record<DealFeeModel, string> = {
  planning_fee: "Planning fee (flat, paid by the buyer)",
  referral_fee: "Referral fee (paid by the partner)",
  markup: "Markup on the partner's price",
  none: "No fee",
};

export const OPTED_OUT_LOCKED = "This buyer opted out. The record stays locked so you never contact them again.";

/** Days after "Contacted" at which a follow-up is suggested when none is set. */
export const DEFAULT_FOLLOW_UP_DAYS = 3;

export const MAX_DEAL_USD = 10_000_000;
export const MAX_GUESTS = 1_000_000;
export const MAX_PARTNERS_PER_DEAL = 10;

/** One deal as read from the database. Dates are YYYY-MM-DD; money is dollars. */
export interface DealRow {
  id: string;
  source: DealSource;
  sourceRef: string;
  title: string;
  buyerName: string;
  buyerType: BuyerType;
  contactChannel: ContactChannel;
  contactInfo: string;
  eventDate: string | null;
  guests: number | null;
  location: string;
  needs: string;
  budgetUsd: number | null;
  status: DealStatus;
  lostReason: string;
  partnerIds: string[];
  quoteUsd: number | null;
  feeUsd: number | null;
  feeModel: DealFeeModel | "";
  feeCollected: boolean;
  nextFollowUp: string | null;
  notes: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface PartnerRow {
  id: string;
  name: string;
  services: string;
  area: string;
  contactName: string;
  phone: string;
  email: string;
  website: string;
  feeTerms: string;
  agreementSigned: boolean;
  notes: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface DealEventRow {
  id: number;
  dealId: string;
  status: DealStatus;
  note: string;
  createdAt: Date;
}

export type CreateResult = { ok: true; id: string } | { ok: false; error: string };

export function isDealStatus(value: unknown): value is DealStatus {
  return typeof value === "string" && (DEAL_STATUS_VALUES as readonly string[]).includes(value);
}

/** A do-not-contact deal: nothing is drafted, no follow-up is scheduled and the status cannot be changed back. */
export function isOptedOut(status: DealStatus): boolean {
  return status === "opted_out";
}

/**
 * A comparable form of a handle, email or phone number, so a contact who opted out on one deal is recognized on
 * another: case, a leading @ and spacing are ignored, and phone numbers compare by their last ten digits.
 */
export function contactKey(info: string): string {
  const s = info.trim().toLowerCase();
  if (s === "") return "";
  const digits = s.replace(/\D/g, "");
  if (/^[\d\s().+-]+$/.test(s) && digits.length >= 7) return digits.slice(-10);
  return s.replace(/^@/, "").replace(/\s+/g, "");
}

/** True when another of the owner's deals with the same contact has opted out. */
export function matchesOptedOutContact(
  deal: { id: string; contactInfo: string },
  all: { id: string; status: DealStatus; contactInfo: string }[],
): boolean {
  const key = contactKey(deal.contactInfo);
  if (key === "") return false;
  return all.some((d) => d.id !== deal.id && isOptedOut(d.status) && contactKey(d.contactInfo) === key);
}

/** Due today or overdue. Opted-out deals never come up: there is nobody to follow up with. */
export function isDealDue(row: { status: DealStatus; nextFollowUp: string | null }, today: string): boolean {
  return row.nextFollowUp !== null && row.nextFollowUp <= today && !isOptedOut(row.status);
}

export function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((Date.parse(`${toIso}T00:00:00Z`) - Date.parse(`${fromIso}T00:00:00Z`)) / 86_400_000);
}

/** "in 12 days", "tomorrow", "today", "3 days ago"; "" without a date. */
export function daysUntilLabel(date: string | null, today: string): string {
  if (!date) return "";
  const d = daysBetween(today, date);
  if (d === 0) return "today";
  if (d === 1) return "tomorrow";
  if (d === -1) return "yesterday";
  return d > 0 ? `in ${d} days` : `${-d} days ago`;
}

/** A deal that is still being worked, for the open-versus-finished split in the list. */
export function isOpenDeal(status: DealStatus): boolean {
  return status !== "completed" && status !== "lost" && status !== "opted_out";
}

/** Plain next step for each stage; used in the due list and the assistant. Contains no buyer details. */
export function dealNextStep(row: { status: DealStatus; feeUsd: number | null; feeCollected: boolean }): string {
  switch (row.status) {
    case "found":
      return "Send a first personal message (the deal page has a draft)";
    case "contacted":
      return "Follow up once if there is no reply";
    case "replied":
      return "Find out what they need: date, size, budget";
    case "interested":
      return "Get the partner's price and send a quote";
    case "quoted":
      return "Follow up on the quote";
    case "booked":
      return "Confirm the details with the partner and collect your fee";
    case "completed":
      return row.feeUsd !== null && row.feeUsd > 0 && !row.feeCollected ? "Collect your fee" : "Nothing: record the outcome";
    case "lost":
      return "Nothing unless they contact you again";
    case "opted_out":
      return "Do not contact";
  }
}

function oneOf<T extends string>(value: unknown, allowed: readonly T[], label: string): T {
  if (typeof value !== "string" || !allowed.includes(value as T)) throw new UserError(`Unknown ${label}`);
  return value as T;
}

function cleanDate(value: unknown, label: string): string | null {
  const d = value === null || value === undefined ? "" : String(value).trim();
  if (d === "") return null;
  if (!isValidDate(d)) throw new UserError(`${label} is not a valid date`);
  const year = Number(d.slice(0, 4));
  if (year < 2000 || year > 2100) throw new UserError(`${label} must be between 2000 and 2100`);
  return d;
}

export const cleanFollowUpDate = (value: unknown): string | null => cleanDate(value, "Follow-up date");

function cleanGuests(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const s = typeof value === "number" ? String(value) : String(value).trim().replaceAll(",", "");
  if (s === "") return null;
  if (!/^\d{1,7}$/.test(s)) throw new UserError("Guests or size must be a whole number");
  const n = Number(s);
  if (n > MAX_GUESTS) throw new UserError(`Guests or size can't be more than ${MAX_GUESTS.toLocaleString("en-US")}`);
  return n;
}

const URL_WITH_SCHEME = /^[a-z][a-z0-9+.-]*:\/\//i;
const OTHER_SCHEME = /^(javascript|data|vbscript|file|blob|about|mailto|tel|sms):/i;
const BARE_DOMAIN = /^(?:www\.)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:[/?#]|$)/i;
const REF_TOKEN = /^[A-Za-z0-9][A-Za-z0-9._:/#=&%+~-]*$/;

function httpUrl(candidate: string): string {
  let url: URL;
  try {
    url = new URL(candidate);
  } catch {
    throw new UserError("Link is not a valid http or https address");
  }
  if ((url.protocol !== "http:" && url.protocol !== "https:") || !url.hostname.includes(".")) {
    throw new UserError("Link must be an http or https address");
  }
  if (url.username || url.password) throw new UserError("Link must not contain a login");
  return candidate;
}

/**
 * Where the deal was found: an http(s) link to the public post or page, or a Brickline lead or event id.
 * Any other scheme (javascript:, data:, file:, ftp://) is rejected; a bare "instagram.com/p/abc" gets https://.
 */
export function cleanSourceRef(value: unknown): string {
  const raw = singleLine(value, 400, "Link or id");
  if (raw === "") return "";
  if (/\s/.test(raw)) throw new UserError("Link or id can't contain spaces");
  if (URL_WITH_SCHEME.test(raw) || OTHER_SCHEME.test(raw)) return httpUrl(raw);
  if (BARE_DOMAIN.test(raw)) return httpUrl(`https://${raw}`);
  if (!REF_TOKEN.test(raw)) throw new UserError("Link or id has characters that aren't allowed");
  return raw;
}

/** Best guess of the contact channel from a link to a public post. */
export function guessChannel(sourceRef: string): ContactChannel {
  if (!isHttpUrl(sourceRef)) return "other";
  let host = "";
  try {
    host = new URL(sourceRef).hostname.toLowerCase();
  } catch {
    return "other";
  }
  const on = (domain: string) => host === domain || host.endsWith(`.${domain}`);
  if (on("instagram.com")) return "instagram";
  if (on("facebook.com") || on("fb.com") || on("fb.watch")) return "facebook";
  if (on("tiktok.com")) return "tiktok";
  return "other";
}

export interface DealFields {
  source?: string;
  sourceRef?: string;
  title?: string;
  buyerName?: string;
  buyerType?: string;
  contactChannel?: string;
  contactInfo?: string;
  /** YYYY-MM-DD or "" / null to clear. */
  eventDate?: string | null;
  guests?: string | number | null;
  location?: string;
  needs?: string;
  budget?: string | number | null;
  notes?: string;
}

export interface CleanDealFields {
  source?: DealSource;
  sourceRef?: string;
  title?: string;
  buyerName?: string;
  buyerType?: BuyerType;
  contactChannel?: ContactChannel;
  contactInfo?: string;
  eventDate?: string | null;
  guests?: number | null;
  location?: string;
  needs?: string;
  budget?: MoneyAmount | null;
  notes?: string;
}

/** Validates and trims only the fields that are present. Throws a UserError with a message safe to show. */
export function cleanDealFields(fields: DealFields): CleanDealFields {
  const out: CleanDealFields = {};
  if (fields.source !== undefined) out.source = oneOf(fields.source, DEAL_SOURCES, "source");
  if (fields.sourceRef !== undefined) out.sourceRef = cleanSourceRef(fields.sourceRef);
  if (fields.title !== undefined) {
    out.title = singleLine(fields.title, 120, "Title");
    if (out.title === "") throw new UserError("Add a short title so you can find this deal again");
  }
  if (fields.buyerName !== undefined) out.buyerName = singleLine(fields.buyerName, 120, "Buyer name");
  if (fields.buyerType !== undefined) out.buyerType = oneOf(fields.buyerType, BUYER_TYPES, "buyer type");
  if (fields.contactChannel !== undefined) {
    out.contactChannel = oneOf(fields.contactChannel, CONTACT_CHANNELS, "contact channel");
  }
  if (fields.contactInfo !== undefined) out.contactInfo = singleLine(fields.contactInfo, 200, "Handle or contact info");
  if (fields.eventDate !== undefined) out.eventDate = cleanDate(fields.eventDate, "Event or job date");
  if (fields.guests !== undefined) out.guests = cleanGuests(fields.guests);
  if (fields.location !== undefined) out.location = singleLine(fields.location, 200, "Location");
  if (fields.needs !== undefined) out.needs = multiLine(fields.needs, 2000, "Needs");
  if (fields.budget !== undefined) out.budget = parseMoney(fields.budget, { label: "Budget", max: MAX_DEAL_USD });
  if (fields.notes !== undefined) out.notes = multiLine(fields.notes, 4000, "Notes");
  return out;
}

export interface QuoteFeeFields {
  quote?: string | number | null;
  fee?: string | number | null;
  /** One of FEE_MODEL_VALUES, or "" to clear. */
  feeModel?: string;
}

export interface CleanQuoteFee {
  quote?: MoneyAmount | null;
  fee?: MoneyAmount | null;
  feeModel?: DealFeeModel | "";
}

export function cleanQuoteFee(fields: QuoteFeeFields): CleanQuoteFee {
  const out: CleanQuoteFee = {};
  if (fields.quote !== undefined) out.quote = parseMoney(fields.quote, { label: "Quote", max: MAX_DEAL_USD });
  if (fields.fee !== undefined) out.fee = parseMoney(fields.fee, { label: "Your fee", max: MAX_DEAL_USD });
  if (fields.feeModel !== undefined) {
    const model = typeof fields.feeModel === "string" ? fields.feeModel.trim() : null;
    if (model === null || (model !== "" && !(FEE_MODEL_VALUES as readonly string[]).includes(model))) {
      throw new UserError("Unknown fee model");
    }
    out.feeModel = model as DealFeeModel | "";
  }
  return out;
}

export interface PartnerFields {
  name?: string;
  services?: string;
  area?: string;
  contactName?: string;
  phone?: string;
  email?: string;
  website?: string;
  feeTerms?: string;
  agreementSigned?: boolean;
  notes?: string;
}

export interface CleanPartnerFields extends Omit<PartnerFields, "agreementSigned"> {
  agreementSigned?: boolean;
}

/** "tent rental,  tables;chairs" -> "tent rental, tables, chairs": at most 12 services, no duplicates. */
function cleanServices(value: unknown): string {
  const raw = singleLine(value, 300, "Services");
  const seen = new Set<string>();
  const list: string[] = [];
  for (const part of raw.split(/[,;]/)) {
    const s = part.trim();
    if (s === "" || seen.has(s.toLowerCase())) continue;
    if (s.length > 60) throw new UserError("Each service can be at most 60 characters");
    seen.add(s.toLowerCase());
    list.push(s);
  }
  if (list.length > 12) throw new UserError("List at most 12 services");
  return list.join(", ");
}

export function cleanPartnerFields(fields: PartnerFields): CleanPartnerFields {
  const out: CleanPartnerFields = {};
  if (fields.name !== undefined) {
    out.name = singleLine(fields.name, 120, "Name");
    if (out.name === "") throw new UserError("Add the partner's business name");
  }
  if (fields.services !== undefined) out.services = cleanServices(fields.services);
  if (fields.area !== undefined) out.area = singleLine(fields.area, 120, "Area");
  if (fields.contactName !== undefined) out.contactName = singleLine(fields.contactName, 120, "Contact name");
  if (fields.phone !== undefined) out.phone = singleLine(fields.phone, 40, "Phone");
  if (fields.email !== undefined) {
    const email = singleLine(fields.email, 200, "Email");
    if (email !== "" && !EMAIL.test(email)) throw new UserError("Email doesn't look right");
    out.email = email;
  }
  if (fields.website !== undefined) out.website = cleanWebsite(fields.website);
  if (fields.feeTerms !== undefined) out.feeTerms = singleLine(fields.feeTerms, 200, "Fee terms");
  if (fields.agreementSigned !== undefined) {
    if (typeof fields.agreementSigned !== "boolean") throw new UserError("Unknown agreement value");
    out.agreementSigned = fields.agreementSigned;
  }
  if (fields.notes !== undefined) out.notes = multiLine(fields.notes, 4000, "Notes");
  return out;
}

/** A list of partner ids from the client: strings only, no duplicates, a sane maximum. */
export function cleanPartnerIds(value: unknown): string[] {
  if (!Array.isArray(value)) throw new UserError("Unknown partners");
  const ids: string[] = [];
  for (const v of value) {
    if (typeof v !== "string" || v.length === 0 || v.length > 80) throw new UserError("Unknown partner");
    if (!ids.includes(v)) ids.push(v);
  }
  if (ids.length > MAX_PARTNERS_PER_DEAL) throw new UserError(`Attach at most ${MAX_PARTNERS_PER_DEAL} partners to one deal`);
  return ids;
}

export function cleanDealId(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 80) throw new UserError("Unknown deal");
  return value;
}
