"use server";

import { refresh } from "next/cache";
import { sql } from "@/lib/db";
import {
  addDays,
  cleanProspectFields,
  CLOSED_STATUSES,
  FOLLOW_UP_DAYS,
  MAX_SEQUENCE_STEP,
  PROSPECT_STATUS_LABEL,
  todayChicago,
  type ProspectFields,
  type ProspectStatus,
} from "@/lib/pipeline";
import { getPipelineRow } from "@/lib/prospect-pipeline";
import { getProspect } from "@/lib/prospects";
import { viewerId } from "@/lib/workspace";

async function requireOwner(): Promise<string> {
  const owner = await viewerId();
  if (!owner) throw new Error("Sign in to save changes");
  return owner;
}

async function requireProspect(prospectId: unknown): Promise<string> {
  if (typeof prospectId !== "string" || prospectId.length === 0 || prospectId.length > 120) {
    throw new Error("Unknown prospect");
  }
  if (!(await getProspect(prospectId))) throw new Error("Unknown prospect");
  return prospectId;
}

async function logEvent(owner: string, prospectId: string, status: ProspectStatus, note: string) {
  await sql("insert into prospect_event (owner_id, prospect_id, status, note) values ($1, $2, $3, $4)", [
    owner,
    prospectId,
    status,
    note,
  ]);
}

const UPSERT = `
  insert into prospect_status
    (owner_id, prospect_id, status, contact_name, email, phone, website, notes, sequence_step, next_follow_up, updated_at)
  values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::date, now())
  on conflict (owner_id, prospect_id) do update set
    status = $3, contact_name = $4, email = $5, phone = $6, website = $7, notes = $8,
    sequence_step = $9, next_follow_up = $10::date, updated_at = now()`;

/** Saves the given fields (others are left as they are) and records what changed in the history. */
export async function saveProspect(prospectId: string, fields: ProspectFields) {
  const owner = await requireOwner();
  const id = await requireProspect(prospectId);
  const clean = cleanProspectFields(fields ?? {});
  const cur = await getPipelineRow(owner, id);

  const status = clean.status ?? cur?.status ?? "not_contacted";
  const statusChanged = status !== (cur?.status ?? "not_contacted");
  let nextFollowUp = clean.nextFollowUp !== undefined ? clean.nextFollowUp : (cur?.nextFollowUp ?? null);
  if (clean.status !== undefined && CLOSED_STATUSES.includes(status) && clean.nextFollowUp === undefined) {
    nextFollowUp = null;
  }
  const next = {
    contactName: clean.contactName ?? cur?.contactName ?? "",
    email: clean.email ?? cur?.email ?? "",
    phone: clean.phone ?? cur?.phone ?? "",
    website: clean.website ?? cur?.website ?? "",
    notes: clean.notes ?? cur?.notes ?? "",
  };
  const contactChanged =
    next.contactName !== (cur?.contactName ?? "") ||
    next.email !== (cur?.email ?? "") ||
    next.phone !== (cur?.phone ?? "") ||
    next.website !== (cur?.website ?? "");
  const notesChanged = next.notes !== (cur?.notes ?? "");
  const followUpChanged = nextFollowUp !== (cur?.nextFollowUp ?? null);
  if (cur && !statusChanged && !contactChanged && !notesChanged && !followUpChanged) return;

  await sql(UPSERT, [
    owner,
    id,
    status,
    next.contactName,
    next.email,
    next.phone,
    next.website,
    next.notes,
    cur?.sequenceStep ?? 0,
    nextFollowUp,
  ]);

  const parts: string[] = [];
  if (statusChanged) parts.push(`Status: ${PROSPECT_STATUS_LABEL[status]}`);
  if (contactChanged) parts.push("Contact details updated");
  if (notesChanged) parts.push("Notes updated");
  if (followUpChanged) parts.push(nextFollowUp ? `Follow-up set for ${nextFollowUp}` : "Follow-up cleared");
  if (parts.length === 0) parts.push("Added to pipeline");
  await logEvent(owner, id, status, parts.join(". "));
  refresh();
}

/**
 * Records that the next email in the playbook sequence (day 0, 4, 10) was sent: advances the step, sets the
 * follow-up date, and moves a not-yet-contacted prospect to "emailed". A prospect who has already replied (or
 * is further along) keeps that status.
 */
export async function logEmailSent(prospectId: string) {
  const owner = await requireOwner();
  const id = await requireProspect(prospectId);
  const cur = await getPipelineRow(owner, id);
  const step = (cur?.sequenceStep ?? 0) + 1;
  if (step > MAX_SEQUENCE_STEP) throw new Error("All three emails are already logged");

  const curStatus = cur?.status ?? "not_contacted";
  const status: ProspectStatus = curStatus === "not_contacted" ? "emailed" : curStatus;
  const days = FOLLOW_UP_DAYS[step] ?? null;
  const nextFollowUp = CLOSED_STATUSES.includes(status) ? null : days === null ? null : addDays(todayChicago(), days);

  await sql(UPSERT, [
    owner,
    id,
    status,
    cur?.contactName ?? "",
    cur?.email ?? "",
    cur?.phone ?? "",
    cur?.website ?? "",
    cur?.notes ?? "",
    step,
    nextFollowUp,
  ]);
  await logEvent(
    owner,
    id,
    status,
    `Email ${step} of ${MAX_SEQUENCE_STEP} sent. ${nextFollowUp ? `Next follow-up ${nextFollowUp}` : "Sequence finished"}`,
  );
  refresh();
}
