import "server-only";

import { daysBetween } from "@/lib/deals";
import type { EventsFile, UpcomingEvent } from "@/lib/events";
import { count, dateLabel, pct } from "@/lib/format";
import { findingsFor, type PestFile } from "@/lib/pest";
import type { ClosedRestaurantLead, Snapshot } from "@/lib/snapshot";
import type { TargetKey } from "@/lib/targets";

/** How many rows the dashboard shows from a list. */
export const TOP_ROWS = 5;

export interface SummaryStat {
  label: string;
  value: string;
  hint?: string;
}

export interface SummaryRow {
  id: string;
  title: string;
  subtitle: string;
  meta: string;
  href?: string;
}

/** Counts and top rows of one target's list, ready to render. Every number is read from the data files. */
export interface ListSummary {
  stats: SummaryStat[];
  rowsTitle: string;
  rows: SummaryRow[];
  /** Where the full list lives, and what to call the link. */
  listHref: string;
  listLabel: string;
  note: string;
}

export interface EventsSummary {
  /** Events that name an organization, counted from today. */
  organizations: { next30: number; next60: number; next120: number };
  recurringNext90: number;
  blockPartiesNext60: number;
  /** The next events that name an organization, soonest first. */
  nextEvents: UpcomingEvent[];
}

/**
 * Counts from today, not from the day the file was built: an event that already ended is not upcoming. Events and
 * block parties are measured from their own dates; a recurring series only has `daysUntilExpected`, which is relative
 * to the file's `asOf` date, so the days elapsed since then are taken off it.
 */
export function summarizeEvents(file: EventsFile, today: string): EventsSummary {
  const elapsed = Math.max(0, daysBetween(file.asOf, today));
  const live = file.upcoming.filter((e) => e.endDate >= today);
  const withOrg = live.filter((e) => e.organizer);
  const within = (events: UpcomingEvent[], days: number) => events.filter((e) => daysBetween(today, e.startDate) <= days).length;
  return {
    organizations: { next30: within(withOrg, 30), next60: within(withOrg, 60), next120: within(withOrg, 120) },
    recurringNext90: file.recurring.filter((s) => s.expectedEnd >= today && s.daysUntilExpected - elapsed <= 90).length,
    blockPartiesNext60: file.blockParties.items.filter(
      (b) => b.endDate >= today && daysBetween(today, b.startDate) <= 60,
    ).length,
    nextEvents: [...withOrg]
      .sort((a, b) => a.startDate.localeCompare(b.startDate) || a.id.localeCompare(b.id))
      .slice(0, TOP_ROWS),
  };
}

function summarizeNewBusiness(snap: Snapshot, names: Map<number, string>): ListSummary {
  const { model: m, spaces, spacesTotal } = snap.commercial.newBusiness;
  const recent = spaces.filter((s) => s.ageDays <= 30).length;
  return {
    stats: [
      { label: "Current spaces", value: count(spacesTotal), hint: "Build-out permits, last 180 days, no business license yet" },
      { label: "New in the last 30 days", value: count(recent), hint: `of the newest ${count(spaces.length)} on file` },
      { label: "Followed by a license", value: pct(m.rate, 0), hint: `within a year, ${m.lift.toFixed(1)}x comparable addresses` },
      { label: "Median days to the license", value: m.medianDays.toFixed(0), hint: `middle half ${m.daysP25.toFixed(0)}–${m.daysP75.toFixed(0)}` },
    ],
    rowsTitle: "Newest build-out permits with no license yet",
    rows: spaces.slice(0, TOP_ROWS).map((s) => ({
      id: s.id,
      title: s.address,
      subtitle: `${s.communityArea ? (names.get(s.communityArea) ?? "Chicago") : "Chicago"} · ${s.class}`,
      meta: `Permit ${dateLabel(s.permitDate)}`,
    })),
    listHref: "/commercial#new-business",
    listLabel: "All spaces and the CSV",
    note: `Build-out permits and business licenses through ${dateLabel(snap.meta.dataAsOf.permits)}.`,
  };
}

function summarizeRestaurantSpaces(snap: Snapshot, names: Map<number, string>): ListSummary {
  const closed = snap.leads.filter((l): l is ClosedRestaurantLead => l.kind === "closed_restaurant");
  const m = snap.models.closedRestaurant;
  return {
    stats: [
      { label: "Closed restaurant spaces", value: count(closed.length), hint: "Recorded closed in the last 180 days, no new food license yet" },
      { label: "Act now", value: count(closed.filter((l) => l.tier === "act_now").length), hint: `${count(closed.filter((l) => l.tier === "this_week").length)} more this week` },
      { label: "Build-out permits, no license", value: count(snap.commercial.newBusiness.spacesTotal), hint: "Spaces with a permit and no business license yet" },
      { label: "New food business in a year", value: pct(m.license.p365, 0), hint: `vs ${pct(m.license.baseline365, 0)} after ordinary inspections` },
    ],
    rowsTitle: "Newest closed restaurant spaces",
    rows: closed.slice(0, TOP_ROWS).map((l) => ({
      id: l.id,
      title: l.address,
      subtitle: `${l.communityArea ? (names.get(l.communityArea) ?? "Chicago") : "Chicago"} · ${l.restaurant.name ?? "Restaurant"}`,
      meta: `Closed ${dateLabel(l.signalDate)}`,
      href: `/leads/${encodeURIComponent(l.id)}`,
    })),
    listHref: "/commercial#closed-restaurants",
    listLabel: "All closed spaces",
    note: `Food inspections through ${dateLabel(snap.meta.dataAsOf.foodInspections)}.`,
  };
}

function summarizeOpenTrades(snap: Snapshot, names: Map<number, string>): ListSummary {
  const { model: m, recent, recentTotal } = snap.commercial.openTrades;
  const open = m.byTrade.filter((t) => !t.mostlyLockedIn);
  const labels = new Map(m.byTrade.map((t) => [t.trade, t.label]));
  return {
    stats: [
      { label: "$1M+ permits, last 365 days", value: count(recentTotal), hint: `about ${m.perWeek.toFixed(0)} a week across all address types` },
      { label: "Nothing followed yet", value: count(recent.filter((b) => b.appeared.length === 0).length), hint: `of the newest ${count(recent.length)} on file` },
      { label: "Trades still open", value: `${open.length} of ${m.byTrade.length}`, hint: open.map((t) => t.label).join(", ") },
      { label: "Follow-on within 540 days", value: pct(m.followOnRate, 0), hint: `median ${m.medianDays.toFixed(0)} days after the big permit` },
    ],
    rowsTitle: "Newest $1M+ permits",
    rows: recent.slice(0, TOP_ROWS).map((b) => ({
      id: b.id,
      title: b.address,
      subtitle: `${b.communityArea ? (names.get(b.communityArea) ?? "Chicago") : "Chicago"} · ${b.permitType}`,
      meta:
        b.appeared.length === 0
          ? `Permit ${dateLabel(b.permitDate)} · nothing followed yet`
          : `Permit ${dateLabel(b.permitDate)} · followed by ${b.appeared.map((t) => labels.get(t) ?? t).join(", ")}`,
    })),
    listHref: "/commercial#open-trades",
    listLabel: "All big permits",
    note: `Building permits through ${dateLabel(snap.meta.dataAsOf.permits)}.`,
  };
}

function summarizePest(file: PestFile | null): ListSummary {
  if (!file) {
    return { stats: [], rowsTitle: "Pest findings", rows: [], listHref: "/pilots/pest", listLabel: "Pest list", note: "The pest list has not been generated yet." };
  }
  const week = findingsFor(file, "week");
  const rows = (week.length > 0 ? week : findingsFor(file, "28d")).slice(0, TOP_ROWS);
  return {
    stats: [
      { label: "Fresh findings, latest week", value: count(file.counts.latestWeek), hint: "Inspections post with a delay" },
      { label: `Fresh findings, ${file.windows.backfillDays} days`, value: count(file.counts.last28Days) },
      { label: "With a phone or website", value: count(file.counts.withContact), hint: `of ${count(file.counts.last28Days)} in the ${file.windows.backfillDays} days` },
      { label: "Pest-control companies", value: count(file.counts.pestCompanies), hint: "To pitch, from public listings" },
    ],
    rowsTitle: week.length > 0 ? "Restaurants with a finding this week" : `Restaurants with a finding, last ${file.windows.backfillDays} days`,
    rows: rows.map((f) => ({
      id: String(f.inspectionId),
      title: f.restaurant,
      subtitle: `${f.address}${f.communityArea ? ` · ${f.communityArea.name}` : ""}`,
      meta: `${dateLabel(f.date)} · ${f.pestTerms.length > 0 ? f.pestTerms.join(", ") : "pests"}`,
    })),
    listHref: "/pilots/pest",
    listLabel: "Full pest list",
    note: `Inspection data through ${dateLabel(file.asOf)}.`,
  };
}

/** The dashboard summary for a commercial target. Events have their own (`summarizeEvents`). */
export function summarizeCommercial(target: TargetKey, snap: Snapshot, pest: PestFile | null): ListSummary | null {
  const names = new Map(snap.areas.map((a) => [a.id, a.name]));
  switch (target) {
    case "new_business":
      return summarizeNewBusiness(snap, names);
    case "restaurant_spaces":
      return summarizeRestaurantSpaces(snap, names);
    case "commercial_subs":
      return summarizeOpenTrades(snap, names);
    case "pest_control":
      return summarizePest(pest);
    default:
      return null;
  }
}
