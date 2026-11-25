import { Download } from "lucide-react";
import Link from "next/link";
import { EmptyState, PageHeader, StatCard } from "@/components/bits";
import { ScannerView } from "@/components/events/scanner-view";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type EventsFile,
  type EventTab,
  getEvents,
  inNoticeWindow,
  monthLabel,
  parseEventTab,
  withOrganizer,
  withoutOrganizer,
} from "@/lib/events";
import { getEventBoard } from "@/lib/event-board";
import { getEventLeads } from "@/lib/event-leads";
import { count, dateLabel, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { viewerId } from "@/lib/workspace";
import { BlockPartyTable, RecurringTable, UpcomingTable } from "./events-tables";

const BLOCK_ROWS_SHOWN = 300;

type SearchParams = Record<string, string | string[] | undefined>;

/** The page URL with these query params: tabs and filters stay on whichever route renders the view. */
function hrefOf(basePath: string, params: Record<string, string> = {}): string {
  const search = new URLSearchParams(params).toString();
  return search ? `${basePath}?${search}` : basePath;
}

/**
 * The upcoming-events list: organizations in the next 120 days, recurring series and block parties. Rendered by
 * /events (canonical), /pilots/events and /leads (when the workspace is looking for events), so every link in it stays
 * on `basePath`. `title`, `description` and `actions` let a route give it its own header.
 */
export async function EventsView({
  searchParams,
  basePath,
  title = "Upcoming events",
  description,
  actions,
}: {
  searchParams: Promise<SearchParams>;
  basePath: string;
  title?: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  const sp = await searchParams;
  const tab = parseEventTab(sp.tab);
  const narrow = (Array.isArray(sp.notice) ? sp.notice[0] : sp.notice) === "2-8";
  const viewParam = Array.isArray(sp.view) ? sp.view[0] : sp.view;
  const view: RecurringView = viewParam === "next120" || viewParam === "all" ? viewParam : "organizations";
  const [owner, file, board, leads] = await Promise.all([
    viewerId(),
    getEvents(),
    getEventBoard(),
    getEventLeads(),
  ]);
  const boardIds = new Set(board.events.map((e) => e.id));

  if (!file && tab !== "scanner") {
    return (
      <>
        <PageHeader title={title} actions={actions} />
        <EmptyState title="The events list has not been generated yet">
          Run <code>uv run python -m engine.leads.events</code> from the repository root, then reload. The daily
          scanner is on the{" "}
          <Link href={hrefOf(basePath, { tab: "scanner" })} className="underline underline-offset-2">
            scanner tab
          </Link>
          .
        </EmptyState>
      </>
    );
  }

  const c = file?.counts;
  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");
  const tabs: { key: EventTab; label: string }[] = [
    {
      key: "organizations",
      label: `Next ${file?.windowDays ?? 120} days: organizations (${count(c?.upcomingWithOrganization ?? 0)})`,
    },
    { key: "recurring", label: `Expected next season, recurring (${count(c?.recurring ?? 0)})` },
    { key: "blockparties", label: `Block parties, next ${file?.windowDays ?? 120} days (${count(c?.blockParties ?? 0)})` },
    { key: "scanner", label: `Daily scanner (${count(leads.counts.total)})` },
  ];
  const csv = (group: string, label: string) => (
    <a
      key={group}
      href={`/export/events?group=${group}`}
      className={buttonVariants({ variant: "outline", size: "sm" })}
    >
      <Download /> {label}
    </a>
  );

  function tabPanel(): React.ReactNode {
    switch (tab) {
      case "scanner":
        return <ScannerView file={leads} signedIn={Boolean(owner)} />;
      case "organizations":
        return file ? (
          <OrganizationsTab file={file} narrow={narrow} basePath={basePath} boardIds={boardIds} />
        ) : null;
      case "recurring":
        return file ? <RecurringTab file={file} view={view} basePath={basePath} /> : null;
      case "blockparties":
        return file ? <BlockPartiesTab file={file} boardIds={boardIds} /> : null;
      default: {
        const _exhaustive: never = tab;
        return _exhaustive;
      }
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title={title}
        description={
          description ?? (
            <>
              Chicago events on the City&rsquo;s public permit records
              {file ? ` through ${dateLabel(file.asOf)}` : ""}, with the organizer when it is an organization and a
              business listing to start from. A targeting list for event services and the vendors who supply them:
              nothing here predicts who will hire anyone.
            </>
          )
        }
        actions={
          (actions || owner) && (
            <>
              {actions}
              {owner && (
                <>
                  {csv("organizations", "Organizations CSV")}
                  {csv("recurring", "Recurring CSV")}
                  {csv("blockparties", "Block parties CSV")}
                </>
              )}
            </>
          )
        }
      />

      {file && <Explainer file={file} />}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2" role="navigation" aria-label="Event list sections">
          {tabs.map((t) => (
            <Link key={t.key} href={t.key === "organizations" ? basePath : hrefOf(basePath, { tab: t.key })} className={pill(tab === t.key)}>
              {t.label}
            </Link>
          ))}
        </div>

        {tabPanel()}
      </section>

      {file && <HowToUse file={file} />}

      <p className="text-xs text-muted-foreground">
        {file
          ? `${file.attribution.text} Event data as of ${dateLabel(file.asOf)}${
              file.parkListedThrough ? ` (Park District feed listed through ${dateLabel(file.parkListedThrough)})` : ""
            }. ${file.privacy}`
          : "Daily scanner leads are stored in event-leads.json. Review status lives in the app database."}
      </p>
    </div>
  );
}

function Explainer({ file }: { file: EventsFile }) {
  const c = file.counts;
  const ctx = file.context;
  const lt = (type: string) => ctx.byType.find((r) => r.type === type);
  const spoken = (type: string, noun: string) => {
    const r = lt(type);
    return r && r.medianDays !== null && r.p25Days !== null && r.p75Days !== null
      ? `${noun} a median ${Math.round(r.medianDays)} days (middle half ${Math.round(r.p25Days)} to ${Math.round(r.p75Days)})`
      : null;
  };
  const sentence = [
    spoken("Festival", "festivals"),
    spoken("Athletic event", "athletic events"),
    spoken("Parade", "parades"),
    spoken("Block party", "block parties"),
  ].filter(Boolean);
  const block = lt("Block party");
  const total = (m: { total: number }[]) => m.reduce((s, x) => s + x.total, 0);
  const peak = ctx.pastMonths.reduce((a, b) => (b.total > a.total ? b : a), ctx.pastMonths[0]);
  const types = ctx.byType.map((r) => r.type);
  const complete = ctx.nextMonths.slice(0, -1);
  const lastYear = ctx.pastMonths.filter(
    (m) => m.month < file.asOf.slice(0, 7) && complete.some((n) => n.month.slice(5) === m.month.slice(5)),
  );
  const stretch =
    complete.length > 0 && lastYear.length === complete.length
      ? {
          from: lastYear[0].month,
          to: lastYear[lastYear.length - 1].month,
          last: total(lastYear),
          filed: total(complete),
        }
      : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>What this data is</CardTitle>
        <CardDescription>
          Two public sources: the Chicago Department of Transportation&rsquo;s street-closure permits for festivals,
          parades, athletic events, assemblies, sidewalk sales and block parties, and the Chicago Park District&rsquo;s
          event reservations. Each CDOT permit shows the event date, the date the City began reviewing it, and the
          applicant; an applicant that is an individual is never stored or shown. {file.definition}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label={`Events in the next ${file.windowDays} days`}
            value={count(c.upcoming)}
            hint={`${count(c.upcomingWithOrganization)} name an organization; ${count(c.upcomingNoOrganization)} do not`}
          />
          <StatCard
            label="Organizations, 2 to 8 weeks out"
            value={count(c.upcoming2To8Weeks)}
            hint="14 to 56 days of notice, the window to contact"
          />
          <StatCard
            label={`Recurring series expected in ${file.windowDays} days`}
            value={count(file.recurring.filter((s) => s.daysUntilExpected <= file.windowDays).length)}
            hint={`${count(c.recurring)} in the next ${file.recurringDays}; ${count(c.recurringOnCalendar)} already filed`}
          />
          <StatCard
            label={`Block parties in ${file.windowDays} days`}
            value={count(c.blockParties)}
            hint="resident-filed; flyers only"
          />
        </div>

        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong className="text-foreground">Notice period.</strong> From the date the City began reviewing a permit
            to the event date, {ctx.leadTimePeriod.from.slice(0, 4)} to {ctx.leadTimePeriod.to.slice(0, 4)}:{" "}
            {sentence.join("; ")}. Park District events carry no review date, so their notice cannot be computed: their
            &ldquo;listed&rdquo; date is when the row first appeared in the feed (often a bulk load), not an application
            date. {block && block.organizationShare !== null && (
              <>
                Block parties are filed by residents: only {pct(block.organizationShare, 0)} name an organization, so
                the contact for a block party is a flyer on the block, not a person.
              </>
            )}
          </p>
          <p>
            <strong className="text-foreground">Seasonality.</strong> The last 12 months had {count(total(ctx.pastMonths))}{" "}
            events, peaking in {monthLabel(peak.month)} with {count(peak.total)}. The next {file.windowDays} days have{" "}
            {count(total(ctx.nextMonths))} on file so far
            {stretch && (
              <>
                ; the same stretch last year ({monthLabel(stretch.from)} to {monthLabel(stretch.to)}) had{" "}
                {count(stretch.last)} events against {count(stretch.filed)} filed so far for the months to come, because
                many permits are filed only weeks ahead (see the notice table), so later months will grow
              </>
            )}
            .
          </p>
        </div>

        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[44rem] text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Permit type</th>
                <th className="px-3 py-2 font-medium">Permits</th>
                <th className="px-3 py-2 font-medium">Median notice</th>
                <th className="px-3 py-2 font-medium">Middle half</th>
                <th className="px-3 py-2 font-medium">4+ weeks</th>
                <th className="px-3 py-2 font-medium">8+ weeks</th>
                <th className="px-3 py-2 font-medium">Organization named</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {ctx.byType.map((r) => (
                <tr key={r.type}>
                  <td className="px-3 py-2 font-medium">{r.type}</td>
                  <td className="px-3 py-2 tabular-nums">{count(r.permits)}</td>
                  <td className="px-3 py-2 tabular-nums">{r.medianDays === null ? "—" : `${Math.round(r.medianDays)} days`}</td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">
                    {r.p25Days === null || r.p75Days === null ? "—" : `${Math.round(r.p25Days)} to ${Math.round(r.p75Days)} days`}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{pct(r.atLeast28DaysShare, 0)}</td>
                  <td className="px-3 py-2 tabular-nums">{pct(r.atLeast56DaysShare, 0)}</td>
                  <td className="px-3 py-2 tabular-nums">{pct(r.organizationShare, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">
          {ctx.label}: permits starting {dateLabel(ctx.leadTimePeriod.from)} to {dateLabel(ctx.leadTimePeriod.to)} that were not cancelled or
          denied ({types.length} types; sidewalk sales often have no review date). &ldquo;Organization named&rdquo; counts
          applicant names that read as an organization; ambiguous names are treated as individuals and withheld
          ({count(c.withheldOrganizerNames)} of {count(c.organizerNamesScreened)} applicant names screened).
        </p>

        <details className="rounded-md border">
          <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium select-none">
            Events by month: last 12 months and the next {file.windowDays} days
          </summary>
          <div className="space-y-3 border-t p-4">
            <MonthTable title="Last 12 months" months={ctx.pastMonths} />
            <MonthTable title={`Next ${file.windowDays} days (filed so far)`} months={ctx.nextMonths} />
            <p className="text-xs text-muted-foreground">
              CDOT permits and Park District event names that start in the month; Park District counts only events held
              (approved, issued or completed) in the past and includes tentative reservations in the future.
            </p>
          </div>
        </details>
      </CardContent>
    </Card>
  );
}

function MonthTable({ title, months }: { title: string; months: EventsFile["context"]["pastMonths"] }) {
  const types = months[0] ? Object.keys(months[0].counts) : [];
  const max = Math.max(1, ...months.map((m) => m.total));
  return (
    <div>
      <div className="mb-1 text-sm font-medium">{title}</div>
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[52rem] text-xs">
          <thead className="border-b text-left text-muted-foreground">
            <tr>
              <th className="px-2 py-1.5 font-medium">Month</th>
              <th className="px-2 py-1.5 font-medium">Total</th>
              {types.map((t) => (
                <th key={t} className="px-2 py-1.5 font-medium">
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {months.map((m, i) => (
              <tr key={`${m.month}-${i}`}>
                <td className="px-2 py-1.5 whitespace-nowrap">{monthLabel(m.month)}</td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-10 tabular-nums">{count(m.total)}</span>
                    <span className="h-1.5 rounded bg-primary/40" style={{ width: `${Math.max(2, (m.total / max) * 80)}px` }} aria-hidden />
                  </div>
                </td>
                {types.map((t) => (
                  <td key={t} className="px-2 py-1.5 tabular-nums text-muted-foreground">
                    {count(m.counts[t])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OrganizationsTab({
  file,
  narrow,
  basePath,
  boardIds,
}: {
  file: EventsFile;
  narrow: boolean;
  basePath: string;
  boardIds: ReadonlySet<string>;
}) {
  const all = withOrganizer(file);
  const rows = narrow ? all.filter((e) => inNoticeWindow(e.daysUntil)) : all;
  const rest = withoutOrganizer(file);
  const stats = file.contactMatch.upcoming;
  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={basePath} className={pill(!narrow)}>
          All ({count(all.length)})
        </Link>
        <Link href={hrefOf(basePath, { notice: "2-8" })} className={pill(narrow)}>
          2 to 8 weeks out ({count(all.filter((e) => inNoticeWindow(e.daysUntil)).length)})
        </Link>
      </div>
      <h2 className="text-lg font-semibold">
        Organizations running events in the next {file.windowDays} days{" "}
        <span className="text-sm font-normal text-muted-foreground">({count(rows.length)} events)</span>
      </h2>
      <UpcomingTable rows={rows} boardIds={boardIds} />
      <p className="text-xs text-muted-foreground">
        Contact suggestions: {count(stats.withSuggestion)} of {count(stats.organizations)} distinct organizations here have a
        public listing match ({count(stats.withPhoneWebsiteOrEmail)} with a phone, website or generic email). {file.contactMatch.note}
      </p>
      {rest.length > 0 && (
        <details className="rounded-md border">
          <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium select-none">
            Other events in the window with no organization named ({count(rest.length)})
          </summary>
          <div className="space-y-2 border-t p-4">
            <p className="text-sm text-muted-foreground">
              Filed by an individual, with an ambiguous name, or from the Park District feed, which does not publish
              organizers. These are shown for context only: there is no one to contact from this data.
            </p>
            <UpcomingTable rows={rest} boardIds={boardIds} />
          </div>
        </details>
      )}
    </div>
  );
}

type RecurringView = "organizations" | "next120" | "all";
const RECURRING_ROWS_SHOWN = 300;

function RecurringTab({ file, view, basePath }: { file: EventsFile; view: RecurringView; basePath: string }) {
  const withOrg = file.recurring.filter((s) => s.organizer);
  const soon = file.recurring.filter((s) => s.daysUntilExpected <= file.windowDays);
  const all = view === "all" ? file.recurring : view === "next120" ? soon : withOrg;
  const rows = all.slice(0, RECURRING_ROWS_SHOWN);
  const r = file.recurrence;
  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");
  const line = (label: string, k: keyof typeof r) => {
    const x = r[k];
    return x.heldTwo?.rate != null ? (
      <li key={k}>
        {label}: {pct(x.heldTwo.rate, 0)} of {count(x.heldTwo.series)} series held in each of the last 2 years came back
        {x.heldThree?.rate != null ? `; ${pct(x.heldThree.rate, 0)} of ${count(x.heldThree.series)} after 3 years` : ""}
        {x.debut?.rate != null ? ` (a first-time series: ${pct(x.debut.rate, 0)})` : ""}.
      </li>
    ) : null;
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={hrefOf(basePath, { tab: "recurring" })} className={pill(view === "organizations")}>
          Organization named ({count(withOrg.length)})
        </Link>
        <Link href={hrefOf(basePath, { tab: "recurring", view: "next120" })} className={pill(view === "next120")}>
          Expected in {file.windowDays} days ({count(soon.length)})
        </Link>
        <Link href={hrefOf(basePath, { tab: "recurring", view: "all" })} className={pill(view === "all")}>
          All ({count(file.recurring.length)})
        </Link>
      </div>
      <h2 className="text-lg font-semibold">
        Expected next season{" "}
        <span className="text-sm font-normal text-muted-foreground">
          ({count(all.length)} recurring occurrences, next {file.recurringDays} days)
        </span>
      </h2>
      <p className="text-sm text-muted-foreground">
        Series (the same event name and organizer, or the same organizer and ward when the permit has no name, or the
        same event at the same park) with a run in at least 2 of the last 3 twelve-month seasons. The expected window is
        the same dates one year on, plus or minus the spread seen, at least a week. Contact the organizer the season
        before; the &ldquo;past recurrence&rdquo; figure is how often a series with that history came back in earlier years.
      </p>
      <RecurringTable rows={rows} />
      {all.length > rows.length && (
        <p className="text-xs text-muted-foreground">
          Showing the first {count(rows.length)} of {count(all.length)} by expected date; the recurring CSV has them all.
        </p>
      )}
      <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
        {line("CDOT events with a name", "cdotNamed")}
        {line("CDOT events without a name", "cdotUnnamed")}
        {line("Park District events", "park")}
      </ul>
      <p className="text-xs text-muted-foreground">
        Rates come from the same series logic as signal lab H38 (pandemic years left out); they apply to series that ran
        in the last 12 months and the season before. An event that came back is a permit within a month of the same date a
        year later; it is not a promise that the organizer will hire a vendor. {count(file.counts.recurringWithOrganization)} of
        these {count(file.counts.recurring)} occurrences name an organization; the Park District feed names none.
      </p>
    </div>
  );
}

function BlockPartiesTab({ file, boardIds }: { file: EventsFile; boardIds: ReadonlySet<string> }) {
  const b = file.blockParties;
  const weeks = b.byWeek.filter((w) => w.parties > 0);
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">
        Block parties in the next {file.windowDays} days{" "}
        <span className="text-sm font-normal text-muted-foreground">({count(b.total)} permits)</span>
      </h2>
      <Card size="sm">
        <CardContent className="text-sm text-muted-foreground">
          <strong className="text-foreground">How to reach them:</strong> {b.note}
        </CardContent>
      </Card>
      {b.total === 0 ? (
        <EmptyState title="No block parties filed for this window yet" />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <div className="mb-1.5 text-sm font-medium">By neighborhood</div>
              <div className="flex flex-wrap gap-2 text-sm">
                {b.byArea.map((a) => (
                  <span key={`${a.id}-${a.name}`} className="rounded-md border px-2 py-1">
                    {a.name} <span className="tabular-nums text-muted-foreground">{count(a.parties)}</span>
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1.5 text-sm font-medium">By week (starting)</div>
              <div className="flex flex-wrap gap-2 text-sm">
                {weeks.map((w) => (
                  <span key={w.weekStart} className="rounded-md border px-2 py-1">
                    {dateLabel(w.weekStart).replace(/, \d{4}$/, "")}{" "}
                    <span className="tabular-nums text-muted-foreground">{count(w.parties)}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
          <BlockPartyTable rows={b.items.slice(0, BLOCK_ROWS_SHOWN)} boardIds={boardIds} />
          {b.items.length > BLOCK_ROWS_SHOWN && (
            <p className="text-xs text-muted-foreground">
              Showing the first {count(BLOCK_ROWS_SHOWN)} by date; the full list is in the block parties CSV.
            </p>
          )}
        </>
      )}
      <p className="text-xs text-muted-foreground">
        Only the block, date, ward and neighborhood are kept. The permit data holds no business to contact, and this page
        stores and shows no applicant data.
      </p>
    </div>
  );
}

function HowToUse({ file }: { file: EventsFile }) {
  const lt = (type: string) => file.context.byType.find((r) => r.type === type);
  const early = (type: string, label: string) => {
    const r = lt(type);
    return r?.atLeast28DaysShare == null ? null : `${pct(r.atLeast28DaysShare, 0)} of ${label}`;
  };
  const ahead = [
    early("Festival", "festivals"),
    early("Athletic event", "athletic events"),
    early("Parade", "parades"),
    early("Block party", "block parties"),
  ].filter(Boolean);
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>How to use this list</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Contact organizations 4 to 8 weeks before the event, and recurring organizers the season before.
            {ahead.length > 0 &&
              ` Already in City review 4 or more weeks ahead (permits starting ${file.context.leadTimePeriod.from.slice(0, 4)} to ${file.context.leadTimePeriod.to.slice(0, 4)}): ${ahead.join(", ")}.`}
          </li>
          <li>
            Reach each organization one by one through its business phone, website or email, by hand. No bulk sends, no
            autodialed or AI calls, no texts. Block parties get flyers or door hangers on the block, not personal contact.
          </li>
          <li>
            Honor opt-outs the same day and keep your own do-not-contact list. A contact suggestion is a name match to a
            public listing, so confirm it is the right organization first.
          </li>
          <li>
            You are an independent business. Never say or imply you represent the City, the Park District or any agency.
          </li>
          <li>Write down who you contacted, when, and what happened (the CSV has empty columns for it).</li>
        </ul>
      </CardContent>
    </Card>
  );
}
