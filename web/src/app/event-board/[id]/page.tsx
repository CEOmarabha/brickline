import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { CopyButton } from "@/components/copy-button";
import { DealStatusBadge } from "@/components/deal-bits";
import { EventHostPanels } from "@/components/event-board-bits";
import { PossibleJobsCard } from "@/components/possible-jobs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getDeals } from "@/lib/deal-store";
import { daysBetween, getEventBoard } from "@/lib/event-board";
import { dateLabel, pct } from "@/lib/format";
import { getLifecycles } from "@/lib/lifecycles";
import { eventJobs, findBoardEvent } from "@/lib/possible-jobs";
import { viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Event" };

export default function EventPage({ params }: PageProps<"/event-board/[id]">) {
  return (
    <>
      <Link href="/event-board" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Event board
      </Link>
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <EventDetail params={params} />
      </Suspense>
    </>
  );
}

async function EventDetail({ params }: { params: PageProps<"/event-board/[id]">["params"] }) {
  const { id: rawId } = await params;
  let id: string;
  try {
    id = decodeURIComponent(rawId);
  } catch {
    notFound();
  }
  const [board, lifecycles, owner] = await Promise.all([getEventBoard(), getLifecycles(), viewerId()]);
  const e = findBoardEvent(board, id);
  if (!e) notFound();
  const deals = owner ? (await getDeals(owner)).filter((d) => d.sourceRef === e.id) : [];
  const jobs = eventJobs(e, board, lifecycles);
  const until = daysBetween(board.asOf, e.start);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex flex-wrap gap-1.5">
            <Badge>{e.category}</Badge>
            {e.chance != null && <Badge variant="outline">{pct(e.chance, 0)} chance it happens again</Badge>}
          </div>
          <h1 className="text-2xl font-semibold tracking-tight capitalize">{e.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {[e.place, e.area?.name, e.ward ? `Ward ${e.ward}` : null].filter(Boolean).join(" · ") || "Place not published"}
          </p>
        </div>
        <div className="text-right text-sm">
          <div className="font-medium">
            {dateLabel(e.start)}
            {e.end && e.end !== e.start ? ` – ${dateLabel(e.end)}` : ""}
          </div>
          <div className="text-xs text-muted-foreground">{until >= 0 ? `in ${until} days` : `${-until} days ago`}</div>
        </div>
      </header>

      {jobs && (
        <PossibleJobsCard
          plan={jobs}
          description={`${jobs.lifecycleName}: the jobs this event needs, dated back from the event day, with the Chicago companies that sell each one.`}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Who to contact</CardTitle>
          <CardDescription>
            {e.host.needsSkipTrace
              ? "The host is a private person: write first, and call or text only a skip-traced number that passed a Do Not Call scrub, dialed by hand."
              : "Public contact details from the permit, the City's ward offices or a matched business listing."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EventHostPanels e={e} board={board} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Track it as a deal</CardTitle>
          <CardDescription>
            Quick add on <Link href="/deals" className="underline">Deals</Link> with this event&apos;s id as the link; the deal
            page then shows these jobs next to your partners and quote.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground">Event id</span>
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{e.id}</code>
            <CopyButton text={e.id} label="Copy id" />
          </div>
          {deals.length > 0 && (
            <ul className="space-y-1.5">
              {deals.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-2">
                  <Link href={`/deals/${encodeURIComponent(d.id)}`} className="text-primary hover:underline">
                    {d.title || "Untitled deal"}
                  </Link>
                  <DealStatusBadge status={d.status} />
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-muted-foreground">
            Status: {e.status ?? "—"} · Source: {e.source} · Records through {dateLabel(board.asOf)}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
