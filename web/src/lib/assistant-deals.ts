import "server-only";

import type { ToolContext } from "@/lib/assistant-tools";
import { getDealEventTimes, getDeals } from "@/lib/deal-store";
import { computeDealMetrics, type Funnel } from "@/lib/deal-metrics";
import {
  BUYER_TYPE_LABEL,
  DEAL_SOURCE_LABEL,
  DEAL_STATUS_LABEL,
  DEAL_STATUS_VALUES,
  type DealRow,
  daysBetween,
  dealNextStep,
  isDealDue,
} from "@/lib/deals";
import { dateLabel, pct } from "@/lib/format";
import { todayChicago } from "@/lib/pipeline";

/*
 * The founder's deals, for the assistant. Results are sent to the AI provider, so they never carry anything that
 * identifies or contacts a buyer: no names, titles (which often hold a name), links to the public post (which hold a
 * handle), contact info, locations, budgets, needs, lost reasons or notes. A deal is described by its type, source
 * kind, event date and id, with a link to the page where the founder sees the rest.
 */

const NEEDS_SIGN_IN = { error: "Sign in required: the deal tools read your private deal pipeline." };
const DUE_LIMIT = 25;

const dealLink = (id: string) => `/deals/${encodeURIComponent(id)}`;

/** "Person deal, event Jun 14, 2026": type and date only. */
function dealLabel(d: DealRow): string {
  return `${BUYER_TYPE_LABEL[d.buyerType]} deal, ${d.eventDate ? `event ${dateLabel(d.eventDate)}` : "no date"}`;
}

function funnelFacts(f: Funnel) {
  return {
    deals: f.deals,
    contacted: f.contacted,
    replied: f.replied,
    booked: f.booked,
    reply_rate_of_contacted: f.replyRate === null ? null : pct(f.replyRate, 0),
    booked_of_contacted: f.bookedOfContacted === null ? null : pct(f.bookedOfContacted, 0),
  };
}

export interface DealsStatusResult {
  today: string;
  deals_total: number;
  counts_by_status: Record<string, number>;
  do_not_contact_total: number;
  due_total: number;
  due: {
    deal_id: string;
    label: string;
    source: string;
    status: string;
    days_until_event: number | null;
    follow_up_date: string;
    days_overdue: number;
    next_step: string;
    partners_attached: number;
    link: string;
  }[];
  money_from_your_records: {
    total_quoted_usd: number | null;
    deals_with_a_quote: number;
    fees_on_booked_or_completed_usd: number | null;
    deals_with_a_fee: number;
    average_fee_usd: number | null;
    fees_collected_usd: number | null;
  };
  funnel_from_your_records: ReturnType<typeof funnelFacts> & { median_days_found_to_booked: number | null };
  by_source: ({ source: string } & ReturnType<typeof funnelFacts>)[];
  privacy_note: string;
}

/** The founder's deal pipeline (owner-scoped), with no buyer identity or contact details. */
export async function dealsStatus(ctx: ToolContext): Promise<DealsStatusResult | { error: string }> {
  const owner = ctx.owner;
  if (!owner) return NEEDS_SIGN_IN;
  const [deals, events] = await Promise.all([getDeals(owner), getDealEventTimes(owner)]);
  const today = todayChicago();
  const metrics = computeDealMetrics(deals, events);

  const due = deals
    .filter((d) => isDealDue(d, today))
    .sort((a, b) => (a.nextFollowUp ?? "").localeCompare(b.nextFollowUp ?? "") || a.id.localeCompare(b.id));

  return {
    today,
    deals_total: deals.length,
    counts_by_status: Object.fromEntries(DEAL_STATUS_VALUES.map((s) => [DEAL_STATUS_LABEL[s], metrics.total.byStatus[s]])),
    do_not_contact_total: metrics.total.byStatus.opted_out,
    due_total: due.length,
    due: due.slice(0, DUE_LIMIT).map((d) => ({
      deal_id: d.id,
      label: dealLabel(d),
      source: DEAL_SOURCE_LABEL[d.source],
      status: DEAL_STATUS_LABEL[d.status],
      days_until_event: d.eventDate ? daysBetween(today, d.eventDate) : null,
      follow_up_date: d.nextFollowUp as string,
      days_overdue: Math.max(0, daysBetween(d.nextFollowUp as string, today)),
      next_step: dealNextStep(d),
      partners_attached: d.partnerIds.length,
      link: dealLink(d.id),
    })),
    money_from_your_records: {
      total_quoted_usd: metrics.quoted.count > 0 ? metrics.quoted.totalUsd : null,
      deals_with_a_quote: metrics.quoted.count,
      fees_on_booked_or_completed_usd: metrics.fees.count > 0 ? metrics.fees.totalUsd : null,
      deals_with_a_fee: metrics.fees.count,
      average_fee_usd: metrics.fees.averageUsd,
      fees_collected_usd: metrics.collected.count > 0 ? metrics.collected.totalUsd : null,
    },
    funnel_from_your_records: { ...funnelFacts(metrics.total), median_days_found_to_booked: metrics.daysToBooked.median },
    by_source: metrics.bySource.map((s) => ({ source: DEAL_SOURCE_LABEL[s.source], ...funnelFacts(s) })),
    privacy_note:
      "Buyer names, titles, handles, contact details, locations, budgets and notes are deliberately not included. Refer to a deal by its type, event date and link; the founder sees the details on its page. No message to a buyer is drafted here.",
  };
}
