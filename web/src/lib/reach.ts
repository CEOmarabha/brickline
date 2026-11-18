import "server-only";

import { type ContactsFile, getContacts, mergeSuggestions } from "@/lib/contacts";
import type { LeadReply } from "@/lib/replies";
import type { Lead } from "@/lib/snapshot";

export type Way = "mail" | "email" | "phone";
export const WAY_LABEL: Record<Way, string> = { mail: "Mail", email: "Email", phone: "Phone" };
export const REACH_FILTERS = ["all", "direct", "mail_only", "none"] as const;

/**
 * How a lead can be reached today: a mailing address on the tax roll, a public business phone or email suggestion,
 * or a phone or email the owner gave when replying. Individual owners have no public phone or email, so for them a
 * reply is the only way past the letter.
 */
export function waysFor(lead: Lead, contacts: ContactsFile, replies: LeadReply[] = []): Way[] {
  const key = contacts.leadOwners[lead.id];
  const c = mergeSuggestions(key ? (contacts.owners[key] ?? null) : null, contacts.leads?.[lead.id] ?? null);
  const own = replies.filter((r) => r.leadId === lead.id);
  const ways: Way[] = [];
  if (lead.owner.mailing) ways.push("mail");
  if ((c?.emails.length ?? 0) > 0 || own.some((r) => r.contactEmail)) ways.push("email");
  if ((c?.phones.length ?? 0) > 0 || own.some((r) => r.contactPhone)) ways.push("phone");
  return ways;
}

export async function waysByLead(leads: Lead[], replies: LeadReply[] = []): Promise<Map<string, Way[]>> {
  const contacts = await getContacts();
  return new Map(leads.map((l) => [l.id, waysFor(l, contacts, replies)]));
}

export function matchesReach(ways: Way[] | undefined, reach: string): boolean {
  if (reach === "all" || !ways) return true;
  const direct = ways.includes("email") || ways.includes("phone");
  if (reach === "direct") return direct;
  if (reach === "mail_only") return !direct && ways.includes("mail");
  if (reach === "none") return ways.length === 0;
  return true;
}
