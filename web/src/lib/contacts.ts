import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

export type ContactSource =
  | "overture"
  | "chicago_business_licenses"
  | "company_website"
  | "cdb_vendors"
  | "idph_lead_contractors"
  | "idph_asbestos_contractors"
  | "foreclosed_rental_registry"
  | "overture_at_mailing_address";
export type MatchConfidence = "high" | "medium";

/** One suggested value with where it came from. Suggestions are never saved without the founder pressing Save. */
export interface ContactField {
  value: string;
  source: ContactSource;
  /** Where to verify it: the page it was read from, or the public record. Null when there is no single page. */
  sourceUrl: string | null;
  confidence: MatchConfidence;
  retrievedAt: string;
  /** Other sources that listed the same value. */
  alsoFoundIn?: ContactSource[];
  /** For suggestions found by address: the business Overture lists there (it may not be the owner). */
  listing?: string;
}

export interface ContactNameField extends ContactField {
  title: string;
}

export interface ContactSuggestions {
  /** The business name the public sources matched (may differ slightly from ours). */
  name: string;
  website: ContactField | null;
  phones: ContactField[];
  emails: ContactField[];
  /** Business pages (Facebook, Instagram, LinkedIn company pages) Overture lists for the matched business. */
  socials?: ContactField[];
  contactName: ContactNameField | null;
  address: ContactField | null;
  matches: { source: ContactSource; method: string; confidence: MatchConfidence }[];
}

export interface ContactsFile {
  generatedFor: string;
  sources: Record<ContactSource, { label: string; release?: string; license?: string; attribution?: string; url?: string }>;
  prospects: Record<string, ContactSuggestions>;
  owners: Record<string, ContactSuggestions>;
  /** Lead id to key in `owners`, for leads whose company owner or buyer has suggestions. */
  leadOwners: Record<string, string>;
  /** Suggestions found by the lead's property or mailing address (company owners only). */
  leads?: Record<string, ContactSuggestions>;
}

let loaded: Promise<ContactsFile> | undefined;

export function getContacts(): Promise<ContactsFile> {
  loaded ??= readFile(path.join(process.cwd(), "data", "contacts.json"), "utf8")
    .then((raw) => JSON.parse(raw) as ContactsFile)
    .catch((error: unknown) => {
      loaded = undefined;
      throw error;
    });
  return loaded;
}

export async function getProspectContacts(prospectId: string): Promise<ContactSuggestions | null> {
  const file = await getContacts();
  return file.prospects[prospectId] ?? null;
}

export async function getLeadContacts(leadId: string): Promise<ContactSuggestions | null> {
  const file = await getContacts();
  const key = file.leadOwners[leadId];
  return mergeSuggestions(key ? (file.owners[key] ?? null) : null, file.leads?.[leadId] ?? null);
}

/** Name-matched suggestions first, then address-matched ones; a value already listed is not repeated. */
export function mergeSuggestions(
  byName: ContactSuggestions | null,
  byAddress: ContactSuggestions | null,
): ContactSuggestions | null {
  if (!byName || !byAddress) return byName ?? byAddress;
  const add = (a: ContactField[] = [], b: ContactField[] = []) => {
    const seen = new Set(a.map((f) => f.value.toLowerCase()));
    return [...a, ...b.filter((f) => !seen.has(f.value.toLowerCase()))];
  };
  return {
    ...byName,
    website: byName.website ?? byAddress.website,
    phones: add(byName.phones, byAddress.phones),
    emails: add(byName.emails, byAddress.emails),
    socials: add(byName.socials, byAddress.socials),
    matches: [...byName.matches, ...byAddress.matches],
  };
}

export function hasAnyContact(c: ContactSuggestions | undefined | null): boolean {
  return !!c && !!(c.website || c.phones.length || c.emails.length || c.contactName || c.socials?.length);
}
