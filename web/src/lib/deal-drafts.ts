import {
  type BuyerType,
  type ContactChannel,
  type DealFeeModel,
  type DealSource,
  type DealStatus,
  isOptedOut,
} from "@/lib/deals";

/*
 * Message drafts for the founder to review, edit and send himself, one buyer at a time. Deterministic templates, no
 * AI. Rules baked into every draft: a personal one-to-one tone, who is writing, a clear opt-out line, no claim that
 * can't be verified (no "cheaper than the market"), no mention of how the buyer was found beyond general terms, and
 * no suggestion of any link to the City or the platform the buyer was found on.
 */

export type DraftKind = "dm" | "email" | "follow_up" | "quote";

export const DRAFT_LABEL: Record<DraftKind, string> = {
  dm: "First message (social DM)",
  email: "First message (email)",
  follow_up: "Follow-up",
  quote: "Quote cover note",
};

export interface DraftSender {
  /** The founder's name; "[Your name]" until filled in. */
  name: string;
  business: string;
  /** A real postal address, required in every commercial email. */
  address: string;
}

export interface DraftInput {
  status: DealStatus;
  source: DealSource;
  buyerType: BuyerType;
  buyerName: string;
  channel: ContactChannel;
  /** YYYY-MM-DD; only the month is ever used. */
  eventDate: string | null;
  /** The occasion in general terms, e.g. "a graduation party". Blank gives "an event" or "a project". */
  occasion: string;
  quoteUsd: number | null;
  feeUsd: number | null;
  feeModel: DealFeeModel | "";
  partnerNames: string[];
  /** Another deal with the same handle, email or phone number already opted out. */
  matchesOptedOut: boolean;
  sender: DraftSender;
}

export interface Draft {
  kind: DraftKind;
  label: string;
  /** Present for email drafts. */
  subject?: string;
  body: string;
}

export type DraftResult =
  | { refused: true; reason: string }
  | { refused: false; drafts: Draft[]; warnings: string[] };

export const DEFAULT_SENDER_NAME = "[Your name]";
export const DEFAULT_SENDER_BUSINESS = "[Your business name]";
export const DEFAULT_SENDER_ADDRESS = "[your mailing address]";

export const OPT_OUT_REFUSAL =
  "This buyer opted out, so no message is drafted. Do not contact them again on any channel.";

export const MATCHES_OPT_OUT_REFUSAL =
  "This handle, email or phone number matches a buyer on another deal who opted out, so no message is drafted. Do not contact them again.";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

function monthPhrase(date: string | null): string {
  if (!date) return "";
  const month = Number(date.slice(5, 7));
  return month >= 1 && month <= 12 ? ` in ${MONTHS[month - 1]}` : "";
}

function firstName(name: string): string {
  const first = name.trim().split(/\s+/)[0] ?? "";
  return /^[\p{L}][\p{L}'’.-]*$/u.test(first) ? first : "";
}

function greeting(input: DraftInput): string {
  if (input.buyerType === "person") {
    const first = firstName(input.buyerName);
    return first ? `Hi ${first},` : "Hi,";
  }
  const org = input.buyerName.trim();
  return org ? `Hello ${org} team,` : "Hello,";
}

function what(input: DraftInput): string {
  const o = input.occasion.trim();
  if (o !== "") return o;
  return input.source === "letter_callback" || input.source === "pilot_list" ? "a project" : "an event";
}

function topicOf(input: DraftInput): string {
  return `${what(input)}${monthPhrase(input.eventDate)}`;
}

/** One sentence on why the founder is writing, in general terms only. */
function whyWriting(input: DraftInput): string {
  const topic = topicOf(input);
  const name = input.buyerName.trim();
  switch (input.source) {
    case "letter_callback":
      return "Thanks for getting back to me about my letter.";
    case "event_data":
      return `I came across a public listing for ${topic} and wanted to reach out.`;
    case "pilot_list":
      return `I came across ${name || "your business"} in public business listings and wanted to ask about ${topic}.`;
    case "social":
      return input.buyerType === "organization" ? `I saw ${name || "your team"} is planning ${topic}.` : `I saw you're planning ${topic}.`;
    default:
      return `I'm reaching out about ${topic}.`;
  }
}

/** What the founder does and how he is paid, in words the buyer can check. Never claims a fee model the deal doesn't use. */
function offer(input: DraftInput): string {
  const base = "I help people line up local vendors, such as rentals and catering, through one point of contact.";
  switch (input.feeModel) {
    case "referral_fee":
      return `${base} I'll tell you up front how I'm paid.`;
    case "markup":
      return `${base} You'll get a clear, itemized price.`;
    case "none":
      return `${base} There's no fee from me.`;
    default:
      return `${base} I charge a transparent flat planning fee.`;
  }
}

const OPT_OUT = `If you'd rather not hear from me, just reply STOP or say "no thanks" and I won't message you again.`;

function signature(input: DraftInput): string {
  const { name, business, address } = input.sender;
  return [name, business, address].join("\n");
}

function commercialLine(input: DraftInput): string {
  return `This is a one-to-one commercial message from ${input.sender.business}.`;
}

function dm(input: DraftInput): Draft {
  const { name, business } = input.sender;
  const body = [
    `${greeting(input)} I'm ${name} from ${business} here in Chicago.`,
    whyWriting(input),
    offer(input),
    `Would a quick, no-obligation outline be useful? ${OPT_OUT}`,
  ].join(" ");
  return { kind: "dm", label: DRAFT_LABEL.dm, body };
}

function email(input: DraftInput): Draft {
  const { name, business } = input.sender;
  const subject = input.source === "letter_callback" ? "Thanks for getting back to me" : `Help with ${topicOf(input)}?`;
  const body = [
    greeting(input),
    "",
    whyWriting(input),
    "",
    `I'm ${name} with ${business} here in Chicago. ${offer(input)}`,
    "",
    "If it's useful, I can send a short, no-obligation outline. These details would help:",
    "- the date and where it will be",
    "- roughly how many guests, or the size of the job",
    "- what you need and a rough budget range",
    "",
    OPT_OUT,
    "",
    "Thanks,",
    signature(input),
    "",
    commercialLine(input),
  ].join("\n");
  return { kind: "email", label: DRAFT_LABEL.email, subject, body };
}

function followUp(input: DraftInput): Draft {
  const { name, business } = input.sender;
  const topic = topicOf(input);
  const core = `I'm following up once on my earlier note about ${topic}. If it's still on your list, I'm happy to send a short, no-obligation outline. If plans changed or you're all set, no problem at all, and I won't keep following up.`;
  if (input.channel === "email") {
    return {
      kind: "follow_up",
      label: DRAFT_LABEL.follow_up,
      subject: `Quick follow-up on ${topic}`,
      body: [
        greeting(input),
        "",
        `It's ${name} from ${business} again. ${core}`,
        "",
        OPT_OUT,
        "",
        "Thanks,",
        signature(input),
        "",
        commercialLine(input),
      ].join("\n"),
    };
  }
  return {
    kind: "follow_up",
    label: DRAFT_LABEL.follow_up,
    body: `${greeting(input)} it's ${name} from ${business} again. ${core} ${OPT_OUT}`,
  };
}

function feeSentence(input: DraftInput): string {
  const fee = input.feeUsd !== null && input.feeUsd > 0 ? usd.format(input.feeUsd) : null;
  const vendors = input.partnerNames.length > 0 ? input.partnerNames.join(" and ") : "the vendor";
  switch (input.feeModel) {
    case "planning_fee":
      return `The total includes my flat planning fee of ${fee ?? "[$ amount]"}, shown separately so you can see what each part covers.`;
    case "referral_fee":
      return `For transparency: ${vendors} pays me a referral fee when you book.`;
    case "markup":
      return "The total includes my coordination fee.";
    case "none":
      return "";
    default:
      return "[Say how you're paid: a flat planning fee, a referral fee from the vendor, or included in the total.]";
  }
}

function quote(input: DraftInput): Draft {
  const topic = topicOf(input);
  const total = input.quoteUsd !== null ? usd.format(input.quoteUsd) : "[$ total]";
  const vendors = input.partnerNames.length > 0 ? input.partnerNames.join(", ") : "[vendor name]";
  const fee = feeSentence(input);
  const body = [
    greeting(input),
    "",
    `Thanks for the details about ${topic}. Here is the quote.`,
    "",
    `Total: ${total}`,
    "Includes: [list what's included]",
    `Vendor: ${vendors}`,
    ...(fee ? ["", fee] : []),
    "",
    "This quote is valid until [date] and depends on the vendor confirming availability.",
    "",
    `To go ahead, just reply "yes" and I'll confirm with the vendor and send the next steps. Questions are welcome, I'm your one point of contact.`,
    "",
    OPT_OUT,
    "",
    "Thanks,",
    signature(input),
    "",
    commercialLine(input),
  ].join("\n");
  return { kind: "quote", label: DRAFT_LABEL.quote, subject: `Your quote for ${topic}`, body };
}

const CHANNEL_WARNING: Partial<Record<ContactChannel, string>> = {
  phone:
    "Phone: don't text this number without their prior written consent. Call by hand (no autodialer, no recorded or AI voice), or use the email version.",
  in_person: "In person: use these as talking points, and honor a no on the spot.",
  instagram: "Instagram: send it yourself, one person at a time, from your own account and within Instagram's rules.",
  facebook: "Facebook: send it yourself, one person at a time, and check a group's rules before messaging one of its members.",
  tiktok: "TikTok: send it yourself, one person at a time, from your own account and within TikTok's rules.",
};

const isPlaceholder = (v: string) => v.trim() === "" || /^\[.*\]$/.test(v.trim());

/**
 * All four drafts for one deal, or a refusal when the buyer opted out. Placeholders in [brackets] are things the
 * founder must fill in before sending; `warnings` lists what is missing or risky. An opt-out is final: the buyer's own
 * deal and any other deal with the same contact are refused.
 */
export function buildDealDrafts(input: DraftInput): DraftResult {
  if (isOptedOut(input.status)) return { refused: true, reason: OPT_OUT_REFUSAL };
  if (input.matchesOptedOut) return { refused: true, reason: MATCHES_OPT_OUT_REFUSAL };
  const drafts = [dm(input), email(input), followUp(input), quote(input)];
  const warnings: string[] = [];
  const channelWarning = CHANNEL_WARNING[input.channel];
  if (channelWarning) warnings.push(channelWarning);
  if (input.status === "lost") warnings.push("This deal is marked Lost: message them again only if they contact you first.");
  if (input.status === "completed") warnings.push("This deal is Completed: write again only about something new, not a repeat pitch.");
  if (isPlaceholder(input.sender.address)) {
    warnings.push("Add your real mailing address above: every commercial email needs a postal address.");
  }
  if (input.feeModel === "") {
    warnings.push(`The fee model isn't set, so the drafts say "a transparent flat planning fee". Change the wording if you are paid another way.`);
  }
  if (input.quoteUsd === null) warnings.push("No quote amount is saved yet: the quote note shows [$ total].");
  if (input.partnerNames.length === 0) {
    warnings.push("No partner is attached yet. Confirm the partner's price and availability before you quote.");
  }
  if (drafts.some((d) => /\[[^\]]+\]/.test(`${d.subject ?? ""}\n${d.body}`))) {
    warnings.push("Fill in every [bracket] and read each draft before sending: fix anything that isn't true for this buyer.");
  }
  return { refused: false, drafts, warnings };
}

/** The checklist shown next to the drafts. General rules, not legal advice. */
export const COMPLIANCE_CHECKLIST: { rule: string; detail: string }[] = [
  {
    rule: "One-to-one, personal messages only",
    detail: "Write and send each message yourself. No bulk, scheduled or automated DMs, and no tools that message for you.",
  },
  {
    rule: "Respect platform rules and group rules",
    detail: "Follow each platform's terms on business messages and any group's rules on solicitation. If a group bans it, don't.",
  },
  {
    rule: "Honor opt-outs immediately",
    detail: "STOP, no thanks, or any clear no: mark the deal Opted out here. Drafts lock and you never write again.",
  },
  {
    rule: "Email follows CAN-SPAM",
    detail:
      "Your real name and sender address, an honest subject (no Re: or Fwd:), your postal address, a working opt-out honored right away, and a line saying it is a commercial message.",
  },
  {
    rule: "No texts without consent",
    detail: "Don't text a phone number without prior express written consent.",
  },
  {
    rule: "No autodialed or recorded calls",
    detail:
      "Dial by hand only: no autodialer, no prerecorded or AI voice. Call between 8:00 and 17:00, and check the Do Not Call Registry for personal numbers.",
  },
  {
    rule: "Say only what you can verify",
    detail: 'No "cheapest" or "best price". Confirm the partner\'s price and availability before you quote, and say how you are paid.',
  },
  {
    rule: "Keep it general, never imply an affiliation",
    detail: "Mention how you found them only in general terms. Never suggest a link to the City, the platform or the venue.",
  },
];
