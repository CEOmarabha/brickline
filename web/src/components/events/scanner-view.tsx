import Link from "next/link";
import { EmptyState, StatCard } from "@/components/bits";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ReviewStatusSelect } from "@/components/events/review-status";
import { count, dateLabel } from "@/lib/format";
import {
  type EventLead,
  type EventLeadNote,
  type EventLeadsFile,
  leadTitle,
  leadWhen,
} from "@/lib/event-lead-types";

function sourceLabel(source: string): string {
  return source.replaceAll("_", " ");
}

function NoteList({ notes }: { notes: EventLeadNote[] }) {
  const interesting = notes.filter((n) => n.status && n.status !== "ok");
  if (interesting.length === 0) return null;
  return (
    <ul className="space-y-1 text-sm text-muted-foreground">
      {interesting.map((n) => (
        <li key={`${n.source}-${n.status}-${n.detail ?? n.note ?? ""}`}>
          <span className="font-medium text-foreground">{n.source}</span>: {n.status}
          {n.detail || n.note || n.records_path ? ` — ${n.detail || n.note || n.records_path}` : ""}
        </li>
      ))}
    </ul>
  );
}

function LeadRow({ row, signedIn }: { row: EventLead; signedIn: boolean }) {
  const when = leadWhen(row);
  const needs = (row.vendor_needs ?? []).join(", ");
  return (
    <li className="grid gap-3 border-b py-4 last:border-0 md:grid-cols-[1fr_12rem]">
      <div className="min-w-0 space-y-1">
        <div className="font-medium">
          {row.source_url ? (
            <a href={row.source_url} className="underline-offset-2 hover:underline" target="_blank" rel="noreferrer">
              {leadTitle(row)}
            </a>
          ) : (
            leadTitle(row)
          )}
        </div>
        <div className="text-sm text-muted-foreground">
          {sourceLabel(row.source)}
          {when ? ` · ${dateLabel(when)}` : ""}
          {row.venue ? ` · ${row.venue}` : ""}
          {row.city ? ` · ${row.city}` : ""}
          {row.region ? ` · ${row.region}` : ""}
        </div>
        {row.host_org && <div className="text-sm">Host: {row.host_org}</div>}
        {needs && <div className="text-sm">Vendor needs: {needs}</div>}
        {row.evidence_quote && <p className="text-sm italic text-muted-foreground">“{row.evidence_quote}”</p>}
      </div>
      <div className="space-y-2">
        <div className="text-sm tabular-nums text-muted-foreground">Score {row.score.toFixed(0)}</div>
        <ReviewStatusSelect itemHash={row.item_hash} value={row.review_status} signedIn={signedIn} />
      </div>
    </li>
  );
}

/** Daily scanner results: public calendars plus configured social sources, with review status. */
export function ScannerView({ file, signedIn }: { file: EventLeadsFile; signedIn: boolean }) {
  const c = file.counts;
  if (!file.asOf && file.items.length === 0) {
    return (
      <EmptyState title="The daily event-lead scanner has not run yet">
        Run <code>python -m engine.leads.event_scan --public-only --no-llm</code> from the repository root, then reload.
        Setup for logged-in Facebook, Instagram and TikTok sessions is in{" "}
        <Link href="/events/digest" className="underline underline-offset-2">
          today&rsquo;s digest
        </Link>{" "}
        and <code>docs/21-event-lead-scanner.md</code>.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Stored leads" value={count(c.total)} />
        <StatCard label="New this run" value={count(c.new)} />
        <StatCard label="Changed" value={count(c.changed)} />
      </div>
      <p className="text-sm text-muted-foreground">
        As of {file.asOf ? dateLabel(file.asOf) : "—"}, America/Chicago.{" "}
        <Link href="/events/digest" className="underline underline-offset-2">
          Open the 7 AM digest
        </Link>
        .
      </p>
      <NoteList notes={file.notes} />
      {Object.keys(c.bySource).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>By source</CardTitle>
            <CardDescription>Counts in the stored snapshot, including earlier days still on file.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-1 text-sm sm:grid-cols-2">
              {Object.entries(c.bySource).map(([source, n]) => (
                <li key={source} className="flex justify-between gap-4">
                  <span>{sourceLabel(source)}</span>
                  <span className="tabular-nums text-muted-foreground">{count(n)}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
      <ul>
        {file.items
          .slice()
          .sort((a, b) => b.score - a.score || (leadWhen(a) ?? "").localeCompare(leadWhen(b) ?? ""))
          .slice(0, 200)
          .map((row) => (
            <LeadRow key={row.item_hash} row={row} signedIn={signedIn} />
          ))}
      </ul>
    </div>
  );
}
