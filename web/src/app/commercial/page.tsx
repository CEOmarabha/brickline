import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/bits";
import { ClosedRestaurants } from "@/components/commercial/closed-restaurants";
import { NewBusiness } from "@/components/commercial/new-business";
import { OpenTrades } from "@/components/commercial/open-trades";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { count, dateLabel, money, pct } from "@/lib/format";
import { areaNames, type GcTarget, getSnapshot } from "@/lib/snapshot";
import { getWorkspace } from "@/lib/workspace";

export const metadata: Metadata = { title: "Commercial" };

export default function CommercialPage() {
  return (
    <>
      <PageHeader
        title="Commercial intelligence"
        description={
          <>
            For subcontractors and suppliers: properties likely to file a major project before the permit exists, and
            general contractors who regularly bring in new subs.{" "}
            <Badge variant="outline" className="align-middle">
              Preview
            </Badge>
          </>
        }
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Commercial />
      </Suspense>
    </>
  );
}

async function Commercial() {
  const [snap, ws] = await Promise.all([getSnapshot(), getWorkspace()]);
  const names = areaNames(snap);
  const pre = snap.commercial.preApplication;
  const projects = pre.projects.filter(
    (p) => ws.areas.length === 0 || (p.communityArea !== null && ws.areas.includes(p.communityArea)),
  );

  return (
    <div className="space-y-10">
      <Tabs defaultValue="pre">
        <TabsList>
          <TabsTrigger value="pre">Pre-application projects</TabsTrigger>
          <TabsTrigger value="gc">General contractors to approach</TabsTrigger>
        </TabsList>

        <TabsContent value="pre" className="mt-4 space-y-4">
          <p className="max-w-3xl text-sm text-muted-foreground">
            Parcels whose current mix of signals (recent permits, violations, sales, demolition) historically preceded a
            $100k+ permit application within 180 days. Citywide base rate: {pct(pre.baseRate, 2)}. Back-tested on later
            years the model never saw, the highest-scoring parcels filed far more often than the base rate; the rate on
            each card is the historical rate for parcels with the same signals.
          </p>
          {projects.length === 0 ? (
            <p className="text-sm text-muted-foreground">None in your neighborhoods right now.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {projects.slice(0, 40).map((p) => (
                <Card key={p.id} className="gap-3">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle>{p.address}</CardTitle>
                        <CardDescription>
                          {p.communityArea ? names.get(p.communityArea) : "Chicago"}
                          {p.owner ? ` · ${p.owner}` : ""}
                        </CardDescription>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold tabular-nums">{pct(p.probability, 0)}</div>
                        <div className="text-xs text-muted-foreground">{p.lift}× base</div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="flex flex-wrap gap-1.5">
                      {p.signals.map((s) => (
                        <Badge key={s} variant="secondary" className="font-normal">
                          {s}
                        </Badge>
                      ))}
                    </div>
                    {p.recentPermits[0] && (
                      <div className="text-muted-foreground">
                        Latest permit {dateLabel(p.recentPermits[0].date)}: {p.recentPermits[0].description}
                      </div>
                    )}
                    {p.recentGcs.length > 0 && (
                      <div>
                        <span className="text-muted-foreground">GCs on recent permits:</span> {p.recentGcs.join(", ")}
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground">
                      Based on {count(p.historicalCases)} parcels with the same signals, 2019–2025.
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="gc" className="mt-4 space-y-4">
          <p className="max-w-3xl text-sm text-muted-foreground">
            &quot;Open door&quot; is the share of a GC&apos;s past jobs that used a subcontractor new to them. In
            back-testing, GCs with the highest open-door scores brought in a new sub on a much larger share of their
            next jobs than GCs with the lowest.
          </p>
          <Tabs defaultValue="electrical">
            <TabsList>
              <TabsTrigger value="electrical">Electrical</TabsTrigger>
              <TabsTrigger value="plumbing">Plumbing</TabsTrigger>
              <TabsTrigger value="hvac">HVAC</TabsTrigger>
            </TabsList>
            {(["electrical", "plumbing", "hvac"] as const).map((t) => (
              <TabsContent key={t} value={t} className="mt-3">
                <GcTable rows={snap.commercial.gcTargets[t]} names={names} />
              </TabsContent>
            ))}
          </Tabs>
        </TabsContent>
      </Tabs>
      <ClosedRestaurants snap={snap} names={names} />
      <NewBusiness snap={snap} names={names} />
      <OpenTrades snap={snap} names={names} />
    </div>
  );
}

function GcTable({ rows, names }: { rows: GcTarget[]; names: Map<number, string> }) {
  return (
    <Card className="overflow-x-auto py-0">
      <table className="w-full min-w-[48rem] text-sm">
        <thead className="border-b text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-4 py-2.5 font-medium">General contractor</th>
            <th className="px-4 py-2.5 font-medium">Open door</th>
            <th className="px-4 py-2.5 font-medium">Jobs, 24 mo</th>
            <th className="px-4 py-2.5 font-medium">Typical job</th>
            <th className="px-4 py-2.5 font-medium">Subs they use now</th>
            <th className="px-4 py-2.5 font-medium">Where</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((g) => (
            <tr key={g.gc}>
              <td className="px-4 py-2.5">
                <div className="font-medium">{g.gc}</div>
                <div className="text-xs text-muted-foreground">Last job {dateLabel(g.lastJob)}</div>
              </td>
              <td className="px-4 py-2.5 tabular-nums">{pct(g.openDoor, 0)}</td>
              <td className="px-4 py-2.5 tabular-nums">{count(g.jobs24m)}</td>
              <td className="px-4 py-2.5 tabular-nums">{money(g.medianCost)}</td>
              <td className="px-4 py-2.5 text-muted-foreground">
                {g.currentSubs.map((s) => `${s.name} (${s.jobs})`).join(", ")}
              </td>
              <td className="px-4 py-2.5 text-muted-foreground">
                {g.areas.map((a) => names.get(a)).filter(Boolean).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
