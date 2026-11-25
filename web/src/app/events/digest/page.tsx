import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, StatCard } from "@/components/bits";
import { ReviewStatusSelect } from "@/components/events/review-status";
import { Skeleton } from "@/components/ui/skeleton";
import { leadTitle, leadWhen } from "@/lib/event-lead-types";
import { getEventDigest } from "@/lib/event-leads";
import { count, dateLabel } from "@/lib/format";
import { viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Event leads digest" };

export default function EventDigestPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
      <EventDigestBody />
    </Suspense>
  );
}

async function EventDigestBody() {
  const [file, owner] = await Promise.all([getEventDigest(), viewerId()]);
  const signedIn = Boolean(owner);

  return (
    <div className="space-y-8">
      <PageHeader
        title={file.title || "Event leads digest"}
        description={
          <>
            Top new and still-unreviewed event leads for 7:00 America/Chicago. Source links stay on the original
            calendar or post. Outreach stays one message at a time from a real account — this page does not send.
          </>
        }
        actions={
          <Link href="/events?tab=scanner" className="text-sm underline underline-offset-2">
            All scanner leads
          </Link>
        }
      />
      {!file.asOf && file.top.length === 0 ? (
        <EmptyState title="No digest yet">
          The daily job writes this file at 7 AM Chicago. Run{" "}
          <code>python -m engine.leads.event_scan --public-only --no-llm</code> to generate one now.
        </EmptyState>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label="On file" value={count(file.counts.total)} />
            <StatCard label="New" value={count(file.counts.new)} />
            <StatCard label="In this digest" value={count(file.top.length)} />
          </div>
          <p className="text-sm text-muted-foreground">
            {file.asOf ? dateLabel(file.asOf) : "—"} · {file.timezone}
          </p>
          <ol className="space-y-4">
            {file.top.map((row, i) => {
              const when = leadWhen(row);
              return (
                <li key={row.item_hash} className="grid gap-3 border-b pb-4 md:grid-cols-[1fr_12rem]">
                  <div className="min-w-0 space-y-1">
                    <div className="text-xs tabular-nums text-muted-foreground">{i + 1}</div>
                    <div className="font-medium">
                      {row.source_url ? (
                        <a
                          href={row.source_url}
                          className="underline-offset-2 hover:underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          {leadTitle(row)}
                        </a>
                      ) : (
                        leadTitle(row)
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {row.source.replaceAll("_", " ")}
                      {when ? ` · ${dateLabel(when)}` : ""}
                      {row.venue ? ` · ${row.venue}` : ""}
                      {row.region ? ` · ${row.region}` : ""}
                    </div>
                    {row.evidence_quote && (
                      <p className="text-sm italic text-muted-foreground">“{row.evidence_quote}”</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm tabular-nums text-muted-foreground">Score {row.score.toFixed(0)}</div>
                    <ReviewStatusSelect itemHash={row.item_hash} value={row.review_status} signedIn={signedIn} />
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </div>
  );
}
