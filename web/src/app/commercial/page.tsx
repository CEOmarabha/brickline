import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/bits";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { count, dateLabel, liftLabel, money, pct } from "@/lib/format";
import {
  areaNames,
  type ClosedRestaurantLead,
  type GcTarget,
  getSnapshot,
  type PermitContractor,
  type Snapshot,
} from "@/lib/snapshot";
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
            $100k+ permit application within 180 days. Citywide base rate: {pct(pre.baseRate, 2)}. Tested on 2022–2024
            data the model never saw: the top 100 parcels per half-year hit about 26%.
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
            &quot;Open door&quot; is the share of a GC&apos;s past jobs that used a subcontractor new to them. In testing,
            GCs in the top fifth brought in a new sub on about 30% of their next jobs, versus under 6% for the bottom
            fifth.
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

const CLOSED_ROWS = 60;

/** Citywide pilot list (not filtered by workspace): restaurant spaces recorded closed in the last 180 days. */
function ClosedRestaurants({ snap, names }: { snap: Snapshot; names: Map<number, string> }) {
  const m = snap.models.closedRestaurant;
  const all = snap.leads.filter((l): l is ClosedRestaurantLead => l.kind === "closed_restaurant");
  const rows = all.slice(0, CLOSED_ROWS);
  return (
    <section className="space-y-4" aria-labelledby="closed-restaurants">
      <div>
        <h2 id="closed-restaurants" className="text-lg font-semibold tracking-tight">
          Closed restaurant spaces (pilot list)
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Restaurants recorded out of business in public inspection data, with no new food license under another name
          yet. Of {count(m.episodes)} closures ({m.period}, about {m.closuresPerWeek.toFixed(1)} a week lately),{" "}
          {pct(m.license.p365)} were followed by a new food business at the same address within a year, versus{" "}
          {pct(m.license.baseline365)} after ordinary restaurant inspections ({m.license.lift.toFixed(1)}x). Many of
          those licenses arrive within weeks; counting only licenses issued 31+ days after the closure it is{" "}
          {pct(m.licenseAfter30.p365)} versus {pct(m.licenseAfter30.baseline365)} ({m.licenseAfter30.lift.toFixed(1)}x),
          a median of {m.licenseAfter30.medianDays.toFixed(0)} days later (middle half{" "}
          {m.licenseAfter30.daysP25.toFixed(0)}–{m.licenseAfter30.daysP75.toFixed(0)} days). A renovation or build-out
          permit follows {pct(m.permit.p365)} versus {pct(m.permit.baseline365)} ({m.permit.lift.toFixed(2)}x),{" "}
          {liftLabel(m.permit.lift)}. Rates are floors: the license table covers retail food establishments only.
        </p>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Pilot list: who will pay for this (build-out general contractors, kitchen equipment dealers, signage,
          brokers) is unproven. It shows every current space citywide, not just your neighborhoods.
        </p>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No closures in the last 180 days of inspection data.</p>
      ) : (
        <>
          <Card className="overflow-x-auto py-0">
            <table className="w-full min-w-[52rem] text-sm">
              <thead className="border-b text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Address</th>
                  <th className="px-4 py-2.5 font-medium">Neighborhood</th>
                  <th className="px-4 py-2.5 font-medium">Restaurant</th>
                  <th className="px-4 py-2.5 font-medium">Closed</th>
                  <th className="px-4 py-2.5 text-right font-medium">New food business</th>
                  <th className="px-4 py-2.5 text-right font-medium">Build-out permit</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((l) => (
                  <tr key={l.id}>
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/leads/${encodeURIComponent(l.id)}`}
                        className="font-medium underline-offset-2 hover:underline"
                      >
                        {l.address}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">
                      {l.communityArea ? (names.get(l.communityArea) ?? "Chicago") : "Chicago"}
                    </td>
                    <td className="px-4 py-2.5">{l.restaurant.name ?? "—"}</td>
                    <td className="px-4 py-2.5 whitespace-nowrap">{dateLabel(l.signalDate)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{pct(l.probability, 0)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{pct(l.tradeProbabilities.general ?? null, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <p className="text-xs text-muted-foreground">
            {all.length > rows.length
              ? `Showing the newest ${count(rows.length)} of ${count(all.length)} spaces, newest first.`
              : `${count(all.length)} spaces, newest first.`}{" "}
            Chances are historical rates adjusted for the days since the closure. Source: City of Chicago food
            inspections and business licenses.
          </p>
        </>
      )}
    </section>
  );
}

const NEW_BUSINESS_ROWS = 60;
const BIG_PERMIT_ROWS = 60;

function classLabel(c: string): string {
  return c === "unknown class" ? "Class not on record" : c.charAt(0).toUpperCase() + c.slice(1);
}

function contractorList(list: PermitContractor[], max: number): string {
  const shown = list.slice(0, max).map((c) => `${c.name} (${c.role.toLowerCase()})`);
  return list.length > max ? `${shown.join("; ")}; +${list.length - max} more` : shown.join("; ");
}

function range(lo: number | null, hi: number | null): string {
  return lo === null || hi === null ? "—" : `${lo.toFixed(0)}–${hi.toFixed(0)}`;
}

/** Citywide pilot list (not filtered by workspace): build-out permits at addresses with no business license. */
function NewBusiness({ snap, names }: { snap: Snapshot; names: Map<number, string> }) {
  const { model: m, spaces, spacesTotal } = snap.commercial.newBusiness;
  const rows = spaces.slice(0, NEW_BUSINESS_ROWS);
  const groups = m.byGroup.slice(0, 3);
  return (
    <section className="space-y-4" aria-labelledby="new-business">
      <div>
        <h2 id="new-business" className="text-lg font-semibold tracking-tight">
          New business coming (pilot list)
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Build-out permits at commercial, mixed-use and 7+ unit addresses where no business license was in force on
          the permit date. Of {count(m.signals)} such permits ({m.period}, about {m.perWeek.toFixed(0)} a week), {pct(m.rate)}{" "}
          were followed by a new business license at the same address within a year, versus {pct(m.matchedRate)} at
          comparable unlicensed addresses with no renovation permit ({m.lift.toFixed(1)}x, {liftLabel(m.lift)}). Against
          addresses with some other recent permit it is {pct(m.busyRate)} ({m.liftVsBusy.toFixed(1)}x,{" "}
          {liftLabel(m.liftVsBusy)}). The license arrives late: a median {m.medianDays.toFixed(0)} days after the permit
          (middle half {m.daysP25.toFixed(0)}–{m.daysP75.toFixed(0)} days), so a seller can reach the new tenant months
          ahead of the license record. Who arrives (share of the new licenses):{" "}
          {groups.map((g) => `${g.group} ${pct(g.share, 0)}`).join(", ")}.
        </p>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Pilot list for sellers to new businesses (signage, payments and POS, insurance, cleaning, security,
          furniture) and the brokers and subs who serve them. It is a targeting list, not a chance of work for any
          trade, and the rates are floors (unlicensed tenants and offices are invisible). Who pays for it is unproven.
          It shows every current space citywide, not just your neighborhoods.
        </p>
      </div>
      <Card className="overflow-x-auto py-0">
        <table className="w-full min-w-[40rem] text-sm">
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Address class</th>
              <th className="px-4 py-2.5 text-right font-medium">Permits</th>
              <th className="px-4 py-2.5 text-right font-medium">New license in a year</th>
              <th className="px-4 py-2.5 text-right font-medium">Comparable addresses</th>
              <th className="px-4 py-2.5 text-right font-medium">Lift</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {m.byClass.map((c) => (
              <tr key={c.class}>
                <td className="px-4 py-2.5">{classLabel(c.class)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{count(c.signals)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{pct(c.rate)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{pct(c.matchedRate)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {c.lift.toFixed(1)}x <span className="text-muted-foreground">({liftLabel(c.lift)})</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No qualifying build-out permits in the last 180 days.</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-medium">Current spaces: build-out permits from the last 180 days</p>
            <a href="/export/new-business" className={buttonVariants({ variant: "outline", size: "sm" })} download>
              Download CSV ({count(spaces.length)} spaces)
            </a>
          </div>
          <Card className="overflow-x-auto py-0">
            <table className="w-full min-w-[64rem] text-sm">
              <thead className="border-b text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Address</th>
                  <th className="px-4 py-2.5 font-medium">Class</th>
                  <th className="px-4 py-2.5 font-medium">Permit date</th>
                  <th className="px-4 py-2.5 text-right font-medium">Cost</th>
                  <th className="px-4 py-2.5 font-medium">Work</th>
                  <th className="px-4 py-2.5 font-medium">Contractor</th>
                  <th className="px-4 py-2.5 text-right font-medium">New license in a year</th>
                </tr>
              </thead>
              <tbody className="divide-y align-top">
                {rows.map((s) => (
                  <tr key={s.id}>
                    <td className="px-4 py-2.5">
                      <div className="font-medium">{s.address}</div>
                      <div className="text-xs text-muted-foreground">
                        {s.communityArea ? (names.get(s.communityArea) ?? "Chicago") : "Chicago"}
                      </div>
                      {s.alsoClosedRestaurant && (
                        <Badge variant="secondary" className="mt-1 font-normal">
                          Also a closed restaurant
                        </Badge>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">{classLabel(s.class)}</td>
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      <a
                        href={s.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="underline-offset-2 hover:underline"
                      >
                        {dateLabel(s.permitDate)}
                      </a>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{money(s.reportedCost)}</td>
                    <td className="max-w-xs px-4 py-2.5 text-xs text-muted-foreground">{s.workDescription || "—"}</td>
                    <td className="max-w-56 px-4 py-2.5 text-xs">
                      {contractorList(s.contractors, 3) || <span className="text-muted-foreground">Not named</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{pct(s.historicalRate, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <p className="text-xs text-muted-foreground">
            {spacesTotal > rows.length
              ? `Showing the newest ${count(rows.length)} of ${count(spacesTotal)} spaces${spaces.length < spacesTotal ? ` (the CSV holds the newest ${count(spaces.length)})` : ""}, newest first.`
              : `${count(rows.length)} spaces, newest first.`}{" "}
            The last column is the class&apos;s historical rate of a new license within a year, adjusted for the days
            since the permit with no license yet; it is not a chance of work. A space drops off once any business
            license is issued at the address. Source: City of Chicago building permits and business licenses.
          </p>
        </>
      )}
    </section>
  );
}

/** Citywide block: which trades are still open after a $1M+ permit, and the recent big permits. */
function OpenTrades({ snap, names }: { snap: Snapshot; names: Map<number, string> }) {
  const { model: m, recent, recentTotal } = snap.commercial.openTrades;
  const rows = recent.slice(0, BIG_PERMIT_ROWS);
  const labels = new Map(m.byTrade.map((t) => [t.trade, t.label]));
  const openCount = m.byTrade.filter((t) => !t.mostlyLockedIn).length;
  const headline = m.headlineTrades.map((t) => (labels.get(t) ?? t).toLowerCase());
  return (
    <section className="space-y-4" aria-labelledby="open-trades">
      <div>
        <h2 id="open-trades" className="text-lg font-semibold tracking-tight">
          Trades still open after big permits
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          After a $1M+ new-construction or renovation permit at a commercial, multifamily, mixed-use or flats address (
          {count(m.bigPermits)} permits, {m.period}; about {m.perWeek.toFixed(0)} a week across all address types),{" "}
          {pct(m.followOnRate, 0)} saw a follow-on permit for {headline.slice(0, -1).join(", ")} or{" "}
          {headline[headline.length - 1]} work at the address within 540 days (median {m.medianDays.toFixed(0)} days,
          middle half {m.daysP25.toFixed(0)}–{m.daysP75.toFixed(0)}). Compared with addresses that only had a
          $100k–$1M permit, that is {m.liftVsBusy.toFixed(1)}x, {liftLabel(m.liftVsBusy)}: much of it is simply an active
          building. The useful part is who gets the work: in {openCount} of {m.byTrade.length} trades most follow-on
          permits go to a contractor that was not named on the big permit; in the rest the contractor is mostly
          already on it (locked in) or not named at all.
        </p>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Targeting list for sellers in the open trades, not a chance of work for any trade. Contractor names are
          matched exactly (cut at 30 characters), so spelling variants count as new, and permits capture permitted work
          only. Shows every address citywide.
        </p>
      </div>
      <Card className="overflow-x-auto py-0">
        <table className="w-full min-w-[52rem] text-sm">
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Trade</th>
              <th className="px-4 py-2.5 text-right font-medium">Big permits followed by it</th>
              <th className="px-4 py-2.5 text-right font-medium">...with a new contractor</th>
              <th className="px-4 py-2.5 text-right font-medium">Follow-on permits to a new contractor</th>
              <th className="px-4 py-2.5 text-right font-medium">Median days (middle half)</th>
              <th className="px-4 py-2.5 text-right font-medium">Vs busy addresses</th>
              <th className="px-4 py-2.5 font-medium">Open?</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {m.byTrade.map((t) => (
              <tr key={t.trade}>
                <td className="px-4 py-2.5 font-medium">
                  {t.label}
                  {t.signals !== m.bigPermits && (
                    <div className="text-xs font-normal text-muted-foreground">
                      shorter history, {count(t.signals)} permits
                    </div>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">{pct(t.followOnRate, 0)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{pct(t.newContractorRate, 0)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{pct(t.newShare, 0)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {t.medianDays === null ? "—" : t.medianDays.toFixed(0)}{" "}
                  <span className="text-muted-foreground">({range(t.daysP25, t.daysP75)})</span>
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {t.liftVsBusy === null ? (
                    "—"
                  ) : (
                    <>
                      {t.liftVsBusy.toFixed(1)}x <span className="text-muted-foreground">({liftLabel(t.liftVsBusy)})</span>
                    </>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  {t.mostlyLockedIn ? (
                    <Badge variant="outline" className="font-normal">
                      {(t.lockedShare ?? 0) >= (t.unnamedShare ?? 0) ? "Mostly locked in" : "Contractor often not named"}
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="font-normal">
                      Open
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No $1M+ permits in the last 365 days.</p>
      ) : (
        <>
          <p className="text-sm font-medium">Recent $1M+ permits: what has already followed, and what is still open</p>
          <Card className="overflow-x-auto py-0">
            <table className="w-full min-w-[64rem] text-sm">
              <thead className="border-b text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Address</th>
                  <th className="px-4 py-2.5 font-medium">Permit date</th>
                  <th className="px-4 py-2.5 text-right font-medium">Cost</th>
                  <th className="px-4 py-2.5 font-medium">Work</th>
                  <th className="px-4 py-2.5 font-medium">Contractors on the permit</th>
                  <th className="px-4 py-2.5 font-medium">Already appeared</th>
                </tr>
              </thead>
              <tbody className="divide-y align-top">
                {rows.map((b) => (
                  <tr key={b.id}>
                    <td className="px-4 py-2.5">
                      <div className="font-medium">{b.address}</div>
                      <div className="text-xs text-muted-foreground">
                        {b.communityArea ? (names.get(b.communityArea) ?? "Chicago") : "Chicago"} · {classLabel(b.class)}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      <a
                        href={b.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="underline-offset-2 hover:underline"
                      >
                        {dateLabel(b.permitDate)}
                      </a>
                      <div className="text-xs text-muted-foreground">{b.permitType}</div>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{money(b.reportedCost)}</td>
                    <td className="max-w-xs px-4 py-2.5 text-xs text-muted-foreground">{b.description || "—"}</td>
                    <td className="max-w-56 px-4 py-2.5 text-xs">
                      {contractorList(b.contractors, 3) || <span className="text-muted-foreground">Not named</span>}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {b.appeared.length === 0 ? (
                        <span className="text-muted-foreground">Nothing yet</span>
                      ) : (
                        b.appeared.map((t) => labels.get(t) ?? t).join(", ")
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <p className="text-xs text-muted-foreground">
            {recentTotal > rows.length
              ? `Showing the newest ${count(rows.length)} of ${count(recentTotal)} permits from the last 365 days, newest first${recent.length < recentTotal ? ` (the data keeps the newest ${count(recent.length)})` : ""}.`
              : `${count(recentTotal)} permits from the last 365 days, newest first.`}{" "}
            Single-family addresses are left out; &quot;Class not on record&quot; means the address has no sale or
            assessor record since 2010. &quot;Already appeared&quot; lists trades with a later permit at the address (sign,
            elevator and demolition permits by type; the others by permit text). Source: City of Chicago building
            permits.
          </p>
        </>
      )}
    </section>
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
