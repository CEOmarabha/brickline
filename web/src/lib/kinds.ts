export type LeadKindKey = "violation" | "complaint" | "porch_request" | "vacant" | "investor_purchase";

/** Plural labels, shared by the filters, CSV export and results. */
export const KIND_LABEL: Record<LeadKindKey, string> = {
  violation: "Violations",
  complaint: "311 complaints",
  porch_request: "Porch inspection requests",
  vacant: "Vacant buildings",
  investor_purchase: "Investor purchases",
};
