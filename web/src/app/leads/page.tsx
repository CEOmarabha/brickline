import { Download } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, Pagination } from "@/components/bits";
import { LeadFilters } from "@/components/lead-filters";
import { LeadList } from "@/components/lead-list";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { count } from "@/lib/format";
import { filtersToSearch, parseFilters, queryLeads } from "@/lib/lead-query";
import { getCloseRates } from "@/lib/outcomes";
import { firstParam } from "@/lib/search-params";
import { areaNames, getSnapshot } from "@/lib/snapshot";
import { getStatuses, getWorkspace } from "@/lib/workspace";

export const metadata: Metadata = { title: "Leads" };

const PAGE_SIZE = 25;

export default function LeadsPage({ searchParams }: PageProps<"/leads">) {
  return (
    <>
      <PageHeader
        title="Leads"
        description="Owners ordered to make repairs or reported to 311 (building complaints, porch inspections, vacant buildings), and investors who just bought. Ranked by priority and how often signals like these turned into permitted work."
      />
      <Suspense fallback={<LeadsSkeleton />}>
        <Leads searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Leads({ searchParams }: { searchParams: PageProps<"/leads">["searchParams"] }) {
  const sp = await searchParams;
  const [snap, ws, statuses, rates] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses(), getCloseRates()]);
  const names = areaNames(snap);
  const values = parseFilters(sp);
  const areaIds = ws.areas.length > 0 ? ws.areas : snap.areas.map((a) => a.id);
  const filtered = queryLeads(snap, ws, statuses, values, rates);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Math.floor(Number(firstParam(sp.page))) || 1));
  const shown = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const pageHref = (n: number) => {
    const search = filtersToSearch(values, n > 1 ? { page: String(n) } : {});
    return search ? `/leads?${search}` : "/leads";
  };
  const exportHref = (format: string) => `/export/leads?${filtersToSearch(values, { format })}`;

  return (
    <>
      <LeadFilters
        values={values}
        areas={areaIds.map((id) => ({ id, name: names.get(id) ?? `Area ${id}` })).sort((a, b) => a.name.localeCompare(b.name))}
      />
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
        <span>
          {count(filtered.length)} leads · {snap.trades[ws.trade].label}
          {ws.areas.length > 0 ? ` · ${ws.areas.length} neighborhoods` : " · citywide"}
        </span>
        {filtered.length > 0 && (
          <span className="flex gap-2">
            <a href={exportHref("mail")} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <Download /> Mail-merge CSV
            </a>
            <a href={exportHref("all")} className={buttonVariants({ variant: "ghost", size: "sm" })}>
              Export all columns
            </a>
          </span>
        )}
      </div>
      {shown.length === 0 ? (
        <EmptyState title="No leads match these filters">
          Try clearing filters, or widen your neighborhoods in <Link href="/settings" className="underline">Settings</Link>.
        </EmptyState>
      ) : (
        <LeadList leads={shown} snap={snap} trade={ws.trade} statuses={statuses} areaNames={names} rates={rates} />
      )}
      <Pagination page={page} pages={pages} href={pageHref} className="mt-4" />
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
