import { FileText } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, Trend } from "@/components/bits";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { count, dateLabel, money } from "@/lib/format";
import { getProspects, isBestFit, PROSPECT_TRADES, type Prospect, type ProspectTrade } from "@/lib/prospects";
import { areaNames, getSnapshot } from "@/lib/snapshot";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Prospects" };

const PAGE_SIZE = 50;

export default function ProspectsPage({ searchParams }: PageProps<"/prospects">) {
  return (
    <>
      <PageHeader
        title="Prospects"
        description="Our own sales list: Chicago contractors doing 3–60 permitted jobs a year, from public permit records. Open a teaser to see what Brickline would show them this week, plus a cold-email draft."
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Prospects searchParams={searchParams} />
      </Suspense>
    </>
  );
}

function first(v: string | string[] | undefined): string {
  return (Array.isArray(v) ? v[0] : v) ?? "";
}

function href(trade: string, best: boolean, page = 1): string {
  const params = new URLSearchParams();
  if (trade !== "all") params.set("trade", trade);
  if (best) params.set("fit", "best");
  if (page > 1) params.set("page", String(page));
  const qs = params.toString();
  return qs ? `/prospects?${qs}` : "/prospects";
}

async function Prospects({ searchParams }: { searchParams: PageProps<"/prospects">["searchParams"] }) {
  const sp = await searchParams;
  const tradeParam = first(sp.trade);
  const trade: ProspectTrade | "all" = PROSPECT_TRADES.includes(tradeParam as ProspectTrade)
    ? (tradeParam as ProspectTrade)
    : "all";
  const best = first(sp.fit) === "best";
  const [file, snap] = await Promise.all([getProspects(), getSnapshot()]);
  const names = areaNames(snap);

  const byTrade = new Map<string, number>();
  for (const p of file.prospects) byTrade.set(p.trade, (byTrade.get(p.trade) ?? 0) + 1);
  const rows = file.prospects.filter((p) => (trade === "all" || p.trade === trade) && (!best || isBestFit(p)));
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Number(first(sp.page)) || 1));
  const shown = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={href("all", best)} className={pill(trade === "all")}>
          All trades ({count(file.prospects.length)})
        </Link>
        {PROSPECT_TRADES.map((t) => (
          <Link key={t} href={href(t, best)} className={pill(trade === t)}>
            {snap.trades[t].label} ({count(byTrade.get(t) ?? 0)})
          </Link>
        ))}
        <span className="mx-1 hidden h-5 w-px bg-border sm:block" />
        <Link href={href(trade, !best)} className={pill(best)} title="Already win violation jobs, 5–40 jobs a year">
          Best fit only
        </Link>
      </div>
      <p className="text-xs text-muted-foreground">
        {count(rows.length)} contractors · permits through {dateLabel(file.generatedFor)}. Violation-driven jobs are
        permits pulled at an address that had a violation in the same trade in the year before.
      </p>

      {rows.length === 0 ? (
        <EmptyState title="No prospects match">Try another trade or turn off &ldquo;Best fit only&rdquo;.</EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[56rem] text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Company</th>
                <th className="px-4 py-2 font-medium">Trade</th>
                <th className="px-4 py-2 font-medium">Jobs, 12 mo</th>
                <th className="px-4 py-2 font-medium">Typical job</th>
                <th className="px-4 py-2 font-medium">Last job</th>
                <th className="px-4 py-2 font-medium">Violation-driven</th>
                <th className="px-4 py-2 font-medium">Neighborhoods</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {shown.map((p) => (
                <ProspectRow key={p.id} p={p} label={snap.trades[p.trade].label} names={names} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            {page > 1 && (
              <Link href={href(trade, best, page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
                Previous
              </Link>
            )}
            {page < pages && (
              <Link href={href(trade, best, page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
                Next
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ProspectRow({ p, label, names }: { p: Prospect; label: string; names: Map<number, string> }) {
  return (
    <tr>
      <td className="px-4 py-2.5 font-medium">{p.company}</td>
      <td className="px-4 py-2.5 text-muted-foreground">{label}</td>
      <td className="px-4 py-2.5 tabular-nums">
        {count(p.jobs12m)} <Trend now={p.jobs12m} before={p.jobsPrev12m} />
      </td>
      <td className="px-4 py-2.5 tabular-nums">{money(p.medianJob)}</td>
      <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">{dateLabel(p.lastJob)}</td>
      <td className="px-4 py-2.5 tabular-nums">{count(p.violationDrivenJobs)}</td>
      <td className="px-4 py-2.5 text-muted-foreground">
        {p.areaIds.map((a) => names.get(a)).filter(Boolean).join(", ")}
      </td>
      <td className="px-4 py-2.5 text-right">
        <Link href={`/prospects/${p.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
          <FileText /> Teaser
        </Link>
      </td>
    </tr>
  );
}
