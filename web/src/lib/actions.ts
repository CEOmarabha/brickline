"use server";

import { refresh } from "next/cache";
import { sql } from "@/lib/db";
import { TRADE_KEYS, type TradeKey } from "@/lib/snapshot";
import { LEAD_STATUSES, type LeadStatus, viewerWorkspaceId } from "@/lib/workspace";

async function requireWorkspace(): Promise<string> {
  const wsId = await viewerWorkspaceId();
  if (!wsId) throw new Error("Sign in to save changes");
  return wsId;
}

export async function saveWorkspace(formData: FormData) {
  const wsId = await requireWorkspace();
  const trade = String(formData.get("trade") ?? "porch") as TradeKey;
  if (!TRADE_KEYS.includes(trade)) throw new Error("Unknown trade");
  const areas = formData
    .getAll("areas")
    .map((v) => Number(v))
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 77);
  await sql(
    `insert into workspace (id, business_name, trade, areas, phone, mailing_address, updated_at)
     values ($1, $2, $3, $4, $5, $6, now())
     on conflict (id) do update set business_name = $2, trade = $3, areas = $4, phone = $5,
       mailing_address = $6, updated_at = now()`,
    [
      wsId,
      String(formData.get("businessName") ?? "").trim().slice(0, 120),
      trade,
      areas,
      String(formData.get("phone") ?? "").trim().slice(0, 40),
      String(formData.get("mailingAddress") ?? "").trim().slice(0, 200),
    ],
  );
  refresh();
}

export async function setLeadStatus(leadId: string, status: LeadStatus, note: string) {
  const wsId = await requireWorkspace();
  if (typeof leadId !== "string" || leadId.length === 0 || leadId.length > 120) throw new Error("Bad lead id");
  if (!LEAD_STATUSES.includes(status)) throw new Error("Unknown status");
  const cleanNote = note.trim().slice(0, 2000);
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
