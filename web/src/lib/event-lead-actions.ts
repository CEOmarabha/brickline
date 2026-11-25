"use server";

import { refresh } from "next/cache";
import { type ActionResult, runAction, UserError } from "@/lib/action-result";
import { sql } from "@/lib/db";
import { hasPostgres, writeLocalReview } from "@/lib/event-lead-reviews-file";
import { REVIEW_STATUSES, type ReviewStatus } from "@/lib/event-lead-types";
import { requireOwner } from "@/lib/workspace";

function parseHash(value: unknown): string {
  if (typeof value !== "string" || !/^[a-f0-9]{16,64}$/i.test(value)) {
    throw new UserError("Unknown event lead");
  }
  return value;
}

function parseStatus(value: unknown): ReviewStatus {
  if (typeof value !== "string" || !(REVIEW_STATUSES as readonly string[]).includes(value)) {
    throw new UserError("Unknown review status");
  }
  return value as ReviewStatus;
}

/** Sets review_status for one event lead. Creates a stub row if the scanner has not upserted yet. */
export async function setEventLeadReview(itemHash: unknown, status: unknown): Promise<ActionResult> {
  return runAction(async () => {
    await requireOwner();
    const hash = parseHash(itemHash);
    const review = parseStatus(status);
    if (hasPostgres()) {
      await sql(
        `insert into event_lead (item_hash, source, review_status, last_seen)
         values ($1, 'manual', $2, now())
         on conflict (item_hash) do update set review_status = $2`,
        [hash, review],
      );
    } else {
      await writeLocalReview(hash, review);
    }
    refresh();
  });
}
