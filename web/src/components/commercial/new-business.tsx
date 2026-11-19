import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { count, liftLabel, money, pct } from "@/lib/format";
import type { Snapshot } from "@/lib/snapshot";
import { classLabel, contractorList, SourceDate } from "./shared";

const NEW_BUSINESS_ROWS = 60;

/** Citywide pilot list (not filtered by workspace): build-out permits at addresses with no business license. */
export function NewBusiness({ snap, names }: { snap: Snapshot; names: Map<number, string> }) {
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
                      <SourceDate url={s.sourceUrl} date={s.permitDate} />
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
