import "server-only";

import {
  type CloseRates,
  expectedValue,
  type Lead,
  leadsForWorkspace,
  type Snapshot,
  TIER_ORDER,
  tradeProbability,
} from "@/lib/snapshot";
import { firstParam } from "@/lib/search-params";
import { isOpenLead, type LeadStatusRow, type Workspace } from "@/lib/workspace";

export interface LeadFiltersInput {
  kind: string;
  tier: string;
  area: string;
  status: string;
  sort: string;
  q: string;
}

export const DEFAULT_FILTERS: LeadFiltersInput = {
  kind: "all",
  tier: "all",
  area: "all",
  status: "all",
  sort: "priority",
  q: "",
};

type Params = Record<string, string | string[] | undefined>;

export function parseFilters(sp: Params | URLSearchParams): LeadFiltersInput {
  const get = (k: keyof LeadFiltersInput) =>
    (sp instanceof URLSearchParams ? sp.get(k) : firstParam(sp[k])) || DEFAULT_FILTERS[k];
  return {
    kind: get("kind"),
    tier: get("tier"),
    area: get("area"),
    status: get("status"),
    sort: get("sort"),
    q: get("q").slice(0, 100),
  };
}

export function filtersToSearch(values: LeadFiltersInput, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(values)) {
    if (v && v !== "all" && !(k === "sort" && v === "priority")) params.set(k, v);
  }
  for (const [k, v] of Object.entries(extra)) params.set(k, v);
  return params.toString();
}

/** Filtered, sorted leads for a workspace. One implementation for the list, exports and reports. */
export function queryLeads(
  snap: Snapshot,
  ws: Workspace,
  statuses: Map<string, LeadStatusRow>,
  f: LeadFiltersInput,
  rates?: CloseRates,
): Lead[] {
  const q = f.q.toLowerCase();
  const out = leadsForWorkspace(snap, ws.trade, ws.areas).filter((l) => {
    if (f.kind !== "all" && l.kind !== f.kind) return false;
    if (f.tier !== "all" && l.tier !== f.tier) return false;
    if (f.area !== "all" && String(l.communityArea) !== f.area) return false;
    if (f.status === "open") {
      if (!isOpenLead(statuses, l.id)) return false;
    } else if (f.status !== "all" && statuses.get(l.id)?.status !== f.status) return false;
    if (q) {
      const hay = [
        l.address,
        l.owner.name,
        l.kind === "investor_purchase" ? l.buyer.name : "",
        l.kind === "closed_restaurant" ? l.restaurant.name : "",
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const ev = (l: Lead) => expectedValue(l, ws.trade, snap, rates);
  const sorters: Record<string, (a: Lead, b: Lead) => number> = {
    priority: (a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier] || ev(b) - ev(a),
    value: (a, b) => ev(b) - ev(a),
    newest: (a, b) => b.signalDate.localeCompare(a.signalDate),
    probability: (a, b) => tradeProbability(b, ws.trade, snap) - tradeProbability(a, ws.trade, snap),
  };
  return out.sort(sorters[f.sort] ?? sorters.priority);
}
