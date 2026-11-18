"use server";

import { refresh } from "next/cache";
import { type ActionResult, runAction, UserError } from "@/lib/action-result";
import { multiLine, singleLine } from "@/lib/clean-text";
import { sql } from "@/lib/db";
import { leadForCode, REPLY_CHANNELS, type ReplyChannel } from "@/lib/replies";
import { normalizeReplyCode } from "@/lib/reply-code";
import { getSnapshot } from "@/lib/snapshot";
import { currentWorkspaceId, requireOwner } from "@/lib/workspace";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type RecordReplyResult = ActionResult & { leadId?: string };

/** The founder records a reply an owner made by quoting the code on a letter or email. */
export async function recordReply(formData: FormData): Promise<RecordReplyResult> {
  let leadId = "";
  const result = await runAction(async () => {
    const owner = await requireOwner();
    const wsId = await currentWorkspaceId(owner);
    const code = normalizeReplyCode(String(formData.get("code") ?? ""));
    if (!code) throw new UserError("A reply code has 8 letters and digits, like ABCD-2346");
    const channel = String(formData.get("channel") ?? "");
    if (!REPLY_CHANNELS.includes(channel as ReplyChannel)) throw new UserError("Pick how the owner replied");
    const receivedOn = String(formData.get("receivedOn") ?? "");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(receivedOn) || Number.isNaN(Date.parse(receivedOn))) {
      throw new UserError("Enter the date the reply came in");
    }
    if (Date.parse(receivedOn) > Date.now() + 86_400_000) throw new UserError("The reply date is in the future");
    const phone = singleLine(formData.get("contactPhone"), 40, "Phone");
    const email = singleLine(formData.get("contactEmail"), 200, "Email");
    if (email && !EMAIL.test(email)) throw new UserError("That email address doesn't look right");
    const message = multiLine(formData.get("message"), 2000, "Message");
    const lead = leadForCode(await getSnapshot(), wsId, code);
    leadId = lead?.id ?? "";
    await sql(
      `insert into lead_reply (workspace_id, lead_id, code, channel, received_on, contact_phone, contact_email, message)
       values ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [wsId, leadId, code, channel, receivedOn, phone, email, message],
    );
    refresh();
  });
  return result.ok ? { ...result, leadId } : result;
}
