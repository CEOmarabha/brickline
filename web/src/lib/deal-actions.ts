"use server";

import { randomUUID } from "node:crypto";
import { refresh } from "next/cache";
import { type ActionResult, runAction, UserError } from "@/lib/action-result";
import { sql } from "@/lib/db";
import { getDeal, getPartner } from "@/lib/deal-store";
import {
  type CleanDealFields,
  cleanDealFields,
  cleanDealId,
  cleanFollowUpDate,
  cleanPartnerFields,
  cleanPartnerIds,
  cleanQuoteFee,
  type CreateResult,
  DEAL_FEE_MODEL_LABEL,
  DEAL_STATUS_LABEL,
  DEFAULT_FOLLOW_UP_DAYS,
  type DealFields,
  type DealRow,
  guessChannel,
  isDealStatus,
  isOptedOut,
  OPTED_OUT_LOCKED,
  type PartnerFields,
  type QuoteFeeFields,
} from "@/lib/deals";
import { singleLine } from "@/lib/clean-text";
import { centsToText, dollarsToCents } from "@/lib/money-input";
import { addDays, todayChicago } from "@/lib/pipeline";
import { requireOwner } from "@/lib/workspace";

/*
 * Server actions for the founder's deal pipeline. Each one checks the signed-in viewer, validates on the server, and
 * runs parameterized SQL scoped `where owner_id = $viewer`, so an id that belongs to another owner is simply unknown.
 */

const newId = (prefix: string) => `${prefix}-${randomUUID().replaceAll("-", "").slice(0, 16)}`;

async function runWithId(fn: () => Promise<string>): Promise<CreateResult> {
  try {
    return { ok: true, id: await fn() };
  } catch (error) {
    if (error instanceof UserError) return { ok: false, error: error.message };
    throw error;
  }
}

async function requireDeal(owner: string, id: unknown): Promise<DealRow> {
  const deal = await getDeal(owner, cleanDealId(id));
  if (!deal) throw new UserError("Unknown deal");
  return deal;
}

const money = (cents: number | null) => (cents === null ? null : centsToText(cents));

async function ensureNoDuplicateRef(owner: string, sourceRef: string, exceptId: string | null) {
  if (sourceRef === "") return;
  const rows = await sql<{ title: string }>(
    "select title from deal where owner_id = $1 and source_ref = $2 and ($3::text is null or id <> $3::text) limit 1",
    [owner, sourceRef, exceptId],
  );
  if (rows[0]) throw new UserError(`You already added this link as "${rows[0].title}"`);
}

/** Quick add: a title is required; everything else is optional. New deals start at Found. */
export async function createDeal(fields: DealFields): Promise<CreateResult> {
  return runWithId(async () => {
    const owner = await requireOwner();
    const clean = cleanDealFields(fields ?? {});
    if (clean.title === undefined) throw new UserError("Add a short title so you can find this deal again");
    const sourceRef = clean.sourceRef ?? "";
    await ensureNoDuplicateRef(owner, sourceRef, null);

    const id = newId("d");
    await sql(
      `with saved as (
         insert into deal
           (id, owner_id, source, source_ref, title, buyer_name, buyer_type, contact_channel, contact_handle_or_info,
            event_or_job_date, guests_or_size, location, needs, budget_usd, status, notes)
         values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::date, $11::int, $12, $13, $14::numeric(12,2), 'found', $15)
         returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $2::text, id, 'found', $16::text from saved`,
      [
        id,
        owner,
        clean.source ?? "other",
        sourceRef,
        clean.title,
        clean.buyerName ?? "",
        clean.buyerType ?? "person",
        clean.contactChannel ?? guessChannel(sourceRef),
        clean.contactInfo ?? "",
        clean.eventDate ?? null,
        clean.guests ?? null,
        clean.location ?? "",
        clean.needs ?? "",
        clean.budget?.text ?? null,
        clean.notes ?? "",
        "Deal added",
      ],
    );
    refresh();
    return id;
  });
}

const DETAIL_LABELS: [keyof CleanDealFields, string][] = [
  ["source", "source"],
  ["sourceRef", "link"],
  ["title", "title"],
  ["buyerName", "buyer name"],
  ["buyerType", "buyer type"],
  ["contactChannel", "contact channel"],
  ["contactInfo", "contact info"],
  ["eventDate", "date"],
  ["guests", "size"],
  ["location", "location"],
  ["needs", "needs"],
  ["budget", "budget"],
  ["notes", "notes"],
];

/** Saves the given detail fields (others are left alone) and writes what changed to the history. */
export async function updateDeal(dealId: string, fields: DealFields): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const cur = await requireDeal(owner, dealId);
    const clean = cleanDealFields(fields ?? {});

    const next = {
      source: clean.source ?? cur.source,
      sourceRef: clean.sourceRef ?? cur.sourceRef,
      title: clean.title ?? cur.title,
      buyerName: clean.buyerName ?? cur.buyerName,
      buyerType: clean.buyerType ?? cur.buyerType,
      contactChannel: clean.contactChannel ?? cur.contactChannel,
      contactInfo: clean.contactInfo ?? cur.contactInfo,
      eventDate: clean.eventDate !== undefined ? clean.eventDate : cur.eventDate,
      guests: clean.guests !== undefined ? clean.guests : cur.guests,
      location: clean.location ?? cur.location,
      needs: clean.needs ?? cur.needs,
      budgetCents: clean.budget !== undefined ? (clean.budget?.cents ?? null) : dollarsToCents(cur.budgetUsd),
      notes: clean.notes ?? cur.notes,
    };
    const was: Record<string, unknown> = {
      source: cur.source,
      sourceRef: cur.sourceRef,
      title: cur.title,
      buyerName: cur.buyerName,
      buyerType: cur.buyerType,
      contactChannel: cur.contactChannel,
      contactInfo: cur.contactInfo,
      eventDate: cur.eventDate,
      guests: cur.guests,
      location: cur.location,
      needs: cur.needs,
      budget: dollarsToCents(cur.budgetUsd),
      notes: cur.notes,
    };
    const now: Record<string, unknown> = { ...next, budget: next.budgetCents };
    const changed = DETAIL_LABELS.filter(([key]) => was[key] !== now[key]).map(([, label]) => label);
    if (changed.length === 0) return;
    if (next.sourceRef !== cur.sourceRef) await ensureNoDuplicateRef(owner, next.sourceRef, cur.id);

    await sql(
      `with saved as (
         update deal set source = $3, source_ref = $4, title = $5, buyer_name = $6, buyer_type = $7,
           contact_channel = $8, contact_handle_or_info = $9, event_or_job_date = $10::date, guests_or_size = $11::int,
           location = $12, needs = $13, budget_usd = $14::numeric(12,2), notes = $15, updated_at = now()
         where owner_id = $1 and id = $2
         returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $1::text, id, $16::text, $17::text from saved`,
      [
        owner,
        cur.id,
        next.source,
        next.sourceRef,
        next.title,
        next.buyerName,
        next.buyerType,
        next.contactChannel,
        next.contactInfo,
        next.eventDate,
        next.guests,
        next.location,
        next.needs,
        money(next.budgetCents),
        next.notes,
        cur.status,
        `Updated ${changed.join(", ")}`,
      ],
    );
    refresh();
  });
}

/**
 * Moves a deal to another status and writes the history line. Opted out is final: it clears the follow-up, locks
 * the drafts and refuses every later status change. Lost, Completed and Opted out clear the follow-up date; a deal
 * moved to Contacted with no follow-up gets one a few days out.
 */
export async function changeDealStatus(
  dealId: string,
  status: string,
  options?: { lostReason?: string; note?: string },
): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    if (!isDealStatus(status)) throw new UserError("Unknown status");
    const cur = await requireDeal(owner, dealId);
    if (isOptedOut(cur.status) && status !== "opted_out") throw new UserError(OPTED_OUT_LOCKED);

    const note = singleLine(options?.note ?? "", 300, "Note");
    const lostReason = status === "lost" ? singleLine(options?.lostReason ?? cur.lostReason, 200, "Reason") : "";
    const statusChanged = status !== cur.status;
    if (!statusChanged && lostReason === cur.lostReason && note === "") return;

    let nextFollowUp = cur.nextFollowUp;
    if (statusChanged) {
      if (status === "completed" || status === "lost" || status === "opted_out") nextFollowUp = null;
      else if (status === "contacted" && nextFollowUp === null) nextFollowUp = addDays(todayChicago(), DEFAULT_FOLLOW_UP_DAYS);
    }
    const parts: string[] = [];
    if (statusChanged) parts.push(`Status: ${DEAL_STATUS_LABEL[status]}`);
    if (status === "lost" && lostReason !== "" && lostReason !== cur.lostReason) parts.push(`Reason: ${lostReason}`);
    if (nextFollowUp !== cur.nextFollowUp) {
      parts.push(nextFollowUp ? `Follow-up set for ${nextFollowUp}` : "Follow-up cleared");
    }
    if (note !== "") parts.push(note);

    await sql(
      `with saved as (
         update deal set status = $3, lost_reason = $4, next_follow_up = $5::date, updated_at = now()
         where owner_id = $1 and id = $2 and (status <> 'opted_out' or $3 = 'opted_out')
         returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $1::text, id, $3::text, $6::text from saved`,
      [owner, cur.id, status, lostReason, nextFollowUp, parts.join(". ")],
    );
    refresh();
  });
}

export async function setNextFollowUp(dealId: string, date: string | null): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const cur = await requireDeal(owner, dealId);
    const next = cleanFollowUpDate(date);
    if (next !== null && isOptedOut(cur.status)) throw new UserError(OPTED_OUT_LOCKED);
    if (next === cur.nextFollowUp) return;
    await sql(
      `with saved as (
         update deal set next_follow_up = $3::date, updated_at = now() where owner_id = $1 and id = $2 returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $1::text, id, $4::text, $5::text from saved`,
      [owner, cur.id, next, cur.status, next ? `Follow-up set for ${next}` : "Follow-up cleared"],
    );
    refresh();
  });
}

/** Replaces the partners attached to a deal. Every id must be one of this owner's partners. */
export async function setDealPartners(dealId: string, partnerIds: string[]): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const cur = await requireDeal(owner, dealId);
    const ids = cleanPartnerIds(partnerIds);
    const found = ids.length
      ? await sql<{ id: string; name: string }>("select id, name from partner where owner_id = $1 and id = any($2::text[])", [owner, ids])
      : [];
    if (found.length !== ids.length) throw new UserError("Unknown partner");
    if (ids.length === cur.partnerIds.length && ids.every((id, i) => id === cur.partnerIds[i])) return;

    const names = ids.map((id) => found.find((f) => f.id === id)?.name ?? "");
    await sql(
      `with saved as (
         update deal set partner_ids = $3::text[], updated_at = now() where owner_id = $1 and id = $2 returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $1::text, id, $4::text, $5::text from saved`,
      [owner, cur.id, ids, cur.status, ids.length ? `Partners: ${names.join(", ")}` : "Partners cleared"],
    );
    refresh();
  });
}

/** Records the quote the buyer sees and your own fee (and how you are paid). Only the given fields change. */
export async function recordQuoteAndFee(dealId: string, fields: QuoteFeeFields): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const cur = await requireDeal(owner, dealId);
    const clean = cleanQuoteFee(fields ?? {});

    const curQuote = dollarsToCents(cur.quoteUsd);
    const curFee = dollarsToCents(cur.feeUsd);
    const quote = clean.quote !== undefined ? (clean.quote?.cents ?? null) : curQuote;
    const fee = clean.fee !== undefined ? (clean.fee?.cents ?? null) : curFee;
    const feeModel = clean.feeModel !== undefined ? clean.feeModel : cur.feeModel;
    if (feeModel === "none" && fee !== null && fee > 0) throw new UserError(`The fee model "No fee" can't have a fee amount`);
    // A fee that is gone can't have been collected.
    const feeCollected = cur.feeCollected && fee !== null && fee > 0;

    const parts: string[] = [];
    if (quote !== curQuote) parts.push(quote === null ? "Quote cleared" : `Quote set to $${centsToText(quote)}`);
    if (fee !== curFee) parts.push(fee === null ? "Fee cleared" : `Fee set to $${centsToText(fee)}`);
    if (feeModel !== cur.feeModel) {
      parts.push(feeModel === "" ? "Fee model cleared" : `Fee model: ${DEAL_FEE_MODEL_LABEL[feeModel]}`);
    }
    if (feeCollected !== cur.feeCollected) parts.push("Fee no longer marked collected");
    if (parts.length === 0) return;

    await sql(
      `with saved as (
         update deal set quote_usd = $3::numeric(12,2), fee_usd = $4::numeric(12,2), fee_model = $5, fee_collected = $6,
           updated_at = now()
         where owner_id = $1 and id = $2
         returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $1::text, id, $7::text, $8::text from saved`,
      [owner, cur.id, money(quote), money(fee), feeModel, feeCollected, cur.status, parts.join(". ")],
    );
    refresh();
  });
}

export async function markFeeCollected(dealId: string, collected: boolean): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const cur = await requireDeal(owner, dealId);
    if (typeof collected !== "boolean") throw new UserError("Unknown value");
    if (collected) {
      if (cur.status !== "booked" && cur.status !== "completed") {
        throw new UserError("Mark the deal Booked or Completed before recording your fee as collected");
      }
      if (cur.feeUsd === null || cur.feeUsd <= 0) throw new UserError("Enter your fee first");
    }
    if (collected === cur.feeCollected) return;
    await sql(
      `with saved as (
         update deal set fee_collected = $3, updated_at = now() where owner_id = $1 and id = $2 returning id
       )
       insert into deal_event (owner_id, deal_id, status, note)
       select $1::text, id, $4::text, $5::text from saved`,
      [
        owner,
        cur.id,
        collected,
        cur.status,
        collected ? `Fee collected: $${centsToText(dollarsToCents(cur.feeUsd) ?? 0)}` : "Fee marked not collected",
      ],
    );
    refresh();
  });
}

export async function createPartner(fields: PartnerFields): Promise<CreateResult> {
  return runWithId(async () => {
    const owner = await requireOwner();
    const clean = cleanPartnerFields(fields ?? {});
    if (clean.name === undefined) throw new UserError("Add the partner's business name");
    const id = newId("p");
    await sql(
      `insert into partner
         (id, owner_id, name, services, area, contact_name, phone, email, website, fee_terms, agreement_signed, notes)
       values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
      [
        id,
        owner,
        clean.name,
        clean.services ?? "",
        clean.area ?? "",
        clean.contactName ?? "",
        clean.phone ?? "",
        clean.email ?? "",
        clean.website ?? "",
        clean.feeTerms ?? "",
        clean.agreementSigned ?? false,
        clean.notes ?? "",
      ],
    );
    refresh();
    return id;
  });
}

export async function updatePartner(partnerId: string, fields: PartnerFields): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    if (typeof partnerId !== "string" || partnerId.length === 0 || partnerId.length > 80) throw new UserError("Unknown partner");
    const cur = await getPartner(owner, partnerId);
    if (!cur) throw new UserError("Unknown partner");
    const clean = cleanPartnerFields(fields ?? {});
    await sql(
      `update partner set name = $3, services = $4, area = $5, contact_name = $6, phone = $7, email = $8, website = $9,
         fee_terms = $10, agreement_signed = $11, notes = $12, updated_at = now()
       where owner_id = $1 and id = $2`,
      [
        owner,
        cur.id,
        clean.name ?? cur.name,
        clean.services ?? cur.services,
        clean.area ?? cur.area,
        clean.contactName ?? cur.contactName,
        clean.phone ?? cur.phone,
        clean.email ?? cur.email,
        clean.website ?? cur.website,
        clean.feeTerms ?? cur.feeTerms,
        clean.agreementSigned ?? cur.agreementSigned,
        clean.notes ?? cur.notes,
      ],
    );
    refresh();
  });
}
