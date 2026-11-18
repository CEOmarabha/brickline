import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, StatCard } from "@/components/bits";
import { DealsCard } from "@/components/dashboard/deals-card";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { daysUntilLabel } from "@/lib/deals";
import { dayRange, eventTitle, getEvents } from "@/lib/events";
import { count, dateLabel } from "@/lib/format";
import { todayChicago } from "@/lib/pipeline";
import { summarizeEvents } from "@/lib/target-summary";

/** Dashboard body when the workspace is looking for event planning and rentals. */
export async function EventsDashboard() {
  const file = await getEvents();
  if (!file) {
    return (
      <EmptyState title="The events list has not been generated yet">
        Run <code>uv run python -m engine.leads.events</code> from the repository root, then reload.
      </EmptyState>
    );
  }
  const today = todayChicago();
  const s = summarizeEvents(file, today);
  const noContact = file.upcoming.filter((e) => e.endDate >= today && !e.organizer).length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard label="Organization events, next 30 days" value={count(s.organizations.next30)} hint="Events that name an organization" />
        <StatCard label="Organization events, next 60 days" value={count(s.organizations.next60)} hint="Events that name an organization" />
        <StatCard label="Organization events, next 120 days" value={count(s.organizations.next120)} hint="All on file that name one" />
        <StatCard label="Recurring series, next 90 days" value={count(s.recurringNext90)} hint="Expected again, from earlier seasons" />
        <StatCard label="Block parties, next 60 days" value={count(s.blockPartiesNext60)} hint="Resident-filed: flyers only" />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Next 5 events with an organization</h2>
            <Link href="/leads" className="text-sm text-primary hover:underline">
              See all {count(s.organizations.next120)}
            </Link>
          </div>
          {s.nextEvents.length === 0 ? (
            <EmptyState title="No upcoming events name an organization" />
          ) : (
            <ul className="divide-y rounded-lg border bg-card">
              {s.nextEvents.map((e) => (
                <li key={e.id}>
                  <Link href="/leads" className="block p-4 transition-colors hover:bg-muted/50">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="font-medium">{eventTitle(e)}</span>
                      <span className="text-sm text-muted-foreground tabular-nums">
                        {dayRange(e.startDate, e.endDate)} · {daysUntilLabel(e.startDate, today)}
                      </span>
                    </div>
                    <div className="mt-0.5 text-sm text-muted-foreground">
                      {e.organizer} · {e.type}
                      {e.location ? ` · ${e.location}` : ""}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Counted from today, {dateLabel(today)}, from the permit list built {dateLabel(file.asOf)}.{" "}
            {count(noContact)} more events in the window name no organization and are left out here.
          </p>
        </section>

        <section className="space-y-3 lg:col-span-2">
          <Suspense fallback={<Skeleton className="h-80 w-full" />}>
            <DealsCard />
          </Suspense>
          <Card size="sm">
            <CardHeader>
              <CardTitle>Where to work</CardTitle>
              <CardDescription>The full lists and your pipeline.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Link href="/leads" className={buttonVariants({ size: "sm" })}>
                Event leads
              </Link>
              <Link href="/deals" className={buttonVariants({ variant: "outline", size: "sm" })}>
                Deals
              </Link>
              <Link href="/pilots#events" className={buttonVariants({ variant: "outline", size: "sm" })}>
                Who buys this
              </Link>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
