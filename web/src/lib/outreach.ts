import { dateLabel } from "@/lib/format";
import { tradeNoun } from "@/lib/insights";
import type { Lead, Snapshot, TradeKey } from "@/lib/snapshot";
import { replyCode } from "@/lib/reply-code";
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
  /** Printed on the draft; an owner who quotes it can be matched to this lead (see `/leads/replies`). */
  replyCode: string;
  /**
   * Letters only. Illinois 815 ILCS 505/2PP: a solicitation letter must say at the top, in at least 14-point bold
   * type in a black-outlined box, that it is not a bill, that it is a solicitation, and any affiliation or lack of it.
   */
  disclosure?: string;
}

interface LetterContext {
  address: string;
  business: string;
  phone: string;
  noun: string;
  where: string;
}

/** Tax-roll names can be fragments like "2315 2"; address those letters to the property owner instead. */
function ownerGreeting(name: string | null): string {
  return name && /[A-Za-z]{2,}/.test(name) ? `Dear ${name},` : "Dear Property Owner,";
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

/**
 * A first-touch draft for a human to review and send. Never auto-sent. Carries the lead's reply code; letters also
 * carry the not-a-bill disclosure and the contractor's license number (docs/18 §5).
 */
export function draftOutreach(lead: Lead, ws: Workspace, snap: Snapshot, areaName: string | null): Draft {
  const draft = firstTouch(lead, ws, snap, areaName);
  const code = replyCode(ws.id, lead.id);
  const lines = draft.body.split("\n");
  const business = ws.businessName || "[Your company]";
  const address = ws.mailingAddress || "[your mailing address]";
  const sincerely = lines.indexOf("Sincerely,");
  const at = sincerely >= 0 ? sincerely : lines.lastIndexOf(business);
  const ref =
    draft.channel === "letter"
      ? `Reference code ${code}: please mention it when you call or write, so we know which property you mean.`
      : `Reference code ${code} (quote it in a reply so we can find this property).`;
  lines.splice(at < 0 ? lines.length : at, 0, ref, "");
  if (draft.channel !== "letter") {
    const optOut = lines.findIndex((l) => l.startsWith("Reply \"unsubscribe\""));
    lines.splice(optOut < 0 ? lines.length : optOut, 0, `This email is an advertisement from ${business}, ${address}.`);
    return { ...draft, body: lines.join("\n"), replyCode: code };
  }
  const signature = lines.lastIndexOf(address);
  lines.splice(signature < 0 ? lines.length : signature + 1, 0, `Chicago license no. ${ws.licenseNo || "[license number]"}`);
  const disclosure =
    `THIS IS NOT A BILL. This letter is a solicitation for contracting services from ${business}, a private ` +
    `contractor. ${business} is not affiliated with the City of Chicago or any other government agency.`;
  return { ...draft, body: lines.join("\n"), replyCode: code, disclosure };
}

function firstTouch(lead: Lead, ws: Workspace, snap: Snapshot, areaName: string | null): Omit<Draft, "replyCode"> {
  const business = ws.businessName || "[Your company]";
  const phone = ws.phone || "[phone]";
  const address = ws.mailingAddress || "[your mailing address]";
  const trade: TradeKey = ws.trade;
  const noun = tradeNoun(trade);
  const where = areaName ? ` in ${areaName}` : "";

  if (lead.kind === "violation") {
    const greeting = ownerGreeting(lead.owner.name);
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
        "Individual owners: mail first. Call or text only a number from a marketing-permitted provider that passed a Do Not Call scrub, by hand, 9:00-20:00; no autodialer or recorded voice.",
        "Keep the not-a-bill box at the top (14-point bold, outlined), the license number, the not-affiliated line and the opt-out.",
      ],
    };
  }

  if (lead.kind === "closed_restaurant") {
    const greeting = ownerGreeting(lead.owner.name);
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
          ? "Company-owned: business-to-business mail or email to a business contact is fine; call the business line by hand."
          : "Individual owners: mail first. Call or text only a number from a marketing-permitted provider that passed a Do Not Call scrub, by hand, 9:00-20:00; no autodialer or recorded voice.",
        "Keep the not-a-bill box at the top (14-point bold, outlined), the license number, the not-affiliated line and the opt-out.",
        "Don't mention the restaurant, its closing or any inspection or public record; the letter stands on its own offer to prepare the space.",
        "Pilot list: the contractor audience is unproven, so record outcomes for every lead you work.",
      ],
    };
  }

  if (lead.kind !== "investor_purchase") {
    const greeting = ownerGreeting(lead.owner.name);
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
        "Individual owners: mail first. Call or text only a number from a marketing-permitted provider that passed a Do Not Call scrub, by hand, 9:00-20:00; no autodialer or recorded voice.",
        "Keep the not-a-bill box at the top (14-point bold, outlined), the license number, the not-affiliated line and the opt-out.",
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
      "Business-to-business email is allowed under CAN-SPAM when it says it is an advertisement and has your real name, postal address and a working opt-out.",
      "Calls to the company's business line are fine; no autodialed or prerecorded calls or texts to cell phones.",
    ],
  };
}
