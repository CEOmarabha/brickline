import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";
import type { TradeKey } from "@/lib/snapshot";

export type ProspectTrade = Exclude<TradeKey, "general">;

export const PROSPECT_TRADES: ProspectTrade[] = ["porch", "masonry", "roofing", "plumbing", "electrical"];

export interface Prospect {
  id: string;
  trade: ProspectTrade;
  company: string;
  jobs12m: number;
  jobsPrev12m: number;
  medianJob: number;
  lastJob: string;
  /** Permits pulled at an address that had a violation in this trade in the year before. */
  violationDrivenJobs: number;
  /** Community areas where they pull the most permits, busiest first (max 4). */
  areaIds: number[];
}

export interface ProspectFile {
  generatedFor: string;
  prospects: Prospect[];
}

/** The profile the sales playbook calls the best first customers: they already win violation jobs, and are mid-sized. */
export function isBestFit(p: Prospect): boolean {
  return p.violationDrivenJobs > 0 && p.jobs12m >= 5 && p.jobs12m <= 40;
}

let loaded: Promise<ProspectFile> | undefined;

export function getProspects(): Promise<ProspectFile> {
  loaded ??= readFile(path.join(process.cwd(), "data", "prospects.json"), "utf8")
    .then((raw) => JSON.parse(raw) as ProspectFile)
    .catch((error: unknown) => {
      loaded = undefined;
      throw error;
    });
  return loaded;
}

export async function getProspect(id: string): Promise<Prospect | undefined> {
  const file = await getProspects();
  return file.prospects.find((p) => p.id === id);
}
