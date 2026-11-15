import "server-only";

import { ago, change, count, pct } from "@/lib/format";
import {
  expectedValue,
  type InvestorLead,
  type Lead,
  type Snapshot,
  type TradeKey,
} from "@/lib/snapshot";
import type { LeadStatusRow, Workspace } from "@/lib/workspace";

export interface Insight {
  id: string;
  title: string;
  detail: string;
  href?: string;
  cta?: string;
  kind: "opportunity" | "market" | "competition" | "follow_up" | "data";
}

const FOLLOW_UP_DAYS = 21;

/** Suggested next moves, each computed from the snapshot and the workspace's own pipeline. */
export function buildInsights(
  snap: Snapshot,
  ws: Workspace,
  leads: Lead[],
  statuses: Map<string, LeadStatusRow>,
): Insight[] {
  const out: Insight[] = [];
  const trade = ws.trade;
  const tradeLabel = snap.trades[trade].label.toLowerCase();
  const open = leads.filter((l) => !statuses.has(l.id));

  const repeatInvestors = open.filter(
    (l): l is InvestorLead => l.kind === "investor_purchase" && l.buyer.purchases24m >= 3 && l.tier === "act_now",
  );
  if (repeatInvestors.length > 0) {
    const top = [...repeatInvestors].sort((a, b) => b.buyer.purchases24m - a.buyer.purchases24m)[0];
    out.push({
      id: "repeat-investors",
      kind: "opportunity",
      title: `Call ${count(repeatInvestors.length)} repeat investors first`,
      detail: `${top.buyer.name} has bought ${top.buyer.purchases24m} properties in two years, most recently ${top.address}. Investors who keep buying need a reliable crew for every property.`,
      href: "/leads?kind=investor_purchase&tier=act_now",
      cta: "See repeat investors",
    });
  }

  const freshViolations = open.filter((l) => l.kind === "violation" && l.ageDays <= 14);
  if (freshViolations.length > 0 && trade !== "general") {
    const ev = freshViolations.reduce((s, l) => s + expectedValue(l, trade, snap), 0);
    out.push({
      id: "fresh-violations",
      kind: "opportunity",
      title: `${count(freshViolations.length)} owners were ordered to fix ${tradeLabel} work in the last 2 weeks`,
      detail: `Historically ${pct(snap.models.violation[trade]?.individual.p365)} of these lead to a permitted repair within a year, most after 3+ months. Mailing now puts you first in line. Combined expected value at your assumptions: ${Math.round(ev).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })}.`,
      href: "/leads?kind=violation&tier=act_now",
      cta: "Review new violations",
    });
  }

  const areaPool = snap.areas.filter((a) => ws.areas.length === 0 || ws.areas.includes(a.id));
  const metric = (a: (typeof areaPool)[number]) =>
    trade === "general"
      ? { now: a.majorProjects.last90, before: a.majorProjects.lastYear, what: "major renovations" }
      : {
          now: a.violations[trade]?.last90 ?? 0,
          before: a.violations[trade]?.lastYear ?? 0,
          what: `${tradeLabel} violations`,
        };
  const rising = areaPool
    .map((a) => ({ a, ...metric(a) }))
    .filter((x) => x.now >= 5 && x.now > x.before * 1.25)
    .sort((x, y) => y.now - y.before - (x.now - x.before))[0];
  if (rising) {
    const c = change(rising.now, rising.before);
    out.push({
      id: "rising-area",
      kind: "market",
      title: `${rising.a.name} is heating up`,
      detail: `${count(rising.now)} ${rising.what} in the last 90 days vs ${count(rising.before)} in the same period last year (${c.label}). Consider concentrating mail and door hangers there.`,
      href: "/areas",
      cta: "Compare neighborhoods",
    });
  }

  const comp = snap.competitors[trade];
  const leader = comp?.violationJobsWon[0];
  if (leader && leader.jobs >= 2) {
    out.push({
      id: "competitor",
      kind: "competition",
      title: `${leader.name} is winning violation-driven ${tradeLabel} jobs`,
      detail: `They pulled permits on ${leader.jobs} recent violation addresses in this snapshot. Faster first contact is how you take share from them.`,
      href: "/market",
      cta: "See the market",
    });
  } else if (comp?.contractors[0]) {
    const c = comp.contractors[0];
    out.push({
      id: "competitor",
      kind: "competition",
      title: `${c.name} leads ${tradeLabel} permits citywide`,
      detail: `${count(c.jobs12m)} permitted jobs in 12 months (${pct(c.share)} of the market).`,
      href: "/market",
      cta: "See the market",
    });
  }

  const now = Date.now();
  const due = [...statuses.values()].filter(
    (s) => s.status === "contacted" && now - s.updatedAt.getTime() > FOLLOW_UP_DAYS * 86_400_000,
  );
  if (due.length > 0) {
    out.push({
      id: "follow-ups",
      kind: "follow_up",
      title: `${count(due.length)} follow-ups are due`,
      detail: `You contacted these more than ${FOLLOW_UP_DAYS} days ago. Most permitted repairs happen 3–9 months after the signal, so a second touch matters.`,
      href: "/leads?status=contacted",
      cta: "Open follow-ups",
    });
  }

  const salesAge = Math.round((now - new Date(`${snap.meta.dataAsOf.sales}T12:00:00`).getTime()) / 86_400_000);
  out.push({
    id: "sales-lag",
    kind: "data",
    title: "Property sales arrive with a lag",
    detail: `Cook County publishes sales months after they close; the newest sale in this snapshot is from ${ago(salesAge)}. Investor leads are still worth calling because repeat buyers keep buying.`,
  });

  if (trade === "general" || trade === "electrical" || trade === "plumbing") {
    const projects = snap.commercial.preApplication.projects.filter(
      (p) => ws.areas.length === 0 || (p.communityArea !== null && ws.areas.includes(p.communityArea)),
    );
    if (projects.length > 0) {
      out.splice(1, 0, {
        id: "pre-application",
        kind: "opportunity",
        title: `${count(projects.length)} properties look likely to file a $100k+ project soon`,
        detail: `Parcels with the same signal combination filed a major permit within 180 days ${pct(projects[0].probability)} of the time, about ${Math.round(projects[0].lift)}× the citywide rate. Bidding happens before permits are issued.`,
        href: "/commercial",
        cta: "See pre-application projects",
      });
    }
  }

  return out;
}

export function tradeNoun(trade: TradeKey): string {
  return {
    porch: "porch",
    masonry: "masonry",
    roofing: "roof",
    plumbing: "plumbing",
    electrical: "electrical",
    general: "renovation",
  }[trade];
}
