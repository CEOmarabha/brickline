import { BUYER_LIST_KEYS, getBuyers, listOf, parseBuyerList } from "@/lib/buyers";
import { toCsv } from "@/lib/csv";
import { viewerId } from "@/lib/workspace";

const NO_STORE = { "cache-control": "private, no-store" };

export async function GET(request: Request) {
  const owner = await viewerId();
  if (!owner) return new Response("Sign in required", { status: 401, headers: NO_STORE });
  const key = parseBuyerList(new URL(request.url).searchParams.get("list"));
  if (!key) {
    return new Response(`Unknown list. Use list=${BUYER_LIST_KEYS.join("|")}`, { status: 400, headers: NO_STORE });
  }
  const file = await getBuyers();
  if (!file) return new Response("Buyers list not generated yet", { status: 404, headers: NO_STORE });
  const list = listOf(file, key);
  if (!list) return new Response("This list is not in the buyers file", { status: 404, headers: NO_STORE });
  const labels = new Map(list.segments.map((s) => [s.key, s.label]));
  const rows = list.buyers.map((b) => [
    labels.get(b.segment) ?? b.segment,
    b.name,
    b.category ?? "",
    b.address ?? "",
    b.phone ?? "",
    b.website ?? "",
    b.email ?? "",
    b.sources.join("; "),
    b.evidence,
    b.permits ?? "",
    b.lastPermit ?? "",
    "",
    "",
    "",
  ]);
  const body = toCsv(
    [
      "buyer_type",
      "company",
      "category",
      "address",
      "phone",
      "website",
      "email",
      "sources",
      "evidence",
      "permits_last_12_months",
      "latest_permit_date",
      "date_contacted",
      "outcome",
      "notes",
    ],
    rows,
  );
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-buyers-${key}-${file.asOf}.csv"`,
      ...NO_STORE,
    },
  });
}
