import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { EmptyState, PageHeader } from "@/components/bits";
import { ReplyForm } from "@/components/reply-form";
import { Skeleton } from "@/components/ui/skeleton";
import { count, dateLabel } from "@/lib/format";
import { chicagoDate, getReplies, REPLY_CHANNEL_LABEL } from "@/lib/replies";
import { getSnapshot } from "@/lib/snapshot";
import { getWorkspace } from "@/lib/workspace";

export const metadata: Metadata = { title: "Owner replies" };

export default function RepliesPage() {
  return (
    <>
      <PageHeader
        title="Owner replies"
        description="Every letter and email draft carries a reference code. When an owner calls, writes or emails and quotes it, record the reply here: it links to the lead and counts toward the reply rate. This is how owners with no public phone or email become reachable."
      />
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <Replies />
      </Suspense>
    </>
  );
}

async function Replies() {
  await connection();
  const [ws, snap, replies] = await Promise.all([getWorkspace(), getSnapshot(), getReplies()]);
  if (!ws.signedIn) {
    return <EmptyState title="Sign in to record replies" />;
  }
  const today = chicagoDate();
  const byId = new Map(snap.leads.map((l) => [l.id, l]));
  const matched = replies.filter((r) => r.leadId).length;
  return (
    <div className="space-y-6">
      <ReplyForm today={today} />
      <div>
        <div className="mb-2 text-sm text-muted-foreground">
          {count(replies.length)} replies recorded · {count(matched)} matched to a current lead
        </div>
        {replies.length === 0 ? (
          <EmptyState title="No replies yet">Replies you record appear here, newest first.</EmptyState>
        ) : (
          <ul className="divide-y rounded-lg border bg-card text-sm">
            {replies.map((r) => {
              const lead = byId.get(r.leadId);
              return (
                <li key={r.id} className="grid gap-1 p-4 sm:grid-cols-[8rem_1fr_14rem]">
                  <div>
                    <div className="font-mono">{r.code}</div>
                    <div className="text-xs text-muted-foreground">
                      {REPLY_CHANNEL_LABEL[r.channel]} · {dateLabel(r.receivedOn)}
                    </div>
                  </div>
                  <div className="min-w-0">
                    {lead ? (
                      <Link href={`/leads/${encodeURIComponent(lead.id)}`} className="font-medium hover:underline">
                        {lead.address}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">No current lead has this code</span>
                    )}
                    {r.message && <p className="mt-1 whitespace-pre-line text-muted-foreground">{r.message}</p>}
                  </div>
                  <div className="text-xs break-all text-muted-foreground">
                    {r.contactPhone && <div>{r.contactPhone}</div>}
                    {r.contactEmail && <div>{r.contactEmail}</div>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
