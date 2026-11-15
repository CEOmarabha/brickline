import "server-only";

import { sql } from "@/lib/db";
import type { ProspectStatus } from "@/lib/pipeline";

export interface PipelineRow {
  prospectId: string;
  status: ProspectStatus;
  contactName: string;
  email: string;
  phone: string;
  website: string;
  notes: string;
  sequenceStep: number;
  nextFollowUp: string | null;
  updatedAt: Date;
}

export interface PipelineEvent {
  id: number;
  status: ProspectStatus;
  note: string;
  createdAt: Date;
}

interface StatusRow {
  prospect_id: string;
  status: ProspectStatus;
  contact_name: string;
  email: string;
  phone: string;
  website: string;
  notes: string;
  sequence_step: number;
  next_follow_up: string | null;
  updated_at: Date;
}

const COLUMNS = `prospect_id, status, contact_name, email, phone, website, notes, sequence_step,
  next_follow_up::text as next_follow_up, updated_at`;

export function toPipelineRow(r: StatusRow): PipelineRow {
  return {
    prospectId: r.prospect_id,
    status: r.status,
    contactName: r.contact_name,
    email: r.email,
    phone: r.phone,
    website: r.website,
    notes: r.notes,
    sequenceStep: r.sequence_step,
    nextFollowUp: r.next_follow_up,
    updatedAt: new Date(r.updated_at),
  };
}

/** Every pipeline row for this owner, by prospect id. Owner-scoped: never read through a client workspace. */
export async function getPipeline(owner: string): Promise<Map<string, PipelineRow>> {
  const rows = await sql<StatusRow>(`select ${COLUMNS} from prospect_status where owner_id = $1`, [owner]);
  return new Map(rows.map((r) => [r.prospect_id, toPipelineRow(r)]));
}

export async function getPipelineRow(owner: string, prospectId: string): Promise<PipelineRow | undefined> {
  const rows = await sql<StatusRow>(`select ${COLUMNS} from prospect_status where owner_id = $1 and prospect_id = $2`, [
    owner,
    prospectId,
  ]);
  return rows[0] ? toPipelineRow(rows[0]) : undefined;
}

export async function getPipelineHistory(owner: string, prospectId: string): Promise<PipelineEvent[]> {
  const rows = await sql<{ id: number | string; status: ProspectStatus; note: string; created_at: Date }>(
    `select id, status, note, created_at from prospect_event
     where owner_id = $1 and prospect_id = $2 order by created_at desc, id desc limit 100`,
    [owner, prospectId],
  );
  return rows.map((r) => ({ id: Number(r.id), status: r.status, note: r.note, createdAt: new Date(r.created_at) }));
}
