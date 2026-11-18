"use server";

import { refresh } from "next/cache";
import { type ActionResult, runAction, UserError } from "@/lib/action-result";
import { multiLine, singleLine } from "@/lib/clean-text";
import { sql } from "@/lib/db";
import { HOLDOUT_CHOICES } from "@/lib/experiments";
import { MAX_JOB_VALUE, parseMoney } from "@/lib/money-input";
import { getSnapshot, TRADE_KEYS, type TradeKey } from "@/lib/snapshot";
import {
  currentWorkspaceId,
  LEAD_STATUSES,
  type LeadStatus,
  ownsWorkspace,
  requireOwner,
} from "@/lib/workspace";

const MAX_WORKSPACES = 50;
const MAX_NOTE = 2000;

export async function saveWorkspace(formData: FormData): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const wsId = await currentWorkspaceId(owner);
    const trade = formData.get("trade");
    if (typeof trade !== "string" || !TRADE_KEYS.includes(trade as TradeKey)) throw new UserError("Pick a trade");
    const areas = new Set<number>();
    for (const value of formData.getAll("areas")) {
      const id = Number(value);
      if (!Number.isInteger(id) || id < 1 || id > 77) throw new UserError("Unknown neighborhood");
      areas.add(id);
    }
    const businessName = singleLine(formData.get("businessName"), 120, "Company name");
    const phone = singleLine(formData.get("phone"), 40, "Phone");
    const mailingAddress = singleLine(formData.get("mailingAddress"), 200, "Mailing address");
    const holdout = Number(formData.get("holdoutPct") ?? 0);
    if (!HOLDOUT_CHOICES.includes(holdout as (typeof HOLDOUT_CHOICES)[number])) throw new UserError("Unknown holdout share");
    await sql(
      `insert into workspace (id, owner_id, name, business_name, trade, areas, phone, mailing_address, holdout_pct,
         updated_at)
       values ($1, $2, $3, $3, $4, $5, $6, $7, $8, now())
       on conflict (id) do update set name = $3, business_name = $3, trade = $4, areas = $5, phone = $6,
         mailing_address = $7, holdout_pct = $8, updated_at = now()
       where workspace.owner_id = $2`,
      [wsId, owner, businessName, trade, [...areas].sort((a, b) => a - b), phone, mailingAddress, holdout],
    );
    refresh();
  });
}

export async function createWorkspace(name: string): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const clean = singleLine(name, 120, "Name");
    if (!clean) throw new UserError("Name required");
    // An owner who never saved Settings works in an implicit workspace; keep it as a real one so it stays in the switcher.
    const current = await currentWorkspaceId(owner);
    await sql("insert into workspace (id, owner_id) values ($1, $2) on conflict (id) do nothing", [current, owner]);
    const count = await sql<{ n: number }>("select count(*)::int as n from workspace where owner_id = $1", [owner]);
    if ((count[0]?.n ?? 0) >= MAX_WORKSPACES) throw new UserError(`You can have at most ${MAX_WORKSPACES} workspaces`);
    const base = (
      await sql<{ trade: TradeKey; areas: number[] }>(
        "select trade, areas from workspace where id = $1 and owner_id = $2",
        [current, owner],
      )
    )[0];
    const id = crypto.randomUUID();
    await sql(
      "insert into workspace (id, owner_id, name, business_name, trade, areas) values ($1, $2, $3, $3, $4, $5)",
      [id, owner, clean, base?.trade ?? "porch", base?.areas ?? []],
    );
    await setCurrent(owner, id);
    refresh();
  });
}

export async function switchWorkspace(workspaceId: string): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    if (typeof workspaceId !== "string" || !(await ownsWorkspace(owner, workspaceId))) {
      throw new UserError("Unknown workspace");
    }
    await setCurrent(owner, workspaceId);
    refresh();
  });
}

async function setCurrent(owner: string, workspaceId: string) {
  await sql(
    `insert into viewer_state (owner_id, current_workspace, updated_at) values ($1, $2, now())
     on conflict (owner_id) do update set current_workspace = $2, updated_at = now()`,
    [owner, workspaceId],
  );
}

/**
 * Sets a lead's status and note. `jobValue` (dollars the user entered) belongs to Won leads only: leaving it out
 * keeps the value a Won lead already has, an empty value clears it, and any other status always clears it. The
 * event row records the value as it was at that moment, so history survives later changes.
 */
export async function setLeadStatus(
  leadId: string,
  status: LeadStatus,
  note: string,
  jobValue?: string | number | null,
): Promise<ActionResult> {
  return runAction(async () => {
    const owner = await requireOwner();
    const wsId = await currentWorkspaceId(owner);
    if (typeof leadId !== "string" || !(await getSnapshot()).leads.some((l) => l.id === leadId)) {
      throw new UserError("That lead is no longer in this week's data");
    }
    if (!LEAD_STATUSES.includes(status)) throw new UserError("Unknown status");
    const cleanNote = multiLine(note, MAX_NOTE, "Note");
    const entered = parseMoney(jobValue, { label: "Job value", max: MAX_JOB_VALUE });
    if (entered && status !== "won") throw new UserError("A job value can only be saved on a Won lead");
    const [current] = await sql<{ status: string; note: string; job_value_usd: string | null }>(
      "select status, note, job_value_usd::text as job_value_usd from lead_status where workspace_id = $1 and lead_id = $2",
      [wsId, leadId],
    );
    let value: string | null = null;
    if (status === "won") {
      value = jobValue === undefined ? (current?.status === "won" ? current.job_value_usd : null) : (entered?.text ?? null);
    }
    if (
      current
        ? current.status === status && current.note === cleanNote && (current.job_value_usd ?? null) === value
        : status === "new" && cleanNote === ""
    ) {
      return;
    }
    await sql(
      `with saved as (
         insert into lead_status (workspace_id, lead_id, status, note, job_value_usd, updated_at)
         values ($1, $2, $3, $4, $5::numeric(12,2), now())
         on conflict (workspace_id, lead_id) do update
           set status = $3, note = $4, job_value_usd = $5::numeric(12,2), updated_at = now()
       )
       insert into lead_event (workspace_id, lead_id, status, note, job_value_usd)
       values ($1, $2, $3, $4, $5::numeric(12,2))`,
      [wsId, leadId, status, cleanNote, value],
    );
    refresh();
  });
}
