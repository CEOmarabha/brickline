import Link from "next/link";
import { Card } from "@/components/ui/card";
import { count, dateLabel, liftLabel, pct } from "@/lib/format";
import type { ClosedRestaurantLead, Snapshot } from "@/lib/snapshot";

const CLOSED_ROWS = 60;

/** Citywide pilot list (not filtered by workspace): restaurant spaces recorded closed in the last 180 days. */
export function ClosedRestaurants({ snap, names }: { snap: Snapshot; names: Map<number, string> }) {
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
