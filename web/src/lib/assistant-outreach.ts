import "server-only";

import type { LeadOutreachSummary, ToolContext } from "@/lib/assistant-tools";
import { getLeadContacts, getProspectContacts, type ContactSuggestions } from "@/lib/contacts";
import { count, dateLabel, pct } from "@/lib/format";
import { tradeNoun } from "@/lib/insights";
import { MIN_DECIDED } from "@/lib/outcomes";
import { draftOutreach } from "@/lib/outreach";
import {
  type DealSummary,
  FEE_MODEL_LABEL,
  FEE_MODELS,
  isDue,
  MAX_SEQUENCE_STEP,
  PROSPECT_STATUS_LABEL,
  PROSPECT_STATUSES,
  summarizeDeals,
  todayChicago,
  type ProspectStatus,
} from "@/lib/pipeline";
import { getPipeline, getPipelineRow, getRecentPipelineEvents, type PipelineRow } from "@/lib/prospect-pipeline";
import { getProspects, type Prospect } from "@/lib/prospects";
import { areaNames, type Lead, tradeProbability } from "@/lib/snapshot";
import { buildTeaser, draftColdEmail, draftFollowUpEmail, joinNames, nameKey } from "@/lib/teaser";

/*
 * Outreach tools for the founder's own sales pipeline. Everything here is read-only and owner-scoped: pipeline rows
 * are read with `ctx.owner` (the signed-in viewer, never the client workspace). Results are sent to the AI provider,
 * so they never carry phone numbers, email addresses or free-text notes, only yes/no flags and a link to the page
 * where the founder sees them. Lead drafts and briefs also leave out property owners' and buyers' names and mailing
 * addresses: placeholders stand in for them, and the lead page fills them in.
 */

type Input = Record<string, unknown>;
const str = (v: unknown) => (typeof v === "string" ? v : undefined);

const NEEDS_SIGN_IN = { error: "Sign in required: the outreach tools read your private prospect pipeline." };
const DAY_LABEL = ["Day 0", "Day 4", "Day 10"];
const DUE_LIMIT = 25;
const EVENT_LIMIT = 8;
/** Statuses where the prospect has engaged or is a customer: the cold sequence no longer applies. */
const ENGAGED: readonly ProspectStatus[] = ["replied", "meeting", "pilot", "paying"];

const prospectLink = (id: string) => `/prospects/${encodeURIComponent(id)}`;
const leadLink = (id: string) => `/leads/${encodeURIComponent(id)}`;

const OWNER_NAME = "[owner name]";
const BUYER_NAME = "[buyer company]";
const OWNER_COMPANY = "[owner company]";

/** The lead with the owner's and buyer's names swapped for placeholders and the owner's mailing address removed. */
function withoutNames(lead: Lead): Lead {
  const owner = { ...lead.owner, name: lead.owner.name ? OWNER_NAME : null, mailing: null };
  return lead.kind === "investor_purchase"
    ? { ...lead, owner, buyer: { ...lead.buyer, name: lead.buyer.name ? BUYER_NAME : null } }
    : { ...lead, owner };
}

/** A saved contact name is used in greetings only if it really is a name (not a pasted phone number or email). */
function usableContactName(name: string): string {
  const n = name.trim();
  if (n === "" || n.length > 80 || /@|https?:|www\./i.test(n) || (n.match(/\d/g) ?? []).length >= 5) return "";
  return n;
}

function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((Date.parse(`${toIso}T00:00:00Z`) - Date.parse(`${fromIso}T00:00:00Z`)) / 86_400_000);
}

type NextStep = { kind: "email"; step: number } | { kind: "call" } | { kind: "record_outcome" } | { kind: "none" };

/** Playbook sections 3 and 5b: emails go out at day 0, 4 and 10; after the third with no reply, call the business line. */
function nextStepFor(status: ProspectStatus, emailsSent: number): NextStep {
  if (status === "paying" || status === "not_interested") return { kind: "none" };
  if (status === "replied" || status === "meeting" || status === "pilot") return { kind: "record_outcome" };
  return emailsSent < MAX_SEQUENCE_STEP ? { kind: "email", step: emailsSent + 1 } : { kind: "call" };
}

function describeStep(s: NextStep): string {
  switch (s.kind) {
    case "email":
      return `Send email ${s.step} of ${MAX_SEQUENCE_STEP} (${DAY_LABEL[s.step - 1]})`;
    case "call":
      return "Call their business line by hand (weekdays 8:00-17:00 Chicago time): all three emails went out with no reply";
    case "record_outcome":
      return "Record the outcome: update the status and notes on their page";
    case "none":
      return "Nothing: this prospect is closed";
  }
}

/** Yes/no flags only. The values are on the prospect's page, which the founder opens himself. */
function contactFlags(row: PipelineRow | undefined, suggestions: ContactSuggestions | null) {
  return {
    phone_on_file: Boolean(row?.phone.trim()),
    email_on_file: Boolean(row?.email.trim()),
    phone_suggested_from_public_sources: Boolean(suggestions?.phones.length),
    email_suggested_from_public_sources: Boolean(suggestions?.emails.length),
  };
}

function eventKind(note: string): { kind: string; email_number?: number } {
  const email = /^Email (\d) of \d sent/.exec(note);
  if (email) return { kind: "email_sent", email_number: Number(email[1]) };
  if (note.startsWith("Status:")) return { kind: "status_change" };
  if (note.startsWith("Contact details updated")) return { kind: "contact_details_updated" };
  if (note.startsWith("Notes updated")) return { kind: "notes_updated" };
  if (note.startsWith("Monthly value") || note.startsWith("Fee model")) return { kind: "deal_terms_updated" };
  if (note.startsWith("Follow-up")) return { kind: "follow_up_changed" };
  return { kind: "added_to_pipeline" };
}

export interface DealValueSummary {
  prospects: number;
  with_monthly_value: number;
  total_monthly_value_usd: number | null;
  by_fee_model: Record<string, number>;
}

function dealValueSummary(s: DealSummary): DealValueSummary {
  return {
    prospects: s.count,
    with_monthly_value: s.withValue,
    total_monthly_value_usd: s.withValue > 0 ? s.totalMonthlyUsd : null,
    by_fee_model: Object.fromEntries(FEE_MODELS.map((m) => [FEE_MODEL_LABEL[m], s.byFeeModel[m]])),
  };
}

export interface OutreachDueRow {
  prospect_id: string;
  company: string;
  trade: string;
  status: string;
  emails_sent: number;
  next_follow_up: string;
  days_overdue: number;
  next_step: string;
  link: string;
  phone_on_file: boolean;
  email_on_file: boolean;
  has_notes: boolean;
}

export interface OutreachStatusResult {
  today: string;
  prospect_pipeline: {
    prospects_total: number;
    prospects_tracked: number;
    counts_by_status: Record<string, number>;
    deal_value: {
      note: string;
      paying: DealValueSummary;
      pilot: DealValueSummary;
    };
    due_total: number;
    due: OutreachDueRow[];
    recent_events: { date: string; kind: string; email_number?: number; status: string; company: string; link: string }[];
    contact_details_note: string;
  };
  lead_outreach: LeadOutreachSummary;
}

/** The founder's prospect pipeline (owner-scoped) plus this workspace's lead outreach, in one call. */
export async function outreachStatus(
  ctx: ToolContext,
  leadOutreach: LeadOutreachSummary,
): Promise<OutreachStatusResult | { error: string }> {
  const owner = ctx.owner;
  if (!owner) return NEEDS_SIGN_IN;
  const [file, pipeline, events] = await Promise.all([
    getProspects(),
    getPipeline(owner),
    getRecentPipelineEvents(owner, 40),
  ]);
  const today = todayChicago();
  const byId = new Map(file.prospects.map((p) => [p.id, p]));
  const tradeLabel = (p: Prospect) => ctx.snap.trades[p.trade].label;

  const counts = new Map<ProspectStatus, number>(PROSPECT_STATUSES.map((s) => [s, 0]));
  let tracked = 0;
  const due: { p: Prospect; row: PipelineRow }[] = [];
  for (const p of file.prospects) {
    const row = pipeline.get(p.id);
    const status = row?.status ?? "not_contacted";
    counts.set(status, (counts.get(status) ?? 0) + 1);
    if (row) tracked++;
    if (row && isDue(row, today)) due.push({ p, row });
  }
  const deals = summarizeDeals(file.prospects.map((p) => pipeline.get(p.id)));
  due.sort((a, b) => (a.row.nextFollowUp ?? "").localeCompare(b.row.nextFollowUp ?? "") || a.p.id.localeCompare(b.p.id));

  const dueRows = await Promise.all(
    due.slice(0, DUE_LIMIT).map(async ({ p, row }): Promise<OutreachDueRow> => {
      const flags = contactFlags(row, await getProspectContacts(p.id));
      return {
        prospect_id: p.id,
        company: p.company,
        trade: tradeLabel(p),
        status: PROSPECT_STATUS_LABEL[row.status],
        emails_sent: row.sequenceStep,
        next_follow_up: row.nextFollowUp as string,
        days_overdue: Math.max(0, daysBetween(row.nextFollowUp as string, today)),
        next_step: describeStep(nextStepFor(row.status, row.sequenceStep)),
        link: prospectLink(p.id),
        phone_on_file: flags.phone_on_file,
        email_on_file: flags.email_on_file,
        has_notes: row.notes.trim() !== "",
      };
    }),
  );

  const recent = events
    .flatMap((e) => {
      const p = byId.get(e.prospectId);
      return p
        ? [
            {
              date: todayChicago(e.createdAt),
              ...eventKind(e.note),
              status: PROSPECT_STATUS_LABEL[e.status],
              company: p.company,
              link: prospectLink(p.id),
            },
          ]
        : [];
    })
    .slice(0, EVENT_LIMIT);

  return {
    today,
    prospect_pipeline: {
      prospects_total: file.prospects.length,
      prospects_tracked: tracked,
      counts_by_status: Object.fromEntries(PROSPECT_STATUSES.map((s) => [PROSPECT_STATUS_LABEL[s], counts.get(s) ?? 0])),
      deal_value: {
        note: "Monthly values are what the founder entered for Paying and Pilot prospects; nothing is estimated, and the totals count only prospects with a value entered. No contact details.",
        paying: dealValueSummary(deals.paying),
        pilot: dealValueSummary(deals.pilot),
      },
      due_total: due.length,
      due: dueRows,
      recent_events: recent,
      contact_details_note:
        "Phone numbers, email addresses and notes are not included here. Open each prospect's link to see them; phone_on_file, email_on_file and has_notes say whether they exist.",
    },
    lead_outreach: leadOutreach,
  };
}

type Resolved = { prospect: Prospect } | { error: string; candidates?: { prospect_id: string; company: string; trade: string }[] };

/** An exact prospect id, else a company name that matches exactly one prospect. */
async function resolveProspect(raw: string): Promise<Resolved> {
  const q = raw.trim().slice(0, 120);
  const file = await getProspects();
  const byId = file.prospects.find((p) => p.id === q);
  if (byId) return { prospect: byId };
  const key = nameKey(q);
  const unknown = {
    error: "No prospect with that id or company name. Use a prospect_id from outreach_status or a /prospects/<id> link.",
  };
  if (key.length < 3) return unknown;
  const exact = file.prospects.filter((p) => nameKey(p.company) === key);
  const hits = exact.length > 0 ? exact : file.prospects.filter((p) => nameKey(p.company).includes(key));
  if (hits.length === 1) return { prospect: hits[0] };
  if (hits.length === 0) return unknown;
  return {
    error: "More than one prospect matches that name. Ask the founder which one, then pass its prospect_id.",
    candidates: hits.slice(0, 6).map((p) => ({ prospect_id: p.id, company: p.company, trade: p.trade })),
  };
}

function pipelineFacts(row: PipelineRow | undefined, suggestions: ContactSuggestions | null, id: string) {
  return {
    status: PROSPECT_STATUS_LABEL[row?.status ?? "not_contacted"],
    emails_sent: row?.sequenceStep ?? 0,
    next_follow_up: row?.nextFollowUp ?? null,
    contact_name_saved: usableContactName(row?.contactName ?? "") !== "",
    ...contactFlags(row, suggestions),
    has_notes: Boolean(row?.notes.trim()),
    see_contact_details_at: prospectLink(id),
  };
}

const EMAIL_RULES = [
  "You review and send this yourself from your own mailbox; the assistant never sends email.",
  "Fill in [Your name] and [your mailing address] (a real postal address is required). Keep the opt-out line, and honor any opt-out the same day by marking the prospect Not interested.",
  "Business contacts only: use a business email you found, never a guessed address. The subject must not start with Re: or Fwd:.",
  "No property owner names: sample addresses stay masked.",
  "Say plainly that you found them in public permit records. Rates are historical floors, so don't promise jobs or a close rate.",
];

async function draftProspectEmail(ctx: ToolContext, owner: string, idInput: string, stepInput: unknown) {
  const resolved = await resolveProspect(idInput);
  if ("error" in resolved) return resolved;
  const p = resolved.prospect;
  const explicitStep = stepInput === undefined ? undefined : Number(stepInput);
  if (
    explicitStep !== undefined &&
    !(typeof stepInput === "number" && Number.isInteger(explicitStep) && explicitStep >= 1 && explicitStep <= MAX_SEQUENCE_STEP)
  ) {
    return { error: "step must be 1, 2 or 3" };
  }

  const [row, suggestions] = await Promise.all([getPipelineRow(owner, p.id), getProspectContacts(p.id)]);
  const status = row?.status ?? "not_contacted";
  const sent = row?.sequenceStep ?? 0;
  const link = prospectLink(p.id);
  if (status === "not_interested") {
    return {
      refused: true,
      reason:
        "This prospect is marked Not interested. Don't email them again; if they asked to opt out, that request must be honored.",
      link,
    };
  }

  let step: number;
  if (explicitStep === undefined) {
    if (ENGAGED.includes(status)) {
      return {
        error: `Status is ${PROSPECT_STATUS_LABEL[status]}, so no cold-email step applies. Write a personal reply instead, or pass step if the founder really wants a draft.`,
        link,
      };
    }
    if (sent >= MAX_SEQUENCE_STEP) {
      return {
        error:
          "All three emails are already logged. The playbook says not to email again for 90 days; the next step is a call to their business line (use call_brief). Pass step to see a draft anyway.",
        link,
      };
    }
    step = sent + 1;
  } else {
    step = explicitStep;
  }

  const warnings: string[] = [];
  if (ENGAGED.includes(status)) {
    warnings.push(`Status is ${PROSPECT_STATUS_LABEL[status]}: the cold sequence is for contacts who haven't replied.`);
  }
  if (step <= sent) warnings.push(`Email ${step} is already logged as sent on their page.`);
  if (step > sent + 1) warnings.push(`Email ${sent + 1} isn't logged yet; the sequence goes in order (day 0, 4, 10).`);
  if (!row?.email.trim()) {
    warnings.push(
      suggestions?.emails.length
        ? "No email is saved yet. Public-source suggestions are on their page: verify one before using it."
        : "No business email is saved. Find one by hand (their website or the state registry); never guess an address.",
    );
  }
  const savedName = row?.contactName ?? "";
  const name = usableContactName(savedName);
  if (savedName.trim() !== "" && name === "") {
    warnings.push("The saved contact name looks like a phone number or email, so the greeting is neutral. Fix it on their page.");
  }

  const teaser = buildTeaser(ctx.snap, p);
  const email = step === 1 ? draftColdEmail(p, teaser, name) : draftFollowUpEmail(p, teaser, step as 2 | 3, name);
  const compliance = [...EMAIL_RULES];
  if (step === 1) compliance.push("Send from a separate, warmed-up sending domain, 15-20 new contractors a day at most.");
  if (step === 3) compliance.push("This is the last touch: if there is no reply, don't email again for 90 days.");

  return {
    channel: "email",
    step,
    cadence_day: DAY_LABEL[step - 1],
    subject: email.subject,
    body: email.body,
    greeting_uses_saved_contact_name: name !== "",
    compliance_notes: compliance,
    warnings,
    after_sending: `Press "I sent email ${step}" on the prospect page so the follow-up date updates.`,
    for: { prospect_id: p.id, company: p.company, trade: ctx.snap.trades[p.trade].label, link },
    pipeline: pipelineFacts(row, suggestions, p.id),
    requires_human_send: true,
  };
}

async function draftLeadEmail(ctx: ToolContext, leadId: string) {
  const { snap, ws } = ctx;
  const lead = snap.leads.find((l) => l.id === leadId);
  if (!lead) return { error: "No lead with that id in this week's data" };
  const area = lead.communityArea ? (areaNames(snap).get(lead.communityArea) ?? null) : null;
  // The business phone and mailing address, and the owner's or buyer's name, stay placeholders so they are not sent
  // to the AI provider; the draft on the lead page fills in the real values.
  const draft = draftOutreach(withoutNames(lead), { ...ws, phone: "", mailingAddress: "" }, snap, area);
  const contacts = await getLeadContacts(lead.id);
  const link = leadLink(lead.id);
  return {
    channel: draft.channel,
    subject: draft.subject ?? null,
    body: draft.body,
    compliance_notes: [
      ...draft.compliance,
      draft.channel === "letter"
        ? "This is a letter: print it, sign it and mail it yourself. The assistant sends nothing."
        : "Send it yourself from your own mailbox to a business contact you found. The assistant sends nothing.",
    ],
    warnings: tradeWarning(lead, ctx),
    placeholders_note: `[phone], [your mailing address], ${OWNER_NAME} and ${BUYER_NAME} are placeholders so your details and the owner's or buyer's name aren't sent to the AI provider. The draft on the lead page (${link}) fills them in from Settings and the public record.`,
    for: { lead_id: lead.id, address: lead.address, link, owner_type: lead.owner.type },
    recipient: {
      mailing_address_on_file: Boolean(lead.owner.mailing),
      phone_on_file: Boolean(contacts?.phones.length),
      email_on_file: Boolean(contacts?.emails.length),
      note: "Phone and email flags mean a suggestion from public sources exists; see them on the lead page.",
      see_contact_details_at: link,
    },
    requires_human_send: true,
  };
}

export async function draftEmail(input: Input, ctx: ToolContext) {
  if (!ctx.owner) return NEEDS_SIGN_IN;
  const prospectId = str(input.prospect_id);
  const leadId = str(input.lead_id);
  if (prospectId && leadId) return { error: "Pass either prospect_id or lead_id, not both" };
  if (prospectId) return draftProspectEmail(ctx, ctx.owner, prospectId, input.step ?? undefined);
  if (leadId) return draftLeadEmail(ctx, leadId);
  return { error: "Pass prospect_id (a contractor prospect) or lead_id (a lead in this workspace)" };
}

const CALL_RULES = [
  "You dial by hand, to the company's published business line. No autodialer, no prerecorded or AI-voice calls; the assistant never places calls.",
  "No texts without prior express written consent; the playbook's rule is not to text at all.",
  "Call weekdays between 8:00 and 17:00 Chicago time (the legal window is 8:00 to 21:00; the playbook is stricter).",
  "If the number could be a personal line (for example a sole proprietor), check the National Do Not Call Registry first.",
  "If they say stop or don't call again: apologize, say yes, record it the same day, and never call again.",
  "Never imply City affiliation: you are an independent company. Rates are historical floors, so never promise jobs or a close rate.",
];

function prospectCallBrief(ctx: ToolContext, p: Prospect, row: PipelineRow | undefined, suggestions: ContactSuggestions | null) {
  const t = buildTeaser(ctx.snap, p);
  const noun = tradeNoun(p.trade);
  const where = joinNames(t.areaNames) || "Chicago";
  const sent = row?.sequenceStep ?? 0;
  const status = row?.status ?? "not_contacted";
  const name = usableContactName(row?.contactName ?? "");
  const flags = contactFlags(row, suggestions);
  const link = prospectLink(p.id);

  const found: string[] = [];
  if (t.violationLeads > 0) {
    found.push(
      `${count(t.violationLeads)} ${noun} repair notices${t.newViolationLeads > 0 ? ` (${count(t.newViolationLeads)} from the last 7 days)` : ""}`,
    );
  }
  if (t.investorLeads > 0) found.push(`${count(t.investorLeads)} investor purchases`);
  const rate = t.violationModel
    ? `Across Chicago, ${pct(t.violationModel.individual)} of individual owners cited for a ${noun} violation pulled a ${noun} permit within a year (${count(t.violationModel.episodes)} citations). That is a historical rate and a floor, not a promise.`
    : null;
  const reason = [
    found.length > 0
      ? `City and county records through ${dateLabel(t.dataAsOf)} show ${joinNames(found)} in ${where}.`
      : `City and county records through ${dateLabel(t.dataAsOf)} show ${count(t.openLeads)} open leads in ${where}.`,
    rate,
    `${p.company} pulled ${count(p.jobs12m)} ${noun} permits in the last 12 months (${count(p.jobsPrev12m)} in the 12 months before)${
      p.violationDrivenJobs > 0
        ? `, ${count(p.violationDrivenJobs)} of them at addresses with a ${noun} violation on record in the year before`
        : ""
    }.`,
  ].filter((s): s is string => s !== null);

  const before: string[] = [];
  if (flags.phone_on_file) before.push(`A phone number is saved on their page (${link}). Confirm it is the company's published business line.`);
  else if (flags.phone_suggested_from_public_sources) {
    before.push(`No phone is saved; a public-source suggestion is on their page (${link}). Verify it is the company's business line (website or Google profile) before dialing.`);
  } else {
    before.push(`No phone is saved. Find the published business line (their website, Google Business Profile or the state registry, 10 minutes at most), save it on their page (${link}), or skip this company.`);
  }
  if (sent < 2) {
    before.push(`The playbook calls after the day-4 email; you have logged ${sent} of ${MAX_SEQUENCE_STEP} emails.`);
  }
  if (ENGAGED.includes(status)) {
    before.push(`Status is ${PROSPECT_STATUS_LABEL[status]}: they already know who you are, so skip the cold opener and refer to your last conversation.`);
  }

  const violationQuestion =
    p.violationDrivenJobs > 0
      ? `Some of your recent ${noun} jobs were at addresses that had a ${noun} violation on record. How do you usually hear about those owners?`
      : `Do you take ${noun} jobs that start with a city repair notice? How do you reach those owners?`;

  return {
    for: { prospect_id: p.id, company: p.company, trade: ctx.snap.trades[p.trade].label, link },
    pipeline: pipelineFacts(row, suggestions, p.id),
    facts: {
      areas: t.areaNames,
      data_as_of: t.dataAsOf,
      open_leads: t.openLeads,
      repair_notice_leads: t.violationLeads,
      repair_notice_leads_last_7_days: t.newViolationLeads,
      investor_purchase_leads: t.investorLeads,
      historical_permit_rate_after_violation: t.violationModel ? pct(t.violationModel.individual) : null,
      violation_episodes_behind_rate: t.violationModel?.episodes ?? null,
      jobs_last_12_months: p.jobs12m,
      jobs_prior_12_months: p.jobsPrev12m,
      jobs_at_addresses_with_prior_violation: p.violationDrivenJobs,
    },
    before_you_dial: before,
    opening_statement: `Hi, is this ${name || "[Name]"}? This is [Your name] with Brickline here in Chicago. ${
      ENGAGED.includes(status)
        ? "Thanks for getting back to me. I wanted to follow up on the phone. Do you have a few minutes?"
        : `I'm not selling a lead-gen subscription over the phone. ${
            sent >= 1 ? "I emailed you recently. " : ""
          }I found ${p.company} in the city's public permit records and built a weekly list of properties in ${where} with ${noun} repair notices. Do you have 30 seconds for me to tell you what's in it?`
    }`,
    reason_for_calling: reason,
    if_they_say_yes: `${
      t.violationLeads > 0
        ? `There are ${count(t.violationLeads)} ${noun} repair notices in ${where} right now${t.newViolationLeads > 0 ? `, ${count(t.newViolationLeads)} from the last 7 days` : ""}. `
        : ""
    }${rate ? `${rate} ` : ""}I'm giving a few Chicago contractors the first month free if they tell me which leads were any good. Can I send you the one-page summary, and could we talk for 15 minutes on [day]?`,
    if_busy_or_no: "Understood. Is there a better time, or should I take you off my list?",
    discovery_questions: [
      `How do you find most of your ${noun} jobs today: referrals, ads, or something else?`,
      violationQuestion,
      `Which neighborhoods do you most want more work in right now? (Their permits are concentrated in ${where}.)`,
      "How full is your schedule over the next six to eight weeks?",
      "Who handles estimates and marketing at your company, and is email, paper or a phone call best for you?",
    ],
    likely_objections: [
      {
        objection: "I already get leads from Angi / HomeAdvisor / Thumbtack.",
        honest_answer:
          "Those sell the same inquiry to several contractors. These aren't inquiries: they are properties with a city repair order or a recent complaint and no permit issued yet. Keep Angi; this is a second source, and you contact the owner first. Don't claim the data is exclusive: the records are public. Brickline's edge is that it's already collated, ranked and drafted.",
      },
      {
        objection: "I get enough work.",
        honest_answer: `Then you may not need it. Your permits show ${count(p.jobs12m)} jobs in the last 12 months versus ${count(p.jobsPrev12m)} the year before. If you're full, say so and I'll check back next season. Don't push.`,
      },
      {
        objection: "How do I know these convert?",
        honest_answer: `${rate ? `${rate} ` : ""}Each lead shows the historical rate and the number of cases behind it, and they're floors because permits miss unpermitted work. During the pilot you mark each lead won or lost, and after ${MIN_DECIDED} decided leads the Results page replaces my averages with your own measured close rate. Never promise a close rate.`,
      },
      {
        objection: "I don't do computers / I don't read email.",
        honest_answer: "The weekly report prints on paper, and the letters print ready to sign and mail. I can walk you through it on the phone once.",
      },
      {
        objection: "Is this legal? Are you the City?",
        honest_answer: "Brickline is independent and not affiliated with the City. Everything comes from public records, and letters never imitate a City notice.",
      },
      {
        objection: "What does it cost?",
        honest_answer:
          "The first month is free in exchange for weekly feedback and outcome data. Months 2 to 3 are a pilot price of $250 to $500 a month, then $750 to $1,500 a month depending on volume and markets. Those are planning ranges from the sales playbook, not a final quote; the cancellation terms go in the pilot agreement.",
      },
      {
        objection: "Send me something.",
        honest_answer: "Send the printed one-page summary from their prospect page and propose a time. Never send property owner names before they are a client.",
      },
    ],
    suggested_next_step:
      "The goal of the call is a yes to the one-page summary or a 15-minute meeting, not a sale. Offer to send the summary (print it from their prospect page) and propose a day for 15 minutes. Afterward, record the outcome on their page (status, notes, next follow-up date).",
    voicemail:
      "At most one voicemail per contact: your name, Brickline, one sentence about why you called, your number, and \"reply to my email or call back\".",
    compliance_reminders: [...CALL_RULES, "No property owner names in prospecting calls."],
    requires_human_dial: true,
  };
}

/** Per-kind spoken reason for the call; mirrors the letters in outreach.ts, including what must never be mentioned. */
function leadPitch(lead: Lead, noun: string, business: string, where: string) {
  const none = { mustNotMention: [] as string[] };
  switch (lead.kind) {
    case "violation":
      return {
        reason: `I'm calling about ${lead.address}. Public City of Chicago building records show a ${noun} repair notice there dated ${dateLabel(lead.signalDate)}. If you're planning that work, ${business} handles ${noun} repairs and the permit paperwork, and I can offer a free inspection and a written estimate.`,
        ...none,
      };
    case "investor_purchase":
      return {
        reason: `Congratulations on picking up ${lead.address}. ${business} works with investors on ${lead.segment} rehabs${where}. If ${noun} work is planned there, I can walk it with you and send a written quote.`,
        ...none,
      };
    case "porch_request":
      return {
        reason: `${business} is offering owners a free porch assessment at ${lead.address}: I'd look at the porch, tell you plainly what it needs (including nothing), and send a written estimate, and we handle the permit paperwork too.`,
        mustNotMention: ["the 311 report or any complaint", "the property's records"],
      };
    case "vacant":
      return {
        reason: `${business} helps owners of Chicago properties${where} secure, repair and renovate buildings that aren't in regular use. I can walk ${lead.address} and give you a written estimate at no cost.`,
        mustNotMention: ["the 311 report or any complaint", "the property's records", "that the building was reported vacant"],
      };
    case "closed_restaurant":
      return {
        reason: `${business} prepares and builds out commercial space for the next operator${where}: clean-out, coordination of kitchen, hood, plumbing and electrical rough-in, and permit paperwork. If the space at ${lead.address} is already spoken for, I'll leave you be.`,
        mustNotMention: ["the restaurant", "its closing", "any inspection or public record"],
      };
    default:
      return {
        reason: `${business} is offering owners a free exterior check of ${lead.address}: I'd look at the property, tell you plainly what needs work and what doesn't, and send a written estimate, and we handle the permit paperwork too.`,
        mustNotMention: ["the 311 report or any complaint", "the property's records"],
      };
  }
}

/** Leads are listed for every trade; a lead outside this workspace's trade gets a warning, not a silent pitch. */
function tradeWarning(lead: Lead, ctx: ToolContext): string[] {
  return lead.trades.includes(ctx.ws.trade)
    ? []
    : [
        `This lead isn't one of this workspace's trade (${ctx.snap.trades[ctx.ws.trade].label}); the chance of work shown is for that trade and the pitch may not fit the business.`,
      ];
}

async function leadCallBrief(ctx: ToolContext, leadId: string) {
  const { snap, ws } = ctx;
  const lead = snap.leads.find((l) => l.id === leadId);
  if (!lead) return { error: "No lead with that id in this week's data" };
  const link = leadLink(lead.id);
  const individual = lead.owner.type !== "company";

  const contacts = await getLeadContacts(lead.id);
  const business = ws.businessName || "[Your company]";
  const noun = tradeNoun(ws.trade);
  const area = lead.communityArea ? (areaNames(snap).get(lead.communityArea) ?? null) : null;
  const where = area ? ` in ${area}` : "";
  const company = !individual && lead.owner.name ? OWNER_COMPANY : null;
  const pitch = leadPitch(lead, noun, business, where);
  const phoneOnFile = Boolean(contacts?.phones.length);

  return {
    for: {
      lead_id: lead.id,
      address: lead.address,
      link,
      owner_type: lead.owner.type,
      owner_name_on_file: Boolean(lead.owner.name),
      ...(company ? { placeholders_note: `${OWNER_COMPANY} stands for the company's name, which is on the lead page.` } : {}),
    },
    facts: {
      address: lead.address,
      neighborhood: area,
      signal: lead.title,
      signal_date: lead.signalDate,
      days_ago: lead.ageDays,
      fits_workspace_trade: lead.trades.includes(ws.trade),
      chance_of_work: pct(tradeProbability(lead, ws.trade, snap)),
      basis: lead.probabilityBasis,
    },
    warnings: tradeWarning(lead, ctx),
    contact: {
      phone_on_file: phoneOnFile,
      email_on_file: Boolean(contacts?.emails.length),
      note: individual
        ? "Individual owner: public records carry no phone. Use a number from a skip-trace provider whose terms allow marketing, scrubbed against the National Do Not Call Registry and our opt-out list within the last 31 days (docs/14 section 8)."
        : "Flags mean a suggestion from public sources exists. Find and verify the company's published business line on the lead page.",
      see_contact_details_at: link,
    },
    before_you_dial: individual
      ? [
          "Only call a number that came from a provider whose terms allow marketing and passed a Do Not Call scrub in the last 31 days; skip any number on our opt-out list.",
          "Dial by hand between 9:00 and 20:00 Chicago time. No autodialer, no recorded or AI voice; texts the same way, one at a time.",
          "Open with your name, company and why you are calling, then ask if they want to continue (Illinois Telephone Solicitations Act). Stop and add them to the opt-out list if they say no.",
        ]
      : [
      phoneOnFile
        ? `A public-source phone suggestion is on the lead page (${link}). Verify it is the company's business line (website or Google profile) first.`
        : `No phone suggestion exists. Find the company's published business line (website, Google Business Profile or the state registry), or send mail instead.`,
      company ? `Ask for someone who handles properties at ${company}.` : "The owner's name isn't in the records: ask for whoever handles the property.",
        ],
    must_not_mention: [...pitch.mustNotMention, "any City affiliation"],
    opening_statement: individual
      ? `Hi, this is [Your name] with ${business}, a Chicago ${snap.trades[ws.trade].label.toLowerCase()} contractor. I'm calling about ${lead.address} to offer a written estimate. Is it OK if I take a minute?`
      : `Hi, ${company ? `is this someone at ${company}?` : `I'm looking for whoever handles ${lead.address}.`} This is [Your name] with ${business}, a Chicago ${snap.trades[ws.trade].label.toLowerCase()} contractor. Do you have a minute?`,
    reason_for_calling: pitch.reason,
    discovery_questions: [
      `Who makes the decisions about repairs and contractors for ${lead.address}?`,
      lead.kind === "closed_restaurant"
        ? "Is the space already spoken for, or are you looking for a tenant or a build-out partner?"
        : `Is any ${noun} work planned or budgeted for it?`,
      "Do you already work with a contractor on that? Would a second written estimate be useful?",
      "What timeline are you working to?",
      "What's the best way to get a written estimate to you: email or mail?",
    ],
    likely_objections: [
      {
        objection: "How did you get my number?",
        honest_answer:
          "I called the business line listed for your company. If they ask how you found the property: the owner of record is public information, and you're a private contractor. Answer truthfully, but don't bring up or discuss the items under must_not_mention.",
      },
      {
        objection: "Are you the City? Is this a violation notice?",
        honest_answer: "No. You're an independent private contractor and not affiliated with the City of Chicago.",
      },
      {
        objection: "We already have a contractor.",
        honest_answer: "Understood. A second written estimate costs nothing if one is ever useful. Or ask to be taken off the list.",
      },
      {
        objection: "Send me something.",
        honest_answer: "Offer a short written summary by email or mail, and ask them for the right address. Never guess an email address.",
      },
      {
        objection: "Stop calling / not interested.",
        honest_answer: "Apologize, say yes, thank them, record it the same day and never call again.",
      },
    ],
    suggested_next_step:
      "The goal is a yes to a free walk-through or a written estimate, not a sale. Propose a day to look at the property. Afterward set the lead's status (Contacted, Meeting booked, Lost or Not relevant) and a note on the lead page.",
    compliance_reminders: [
      ...CALL_RULES,
      "Individual owners: only a skip-traced number from a provider that allows marketing, scrubbed against Do Not Call within 31 days and not on our opt-out list; hand-dialed, 9:00-20:00.",
      "Only promise what the business can deliver, such as an inspection date or a quote turnaround.",
    ],
    requires_human_dial: true,
  };
}

export async function callBrief(input: Input, ctx: ToolContext) {
  const owner = ctx.owner;
  if (!owner) return NEEDS_SIGN_IN;
  const prospectId = str(input.prospect_id);
  const leadId = str(input.lead_id);
  if (prospectId && leadId) return { error: "Pass either prospect_id or lead_id, not both" };
  if (leadId) return leadCallBrief(ctx, leadId);
  if (!prospectId) return { error: "Pass prospect_id (a contractor prospect) or lead_id (a lead in this workspace)" };

  const resolved = await resolveProspect(prospectId);
  if ("error" in resolved) return resolved;
  const p = resolved.prospect;
  const [row, suggestions] = await Promise.all([getPipelineRow(owner, p.id), getProspectContacts(p.id)]);
  if (row?.status === "not_interested") {
    return {
      refused: true,
      reason:
        "This prospect is marked Not interested. Don't call them again; if they asked not to be contacted, that request must be honored.",
      link: prospectLink(p.id),
    };
  }
  return prospectCallBrief(ctx, p, row, suggestions);
}
