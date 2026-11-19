import "server-only";

import { readFile, stat } from "node:fs/promises";
import path from "node:path";

/** Allow-list of CSV groups and page tabs. Anything else is rejected. */
export const EVENT_GROUPS = ["organizations", "recurring", "blockparties"] as const;
export type EventGroup = (typeof EVENT_GROUPS)[number];

export const EVENT_TABS = ["organizations", "recurring", "blockparties"] as const;
export type EventTab = (typeof EVENT_TABS)[number];

export interface EventContact {
  name: string | null;
  phone: string | null;
  website: string | null;
  email: string | null;
  address: string | null;
  source: string;
  match: "exact" | "similar";
  alsoIn: string[];
}

export interface AreaRef {
  id: number;
  name: string;
}

export type OrganizerStatus = "organization" | "individual" | "withheld" | "unpublished";

interface EventBase {
  id: string;
  source: string;
  type: string;
  name: string | null;
  organizer: string | null;
  organizerIsPerson: boolean | null;
  organizerStatus: OrganizerStatus;
  kind: string | null;
  location: string | null;
  segments: number;
  communityArea: AreaRef | null;
  ward: number | null;
  contact: EventContact | null;
}

export interface UpcomingEvent extends EventBase {
  tier: string | null;
  startDate: string;
  endDate: string;
  daysUntil: number;
  closure: string | null;
  status: string;
  firstSeen: string | null;
}

export interface RecurrenceRate {
  rate: number;
  series: number;
  years: number;
  scope: string;
}

export interface RecurringSeries extends EventBase {
  seasonsRun: number;
  yearsRun: number[];
  lastDate: string;
  ranLastSeason: boolean;
  consecutive: boolean;
  typicalStart: string;
  typicalEnd: string;
  expectedStart: string;
  expectedEnd: string;
  spreadDays: number;
  daysUntilExpected: number;
  recurrence: RecurrenceRate | null;
  onCalendar: boolean;
}

export interface BlockParty {
  id: string;
  startDate: string;
  endDate: string;
  daysUntil: number;
  block: string | null;
  segments: number;
  closure: string | null;
  ward: number | null;
  communityArea: AreaRef | null;
  status: string;
}

export interface MonthCounts {
  month: string;
  counts: Record<string, number>;
  total: number;
}

export interface LeadTimeRow {
  type: string;
  permits: number;
  withReviewDate: number;
  medianDays: number | null;
  p10Days: number | null;
  p25Days: number | null;
  p75Days: number | null;
  p90Days: number | null;
  atLeast14DaysShare: number | null;
  atLeast28DaysShare: number | null;
  atLeast56DaysShare: number | null;
  between14And56DaysShare: number | null;
  organizationShare: number | null;
  rawOrganizationShare: number | null;
}

export interface ContactStats {
  organizations: number;
  withSuggestion: number;
  withPhoneWebsiteOrEmail: number;
  suggestionShare: number | null;
  detailsShare: number | null;
}

export interface RateEntry {
  series: number;
  hits: number;
  rate: number | null;
}

export interface RecurrenceKind {
  label: string;
  heldTwo: RateEntry | null;
  heldThree: RateEntry | null;
  debut: RateEntry | null;
}

export interface EventsFile {
  generatedAt: string;
  asOf: string;
  parkListedThrough: string | null;
  windowDays: number;
  recurringDays: number;
  definition: string;
  privacy: string;
  counts: {
    upcoming: number;
    upcomingWithOrganization: number;
    upcomingNoOrganization: number;
    upcomingCdot: number;
    upcomingPark: number;
    upcoming2To8Weeks: number;
    recurring: number;
    recurringWithOrganization: number;
    recurringOnCalendar: number;
    blockParties: number;
    withheldOrganizerNames: number;
    organizerNamesScreened: number;
  };
  contactMatch: { upcoming: ContactStats; recurring: ContactStats; all: ContactStats; note: string };
  upcoming: UpcomingEvent[];
  recurring: RecurringSeries[];
  recurrence: Record<"cdotNamed" | "cdotUnnamed" | "park", RecurrenceKind>;
  blockParties: {
    note: string;
    total: number;
    byArea: { id: number; name: string; parties: number }[];
    byWeek: { weekStart: string; parties: number }[];
    items: BlockParty[];
  };
  context: {
    label: string;
    leadTimePeriod: { from: string; to: string };
    pastMonths: MonthCounts[];
    nextMonths: MonthCounts[];
    byType: LeadTimeRow[];
  };
  attribution: { text: string; overtureRelease: string; contactMatch: string };
}

export function parseEventGroup(value: string | string[] | null | undefined): EventGroup | null {
  const v = Array.isArray(value) ? value[0] : value;
  return EVENT_GROUPS.find((g) => g === v) ?? null;
}

export function parseEventTab(value: string | string[] | null | undefined): EventTab {
  const v = Array.isArray(value) ? value[0] : value;
  return EVENT_TABS.find((t) => t === v) ?? "organizations";
}

/** The 2 to 8 week window the founder wants (14 to 56 days of notice). */
export const NOTICE_MIN_DAYS = 14;
export const NOTICE_MAX_DAYS = 56;

export function inNoticeWindow(daysUntil: number): boolean {
  return daysUntil >= NOTICE_MIN_DAYS && daysUntil <= NOTICE_MAX_DAYS;
}

export function withOrganizer(file: EventsFile): UpcomingEvent[] {
  return file.upcoming.filter((e) => e.organizer);
}

export function withoutOrganizer(file: EventsFile): UpcomingEvent[] {
  return file.upcoming.filter((e) => !e.organizer);
}

let loaded: { mtimeMs: number; file: EventsFile } | undefined;

/** The generated events file, or null when `engine.leads.events` has not been run. Reloads when the file changes. */
export async function getEvents(): Promise<EventsFile | null> {
  const file = path.join(process.cwd(), "data", "events.json");
  try {
    const { mtimeMs } = await stat(file);
    if (loaded?.mtimeMs !== mtimeMs) {
      loaded = { mtimeMs, file: JSON.parse(await readFile(file, "utf8")) as EventsFile };
    }
    return loaded.file;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

/** "Nov 19" or "Nov 19 to Dec 24" (the year is implied by the as-of date shown beside the table). */
export function dayRange(start: string, end: string): string {
  const fmt = (iso: string) =>
    new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return start === end ? fmt(start) : `${fmt(start)} to ${fmt(end)}`;
}

/** "06-21" -> "Jun 21" */
export function monthDay(mmdd: string): string {
  const [m, d] = mmdd.split("-").map(Number);
  return new Date(2001, m - 1, d, 12).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "2026-11" -> "Nov 2026" */
export function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1, 12).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

export function weeksLabel(days: number): string {
  if (days < 7) return `${days} day${days === 1 ? "" : "s"}`;
  const w = days / 7;
  return `${Number.isInteger(w) ? w : w.toFixed(1)} wk`;
}

export function eventTitle(e: { name: string | null; type: string }): string {
  return e.name ?? `Unnamed ${e.type.toLowerCase()}`;
}
