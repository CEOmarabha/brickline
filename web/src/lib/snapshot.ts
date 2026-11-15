import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

export type TradeKey = "porch" | "masonry" | "roofing" | "plumbing" | "electrical" | "general";
export type Tier = "act_now" | "this_week" | "monitor";
export type LeadKind = "violation" | "investor_purchase";

export interface Evidence {
  label: string;
  value: string;
}

export interface Owner {
  name: string | null;
  type: "individual" | "company";
  mailing: string | null;
  units: number | null;
  note?: string;
}

interface LeadBase {
  id: string;
  kind: LeadKind;
  trades: TradeKey[];
  trade: TradeKey | null;
  title: string;
  address: string;
  communityArea: number | null;
  signalDate: string;
  ageDays: number;
  tier: Tier;
  probability: number;
  probabilityBasis: string;
  owner: Owner;
  evidence: Evidence[];
  action: string;
  sourceUrl: string;
}

export interface ViolationLead extends LeadBase {
  kind: "violation";
  trade: TradeKey;
  lat: number | null;
  lon: number | null;
  expectedValue: number;
  jobValue: number;
}

export interface PermitSummary {
  date: string;
  type: string;
  cost: number | null;
  description: string;
}

export interface InvestorLead extends LeadBase {
  kind: "investor_purchase";
  tradeProbabilities: Record<TradeKey, number>;
  majorProbability: number;
  segment: string;
  salePrice: number | null;
  buyer: {
    name: string | null;
    purchases24m: number;
    otherProperties: string[];
    contractorsUsed: { name: string; jobs: number }[];
  };
  permitsSince: PermitSummary[];
}

export type Lead = ViolationLead | InvestorLead;

export interface Area {
  id: number;
  name: string;
  violations: Partial<Record<TradeKey, { last90: number; lastYear: number }>>;
  permits: Record<TradeKey, { last90: number; lastYear: number }>;
  majorProjects: { last90: number; lastYear: number; value90: number };
  investorPurchases: { last180: number; lastYear: number };
  medianInvestorPrice: number | null;
}

export interface Competitor {
  name: string;
  jobs12m: number;
  jobsPrev12m: number;
  share: number;
  medianCost: number | null;
  areas: number[];
}

export interface RecentWin {
  trade: TradeKey;
  address: string;
  communityArea: number | null;
  signalDate: string;
  permitDate: string;
  contractor: string | null;
  daysToPermit: number;
}

export interface PreAppProject {
  id: string;
  address: string;
  communityArea: number | null;
  owner: string | null;
  probability: number;
  lift: number;
  historicalCases: number;
  signals: string[];
  recentPermits: PermitSummary[];
  recentGcs: string[];
}

export interface GcTarget {
  gc: string;
  openDoor: number;
  jobsTotal: number;
  jobs24m: number;
  medianCost: number | null;
  lastJob: string;
  currentSubs: { name: string; jobs: number }[];
  areas: number[];
}

export interface Snapshot {
  meta: {
    generatedAt: string;
    dataAsOf: { permits: string; violations: string; sales: string };
    sources: { name: string; url: string }[];
    assumptions: { winRate: { individual: number; company: number }; margin: number };
  };
  trades: Record<TradeKey, { label: string; jobValue: number }>;
  models: {
    violation: Partial<Record<TradeKey, Record<"individual" | "company", { episodes: number; p365: number }>>>;
    investorPurchase: Record<
      string,
      { purchases: number; pAny: number; pMajor: number; pTrade: Record<TradeKey, number> }
    >;
  };
  leads: Lead[];
  recentWins: RecentWin[];
  competitors: Record<TradeKey, { contractors: Competitor[]; violationJobsWon: { name: string; jobs: number }[] }>;
  areas: Area[];
  commercial: {
    preApplication: { baseRate: number; projects: PreAppProject[] };
    gcTargets: Record<"electrical" | "plumbing" | "hvac", GcTarget[]>;
  };
}

let loaded: Promise<Snapshot> | undefined;

export function getSnapshot(): Promise<Snapshot> {
  loaded ??= readFile(path.join(process.cwd(), "data", "snapshot.json"), "utf8")
    .then((raw) => JSON.parse(raw) as Snapshot)
    .catch((error: unknown) => {
      loaded = undefined;
      throw error;
    });
  return loaded;
}

export const TRADE_KEYS: TradeKey[] = ["porch", "masonry", "roofing", "plumbing", "electrical", "general"];

export const TIER_ORDER: Record<Tier, number> = { act_now: 0, this_week: 1, monitor: 2 };

/** Close rates measured from a workspace's own outcomes; null means "not enough data, use the assumption". */
export interface CloseRates {
  individual: number | null;
  company: number | null;
}

export function closeRateFor(lead: Lead, snap: Snapshot, rates?: CloseRates): { rate: number; measured: boolean } {
  const ownerType = lead.kind === "investor_purchase" || lead.owner.type === "company" ? "company" : "individual";
  const measured = rates?.[ownerType] ?? null;
  return measured === null
    ? { rate: snap.meta.assumptions.winRate[ownerType], measured: false }
    : { rate: measured, measured: true };
}

/** Expected gross profit for a contractor in `trade` pursuing this lead. */
export function expectedValue(lead: Lead, trade: TradeKey, snap: Snapshot, rates?: CloseRates): number {
  const { rate } = closeRateFor(lead, snap, rates);
  return tradeProbability(lead, trade, snap) * rate * snap.trades[trade].jobValue * snap.meta.assumptions.margin;
}

/** Probability that this lead turns into work for `trade` (historical rate, time-adjusted). */
export function tradeProbability(lead: Lead, trade: TradeKey, snap: Snapshot): number {
  if (lead.kind === "violation") return lead.probability;
  const model = snap.models.investorPurchase[lead.segment];
  const timeLeft = model ? Math.min(1, lead.probability / model.pAny) : 1;
  return lead.tradeProbabilities[trade] * timeLeft;
}

export function leadsForWorkspace(snap: Snapshot, trade: TradeKey, areas: number[]): Lead[] {
  const inArea = (a: number | null) => areas.length === 0 || (a !== null && areas.includes(a));
  return snap.leads.filter(
    (l) => inArea(l.communityArea) && (l.kind === "investor_purchase" || l.trade === trade),
  );
}

export function areaNames(snap: Snapshot): Map<number, string> {
  return new Map(snap.areas.map((a) => [a.id, a.name]));
}
