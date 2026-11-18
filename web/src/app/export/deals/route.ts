import { toCsv } from "@/lib/csv";
import { getDeals, getPartners } from "@/lib/deal-store";
import { BUYER_TYPE_LABEL, CHANNEL_LABEL, DEAL_FEE_MODEL_LABEL, DEAL_SOURCE_LABEL, DEAL_STATUS_LABEL } from "@/lib/deals";
import { todayChicago } from "@/lib/pipeline";
import { viewerId } from "@/lib/workspace";

export async function GET() {
  const owner = await viewerId();
  if (!owner) return new Response("Sign in required", { status: 401, headers: { "cache-control": "private, no-store" } });
  const [deals, partners] = await Promise.all([getDeals(owner), getPartners(owner)]);
  const partnerName = new Map(partners.map((p) => [p.id, p.name]));
  const rows = deals.map((d) => [
    d.id,
    d.title,
    DEAL_STATUS_LABEL[d.status],
    d.status === "opted_out" ? "yes" : "",
    DEAL_SOURCE_LABEL[d.source],
    d.sourceRef,
    d.buyerName,
    BUYER_TYPE_LABEL[d.buyerType],
    CHANNEL_LABEL[d.contactChannel],
    d.contactInfo,
    d.eventDate ?? "",
    d.guests === null ? "" : d.guests,
    d.location,
    d.needs,
    d.budgetUsd === null ? "" : d.budgetUsd.toFixed(2),
    d.lostReason,
    d.partnerIds.map((id) => partnerName.get(id) ?? "").filter(Boolean).join("; "),
    d.quoteUsd === null ? "" : d.quoteUsd.toFixed(2),
    d.feeUsd === null ? "" : d.feeUsd.toFixed(2),
    d.feeModel === "" ? "" : DEAL_FEE_MODEL_LABEL[d.feeModel],
    d.feeCollected ? "yes" : "",
    d.nextFollowUp ?? "",
    d.notes,
    d.createdAt.toISOString(),
    d.updatedAt.toISOString(),
  ]);
  const body = toCsv(
    [
      "deal_id",
      "title",
      "status",
      "do_not_contact",
      "source",
      "source_link_or_id",
      "buyer_name",
      "buyer_type",
      "contact_channel",
      "contact_handle_or_info",
      "event_or_job_date",
      "guests_or_size",
      "location",
      "needs",
      "budget_usd",
      "lost_reason",
      "partners",
      "quote_usd",
      "your_fee_usd",
      "fee_model",
      "fee_collected",
      "next_follow_up",
      "notes",
      "created_at",
      "updated_at",
    ],
    rows,
  );
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-deals-${todayChicago()}.csv"`,
      "cache-control": "private, no-store",
    },
  });
}
