import "server-only";

import { cache } from "react";
import { sql } from "@/lib/db";
import { replyCode } from "@/lib/reply-code";
import type { Lead, Snapshot } from "@/lib/snapshot";
import { getWorkspace } from "@/lib/workspace";

export const REPLY_CHANNELS = ["phone", "email", "mail", "web", "other"] as const;
export type ReplyChannel = (typeof REPLY_CHANNELS)[number];
export const REPLY_CHANNEL_LABEL: Record<ReplyChannel, string> = {
  phone: "Phone call",
  email: "Email",
  mail: "Letter",
  web: "Web form",
  other: "Other",
};

export interface LeadReply {
  id: number;
  leadId: string;
  code: string;
  channel: ReplyChannel;
  receivedOn: string;
  contactPhone: string;
  contactEmail: string;
  message: string;
}

/** Today's date in Chicago minus `daysAgo` days, as YYYY-MM-DD. */
export function chicagoDate(daysAgo = 0): string {
  return new Date(Date.now() - daysAgo * 86_400_000).toLocaleDateString("en-CA", { timeZone: "America/Chicago" });
}

/** The current lead in `snap` whose reply code in this workspace is `code`, if any. */
export function leadForCode(snap: Snapshot, workspaceId: string, code: string): Lead | null {
  return snap.leads.find((l) => replyCode(workspaceId, l.id) === code) ?? null;
}

/** Replies recorded in the current workspace, newest first. Contains what owners chose to share; never shipped. */
export const getReplies = cache(async (): Promise<LeadReply[]> => {
  const ws = await getWorkspace();
  if (!ws.signedIn) return [];
  const rows = await sql<{
    id: number;
    lead_id: string;
    code: string;
    channel: ReplyChannel;
    received_on: string;
    contact_phone: string;
    contact_email: string;
    message: string;
  }>(
    `select id, lead_id, code, channel, to_char(received_on, 'YYYY-MM-DD') as received_on, contact_phone,
       contact_email, message
     from lead_reply where workspace_id = $1 order by received_on desc, id desc`,
    [ws.id],
  );
  return rows.map((r) => ({
    id: Number(r.id),
    leadId: r.lead_id,
    code: r.code,
    channel: r.channel,
    receivedOn: r.received_on,
    contactPhone: r.contact_phone,
    contactEmail: r.contact_email,
    message: r.message,
  }));
});
