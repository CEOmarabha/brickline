import { splitMailing, toCsv } from "@/lib/csv";
import { parseFilters, queryLeads } from "@/lib/lead-query";
import { getCloseRates } from "@/lib/outcomes";
import { draftOutreach } from "@/lib/outreach";
import { areaNames, expectedValue, getSnapshot, tradeProbability } from "@/lib/snapshot";
import { getStatuses, getWorkspace, STATUS_LABEL } from "@/lib/workspace";

const MAX_ROWS = 5000;

export async function GET(request: Request) {
  const ws = await getWorkspace();
  if (!ws.signedIn) return new Response("Sign in required", { status: 401 });
  const url = new URL(request.url);
  const format = url.searchParams.get("format") === "mail" ? "mail" : "all";
  const [snap, statuses, rates] = await Promise.all([getSnapshot(), getStatuses(), getCloseRates()]);
  const names = areaNames(snap);
  const leads = queryLeads(snap, ws, statuses, parseFilters(url.searchParams), rates).slice(0, MAX_ROWS);
  const area = (id: number | null) => (id ? (names.get(id) ?? "") : "");
  const stamp = snap.meta.dataAsOf.violations;

  let body: string;
  if (format === "mail") {
    const rows = leads
      .filter((l) => l.owner.mailing)
      .map((l) => {
        const m = splitMailing(l.owner.mailing);
        const draft = draftOutreach(l, ws, snap, area(l.communityArea) || null);
        return [
          l.owner.name ?? "Property Owner",
          m.street,
          m.city,
          m.state,
          m.zip,
          l.address,
          area(l.communityArea),
          l.title,
          l.signalDate,
          draft.body,
          l.id,
        ];
      });
    body = toCsv(
      [
        "recipient",
        "street",
        "city",
        "state",
        "zip",
        "property_address",
        "neighborhood",
        "signal",
        "signal_date",
        "letter_text",
        "lead_id",
      ],
      rows,
    );
  } else {
    body = toCsv(
      [
        "lead_id",
        "kind",
        "priority",
        "status",
        "property_address",
        "neighborhood",
        "signal",
        "signal_date",
        "chance_of_work",
        "expected_value",
        "owner_name",
        "owner_type",
        "owner_mailing",
        "buyer",
        "buyer_purchases_24m",
        "next_step",
        "source_url",
      ],
      leads.map((l) => [
        l.id,
        l.kind,
        l.tier,
        STATUS_LABEL[statuses.get(l.id)?.status ?? "new"],
        l.address,
        area(l.communityArea),
        l.title,
        l.signalDate,
        tradeProbability(l, ws.trade, snap).toFixed(4),
        expectedValue(l, ws.trade, snap, rates).toFixed(2),
        l.owner.name,
        l.owner.type,
        l.owner.mailing,
        l.kind === "investor_purchase" ? l.buyer.name : "",
        l.kind === "investor_purchase" ? l.buyer.purchases24m : "",
        l.action,
        l.sourceUrl,
      ]),
    );
  }

  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="brickline-${format === "mail" ? "mail-merge" : "leads"}-${stamp}.csv"`,
      "cache-control": "private, no-store",
    },
  });
}
