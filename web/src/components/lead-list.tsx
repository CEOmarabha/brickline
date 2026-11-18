import { Building, DoorClosed, Hammer, House, MessageSquareWarning, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { ProbabilityBar, StatusBadge, TierBadge } from "@/components/bits";
import { ago, money, pct } from "@/lib/format";
import { type CloseRates, expectedValue, type Lead, type Snapshot, type TradeKey, tradeProbability } from "@/lib/snapshot";
import type { Way } from "@/lib/reach";
import { type LeadStatusRow, STATUS_LABEL } from "@/lib/workspace";

const WAY_TEXT: Record<Way, string> = { mail: "mail", email: "email", phone: "phone" };

function reachText(ways: Way[]): string {
  return ways.length ? `Reach by ${ways.map((w) => WAY_TEXT[w]).join(", ")}` : "No mailing address or contact yet";
}

const KIND_ICON = {
  violation: Hammer,
  complaint: MessageSquareWarning,
  porch_request: House,
  vacant: DoorClosed,
  closed_restaurant: UtensilsCrossed,
  investor_purchase: Building,
};

function subtitle(lead: Lead): string {
  const owner = lead.owner.name ?? "Owner of record";
  switch (lead.kind) {
    case "violation":
      return `${lead.title} · ${lead.evidence.find((e) => e.label === "Violation")?.value ?? ""}`;
    case "complaint":
      return `${lead.title} · ${owner} · ${pct(lead.probability, 0)} chance of a citation`;
    case "porch_request":
      return `${lead.title} · ${owner}`;
    case "vacant":
      return `${lead.title} · ${owner} · ${pct(lead.probability, 0)} chance it sells`;
    case "closed_restaurant":
      return `${lead.title} · ${lead.restaurant.name ?? "Restaurant"} · ${pct(lead.probability, 0)} chance of a new food business`;
    case "investor_purchase":
      return `${lead.title} · ${lead.buyer.name}${lead.buyer.purchases24m >= 3 ? ` · ${lead.buyer.purchases24m} buys in 2 yrs` : ""}`;
  }
}

export function LeadList({
  leads,
  snap,
  trade,
  statuses,
  areaNames,
  rates,
  ways,
}: {
  rates?: CloseRates;
  ways?: Map<string, Way[]>;
  leads: Lead[];
  snap: Snapshot;
  trade: TradeKey;
  statuses: Map<string, LeadStatusRow>;
  areaNames: Map<number, string>;
}) {
  return (
    <ul className="divide-y rounded-lg border bg-card">
      {leads.map((lead) => {
        const status = statuses.get(lead.id);
        const p = tradeProbability(lead, trade, snap);
        const Icon = KIND_ICON[lead.kind];
        return (
          <li key={lead.id}>
            <Link
              href={`/leads/${encodeURIComponent(lead.id)}`}
              className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 p-4 transition-colors hover:bg-muted/50 sm:grid-cols-[auto_1fr_10rem_7rem]"
            >
              <span className="mt-0.5 grid size-8 place-items-center rounded-md bg-muted text-muted-foreground">
                <Icon className="size-4" />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate font-medium">{lead.address}</span>
                  <TierBadge tier={lead.tier} />
                  {status && <StatusBadge status={status.status} label={STATUS_LABEL[status.status]} />}
                </div>
                <div className="mt-0.5 truncate text-sm text-muted-foreground">
                  {subtitle(lead)}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {lead.communityArea ? areaNames.get(lead.communityArea) : "Area unknown"} · {ago(lead.ageDays)}
                  {ways && ` · ${reachText(ways.get(lead.id) ?? [])}`}
                </div>
              </div>
              <div className="col-start-2 sm:col-start-auto">
                <div className="flex items-baseline justify-between text-xs text-muted-foreground">
                  <span>Chance of work</span>
                  <span className="font-medium text-foreground tabular-nums">{pct(p)}</span>
                </div>
                <div className="mt-1.5">
                  <ProbabilityBar value={p} />
                </div>
              </div>
              <div className="col-start-2 text-left sm:col-start-auto sm:text-right">
                <div className="text-xs text-muted-foreground">Expected value</div>
                <div className="font-medium tabular-nums">{money(expectedValue(lead, trade, snap, rates))}</div>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
