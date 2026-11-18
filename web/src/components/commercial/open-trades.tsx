import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { count, liftLabel, money, pct } from "@/lib/format";
import type { Snapshot } from "@/lib/snapshot";
import { classLabel, contractorList, range, SourceDate } from "./shared";

const BIG_PERMIT_ROWS = 60;

/** Citywide block: which trades are still open after a $1M+ permit, and the recent big permits. */
export function OpenTrades({ snap, names }: { snap: Snapshot; names: Map<number, string> }) {
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
                      <SourceDate url={b.sourceUrl} date={b.permitDate} />
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
