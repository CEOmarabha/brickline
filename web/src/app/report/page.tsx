import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader, Trend } from "@/components/bits";
import { PrintButton } from "@/components/print-button";
import { Skeleton } from "@/components/ui/skeleton";
import { count, dateLabel, money, pct } from "@/lib/format";
import { buildInsights } from "@/lib/insights";
import { queryLeads, DEFAULT_FILTERS } from "@/lib/lead-query";
import { getCloseRates } from "@/lib/outcomes";
import { draftOutreach } from "@/lib/outreach";
import { areaNames, expectedValue, getSnapshot, tradeProbability } from "@/lib/snapshot";
import { getStatuses, getWorkspace, workspaceLabel } from "@/lib/workspace";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Weekly report" };

const TOP = 20;
const MAX_LETTERS = 100;

export default function ReportPage({ searchParams }: PageProps<"/report">) {
  return (
    <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
      <Report searchParams={searchParams} />
    </Suspense>
  );
}

async function Report({ searchParams }: { searchParams: PageProps<"/report">["searchParams"] }) {
  const sp = await searchParams;
  const view = sp.view === "letters" ? "letters" : "summary";
  const [snap, ws, statuses, rates] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses(), getCloseRates()]);
  const names = areaNames(snap);
  const label = workspaceLabel(ws);
  const tradeLabel = snap.trades[ws.trade].label;
  const open = queryLeads(snap, ws, statuses, { ...DEFAULT_FILTERS, status: "open" }, rates);

  const tabs = (
    <div className="flex gap-2 print:hidden">
      {(["summary", "letters"] as const).map((v) => (
        <Link
          key={v}
          href={v === "summary" ? "/report" : "/report?view=letters"}
          className={cn(
            "rounded-full border px-3 py-1 text-sm hover:bg-muted",
            view === v && "border-primary bg-primary/10 text-primary",
          )}
        >
          {v === "summary" ? "Client summary" : "Print-ready letters"}
        </Link>
      ))}
    </div>
  );

  if (view === "letters") {
    const letters = open
      .filter((l) => l.kind !== "investor_purchase" && l.owner.mailing && l.tier !== "monitor")
      .slice(0, MAX_LETTERS);
    return (
      <>
        <div className="print:hidden">
          <PageHeader
            title="Print-ready letters"
            description={`One letter per page for ${count(letters.length)} not-yet-contacted owner leads (act now and this week) with a mailing address. Print, sign, and mail; then mark them Contacted.`}
            actions={<PrintButton label="Print letters" />}
          />
          {tabs}
          {!ws.configured && (
            <p className="mt-3 text-sm text-muted-foreground">
              Add the company name, phone and mailing address in <Link href="/settings" className="underline">Settings</Link> first.
            </p>
          )}
        </div>
        <div className="mt-6 space-y-6 print:mt-0 print:space-y-0">
          {letters.map((l) => {
            const draft = draftOutreach(l, ws, snap, l.communityArea ? (names.get(l.communityArea) ?? null) : null);
            return (
              <article
                key={l.id}
                className="mx-auto max-w-[8.5in] break-after-page rounded-lg border bg-white p-12 text-[11pt] leading-relaxed text-black shadow-sm print:max-w-none print:rounded-none print:border-0 print:p-[0.9in] print:shadow-none"
              >
                <div className="mb-10 text-sm">
                  <div className="font-semibold">{ws.businessName || "[Your company]"}</div>
                  <div>{ws.mailingAddress || "[your mailing address]"}</div>
                  <div>{ws.phone || "[phone]"}</div>
                </div>
                <div className="mb-8 text-sm">
                  <div>{l.owner.name ?? "Property Owner"}</div>
                  <div className="whitespace-pre-line">{l.owner.mailing?.replace(", ", "\n")}</div>
                </div>
                <div className="mb-6 text-sm">{dateLabel(snap.meta.dataAsOf.violations)}</div>
                <div className="font-sans whitespace-pre-wrap">{draft.body}</div>
              </article>
            );
          })}
        </div>
      </>
    );
  }

  const top = open.slice(0, TOP);
  const actNow = open.filter((l) => l.tier === "act_now");
  const insights = buildInsights(snap, ws, open, statuses, rates).filter((i) => i.kind !== "data");
  const areas = snap.areas
    .filter((a) => ws.areas.length === 0 || ws.areas.includes(a.id))
    .map((a) => ({
      a,
      now: ws.trade === "general" ? a.majorProjects.last90 : (a.violations[ws.trade]?.last90 ?? 0),
      before: ws.trade === "general" ? a.majorProjects.lastYear : (a.violations[ws.trade]?.lastYear ?? 0),
      leads: open.filter((l) => l.communityArea === a.id).length,
    }))
    .sort((x, y) => y.leads - x.leads)
    .slice(0, 6);
  const competitors = snap.competitors[ws.trade].contractors.slice(0, 5);

  return (
    <div className="mx-auto max-w-4xl space-y-8 print:max-w-none print:text-[10pt]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Brickline weekly lead report</div>
          <h1 className="text-2xl font-semibold tracking-tight">{label}</h1>
          <p className="text-sm text-muted-foreground">
            {tradeLabel} · {ws.areas.length === 0 ? "all of Chicago" : `${ws.areas.length} neighborhoods`} · data through{" "}
            {dateLabel(snap.meta.dataAsOf.violations)}
          </p>
        </div>
        <PrintButton />
      </div>
      {tabs}

      <section className="grid grid-cols-3 gap-3">
        <Stat label="New act-now leads" value={count(actNow.length)} />
        <Stat label="Open leads" value={count(open.length)} />
        <Stat
          label="Expected value, act-now"
          value={money(actNow.reduce((s, l) => s + expectedValue(l, ws.trade, snap, rates), 0))}
        />
      </section>

      {insights.length > 0 && (
        <section>
          <h2 className="mb-2 font-semibold">This week&apos;s recommendations</h2>
          <ul className="list-disc space-y-1.5 pl-5 text-sm">
            {insights.map((i) => (
              <li key={i.id}>
                <span className="font-medium">{i.title}.</span> <span className="text-muted-foreground">{i.detail}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="mb-2 font-semibold">Top {top.length} leads</h2>
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="py-1.5 pr-3 font-medium">Property</th>
              <th className="py-1.5 pr-3 font-medium">Signal</th>
              <th className="py-1.5 pr-3 font-medium">Contact</th>
              <th className="py-1.5 pr-3 text-right font-medium">Chance</th>
              <th className="py-1.5 text-right font-medium">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {top.map((l) => (
              <tr key={l.id} className="break-inside-avoid align-top">
                <td className="py-2 pr-3">
                  <div className="font-medium">{l.address}</div>
                  <div className="text-xs text-muted-foreground">{l.communityArea ? names.get(l.communityArea) : ""}</div>
                </td>
                <td className="py-2 pr-3">
                  <div>{l.title}</div>
                  <div className="text-xs text-muted-foreground">{dateLabel(l.signalDate)}</div>
                </td>
                <td className="py-2 pr-3 text-xs">
                  {l.kind === "investor_purchase"
                    ? `${l.buyer.name}${l.buyer.purchases24m >= 3 ? ` (${l.buyer.purchases24m} buys)` : ""}`
                    : (l.owner.name ?? "Owner of record")}
                  {l.owner.mailing && <div className="text-muted-foreground">{l.owner.mailing}</div>}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">{pct(tradeProbability(l, ws.trade, snap))}</td>
                <td className="py-2 text-right tabular-nums">{money(expectedValue(l, ws.trade, snap, rates))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid gap-8 sm:grid-cols-2 print:grid-cols-2">
        <div>
          <h2 className="mb-2 font-semibold">Neighborhoods</h2>
          <ul className="space-y-1 text-sm">
            {areas.map(({ a, now, before, leads }) => (
              <li key={a.id} className="flex justify-between gap-2">
                <span>{a.name}</span>
                <span className="tabular-nums text-muted-foreground">
                  {count(leads)} leads · {count(now)} {ws.trade === "general" ? "projects" : "violations"}{" "}
                  <Trend now={now} before={before} />
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="mb-2 font-semibold">Most active competitors</h2>
          <ul className="space-y-1 text-sm">
            {competitors.map((c) => (
              <li key={c.name} className="flex justify-between gap-2">
                <span className="truncate">{c.name}</span>
                <span className="tabular-nums text-muted-foreground">{count(c.jobs12m)} jobs / 12 mo</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <p className="text-xs text-muted-foreground">
        Chance of work is the historical rate at which the same kind of signal in Chicago led to a permitted job,
        adjusted for time already passed. Sources: City of Chicago building permits and violations; Cook County
        Assessor sales and parcel records.
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}
