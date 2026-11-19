import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";
import type { LeadKindKey } from "@/lib/kinds";

export type TradeKey = "porch" | "masonry" | "roofing" | "plumbing" | "electrical" | "general";
export type Tier = "act_now" | "this_week" | "monitor";
export type LeadKind = LeadKindKey;

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
  /** Set when the mailing address is not the property's own tax-roll entry. */
  mailingSource?: "tax_roll_by_buyer_name";
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
  /** Chance of work per trade for kinds that cover several trades (already time-adjusted unless noted in the basis). */
  tradeProbabilities?: Partial<Record<TradeKey, number>>;
  /** On the City's Building Code Scofflaw List. Evidence only: signal lab H42 found no lift, so it does not affect ranking. */
  scofflaw?: { listedSince: string | null; cases: number };
}

export interface ViolationLead extends LeadBase {
  kind: "violation";
  trade: TradeKey;
  expectedValue: number;
  jobValue: number;
}

/** 311 building complaint with no city violation yet; `probability` is the chance it gets cited. */
export interface ComplaintLead extends LeadBase {
  kind: "complaint";
  tradeProbabilities: Partial<Record<TradeKey, number>>;
}

/** 311 porch inspection request with no porch permit yet; `probability` is the chance of a porch permit. */
export interface PorchRequestLead extends LeadBase {
  kind: "porch_request";
  trade: "porch";
}

/** 311 vacant/abandoned building complaint with no sale yet; `probability` is the chance it sells. */
export interface VacantLead extends LeadBase {
  kind: "vacant";
  tradeProbabilities: Partial<Record<TradeKey, number>>;
}

/**
 * Restaurant recorded out of business, no new food license under another name yet. `probability` is the chance a
 * different food business is licensed at the address within a year; `tradeProbabilities.general` the chance of a
 * renovation or build-out permit (a weak signal).
 */
export interface ClosedRestaurantLead extends LeadBase {
  kind: "closed_restaurant";
  trade: "general";
  tradeProbabilities: Partial<Record<TradeKey, number>>;
  restaurant: { name: string | null; licenseNo: number | null };
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
    /** Other parcels on the county tax roll under the buyer's exact name. */
    parcelsOnRoll?: number;
    contractorsUsed: { name: string; jobs: number }[];
  };
  permitsSince: PermitSummary[];
  /** Where the sale came from: the Assessor's sales, or a state transfer declaration the Assessor has not loaded yet. */
  saleSource?: "assessor" | "ptax";
}

export type Lead =
  | ViolationLead
  | ComplaintLead
  | PorchRequestLead
  | VacantLead
  | ClosedRestaurantLead
  | InvestorLead;

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

export interface RoofingBlock {
  id: string;
  communityArea: number | null;
  recentReroofs: number;
  lastPermit: string;
  residentialParcels: number;
  addresses: string[];
}

export interface RoofingBlockModel {
  exposedRate: number;
  baseRate: number;
  lift: number;
  exposedCases: number;
  baseCases: number;
  horizonDays: number;
  period: string;
}

/** One outcome of the closed-restaurant model: rate within a year, matched baseline, lift and timing (days). */
export interface ClosedRestaurantOutcome {
  p365: number;
  baseline365: number;
  lift: number;
  medianDays: number;
  daysP25: number;
  daysP75: number;
}

export interface PermitContractor {
  name: string;
  role: string;
}

export interface NewBusinessModel {
  period: string;
  signals: number;
  /** Share of signals followed by a new business license at the address within 365 days. */
  rate: number;
  /** Matched control: comparable unlicensed addresses with no renovation permit nearby, same class and year mix. */
  matchedRate: number;
  lift: number;
  /** Control: unlicensed addresses with some other permit in the prior 90 days. */
  busyRate: number;
  liftVsBusy: number;
  medianDays: number;
  daysP25: number;
  daysP75: number;
  perWeek: number;
  byClass: { class: string; signals: number; rate: number; matchedRate: number; lift: number }[];
  byGroup: { group: string; share: number }[];
}

/** A build-out permit at a commercial, mixed-use or 7+ unit address with no business license since (H33). */
export interface NewBusinessSpace {
  id: string;
  address: string;
  communityArea: number | null;
  class: string;
  permitDate: string;
  ageDays: number;
  reportedCost: number | null;
  workDescription: string;
  contractors: PermitContractor[];
  applicant: string | null;
  owner: { name: string | null; company: boolean; mailing: string | null };
  alsoClosedRestaurant: boolean;
  /** The class's historical rate of a new license within a year, not adjusted for time passed. */
  classRate: number;
  /** `classRate` conditioned on the days since the permit (no license yet). */
  historicalRate: number;
  sourceUrl: string;
}

export interface OpenTradeRow {
  trade: string;
  label: string;
  signals: number;
  /** Share of big permits followed by any permit for this trade at the address within 540 days. */
  followOnRate: number;
  /** Share of big permits followed by this trade's permit with a contractor not named on the big permit. */
  newContractorRate: number;
  /** Share of the trade's follow-on permits whose contractor was not named on the big permit. */
  newShare: number | null;
  lockedShare: number | null;
  unnamedShare: number | null;
  liftVsBusy: number | null;
  medianDays: number | null;
  daysP25: number | null;
  daysP75: number | null;
  mostlyLockedIn: boolean;
}

export interface OpenTradesModel {
  period: string;
  bigPermits: number;
  perWeek: number;
  perWeekClassKnown: number;
  medianDays: number;
  daysP25: number;
  daysP75: number;
  headlineTrades: string[];
  followOnRate: number;
  liftVsBusy: number;
  byTrade: OpenTradeRow[];
}

export interface BigPermit {
  id: string;
  address: string;
  communityArea: number | null;
  class: string;
  permitType: string;
  permitDate: string;
  ageDays: number;
  reportedCost: number;
  description: string;
  contractors: PermitContractor[];
  /** Follow-on trade keys (see `OpenTradeRow.trade`) already seen at the address since the permit. */
  appeared: string[];
  sourceUrl: string;
}

export interface Snapshot {
  meta: {
    generatedAt: string;
    dataAsOf: {
      permits: string;
      violations: string;
      sales: string;
      /** Newest state transfer declaration (PTAX-203); investor leads use these sales before the Assessor has them. */
      transfers?: string;
      complaints: string;
      foodInspections: string;
    };
    investorSales?: { newestSale: string; transferRowsAdded: number; transferRowsUsable: number };
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
    complaint: {
      period: string;
      episodes: number;
      pViolation120: number;
      medianDaysToViolation: number | null;
      pTrade365: Partial<Record<TradeKey, number>>;
    };
    porchRequest: { period: string; episodes: number; pPorch365: number };
    vacant: {
      period: string;
      episodes: number;
      pSale365: number;
      permitPeriod: string;
      permitEpisodes: number;
      pTrade730: Record<TradeKey, number>;
    };
    closedRestaurant: {
      period: string;
      episodes: number;
      closuresPerWeek: number;
      license: ClosedRestaurantOutcome;
      licenseAfter30: ClosedRestaurantOutcome;
      permit: ClosedRestaurantOutcome;
    };
    masonryAge: {
      useCells: boolean;
      age: Record<"pre1910" | "other", { episodes: number; p365: number }>;
      cells: Record<string, { episodes: number; p365: number }>;
    };
  };
  leads: Lead[];
  recentWins: RecentWin[];
  competitors: Record<TradeKey, { contractors: Competitor[]; violationJobsWon: { name: string; jobs: number }[] }>;
  areas: Area[];
  blocks: { roofing: RoofingBlock[]; roofingModel: RoofingBlockModel };
  commercial: {
    preApplication: { baseRate: number; projects: PreAppProject[] };
    gcTargets: Record<"electrical" | "plumbing" | "hvac", GcTarget[]>;
    newBusiness: { model: NewBusinessModel; spacesTotal: number; spaces: NewBusinessSpace[] };
    openTrades: { model: OpenTradesModel; recentTotal: number; recent: BigPermit[] };
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

/**
 * What a workspace's own outcomes have measured. A null close rate means "not enough data, use the assumption".
 * `jobValues` holds the median job value the user entered on won leads, by results segment (`segmentOf`), and only for
 * segments with enough won jobs to trust it; absent segments keep the permit-based typical job.
 */
export interface CloseRates {
  individual: number | null;
  company: number | null;
  jobValues?: Record<string, { median: number; n: number }>;
}

/** The results segment a lead belongs to: the unit that outcomes and measured job values are grouped by. */
export function segmentOf(lead: Lead, snap: Snapshot): { key: string; label: string } {
  if (lead.kind === "investor_purchase") {
    return lead.buyer.purchases24m >= 3
      ? { key: "investor-repeat", label: "Repeat investor purchases" }
      : { key: "investor", label: "Investor purchases" };
  }
  const owner = lead.owner.type === "company" ? "company-owned" : "individual-owned";
  switch (lead.kind) {
    case "complaint":
      return { key: `complaint-${owner}`, label: `311 building complaints, ${owner}` };
    case "porch_request":
      return { key: `porch-request-${owner}`, label: `Porch inspection requests, ${owner}` };
    case "vacant":
      return { key: `vacant-${owner}`, label: `Vacant buildings, ${owner}` };
    case "closed_restaurant":
      return { key: `closed-restaurant-${owner}`, label: `Closed restaurant spaces, ${owner}` };
    case "violation":
      return { key: `violation-${lead.trade}-${owner}`, label: `${snap.trades[lead.trade].label} violations, ${owner}` };
  }
}

/** Investor and vacant-building leads are worked like company leads (business contact, not homeowner mail). */
export function ownerTypeFor(lead: Lead): "individual" | "company" {
  return lead.kind === "investor_purchase" || lead.kind === "vacant" || lead.owner.type === "company"
    ? "company"
    : "individual";
}

export function closeRateFor(lead: Lead, snap: Snapshot, rates?: CloseRates): { rate: number; measured: boolean } {
  const ownerType = ownerTypeFor(lead);
  const measured = rates?.[ownerType] ?? null;
  return measured === null
    ? { rate: snap.meta.assumptions.winRate[ownerType], measured: false }
    : { rate: measured, measured: true };
}

/**
 * The job value behind a lead's expected value: the median the user entered on won leads of the same segment once
 * there are enough of them (`rates.jobValues`), else the permit-based typical job for the trade.
 */
export function jobValueFor(
  lead: Lead,
  trade: TradeKey,
  snap: Snapshot,
  rates?: CloseRates,
): { value: number; measured: boolean; n: number } {
  const m = rates?.jobValues ? rates.jobValues[segmentOf(lead, snap).key] : undefined;
  return m
    ? { value: m.median, measured: true, n: m.n }
    : { value: snap.trades[trade].jobValue, measured: false, n: 0 };
}

/** Expected gross profit for a contractor in `trade` pursuing this lead. */
export function expectedValue(lead: Lead, trade: TradeKey, snap: Snapshot, rates?: CloseRates): number {
  const { rate } = closeRateFor(lead, snap, rates);
  const { value } = jobValueFor(lead, trade, snap, rates);
  return tradeProbability(lead, trade, snap) * rate * value * snap.meta.assumptions.margin;
}

/** Probability that this lead turns into work for `trade` (historical rate, time-adjusted where the kind allows). */
export function tradeProbability(lead: Lead, trade: TradeKey, snap: Snapshot): number {
  if (lead.kind === "investor_purchase") {
    const model = snap.models.investorPurchase[lead.segment];
    const timeLeft = model ? Math.min(1, lead.probability / model.pAny) : 1;
    return lead.tradeProbabilities[trade] * timeLeft;
  }
  if (lead.tradeProbabilities) return lead.tradeProbabilities[trade] ?? 0;
  return lead.probability;
}

export function leadsForWorkspace(snap: Snapshot, trade: TradeKey, areas: number[]): Lead[] {
  const inArea = (a: number | null) => areas.length === 0 || (a !== null && areas.includes(a));
  return snap.leads.filter((l) => inArea(l.communityArea) && l.trades.includes(trade));
}

/** Signals in the last 90 days and the same period a year earlier: major projects for general contractors, violations for every other trade. */
export function areaSignal(area: Area, trade: TradeKey): { now: number; before: number } {
  if (trade === "general") return { now: area.majorProjects.last90, before: area.majorProjects.lastYear };
  const v = area.violations[trade];
  return { now: v?.last90 ?? 0, before: v?.lastYear ?? 0 };
}

export function areaNames(snap: Snapshot): Map<number, string> {
  return new Map(snap.areas.map((a) => [a.id, a.name]));
}
