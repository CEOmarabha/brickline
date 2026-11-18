import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, StatCard } from "@/components/bits";
import { DealsCard } from "@/components/dashboard/deals-card";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPest } from "@/lib/pest";
import { getSnapshot } from "@/lib/snapshot";
import { getTarget, type TargetKey } from "@/lib/targets";
import { summarizeCommercial } from "@/lib/target-summary";

/** Dashboard body for the commercial targets: counts and top rows from the target's list, plus the deals due. */
export async function CommercialDashboard({ target }: { target: TargetKey }) {
  const [snap, pest] = await Promise.all([getSnapshot(), target === "pest_control" ? getPest() : Promise.resolve(null)]);
  const summary = summarizeCommercial(target, snap, pest);
  const pilotAnchor = getTarget(target).pilotAnchor;
  if (!summary) return <EmptyState title="Nothing to show for this target yet" />;

  return (
    <div className="space-y-6">
      {summary.stats.length > 0 && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {summary.stats.map((s) => (
            <StatCard key={s.label} label={s.label} value={s.value} hint={s.hint} />
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">{summary.rowsTitle}</h2>
            <Link href="/leads" className="text-sm text-primary hover:underline">
              See the list
            </Link>
          </div>
          {summary.rows.length === 0 ? (
            <EmptyState title="Nothing on this list right now" />
          ) : (
            <ul className="divide-y rounded-lg border bg-card">
              {summary.rows.map((r) => {
                const body = (
                  <>
                    <div className="font-medium">{r.title}</div>
                    <div className="mt-0.5 text-sm text-muted-foreground">{r.subtitle}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{r.meta}</div>
                  </>
                );
                return (
                  <li key={r.id}>
                    <Link href={r.href ?? "/leads"} className="block p-4 transition-colors hover:bg-muted/50">
                      {body}
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="mt-2 text-xs text-muted-foreground">{summary.note}</p>
        </section>

        <section className="space-y-3 lg:col-span-2">
          <Suspense fallback={<Skeleton className="h-80 w-full" />}>
            <DealsCard />
          </Suspense>
          <Card size="sm">
            <CardHeader>
              <CardTitle>Where to work</CardTitle>
              <CardDescription>The full list and who might buy it.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Link href="/leads" className={buttonVariants({ size: "sm" })}>
                Open leads
              </Link>
              <Link href={summary.listHref} className={buttonVariants({ variant: "outline", size: "sm" })}>
                {summary.listLabel}
              </Link>
              {pilotAnchor && (
                <Link href={`/pilots#${pilotAnchor}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  Who buys this
                </Link>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
