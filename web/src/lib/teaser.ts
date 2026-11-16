import "server-only";

import { DEFAULT_FILTERS, queryLeads } from "@/lib/lead-query";
import { count, dateLabel, pct } from "@/lib/format";
import { tradeNoun } from "@/lib/insights";
import { KIND_LABEL, type LeadKindKey } from "@/lib/kinds";
import type { Prospect } from "@/lib/prospects";
import { areaNames, expectedValue, type Lead, type Snapshot, tradeProbability } from "@/lib/snapshot";
import type { Workspace } from "@/lib/workspace";

/** "2837 W Polk St" -> "28xx W Polk St". Keeps everything but the last two digits of the house number. */
export function maskAddress(address: string): string {
  return address.replace(/^(\d+)/, (digits) => `${digits.slice(0, Math.max(0, digits.length - 2))}xx`);
}

export function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

export function nameKey(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

export interface TeaserSample {
  id: string;
  kind: LeadKindKey;
  maskedAddress: string;
  area: string | null;
  title: string;
  signalDate: string;
  chance: number;
}

export interface TeaserAreaTrend {
  id: number;
  name: string;
  violations: { now: number; before: number } | null;
  permits: { now: number; before: number };
}

export interface TeaserCompetitor {
  name: string;
  jobs12m: number;
  jobsPrev12m: number;
  areas: string[];
}

export interface Teaser {
  areaNames: string[];
  openLeads: number;
  actNowLeads: number;
  actNowValue: number;
  byKind: { kind: LeadKindKey; label: string; count: number }[];
  violationLeads: number;
  newViolationLeads: number;
  investorLeads: number;
  samples: TeaserSample[];
  trends: TeaserAreaTrend[];
  competitors: TeaserCompetitor[];
  dataAsOf: string;
  winRate: { individual: number; company: number };
  margin: number;
  /** Historical rate of a permit within a year of a violation in this trade, from the snapshot models. */
  violationModel: { individual: number; episodes: number } | null;
}

/** Targeting comes from the prospect's own trade and areas, never from the viewer's workspace. */
function syntheticWorkspace(p: Prospect): Workspace {
  return {
    id: `prospect-${p.id}`,
    name: p.company,
    businessName: p.company,
    trade: p.trade,
    areas: p.areaIds,
    phone: "",
    mailingAddress: "",
    configured: false,
    signedIn: false,
  };
}

function pickSamples(leads: Lead[], count: number): Lead[] {
  const picked: Lead[] = [];
  const kinds = new Set<string>();
  for (const l of leads) {
    if (picked.length >= count) break;
    if (!kinds.has(l.kind)) {
      kinds.add(l.kind);
      picked.push(l);
    }
  }
  for (const l of leads) {
    if (picked.length >= count) break;
    if (!picked.includes(l)) picked.push(l);
  }
  return picked;
}

export function buildTeaser(snap: Snapshot, p: Prospect): Teaser {
  const ws = syntheticWorkspace(p);
  const names = areaNames(snap);
  const leads = queryLeads(snap, ws, new Map(), DEFAULT_FILTERS);
  const actNow = leads.filter((l) => l.tier === "act_now");

  const kindCounts = new Map<LeadKindKey, number>();
  for (const l of leads) kindCounts.set(l.kind, (kindCounts.get(l.kind) ?? 0) + 1);
  const byKind = [...kindCounts.entries()]
    .map(([kind, n]) => ({ kind, label: KIND_LABEL[kind], count: n }))
    .sort((a, b) => b.count - a.count);

  const areaSet = new Set(p.areaIds);
  const trends = p.areaIds.flatMap((id) => {
    const a = snap.areas.find((x) => x.id === id);
    if (!a) return [];
    const v = a.violations[p.trade];
    return [
      {
        id,
        name: a.name,
        violations: v ? { now: v.last90, before: v.lastYear } : null,
        permits: { now: a.permits[p.trade].last90, before: a.permits[p.trade].lastYear },
      },
    ];
  });

  const self = nameKey(p.company);
  const competitors = snap.competitors[p.trade].contractors
    .filter((c) => nameKey(c.name) !== self && c.areas.some((a) => areaSet.has(a)))
    .sort((a, b) => b.jobs12m - a.jobs12m || a.name.localeCompare(b.name))
    .slice(0, 3)
    .map((c) => ({
      name: c.name,
      jobs12m: c.jobs12m,
      jobsPrev12m: c.jobsPrev12m,
      areas: c.areas.filter((a) => areaSet.has(a)).map((a) => names.get(a) ?? String(a)),
    }));

  const vm = snap.models.violation[p.trade]?.individual;
  const violationLeadList = leads.filter((l) => l.kind === "violation");

  return {
    areaNames: p.areaIds.map((id) => names.get(id)).filter((n): n is string => Boolean(n)),
    openLeads: leads.length,
    actNowLeads: actNow.length,
    actNowValue: actNow.reduce((s, l) => s + expectedValue(l, p.trade, snap), 0),
    byKind,
    violationLeads: violationLeadList.length,
    newViolationLeads: violationLeadList.filter((l) => l.ageDays <= 7).length,
    investorLeads: kindCounts.get("investor_purchase") ?? 0,
    samples: pickSamples(leads, 3).map((l) => ({
      id: l.id,
      kind: l.kind,
      maskedAddress: maskAddress(l.address),
      area: l.communityArea ? (names.get(l.communityArea) ?? null) : null,
      title: l.title,
      signalDate: l.signalDate,
      chance: tradeProbability(l, p.trade, snap),
    })),
    trends,
    competitors,
    dataAsOf: snap.meta.dataAsOf.violations,
    winRate: snap.meta.assumptions.winRate,
    margin: snap.meta.assumptions.margin,
    violationModel: vm ? { individual: vm.p365, episodes: vm.episodes } : null,
  };
}

export interface EmailDraft {
  subject: string;
  body: string;
}

/** "Hello Maria," when the founder saved a contact name; a neutral "Hello," otherwise. Never guesses a name. */
function greeting(contactName: string): string {
  return contactName ? `Hello ${contactName},` : "Hello,";
}

function optOutLine(p: Prospect): string {
  return `You're receiving this because ${p.company} appears as a contractor on public building permits. If you'd rather not hear from me, reply "no thanks" and I won't email you again.`;
}

/**
 * Cold-email draft for a prospect (day 0). Real numbers only; no owner names; CAN-SPAM identity, address and
 * opt-out. `contactName` is the name the founder saved in the pipeline, if any.
 */
export function draftColdEmail(p: Prospect, t: Teaser, contactName = ""): EmailDraft {
  const noun = tradeNoun(p.trade);
  const where = joinNames(t.areaNames);
  const counts: string[] = [];
  if (t.violationLeads > 0) counts.push(`${count(t.violationLeads)} ${noun} repair notices`);
  if (t.investorLeads > 0) counts.push(`${count(t.investorLeads)} investor purchases`);
  const found = counts.length > 0 ? joinNames(counts) : `${count(t.openLeads)} open leads`;
  const nearby = t.areaNames.slice(0, 2);
  const more = t.areaNames.length - nearby.length;
  const subject =
    more > 0
      ? `${found} in ${nearby.join(", ")} and ${more} more ${more === 1 ? "neighborhood" : "neighborhoods"}`
      : `${found} in ${joinNames(nearby)}`;

  const lines = [
    greeting(contactName),
    "",
    `I'm [Your name], founder of Brickline, a small Chicago company that turns public records into weekly lead lists for contractors. We're independent and not affiliated with the City of Chicago.`,
    "",
    `I found ${p.company} in the City's public building-permit data: ${count(p.jobs12m)} ${noun} permits in the last 12 months${
      p.violationDrivenJobs > 0
        ? `, ${count(p.violationDrivenJobs)} of them at addresses with a ${noun} violation on record in the year before`
        : ""
    }.`,
    "",
    `For the neighborhoods where you work most (${where}), city and county records through ${dateLabel(t.dataAsOf)} show ${found}${
      t.newViolationLeads > 0 ? `, ${count(t.newViolationLeads)} of the repair notices from the last 7 days` : ""
    }. Each lead comes with its evidence and how often similar signals have led to a permitted job.`,
  ];
  if (t.violationModel) {
    lines.push(
      "",
      `For context: across Chicago's records, ${pct(t.violationModel.individual)} of individual owners cited for a ${noun} violation pulled a ${noun} permit within a year (${count(t.violationModel.episodes)} citations). Permits miss unpermitted work, so this is a floor.`,
    );
  }
  lines.push(
    "",
    `I put together a one-page summary for ${p.company} with these counts, neighborhood trends and three sample leads (addresses partly hidden). Would you like me to send it?`,
    "",
    "I'm offering a free first month to a few Chicago contractors in exchange for weekly feedback on which leads were useful.",
    "",
    "[Your name]",
    "Brickline",
    "[your mailing address]",
    "",
    optOutLine(p),
  );
  return { subject, body: lines.join("\n") };
}

/** What a sample lead is, in words that match the letters the app drafts (a violation is a "repair notice"). */
function sampleWhat(s: TeaserSample, noun: string): string {
  const when = dateLabel(s.signalDate);
  return s.kind === "violation"
    ? `a ${noun} repair notice dated ${when}`
    : `${s.title.charAt(0).toLowerCase()}${s.title.slice(1)}, dated ${when}`;
}

/**
 * Follow-up emails of the playbook's day 0/4/10 sequence (section 3). Day 4 brings one new, real fact (a masked
 * sample lead from the teaser with its historical chance of work); day 10 closes the loop. Both keep the sender
 * identity, address placeholder and opt-out, never use "Re:" in the subject, and never name property owners.
 */
export function draftFollowUpEmail(p: Prospect, t: Teaser, step: 2 | 3, contactName = ""): EmailDraft {
  const noun = tradeNoun(p.trade);
  const where = joinNames(t.areaNames) || "Chicago";
  const signature = ["[Your name]", "Brickline", "[your mailing address]"];
  const footer = [optOutLine(p), "Brickline is independent and not affiliated with the City of Chicago."];

  if (step === 2) {
    const sample = t.samples.find((s) => s.kind === "violation") ?? t.samples[0];
    const fact = sample
      ? [
          `Here is one example from the list for ${p.company}'s neighborhoods: ${sample.maskedAddress}${sample.area ? `, ${sample.area}` : ""}, ${sampleWhat(sample, noun)}. Its historical chance of work is ${pct(sample.chance)}, a floor because permits miss unpermitted work. I've hidden the last two digits of the house number; the weekly list has the full address, the evidence and a drafted letter for each lead.`,
        ]
      : [
          `As of ${dateLabel(t.dataAsOf)}, the records show ${count(t.openLeads)} open leads in ${where}, with the evidence and the historical chance of work for each.`,
        ];
    return {
      subject: sample
        ? `Following up: a sample ${noun} lead${sample.area ? ` in ${sample.area}` : ""}`
        : `Following up: ${noun} leads for ${p.company}`,
      body: [
        greeting(contactName),
        "",
        `I wrote to you recently about Brickline, a small Chicago company that turns public City and county records into weekly lead lists for contractors.`,
        "",
        ...fact,
        "",
        `I'm offering a free first month to a few Chicago contractors in exchange for weekly feedback on which leads were useful. Would you like the one-page summary for ${p.company}?`,
        "",
        ...signature,
        "",
        ...footer,
      ].join("\n"),
    };
  }

  return {
    subject: `Closing the loop on ${noun} leads for ${p.company}`,
    body: [
      greeting(contactName),
      "",
      `I'll stop here so I don't fill your inbox. I've written to you before about the weekly list of ${noun} leads that Brickline builds from public records for ${p.company}'s neighborhoods (${where}).`,
      "",
      `If lead flow isn't a problem right now, no worries. If it ever is, here is what I'd send: a weekly list of properties in ${where === "Chicago" ? where : "those neighborhoods"} with the evidence for each, how often similar signals have led to a permitted job, and a drafted letter, with the first month free. If you'd like the one-page summary, just reply "send it".`,
      "",
      ...signature,
      "",
      ...footer,
    ].join("\n"),
  };
}

