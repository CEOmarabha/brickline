import "server-only";

import { type BoardEvent, daysBetween, type EventBoard, type Partner, shiftDate } from "@/lib/event-board";
import type { Lifecycle, LifecyclesFile } from "@/lib/lifecycles";
import { type Lead, type LeadKind, type Snapshot, TRADE_KEYS, type TradeKey, tradeProbability } from "@/lib/snapshot";

/** The incumbent text lifecycles.py writes when public records don't show who has the job. */
export const INCUMBENT_UNKNOWN = "Not visible in public data: ask, or offer to match the current provider.";

export type StageState = "passed" | "now" | "next" | "undated";

export interface JobChance {
  trade: TradeKey;
  label: string;
  p: number;
}

export interface PossibleJob {
  name: string;
  vendorLabel: string | null;
  companies: number | null;
  withPhone: number | null;
  incumbent: string;
  incumbentShare: number | null;
  /** Measured chance of a permit for the job's trades on this lead, highest first. */
  chances: JobChance[];
  /** Public business listings that sell the job (events only). */
  partners: Partner[];
  /** Contractors this buyer named on earlier permits (investor leads, general-contractor job). */
  usedBefore: { name: string; jobs: number }[];
}

export interface JobStage {
  name: string;
  when: string;
  from: string | null;
  to: string | null;
  state: StageState;
  /** Days from `asOf` to the stage's start, for stages still ahead. */
  startsIn: number | null;
  jobs: PossibleJob[];
}

export interface JobsPlan {
  lifecycleId: string;
  lifecycleName: string;
  /** What the stage dates are counted from, e.g. "the sale" or "the event". */
  anchorLabel: string;
  anchor: string;
  asOf: string;
  stages: JobStage[];
  jobs: number;
  openNow: number;
  comingUp: number;
}

const LEAD_ANCHOR: Record<LeadKind, string> = {
  violation: "the citation",
  complaint: "the complaint",
  porch_request: "the inspection request",
  vacant: "the vacancy report",
  closed_restaurant: "the closure",
  investor_purchase: "the sale",
};

function stageState(from: string | null, to: string | null, asOf: string): StageState {
  if (from === null || to === null) return "undated";
  if (to < asOf) return "passed";
  return from > asOf ? "next" : "now";
}

function planJobs(
  lc: Lifecycle,
  data: LifecyclesFile,
  opts: {
    anchor: string;
    anchorLabel: string;
    asOf: string;
    chances?: Partial<Record<TradeKey, number>>;
    tradeLabel?: (t: TradeKey) => string;
    partners?: Record<string, Partner[]>;
    usedBefore?: { name: string; jobs: number }[];
  },
): JobsPlan {
  const stages = lc.stages.map((st): JobStage => {
    const from = st.offsetDays ? shiftDate(opts.anchor, st.offsetDays[0]) : null;
    const to = st.offsetDays ? shiftDate(opts.anchor, st.offsetDays[1]) : null;
    const state = stageState(from, to, opts.asOf);
    return {
      name: st.name,
      when: st.when,
      from,
      to,
      state,
      startsIn: state === "next" && from ? daysBetween(opts.asOf, from) : null,
      jobs: st.services.map((sv) => {
        const v = data.vendors[sv.vendor];
        const chances = sv.trades
          .flatMap((t) => {
            const p = opts.chances?.[t];
            return p === undefined ? [] : [{ trade: t, label: opts.tradeLabel?.(t) ?? t, p }];
          })
          .sort((a, b) => b.p - a.p);
        return {
          name: sv.name,
          vendorLabel: v?.label ?? null,
          companies: v?.companies ?? null,
          withPhone: v?.withPhone ?? null,
          incumbent: sv.incumbent,
          incumbentShare: sv.incumbentShare,
          chances,
          partners: opts.partners?.[sv.vendor] ?? [],
          usedBefore: sv.vendor === "gc" ? (opts.usedBefore ?? []) : [],
        };
      }),
    };
  });
  const jobsIn = (s: StageState) => stages.filter((st) => st.state === s).reduce((n, st) => n + st.jobs.length, 0);
  return {
    lifecycleId: lc.id,
    lifecycleName: lc.name,
    anchorLabel: opts.anchorLabel,
    anchor: opts.anchor,
    asOf: opts.asOf,
    stages,
    jobs: stages.reduce((n, st) => n + st.jobs.length, 0),
    openNow: jobsIn("now"),
    comingUp: jobsIn("next"),
  };
}

export function lifecycleForLead(lead: Lead, data: LifecyclesFile): Lifecycle | undefined {
  return data.lifecycles.find((l) => l.leadKinds.includes(lead.kind));
}

/**
 * The chance of a permit per trade this lead's data measures. Kinds without per-trade rates (violations, porch
 * requests) only measure their own trade, so other trades stay unknown rather than borrowing that rate.
 */
export function leadTradeChances(lead: Lead, snap: Snapshot): Partial<Record<TradeKey, number>> {
  if (lead.kind === "investor_purchase") {
    return Object.fromEntries(TRADE_KEYS.map((t) => [t, tradeProbability(lead, t, snap)]));
  }
  if (lead.tradeProbabilities) return lead.tradeProbabilities;
  return lead.trade ? { [lead.trade]: lead.probability } : {};
}

/** The lead's lifecycle with stage dates counted from its signal, as of the lead's own data date. */
export function leadJobs(lead: Lead, snap: Snapshot, data: LifecyclesFile): JobsPlan | null {
  const lc = lifecycleForLead(lead, data);
  if (!lc) return null;
  return planJobs(lc, data, {
    anchor: lead.signalDate,
    anchorLabel: LEAD_ANCHOR[lead.kind],
    asOf: shiftDate(lead.signalDate, lead.ageDays),
    chances: leadTradeChances(lead, snap),
    tradeLabel: (t) => snap.trades[t].label,
    usedBefore: lead.kind === "investor_purchase" ? lead.buyer.contractorsUsed : undefined,
  });
}

export function findBoardEvent(board: EventBoard, id: string): BoardEvent | undefined {
  return board.events.find((e) => e.id === id) ?? board.predicted.find((e) => e.id === id);
}

/** The event's lifecycle with stage dates counted back from the event day, with partner examples per job. */
export function eventJobs(e: BoardEvent, board: EventBoard, data: LifecyclesFile): JobsPlan | null {
  const lc = data.lifecycles.find((l) => l.id === e.lifecycle);
  if (!lc) return null;
  return planJobs(lc, data, {
    anchor: e.start,
    anchorLabel: "the event",
    asOf: board.asOf,
    partners: board.partners,
  });
}

/** The event board page for a row of the upcoming-events list, when the board has it (block parties use `bp-`). */
export function boardEventHref(eventsId: string, boardIds: ReadonlySet<string>): string | null {
  const id = eventsId.replace(/^cdot-(\d+)-blockparty$/, "bp-$1");
  return boardIds.has(id) ? `/event-board/${encodeURIComponent(id)}` : null;
}
