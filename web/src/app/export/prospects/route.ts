import { toCsv } from "@/lib/csv";
import { PROSPECT_STATUS_LABEL, todayChicago } from "@/lib/pipeline";
import { getPipeline } from "@/lib/prospect-pipeline";
import { getProspects } from "@/lib/prospects";
import { viewerId } from "@/lib/workspace";

export async function GET() {
  const owner = await viewerId();
  if (!owner) return new Response("Sign in required", { status: 401, headers: { "cache-control": "private, no-store" } });
  const [file, pipeline] = await Promise.all([getProspects(), getPipeline(owner)]);
  const byId = new Map(file.prospects.map((p) => [p.id, p]));
  const rows = [...pipeline.values()]
    .sort((a, b) => a.prospectId.localeCompare(b.prospectId))
    .map((r) => {
      const p = byId.get(r.prospectId);
      return [
        r.prospectId,
        p?.company ?? "",
        p?.trade ?? "",
        PROSPECT_STATUS_LABEL[r.status],
        r.contactName,
        r.email,
        r.phone,
        r.website,
        r.sequenceStep,
        r.nextFollowUp ?? "",
        r.notes,
        r.updatedAt.toISOString(),
        r.monthlyValueUsd === null ? "" : r.monthlyValueUsd.toFixed(2),
        r.feeModel,
      ];
    });
  const body = toCsv(
    [
      "prospect_id",
      "company",
      "trade",
      "status",
      "contact_name",
      "email",
      "phone",
      "website",
      "emails_sent",
      "next_follow_up",
      "notes",
      "updated_at",
      "monthly_value_usd",
      "fee_model",
    ],
    rows,
  );
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-prospect-pipeline-${todayChicago()}.csv"`,
      "cache-control": "private, no-store",
    },
  });
}
