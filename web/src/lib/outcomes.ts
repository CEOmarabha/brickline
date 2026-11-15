import "server-only";

import { cache } from "react";
import { type CloseRates, getSnapshot, type Lead, type Snapshot, tradeProbability } from "@/lib/snapshot";
import { getEvents, getStatuses, getWorkspace, type LeadStatus } from "@/lib/workspace";

/** Decided outcomes (won + lost) needed before a measured close rate replaces the assumption. */
export const MIN_DECIDED = 10;

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
}

function segmentOf(lead: Lead, snap: Snapshot): { key: string; label: string } {
  if (lead.kind === "investor_purchase") {
    return lead.buyer.purchases24m >= 3
      ? { key: "investor-repeat", label: "Repeat investor purchases" }
      : { key: "investor", label: "Investor purchases" };
  }
  const owner = lead.owner.type === "company" ? "company-owned" : "individual-owned";
  return { key: `violation-${lead.trade}-${owner}`, label: `${snap.trades[lead.trade].label} violations, ${owner}` };
}

function median(xs: number[]): number | null {
  if (xs.length === 0) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
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

  const segments = new Map<string, SegmentOutcome & { delays: number[] }>();
  // expectedJobs = sum of the model's chance of work over decided leads, for calibrating the close rate.
  const ownerTotals = {
    individual: { won: 0, lost: 0, expectedJobs: 0 },
    company: { won: 0, lost: 0, expectedJobs: 0 },
  };
  let unknown = 0;

  for (const [leadId, st] of statuses) {
    const lead = byId.get(leadId);
    if (!lead) {
      unknown++;
      continue;
    }
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
        delays: [],
      };
    const history = reached.get(leadId) ?? new Set([st.status]);
    if (st.status === "not_relevant") row.notRelevant++;
    if (WORKED.includes(st.status)) row.worked++;
    if (history.has("meeting") || st.status === "won") row.meetings++;
    if (st.status === "won") row.won++;
    if (st.status === "lost") row.lost++;
    const contact = firstContact.get(leadId);
    if (contact) {
      const signal = new Date(`${lead.signalDate}T12:00:00`);
      row.delays.push(Math.max(0, Math.round((contact.getTime() - signal.getTime()) / 86_400_000)));
    }
    const ownerType = lead.kind === "investor_purchase" || lead.owner.type === "company" ? "company" : "individual";
    if (st.status === "won" || st.status === "lost") {
      ownerTotals[ownerType][st.status]++;
      ownerTotals[ownerType].expectedJobs += tradeProbability(lead, ws.trade, snap);
    }
    segments.set(seg.key, row);
  }

  const rows: SegmentOutcome[] = [...segments.values()]
    .map(({ delays, ...r }) => ({
      ...r,
      meetingRate: r.worked > 0 ? r.meetings / r.worked : null,
      closeRate: r.won + r.lost > 0 ? r.won / (r.won + r.lost) : null,
      medianDaysSignalToContact: median(delays),
    }))
    .sort((a, b) => b.worked - a.worked);

  // Calibrated close rate: wins divided by the jobs the model expected among decided leads (capped at 1).
  const measured = (t: { won: number; lost: number; expectedJobs: number }) =>
    t.won + t.lost >= MIN_DECIDED && t.expectedJobs > 0 ? Math.min(1, t.won / t.expectedJobs) : null;
  const rates: CloseRates = { individual: measured(ownerTotals.individual), company: measured(ownerTotals.company) };

  return { rows, rates, ownerTotals, unknown };
});

export async function getCloseRates(): Promise<CloseRates> {
  return (await getOutcomes()).rates;
}
