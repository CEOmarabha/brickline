import { ArrowRight, Lightbulb, LineChart, Swords, TimerReset, Database } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader, StatCard, Trend } from "@/components/bits";
import { LeadList } from "@/components/lead-list";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count, money } from "@/lib/format";
import { buildInsights, type Insight } from "@/lib/insights";
import { areaNames, expectedValue, getSnapshot, leadsForWorkspace, TIER_ORDER } from "@/lib/snapshot";
import { getStatuses, getWorkspace } from "@/lib/workspace";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <Dashboard />
    </Suspense>
  );
}

async function Dashboard() {
  const [snap, ws, statuses] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses()]);
  const names = areaNames(snap);
  const tradeLabel = snap.trades[ws.trade].label;
  const leads = leadsForWorkspace(snap, ws.trade, ws.areas);
  const open = leads.filter((l) => !statuses.has(l.id) || statuses.get(l.id)?.status === "new");
  const actNow = open.filter((l) => l.tier === "act_now");
  const top = [...open]
    .sort(
      (a, b) =>
        TIER_ORDER[a.tier] - TIER_ORDER[b.tier] || expectedValue(b, ws.trade, snap) - expectedValue(a, ws.trade, snap),
    )
    .slice(0, 6);
  const pipeline = [...statuses.values()];
  const insights = buildInsights(snap, ws, leads, statuses);
  const areaRows = snap.areas
    .filter((a) => ws.areas.length === 0 || ws.areas.includes(a.id))
    .map((a) => {
      const v = a.violations[ws.trade];
      const now = ws.trade === "general" ? a.majorProjects.last90 : (v?.last90 ?? 0);
      const before = ws.trade === "general" ? a.majorProjects.lastYear : (v?.lastYear ?? 0);
      return { a, now, before, openLeads: open.filter((l) => l.communityArea === a.id).length };
    })
    .sort((x, y) => y.openLeads - x.openLeads || y.now - x.now)
    .slice(0, 6);

  return (
    <>
      <PageHeader
        title={ws.businessName ? `This week for ${ws.businessName}` : "This week in Chicago"}
        description={
          <>
            {tradeLabel} leads in{" "}
            {ws.areas.length === 0 ? "all 77 community areas" : `${ws.areas.length} neighborhoods you serve`}. Every
            number comes from public records and historical outcomes.
          </>
        }
        actions={
          <Link href="/leads" className={buttonVariants()}>
            Open leads <ArrowRight />
          </Link>
        }
      />

      {!ws.configured && (
        <Card className="mb-6 border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle>Tell us what you do and where</CardTitle>
            <CardDescription>
              Pick your trade and the neighborhoods you work in, and add the phone and mailing address that go on your
              letters. Until then you&apos;re seeing citywide porch leads.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/settings" className={buttonVariants()}>
              Set up your business
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Act now" value={count(actNow.length)} hint="New signals worth contacting this week" />
        <StatCard
          label="Expected value, act-now leads"
          value={money(actNow.reduce((s, l) => s + expectedValue(l, ws.trade, snap), 0))}
          hint="Gross profit at your stated assumptions"
        />
        <StatCard label="Open leads" value={count(open.length)} hint="Not yet worked" />
        <StatCard
          label="Your pipeline"
          value={`${count(pipeline.filter((s) => s.status === "contacted").length)} · ${count(
            pipeline.filter((s) => s.status === "meeting").length,
          )} · ${count(pipeline.filter((s) => s.status === "won").length)}`}
          hint="Contacted · meetings · won"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-2">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Lightbulb className="size-4 text-primary" /> Suggested moves
          </h2>
          <div className="flex flex-col gap-3">
            {insights.map((i) => (
              <InsightCard key={i.id} insight={i} />
            ))}
          </div>
        </section>
        <section className="lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Best leads right now</h2>
            <Link href="/leads" className="text-sm text-primary hover:underline">
              See all {count(open.length)}
            </Link>
          </div>
          <LeadList leads={top} snap={snap} trade={ws.trade} statuses={statuses} areaNames={names} />

          <div className="mt-6 mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Your neighborhoods</h2>
            <Link href="/areas" className="text-sm text-primary hover:underline">
              Compare all
            </Link>
          </div>
          <Card className="py-0">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Neighborhood</th>
                  <th className="px-4 py-2 font-medium">
                    {ws.trade === "general" ? "Major projects, 90 days" : "Violations, 90 days"}
                  </th>
                  <th className="px-4 py-2 text-right font-medium">Open leads</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {areaRows.map(({ a, now, before, openLeads }) => (
                  <tr key={a.id}>
                    <td className="px-4 py-2.5">
                      <Link href={`/leads?area=${a.id}`} className="hover:underline">
                        {a.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 tabular-nums">
                      {count(now)} <Trend now={now} before={before} />
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{count(openLeads)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </section>
      </div>
    </>
  );
}

const INSIGHT_ICON: Record<Insight["kind"], React.ComponentType<{ className?: string }>> = {
  opportunity: Lightbulb,
  market: LineChart,
  competition: Swords,
  follow_up: TimerReset,
  data: Database,
};

function InsightCard({ insight }: { insight: Insight }) {
  const Icon = INSIGHT_ICON[insight.kind];
  return (
    <Card className={cn("gap-2 py-4", insight.kind === "data" && "bg-muted/40 shadow-none")}>
      <CardHeader className="px-4">
        <CardTitle className="flex items-start gap-2 text-sm leading-snug">
          <Icon className="mt-0.5 size-4 shrink-0 text-primary" />
          {insight.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 text-sm text-muted-foreground">
        <p>{insight.detail}</p>
        {insight.href && (
          <Link href={insight.href} className="mt-2 inline-flex items-center gap-1 font-medium text-primary">
            {insight.cta} <ArrowRight className="size-3.5" />
          </Link>
        )}
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-10 w-80" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <Skeleton className="h-96 lg:col-span-2" />
        <Skeleton className="h-96 lg:col-span-3" />
      </div>
    </div>
  );
}
