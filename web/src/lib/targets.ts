/*
 * What a workspace is looking for. Shared by server code and client components (labels, grouping), so it imports
 * nothing server-only. A trade target uses the trade lead flow (violations, 311 reports, investor purchases scored for
 * that trade); every other target points at one of the pilot lists.
 */
import type { TradeKey } from "@/lib/snapshot";

export type TradeTargetKey = TradeKey;
export type ListTargetKey = "events" | "new_business" | "restaurant_spaces" | "commercial_subs" | "pest_control";
export type TargetKey = TradeTargetKey | ListTargetKey;

export type TargetGroupKey = "trades" | "events" | "commercial";

export interface TargetGroup {
  key: TargetGroupKey;
  label: string;
  description: string;
}

export const TARGET_GROUPS: readonly TargetGroup[] = [
  { key: "trades", label: "Trades", description: "Homeowner and property leads for a trade" },
  { key: "events", label: "Events", description: "Organizations running events in Chicago" },
  { key: "commercial", label: "Commercial services", description: "Businesses and buildings that need a service" },
];

export interface TargetDef {
  key: TargetKey;
  /** Trade labels mirror `snap.trades`; callers with the snapshot pass it to `targetOptions` so the data wins. */
  label: string;
  group: TargetGroupKey;
  description: string;
  /** Heading of /leads while this is the target. */
  leadsTitle: string;
  /** Where the full list lives. `/leads` shows the same list for the current target. */
  route: string;
  /** Anchor of this target's buyers and pitch card on /pilots, when it has one. */
  pilotAnchor: string | null;
  usesTradeLeadFlow: boolean;
}

const trade = (key: TradeTargetKey, label: string, description: string): TargetDef => ({
  key,
  label,
  group: "trades",
  description,
  leadsTitle: "Leads",
  route: "/leads",
  pilotAnchor: null,
  usesTradeLeadFlow: true,
});

export const TARGETS: readonly TargetDef[] = [
  trade("porch", "Porches & decks", "Owners cited for porch, deck and stair violations, porch inspection requests, investor purchases"),
  trade("masonry", "Masonry & tuckpointing", "Owners cited for exterior wall, masonry and chimney violations, older buildings, investor purchases"),
  trade("roofing", "Roofing", "Owners cited for roof and gutter violations, 311 complaints, reroof blocks, investor purchases"),
  trade("plumbing", "Plumbing", "Owners cited for plumbing and drain violations, investor purchases"),
  trade("electrical", "Electrical", "Owners cited for electrical violations, investor purchases"),
  trade("general", "General contracting & rehab", "Major projects, vacant buildings, closed restaurant spaces, investor purchases"),
  {
    key: "events",
    label: "Event planning & rentals",
    group: "events",
    description: "Organizations with events in the next 120 days, recurring events, block parties, and your deals",
    leadsTitle: "Event leads",
    route: "/events",
    pilotAnchor: "events",
    usesTradeLeadFlow: false,
  },
  {
    key: "new_business",
    label: "Commercial cleaning & new openings",
    group: "commercial",
    description: "Build-out permits at addresses with no business license yet: tenants about to open",
    leadsTitle: "New-business leads",
    route: "/commercial#new-business",
    pilotAnchor: "new-business",
    usesTradeLeadFlow: false,
  },
  {
    key: "restaurant_spaces",
    label: "Restaurant build-outs & space turnover",
    group: "commercial",
    description: "Restaurants recorded closed, plus build-out permits: spaces about to change hands",
    leadsTitle: "Restaurant-space leads",
    route: "/commercial#closed-restaurants",
    pilotAnchor: "closed-restaurants",
    usesTradeLeadFlow: false,
  },
  {
    key: "commercial_subs",
    label: "Elevator, fire-alarm, electrical & sign subcontractors",
    group: "commercial",
    description: "$1M+ permits and which trades are still open at each building",
    leadsTitle: "Open-trade leads",
    route: "/commercial#open-trades",
    pilotAnchor: "open-trades",
    usesTradeLeadFlow: false,
  },
  {
    key: "pest_control",
    label: "Pest control",
    group: "commercial",
    description: "Restaurants with a fresh pest finding in inspection records, and pest-control companies to pitch",
    leadsTitle: "Pest-control leads",
    route: "/pilots/pest",
    pilotAnchor: "pest",
    usesTradeLeadFlow: false,
  },
];

export const TARGET_KEYS: readonly TargetKey[] = TARGETS.map((t) => t.key);

export const DEFAULT_TARGET: TargetKey = "porch";

export function isTargetKey(value: unknown): value is TargetKey {
  return typeof value === "string" && TARGET_KEYS.includes(value as TargetKey);
}

export function isTradeTarget(key: TargetKey): key is TradeTargetKey {
  return getTarget(key).usesTradeLeadFlow;
}

export function getTarget(key: TargetKey): TargetDef {
  return TARGETS.find((t) => t.key === key) ?? TARGETS[0];
}

/**
 * The target a stored row stands for. An empty or unknown value means "use the trade". A trade target always follows
 * the `trade` column, so the two can never disagree about which trade a workspace works in.
 */
export function resolveTarget(stored: string | null | undefined, trade: TradeKey): TargetKey {
  return isTargetKey(stored) && !isTradeTarget(stored) ? stored : trade;
}

/** A target as a client component needs it: serializable, with the label to show. */
export interface TargetOption {
  key: TargetKey;
  label: string;
  group: TargetGroupKey;
  description: string;
}

type TradeLabels = Partial<Record<TradeKey, { label: string }>>;

export function targetOptions(tradeLabels?: TradeLabels): TargetOption[] {
  return TARGETS.map((t) => ({
    key: t.key,
    label: (isTradeTarget(t.key) ? tradeLabels?.[t.key]?.label : undefined) ?? t.label,
    group: t.group,
    description: t.description,
  }));
}

export function targetLabel(key: TargetKey, tradeLabels?: TradeLabels): string {
  return targetOptions(tradeLabels).find((o) => o.key === key)?.label ?? key;
}

export function groupedOptions(options: TargetOption[]): { group: TargetGroup; options: TargetOption[] }[] {
  return TARGET_GROUPS.map((group) => ({ group, options: options.filter((o) => o.group === group.key) })).filter(
    (g) => g.options.length > 0,
  );
}
