import "server-only";

import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { isReviewStatus, type ReviewStatus } from "@/lib/event-lead-types";

/** Gitignored JSON used when DATABASE_URL is unset (PGlite is in-memory). */
export function hasPostgres(): boolean {
  return Boolean(process.env.DATABASE_URL?.trim());
}

export function reviewsFilePath(): string {
  const override = process.env.EVENT_LEAD_REVIEWS_PATH?.trim();
  if (override) return override;
  const fromWeb = path.join(process.cwd(), "..", "data", "event-lead-reviews.json");
  const fromRoot = path.join(process.cwd(), "data", "event-lead-reviews.json");
  // Next `npm run dev` cwd is web/; engine scans from the repo root.
  return path.basename(process.cwd()) === "web" ? fromWeb : fromRoot;
}

export async function readLocalReviews(): Promise<Map<string, ReviewStatus>> {
  const overlay = new Map<string, ReviewStatus>();
  try {
    const raw = JSON.parse(await readFile(reviewsFilePath(), "utf8")) as unknown;
    const blob =
      raw && typeof raw === "object" && "reviews" in raw && typeof (raw as { reviews: unknown }).reviews === "object"
        ? (raw as { reviews: Record<string, unknown> }).reviews
        : (raw as Record<string, unknown>);
    if (!blob || typeof blob !== "object") return overlay;
    for (const [hash, status] of Object.entries(blob)) {
      if (hash === "updatedAt") continue;
      if (typeof status === "string" && isReviewStatus(status)) overlay.set(hash, status);
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  return overlay;
}

export async function writeLocalReview(itemHash: string, status: ReviewStatus): Promise<void> {
  const file = reviewsFilePath();
  const overlay = await readLocalReviews();
  overlay.set(itemHash, status);
  const payload = {
    updatedAt: new Date().toISOString(),
    reviews: Object.fromEntries(overlay),
  };
  await mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp`;
  await writeFile(tmp, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  await rename(tmp, file);
}
