import { dateLabel } from "@/lib/format";
import { tradeNoun } from "@/lib/insights";
import type { Lead, Snapshot, TradeKey } from "@/lib/snapshot";
import type { Workspace } from "@/lib/workspace";

export interface Draft {
  channel: "letter" | "email";
  subject?: string;
  body: string;
  compliance: string[];
}

/** A first-touch draft for a human to review and send. Never auto-sent. */
export function draftOutreach(lead: Lead, ws: Workspace, snap: Snapshot, areaName: string | null): Draft {
  const business = ws.businessName || "[Your company]";
  const phone = ws.phone || "[phone]";
  const address = ws.mailingAddress || "[your mailing address]";
  const trade: TradeKey = ws.trade;
  const noun = tradeNoun(trade);
  const where = areaName ? ` in ${areaName}` : "";

  if (lead.kind === "violation") {
    const greeting = lead.owner.name ? `Dear ${lead.owner.name},` : "Dear Property Owner,";
    return {
      channel: "letter",
      body: [
        greeting,
        "",
        `Public City of Chicago building records show a ${noun} repair notice for ${lead.address} dated ${dateLabel(lead.signalDate)}.`,
        "",
        `If you're planning that work, ${business} can help. We handle ${noun} repairs and the permit paperwork for properties${where}, and we can usually inspect within a week and give you a written estimate at no cost.`,
        "",
        `Call ${phone} to schedule a visit, or keep this letter for when you're ready.`,
        "",
        "Sincerely,",
        business,
        address,
        "",
        `${business} is a private contractor and is not affiliated with the City of Chicago. To stop receiving mail from us, call ${phone}.`,
      ].join("\n"),
      compliance: [
        "Mail only for individual owners; don't cold-call or text personal numbers.",
        "Keep the not-affiliated-with-the-City line and an opt-out.",
      ],
    };
  }

  const buyer = lead.buyer.name ?? "there";
  const segment = lead.segment === "2-6 unit flat" ? "2–6 flat" : lead.segment;
  const repeat =
    lead.buyer.purchases24m >= 3
      ? ` and your other ${lead.buyer.purchases24m - 1} recent properties`
      : "";
  return {
    channel: "email",
    subject: `${snap.trades[trade].label} crew for ${lead.address}`,
    body: [
      `Hi ${buyer} team,`,
      "",
      `Congratulations on picking up ${lead.address}. ${business} is a Chicago ${snap.trades[trade].label.toLowerCase()} contractor working with investors on ${segment} rehabs${where}.`,
      "",
      `If there's ${noun} work planned for this property${repeat}, we can walk it this week and turn around a quote in 48 hours. We pull permits and work to your schedule.`,
      "",
      `Worth a quick call? ${phone}`,
      "",
      business,
      address,
      "",
      "Reply \"unsubscribe\" and we won't email again.",
    ].join("\n"),
    compliance: [
      "Business-to-business email is allowed under CAN-SPAM with your real name, postal address and a working opt-out.",
      "Calls to the company's business line are fine; no autodialed or prerecorded calls or texts to cell phones.",
    ],
  };
}
