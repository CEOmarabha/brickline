import { Building, Hammer } from "lucide-react";
import Link from "next/link";
import { ProbabilityBar, StatusBadge, TierBadge } from "@/components/bits";
import { ago, money, pct } from "@/lib/format";
import { type CloseRates, expectedValue, type Lead, type Snapshot, type TradeKey, tradeProbability } from "@/lib/snapshot";
import { type LeadStatusRow, STATUS_LABEL } from "@/lib/workspace";

export function LeadList({
  leads,
  snap,
  trade,
  statuses,
  areaNames,
  rates,
}: {
  rates?: CloseRates;
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
        const Icon = lead.kind === "violation" ? Hammer : Building;
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
                  {lead.kind === "violation"
                    ? `${lead.title} · ${lead.evidence.find((e) => e.label === "Violation")?.value ?? ""}`
                    : `${lead.title} · ${lead.buyer.name}${lead.buyer.purchases24m >= 3 ? ` · ${lead.buyer.purchases24m} buys in 2 yrs` : ""}`}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {lead.communityArea ? areaNames.get(lead.communityArea) : "Area unknown"} · {ago(lead.ageDays)}
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
