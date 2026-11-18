"use client";

import { Ban, Check, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { EnumSelect, SAVE_FAILED, useRun } from "@/components/deal-fields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { UserError } from "@/lib/action-result";
import {
  changeDealStatus,
  markFeeCollected,
  recordQuoteAndFee,
  setDealPartners,
  setNextFollowUp,
  updateDeal,
} from "@/lib/deal-actions";
import {
  BUYER_TYPE_LABEL,
  CHANNEL_LABEL,
  cleanDealFields,
  cleanQuoteFee,
  type ContactChannel,
  DEAL_FEE_MODEL_LABEL,
  DEAL_SOURCE_LABEL,
  DEAL_STATUS_LABEL,
  DEAL_STATUS_VALUES,
  type DealFeeModel,
  type DealSource,
  type DealStatus,
  FEE_MODEL_VALUES,
  type BuyerType,
  isDealDue,
  isOptedOut,
  OPTED_OUT_LOCKED,
} from "@/lib/deals";
import { isHttpUrl } from "@/lib/links";
import { centsToInput, dollarsToCents } from "@/lib/money-input";
import { cn } from "@/lib/utils";

export interface DealView {
  id: string;
  title: string;
  status: DealStatus;
  source: DealSource;
  sourceRef: string;
  buyerName: string;
  buyerType: BuyerType;
  contactChannel: ContactChannel;
  contactInfo: string;
  eventDate: string | null;
  guests: number | null;
  location: string;
  needs: string;
  budgetUsd: number | null;
  lostReason: string;
  partnerIds: string[];
  quoteUsd: number | null;
  feeUsd: number | null;
  feeModel: DealFeeModel | "";
  feeCollected: boolean;
  nextFollowUp: string | null;
  notes: string;
}

export interface DealHistoryItem {
  id: number;
  status: DealStatus;
  note: string;
  at: string;
}

export interface PartnerChoice {
  id: string;
  name: string;
  services: string;
  agreementSigned: boolean;
}

const OPT_OUT_CONFIRM =
  "Mark this buyer as opted out?\n\nThis cannot be undone: drafts are locked, the follow-up is cleared and the status can never be changed back, so you will never message them again.";

function errorMessage(error: unknown): string {
  return error instanceof UserError ? error.message : SAVE_FAILED;
}

export function DealStatusSection({ deal, today }: { deal: DealView; today: string }) {
  const { pending, run } = useRun();
  const [lostReason, setLostReason] = useState(deal.lostReason);
  const [followUp, setFollowUp] = useState(deal.nextFollowUp ?? "");
  const locked = isOptedOut(deal.status);
  const due = isDealDue(deal, today);

  function setStatus(status: DealStatus) {
    if (status === "opted_out" && !window.confirm(OPT_OUT_CONFIRM)) return;
    const options = status === "lost" ? { lostReason } : undefined;
    run(() => changeDealStatus(deal.id, status, options), `Marked as ${DEAL_STATUS_LABEL[status]}`);
  }

  function saveFollowUp(date: string | null) {
    run(() => setNextFollowUp(deal.id, date), date ? "Follow-up saved" : "Follow-up cleared");
  }

  return (
    <div className="space-y-4">
      {locked && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
          <Ban className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
          <div>
            <div className="font-medium text-destructive">Do not contact</div>
            <p className="text-muted-foreground">{OPTED_OUT_LOCKED} Drafts are locked and no follow-up can be set.</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2" role="group" aria-label="Deal status">
        {DEAL_STATUS_VALUES.map((s) => (
          <Button
            key={s}
            type="button"
            size="sm"
            variant={deal.status === s ? "default" : s === "opted_out" ? "destructive" : "outline"}
            disabled={pending || (locked && s !== "opted_out")}
            aria-pressed={deal.status === s}
            onClick={() => setStatus(s)}
          >
            {DEAL_STATUS_LABEL[s]}
          </Button>
        ))}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="deal-lost-reason">Reason if lost (optional)</Label>
        <Input
          id="deal-lost-reason"
          value={lostReason}
          onChange={(e) => setLostReason(e.target.value)}
          maxLength={200}
          placeholder="e.g. went with a friend's caterer"
          disabled={locked}
          autoComplete="off"
        />
        <p className="text-xs text-muted-foreground">Saved when you press Lost.</p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="deal-follow-up">Next follow-up</Label>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            id="deal-follow-up"
            type="date"
            value={followUp}
            onChange={(e) => setFollowUp(e.target.value)}
            disabled={locked}
            className="w-44"
          />
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={pending || locked || followUp === (deal.nextFollowUp ?? "")}
            onClick={() => saveFollowUp(followUp || null)}
          >
            Save follow-up
          </Button>
          {deal.nextFollowUp && !locked && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={pending}
              onClick={() => {
                setFollowUp("");
                saveFollowUp(null);
              }}
            >
              Clear
            </Button>
          )}
        </div>
        {deal.nextFollowUp && (
          <p className={cn("text-xs", due ? "font-medium text-amber-700" : "text-muted-foreground")}>
            Follow up {deal.nextFollowUp}
            {due ? (deal.nextFollowUp < today ? " (overdue)" : " (due today)") : ""}
          </p>
        )}
      </div>
    </div>
  );
}

const TYPE_ITEMS: Record<string, string> = BUYER_TYPE_LABEL;
const CHANNEL_ITEMS: Record<string, string> = CHANNEL_LABEL;
const SOURCE_ITEMS: Record<string, string> = DEAL_SOURCE_LABEL;

export function DealDetailsForm({ deal, leadLink }: { deal: DealView; leadLink: string | null }) {
  const { pending, run } = useRun();
  const [title, setTitle] = useState(deal.title);
  const [buyerName, setBuyerName] = useState(deal.buyerName);
  const [buyerType, setBuyerType] = useState<string>(deal.buyerType);
  const [channel, setChannel] = useState<string>(deal.contactChannel);
  const [contactInfo, setContactInfo] = useState(deal.contactInfo);
  const [source, setSource] = useState<string>(deal.source);
  const [sourceRef, setSourceRef] = useState(deal.sourceRef);
  const [eventDate, setEventDate] = useState(deal.eventDate ?? "");
  const [guests, setGuests] = useState(deal.guests === null ? "" : String(deal.guests));
  const [location, setLocation] = useState(deal.location);
  const [budget, setBudget] = useState(centsToInput(dollarsToCents(deal.budgetUsd)));
  const [needs, setNeeds] = useState(deal.needs);
  const [notes, setNotes] = useState(deal.notes);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const fields = {
      title,
      buyerName,
      buyerType,
      contactChannel: channel,
      contactInfo,
      source,
      sourceRef,
      eventDate: eventDate || null,
      guests,
      location,
      budget,
      needs,
      notes,
    };
    try {
      const clean = cleanDealFields(fields);
      setSourceRef(clean.sourceRef ?? sourceRef);
    } catch (error) {
      toast.error(errorMessage(error));
      return;
    }
    run(() => updateDeal(deal.id, fields), "Saved");
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="dd-title">Title</Label>
          <Input id="dd-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dd-buyer">Buyer name</Label>
          <Input id="dd-buyer" value={buyerName} onChange={(e) => setBuyerName(e.target.value)} maxLength={120} autoComplete="off" />
        </div>
        <EnumSelect id="dd-type" label="Buyer type" value={buyerType} items={TYPE_ITEMS} onChange={setBuyerType} />
        <EnumSelect id="dd-channel" label="Contact channel" value={channel} items={CHANNEL_ITEMS} onChange={setChannel} />
        <div className="space-y-1.5">
          <Label htmlFor="dd-contact">Handle, email or phone</Label>
          <Input
            id="dd-contact"
            value={contactInfo}
            onChange={(e) => setContactInfo(e.target.value)}
            maxLength={200}
            autoComplete="off"
          />
        </div>
        <EnumSelect id="dd-source" label="Source" value={source} items={SOURCE_ITEMS} onChange={setSource} />
        <div className="space-y-1.5">
          <Label htmlFor="dd-ref">Link or id of the public post or page</Label>
          <Input
            id="dd-ref"
            value={sourceRef}
            onChange={(e) => setSourceRef(e.target.value)}
            maxLength={400}
            placeholder="https://"
            autoComplete="off"
          />
          {isHttpUrl(deal.sourceRef) && (
            <a
              href={deal.sourceRef}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="inline-flex items-center gap-1 text-xs text-primary underline-offset-4 hover:underline"
            >
              Open the original <ExternalLink className="size-3" aria-hidden />
            </a>
          )}
          {leadLink && (
            <Link href={leadLink} className="text-xs text-primary underline-offset-4 hover:underline">
              Open this lead in Brickline
            </Link>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dd-date">Event or job date</Label>
          <Input id="dd-date" type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dd-guests">Guests or size</Label>
          <Input
            id="dd-guests"
            inputMode="numeric"
            value={guests}
            onChange={(e) => setGuests(e.target.value)}
            maxLength={9}
            placeholder="e.g. 60"
            autoComplete="off"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dd-location">Location</Label>
          <Input id="dd-location" value={location} onChange={(e) => setLocation(e.target.value)} maxLength={200} autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dd-budget">Budget ($)</Label>
          <Input
            id="dd-budget"
            inputMode="decimal"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            maxLength={14}
            placeholder="e.g. 2500"
            autoComplete="off"
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="dd-needs">What they need</Label>
        <Textarea id="dd-needs" value={needs} onChange={(e) => setNeeds(e.target.value)} rows={3} maxLength={2000} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="dd-notes">Notes</Label>
        <Textarea
          id="dd-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          maxLength={4000}
          placeholder="What they said, what you promised, opt-outs…"
        />
      </div>
      <Button type="submit" variant="secondary" size="sm" disabled={pending}>
        Save details
      </Button>
    </form>
  );
}

const UNSET = "unset";
const FEE_ITEMS: Record<string, string> = {
  [UNSET]: "Not set",
  ...Object.fromEntries(FEE_MODEL_VALUES.map((m) => [m, DEAL_FEE_MODEL_LABEL[m]])),
};

export function DealMoneyForm({ deal }: { deal: DealView }) {
  const { pending, run } = useRun();
  const [quote, setQuote] = useState(centsToInput(dollarsToCents(deal.quoteUsd)));
  const [fee, setFee] = useState(centsToInput(dollarsToCents(deal.feeUsd)));
  const [model, setModel] = useState<string>(deal.feeModel || UNSET);
  const canCollect = (deal.status === "booked" || deal.status === "completed") && deal.feeUsd !== null && deal.feeUsd > 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const fields = { quote, fee, feeModel: model === UNSET ? "" : model };
    try {
      cleanQuoteFee(fields);
    } catch (error) {
      toast.error(errorMessage(error));
      return;
    }
    run(() => recordQuoteAndFee(deal.id, fields), "Quote and fee saved");
  }

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="dm-quote">Quote to the buyer ($)</Label>
            <Input
              id="dm-quote"
              inputMode="decimal"
              value={quote}
              onChange={(e) => setQuote(e.target.value)}
              maxLength={14}
              placeholder="e.g. 1800"
              autoComplete="off"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dm-fee">Your fee ($)</Label>
            <Input
              id="dm-fee"
              inputMode="decimal"
              value={fee}
              onChange={(e) => setFee(e.target.value)}
              maxLength={14}
              placeholder="e.g. 250"
              autoComplete="off"
            />
          </div>
          <div className="sm:col-span-2">
            <EnumSelect id="dm-model" label="How you are paid" value={model} items={FEE_ITEMS} onChange={setModel} />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          The quote is the total price the buyer sees. Your fee is what you earn: part of the quote for a planning fee or
          markup, paid by the partner for a referral fee. Nothing here is estimated.
        </p>
        <Button type="submit" variant="secondary" size="sm" disabled={pending}>
          Save quote and fee
        </Button>
      </form>

      <div className="flex flex-wrap items-center gap-3 border-t pt-3">
        {deal.feeCollected ? (
          <>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-emerald-700">
              <Check className="size-4" aria-hidden /> Fee collected
            </span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => run(() => markFeeCollected(deal.id, false), "Fee marked not collected")}
            >
              Mark not collected
            </Button>
          </>
        ) : (
          <>
            <Button
              type="button"
              size="sm"
              disabled={pending || !canCollect}
              onClick={() => run(() => markFeeCollected(deal.id, true), "Fee marked collected")}
            >
              Mark fee collected
            </Button>
            {!canCollect && (
              <span className="text-xs text-muted-foreground">Needs a saved fee and a Booked or Completed deal.</span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export function DealPartnersPicker({
  dealId,
  attached,
  partners,
}: {
  dealId: string;
  attached: string[];
  partners: PartnerChoice[];
}) {
  const { pending, run } = useRun();
  const [selected, setSelected] = useState<string[]>(attached);
  const same = selected.length === attached.length && selected.every((id) => attached.includes(id));

  function toggle(id: string) {
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  }

  if (partners.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No partners yet.{" "}
        <Link href="/deals/partners" className="text-primary underline-offset-4 hover:underline">
          Add a partner vendor
        </Link>{" "}
        to attach it to this deal.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <ul className="divide-y rounded-md border text-sm">
        {partners.map((p) => (
          <li key={p.id}>
            <label className="flex cursor-pointer items-start gap-3 px-3 py-2 hover:bg-muted/50">
              <input
                type="checkbox"
                className="mt-1 size-4 accent-primary"
                checked={selected.includes(p.id)}
                onChange={() => toggle(p.id)}
              />
              <span className="min-w-0">
                <span className="font-medium">{p.name}</span>
                {!p.agreementSigned && <span className="ml-2 text-xs text-amber-700">no agreement yet</span>}
                {p.services && <span className="block text-xs text-muted-foreground">{p.services}</span>}
              </span>
            </label>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={pending || same}
          onClick={() => run(() => setDealPartners(dealId, selected), "Partners saved")}
        >
          Save partners
        </Button>
        <Link href="/deals/partners" className="text-xs text-primary underline-offset-4 hover:underline">
          Manage partners
        </Link>
      </div>
    </div>
  );
}

export function DealHistory({ history }: { history: DealHistoryItem[] }) {
  if (history.length === 0) return <p className="text-sm text-muted-foreground">Nothing logged yet.</p>;
  return (
    <ul className="divide-y rounded-md border text-sm">
      {history.map((h) => (
        <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
          <span>{h.note || DEAL_STATUS_LABEL[h.status]}</span>
          <span className="text-xs whitespace-nowrap text-muted-foreground">{h.at}</span>
        </li>
      ))}
    </ul>
  );
}
