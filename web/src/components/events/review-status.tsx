"use client";

import { EnumSelect, useRun } from "@/components/deal-fields";
import { setEventLeadReview } from "@/lib/event-lead-actions";
import { REVIEW_STATUS_LABEL, type ReviewStatus } from "@/lib/event-lead-types";

const ITEMS: Record<string, string> = { ...REVIEW_STATUS_LABEL };

export function ReviewStatusSelect({
  itemHash,
  value,
  signedIn,
}: {
  itemHash: string;
  value: ReviewStatus;
  signedIn: boolean;
}) {
  const { pending, run } = useRun();
  return (
    <EnumSelect
      id={`review-${itemHash}`}
      label="Review"
      value={value}
      items={ITEMS}
      disabled={!signedIn || pending}
      onChange={(next) => {
        run(() => setEventLeadReview(itemHash, next), "Review status saved");
      }}
    />
  );
}
