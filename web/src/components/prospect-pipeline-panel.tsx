"use client";

import { Mail } from "lucide-react";
import { useState, useTransition } from "react";
import { toast } from "sonner";
import { ProspectStatusBadge } from "@/components/bits";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ContactValue, SourceLine } from "@/components/contact-bits";
import { type ActionResult, UserError } from "@/lib/action-result";
import type { ContactField, ContactSuggestions } from "@/lib/contacts";
import { isHttpUrl } from "@/lib/links";
import { centsToInput, dollarsToCents } from "@/lib/money-input";
import {
  cleanProspectFields,
  DEAL_STATUSES,
  FEE_MODEL_LABEL,
  FEE_MODELS,
  type FeeModel,
  isDue,
  MAX_SEQUENCE_STEP,
  PROSPECT_STATUS_LABEL,
  PROSPECT_STATUSES,
  type ProspectStatus,
} from "@/lib/pipeline";
import { logEmailSent, saveProspect } from "@/lib/prospect-actions";

export interface PanelState {
  status: ProspectStatus;
  contactName: string;
  email: string;
  phone: string;
  website: string;
  notes: string;
  sequenceStep: number;
  nextFollowUp: string | null;
  monthlyValueUsd: number | null;
  feeModel: FeeModel | "";
}

export interface PanelEvent {
  id: number;
  status: ProspectStatus;
  note: string;
  at: string;
}

function SuggestionRow({
  label,
  field,
  kind = "text",
  note,
  current,
  onUse,
}: {
  label: string;
  field: ContactField;
  kind?: "website" | "text";
  note?: string;
  current?: string;
  onUse?: () => void;
}) {
  const used = current !== undefined && current.trim() === field.value;
  const blocked = current !== undefined && current.trim() !== "" && !used;
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-2">
      <div className="min-w-0 flex-1">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div>
          <ContactValue field={field} kind={kind} />
          {note && <span className="ml-1.5 text-xs text-muted-foreground">({note})</span>}
        </div>
        <SourceLine field={field} />
      </div>
      {onUse && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={used || blocked}
          title={blocked ? "The field already has a value. Clear it to use this suggestion." : undefined}
          onClick={onUse}
        >
          {used ? "Used" : "Use these"}
        </Button>
      )}
    </li>
  );
}

const DAYS_LABEL = ["Day 0", "Day 4", "Day 10"];

const SAVE_FAILED = "Couldn't save. Try again.";

const NOT_SET = "none";
const FEE_ITEMS: Record<string, string> = {
  [NOT_SET]: "Not set",
  ...Object.fromEntries(FEE_MODELS.map((m) => [m, FEE_MODEL_LABEL[m]])),
};

/** Monthly value and fee model of a Pilot or Paying prospect. Remounted (via `key`) whenever the saved values change. */
function DealTerms({
  monthlyValueUsd,
  feeModel,
  pending,
  onSave,
}: {
  monthlyValueUsd: number | null;
  feeModel: FeeModel | "";
  pending: boolean;
  onSave: (fields: { monthlyValue: string; feeModel: string }) => void;
}) {
  const [monthly, setMonthly] = useState(centsToInput(dollarsToCents(monthlyValueUsd)));
  const [fee, setFee] = useState<string>(feeModel || NOT_SET);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const fields = { monthlyValue: monthly, feeModel: fee === NOT_SET ? "" : fee };
    try {
      cleanProspectFields(fields);
    } catch (error) {
      toast.error(error instanceof UserError ? error.message : SAVE_FAILED);
      return;
    }
    onSave(fields);
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border p-4">
      <div>
        <h3 className="text-sm font-medium">Deal terms</h3>
        <p className="text-xs text-muted-foreground">
          Optional. What you actually agreed with this contractor. Totals on the Prospects page add up only the monthly
          values entered here; nothing is estimated.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="pp-monthly">Monthly value ($)</Label>
          <Input
            id="pp-monthly"
            inputMode="decimal"
            autoComplete="off"
            value={monthly}
            onChange={(e) => setMonthly(e.target.value)}
            placeholder="e.g. 500"
            maxLength={14}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pp-fee">Fee model</Label>
          <Select items={FEE_ITEMS} value={fee} onValueChange={(v) => setFee(String(v))}>
            <SelectTrigger id="pp-fee" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(FEE_ITEMS).map(([k, label]) => (
                <SelectItem key={k} value={k}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <Button type="submit" variant="secondary" size="sm" disabled={pending}>
        Save deal terms
      </Button>
    </form>
  );
}

export function ProspectPipelinePanel({
  prospectId,
  state,
  history,
  today,
  suggestions,
}: {
  prospectId: string;
  state: PanelState;
  history: PanelEvent[];
  today: string;
  suggestions: ContactSuggestions | null;
}) {
  const [contactName, setContactName] = useState(state.contactName);
  const [email, setEmail] = useState(state.email);
  const [phone, setPhone] = useState(state.phone);
  const [website, setWebsite] = useState(state.website);
  const [notes, setNotes] = useState(state.notes);
  const [followUp, setFollowUp] = useState(state.nextFollowUp ?? "");
  const [pending, startTransition] = useTransition();

  const nextEmail = state.sequenceStep + 1;
  const due = isDue(state, today);

  function run(action: () => Promise<ActionResult>, success: string) {
    startTransition(async () => {
      try {
        const result = await action();
        if (result.ok) toast.success(success);
        else toast.error(result.error);
      } catch {
        toast.error(SAVE_FAILED);
      }
    });
  }

  function setStatus(status: ProspectStatus) {
    run(() => saveProspect(prospectId, { status }), `Marked as ${PROSPECT_STATUS_LABEL[status]}`);
  }

  function sendEmail() {
    run(() => logEmailSent(prospectId), `Email ${nextEmail} logged`);
  }

  function saveDetails(e: React.FormEvent) {
    e.preventDefault();
    const fields = { contactName, email, phone, website, notes, nextFollowUp: followUp || null };
    try {
      const clean = cleanProspectFields(fields);
      setWebsite(clean.website ?? "");
    } catch (error) {
      toast.error(error instanceof UserError ? error.message : SAVE_FAILED);
      return;
    }
    run(() => saveProspect(prospectId, fields), "Saved");
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <ProspectStatusBadge status={state.status} />
        {state.nextFollowUp && (
          <span className={due ? "text-sm font-medium text-amber-700" : "text-sm text-muted-foreground"}>
            Follow up {state.nextFollowUp}
            {due ? (state.nextFollowUp < today ? " (overdue)" : " (due today)") : ""}
          </span>
        )}
        <span className="text-sm text-muted-foreground">
          · {state.sequenceStep} of {MAX_SEQUENCE_STEP} emails sent
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {PROSPECT_STATUSES.map((s) => (
          <Button
            key={s}
            type="button"
            size="sm"
            variant={state.status === s ? "default" : "outline"}
            disabled={pending}
            onClick={() => setStatus(s)}
          >
            {PROSPECT_STATUS_LABEL[s]}
          </Button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" disabled={pending || nextEmail > MAX_SEQUENCE_STEP} onClick={sendEmail}>
          <Mail />
          {nextEmail > MAX_SEQUENCE_STEP ? "All 3 emails sent" : `I sent email ${nextEmail} (${DAYS_LABEL[nextEmail - 1]})`}
        </Button>
        <span className="text-xs text-muted-foreground">
          Sets the next follow-up: 4 days after email 1, 6 days after email 2, none after email 3.
        </span>
      </div>

      {suggestions && (
        <section className="space-y-3 rounded-lg border bg-muted/30 p-4">
          <div>
            <h3 className="text-sm font-medium">Suggested from public sources</h3>
            <p className="text-xs text-muted-foreground">
              Matched by business name to {suggestions.name}. Check the website and trade before using anything. Business
              contacts only: call business lines by hand, never autodial or text, and honor opt-outs. &ldquo;Use&rdquo;
              fills the form below; nothing is saved until you press Save.
            </p>
          </div>
          <ul className="divide-y text-sm">
            {suggestions.contactName && (
              <SuggestionRow
                label="Contact"
                field={suggestions.contactName}
                note={suggestions.contactName.title}
                current={contactName}
                onUse={() => setContactName(suggestions.contactName?.value ?? "")}
              />
            )}
            {suggestions.website && (
              <SuggestionRow
                label="Website"
                field={suggestions.website}
                kind="website"
                current={website}
                onUse={() => setWebsite(suggestions.website?.value ?? "")}
              />
            )}
            {suggestions.phones.map((f) => (
              <SuggestionRow key={`p-${f.value}`} label="Phone" field={f} current={phone} onUse={() => setPhone(f.value)} />
            ))}
            {suggestions.emails.map((f) => (
              <SuggestionRow key={`e-${f.value}`} label="Email" field={f} current={email} onUse={() => setEmail(f.value)} />
            ))}
            {suggestions.address && <SuggestionRow label="Address" field={suggestions.address} />}
          </ul>
        </section>
      )}

      {DEAL_STATUSES.includes(state.status) && (
        <DealTerms
          key={`${state.status}|${state.monthlyValueUsd ?? ""}|${state.feeModel}`}
          monthlyValueUsd={state.monthlyValueUsd}
          feeModel={state.feeModel}
          pending={pending}
          onSave={(fields) => run(() => saveProspect(prospectId, fields), "Deal terms saved")}
        />
      )}

      <form onSubmit={saveDetails} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="pp-contact">Contact name</Label>
            <Input id="pp-contact" value={contactName} onChange={(e) => setContactName(e.target.value)} maxLength={120} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pp-email">Business email</Label>
            <Input
              id="pp-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              maxLength={200}
              autoComplete="off"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pp-phone">Business phone</Label>
            <Input id="pp-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={40} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pp-website">Website</Label>
            <Input
              id="pp-website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://"
              maxLength={200}
            />
            {isHttpUrl(state.website) && (
              <a
                href={state.website}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="text-xs text-primary underline-offset-4 hover:underline"
              >
                Open {state.website}
              </a>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pp-follow">Next follow-up</Label>
            <Input id="pp-follow" type="date" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pp-notes">Notes</Label>
          <Textarea
            id="pp-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            maxLength={4000}
            placeholder="Where you found the contact, what they said, opt-outs…"
          />
        </div>
        <Button type="submit" variant="secondary" size="sm" disabled={pending}>
          Save contact details and notes
        </Button>
      </form>

      <div>
        <h3 className="mb-1.5 text-sm font-medium">History</h3>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing logged yet.</p>
        ) : (
          <ul className="divide-y rounded-md border text-sm">
            {history.map((h) => (
              <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
                <span>
                  {h.note || PROSPECT_STATUS_LABEL[h.status]}
                </span>
                <span className="text-xs whitespace-nowrap text-muted-foreground">{h.at}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
