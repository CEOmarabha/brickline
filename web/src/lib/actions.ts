"use server";

import { refresh } from "next/cache";
import { sql } from "@/lib/db";
import { TRADE_KEYS, type TradeKey } from "@/lib/snapshot";
import { currentWorkspaceId, LEAD_STATUSES, type LeadStatus, ownsWorkspace, viewerId } from "@/lib/workspace";

const MAX_WORKSPACES = 50;

async function requireOwner(): Promise<string> {
  const owner = await viewerId();
  if (!owner) throw new Error("Sign in to save changes");
  return owner;
}

export async function saveWorkspace(formData: FormData) {
  const owner = await requireOwner();
  const wsId = await currentWorkspaceId(owner);
  const trade = String(formData.get("trade") ?? "porch") as TradeKey;
  if (!TRADE_KEYS.includes(trade)) throw new Error("Unknown trade");
  const areas = formData
    .getAll("areas")
    .map((v) => Number(v))
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 77);
  const businessName = String(formData.get("businessName") ?? "").trim().slice(0, 120);
  await sql(
    `insert into workspace (id, owner_id, name, business_name, trade, areas, phone, mailing_address, updated_at)
     values ($1, $2, $3, $3, $4, $5, $6, $7, now())
     on conflict (id) do update set name = $3, business_name = $3, trade = $4, areas = $5, phone = $6,
       mailing_address = $7, updated_at = now()
     where workspace.owner_id = $2`,
    [
      wsId,
      owner,
      businessName,
      trade,
      areas,
      String(formData.get("phone") ?? "").trim().slice(0, 40),
      String(formData.get("mailingAddress") ?? "").trim().slice(0, 200),
    ],
  );
  refresh();
}

export async function createWorkspace(name: string) {
  const owner = await requireOwner();
  const clean = String(name ?? "").trim().slice(0, 120);
  if (!clean) throw new Error("Name required");
  const count = await sql<{ n: number }>("select count(*)::int as n from workspace where owner_id = $1", [owner]);
  if ((count[0]?.n ?? 0) >= MAX_WORKSPACES) throw new Error("Workspace limit reached");
  const current = await currentWorkspaceId(owner);
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
}

export async function switchWorkspace(workspaceId: string) {
  const owner = await requireOwner();
  if (typeof workspaceId !== "string" || !(await ownsWorkspace(owner, workspaceId))) {
    throw new Error("Unknown workspace");
  }
  await setCurrent(owner, workspaceId);
  refresh();
}

async function setCurrent(owner: string, workspaceId: string) {
  await sql(
    `insert into viewer_state (owner_id, current_workspace, updated_at) values ($1, $2, now())
     on conflict (owner_id) do update set current_workspace = $2, updated_at = now()`,
    [owner, workspaceId],
  );
}

export async function setLeadStatus(leadId: string, status: LeadStatus, note: string) {
  const owner = await requireOwner();
  const wsId = await currentWorkspaceId(owner);
  if (typeof leadId !== "string" || leadId.length === 0 || leadId.length > 120) throw new Error("Bad lead id");
  if (!LEAD_STATUSES.includes(status)) throw new Error("Unknown status");
  const cleanNote = String(note ?? "").trim().slice(0, 2000);
  await sql(
    `insert into lead_status (workspace_id, lead_id, status, note, updated_at) values ($1, $2, $3, $4, now())
     on conflict (workspace_id, lead_id) do update set status = $3, note = $4, updated_at = now()`,
    [wsId, leadId, status, cleanNote],
  );
  await sql("insert into lead_event (workspace_id, lead_id, status, note) values ($1, $2, $3, $4)", [
    wsId,
    leadId,
    status,
    cleanNote,
  ]);
  refresh();
}
