import { dateLabel } from "@/lib/format";
import { tradeNoun } from "@/lib/insights";
import type { Lead, Snapshot, TradeKey } from "@/lib/snapshot";
import type { Workspace } from "@/lib/workspace";

export interface EmailDraft {
  subject: string;
  body: string;
}

export interface Draft {
  channel: "letter" | "email";
  subject?: string;
  body: string;
  compliance: string[];
}

interface LetterContext {
  address: string;
  business: string;
  phone: string;
  noun: string;
  where: string;
}

/** Body paragraphs for owner letters triggered by 311 signals. They never mention the 311 report itself. */
function ownerLetterBody(kind: "complaint" | "porch_request" | "vacant", c: LetterContext): string[] {
  if (kind === "porch_request") {
    return [
      `${c.business} is a local porch and deck contractor serving properties${c.where}. Porches take a beating from Chicago weather, and small problems with posts, stairs and railings are much cheaper to fix early.`,
      `We're offering owners near ${c.address} a free porch assessment: we walk the porch, tell you plainly what it needs (including nothing, if that's the case), and send a written estimate. We handle the permit paperwork too.`,
    ];
  }
  if (kind === "vacant") {
    return [
      `${c.business} helps owners of Chicago properties${c.where} secure, repair and renovate buildings that aren't in regular use. ${c.address} may be one of them, so we wanted to reach you directly.`,
      `If you'd like help with ${c.noun} work, securing the building, or a full renovation, we can walk the property this week and give you a written estimate at no cost. If you're thinking about selling instead, we're glad to talk through what repairs are worth doing first.`,
    ];
  }
  return [
    `${c.business} is a local contractor serving properties${c.where}. Older Chicago buildings often need ${c.noun} attention before it becomes urgent, and fixing it early costs less.`,
    `We're offering owners near ${c.address} a free exterior check: we look at the property, tell you plainly what needs work and what doesn't, and send a written estimate. We handle the permit paperwork too.`,
  ];
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

  if (lead.kind === "closed_restaurant") {
    const greeting = lead.owner.name ? `Dear ${lead.owner.name},` : "Dear Property Owner,";
    const company = lead.owner.type === "company";
    return {
      channel: "letter",
      body: [
        greeting,
        "",
        `If you're preparing the space at ${lead.address} for a new tenant, ${business} can help. We prepare and build out commercial space for the next operator${where}: demolition and clean-out, coordination of kitchen, hood, plumbing and electrical rough-in, permit paperwork, and a space that's ready for move-in.`,
        "",
        "We can walk the space this week and send a written estimate at no cost. If the space is already spoken for, or you have a contractor lined up, please disregard this note.",
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
        company
          ? "Company-owned: business-to-business mail or email to a business contact is fine; call a business line, not a personal cell."
          : "Mail only for individual owners; don't cold-call or text personal numbers.",
        "Keep the not-affiliated-with-the-City line and an opt-out.",
        "Don't mention the restaurant, its closing or any inspection or public record; the letter stands on its own offer to prepare the space.",
        "Pilot list: the contractor audience is unproven, so record outcomes for every lead you work.",
      ],
    };
  }

  if (lead.kind !== "investor_purchase") {
    const greeting = lead.owner.name ? `Dear ${lead.owner.name},` : "Dear Property Owner,";
    const lines = ownerLetterBody(lead.kind, { address: lead.address, business, phone, noun, where });
    return {
      channel: "letter",
      body: [
        greeting,
        "",
        ...lines.flatMap((line) => [line, ""]),
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
        "Don't mention the 311 report or the property's records; the letter stands on its own offer.",
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
