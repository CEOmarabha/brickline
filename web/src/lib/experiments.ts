import type { Lead } from "@/lib/snapshot";

/** Holdout shares a workspace can choose in Settings (percent of letter leads kept unmailed). */
export const HOLDOUT_CHOICES = [0, 10, 15, 20] as const;

/**
 * Experiment 1 (docs/19): a fixed, random-looking share of letter leads is never mailed, so the permit rate of
 * mailed leads can be compared with leads nobody contacted. The bucket depends only on the lead id and the
 * experiment name, so it is identical across workspaces and reproducible offline:
 * bucket = FNV-1a-32("holdout-v1:" + leadId) mod 100.
 */
export const HOLDOUT_EXPERIMENT = "holdout-v1";

export function holdoutBucket(leadId: string, experiment = HOLDOUT_EXPERIMENT): number {
  const text = `${experiment}:${leadId}`;
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0) % 100;
}

/** Letters go to owners; investor leads (emails to companies) are not part of the letter holdout. */
export function isHoldout(lead: Lead, holdoutPct: number): boolean {
  return holdoutPct > 0 && lead.kind !== "investor_purchase" && holdoutBucket(lead.id) < holdoutPct;
}
