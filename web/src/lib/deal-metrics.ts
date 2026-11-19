import {
  DEAL_SOURCES,
  DEAL_STATUS_VALUES,
  type DealSource,
  type DealStatus,
  stageRank,
  daysBetween,
} from "@/lib/deals";
import { dollarsToCents } from "@/lib/money-input";
import { todayChicago } from "@/lib/pipeline";

/*
 * Funnel metrics computed from the founder's own deal records. Nothing is estimated: a deal counts as having
 * "reached" a stage when its status, or any status in its history, is that stage or a later one on the forward path
 * (Found, Contacted, Replied, Interested, Quoted, Booked, Completed). Lost and Opted out keep what they reached.
 */

export interface MetricDeal {
  id: string;
  source: DealSource;
  status: DealStatus;
  createdAt: Date;
  quoteUsd: number | null;
  feeUsd: number | null;
  feeCollected: boolean;
}

export interface MetricEvent {
  dealId: string;
  status: DealStatus;
  createdAt: Date;
}

export interface Funnel {
  deals: number;
  byStatus: Record<DealStatus, number>;
  contacted: number;
  replied: number;
  booked: number;
  /** Replied of contacted; null when nobody was contacted. */
  replyRate: number | null;
  /** Booked of contacted. */
  bookedOfContacted: number | null;
  /** Booked of replied. */
  bookedOfReplied: number | null;
}

export interface DealMetrics {
  total: Funnel;
  /** Only the sources that have at least one deal, in the order of DEAL_SOURCES. */
  bySource: ({ source: DealSource } & Funnel)[];
  quoted: { count: number; totalUsd: number };
  /** Your fee on Booked and Completed deals that have a fee entered. */
  fees: { count: number; totalUsd: number; averageUsd: number | null };
  collected: { count: number; totalUsd: number };
  daysToBooked: { count: number; median: number | null };
}

const BOOKED_RANK = stageRank("booked");
const MIN_RANK_CONTACTED = stageRank("contacted");
const MIN_RANK_REPLIED = stageRank("replied");

const rate = (n: number, d: number): number | null => (d > 0 ? n / d : null);

function emptyByStatus(): Record<DealStatus, number> {
  return Object.fromEntries(DEAL_STATUS_VALUES.map((s) => [s, 0])) as Record<DealStatus, number>;
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function funnel(deals: MetricDeal[], reached: Map<string, number>): Funnel {
  const byStatus = emptyByStatus();
  let contacted = 0;
  let replied = 0;
  let booked = 0;
  for (const d of deals) {
    byStatus[d.status]++;
    const r = reached.get(d.id) ?? 0;
    if (r >= MIN_RANK_CONTACTED) contacted++;
    if (r >= MIN_RANK_REPLIED) replied++;
    if (r >= BOOKED_RANK) booked++;
  }
  return {
    deals: deals.length,
    byStatus,
    contacted,
    replied,
    booked,
    replyRate: rate(replied, contacted),
    bookedOfContacted: rate(booked, contacted),
    bookedOfReplied: rate(booked, replied),
  };
}

export function computeDealMetrics(deals: MetricDeal[], events: MetricEvent[]): DealMetrics {
  const reached = new Map<string, number>();
  const bookedAt = new Map<string, Date>();
  for (const d of deals) reached.set(d.id, Math.max(0, stageRank(d.status)));
  for (const e of events) {
    const rank = stageRank(e.status);
    if (!reached.has(e.dealId)) continue;
    reached.set(e.dealId, Math.max(reached.get(e.dealId) ?? 0, rank));
    if (rank >= BOOKED_RANK && !bookedAt.has(e.dealId)) bookedAt.set(e.dealId, e.createdAt);
  }

  const bySource = DEAL_SOURCES.flatMap((source) => {
    const list = deals.filter((d) => d.source === source);
    return list.length === 0 ? [] : [{ source, ...funnel(list, reached) }];
  });

  let quotedCents = 0;
  let quotedCount = 0;
  let feeCents = 0;
  let feeCount = 0;
  let collectedCents = 0;
  let collectedCount = 0;
  const days: number[] = [];
  for (const d of deals) {
    const quote = dollarsToCents(d.quoteUsd);
    if (quote !== null) {
      quotedCents += quote;
      quotedCount++;
    }
    const fee = dollarsToCents(d.feeUsd);
    if (fee !== null && fee > 0) {
      if (d.status === "booked" || d.status === "completed") {
        feeCents += fee;
        feeCount++;
      }
      if (d.feeCollected) {
        collectedCents += fee;
        collectedCount++;
      }
    }
    const booked = bookedAt.get(d.id);
    if (booked) days.push(Math.max(0, daysBetween(todayChicago(d.createdAt), todayChicago(booked))));
  }

  return {
    total: funnel(deals, reached),
    bySource,
    quoted: { count: quotedCount, totalUsd: quotedCents / 100 },
    fees: { count: feeCount, totalUsd: feeCents / 100, averageUsd: feeCount > 0 ? feeCents / feeCount / 100 : null },
    collected: { count: collectedCount, totalUsd: collectedCents / 100 },
    daysToBooked: { count: days.length, median: median(days) },
  };
}
