import "server-only";

import { headers } from "next/headers";
import { connection } from "next/server";
import { cache } from "react";
import { UserError } from "@/lib/action-result";
import { sql } from "@/lib/db";
import type { TradeKey } from "@/lib/snapshot";
import { DEFAULT_TARGET, resolveTarget, type TargetKey } from "@/lib/targets";
import { getIdentity } from "../../cursor/identity";

/**
 * The signed-in owner, as `<stage>:<sub>`. The stage prefix keeps preview sessions out of production data.
 * Returns null when no verified viewer is on the request.
 */
export const viewerId = cache(async (): Promise<string | null> => {
  await connection();
  const identity = await getIdentity(await headers());
  if (!identity.verified) return null;
  return `${identity.stage}:${identity.sub}`;
});

/** The signed-in owner for a server action; signed-out viewers get a UserError. */
export async function requireOwner(): Promise<string> {
  const owner = await viewerId();
  if (!owner) throw new UserError("Sign in to save changes");
  return owner;
}

export interface Workspace {
  id: string;
  name: string;
  businessName: string;
  /** The trade the lead scoring uses. A non-trade target leaves it at the last trade the workspace worked in. */
  trade: TradeKey;
  /** What the workspace is looking for: its trade, or one of the event and commercial lists. */
  target: TargetKey;
  areas: number[];
  phone: string;
  mailingAddress: string;
  configured: boolean;
  signedIn: boolean;
}

export interface WorkspaceSummary {
  id: string;
  label: string;
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

/** A lead left at Contacted this many days or longer counts as an overdue follow-up. */
export const LEAD_FOLLOW_UP_DAYS = 21;

export interface LeadStatusRow {
  leadId: string;
  status: LeadStatus;
  note: string;
  updatedAt: Date;
  /** What the user entered for a Won lead; null when none was entered or the lead is not Won. */
  jobValueUsd: number | null;
}

interface WorkspaceRow {
  id: string;
  name: string;
  business_name: string;
  trade: TradeKey;
  /** Empty for workspaces that never picked a target: they use their trade. */
  target: string | null;
  areas: number[];
  phone: string;
  mailing_address: string;
}

export function workspaceLabel(r: { name: string; business_name?: string; businessName?: string }): string {
  return r.name || r.business_name || r.businessName || "My business";
}

export async function listWorkspaces(owner: string): Promise<WorkspaceSummary[]> {
  const rows = await sql<WorkspaceRow>(
    "select * from workspace where owner_id = $1 order by created_at, id",
    [owner],
  );
  return rows.map((r) => ({ id: r.id, label: workspaceLabel(r) }));
}

/** Id of the workspace the owner is working in: their saved choice, else their first, else their default id. */
export async function currentWorkspaceId(owner: string): Promise<string> {
  const rows = await sql<{ id: string }>(
    `select w.id from workspace w
     left join viewer_state v on v.owner_id = w.owner_id and v.current_workspace = w.id
     where w.owner_id = $1
     order by (v.owner_id is null), w.created_at, w.id
     limit 1`,
    [owner],
  );
  // An owner with no saved workspace yet works in a default one whose id is their owner id.
  return rows[0]?.id ?? owner;
}

export async function ownsWorkspace(owner: string, workspaceId: string): Promise<boolean> {
  if (workspaceId === owner) return true;
  const rows = await sql("select 1 from workspace where id = $1 and owner_id = $2", [workspaceId, owner]);
  return rows.length > 0;
}

export const getWorkspace = cache(async (): Promise<Workspace> => {
  const owner = await viewerId();
  const empty: Workspace = {
    id: owner ?? "",
    name: "",
    businessName: "",
    trade: "porch",
    target: DEFAULT_TARGET,
    areas: [],
    phone: "",
    mailingAddress: "",
    configured: false,
    signedIn: owner !== null,
  };
  if (!owner) return empty;
  const id = await currentWorkspaceId(owner);
  const r = (await sql<WorkspaceRow>("select * from workspace where id = $1 and owner_id = $2", [id, owner]))[0];
  if (!r) return { ...empty, id };
  return {
    id: r.id,
    name: r.name,
    businessName: r.business_name,
    trade: r.trade,
    target: resolveTarget(r.target, r.trade),
    areas: r.areas ?? [],
    phone: r.phone,
    mailingAddress: r.mailing_address,
    configured: true,
    signedIn: true,
  };
});

export const getStatuses = cache(async (): Promise<Map<string, LeadStatusRow>> => {
  const ws = await getWorkspace();
  if (!ws.signedIn) return new Map();
  const rows = await sql<{
    lead_id: string;
    status: LeadStatus;
    note: string;
    updated_at: Date;
    job_value_usd: number | null;
  }>(
    "select lead_id, status, note, updated_at, job_value_usd::float8 as job_value_usd from lead_status where workspace_id = $1",
    [ws.id],
  );
  return new Map(
    rows.map((r) => [
      r.lead_id,
      {
        leadId: r.lead_id,
        status: r.status,
        note: r.note,
        updatedAt: new Date(r.updated_at),
        jobValueUsd: r.job_value_usd === null ? null : Number(r.job_value_usd),
      },
    ]),
  );
});

/** A lead nobody has worked: no saved status, or one that was reset to New. */
export function isOpenLead(statuses: Map<string, LeadStatusRow>, leadId: string): boolean {
  return (statuses.get(leadId)?.status ?? "new") === "new";
}

export async function getLeadHistory(leadId: string) {
  const ws = await getWorkspace();
  if (!ws.signedIn) return [];
  const rows = await sql<{ status: LeadStatus; note: string; created_at: Date; job_value_usd: number | null }>(
    `select status, note, created_at, job_value_usd::float8 as job_value_usd from lead_event
     where workspace_id = $1 and lead_id = $2 order by created_at desc, id desc`,
    [ws.id, leadId],
  );
  return rows.map((r) => ({ ...r, job_value_usd: r.job_value_usd === null ? null : Number(r.job_value_usd) }));
}

export interface OutcomeEvent {
  leadId: string;
  status: LeadStatus;
  createdAt: Date;
}

/** Every status change in the current workspace, oldest first (for measured conversion rates). */
export async function getEvents(): Promise<OutcomeEvent[]> {
  const ws = await getWorkspace();
  if (!ws.signedIn) return [];
  const rows = await sql<{ lead_id: string; status: LeadStatus; created_at: Date }>(
    "select lead_id, status, created_at from lead_event where workspace_id = $1 order by created_at, id",
    [ws.id],
  );
  return rows.map((r) => ({ leadId: r.lead_id, status: r.status, createdAt: new Date(r.created_at) }));
}
