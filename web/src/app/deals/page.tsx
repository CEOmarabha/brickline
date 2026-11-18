import { Check, Download, Users } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { DealQuickAdd } from "@/components/deal-quick-add";
import { DealStatusBadge, DoNotContactBadge } from "@/components/deal-bits";
import { EmptyState, PageHeader, Pagination, StatCard } from "@/components/bits";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { computeDealMetrics, type DealMetrics } from "@/lib/deal-metrics";
import { getDealEventTimes, getDeals, getPartners } from "@/lib/deal-store";
import {
  BUYER_TYPE_LABEL,
  BUYER_TYPES,
  type BuyerType,
  DEAL_SOURCE_LABEL,
  DEAL_SOURCES,
  DEAL_STATUS_LABEL,
  DEAL_STATUS_VALUES,
  type DealRow,
  type DealSource,
  type DealStatus,
  daysBetween,
  daysUntilLabel,
  isDealDue,
  isDealStatus,
  isOpenDeal,
} from "@/lib/deals";
import { count, dateLabel, exactMoney, pct } from "@/lib/format";
import { todayChicago } from "@/lib/pipeline";
import { firstParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";
import { viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Deals" };

const PAGE_SIZE = 50;

export default function DealsPage({ searchParams }: PageProps<"/deals">) {
  return (
    <>
      <PageHeader
        title="Deals"
        description="Your private pipeline for jobs you broker yourself: find a buyer, contact them personally, hand the job to a partner, and track the fee. Only you see this."
        actions={
          <>
            <Link href="/deals/partners" className={buttonVariants({ variant: "outline", size: "sm" })}>
              <Users /> Partners
            </Link>
            <a href="/export/deals" className={buttonVariants({ variant: "outline", size: "sm" })}>
              <Download /> Export deals
            </a>
          </>
        }
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Deals searchParams={searchParams} />
      </Suspense>
    </>
  );
}

type StatusFilter = DealStatus | "due" | "all";

function href(status: StatusFilter, source: DealSource | "all", type: BuyerType | "all", page = 1): string {
  const params = new URLSearchParams();
  if (status !== "all") params.set("status", status);
  if (source !== "all") params.set("source", source);
  if (type !== "all") params.set("type", type);
  if (page > 1) params.set("page", String(page));
  const qs = params.toString();
  return qs ? `/deals?${qs}` : "/deals";
}

/** Open deals first, then the finished ones; inside each group the soonest follow-up, then the newest. */
function compareDeals(a: DealRow, b: DealRow): number {
  const open = Number(isOpenDeal(b.status)) - Number(isOpenDeal(a.status));
  if (open !== 0) return open;
  const fa = a.nextFollowUp ?? "9999-99-99";
  const fb = b.nextFollowUp ?? "9999-99-99";
  return fa.localeCompare(fb) || b.createdAt.getTime() - a.createdAt.getTime() || a.id.localeCompare(b.id);
}

async function Deals({ searchParams }: { searchParams: PageProps<"/deals">["searchParams"] }) {
  const sp = await searchParams;
  const statusParam = firstParam(sp.status);
  const status: StatusFilter = statusParam === "due" || isDealStatus(statusParam) ? statusParam : "all";
  const sourceParam = firstParam(sp.source);
  const source: DealSource | "all" = (DEAL_SOURCES as readonly string[]).includes(sourceParam) ? (sourceParam as DealSource) : "all";
  const typeParam = firstParam(sp.type);
  const type: BuyerType | "all" = (BUYER_TYPES as readonly string[]).includes(typeParam) ? (typeParam as BuyerType) : "all";

  const owner = await viewerId();
  if (!owner) {
    return (
      <div className="space-y-4">
        <DealQuickAdd disabled />
        <EmptyState title="Sign in to use deals">Your deals are private to your account.</EmptyState>
      </div>
    );
  }

  const [deals, partners, events] = await Promise.all([getDeals(owner), getPartners(owner), getDealEventTimes(owner)]);
  const today = todayChicago();
  const partnerName = new Map(partners.map((p) => [p.id, p.name]));
  const metrics = computeDealMetrics(deals, events);
  const dueCount = deals.filter((d) => isDealDue(d, today)).length;

  const rows = deals
    .filter(
      (d) =>
        (status === "all" || (status === "due" ? isDealDue(d, today) : d.status === status)) &&
        (source === "all" || d.source === source) &&
        (type === "all" || d.buyerType === type),
    )
    .sort(compareDeals);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Math.floor(Number(firstParam(sp.page))) || 1));
  const shown = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");
  const filtered = status !== "all" || source !== "all" || type !== "all";

  return (
    <div className="space-y-4">
      <DealQuickAdd disabled={false} />

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5 lg:grid-cols-10">
        <Link
          href={href(status === "due" ? "all" : "due", source, type)}
          className={cn("rounded-lg border p-3 hover:bg-muted", status === "due" && "border-primary bg-primary/5")}
        >
          <div className="text-xs text-muted-foreground">Due today / overdue</div>
          <div className={cn("text-xl font-semibold tabular-nums", dueCount > 0 && "text-amber-700")}>{count(dueCount)}</div>
        </Link>
        {DEAL_STATUS_VALUES.map((s) => (
          <Link
            key={s}
            href={href(status === s ? "all" : s, source, type)}
            className={cn("rounded-lg border p-3 hover:bg-muted", status === s && "border-primary bg-primary/5")}
          >
            <div className="text-xs text-muted-foreground">{DEAL_STATUS_LABEL[s]}</div>
            <div className="text-xl font-semibold tabular-nums">{count(metrics.total.byStatus[s])}</div>
          </Link>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Link href={href(status, "all", type)} className={pill(source === "all")}>
          All sources
        </Link>
        {DEAL_SOURCES.map((s) => (
          <Link key={s} href={href(status, s, type)} className={pill(source === s)}>
            {DEAL_SOURCE_LABEL[s]}
          </Link>
        ))}
        <span className="mx-1 hidden h-5 w-px bg-border sm:block" />
        <Link href={href(status, source, "all")} className={pill(type === "all")}>
          Any type
        </Link>
        {BUYER_TYPES.map((t) => (
          <Link key={t} href={href(status, source, t)} className={pill(type === t)}>
            {BUYER_TYPE_LABEL[t]}
          </Link>
        ))}
        {filtered && (
          <Link href="/deals" className={pill(true)}>
            Clear filters ×
          </Link>
        )}
      </div>

      {deals.length === 0 ? (
        <EmptyState title="No deals yet">
          Paste a public link above to add the first one. Contact buyers one by one, yourself; this page tracks where each
          deal stands.
        </EmptyState>
      ) : rows.length === 0 ? (
        <EmptyState title="No deals match">Try another status, source or type.</EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[56rem] text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Deal</th>
                <th className="px-4 py-2 font-medium">Buyer</th>
                <th className="px-4 py-2 font-medium">Event or job date</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Follow-up</th>
                <th className="px-4 py-2 font-medium">Partner(s)</th>
                <th className="px-4 py-2 font-medium">Your fee</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {shown.map((d) => (
                <DealTableRow key={d.id} d={d} today={today} partnerName={partnerName} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pages={pages} href={(n) => href(status, source, type, n)} />

      {deals.length > 0 && <Results metrics={metrics} />}
    </div>
  );
}

function DealTableRow({ d, today, partnerName }: { d: DealRow; today: string; partnerName: Map<string, string> }) {
  const due = isDealDue(d, today);
  const partners = d.partnerIds.map((id) => partnerName.get(id)).filter(Boolean);
  const eventPast = d.eventDate !== null && daysBetween(today, d.eventDate) < 0;
  return (
    <tr>
      <td className="px-4 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/deals/${encodeURIComponent(d.id)}`} className="font-medium underline-offset-4 hover:underline">
            {d.title}
          </Link>
          {d.status === "opted_out" && <DoNotContactBadge />}
        </div>
        <div className="text-xs text-muted-foreground">{DEAL_SOURCE_LABEL[d.source]}</div>
      </td>
      <td className="px-4 py-2.5">
        <div>{d.buyerName || <span className="text-muted-foreground">—</span>}</div>
        <div className="text-xs text-muted-foreground">{BUYER_TYPE_LABEL[d.buyerType]}</div>
      </td>
      <td className="px-4 py-2.5 whitespace-nowrap">
        {d.eventDate ? (
          <>
            <div>{dateLabel(d.eventDate)}</div>
            <div className={cn("text-xs", eventPast && isOpenDeal(d.status) ? "text-amber-700" : "text-muted-foreground")}>
              {daysUntilLabel(d.eventDate, today)}
            </div>
          </>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="px-4 py-2.5">
        <DealStatusBadge status={d.status} />
      </td>
      <td className={cn("px-4 py-2.5 whitespace-nowrap", due ? "font-medium text-amber-700" : "text-muted-foreground")}>
        {d.nextFollowUp ? dateLabel(d.nextFollowUp) : "—"}
        {due && d.nextFollowUp && d.nextFollowUp < today ? " (overdue)" : ""}
        {due && d.nextFollowUp === today ? " (today)" : ""}
      </td>
      <td className="px-4 py-2.5 text-muted-foreground">{partners.length > 0 ? partners.join(", ") : "—"}</td>
      <td className="px-4 py-2.5 whitespace-nowrap tabular-nums">
        {d.feeUsd !== null && d.feeUsd > 0 ? (
          <>
            <div>{exactMoney(d.feeUsd)}</div>
            {d.feeCollected && (
              <div className="inline-flex items-center gap-0.5 text-xs text-emerald-700">
                <Check className="size-3" aria-hidden /> collected
              </div>
            )}
          </>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
    </tr>
  );
}

const rateText = (rate: number | null, n: number, of: number) => (rate === null ? "—" : `${pct(rate, 0)} (${n} of ${of})`);

function Results({ metrics }: { metrics: DealMetrics }) {
  const { total } = metrics;
  return (
    <section className="space-y-3 pt-4" aria-labelledby="deal-results">
      <div>
        <h2 id="deal-results" className="text-lg font-semibold tracking-tight">
          Results <span className="text-sm font-normal text-muted-foreground">from your records</span>
        </h2>
        <p className="text-xs text-muted-foreground">
          Counted from the deals and history you entered; nothing is estimated. A deal counts as contacted, replied or
          booked once it has reached that stage, even if it was lost or opted out later. With fewer than 10 contacted per
          source, read the counts, not the percentages.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          label="Total quoted"
          value={metrics.quoted.count > 0 ? exactMoney(metrics.quoted.totalUsd) : "—"}
          hint={`${count(metrics.quoted.count)} ${metrics.quoted.count === 1 ? "deal" : "deals"} with a quote`}
        />
        <StatCard
          label="Your fees, booked or completed"
          value={metrics.fees.count > 0 ? exactMoney(metrics.fees.totalUsd) : "—"}
          hint={`${count(metrics.fees.count)} ${metrics.fees.count === 1 ? "deal" : "deals"} with a fee`}
        />
        <StatCard
          label="Fees collected"
          value={metrics.collected.count > 0 ? exactMoney(metrics.collected.totalUsd) : "—"}
          hint={`${count(metrics.collected.count)} ${metrics.collected.count === 1 ? "deal" : "deals"}`}
        />
        <StatCard
          label="Average fee"
          value={metrics.fees.averageUsd === null ? "—" : exactMoney(metrics.fees.averageUsd)}
          hint="Booked or completed deals with a fee"
        />
        <StatCard
          label="Median days, found to booked"
          value={metrics.daysToBooked.median === null ? "—" : String(metrics.daysToBooked.median)}
          hint={`${count(metrics.daysToBooked.count)} booked ${metrics.daysToBooked.count === 1 ? "deal" : "deals"}`}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[44rem] text-sm">
          <caption className="sr-only">Contact, reply and booking rates by source</caption>
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2 font-medium">Source</th>
              <th className="px-4 py-2 font-medium">Deals</th>
              <th className="px-4 py-2 font-medium">Contacted</th>
              <th className="px-4 py-2 font-medium">Replied</th>
              <th className="px-4 py-2 font-medium">Booked</th>
              <th className="px-4 py-2 font-medium">Reply rate</th>
              <th className="px-4 py-2 font-medium">Booked of contacted</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {[...metrics.bySource.map((s) => ({ key: s.source, label: DEAL_SOURCE_LABEL[s.source], f: s })), { key: "all", label: "All sources", f: total }].map(
              ({ key, label, f }) => (
                <tr key={key} className={key === "all" ? "font-medium" : undefined}>
                  <td className="px-4 py-2">{label}</td>
                  <td className="px-4 py-2 tabular-nums">{count(f.deals)}</td>
                  <td className="px-4 py-2 tabular-nums">{count(f.contacted)}</td>
                  <td className="px-4 py-2 tabular-nums">{count(f.replied)}</td>
                  <td className="px-4 py-2 tabular-nums">{count(f.booked)}</td>
                  <td className="px-4 py-2 tabular-nums">{rateText(f.replyRate, f.replied, f.contacted)}</td>
                  <td className="px-4 py-2 tabular-nums">{rateText(f.bookedOfContacted, f.booked, f.contacted)}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[44rem] text-sm">
          <caption className="sr-only">Deals by source and current status</caption>
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2 font-medium">Current status</th>
              {DEAL_STATUS_VALUES.map((s) => (
                <th key={s} className="px-2 py-2 font-medium">
                  {DEAL_STATUS_LABEL[s]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {metrics.bySource.map((s) => (
              <tr key={s.source}>
                <td className="px-4 py-2">{DEAL_SOURCE_LABEL[s.source]}</td>
                {DEAL_STATUS_VALUES.map((st) => (
                  <td key={st} className="px-2 py-2 tabular-nums">
                    {count(s.byStatus[st])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
