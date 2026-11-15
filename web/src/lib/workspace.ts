import "server-only";

import { headers } from "next/headers";
import { sql } from "@/lib/db";
import type { TradeKey } from "@/lib/snapshot";
import { getIdentity } from "../../cursor/identity";

/**
 * Each signed-in viewer gets their own workspace. The stage prefix keeps preview sessions out of
 * production data. Returns null when no verified viewer is on the request.
 */
export async function viewerWorkspaceId(): Promise<string | null> {
  const identity = await getIdentity(await headers());
  if (!identity.verified) return null;
  return `${identity.stage}:${identity.sub}`;
}

export interface Workspace {
  id: string;
  businessName: string;
  trade: TradeKey;
  areas: number[];
  phone: string;
  mailingAddress: string;
  configured: boolean;
  signedIn: boolean;
}

export const LEAD_STATUSES = ["new", "contacted", "meeting", "won", "lost", "not_relevant"] as const;
export type LeadStatus = (typeof LEAD_STATUSES)[number];

export const STATUS_LABEL: Record<LeadStatus, string> = {
  new: "New",
  contacted: "Contacted",
  meeting: "Meeting booked",
  won: "Won",
  lost: "Lost",
  not_relevant: "Not relevant",
};

export interface LeadStatusRow {
  leadId: string;
  status: LeadStatus;
  note: string;
  updatedAt: Date;
}

export async function getWorkspace(): Promise<Workspace> {
  const wsId = await viewerWorkspaceId();
  const rows = await sql<{
    id: string;
    business_name: string;
    trade: TradeKey;
    areas: number[];
    phone: string;
    mailing_address: string;
  }>("select * from workspace where id = $1", [wsId ?? ""]);
  const r = wsId ? rows[0] : undefined;
  if (!r) {
    return {
      id: wsId ?? "",
      businessName: "",
      trade: "porch",
      areas: [],
      phone: "",
      mailingAddress: "",
      configured: false,
      signedIn: wsId !== null,
    };
  }
  return {
    id: r.id,
    businessName: r.business_name,
    trade: r.trade,
    areas: r.areas ?? [],
    phone: r.phone,
    mailingAddress: r.mailing_address,
    configured: true,
    signedIn: true,
  };
}

export async function getStatuses(): Promise<Map<string, LeadStatusRow>> {
  const wsId = await viewerWorkspaceId();
  if (!wsId) return new Map();
  const rows = await sql<{ lead_id: string; status: LeadStatus; note: string; updated_at: Date }>(
    "select lead_id, status, note, updated_at from lead_status where workspace_id = $1",
    [wsId],
  );
  return new Map(
    rows.map((r) => [
      r.lead_id,
      { leadId: r.lead_id, status: r.status, note: r.note, updatedAt: new Date(r.updated_at) },
    ]),
  );
}

export async function getLeadHistory(leadId: string) {
  const wsId = await viewerWorkspaceId();
  if (!wsId) return [];
  return sql<{ status: LeadStatus; note: string; created_at: Date }>(
    "select status, note, created_at from lead_event where workspace_id = $1 and lead_id = $2 order by created_at desc",
    [wsId, leadId],
  );
}
