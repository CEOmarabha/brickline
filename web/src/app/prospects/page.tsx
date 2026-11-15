import { Download, FileText, Globe, Mail, Phone, UserRound } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, ProspectStatusBadge, Trend } from "@/components/bits";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type ContactSuggestions, getContacts, hasAnyContact } from "@/lib/contacts";
import { count, dateLabel, money } from "@/lib/format";
import {
  isDue,
  PROSPECT_STATUS_LABEL,
  PROSPECT_STATUSES,
  todayChicago,
  type ProspectStatus,
} from "@/lib/pipeline";
import { getPipeline, type PipelineRow } from "@/lib/prospect-pipeline";
import { getProspects, isBestFit, PROSPECT_TRADES, type Prospect, type ProspectTrade } from "@/lib/prospects";
import { areaNames, getSnapshot } from "@/lib/snapshot";
import { cn } from "@/lib/utils";
import { viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Prospects" };

const PAGE_SIZE = 50;

export default function ProspectsPage({ searchParams }: PageProps<"/prospects">) {
  return (
    <>
      <PageHeader
        title="Prospects"
        description="Our own sales list: Chicago contractors doing 3–60 permitted jobs a year, from public permit records. Open a teaser to see what Brickline would show them this week, plus a cold-email draft and your pipeline notes."
        actions={
          <a href="/export/prospects" className={buttonVariants({ variant: "outline", size: "sm" })}>
            <Download /> Export pipeline
          </a>
        }
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

type StatusFilter = ProspectStatus | "due" | "all";

function href(trade: string, best: boolean, status: StatusFilter = "all", page = 1, withContact = false): string {
  const params = new URLSearchParams();
  if (trade !== "all") params.set("trade", trade);
  if (best) params.set("fit", "best");
  if (status !== "all") params.set("status", status);
  if (withContact) params.set("contact", "1");
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
  const withContact = first(sp.contact) === "1";
  const statusParam = first(sp.status);
  const status: StatusFilter =
    statusParam === "due" || PROSPECT_STATUSES.includes(statusParam as ProspectStatus)
      ? (statusParam as StatusFilter)
      : "all";
  const owner = await viewerId();
  const [file, snap, contactFile, pipeline] = await Promise.all([
    getProspects(),
    getSnapshot(),
    getContacts(),
    owner ? getPipeline(owner) : Promise.resolve(new Map<string, PipelineRow>()),
  ]);
  const names = areaNames(snap);
  const today = todayChicago();

  const byTrade = new Map<string, number>();
  for (const p of file.prospects) byTrade.set(p.trade, (byTrade.get(p.trade) ?? 0) + 1);
  const statusOf = (p: Prospect): ProspectStatus => pipeline.get(p.id)?.status ?? "not_contacted";
  const byStatus = new Map<ProspectStatus, number>();
  let dueCount = 0;
  for (const p of file.prospects) {
    byStatus.set(statusOf(p), (byStatus.get(statusOf(p)) ?? 0) + 1);
    const row = pipeline.get(p.id);
    if (row && isDue(row, today)) dueCount++;
  }
  const matches = (p: Prospect) => {
    if (status === "all") return true;
    const row = pipeline.get(p.id);
    return status === "due" ? !!row && isDue(row, today) : statusOf(p) === status;
  };
  const suggestionsFor = (p: Prospect) => contactFile.prospects[p.id];
  const rows = file.prospects.filter(
    (p) =>
      (trade === "all" || p.trade === trade) &&
      (!best || isBestFit(p)) &&
      (!withContact || hasAnyContact(suggestionsFor(p))) &&
      matches(p),
  );
  if (status === "due") {
    rows.sort(
      (a, b) =>
        (pipeline.get(a.id)?.nextFollowUp ?? "").localeCompare(pipeline.get(b.id)?.nextFollowUp ?? "") ||
        a.id.localeCompare(b.id),
    );
  }
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Number(first(sp.page)) || 1));
  const shown = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");

  return (
    <div className="space-y-4">
      {owner && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          <Link
            href={href(trade, best, "due", 1, withContact)}
            className={cn("rounded-lg border p-3 hover:bg-muted", status === "due" && "border-primary bg-primary/5")}
          >
            <div className="text-xs text-muted-foreground">Due today / overdue</div>
            <div className={cn("text-xl font-semibold tabular-nums", dueCount > 0 && "text-amber-700")}>
              {count(dueCount)}
            </div>
          </Link>
          {PROSPECT_STATUSES.map((s) => (
            <Link
              key={s}
              href={href(trade, best, status === s ? "all" : s, 1, withContact)}
              className={cn("rounded-lg border p-3 hover:bg-muted", status === s && "border-primary bg-primary/5")}
            >
              <div className="text-xs text-muted-foreground">{PROSPECT_STATUS_LABEL[s]}</div>
              <div className="text-xl font-semibold tabular-nums">{count(byStatus.get(s) ?? 0)}</div>
            </Link>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Link href={href("all", best, status, 1, withContact)} className={pill(trade === "all")}>
          All trades ({count(file.prospects.length)})
        </Link>
        {PROSPECT_TRADES.map((t) => (
          <Link key={t} href={href(t, best, status, 1, withContact)} className={pill(trade === t)}>
            {snap.trades[t].label} ({count(byTrade.get(t) ?? 0)})
          </Link>
        ))}
        <span className="mx-1 hidden h-5 w-px bg-border sm:block" />
        <Link href={href(trade, !best, status, 1, withContact)} className={pill(best)} title="Already win violation jobs, 5–40 jobs a year">
          Best fit only
        </Link>
        <Link
          href={href(trade, best, status, 1, !withContact)}
          className={pill(withContact)}
          title="Phone, website, email or contact name found in public sources"
        >
          Has contact info
        </Link>
        {status !== "all" && (
          <Link href={href(trade, best, "all", 1, withContact)} className={pill(true)}>
            {status === "due" ? "Due today / overdue" : PROSPECT_STATUS_LABEL[status]} ×
          </Link>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        {count(rows.length)} contractors · permits through {dateLabel(file.generatedFor)}. Violation-driven jobs are
        permits pulled at an address that had a violation in the same trade in the year before.
      </p>

      {rows.length === 0 ? (
        <EmptyState title="No prospects match">Try another trade or turn off &ldquo;Best fit only&rdquo;.</EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[72rem] text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Company</th>
                <th className="px-4 py-2 font-medium">Pipeline</th>
                <th className="px-4 py-2 font-medium">Follow-up</th>
                <th className="px-4 py-2 font-medium">Contact info</th>
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
                <ProspectRow
                  key={p.id}
                  p={p}
                  label={snap.trades[p.trade].label}
                  names={names}
                  row={pipeline.get(p.id)}
                  today={today}
                  contact={suggestionsFor(p)}
                />
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
              <Link href={href(trade, best, status, page - 1, withContact)} className={buttonVariants({ variant: "outline", size: "sm" })}>
                Previous
              </Link>
            )}
            {page < pages && (
              <Link href={href(trade, best, status, page + 1, withContact)} className={buttonVariants({ variant: "outline", size: "sm" })}>
                Next
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ContactIcons({ contact }: { contact: ContactSuggestions | undefined }) {
  if (!hasAnyContact(contact) || !contact) return <span className="text-muted-foreground">—</span>;
  const items = [
    { on: contact.phones.length > 0, label: "phone", Icon: Phone },
    { on: !!contact.website, label: "website", Icon: Globe },
    { on: contact.emails.length > 0, label: "email", Icon: Mail },
    { on: !!contact.contactName, label: "contact name", Icon: UserRound },
  ];
  return (
    <span className="inline-flex items-center gap-1.5" title="Suggested from public sources; verify before use">
      {items.map(({ on, label, Icon }) => (
        <span key={label} className={on ? "text-primary" : "text-muted-foreground/30"}>
          <Icon className="size-4" aria-hidden />
          <span className="sr-only">{on ? `Has ${label}` : `No ${label}`}</span>
        </span>
      ))}
    </span>
  );
}

function ProspectRow({
  p,
  label,
  names,
  row,
  today,
  contact,
}: {
  p: Prospect;
  label: string;
  names: Map<number, string>;
  row: PipelineRow | undefined;
  today: string;
  contact: ContactSuggestions | undefined;
}) {
  const due = row ? isDue(row, today) : false;
  return (
    <tr>
      <td className="px-4 py-2.5 font-medium">{p.company}</td>
      <td className="px-4 py-2.5">
        <ProspectStatusBadge status={row?.status ?? "not_contacted"} />
      </td>
      <td className={cn("px-4 py-2.5 whitespace-nowrap", due ? "font-medium text-amber-700" : "text-muted-foreground")}>
        {row?.nextFollowUp ? dateLabel(row.nextFollowUp) : "—"}
        {due && row?.nextFollowUp && row.nextFollowUp < today ? " (overdue)" : ""}
      </td>
      <td className="px-4 py-2.5">
        <ContactIcons contact={contact} />
      </td>
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
