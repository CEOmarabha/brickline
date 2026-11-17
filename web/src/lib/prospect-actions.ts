"use server";

import { refresh } from "next/cache";
import { type ActionResult, runAction, UserError } from "@/lib/action-result";
import { sql } from "@/lib/db";
import {
  addDays,
  cleanProspectFields,
  CLOSED_STATUSES,
  MAX_SEQUENCE_STEP,
  PROSPECT_FOLLOW_UP_DAYS,
  PROSPECT_STATUS_LABEL,
  todayChicago,
  type ProspectFields,
  type ProspectStatus,
} from "@/lib/pipeline";
import { getPipelineRow } from "@/lib/prospect-pipeline";
import { getProspect } from "@/lib/prospects";
import { requireOwner } from "@/lib/workspace";

async function requireProspect(prospectId: unknown): Promise<string> {
  if (typeof prospectId !== "string" || prospectId.length === 0 || prospectId.length > 120) {
    throw new UserError("Unknown prospect");
  }
  if (!(await getProspect(prospectId))) throw new UserError("Unknown prospect");
  return prospectId;
}

interface SavedRow {
  status: ProspectStatus;
  contactName: string;
  email: string;
  phone: string;
  website: string;
  notes: string;
  sequenceStep: number;
  nextFollowUp: string | null;
}

/** Upserts the pipeline row and logs the history line in one statement, so they never disagree. */
async function persist(owner: string, prospectId: string, row: SavedRow, historyNote: string) {
  await sql(
    `with saved as (
       insert into prospect_status
         (owner_id, prospect_id, status, contact_name, email, phone, website, notes, sequence_step, next_follow_up, updated_at)
       values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::date, now())
       on conflict (owner_id, prospect_id) do update set
         status = $3, contact_name = $4, email = $5, phone = $6, website = $7, notes = $8,
         sequence_step = $9, next_follow_up = $10::date, updated_at = now()
     )
     insert into prospect_event (owner_id, prospect_id, status, note) values ($1, $2, $3, $11)`,
    [
      owner,
      prospectId,
      row.status,
      row.contactName,
      row.email,
      row.phone,
      row.website,
      row.notes,
      row.sequenceStep,
      row.nextFollowUp,
      historyNote,
    ],
  );
}

/** Saves the given fields (others are left as they are) and records what changed in the history. */
export async function saveProspect(prospectId: string, fields: ProspectFields): Promise<ActionResult> {
  return runAction(async () => {
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

    const parts: string[] = [];
    if (statusChanged) parts.push(`Status: ${PROSPECT_STATUS_LABEL[status]}`);
    if (contactChanged) parts.push("Contact details updated");
    if (notesChanged) parts.push("Notes updated");
    if (followUpChanged) parts.push(nextFollowUp ? `Follow-up set for ${nextFollowUp}` : "Follow-up cleared");
    if (parts.length === 0) parts.push("Added to pipeline");
    await persist(owner, id, { status, ...next, sequenceStep: cur?.sequenceStep ?? 0, nextFollowUp }, parts.join(". "));
    refresh();
  });
}

/**
 * Records that the next email in the playbook sequence (day 0, 4, 10) was sent: advances the step, sets the
 * follow-up date, and moves a not-yet-contacted prospect to "emailed". A prospect who has already replied (or
 * is further along) keeps that status.
 */
export async function logEmailSent(prospectId: string): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const id = await requireProspect(prospectId);
    const cur = await getPipelineRow(owner, id);
    const step = (cur?.sequenceStep ?? 0) + 1;
    if (step > MAX_SEQUENCE_STEP) throw new UserError("All three emails are already logged");

    const curStatus = cur?.status ?? "not_contacted";
    const status: ProspectStatus = curStatus === "not_contacted" ? "emailed" : curStatus;
    const days = PROSPECT_FOLLOW_UP_DAYS[step] ?? null;
    const nextFollowUp = CLOSED_STATUSES.includes(status) || days === null ? null : addDays(todayChicago(), days);

    await persist(
      owner,
      id,
      {
        status,
        contactName: cur?.contactName ?? "",
        email: cur?.email ?? "",
        phone: cur?.phone ?? "",
        website: cur?.website ?? "",
        notes: cur?.notes ?? "",
        sequenceStep: step,
        nextFollowUp,
      },
      `Email ${step} of ${MAX_SEQUENCE_STEP} sent. ${nextFollowUp ? `Next follow-up ${nextFollowUp}` : "Sequence finished"}`,
    );
    refresh();
  });
}
