import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader, Pagination } from "@/components/bits";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type BoardEvent,
  type EventBoard,
  daysBetween,
  getEventBoard,
  HOST_TYPE_LABEL,
  type HostType,
  shiftDate,
  skipTraceEstimate,
} from "@/lib/event-board";
import { count, dateLabel, pct } from "@/lib/format";
import { getLifecycles, type Lifecycle, type LifecyclesFile } from "@/lib/lifecycles";
import { isHttpUrl } from "@/lib/links";
import { firstParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Event board" };

const PAGE_SIZE = 15;
const DAY_CHOICES = [30, 60, 120] as const;
const HOST_TYPES: HostType[] = ["person", "organization", "ward_office", "unknown"];

type Params = Record<string, string | string[] | undefined>;

export default function EventBoardPage({ searchParams }: PageProps<"/event-board">) {
  return (
    <>
      <PageHeader
        title="Event board"
        description="Every upcoming event in the public records: what it is, who is hosting it and how to reach them, and the jobs it needs, dated from the event backward, with the Chicago companies that sell each one. Block-party hosts are private people: write first, and call or text only a skip-traced number that passed a Do Not Call scrub."
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Board searchParams={searchParams} />
      </Suspense>
    </>
  );
}

function hrefWith(sp: Params, patch: Record<string, string | null>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    const value = firstParam(v);
    if (value && k !== "page") params.set(k, value);
  }
  for (const [k, v] of Object.entries(patch)) {
    if (v === null) params.delete(k);
    else params.set(k, v);
  }
  const s = params.toString();
  return s ? `/event-board?${s}` : "/event-board";
}

async function Board({ searchParams }: { searchParams: PageProps<"/event-board">["searchParams"] }) {
  const sp = (await searchParams) as Params;
  const [board, lifecycles] = await Promise.all([getEventBoard(), getLifecycles()]);
  const view = firstParam(sp.view) === "likely" ? "likely" : "upcoming";
  const list = view === "likely" ? board.predicted : board.events;
  const categories = [...new Set(list.map((e) => e.category))].sort();
  const type = categories.find((c) => c === firstParam(sp.type)) ?? null;
  const days = DAY_CHOICES.find((d) => String(d) === firstParam(sp.days)) ?? 120;
  const host = HOST_TYPES.find((h) => h === firstParam(sp.host)) ?? null;
  const filtered = list
    .filter((e) => !type || e.category === type)
    .filter((e) => !host || e.host.type === host)
    .filter((e) => view === "likely" || daysBetween(board.asOf, e.start) <= days)
    .sort((a, b) =>
      view === "likely" ? (b.chance ?? 0) - (a.chance ?? 0) || a.start.localeCompare(b.start) : a.start.localeCompare(b.start),
    );
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Math.floor(Number(firstParam(sp.page))) || 1));
  const shown = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const byId = new Map(lifecycles.lifecycles.map((l) => [l.id, l]));
  const people = filtered.filter((e) => e.host.needsSkipTrace).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <Chip href={hrefWith({}, {})} active={view === "upcoming"} label={`Upcoming (${count(board.events.length)})`} />
        <Chip
          href={hrefWith({}, { view: "likely" })}
          active={view === "likely"}
          label={`Likely block parties in ${board.season} (${count(board.predicted.length)})`}
        />
        <span className="ml-auto self-center text-xs text-muted-foreground">Records through {dateLabel(board.asOf)}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-xs text-muted-foreground">Type</span>
        <Chip href={hrefWith(sp, { type: null })} active={!type} label="All" />
        {categories.map((c) => (
          <Chip
            key={c}
            href={hrefWith(sp, { type: c })}
            active={type === c}
            label={`${c} (${list.filter((e) => e.category === c).length})`}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-xs text-muted-foreground">Host</span>
        <Chip href={hrefWith(sp, { host: null })} active={!host} label="Any" />
        {HOST_TYPES.map((h) => (
          <Chip key={h} href={hrefWith(sp, { host: h })} active={host === h} label={HOST_TYPE_LABEL[h]} />
        ))}
        {view === "upcoming" && (
          <>
            <span className="ml-4 text-xs text-muted-foreground">Next</span>
            {DAY_CHOICES.map((d) => (
              <Chip key={d} href={hrefWith(sp, { days: String(d) })} active={days === d} label={`${d} days`} />
            ))}
          </>
        )}
      </div>

      {view === "likely" && (
        <p className="text-sm text-muted-foreground">
          Blocks that held a party in at least two of the last three summers and have not filed yet, with last year&apos;s
          date moved to {board.season}. Backtest on {board.season - 1}: blocks with a party in 3 of 3 summers held one
          again {pct(board.backtest["3"]?.repeatRate, 0)} of the time; 2 of 3, {pct(board.backtest["2"]?.repeatRate, 0)}.
        </p>
      )}

      <SkipTracePanel board={board} people={people} total={filtered.length} />

      <div className="text-sm text-muted-foreground">{count(filtered.length)} events</div>
      {shown.length === 0 ? (
        <EmptyState title="No events match these filters" />
      ) : (
        shown.map((e) => <EventCard key={e.id} e={e} board={board} lifecycle={byId.get(e.lifecycle)} lifecycles={lifecycles} />)
      )}
      <Pagination page={page} pages={pages} href={(n) => hrefWith(sp, { page: n > 1 ? String(n) : null })} />
    </div>
  );
}

function Chip({ href, active, label }: { href: string; active: boolean; label: string }) {
  return (
    <Link
      href={href}
      className={cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary")}
    >
      {label}
    </Link>
  );
}

function SkipTracePanel({ board, people, total }: { board: EventBoard; people: number; total: number }) {
  const info = board.skipTrace;
  const est = skipTraceEstimate(info, people);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Skip trace for the hosts on this list</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat label="Hosts who are private people" value={`${count(people)} of ${count(total)}`} />
          <Stat label="Phone numbers found" value={`${count(est.matchesLow)}–${count(est.matchesHigh)}`} />
          <Stat label="Left after the Do Not Call scrub" value={`${count(est.callableLow)}–${count(est.callableHigh)}`} />
          <Stat label="Cost" value={`$${est.costLow.toFixed(0)}–$${est.costHigh.toFixed(0)}`} />
        </div>
        <p className="text-xs text-muted-foreground">
          Found: {pct(info.hitRateLow, 0)}–{pct(info.hitRateHigh, 0)} of names ({info.hitRateSource}). Cost: ${info.priceLow.toFixed(2)}–$
          {info.priceHigh.toFixed(2)} per match. Do Not Call: we assume {pct(info.dncShareLow, 0)}–{pct(info.dncShareHigh, 0)} of
          personal numbers are registered (an estimate; Illinois has {count(info.dnc.illinoisRegistrations)} registered numbers,{" "}
          {count(info.dnc.illinoisPer100k)} per 100,000 residents,{" "}
          <a href={info.dnc.source} target="_blank" rel="noreferrer" className="underline">
            FTC
          </a>
          ). The scrub gives the real count; a number on the list can still get your letter. Ward offices and organizations
          need no skip trace.
        </p>
        <ul className="grid gap-1 text-xs sm:grid-cols-2">
          {info.providers.map((p) => (
            <li key={p.name}>
              <span className="font-medium">{p.name}</span>: {p.price}{" "}
              <a href={p.source} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                source
              </a>
            </li>
          ))}
        </ul>
        <p className="text-xs text-muted-foreground">
          Prices read {dateLabel(info.read)}. Pick a provider whose terms allow marketing use. Call or text by hand, one at a
          time, 9:00–20:00; say who you are and why, and stop when asked (docs/14 §8).
        </p>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function EventCard({
  e,
  board,
  lifecycle,
  lifecycles,
}: {
  e: BoardEvent;
  board: EventBoard;
  lifecycle: Lifecycle | undefined;
  lifecycles: LifecyclesFile;
}) {
  const until = daysBetween(board.asOf, e.start);
  const ward = e.ward ? board.wards[String(e.ward)] : undefined;
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-1 flex flex-wrap gap-1.5">
              <Badge>{e.category}</Badge>
              {e.chance != null && <Badge variant="outline">{pct(e.chance, 0)} chance it happens again</Badge>}
            </div>
            <CardTitle className="capitalize">{e.name}</CardTitle>
            <div className="mt-1 text-sm text-muted-foreground">
              {[e.place, e.area?.name, e.ward ? `Ward ${e.ward}` : null].filter(Boolean).join(" · ") || "Place not published"}
            </div>
          </div>
          <div className="text-right text-sm">
            <div className="font-medium">
              {dateLabel(e.start)}
              {e.end && e.end !== e.start ? ` – ${dateLabel(e.end)}` : ""}
            </div>
            <div className="text-xs text-muted-foreground">{until >= 0 ? `in ${until} days` : `${-until} days ago`}</div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">Host · {HOST_TYPE_LABEL[e.host.type]}</div>
            <div className="font-medium">{e.host.name ?? "Not published"}</div>
            {e.host.mailing && <div>{e.host.mailing}</div>}
            <ContactLinks phone={e.host.phone} email={e.host.email} website={e.host.website} />
            {e.host.needsSkipTrace && (
              <div className="mt-1 text-xs text-amber-700">
                No public phone: skip trace (about ${board.skipTrace.priceLow.toFixed(2)}–${board.skipTrace.priceHigh.toFixed(2)}), then a Do
                Not Call scrub. Mail or a door hanger works now.
              </div>
            )}
            {e.host.source && <div className="mt-1 text-xs text-muted-foreground">Contact source: {e.host.source}</div>}
          </div>
          {ward && e.host.type !== "ward_office" ? (
            <div className="rounded-md border p-3">
              <div className="text-xs text-muted-foreground">Alderman&apos;s office (approves block parties and street events)</div>
              <div className="font-medium">
                Ward {ward.ward} · {ward.alderman}
              </div>
              <div>{ward.address}</div>
              <ContactLinks phone={ward.phone} email={ward.email} website={ward.website} />
            </div>
          ) : (
            <div className="rounded-md border p-3 text-xs text-muted-foreground">
              Status: {e.status ?? "—"}
              <br />
              Source: {e.source}
            </div>
          )}
        </div>

        {lifecycle && (
          <div>
            <div className="mb-2 font-medium">Jobs this event needs, by date</div>
            <div className="grid gap-3 lg:grid-cols-2">
              {lifecycle.stages.map((st) => {
                const from = st.offsetDays ? shiftDate(e.start, st.offsetDays[0]) : null;
                const to = st.offsetDays ? shiftDate(e.start, st.offsetDays[1]) : null;
                const passed = to !== null && to < board.asOf;
                return (
                  <div key={st.name} className={cn("rounded-md border p-3", passed && "opacity-60")}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-medium">{st.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {from && to ? (from === to ? dateLabel(from) : `${dateLabel(from)} – ${dateLabel(to)}`) : st.when}
                        {passed ? " · passed" : ""}
                      </span>
                    </div>
                    <ul className="mt-2 space-y-2">
                      {st.services.map((sv) => {
                        const vendors = lifecycles.vendors[sv.vendor];
                        const partners = board.partners[sv.vendor] ?? [];
                        return (
                          <li key={sv.name}>
                            <div>{sv.name}</div>
                            <div className="text-xs text-muted-foreground">
                              {vendors ? `${count(vendors.companies)} Chicago companies` : ""}
                              {partners.length > 0 && " · e.g. "}
                              {partners.slice(0, 3).map((p, i) => (
                                <span key={p.name}>
                                  {i > 0 && ", "}
                                  {p.name}
                                  {p.phone && (
                                    <>
                                      {" "}
                                      <a href={`tel:${p.phone.replace(/\D/g, "")}`} className="text-primary hover:underline">
                                        {p.phone}
                                      </a>
                                    </>
                                  )}
                                </span>
                              ))}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })}
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              Partner examples are public business listings (Overture Maps); call to confirm they do this work before you sign
              them. <Link href={`/opportunities#${lifecycle.id}`} className="text-primary hover:underline">Full lifecycle</Link>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ContactLinks({ phone, email, website }: { phone: string | null; email: string | null; website: string | null }) {
  if (!phone && !email && !website) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
      {phone && (
        <a href={`tel:${phone.replace(/\D/g, "")}`} className="text-primary hover:underline">
          {phone}
        </a>
      )}
      {email && (
        <a href={`mailto:${email}`} className="text-primary hover:underline">
          {email}
        </a>
      )}
      {website && isHttpUrl(website) && (
        <a href={website} target="_blank" rel="noopener noreferrer nofollow" className="text-primary hover:underline">
          website
        </a>
      )}
    </div>
  );
}
