import { Globe, Mail, MapPin, Phone } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/bits";
import { Badge } from "@/components/ui/badge";
import { count, dateLabel, pct } from "@/lib/format";
import { displayUrl, isHttpUrl } from "@/lib/links";
import {
  type BlockParty,
  dayRange,
  type EventContact,
  eventTitle,
  inNoticeWindow,
  monthDay,
  type RecurringSeries,
  type UpcomingEvent,
  weeksLabel,
} from "@/lib/events";
import { boardEventHref } from "@/lib/possible-jobs";

function searchUrl(name: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(`${name} Chicago`)}`;
}

function Contact({ contact, organizer }: { contact: EventContact | null; organizer: string | null }) {
  if (!contact) {
    return organizer ? (
      <div className="space-y-0.5">
        <span className="text-muted-foreground">No public listing matched</span>
        <div>
          <a href={searchUrl(organizer)} target="_blank" rel="noopener noreferrer" className="text-xs underline">
            Search the web
          </a>
        </div>
      </div>
    ) : (
      <span className="text-muted-foreground">—</span>
    );
  }
  const none = !contact.phone && !contact.website && !contact.email;
  return (
    <div className="space-y-0.5">
      {contact.phone && (
        <div className="flex items-center gap-1 whitespace-nowrap">
          <Phone className="size-3 text-muted-foreground" aria-hidden /> {contact.phone}
        </div>
      )}
      {contact.website && isHttpUrl(contact.website) && (
        <div className="flex items-center gap-1">
          <Globe className="size-3 shrink-0 text-muted-foreground" aria-hidden />
          <a href={contact.website} target="_blank" rel="noopener noreferrer" className="max-w-44 truncate underline">
            {displayUrl(contact.website)}
          </a>
        </div>
      )}
      {contact.email && (
        <div className="flex items-center gap-1">
          <Mail className="size-3 shrink-0 text-muted-foreground" aria-hidden /> {contact.email}
        </div>
      )}
      {contact.address && (
        <div className="flex items-start gap-1 text-xs text-muted-foreground">
          <MapPin className="mt-0.5 size-3 shrink-0" aria-hidden /> {contact.address}
        </div>
      )}
      {none && !contact.address && <span className="text-muted-foreground">Listed, no contact details</span>}
      <div className="text-[11px] text-muted-foreground">
        {contact.source}, {contact.match === "exact" ? "same name" : "similar name"}
        {contact.name ? ` (${contact.name})` : ""}
      </div>
    </div>
  );
}

function Organizer({ e }: { e: UpcomingEvent | RecurringSeries }) {
  if (e.organizer) {
    return (
      <div>
        <span className="font-medium">{e.organizer}</span>
        {e.kind && <div className="text-xs text-muted-foreground">{e.kind}</div>}
      </div>
    );
  }
  const why: Record<string, string> = {
    individual: "Filed by an individual (not shown)",
    withheld: "Name withheld (could be an individual)",
    unpublished: "The Park District feed names no organizer",
    organization: "",
  };
  return <span className="text-xs text-muted-foreground">{why[e.organizerStatus]}</span>;
}

function Place({ e }: { e: UpcomingEvent | RecurringSeries }) {
  const closure = "closure" in e ? e.closure : null;
  return (
    <div>
      {e.location ?? "—"}
      <div className="text-xs text-muted-foreground">
        {e.segments > 1 ? `+${e.segments - 1} more ${e.source.includes("Park") ? "facilit" : "segment"}${e.segments === 2 ? (e.source.includes("Park") ? "y" : "") : e.source.includes("Park") ? "ies" : "s"}` : ""}
        {e.segments > 1 && closure ? ", " : ""}
        {closure ?? ""}
      </div>
    </div>
  );
}

function Area({ e }: { e: UpcomingEvent | RecurringSeries }) {
  return (
    <td className="px-3 py-2.5 text-muted-foreground">
      {e.communityArea?.name ?? "—"}
      {e.ward ? <div className="text-xs">Ward {e.ward}</div> : null}
    </td>
  );
}

export function UpcomingTable({ rows, boardIds }: { rows: UpcomingEvent[]; boardIds: ReadonlySet<string> }) {
  if (rows.length === 0) return <EmptyState title="No events in this view" />;
  return (
    <div className="max-h-[44rem] overflow-auto rounded-lg border">
      <table className="w-full min-w-[74rem] text-sm">
        <thead className="sticky top-0 z-10 border-b bg-background text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Date</th>
            <th className="px-3 py-2 font-medium">Event</th>
            <th className="px-3 py-2 font-medium">Organizer</th>
            <th className="px-3 py-2 font-medium">Location</th>
            <th className="px-3 py-2 font-medium">Neighborhood</th>
            <th className="px-3 py-2 font-medium">Days until</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Contact suggestion</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((e) => {
            const href = boardEventHref(e.id, boardIds);
            return (
              <tr key={e.id} className="align-top">
                <td className="px-3 py-2.5 whitespace-nowrap">{dayRange(e.startDate, e.endDate)}</td>
                <td className="px-3 py-2.5">
                  <div className="font-medium capitalize">
                    {href ? (
                      <Link href={href} className="hover:underline">
                        {eventTitle(e)}
                      </Link>
                    ) : (
                      eventTitle(e)
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {e.type}
                    {e.tier ? `, ${e.tier}` : ""}
                  </div>
                  {href && (
                    <Link href={href} className="text-xs text-primary hover:underline">
                      Possible jobs
                    </Link>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <Organizer e={e} />
                </td>
                <td className="px-3 py-2.5">
                  <Place e={e} />
                </td>
                <Area e={e} />
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <span className="tabular-nums">{e.daysUntil}</span>{" "}
                  <span className="text-xs text-muted-foreground">({weeksLabel(e.daysUntil)})</span>
                  {inNoticeWindow(e.daysUntil) && (
                    <div>
                      <Badge variant="secondary">2 to 8 weeks out</Badge>
                    </div>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  {e.status}
                  <div className="text-xs text-muted-foreground">
                    {e.firstSeen ? `${e.source.includes("Park") ? "Listed" : "Review began"} ${dateLabel(e.firstSeen)}` : "Not yet in review"}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <Contact contact={e.contact} organizer={e.organizer} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function RecurringTable({ rows }: { rows: RecurringSeries[] }) {
  if (rows.length === 0) return <EmptyState title="No recurring series in this view" />;
  return (
    <div className="max-h-[44rem] overflow-auto rounded-lg border">
      <table className="w-full min-w-[80rem] text-sm">
        <thead className="sticky top-0 z-10 border-b bg-background text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Expected next</th>
            <th className="px-3 py-2 font-medium">Event</th>
            <th className="px-3 py-2 font-medium">Organizer</th>
            <th className="px-3 py-2 font-medium">Last place</th>
            <th className="px-3 py-2 font-medium">Neighborhood</th>
            <th className="px-3 py-2 font-medium">History</th>
            <th className="px-3 py-2 font-medium">Past recurrence</th>
            <th className="px-3 py-2 font-medium">Contact suggestion</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((s) => (
            <tr key={s.id} className="align-top">
              <td className="px-3 py-2.5">
                <div className="whitespace-nowrap">{dayRange(s.expectedStart, s.expectedEnd)}</div>
                <div className="text-xs text-muted-foreground">
                  usually starts {monthDay(s.typicalStart)}; in {weeksLabel(s.daysUntilExpected)}
                </div>
                {s.onCalendar && (
                  <div>
                    <Badge variant="secondary">already filed</Badge>
                  </div>
                )}
              </td>
              <td className="px-3 py-2.5">
                <div className="font-medium capitalize">{eventTitle(s)}</div>
                <div className="text-xs text-muted-foreground">{s.type}</div>
              </td>
              <td className="px-3 py-2.5">
                <Organizer e={s} />
              </td>
              <td className="px-3 py-2.5">
                <Place e={s} />
              </td>
              <Area e={s} />
              <td className="px-3 py-2.5">
                <div className="whitespace-nowrap">{s.seasonsRun} of 3 seasons</div>
                <div className="text-xs text-muted-foreground">
                  last {dateLabel(s.lastDate)}
                  {!s.ranLastSeason ? "; not held in the last 12 months" : !s.consecutive ? "; a season was skipped" : ""}
                </div>
              </td>
              <td className="px-3 py-2.5">
                {s.recurrence ? (
                  <>
                    <span className="tabular-nums">{pct(s.recurrence.rate, 0)}</span>
                    <div className="text-xs text-muted-foreground">
                      of {count(s.recurrence.series)} {s.recurrence.scope === "all" ? "" : `${s.recurrence.scope} `}series held {s.recurrence.years} years running came back
                    </div>
                  </>
                ) : (
                  <span className="text-xs text-muted-foreground">Not comparable: a season was skipped</span>
                )}
              </td>
              <td className="px-3 py-2.5">
                <Contact contact={s.contact} organizer={s.organizer} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BlockPartyTable({ rows, boardIds }: { rows: BlockParty[]; boardIds: ReadonlySet<string> }) {
  if (rows.length === 0) return <EmptyState title="No block parties filed for this window yet" />;
  return (
    <div className="max-h-[36rem] overflow-auto rounded-lg border">
      <table className="w-full min-w-[48rem] text-sm">
        <thead className="sticky top-0 z-10 border-b bg-background text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Date</th>
            <th className="px-3 py-2 font-medium">Block</th>
            <th className="px-3 py-2 font-medium">Neighborhood</th>
            <th className="px-3 py-2 font-medium">Ward</th>
            <th className="px-3 py-2 font-medium">Days until</th>
            <th className="px-3 py-2 font-medium">Closure</th>
            <th className="px-3 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((b) => {
            const href = boardEventHref(b.id, boardIds);
            return (
              <tr key={b.id} className="align-top">
                <td className="px-3 py-2 whitespace-nowrap">{dayRange(b.startDate, b.endDate)}</td>
                <td className="px-3 py-2">
                  {href ? (
                    <Link href={href} className="hover:underline">
                      {b.block ?? "—"}
                    </Link>
                  ) : (
                    (b.block ?? "—")
                  )}
                  {b.segments > 1 && (
                    <div className="text-xs text-muted-foreground">
                      +{b.segments - 1} more segment{b.segments === 2 ? "" : "s"}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{b.communityArea?.name ?? "—"}</td>
                <td className="px-3 py-2 text-muted-foreground">{b.ward ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap tabular-nums">
                  {b.daysUntil} <span className="text-xs text-muted-foreground">({weeksLabel(b.daysUntil)})</span>
                </td>
                <td className="px-3 py-2 text-muted-foreground">{b.closure ?? "—"}</td>
                <td className="px-3 py-2">
                  {b.status}
                  {href && (
                    <div>
                      <Link href={href} className="text-xs text-primary hover:underline">
                        Possible jobs
                      </Link>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
