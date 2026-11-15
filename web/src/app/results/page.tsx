import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, StatCard } from "@/components/bits";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count, pct } from "@/lib/format";
import { getOutcomes, MIN_DECIDED } from "@/lib/outcomes";
import { getSnapshot } from "@/lib/snapshot";

export const metadata: Metadata = { title: "Results" };

export default function ResultsPage() {
  return (
    <>
      <PageHeader
        title="Results"
        description="What happened to the leads this workspace worked. Once there are enough won and lost leads, these measured rates replace the default assumptions in every expected-value number."
      />
      <Suspense fallback={<Skeleton className="h-[30rem] w-full" />}>
        <Results />
      </Suspense>
    </>
  );
}

async function Results() {
  const [{ rows, rates, ownerTotals }, snap] = await Promise.all([getOutcomes(), getSnapshot()]);
  const totals = rows.reduce(
    (t, r) => ({ worked: t.worked + r.worked, meetings: t.meetings + r.meetings, won: t.won + r.won, lost: t.lost + r.lost }),
    { worked: 0, meetings: 0, won: 0, lost: 0 },
  );
  const assumptions = snap.meta.assumptions.winRate;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Leads worked" value={count(totals.worked)} hint="Contacted, meeting, won or lost" />
        <StatCard
          label="Meetings"
          value={count(totals.meetings)}
          hint={totals.worked ? `${pct(totals.meetings / totals.worked)} of worked leads` : "—"}
        />
        <StatCard label="Won" value={count(totals.won)} />
        <StatCard
          label="Win rate on decided leads"
          value={totals.won + totals.lost ? pct(totals.won / (totals.won + totals.lost)) : "—"}
          hint={`${count(totals.won + totals.lost)} won or lost`}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(["individual", "company"] as const).map((t) => {
          const decided = ownerTotals[t].won + ownerTotals[t].lost;
          const measured = rates[t];
          return (
            <Card key={t}>
              <CardHeader>
                <CardTitle>{t === "individual" ? "Mailed homeowners" : "Companies and investors"}</CardTitle>
                <CardDescription>Close rate used in scoring</CardDescription>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <div className="text-2xl font-semibold tabular-nums">{pct(measured ?? assumptions[t])}</div>
                <p className="text-muted-foreground">
                  {measured !== null
                    ? `Measured: ${ownerTotals[t].won} wins against ${ownerTotals[t].expectedJobs.toFixed(1)} jobs the model expected among ${decided} decided leads.`
                    : `Default assumption. ${Math.max(0, MIN_DECIDED - decided)} more won or lost leads and this switches to your measured rate.`}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>By signal</CardTitle>
          <CardDescription>Which kinds of leads turn into meetings and wins for this business.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          {rows.length === 0 ? (
            <div className="px-6">
              <EmptyState title="No outcomes recorded yet">
                Open a lead and mark it Contacted, Meeting booked, Won or Lost. Results build up here.{" "}
                <Link href="/leads" className="underline">
                  Go to leads
                </Link>
              </EmptyState>
            </div>
          ) : (
            <table className="w-full min-w-[40rem] text-sm">
              <thead className="border-y text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Signal</th>
                  <th className="px-4 py-2 font-medium">Worked</th>
                  <th className="px-4 py-2 font-medium">Meeting rate</th>
                  <th className="px-4 py-2 font-medium">Won / lost</th>
                  <th className="px-4 py-2 font-medium">Win rate (decided)</th>
                  <th className="px-4 py-2 font-medium">Not relevant</th>
                  <th className="px-4 py-2 font-medium">Median days to first contact</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r) => (
                  <tr key={r.key}>
                    <td className="px-4 py-2.5 font-medium">{r.label}</td>
                    <td className="px-4 py-2.5 tabular-nums">{count(r.worked)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{pct(r.meetingRate)}</td>
                    <td className="px-4 py-2.5 tabular-nums">
                      {r.won} / {r.lost}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums">{pct(r.closeRate)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{count(r.notRelevant)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{r.medianDaysSignalToContact ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
