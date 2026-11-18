import type { Metadata } from "next";
import { Suspense } from "react";
import { EmptyState, PageHeader, Trend } from "@/components/bits";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TradeOnlyNote } from "@/components/trade-only-note";
import { count, dateLabel, money, pct } from "@/lib/format";
import { areaNames, getSnapshot } from "@/lib/snapshot";
import { isTradeTarget } from "@/lib/targets";
import { getWorkspace } from "@/lib/workspace";

export const metadata: Metadata = { title: "Market & competitors" };

export default function MarketPage() {
  return (
    <>
      <PageHeader
        title="Market & competitors"
        description="Who is pulling permits in your trade, how fast they're growing, and who is winning the jobs that follow violations."
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Market />
      </Suspense>
    </>
  );
}

async function Market() {
  const [snap, ws] = await Promise.all([getSnapshot(), getWorkspace()]);
  if (!isTradeTarget(ws.target)) return <TradeOnlyNote target={ws.target} snap={snap} />;
  const names = areaNames(snap);
  const comp = snap.competitors[ws.trade];
  const label = snap.trades[ws.trade].label;
  const wins = snap.recentWins.filter(
    (w) => w.trade === ws.trade && (ws.areas.length === 0 || (w.communityArea !== null && ws.areas.includes(w.communityArea))),
  );
  const total = comp.contractors.reduce((s, c) => s + c.jobs12m, 0);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Top {label.toLowerCase()} contractors, citywide</CardTitle>
          <CardDescription>
            Permitted jobs in the last 12 months. The top {comp.contractors.length} pulled {count(total)} jobs,{" "}
            {pct(comp.contractors.reduce((s, c) => s + c.share, 0), 0)} of all permits in this trade.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <table className="w-full min-w-[36rem] text-sm">
            <thead className="border-y text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">#</th>
                <th className="px-4 py-2 font-medium">Contractor</th>
                <th className="px-4 py-2 font-medium">Jobs, 12 mo</th>
                <th className="px-4 py-2 font-medium">Share</th>
                <th className="px-4 py-2 font-medium">Typical job</th>
                <th className="px-4 py-2 font-medium">Most active in</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {comp.contractors.map((c, i) => (
                <tr key={c.name}>
                  <td className="px-4 py-2.5 text-muted-foreground tabular-nums">{i + 1}</td>
                  <td className="px-4 py-2.5 font-medium">{c.name}</td>
                  <td className="px-4 py-2.5 tabular-nums">
                    {count(c.jobs12m)} <Trend now={c.jobs12m} before={c.jobsPrev12m} />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">{pct(c.share)}</td>
                  <td className="px-4 py-2.5 tabular-nums">{money(c.medianCost)}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {c.areas.map((a) => names.get(a)).filter(Boolean).join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Who wins violation jobs</CardTitle>
            <CardDescription>
              Contractors who pulled permits at addresses cited in the last 150 days. Speed to first contact decides
              these.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {comp.violationJobsWon.length === 0 ? (
              <p className="text-sm text-muted-foreground">No violation-driven permits named a contractor yet.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {comp.violationJobsWon.map((w) => (
                  <li key={w.name} className="flex justify-between gap-2">
                    <span className="truncate">{w.name}</span>
                    <span className="text-muted-foreground tabular-nums">{w.jobs}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recently resolved violations</CardTitle>
            <CardDescription>Repairs permitted in your neighborhoods: how long it took and who got the job.</CardDescription>
          </CardHeader>
          <CardContent>
            {wins.length === 0 ? (
              <EmptyState title="Nothing resolved yet">Recent violations in your areas haven&apos;t been permitted.</EmptyState>
            ) : (
              <ul className="space-y-3 text-sm">
                {wins.slice(0, 12).map((w) => (
                  <li key={`${w.address}-${w.permitDate}`}>
                    <div className="font-medium">{w.address}</div>
                    <div className="text-xs text-muted-foreground">
                      Cited {dateLabel(w.signalDate)} → permit {dateLabel(w.permitDate)} ({w.daysToPermit} days)
                      {w.contractor ? ` · ${w.contractor}` : ""}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
