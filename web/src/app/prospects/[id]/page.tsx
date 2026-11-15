import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Trend } from "@/components/bits";
import { CopyButton } from "@/components/copy-button";
import { PrintButton } from "@/components/print-button";
import { ProspectPipelinePanel } from "@/components/prospect-pipeline-panel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count, dateLabel, money, pct } from "@/lib/format";
import { tradeNoun } from "@/lib/insights";
import { getProspectContacts } from "@/lib/contacts";
import { todayChicago } from "@/lib/pipeline";
import { getPipelineHistory, getPipelineRow } from "@/lib/prospect-pipeline";
import { getProspect } from "@/lib/prospects";
import { getSnapshot } from "@/lib/snapshot";
import { buildTeaser, draftColdEmail, joinNames } from "@/lib/teaser";
import { viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Prospect teaser" };

export default function TeaserPage({ params }: PageProps<"/prospects/[id]">) {
  return (
    <>
      <Link
        href="/prospects"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground print:hidden"
      >
        <ArrowLeft className="size-4" /> All prospects
      </Link>
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Teaser params={params} />
      </Suspense>
    </>
  );
}

async function Teaser({ params }: { params: PageProps<"/prospects/[id]">["params"] }) {
  const { id } = await params;
  const [prospect, snap] = await Promise.all([getProspect(decodeURIComponent(id)), getSnapshot()]);
  if (!prospect) notFound();

  const t = buildTeaser(snap, prospect);
  const tradeLabel = snap.trades[prospect.trade].label;
  const noun = tradeNoun(prospect.trade);
  const email = draftColdEmail(prospect, t);
  const emailText = `Subject: ${email.subject}\n\n${email.body}`;

  return (
    <div className="mx-auto max-w-4xl space-y-8 print:max-w-none print:space-y-5 print:text-[10pt]">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Brickline · prepared for {prospect.company}</div>
          <h1 className="text-2xl font-semibold tracking-tight">What Brickline found for {prospect.company} this week</h1>
          <p className="text-sm text-muted-foreground">
            {tradeLabel} · {joinNames(t.areaNames) || "Chicago"} · city and county data through {dateLabel(t.dataAsOf)}
          </p>
        </div>
        <PrintButton label="Print teaser" />
      </header>

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>Pipeline</CardTitle>
          <CardDescription>
            Your private sales tracking for this contractor: status, contact details (suggestions from public sources, or found by hand), notes, and the
            email sequence (day 0, 4, 10). Only you see this.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<Skeleton className="h-64 w-full" />}>
            <Pipeline prospectId={prospect.id} />
          </Suspense>
        </CardContent>
      </Card>

      <section className="grid grid-cols-3 gap-3">
        <Stat label="Open leads in your areas" value={count(t.openLeads)} />
        <Stat label="Act-now leads" value={count(t.actNowLeads)} />
        <Stat
          label="Expected profit, act-now"
          value={money(t.actNowValue)}
          hint={`${pct(t.winRate.individual, 0)} close (individual owners), ${pct(t.winRate.company, 0)} (companies), ${pct(t.margin, 0)} margin: default assumptions`}
        />
      </section>

      <section>
        <h2 className="mb-2 font-semibold">Open leads by signal</h2>
        {t.byKind.length === 0 ? (
          <p className="text-sm text-muted-foreground">No open leads for this trade in these neighborhoods right now.</p>
        ) : (
          <ul className="grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2 print:grid-cols-2">
            {t.byKind.map((k) => (
              <li key={k.kind} className="flex justify-between gap-2 border-b py-1">
                <span>{k.label}</span>
                <span className="tabular-nums text-muted-foreground">{count(k.count)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {t.samples.length > 0 && (
        <section>
          <h2 className="mb-2 font-semibold">Three sample leads</h2>
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="py-1.5 pr-3 font-medium">Property</th>
                <th className="py-1.5 pr-3 font-medium">Signal</th>
                <th className="py-1.5 text-right font-medium">Chance of work</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {t.samples.map((s) => (
                <tr key={s.id} className="break-inside-avoid">
                  <td className="py-2 pr-3">
                    <div className="font-medium">{s.maskedAddress}</div>
                    <div className="text-xs text-muted-foreground">{s.area}</div>
                  </td>
                  <td className="py-2 pr-3">{s.title}</td>
                  <td className="py-2 text-right tabular-nums">{pct(s.chance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-xs text-muted-foreground">
            Full addresses, owner contacts, evidence and a drafted letter come with the weekly list.
          </p>
        </section>
      )}

      <section>
        <h2 className="mb-2 font-semibold">Neighborhood trends</h2>
        <p className="mb-2 text-xs text-muted-foreground">Last 90 days compared with the same 90 days a year earlier.</p>
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="py-1.5 pr-3 font-medium">Neighborhood</th>
              <th className="py-1.5 pr-3 font-medium">{tradeLabel} violations</th>
              <th className="py-1.5 font-medium">{tradeLabel} permits</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {t.trends.map((a) => (
              <tr key={a.id}>
                <td className="py-2 pr-3 font-medium">{a.name}</td>
                <td className="py-2 pr-3 tabular-nums">
                  {a.violations ? (
                    <>
                      {count(a.violations.now)} <Trend now={a.violations.now} before={a.violations.before} />
                    </>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="py-2 tabular-nums">
                  {count(a.permits.now)} <Trend now={a.permits.now} before={a.permits.before} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid gap-8 sm:grid-cols-2 print:grid-cols-2">
        <div>
          <h2 className="mb-2 font-semibold">Your {noun} activity</h2>
          <ul className="space-y-1 text-sm">
            <li className="flex justify-between gap-2">
              <span>Permitted jobs, last 12 months</span>
              <span className="tabular-nums">
                {count(prospect.jobs12m)} <Trend now={prospect.jobs12m} before={prospect.jobsPrev12m} />
              </span>
            </li>
            <li className="flex justify-between gap-2">
              <span>Jobs in the 12 months before</span>
              <span className="tabular-nums">{count(prospect.jobsPrev12m)}</span>
            </li>
            <li className="flex justify-between gap-2">
              <span>Typical job size</span>
              <span className="tabular-nums">{money(prospect.medianJob)}</span>
            </li>
            <li className="flex justify-between gap-2">
              <span>Most recent permit</span>
              <span className="tabular-nums">{dateLabel(prospect.lastJob)}</span>
            </li>
            <li className="flex justify-between gap-2">
              <span>Jobs at addresses with a recent violation</span>
              <span className="tabular-nums">{count(prospect.violationDrivenJobs)}</span>
            </li>
          </ul>
        </div>
        <div>
          <h2 className="mb-2 font-semibold">Most active competitors in your areas</h2>
          {t.competitors.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              None of the citywide top 25 {noun} contractors is concentrated in your neighborhoods.
            </p>
          ) : (
            <ul className="space-y-2 text-sm">
              {t.competitors.map((c) => (
                <li key={c.name}>
                  <div className="flex justify-between gap-2">
                    <span className="truncate font-medium">{c.name}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {count(c.jobs12m)} jobs <Trend now={c.jobs12m} before={c.jobsPrev12m} />
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">{joinNames(c.areas)}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="break-inside-avoid rounded-lg border bg-primary/5 p-4">
        <h2 className="font-semibold">Try it free</h2>
        <p className="mt-1 text-sm">
          Brickline is offering a free first month to a few Chicago {noun} contractors. You get a weekly list like this
          one for your neighborhoods, with the evidence behind each lead, how often similar signals have led to a
          permitted job, and a drafted letter or email for each. In return, we ask for a few minutes of feedback each
          week and for you to tell us which leads turned into jobs.
        </p>
        {t.violationModel && (
          <p className="mt-2 text-sm">
            For example: {pct(t.violationModel.individual)} of individually owned properties cited for {noun}{" "}
            violations pulled a {noun} permit within a year ({count(t.violationModel.episodes)} citations in
            Chicago&apos;s records).
          </p>
        )}
        <p className="mt-2 text-xs text-muted-foreground">
          Source: City of Chicago building permits, violations and 311 requests; Cook County Assessor sales and parcels.
          Rates are historical and permits miss unpermitted work. Brickline is independent and not affiliated with the
          City of Chicago.
        </p>
      </section>

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>Cold-email draft</CardTitle>
          <CardDescription>
            Review before sending. Fill in your name and mailing address, send from your own mailbox (never from a
            tool that hides who you are), and honor opt-outs right away. Do not add owner names.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="text-sm">
              <span className="text-muted-foreground">Subject: </span>
              <span className="font-medium">{email.subject}</span>
            </div>
            <CopyButton text={emailText} label="Copy email" />
          </div>
          <pre className="rounded-md border bg-muted/40 p-4 font-sans text-sm leading-relaxed whitespace-pre-wrap">
            {email.body}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

const historyTime = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Chicago",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

async function Pipeline({ prospectId }: { prospectId: string }) {
  const owner = await viewerId();
  if (!owner) return <p className="text-sm text-muted-foreground">Sign in to track this prospect.</p>;
  const [row, history, suggestions] = await Promise.all([
    getPipelineRow(owner, prospectId),
    getPipelineHistory(owner, prospectId),
    getProspectContacts(prospectId),
  ]);
  return (
    <ProspectPipelinePanel
      prospectId={prospectId}
      today={todayChicago()}
      suggestions={suggestions}
      state={{
        status: row?.status ?? "not_contacted",
        contactName: row?.contactName ?? "",
        email: row?.email ?? "",
        phone: row?.phone ?? "",
        website: row?.website ?? "",
        notes: row?.notes ?? "",
        sequenceStep: row?.sequenceStep ?? 0,
        nextFollowUp: row?.nextFollowUp ?? null,
      }}
      history={history.map((h) => ({ id: h.id, status: h.status, note: h.note, at: historyTime.format(h.createdAt) }))}
    />
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-[11px] leading-snug text-muted-foreground">{hint}</div>}
    </div>
  );
}
