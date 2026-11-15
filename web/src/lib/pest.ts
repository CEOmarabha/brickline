import "server-only";

import { readFile, stat } from "node:fs/promises";
import path from "node:path";

export const PEST_RANGES = ["week", "28d"] as const;
export type PestRange = (typeof PEST_RANGES)[number];

export interface PestContact {
  placeName: string;
  phone: string | null;
  website: string | null;
  source: string;
  nameMatch: number;
}

export interface PestFinding {
  inspectionId: number;
  date: string;
  inLatestWeek: boolean;
  restaurant: string;
  licenseNo: number;
  address: string;
  addressKey: string;
  communityArea: { id: number; name: string } | null;
  result: string;
  inspectionType: string;
  risk: string | null;
  pestTerms: string[];
  /** True when the record only says "pests" generically (typically entry points or harborage), with no rodent, roach, fly or insect term. */
  pestTermsGeneralOnly: boolean;
  /** Pest-finding inspections at this license in the 730 days before this one. */
  pestFindings2y: number;
  /** The most recent restaurant inspection after the finding, if any. */
  lastInspection: { date: string; result: string; type: string } | null;
  inspectionsSince: number;
  /** Other active-looking licenses (inspected in the last 365 days) with the same normalized name. */
  otherLocations: number;
  otherLocationsPest365: number;
  contact: PestContact | null;
}

export interface PestCompany {
  name: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  email: string | null;
  category: string | null;
  licensedLegalName: string | null;
  source: string;
}

export interface PestContext {
  label: string;
  weeks: number;
  windowStart: string;
  episodes: number;
  perWeek: number | null;
  weeklyMin: number | null;
  weeklyMax: number | null;
  weekly: number[];
  failShare: number | null;
  generalMentionOnlyShare: number | null;
  latestWeekInspections: number;
  typicalWeekInspections: number | null;
  ordinaryInspections: number;
  ordinaryFailShare: number | null;
  areaLocated: number;
  topAreas: { id: number; name: string; episodes: number; share: number | null }[];
}

export interface PestFile {
  generatedAt: string;
  asOf: string;
  definition: string;
  windows: { weekDays: number; backfillDays: number; episodeGapDays: number; historyDays: number; operatorDays: number };
  counts: { latestWeek: number; last28Days: number; withContact: number; pestCompanies: number };
  context: PestContext;
  findings: PestFinding[];
  pestCompanies: PestCompany[];
  attribution: { text: string; overtureRelease: string; contactMatch: string };
}

export function parsePestRange(value: string | string[] | null | undefined): PestRange {
  const v = Array.isArray(value) ? value[0] : value;
  return PEST_RANGES.includes(v as PestRange) ? (v as PestRange) : "week";
}

export function findingsFor(file: PestFile, range: PestRange): PestFinding[] {
  return range === "week" ? file.findings.filter((f) => f.inLatestWeek) : file.findings;
}

let loaded: { mtimeMs: number; file: PestFile } | undefined;

/** The generated pest pilot list, or null when `engine.leads.pest` has not been run. Reloads when the file changes. */
export async function getPest(): Promise<PestFile | null> {
  const file = path.join(process.cwd(), "data", "pest.json");
  try {
    const { mtimeMs } = await stat(file);
    if (loaded?.mtimeMs !== mtimeMs) {
      loaded = { mtimeMs, file: JSON.parse(await readFile(file, "utf8")) as PestFile };
    }
    return loaded.file;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

export interface EmailDraft {
  subject: string;
  body: string;
}

/** Cold email to a pest-control owner offering the free 4-week pilot list. Sender fields are placeholders. */
export function draftPilotEmail(file: PestFile): EmailDraft {
  const perWeek = file.context.perWeek;
  const volume =
    perWeek === null
      ? ""
      : ` Over the last ${file.context.weeks} weeks in the published records, that was about ${perWeek} restaurants a week across Chicago.`;
  const lines = [
    "Hello [Owner first name],",
    "",
    "I'm [Your name], founder of [Your company], a small Chicago company that turns public records into weekly lead lists. We are an independent business, not a government agency, and we are not affiliated with any government office.",
    "",
    `Each week I put together a list of Chicago restaurants whose newest published inspection record shows a new pest finding (rodents, mice, roaches, flies or similar), the first at that restaurant in at least ${file.windows.episodeGapDays} days.${volume} Each row has the address, neighborhood, inspection date, the pest terms in the record, earlier pest findings, whether the restaurant has been re-inspected since, and a business phone or website when a public listing exists.`,
    "",
    "I'd like to send you the list free for 4 weeks. In return I'd ask one thing: tell me which restaurants you contacted and which of them became customers, so I can learn whether the list is useful to a pest-control company. No cost, no contract.",
    "",
    "This is a targeting list built from public records, not a promise of customers, and I don't predict which restaurants will hire anyone. Most restaurants already have a service provider, so the realistic opening is switching or adding service.",
    "",
    "Would you like me to send the first list?",
    "",
    "[Your name]",
    "[Your company]",
    "[Your physical mailing address]",
    "[Your email] · [Your business phone]",
    "",
    `You're receiving this because [Recipient company] appears as a pest-control business in public business listings. If you'd rather not hear from me, reply "unsubscribe" and I will remove you right away and won't email you again.`,
  ];
  return { subject: "Free 4-week list of Chicago restaurants with a new pest finding", body: lines.join("\n") };
}
