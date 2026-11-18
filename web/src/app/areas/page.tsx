import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader, Trend } from "@/components/bits";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TradeOnlyNote } from "@/components/trade-only-note";
import { count, dateLabel, money, pct } from "@/lib/format";
import { areaNames, areaSignal, getSnapshot, leadsForWorkspace, type Snapshot } from "@/lib/snapshot";
import { isTradeTarget } from "@/lib/targets";
import { getStatuses, getWorkspace, isOpenLead } from "@/lib/workspace";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Neighborhoods" };

const SORTS = {
  leads: "Open leads",
  signals: "Your trade's signals",
  growth: "Growth vs last year",
  investors: "Investor purchases",
  projects: "Major projects",
} as const;
type SortKey = keyof typeof SORTS;

export default function AreasPage({ searchParams }: PageProps<"/areas">) {
  return (
    <>
      <PageHeader
        title="Neighborhoods"
        description="Where demand for your trade is building. Last 90 days compared with the same 90 days a year earlier; investor purchases over the last 180 days of sales data."
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Areas searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Areas({ searchParams }: { searchParams: PageProps<"/areas">["searchParams"] }) {
  const sp = await searchParams;
  const sort = (Object.keys(SORTS).includes(String(sp.sort)) ? sp.sort : "leads") as SortKey;
  const mineOnly = sp.scope === "mine";
  const [snap, ws, statuses] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses()]);
  if (!isTradeTarget(ws.target)) return <TradeOnlyNote target={ws.target} snap={snap} />;
  const trade = ws.trade;
  const open = leadsForWorkspace(snap, trade, []).filter((l) => isOpenLead(statuses, l.id));
  const signalLabel = trade === "general" ? "Major projects" : "Violations";

  const rows = snap.areas
    .filter((a) => !mineOnly || ws.areas.length === 0 || ws.areas.includes(a.id))
    .map((a) => ({
      a,
      sig: areaSignal(a, trade),
      permits: a.permits[trade],
      leads: open.filter((l) => l.communityArea === a.id).length,
      mine: ws.areas.length === 0 || ws.areas.includes(a.id),
    }));
  const key: Record<SortKey, (r: (typeof rows)[number]) => number> = {
    leads: (r) => r.leads,
    signals: (r) => r.sig.now,
    growth: (r) => r.sig.now - r.sig.before,
    investors: (r) => r.a.investorPurchases.last180,
    projects: (r) => r.a.majorProjects.last90,
  };
  rows.sort((x, y) => key[sort](y) - key[sort](x) || x.a.name.localeCompare(y.a.name));

  const link = (patch: Record<string, string | undefined>) => {
    const params = new URLSearchParams();
    const next = { sort, scope: mineOnly ? "mine" : undefined, ...patch };
    for (const [k, v] of Object.entries(next)) if (v && !(k === "sort" && v === "leads")) params.set(k, v);
    return `/areas?${params.toString()}`;
  };

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Sort by</span>
        {(Object.keys(SORTS) as SortKey[]).map((k) => (
          <Link
            key={k}
            href={link({ sort: k })}
            className={cn(
              "rounded-full border px-3 py-1 transition-colors hover:bg-muted",
              sort === k && "border-primary bg-primary/10 text-primary",
            )}
          >
            {SORTS[k]}
          </Link>
        ))}
        {ws.areas.length > 0 && (
          <Link href={link({ scope: mineOnly ? undefined : "mine" })} className="ml-auto text-primary hover:underline">
            {mineOnly ? "Show all 77 areas" : "Only my neighborhoods"}
          </Link>
        )}
      </div>
      <Card className="overflow-x-auto py-0">
        <table className="w-full min-w-[46rem] text-sm">
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Neighborhood</th>
              <th className="px-4 py-2.5 font-medium">{signalLabel}, 90 days</th>
              <th className="px-4 py-2.5 font-medium">{snap.trades[trade].label} permits, 90 days</th>
              <th className="px-4 py-2.5 font-medium">Investor purchases, 180 days</th>
              <th className="px-4 py-2.5 font-medium">Major projects, 90 days</th>
              <th className="px-4 py-2.5 text-right font-medium">Open leads</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map(({ a, sig, permits, leads, mine }) => (
              <tr key={a.id} className={cn(!mine && "text-muted-foreground")}>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">{a.name}</span>
                    {mine && ws.areas.length > 0 && (
                      <Badge variant="outline" className="border-primary/20 bg-primary/5 text-primary">
                        Yours
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {count(sig.now)} <Trend now={sig.now} before={sig.before} />
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {count(permits.last90)} <Trend now={permits.last90} before={permits.lastYear} />
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {count(a.investorPurchases.last180)}
                  {a.medianInvestorPrice ? (
                    <span className="ml-1 text-xs text-muted-foreground">median {money(a.medianInvestorPrice)}</span>
                  ) : null}
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {count(a.majorProjects.last90)}
                  {a.majorProjects.value90 > 0 && (
                    <span className="ml-1 text-xs text-muted-foreground">{money(a.majorProjects.value90)}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {leads > 0 && mine ? (
                    <Link href={`/leads?area=${a.id}`} className="font-medium text-primary hover:underline">
                      {count(leads)}
                    </Link>
                  ) : (
                    count(leads)
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <BlockTargeting snap={snap} roofing={trade === "roofing"} />
    </>
  );
}

function BlockTargeting({ snap, roofing }: { snap: Snapshot; roofing: boolean }) {
  const { roofing: blocks, roofingModel: m } = snap.blocks;
  const names = areaNames(snap);
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold tracking-tight">Block targeting</h2>
      {!roofing ? (
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Block lists are available for roofing workspaces: street blocks where several neighbors just re-roofed. Change
          the trade in Settings to see them.
        </p>
      ) : (
        <>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Blocks (about 160 m squares) with 2 or more re-roof permits in the last 90 days. Historically, homes on such
            blocks pulled a roofing permit within {m.horizonDays} days {pct(m.exposedRate, 2)} of the time, versus{" "}
            {pct(m.baseRate, 2)} on blocks with none: {m.lift.toFixed(1)}× the rate ({m.period}, {count(m.exposedCases)}{" "}
            home-quarters on exposed blocks). Good for door hangers and mail to the whole block.
          </p>
          <Card className="mt-4 overflow-x-auto py-0">
            <table className="w-full min-w-[40rem] text-sm">
              <thead className="border-b text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Neighborhood</th>
                  <th className="px-4 py-2.5 text-right font-medium">Re-roofs, 90 days</th>
                  <th className="px-4 py-2.5 text-right font-medium">Homes on block</th>
                  <th className="px-4 py-2.5 font-medium">Latest permit</th>
                  <th className="px-4 py-2.5 font-medium">Permitted addresses</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {blocks.map((b) => (
                  <tr key={b.id} className="align-top">
                    <td className="px-4 py-2.5 font-medium">
                      {b.communityArea ? (names.get(b.communityArea) ?? "Chicago") : "Chicago"}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{count(b.recentReroofs)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{count(b.residentialParcels)}</td>
                    <td className="px-4 py-2.5 whitespace-nowrap">{dateLabel(b.lastPermit)}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{b.addresses.join(" · ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </section>
  );
}
