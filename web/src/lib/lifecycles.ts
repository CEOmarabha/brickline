import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

export type LifecycleFamily = "events" | "property" | "business" | "cleanup";

export interface LifecycleService {
  name: string;
  /** Key in `LifecyclesFile.vendors`: the companies that sell this service. */
  vendor: string;
  /** How to tell who already covers the job. */
  incumbent: string;
  /** Share of permits that name a company in this role (last 730 days), when public data shows it. */
  incumbentShare: number | null;
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
  /** `offsetDays`: stage window in days relative to the event date (negative = before); events only. */
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
