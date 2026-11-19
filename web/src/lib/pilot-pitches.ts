import "server-only";

import type { BuyerList, BuyerListKey, BuyersFile } from "@/lib/buyers";
import type { EventsFile } from "@/lib/events";
import { count, pct } from "@/lib/format";
import type { PestFile } from "@/lib/pest";
import type { ClosedRestaurantLead, OpenTradeRow, Snapshot } from "@/lib/snapshot";

export interface PilotStat {
  label: string;
  value: string;
  hint?: string;
}

export interface PilotLink {
  href: string;
  label: string;
  /** A CSV download: only offered to a signed-in viewer. */
  csv?: boolean;
}

export interface PilotEmail {
  key: string;
  label: string;
  subject: string;
  body: string;
}

export interface PilotCard {
  key: BuyerListKey;
  title: string;
  anchor: string;
  summary: string;
  caveat: string;
  stats: PilotStat[];
  links: PilotLink[];
  emails: PilotEmail[];
}

/** Days after a $1M+ permit in which a follow-on trade permit counts (the same window as the open-trades model). */
const FOLLOW_WINDOW_DAYS = 540;

const NOUN: Record<string, string> = {
  cleaning: "commercial cleaning or janitorial company",
  signage: "sign company",
  security: "security or alarm company",
  insurance: "insurance agency",
  movers: "moving company",
  elevator: "elevator contractor",
  electrical: "electrical contractor",
  fireAlarm: "fire-alarm or fire-protection contractor",
  signs: "sign contractor",
  gc: "general contractor",
  kitchen: "restaurant equipment and supply dealer",
  brokers: "commercial real estate firm",
  pest: "pest-control company",
  events: "rental or event-services company",
};

/** Why this list could matter to this kind of buyer, in plain words and without any promise. */
const WHY: Record<BuyerListKey, Record<string, string>> = {
  newBusiness: {
    cleaning:
      "A new tenant is a natural moment to ask about cleaning and janitorial service, and this list gives you the address while the space is still being built out.",
    signage:
      "A business opening in a newly built-out space may need a sign, and this list gives you the address while the space is still under construction.",
    security:
      "A new business may need alarm, camera or access-control work, and this list gives you the address while the space is still being built out.",
    insurance:
      "A new business has to arrange coverage before it opens, and this list gives you the address while the space is still being built out.",
    movers:
      "A new tenant may need furniture, equipment or an office moved in, and this list gives you the address while the space is still being built out.",
  },
  openTrades: {},
  closedRestaurant: {
    gc: "Your company is named as general contractor on recent restaurant build-out permits in the City's permit records, so you already do this work.",
    kitchen:
      "A restaurant space that closed may be re-let to a new food business, and a new operator may need kitchen equipment.",
    brokers:
      "A restaurant space that closed may be re-let, and this list shows which addresses have no new food license yet.",
    signage:
      "A restaurant space that closed may be re-let to a new operator, and a new operator may need new signage.",
  },
  pest: {
    pest: "Your company appears as a pest-control company in public business listings.",
  },
};

const TRADE_KEY: Record<string, string> = {
  elevator: "elevator",
  electrical: "electrical",
  fireAlarm: "fire_alarm",
  signs: "signs",
};

const INTRO =
  "I'm [Your name], founder of [Your company], a small Chicago company that turns public records into lead lists. We're an independent business, not a government agency, and we're not affiliated with the City of Chicago or any government office.";

const OFFER = [
  "Here is what I'd suggest. I send you a free sample of 5 rows from the current list so you can judge it. If it looks useful, I'll send the list weekly, free, for 4 weeks. In return I'd ask one thing: tell me which rows you contacted and which turned into work, so I can learn whether the list is worth paying for. No cost, no contract.",
  "If a free trial isn't the right fit, I'm also open to talking about paying only for the jobs you win. That is an option to discuss, nothing is set, and any terms would be agreed in writing first.",
].join("\n\n");

const DISCLAIMER_PERMIT =
  "This is a targeting list built from public records, not a promise of customers or revenue. The percentages are historical rates from past records (floors, because permits miss unpermitted work) and may not repeat.";
const DISCLAIMER_PEST =
  "This is a targeting list built from public records, not a promise of customers or revenue. The percentages describe what happened in past inspection records; they say nothing about whether any restaurant will hire a pest-control company.";

function footer(segmentKey: string, permitDerived: boolean): string {
  const noun = NOUN[segmentKey] ?? "business";
  const where = permitDerived
    ? "in public business listings or City of Chicago building permit records"
    : "in public business listings";
  return [
    "[Your name]",
    "[Your company]",
    "[Your physical mailing address]",
    "[Your email] · [Your business phone]",
    "",
    `You're receiving this one-to-one commercial message because [Recipient company] appears ${where} as a ${noun}. If you'd rather not hear from me, reply "unsubscribe" and I will remove you right away and won't email you again.`,
  ].join("\n");
}

function assemble(
  subject: string,
  segmentKey: string,
  permitDerived: boolean,
  paragraphs: string[],
  disclaimer: string = DISCLAIMER_PERMIT,
) {
  const body = [
    "Hello [Owner first name],",
    "",
    INTRO,
    "",
    ...paragraphs.flatMap((p) => [p, ""]),
    OFFER,
    "",
    disclaimer,
    "",
    "Would you like me to send the 5-row sample?",
    "",
    footer(segmentKey, permitDerived),
  ].join("\n");
  return { subject, body };
}

function range(lo: number | null, hi: number | null): string {
  return lo === null || hi === null ? "" : ` (middle half ${lo.toFixed(0)} to ${hi.toFixed(0)} days)`;
}

function newBusinessCard(snap: Snapshot, list: BuyerList | undefined): PilotCard {
  const { model: m, spacesTotal } = snap.commercial.newBusiness;
  const rates = `Of ${count(m.signals)} build-out permits at commercial, mixed-use and larger apartment addresses with no business license in force (${m.period}), ${pct(m.rate)} were followed by a new business license at the same address within a year, against ${pct(m.matchedRate)} at comparable addresses with no build-out permit (${m.lift.toFixed(1)}x). The license arrived a median of ${m.medianDays.toFixed(0)} days after the permit${range(m.daysP25, m.daysP75)}.`;
  return {
    key: "newBusiness",
    title: "New business coming",
    anchor: "new-business",
    summary: `Addresses where a build-out permit was issued and no business license is in force yet. ${rates}`,
    caveat:
      "A targeting list, not a chance of work for any buyer: the permit names the contractor and applicant, not the future tenant, and the rates are floors.",
    stats: [
      { label: "Current spaces", value: count(spacesTotal), hint: "build-out permits, last 180 days, no license yet" },
      { label: "New license within a year", value: pct(m.rate), hint: `vs ${pct(m.matchedRate)} at comparable addresses` },
      {
        label: "Median days permit to license",
        value: m.medianDays.toFixed(0),
        hint: `middle half ${m.daysP25.toFixed(0)} to ${m.daysP75.toFixed(0)}`,
      },
      { label: "Permits behind the rate", value: count(m.signals), hint: m.period },
    ],
    links: [
      { href: "/commercial#new-business", label: "See the list" },
      { href: "/export/new-business", label: "Spaces CSV", csv: true },
    ],
    emails: emailsFor("newBusiness", list, (seg) => {
      const lines = [
        WHY.newBusiness[seg.key] ?? "",
        `Each row is an address where the City issued a build-out permit and no business license is in force yet. ${rates} The list has ${count(spacesTotal)} such addresses right now, each with the address, permit date, the work described on the permit and the contractor named on it. It does not name the future tenant.`,
      ].filter(Boolean);
      return assemble(
        "Free sample: Chicago addresses with a build-out permit and no business license yet",
        seg.key,
        seg.permitDerived,
        lines,
      );
    }),
  };
}

function openTradesCard(snap: Snapshot, list: BuyerList | undefined): PilotCard {
  const { model: m, recentTotal } = snap.commercial.openTrades;
  const labels = new Map(m.byTrade.map((t) => [t.trade, t.label]));
  const headline = m.headlineTrades.map((t) => (labels.get(t) ?? t).toLowerCase());
  const rowFor = (segKey: string): OpenTradeRow | undefined => m.byTrade.find((t) => t.trade === TRADE_KEY[segKey]);
  const openCount = m.byTrade.filter((t) => !t.mostlyLockedIn).length;
  const listed = (["elevator", "electrical", "fire_alarm", "signs"] as const)
    .map((k) => m.byTrade.find((t) => t.trade === k))
    .filter((t): t is OpenTradeRow => t !== undefined);
  return {
    key: "openTrades",
    title: "Trades still open after big permits",
    anchor: "open-trades",
    summary: `After a $1M+ new-construction or renovation permit at a commercial, multifamily, mixed-use or flats address (${count(m.bigPermits)} permits, ${m.period}), ${pct(m.followOnRate, 0)} saw a follow-on permit for ${headline.join(", ")} work at the address within ${FOLLOW_WINDOW_DAYS} days (median ${m.medianDays.toFixed(0)} days). In ${openCount} of ${m.byTrade.length} trades most follow-on permits go to a contractor not named on the big permit.`,
    caveat:
      "A targeting list for the open trades, not a chance of work for any contractor. Much of the follow-on rate is simply an active building, and permits capture permitted work only.",
    stats: [
      { label: "Big permits behind the rates", value: count(m.bigPermits), hint: m.period },
      { label: "Recent $1M+ permits", value: count(recentTotal), hint: "last 365 days, with trades already appeared" },
      ...listed.map((t) => ({
        label: `${t.label} follow-on`,
        value: pct(t.followOnRate, 0),
        hint:
          t.newShare === null
            ? "of big permits"
            : `of big permits; ${pct(t.newShare, 0)} of those to a new contractor`,
      })),
    ],
    links: [{ href: "/commercial#open-trades", label: "See the list" }],
    emails: emailsFor("openTrades", list, (seg) => {
      const row = rowFor(seg.key);
      const label = (row?.label ?? seg.label).toLowerCase();
      const rate = row
        ? `After a $1M+ permit at a commercial, multifamily, mixed-use or flats address (${count(m.bigPermits)} permits, ${m.period}), ${pct(row.followOnRate, 0)} saw a later ${label} permit at the same address within ${FOLLOW_WINDOW_DAYS} days${row.medianDays === null ? "" : `, a median of ${row.medianDays.toFixed(0)} days after the big permit${range(row.daysP25, row.daysP75)}`}.${row.newShare === null ? "" : ` ${pct(row.newShare, 0)} of those follow-on permits went to a contractor who was not named on the big permit.`}`
        : `After a $1M+ permit at a commercial, multifamily, mixed-use or flats address (${count(m.bigPermits)} permits, ${m.period}), ${pct(m.followOnRate, 0)} saw a follow-on permit for ${headline.join(", ")} work within ${FOLLOW_WINDOW_DAYS} days.`;
      const lines = [
        `Each week I list the recent $1M+ permits in Chicago (${count(recentTotal)} in the last 365 days), the contractors named on them, and which trades have already shown up at the address and which have not yet.`,
        `${rate} Whether a follow-on job reaches you depends on you, not on the list; it just shows where ${label} work has not yet appeared.`,
      ];
      return assemble(
        `Free sample: Chicago buildings with a $1M+ permit where ${label} work may still be open`,
        seg.key,
        seg.permitDerived,
        lines,
      );
    }),
  };
}

function closedRestaurantCard(snap: Snapshot, list: BuyerList | undefined): PilotCard {
  const m = snap.models.closedRestaurant;
  const spaces = snap.leads.filter((l): l is ClosedRestaurantLead => l.kind === "closed_restaurant").length;
  const license = `Of ${count(m.episodes)} restaurants recorded out of business (${m.period}), ${pct(m.license.p365)} were followed by a new food business license under another name at the same address within a year, against ${pct(m.license.baseline365)} after ordinary restaurant inspections (${m.license.lift.toFixed(1)}x). Counting only licenses issued 31 or more days after the closure it is ${pct(m.licenseAfter30.p365)} against ${pct(m.licenseAfter30.baseline365)} (${m.licenseAfter30.lift.toFixed(1)}x), a median of ${m.licenseAfter30.medianDays.toFixed(0)} days later${range(m.licenseAfter30.daysP25, m.licenseAfter30.daysP75)}.`;
  const permit = `A renovation or build-out permit followed ${pct(m.permit.p365)} against ${pct(m.permit.baseline365)} (${m.permit.lift.toFixed(2)}x), which is a weak signal, so I am not suggesting construction work is likely.`;
  return {
    key: "closedRestaurant",
    title: "Closed restaurant spaces",
    anchor: "closed-restaurants",
    summary: `Restaurant spaces recorded out of business in public inspection data with no new food license under another name yet. ${license} ${permit}`,
    caveat:
      "Who pays for this list is unproven. The build-out permit rate is weak, so don't pitch construction work; letters to the property owner never mention the closure, the inspection or the City.",
    stats: [
      { label: "Current spaces", value: count(spaces), hint: "closed in the last 180 days, no new license yet" },
      {
        label: "New food business in a year",
        value: pct(m.license.p365),
        hint: `vs ${pct(m.license.baseline365)} ordinary restaurants`,
      },
      {
        label: "...31+ days after closing",
        value: pct(m.licenseAfter30.p365),
        hint: `vs ${pct(m.licenseAfter30.baseline365)}; median ${m.licenseAfter30.medianDays.toFixed(0)} days`,
      },
      {
        label: "Build-out permit in a year",
        value: pct(m.permit.p365),
        hint: `vs ${pct(m.permit.baseline365)}; a weak signal`,
      },
    ],
    links: [{ href: "/commercial#closed-restaurants", label: "See the list" }],
    emails: emailsFor("closedRestaurant", list, (seg) => {
      const lines = [
        WHY.closedRestaurant[seg.key] ?? "",
        `Each row is a Chicago restaurant space recorded out of business in the public inspection data that has no new food license under another name yet (${count(spaces)} right now), with the address, neighborhood and closing date. ${seg.key === "gc" ? `${permit} ${license}` : `${license} ${permit}`}`,
      ].filter(Boolean);
      return assemble(
        "Free sample: Chicago restaurant spaces with no new food license yet",
        seg.key,
        seg.permitDerived,
        lines,
      );
    }),
  };
}

function pestCard(pest: PestFile | null, list: BuyerList | undefined): PilotCard {
  const c = pest?.context;
  const volume =
    c && c.perWeek !== null
      ? `Over the last ${c.weeks} weeks in the published records, that was about ${c.perWeek} restaurants a week across Chicago, and ${pct(c.failShare, 0)} of those inspections failed against ${pct(c.ordinaryFailShare, 0)} of ${count(c.ordinaryInspections)} ordinary restaurant inspections.`
      : "";
  return {
    key: "pest",
    title: "Pest-control pilot",
    anchor: "pest",
    summary: pest
      ? `Restaurants whose newest inspection shows a fresh pest finding (the first at the license in ${pest.windows.episodeGapDays} days), through ${pest.asOf}. ${volume}`
      : "The pest pilot list has not been generated yet.",
    caveat:
      "Descriptive history only: no chance of winning work has been measured. Nearly every restaurant already has pest control, so the realistic offer is to switch or add service.",
    stats: pest
      ? [
          { label: "Fresh findings, latest week", value: count(pest.counts.latestWeek), hint: "inspections post with a delay" },
          { label: `Fresh findings, ${pest.windows.backfillDays} days`, value: count(pest.counts.last28Days) },
          {
            label: `Per week, last ${pest.context.weeks} weeks`,
            value: pest.context.perWeek === null ? "—" : String(pest.context.perWeek),
          },
          {
            label: "Of those inspections, Fail",
            value: pct(pest.context.failShare, 0),
            hint: `vs ${pct(pest.context.ordinaryFailShare, 0)} of ordinary inspections`,
          },
        ]
      : [],
    links: [
      { href: "/pilots/pest", label: "See the list" },
      { href: "/export/pest?range=28d", label: "28-day CSV", csv: true },
    ],
    emails: emailsFor("pest", list, (seg) => {
      const lines = [
        WHY.pest.pest ?? "",
        `Each week I put together a list of Chicago restaurants whose newest published inspection record shows a new pest finding (rodents, mice, roaches, flies or similar), the first at that restaurant in at least ${pest?.windows.episodeGapDays ?? 180} days. ${volume} Each row has the address, neighborhood, inspection date, the pest terms in the record, earlier findings, whether the restaurant has been re-inspected since, and a business phone or website when a public listing exists. Most restaurants already have a provider, so the realistic opening is switching or adding service.`,
      ].filter(Boolean);
      return assemble(
        "Free sample: Chicago restaurants with a new pest finding",
        seg.key,
        seg.permitDerived,
        lines,
        DISCLAIMER_PEST,
      );
    }),
  };
}

function emailsFor(
  key: BuyerListKey,
  list: BuyerList | undefined,
  build: (seg: { key: string; label: string; permitDerived: boolean }) => { subject: string; body: string },
): PilotEmail[] {
  if (!list) return [];
  return list.segments.map((s) => ({
    key: `${key}-${s.key}`,
    label: s.label,
    ...build({ key: s.key, label: s.label, permitDerived: s.permitDerived }),
  }));
}

/** One card per pilot list, in hub order. Every number comes from the snapshot, pest.json or buyers.json. */
export function buildPilotCards(snap: Snapshot, pest: PestFile | null, buyers: BuyersFile | null): PilotCard[] {
  const find = (k: BuyerListKey) => buyers?.lists.find((l) => l.key === k);
  return [
    newBusinessCard(snap, find("newBusiness")),
    openTradesCard(snap, find("openTrades")),
    closedRestaurantCard(snap, find("closedRestaurant")),
    pestCard(pest, find("pest")),
  ];
}

export interface EventsPilotCard {
  key: "events";
  title: string;
  anchor: string;
  summary: string;
  caveat: string;
  stats: PilotStat[];
  links: PilotLink[];
  buyerTypes: { label: string; why: string }[];
  emails: PilotEmail[];
}

const DISCLAIMER_EVENTS =
  "This is a targeting list built from public permit records, not a promise of customers or revenue. It shows which events are on file and who filed them, not who will hire a vendor; many organizers already have one.";

/** The "Upcoming events" card: the founder's own event-services list and a pitch to rental and service vendors. */
export function buildEventsCard(events: EventsFile | null): EventsPilotCard {
  const base = {
    key: "events" as const,
    title: "Upcoming events",
    anchor: "events",
    caveat:
      "A targeting list, not a prediction: no chance of hiring anyone is modelled, no buyer has paid for it yet, and the signal lab did not find new events visible 3 to 9 months ahead. Event volume is seasonal, so winter lists are short.",
    buyerTypes: [
      {
        label: "Your own event-services business",
        why: "Organizations that filed a street or park event 2 to 8 weeks ahead, and recurring organizers to approach the season before, each with a public listing to start from.",
      },
      {
        label: "Tent and staging rental",
        why: "Outdoor festivals, markets and races that closed a street or booked a park may need cover and staging.",
      },
      {
        label: "Portable restrooms and handwash",
        why: "Larger street festivals, races and park events are the kind that bring crowds to a block with no facilities.",
      },
      {
        label: "Fencing and barricades",
        why: "A street closure is on file for each CDOT event: closure type and segments are in the list.",
      },
      { label: "Generators and power", why: "Outdoor events with vendors, stages or lighting often need temporary power." },
      { label: "Event security", why: "Larger festivals, parades and races draw crowds the organizer may want to staff." },
    ],
  };
  if (!events) {
    return {
      ...base,
      summary: "The events list has not been generated yet. Run uv run python -m engine.leads.events, then reload.",
      stats: [],
      links: [{ href: "/events", label: "See the list" }],
      emails: [],
    };
  }
  const c = events.counts;
  const lt = (type: string) => events.context.byType.find((r) => r.type === type);
  const fest = lt("Festival");
  const notice =
    fest?.medianDays != null && fest.p25Days != null && fest.p75Days != null
      ? `Festival permits were first reviewed a median ${Math.round(fest.medianDays)} days before the event (middle half ${Math.round(fest.p25Days)} to ${Math.round(fest.p75Days)}).`
      : "";
  const soon = events.recurring.filter((s) => s.daysUntilExpected <= events.windowDays).length;
  const match = events.contactMatch.all;
  const matchText =
    match.suggestionShare === null
      ? ""
      : ` ${pct(match.suggestionShare, 0)} of the ${count(match.organizations)} organizations have a public business listing match.`;
  const summary = `Chicago street and park events through ${events.asOf}: ${count(c.upcomingWithOrganization)} events in the next ${events.windowDays} days name an organization (${count(c.upcoming2To8Weeks)} of them 2 to 8 weeks out), ${count(c.recurring)} recurring series are expected in the next year (${count(c.recurringWithOrganization)} name an organization), and ${count(c.blockParties)} block parties are filed (resident-filed: flyers only). ${notice}${matchText}`;
  const subject = "Free sample: Chicago events with an organizer, 2 to 8 weeks out";
  const paragraphs = [
    "Each week I put together a list of upcoming Chicago street and park events from public City records: the date, location and event type, the organization that filed it (individuals are never listed), and a business listing to start from when one exists.",
    `Right now the list has ${count(c.upcomingWithOrganization)} events in the next ${events.windowDays} days that name an organization, ${count(c.upcoming2To8Weeks)} of them 2 to 8 weeks out, plus ${count(c.recurring)} recurring series with the dates they are expected next year. ${notice} It is a list of who is running events, not of who needs a tent, restroom, fence, generator or guard.`,
  ];
  const body = [
    "Hello [Owner first name],",
    "",
    INTRO,
    "",
    ...paragraphs.flatMap((p) => [p, ""]),
    OFFER,
    "",
    DISCLAIMER_EVENTS,
    "",
    "Would you like me to send the 5-row sample?",
    "",
    footer("events", false),
  ].join("\n");
  return {
    ...base,
    summary,
    stats: [
      { label: `Organizations, next ${events.windowDays} days`, value: count(c.upcomingWithOrganization), hint: `of ${count(c.upcoming)} events on file` },
      { label: "2 to 8 weeks out", value: count(c.upcoming2To8Weeks), hint: "organizations to contact now" },
      { label: `Recurring, expected in ${events.windowDays} days`, value: count(soon), hint: `${count(c.recurring)} in the next ${events.recurringDays}` },
      { label: "Block parties on file", value: count(c.blockParties), hint: "resident-filed; flyers only" },
    ],
    links: [
      { href: "/events", label: "See the list" },
      { href: "/export/events?group=organizations", label: "Organizations CSV", csv: true },
      { href: "/export/events?group=recurring", label: "Recurring CSV", csv: true },
    ],
    emails: [{ key: "events-vendors", label: "Rental and event-service companies", subject, body }],
  };
}
