import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";
import type { LeadKind, TradeKey } from "@/lib/snapshot";

export type LifecycleFamily = "events" | "property" | "business" | "cleanup";

export interface LifecycleService {
  name: string;
  /** Key in `LifecyclesFile.vendors`: the companies that sell this service. */
  vendor: string;
  /** How to tell who already covers the job. */
  incumbent: string;
  /** Share of permits that name a company in this role (last 730 days), when public data shows it. */
  incumbentShare: number | null;
  /** Snapshot trades whose chance of work on a lead measures this job. */
  trades: TradeKey[];
}

export interface Lifecycle {
  id: string;
  family: LifecycleFamily;
  name: string;
  story: string;
  trigger: string;
  source: string;
  /** Triggers in the last 365 days of the source (or open leads, see `volumeNote`). */
  volume12m: number | null;
  volumeNote: string | null;
  notice: string;
  buyer: string;
  reach: string;
  appLink: string | null;
  tags: string[];
  /** Snapshot lead kinds that start this lifecycle; their lead pages show its jobs. */
  leadKinds: LeadKind[];
  /**
   * `offsetDays`: stage window in days relative to the event date (event lifecycles; negative = before) or to the
   * lead's signal date (lifecycles with `leadKinds`); null when the stage has no dated window.
   */
  stages: { name: string; when: string; offsetDays: [number, number] | null; services: LifecycleService[] }[];
}

export interface LifecyclesFile {
  asOf: string;
  vendors: Record<string, { label: string; companies: number; withPhone: number; withEmail: number; withWebsite: number }>;
  incumbents: Record<string, number>;
  lifecycles: Lifecycle[];
}

export const FAMILY_LABEL: Record<LifecycleFamily, string> = {
  events: "Events",
  property: "Property and construction",
  business: "Business openings and moves",
  cleanup: "Cleanup and restoration",
};

let loaded: Promise<LifecyclesFile> | undefined;

export function getLifecycles(): Promise<LifecyclesFile> {
  loaded ??= readFile(path.join(process.cwd(), "data", "lifecycles.json"), "utf8")
    .then((raw) => JSON.parse(raw) as LifecyclesFile)
    .catch((error: unknown) => {
      loaded = undefined;
      throw error;
    });
  return loaded;
}
