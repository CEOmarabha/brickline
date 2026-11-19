import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

export type HostType = "person" | "organization" | "ward_office" | "unknown";

export interface BoardHost {
  name: string | null;
  type: HostType;
  /** Mailing address from the permit (people and organizations) or the matched business listing. */
  mailing: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  source: string | null;
  /** A private person: no public phone, so a skip trace is the only route to one (D-027). */
  needsSkipTrace: boolean;
}

export interface BoardEvent {
  id: string;
  category: string;
  /** Key in lifecycles.json: the stages and services this event sets off. */
  lifecycle: string;
  name: string;
  start: string;
  end: string | null;
  place: string | null;
  area: { id: number; name: string } | null;
  ward: number | null;
  status: string | null;
  source: string;
  host: BoardHost;
  /** Likely next-season events only: share of similar blocks that held a party again (backtest). */
  chance?: number | null;
}

export interface Partner {
  name: string;
  phone: string | null;
  website: string | null;
  email: string | null;
}

export interface WardOffice {
  ward: number;
  alderman: string;
  address: string;
  phone: string | null;
  email: string | null;
  website: string | null;
}

export interface SkipTraceInfo {
  providers: { name: string; price: string; source: string }[];
  priceLow: number;
  priceHigh: number;
  hitRateLow: number;
  hitRateHigh: number;
  hitRateSource: string;
  dncShareLow: number;
  dncShareHigh: number;
  dnc: { illinoisRegistrations: number; illinoisPer100k: number; usRegistrations: number; asOf: string; source: string };
  read: string;
  upcomingPeople: number;
  predictedPeople: number;
  predictedHosts: number;
}

export interface EventBoard {
  asOf: string;
  windowDays: number;
  season: number;
  backtest: Record<string, { blocks: number; repeatRate: number }>;
  events: BoardEvent[];
  predicted: BoardEvent[];
  wards: Record<string, WardOffice>;
  partners: Record<string, Partner[]>;
  skipTrace: SkipTraceInfo;
}

export const HOST_TYPE_LABEL: Record<HostType, string> = {
  person: "Private person",
  organization: "Organization",
  ward_office: "Alderman's ward office",
  unknown: "Not published",
};

let loaded: Promise<EventBoard> | undefined;

export function getEventBoard(): Promise<EventBoard> {
  loaded ??= readFile(path.join(process.cwd(), "data", "event-board.json"), "utf8")
    .then((raw) => JSON.parse(raw) as EventBoard)
    .catch((error: unknown) => {
      loaded = undefined;
      throw error;
    });
  return loaded;
}

/** Days from `from` to `to` (ISO dates). */
export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000);
}

export function shiftDate(iso: string, days: number): string {
  return new Date(Date.parse(`${iso}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);
}

/** Expected numbers and cost of skip-tracing `people` hosts, as low-high ranges. */
export function skipTraceEstimate(info: SkipTraceInfo, people: number) {
  const matchesLow = Math.round(people * info.hitRateLow);
  const matchesHigh = Math.round(people * info.hitRateHigh);
  return {
    people,
    matchesLow,
    matchesHigh,
    callableLow: Math.round(matchesLow * (1 - info.dncShareHigh)),
    callableHigh: Math.round(matchesHigh * (1 - info.dncShareLow)),
    costLow: matchesLow * info.priceLow,
    costHigh: matchesHigh * info.priceHigh,
  };
}
