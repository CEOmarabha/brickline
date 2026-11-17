import "server-only";

import { cache } from "react";
import { type CloseRates, getSnapshot, ownerTypeFor, segmentOf, tradeProbability } from "@/lib/snapshot";
import { getEvents, getStatuses, getWorkspace, type LeadStatus } from "@/lib/workspace";

/** Decided outcomes (won + lost) needed before a measured close rate replaces the assumption. */
export const MIN_DECIDED = 10;

/** Won jobs with an entered value needed in one segment before its median replaces the permit-based typical job. */
export const MIN_VALUED_WON = 5;

const WORKED: LeadStatus[] = ["contacted", "meeting", "won", "lost"];

export interface SegmentOutcome {
  key: string;
  label: string;
  worked: number;
  meetings: number;
  won: number;
  lost: number;
  notRelevant: number;
  meetingRate: number | null;
  closeRate: number | null;
  medianDaysSignalToContact: number | null;
  /** Won leads where the user entered a job value. Everything below counts only those. */
  wonWithValue: number;
  totalWonValue: number;
  medianJobValue: number | null;
  /** Total won value divided by leads worked; null until at least one won job has a value. */
  revenuePerWorkedLead: number | null;
  /** True when the median job value is used in expected value for this segment (MIN_VALUED_WON or more). */
  jobValueMeasured: boolean;
}

/** Entered job values across every segment of this workspace. All dollars are exactly what the user typed. */
export interface RevenueTotals {
  worked: number;
  won: number;
  wonWithValue: number;
  totalWonValue: number;
  medianJobValue: number | null;
  revenuePerWorkedLead: number | null;
}

function median(xs: number[]): number | null {
  if (xs.length === 0) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Sums in whole cents so a column of entered amounts never picks up floating-point dust. */
function sumDollars(values: number[]): number {
  return values.reduce((t, v) => t + Math.round(v * 100), 0) / 100;
}

export const getOutcomes = cache(async () => {
  const [snap, statuses, events, ws] = await Promise.all([getSnapshot(), getStatuses(), getEvents(), getWorkspace()]);
  const byId = new Map(snap.leads.map((l) => [l.id, l]));
  const firstContact = new Map<string, Date>();
  const reached = new Map<string, Set<LeadStatus>>();
  for (const e of events) {
    if (WORKED.includes(e.status) && !firstContact.has(e.leadId)) firstContact.set(e.leadId, e.createdAt);
    const set = reached.get(e.leadId) ?? new Set<LeadStatus>();
    set.add(e.status);
    reached.set(e.leadId, set);
  }

  const segments = new Map<string, SegmentOutcome & { delays: number[]; values: number[] }>();
  // expectedJobs = sum of the model's chance of work over decided leads, for calibrating the close rate.
  const ownerTotals = {
    individual: { won: 0, lost: 0, expectedJobs: 0 },
    company: { won: 0, lost: 0, expectedJobs: 0 },
  };
  const allValues: number[] = [];

  for (const [leadId, st] of statuses) {
    const lead = byId.get(leadId);
    if (!lead || st.status === "new") continue;
    const seg = segmentOf(lead, snap);
    const row =
      segments.get(seg.key) ??
      {
        ...seg,
        worked: 0,
        meetings: 0,
        won: 0,
        lost: 0,
        notRelevant: 0,
        meetingRate: null,
        closeRate: null,
        medianDaysSignalToContact: null,
        wonWithValue: 0,
        totalWonValue: 0,
        medianJobValue: null,
        revenuePerWorkedLead: null,
        jobValueMeasured: false,
        delays: [],
        values: [],
      };
    const history = reached.get(leadId) ?? new Set([st.status]);
    if (st.status === "not_relevant") row.notRelevant++;
    if (WORKED.includes(st.status)) row.worked++;
    if (history.has("meeting") || st.status === "won") row.meetings++;
    if (st.status === "won") row.won++;
    if (st.status === "won" && st.jobValueUsd !== null) {
      row.values.push(st.jobValueUsd);
      allValues.push(st.jobValueUsd);
    }
    if (st.status === "lost") row.lost++;
    const contact = firstContact.get(leadId);
    if (contact) {
      const signal = new Date(`${lead.signalDate}T12:00:00`);
      row.delays.push(Math.max(0, Math.round((contact.getTime() - signal.getTime()) / 86_400_000)));
    }
    const ownerType = ownerTypeFor(lead);
    if (st.status === "won" || st.status === "lost") {
      ownerTotals[ownerType][st.status]++;
      ownerTotals[ownerType].expectedJobs += tradeProbability(lead, ws.trade, snap);
    }
    segments.set(seg.key, row);
  }

  const jobValues: Record<string, { median: number; n: number }> = {};
  const rows: SegmentOutcome[] = [...segments.values()]
    .map(({ delays, values, ...r }) => {
      const med = median(values);
      const total = sumDollars(values);
      const measuredValue = med !== null && values.length >= MIN_VALUED_WON;
      if (measuredValue) jobValues[r.key] = { median: med, n: values.length };
      return {
        ...r,
        meetingRate: r.worked > 0 ? r.meetings / r.worked : null,
        closeRate: r.won + r.lost > 0 ? r.won / (r.won + r.lost) : null,
        medianDaysSignalToContact: median(delays),
        wonWithValue: values.length,
        totalWonValue: total,
        medianJobValue: med,
        revenuePerWorkedLead: values.length > 0 && r.worked > 0 ? total / r.worked : null,
        jobValueMeasured: measuredValue,
      };
    })
    .sort((a, b) => b.worked - a.worked);

  const revenue: RevenueTotals = {
    worked: rows.reduce((t, r) => t + r.worked, 0),
    won: rows.reduce((t, r) => t + r.won, 0),
    wonWithValue: allValues.length,
    totalWonValue: sumDollars(allValues),
    medianJobValue: median(allValues),
    revenuePerWorkedLead: null,
  };
  if (revenue.wonWithValue > 0 && revenue.worked > 0) revenue.revenuePerWorkedLead = revenue.totalWonValue / revenue.worked;

  // Calibrated close rate: wins divided by the jobs the model expected among decided leads (capped at 1).
  const measured = (t: { won: number; lost: number; expectedJobs: number }) =>
    t.won + t.lost >= MIN_DECIDED && t.expectedJobs > 0 ? Math.min(1, t.won / t.expectedJobs) : null;
  const rates: CloseRates = {
    individual: measured(ownerTotals.individual),
    company: measured(ownerTotals.company),
    ...(Object.keys(jobValues).length > 0 ? { jobValues } : {}),
  };

  return {
    rows,
    rates,
    ownerTotals,
    revenue,
    /** The permit-based typical job for this workspace's trade: what expected value uses without enough entered values. */
    permitJobValue: snap.trades[ws.trade].jobValue,
    tradeLabel: snap.trades[ws.trade].label,
  };
});

export async function getCloseRates(): Promise<CloseRates> {
  return (await getOutcomes()).rates;
}
