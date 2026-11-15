import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader } from "@/components/bits";
import { LeadFilters, type FilterValues } from "@/components/lead-filters";
import { LeadList } from "@/components/lead-list";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { count } from "@/lib/format";
import {
  areaNames,
  expectedValue,
  getSnapshot,
  type Lead,
  leadsForWorkspace,
  TIER_ORDER,
  tradeProbability,
} from "@/lib/snapshot";
import { getStatuses, getWorkspace } from "@/lib/workspace";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Leads" };

const PAGE_SIZE = 25;

export default function LeadsPage({ searchParams }: PageProps<"/leads">) {
  return (
    <>
      <PageHeader
        title="Leads"
        description="Property owners ordered to make repairs, and investors who just bought. Ranked by priority and how often signals like these turned into permitted work."
      />
      <Suspense fallback={<LeadsSkeleton />}>
        <Leads searchParams={searchParams} />
      </Suspense>
    </>
  );
}

function param(v: string | string[] | undefined, fallback = "all"): string {
  return (Array.isArray(v) ? v[0] : v) || fallback;
}

async function Leads({ searchParams }: { searchParams: PageProps<"/leads">["searchParams"] }) {
  const sp = await searchParams;
  const [snap, ws, statuses] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses()]);
  const names = areaNames(snap);
  const values: FilterValues = {
    kind: param(sp.kind),
    tier: param(sp.tier),
    area: param(sp.area),
    status: param(sp.status),
    sort: param(sp.sort, "priority"),
    q: param(sp.q, ""),
  };
  const page = Math.max(1, Number(param(sp.page, "1")) || 1);

  const areaIds = ws.areas.length > 0 ? ws.areas : snap.areas.map((a) => a.id);
  const pool = leadsForWorkspace(snap, ws.trade, ws.areas);
  const q = values.q.toLowerCase();
  const filtered = pool.filter((l: Lead) => {
    if (values.kind !== "all" && l.kind !== values.kind) return false;
    if (values.tier !== "all" && l.tier !== values.tier) return false;
    if (values.area !== "all" && String(l.communityArea) !== values.area) return false;
    const st = statuses.get(l.id)?.status;
    if (values.status === "open" && st && st !== "new") return false;
    if (values.status !== "all" && values.status !== "open" && st !== values.status) return false;
    if (q) {
      const hay = [l.address, l.owner.name, l.kind === "investor_purchase" ? l.buyer.name : ""]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const ev = (l: Lead) => expectedValue(l, ws.trade, snap);
  const sorters: Record<string, (a: Lead, b: Lead) => number> = {
    priority: (a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier] || ev(b) - ev(a),
    value: (a, b) => ev(b) - ev(a),
    newest: (a, b) => b.signalDate.localeCompare(a.signalDate),
    probability: (a, b) => tradeProbability(b, ws.trade, snap) - tradeProbability(a, ws.trade, snap),
  };
  filtered.sort(sorters[values.sort] ?? sorters.priority);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const shown = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const pageHref = (n: number) => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(values)) if (v && v !== "all" && !(k === "sort" && v === "priority")) params.set(k, v);
    if (n > 1) params.set("page", String(n));
    return `/leads?${params.toString()}`;
  };

  return (
    <>
      <LeadFilters
        values={values}
        areas={areaIds.map((id) => ({ id, name: names.get(id) ?? `Area ${id}` })).sort((a, b) => a.name.localeCompare(b.name))}
      />
      <div className="mb-3 text-sm text-muted-foreground">
        {count(filtered.length)} leads · {snap.trades[ws.trade].label}
        {ws.areas.length > 0 ? ` · ${ws.areas.length} neighborhoods` : " · citywide"}
      </div>
      {shown.length === 0 ? (
        <EmptyState title="No leads match these filters">
          Try clearing filters, or widen your neighborhoods in <Link href="/settings" className="underline">Settings</Link>.
        </EmptyState>
      ) : (
        <LeadList leads={shown} snap={snap} trade={ws.trade} statuses={statuses} areaNames={names} />
      )}
      {pages > 1 && (
        <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pagination">
          <span className="text-muted-foreground">
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Link
              href={pageHref(page - 1)}
              aria-disabled={page <= 1}
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), page <= 1 && "pointer-events-none opacity-50")}
            >
              Previous
            </Link>
            <Link
              href={pageHref(page + 1)}
              aria-disabled={page >= pages}
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), page >= pages && "pointer-events-none opacity-50")}
            >
              Next
            </Link>
          </div>
        </nav>
      )}
    </>
  );
}

function LeadsSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-9 w-full" />
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="h-20 w-full" />
      ))}
    </div>
  );
}
