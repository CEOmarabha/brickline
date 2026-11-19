import { toCsv } from "@/lib/csv";
import {
  EVENT_GROUPS,
  type EventContact,
  type EventGroup,
  type EventsFile,
  getEvents,
  parseEventGroup,
  withOrganizer,
} from "@/lib/events";
import { viewerId } from "@/lib/workspace";

const NO_STORE = { "cache-control": "private, no-store" };
const BLOCK_NOTE = "Resident-filed: flyers or door hangers on the block a few weeks before; no personal contact";

const CONTACT_HEADER = [
  "contact_name",
  "contact_phone",
  "contact_website",
  "contact_email",
  "contact_address",
  "contact_source",
  "contact_match",
];
const TAIL_HEADER = ["source", "id", "date_contacted", "outcome", "notes"];

function contactCells(c: EventContact | null): string[] {
  return [c?.name ?? "", c?.phone ?? "", c?.website ?? "", c?.email ?? "", c?.address ?? "", c?.source ?? "", c?.match ?? ""];
}

function place(e: { location: string | null; segments: number }): string {
  return e.location ? (e.segments > 1 ? `${e.location} (+${e.segments - 1} more)` : e.location) : "";
}

function build(file: EventsFile, group: EventGroup): { header: string[]; rows: (string | number | null)[][] } {
  if (group === "organizations") {
    return {
      header: [
        "start_date",
        "end_date",
        "days_until",
        "type",
        "event",
        "organizer",
        "location",
        "community_area",
        "ward",
        "status",
        "first_seen",
        ...CONTACT_HEADER,
        ...TAIL_HEADER,
      ],
      rows: withOrganizer(file).map((e) => [
        e.startDate,
        e.endDate,
        e.daysUntil,
        e.type,
        e.name ?? "",
        e.organizer,
        place(e),
        e.communityArea?.name ?? "",
        e.ward,
        e.status,
        e.firstSeen,
        ...contactCells(e.contact),
        e.source,
        e.id,
        "",
        "",
        "",
      ]),
    };
  }
  if (group === "recurring") {
    return {
      header: [
        "expected_from",
        "expected_to",
        "days_until_expected",
        "ran_last_12_months",
        "type",
        "event",
        "organizer",
        "seasons_run_of_3",
        "years_run",
        "last_date",
        "already_filed",
        "historical_recurrence_rate",
        "rate_series_count",
        "location",
        "community_area",
        "ward",
        ...CONTACT_HEADER,
        ...TAIL_HEADER,
      ],
      rows: file.recurring.map((s) => [
        s.expectedStart,
        s.expectedEnd,
        s.daysUntilExpected,
        s.ranLastSeason ? "yes" : "no",
        s.type,
        s.name ?? "",
        s.organizer ?? "",
        s.seasonsRun,
        s.yearsRun.join("; "),
        s.lastDate,
        s.onCalendar ? "yes" : "no",
        s.recurrence?.rate ?? "",
        s.recurrence?.series ?? "",
        place(s),
        s.communityArea?.name ?? "",
        s.ward,
        ...contactCells(s.contact),
        s.source,
        s.id,
        "",
        "",
        "",
      ]),
    };
  }
  return {
    header: [
      "start_date",
      "end_date",
      "days_until",
      "block",
      "ward",
      "community_area",
      "closure",
      "status",
      "outreach",
      "id",
    ],
    rows: file.blockParties.items.map((b) => [
      b.startDate,
      b.endDate,
      b.daysUntil,
      b.block ? (b.segments > 1 ? `${b.block} (+${b.segments - 1} more)` : b.block) : "",
      b.ward,
      b.communityArea?.name ?? "",
      b.closure ?? "",
      b.status,
      BLOCK_NOTE,
      b.id,
    ]),
  };
}

export async function GET(request: Request) {
  const owner = await viewerId();
  if (!owner) return new Response("Sign in required", { status: 401, headers: NO_STORE });
  const raw = new URL(request.url).searchParams.get("group");
  const group = raw === null ? "organizations" : parseEventGroup(raw);
  if (!group) {
    return new Response(`Unknown group. Use group=${EVENT_GROUPS.join("|")}`, { status: 400, headers: NO_STORE });
  }
  const file = await getEvents();
  if (!file) return new Response("Events list not generated yet", { status: 404, headers: NO_STORE });
  const { header, rows } = build(file, group);
  return new Response(toCsv(header, rows), {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-events-${group}-${file.asOf}.csv"`,
      ...NO_STORE,
    },
  });
}
