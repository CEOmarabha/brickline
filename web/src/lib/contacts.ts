import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

export type ContactSource = "overture" | "chicago_business_licenses" | "company_website";
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
  return key ? (file.owners[key] ?? null) : null;
}

export function hasAnyContact(c: ContactSuggestions | undefined | null): boolean {
  return !!c && !!(c.website || c.phones.length || c.emails.length || c.contactName);
}
