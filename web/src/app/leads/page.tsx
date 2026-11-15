import { Download } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader } from "@/components/bits";
import { LeadFilters } from "@/components/lead-filters";
import { LeadList } from "@/components/lead-list";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { count } from "@/lib/format";
import { filtersToSearch, parseFilters, queryLeads } from "@/lib/lead-query";
import { getCloseRates } from "@/lib/outcomes";
import { areaNames, getSnapshot } from "@/lib/snapshot";
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

async function Leads({ searchParams }: { searchParams: PageProps<"/leads">["searchParams"] }) {
  const sp = await searchParams;
  const [snap, ws, statuses, rates] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses(), getCloseRates()]);
  const names = areaNames(snap);
  const values = parseFilters(sp);
  const page = Math.max(1, Number(Array.isArray(sp.page) ? sp.page[0] : sp.page) || 1);
  const areaIds = ws.areas.length > 0 ? ws.areas : snap.areas.map((a) => a.id);
  const filtered = queryLeads(snap, ws, statuses, values, rates);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const shown = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const pageHref = (n: number) => `/leads?${filtersToSearch(values, n > 1 ? { page: String(n) } : {})}`;
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
