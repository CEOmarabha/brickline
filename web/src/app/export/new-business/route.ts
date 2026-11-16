import { toCsv } from "@/lib/csv";
import { areaNames, getSnapshot } from "@/lib/snapshot";
import { viewerId } from "@/lib/workspace";

const NO_STORE = { "cache-control": "private, no-store" };

export async function GET() {
  const owner = await viewerId();
  if (!owner) return new Response("Sign in required", { status: 401, headers: NO_STORE });
  const snap = await getSnapshot();
  const names = areaNames(snap);
  const { spaces } = snap.commercial.newBusiness;
  const rows = spaces.map((s) => [
    s.permitDate,
    s.ageDays,
    s.address,
    s.communityArea ? (names.get(s.communityArea) ?? "") : "",
    s.class,
    s.reportedCost,
    s.workDescription,
    s.contractors.map((c) => `${c.name} (${c.role})`).join("; "),
    s.applicant ?? "",
    s.owner.company ? "company" : "individual",
    s.owner.company ? (s.owner.name ?? "") : "",
    s.owner.company ? (s.owner.mailing ?? "") : "",
    s.alsoClosedRestaurant ? "yes" : "no",
    s.historicalRate,
    s.classRate,
    s.id.replace(/^nb-/, ""),
    s.sourceUrl,
    "",
    "",
    "",
  ]);
  const body = toCsv(
    [
      "permit_date",
      "days_since_permit",
      "address",
      "community_area",
      "address_class",
      "permit_reported_cost",
      "work_description",
      "contractors_on_permit",
      "applicant",
      "owner_type",
      "owner_name_companies_only",
      "owner_mailing_companies_only",
      "also_closed_restaurant",
      "historical_rate_new_license_within_a_year",
      "class_rate_unadjusted",
      "permit_id",
      "source_url",
      "date_contacted",
      "outcome",
      "notes",
    ],
    rows,
  );
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-new-business-${snap.meta.dataAsOf.permits}.csv"`,
      ...NO_STORE,
    },
  });
}
