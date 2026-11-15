import { toCsv } from "@/lib/csv";
import { findingsFor, getPest, parsePestRange } from "@/lib/pest";
import { viewerId } from "@/lib/workspace";

const NO_STORE = { "cache-control": "private, no-store" };

export async function GET(request: Request) {
  const owner = await viewerId();
  if (!owner) return new Response("Sign in required", { status: 401, headers: NO_STORE });
  const file = await getPest();
  if (!file) return new Response("Pest list not generated yet", { status: 404, headers: NO_STORE });
  const range = parsePestRange(new URL(request.url).searchParams.get("range"));
  const rows = findingsFor(file, range).map((f) => [
    f.inLatestWeek ? "yes" : "no",
    f.date,
    f.restaurant,
    f.address,
    f.communityArea?.name ?? "",
    f.result,
    f.inspectionType,
    f.risk ?? "",
    f.pestTerms.join("; "),
    f.pestTermsGeneralOnly ? "no" : "yes",
    f.pestFindings2y,
    f.lastInspection?.date ?? "",
    f.lastInspection?.result ?? "",
    f.otherLocations,
    f.otherLocationsPest365,
    f.contact?.phone ?? "",
    f.contact?.website ?? "",
    f.contact?.source ?? "",
    f.licenseNo,
    f.inspectionId,
    "",
    "",
    "",
  ]);
  const body = toCsv(
    [
      "in_latest_week",
      "inspection_date",
      "restaurant",
      "address",
      "community_area",
      "result",
      "inspection_type",
      "risk",
      "pest_terms",
      "specific_pest_term",
      "pest_findings_prior_2y",
      "last_inspection_date",
      "last_inspection_result",
      "other_locations_same_name",
      "other_locations_pest_findings_365d",
      "phone",
      "website",
      "contact_source",
      "license_no",
      "inspection_id",
      "date_contacted",
      "outcome",
      "notes",
    ],
    rows,
  );
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-pest-pilot-${file.asOf}.csv"`,
      ...NO_STORE,
    },
  });
}
