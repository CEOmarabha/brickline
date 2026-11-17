import "server-only";

import { readFile, stat } from "node:fs/promises";
import path from "node:path";

/** Allow-list of pilot list keys (also the order the hub shows them in). Anything else is rejected. */
export const BUYER_LIST_KEYS = ["newBusiness", "openTrades", "closedRestaurant", "pest"] as const;
export type BuyerListKey = (typeof BUYER_LIST_KEYS)[number];

export interface Buyer {
  segment: string;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  email: string | null;
  sources: string[];
  evidence: string;
  /** Permits naming this contractor in the last 12 months (permit-derived buyers only). */
  permits: number | null;
  lastPermit: string | null;
}

export interface BuyerCoverage {
  buyers: number;
  withPhone: number;
  withWebsite: number;
  withEmail: number;
  withAnyContact: number;
  phoneShare: number | null;
  websiteShare: number | null;
  emailShare: number | null;
  anyContactShare: number | null;
}

export interface BuyerSegment extends BuyerCoverage {
  key: string;
  label: string;
  listed: number;
  available: number;
  cap: number;
  permitDerived: boolean;
}

export interface BuyerList {
  key: BuyerListKey;
  title: string;
  segments: BuyerSegment[];
  counts: BuyerCoverage;
  buyers: Buyer[];
}

export interface BuyersFile {
  generatedAt: string;
  asOf: string;
  definition: string;
  windows: { permitDays: number; minPermits: number; minPermitsRestaurantGc: number };
  lists: BuyerList[];
  attribution: { text: string; overtureRelease: string; contactMatch: string };
}

export function parseBuyerList(value: string | string[] | null | undefined): BuyerListKey | null {
  const v = Array.isArray(value) ? value[0] : value;
  return BUYER_LIST_KEYS.find((k) => k === v) ?? null;
}

export function listOf(file: BuyersFile, key: BuyerListKey): BuyerList | undefined {
  return file.lists.find((l) => l.key === key);
}

let loaded: { mtimeMs: number; file: BuyersFile } | undefined;

/** The generated buyers file, or null when `engine.leads.buyers` has not been run. Reloads when the file changes. */
export async function getBuyers(): Promise<BuyersFile | null> {
  const file = path.join(process.cwd(), "data", "buyers.json");
  try {
    const { mtimeMs } = await stat(file);
    if (loaded?.mtimeMs !== mtimeMs) {
      loaded = { mtimeMs, file: JSON.parse(await readFile(file, "utf8")) as BuyersFile };
    }
    return loaded.file;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}
