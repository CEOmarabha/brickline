import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, StatCard } from "@/components/bits";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count, exactMoney, money, pct } from "@/lib/format";
import { getOutcomes, MIN_DECIDED, MIN_VALUED_WON } from "@/lib/outcomes";
import { getSnapshot } from "@/lib/snapshot";

export const metadata: Metadata = { title: "Results" };

export default function ResultsPage() {
  return (
    <>
      <PageHeader
        title="Results"
        description="What happened to the leads this workspace worked, and the job values you entered on won leads. Once there are enough won and lost leads, these measured rates replace the default assumptions in every expected-value number."
      />
      <Suspense fallback={<Skeleton className="h-[30rem] w-full" />}>
        <Results />
      </Suspense>
    </>
  );
}

async function Results() {
  const [{ rows, rates, ownerTotals, revenue, permitJobValue, tradeLabel }, snap] = await Promise.all([
    getOutcomes(),
    getSnapshot(),
  ]);
  const wonRows = rows.filter((r) => r.won > 0);
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

      <Card>
        <CardHeader>
          <CardTitle>Revenue from won jobs</CardTitle>
          <CardDescription>
            Entered by you on Won leads. Nothing here is estimated: a won job counts only once you have typed its value,
            and the figures below leave out won jobs without one.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Won jobs with a value"
              value={count(revenue.wonWithValue)}
              hint={`of ${count(revenue.won)} won, entered by you`}
            />
            <StatCard
              label="Total won value"
              value={revenue.wonWithValue > 0 ? exactMoney(revenue.totalWonValue) : "—"}
              hint="Sum of the values you entered"
            />
            <StatCard
              label="Median job value"
              value={exactMoney(revenue.medianJobValue)}
              hint={revenue.wonWithValue > 0 ? `Across ${count(revenue.wonWithValue)} won jobs` : "No values entered yet"}
            />
            <StatCard
              label="Revenue per worked lead"
              value={exactMoney(revenue.revenuePerWorkedLead)}
              hint={`Total won value ÷ ${count(revenue.worked)} leads worked`}
            />
          </div>

          {wonRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No won leads yet. Mark a lead Won and enter its job value on the lead page; revenue by signal builds up here.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[40rem] text-sm">
                <thead className="border-y text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 font-medium">Signal</th>
                    <th className="px-4 py-2 font-medium">Won with value</th>
                    <th className="px-4 py-2 font-medium">Total value</th>
                    <th className="px-4 py-2 font-medium">Median job</th>
                    <th className="px-4 py-2 font-medium">Revenue per worked lead</th>
                    <th className="px-4 py-2 font-medium">Job value in expected value</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {wonRows.map((r) => (
                    <tr key={r.key}>
                      <td className="px-4 py-2.5 font-medium">{r.label}</td>
                      <td className="px-4 py-2.5 tabular-nums">
                        {r.wonWithValue} of {r.won}
                      </td>
                      <td className="px-4 py-2.5 tabular-nums">{r.wonWithValue > 0 ? exactMoney(r.totalWonValue) : "—"}</td>
                      <td className="px-4 py-2.5 tabular-nums">{exactMoney(r.medianJobValue)}</td>
                      <td className="px-4 py-2.5 tabular-nums">{exactMoney(r.revenuePerWorkedLead)}</td>
                      <td className="px-4 py-2.5">
                        {r.jobValueMeasured ? (
                          <span>
                            <span className="font-medium">Your median</span>{" "}
                            <span className="tabular-nums">({exactMoney(r.medianJobValue)})</span>
                          </span>
                        ) : (
                          <span className="text-muted-foreground">
                            Permit-based ({money(permitJobValue)}); {r.wonWithValue} of {MIN_VALUED_WON} valued wins
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Expected value uses the permit-based typical {tradeLabel.toLowerCase()} job ({money(permitJobValue)}). Once a
            signal has {MIN_VALUED_WON} or more won jobs with a value, it uses the median job value you entered for that
            signal instead; the table shows which one each signal uses.
          </p>
        </CardContent>
      </Card>

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
