import "server-only";

import { sql } from "@/lib/db";
import type { BuyerType, ContactChannel, DealEventRow, DealFeeModel, DealRow, DealSource, DealStatus, PartnerRow } from "@/lib/deals";

/*
 * Reads for the founder's deal pipeline. Every query is parameterized and scoped `where owner_id = $1`, where the
 * owner is the signed-in viewer (`viewerId()`), never a client workspace.
 */

interface DealSql {
  id: string;
  source: DealSource;
  source_ref: string;
  title: string;
  buyer_name: string;
  buyer_type: BuyerType;
  contact_channel: ContactChannel;
  contact_handle_or_info: string;
  event_or_job_date: string | null;
  guests_or_size: number | null;
  location: string;
  needs: string;
  budget_usd: number | null;
  status: DealStatus;
  lost_reason: string;
  partner_ids: string[] | null;
  quote_usd: number | null;
  fee_usd: number | null;
  fee_model: DealFeeModel | "";
  fee_collected: boolean;
  next_follow_up: string | null;
  notes: string;
  created_at: Date;
  updated_at: Date;
}

const DEAL_COLUMNS = `id, source, source_ref, title, buyer_name, buyer_type, contact_channel, contact_handle_or_info,
  event_or_job_date::text as event_or_job_date, guests_or_size, location, needs, budget_usd::float8 as budget_usd,
  status, lost_reason, partner_ids, quote_usd::float8 as quote_usd, fee_usd::float8 as fee_usd, fee_model,
  fee_collected, next_follow_up::text as next_follow_up, notes, created_at, updated_at`;

const num = (v: number | string | null): number | null => (v === null ? null : Number(v));

function toDeal(r: DealSql): DealRow {
  return {
    id: r.id,
    source: r.source,
    sourceRef: r.source_ref,
    title: r.title,
    buyerName: r.buyer_name,
    buyerType: r.buyer_type,
    contactChannel: r.contact_channel,
    contactInfo: r.contact_handle_or_info,
    eventDate: r.event_or_job_date,
    guests: num(r.guests_or_size),
    location: r.location,
    needs: r.needs,
    budgetUsd: num(r.budget_usd),
    status: r.status,
    lostReason: r.lost_reason,
    partnerIds: r.partner_ids ?? [],
    quoteUsd: num(r.quote_usd),
    feeUsd: num(r.fee_usd),
    feeModel: r.fee_model,
    feeCollected: r.fee_collected,
    nextFollowUp: r.next_follow_up,
    notes: r.notes,
    createdAt: new Date(r.created_at),
    updatedAt: new Date(r.updated_at),
  };
}

/** Every deal of this owner, newest first. */
export async function getDeals(owner: string): Promise<DealRow[]> {
  const rows = await sql<DealSql>(`select ${DEAL_COLUMNS} from deal where owner_id = $1 order by created_at desc, id`, [owner]);
  return rows.map(toDeal);
}

export async function getDeal(owner: string, id: string): Promise<DealRow | undefined> {
  const rows = await sql<DealSql>(`select ${DEAL_COLUMNS} from deal where owner_id = $1 and id = $2`, [owner, id]);
  return rows[0] ? toDeal(rows[0]) : undefined;
}

interface EventSql {
  id: number | string;
  deal_id: string;
  status: DealStatus;
  note: string;
  created_at: Date;
}

const toEvent = (r: EventSql): DealEventRow => ({
  id: Number(r.id),
  dealId: r.deal_id,
  status: r.status,
  note: r.note,
  createdAt: new Date(r.created_at),
});

/** One deal's history, newest first. */
export async function getDealHistory(owner: string, dealId: string): Promise<DealEventRow[]> {
  const rows = await sql<EventSql>(
    `select id, deal_id, status, note, created_at from deal_event
     where owner_id = $1 and deal_id = $2 order by created_at desc, id desc limit 200`,
    [owner, dealId],
  );
  return rows.map(toEvent);
}

/** Status and time of every event of this owner (no notes), oldest first, for the funnel metrics. */
export async function getDealEventTimes(owner: string): Promise<{ dealId: string; status: DealStatus; createdAt: Date }[]> {
  const rows = await sql<Pick<EventSql, "deal_id" | "status" | "created_at">>(
    "select deal_id, status, created_at from deal_event where owner_id = $1 order by created_at, id",
    [owner],
  );
  return rows.map((r) => ({ dealId: r.deal_id, status: r.status, createdAt: new Date(r.created_at) }));
}

interface PartnerSql {
  id: string;
  name: string;
  services: string;
  area: string;
  contact_name: string;
  phone: string;
  email: string;
  website: string;
  fee_terms: string;
  agreement_signed: boolean;
  notes: string;
  created_at: Date;
  updated_at: Date;
}

const PARTNER_COLUMNS =
  "id, name, services, area, contact_name, phone, email, website, fee_terms, agreement_signed, notes, created_at, updated_at";

const toPartner = (r: PartnerSql): PartnerRow => ({
  id: r.id,
  name: r.name,
  services: r.services,
  area: r.area,
  contactName: r.contact_name,
  phone: r.phone,
  email: r.email,
  website: r.website,
  feeTerms: r.fee_terms,
  agreementSigned: r.agreement_signed,
  notes: r.notes,
  createdAt: new Date(r.created_at),
  updatedAt: new Date(r.updated_at),
});

export async function getPartners(owner: string): Promise<PartnerRow[]> {
  const rows = await sql<PartnerSql>(`select ${PARTNER_COLUMNS} from partner where owner_id = $1 order by lower(name), id`, [owner]);
  return rows.map(toPartner);
}

export async function getPartner(owner: string, id: string): Promise<PartnerRow | undefined> {
  const rows = await sql<PartnerSql>(`select ${PARTNER_COLUMNS} from partner where owner_id = $1 and id = $2`, [owner, id]);
  return rows[0] ? toPartner(rows[0]) : undefined;
}
