"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { UserError } from "@/lib/action-result";
import { setLeadStatus } from "@/lib/actions";
import { centsToInput, dollarsToCents, MAX_JOB_VALUE, parseMoney } from "@/lib/money-input";
import { cn } from "@/lib/utils";
import type { LeadStatus } from "@/lib/workspace";

const OPTIONS: { value: LeadStatus; label: string }[] = [
  { value: "contacted", label: "Contacted" },
  { value: "meeting", label: "Meeting booked" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
  { value: "not_relevant", label: "Not relevant" },
  { value: "new", label: "Reset" },
];

export function LeadStatusPanel({
  leadId,
  current,
  note: initialNote,
  jobValue: initialJobValue,
}: {
  leadId: string;
  current: LeadStatus | null;
  note: string;
  jobValue: number | null;
}) {
  const initialValueText = centsToInput(dollarsToCents(initialJobValue));
  const [status, setStatus] = useState<LeadStatus | null>(current);
  const [note, setNote] = useState(initialNote);
  const [value, setValue] = useState(initialValueText);
  const [pending, startTransition] = useTransition();

  function save(next: LeadStatus, success: string) {
    // Only a Won lead carries a job value; other statuses go to the server without one.
    let enteredText = value;
    if (next === "won") {
      try {
        const amount = parseMoney(value, { label: "Job value", max: MAX_JOB_VALUE });
        enteredText = centsToInput(amount?.cents ?? null);
      } catch (error) {
        toast.error(error instanceof UserError ? error.message : "Couldn't save. Try again.");
        return;
      }
    }
    setStatus(next);
    startTransition(async () => {
      try {
        const result = next === "won" ? await setLeadStatus(leadId, next, note, enteredText) : await setLeadStatus(leadId, next, note);
        if (result.ok) {
          setValue(next === "won" ? enteredText : "");
          toast.success(success);
        } else {
          setStatus(current);
          toast.error(result.error);
        }
      } catch {
        setStatus(current);
        toast.error("Couldn't save. Try again.");
      }
    });
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {OPTIONS.map((o) => (
          <Button
            key={o.value}
            type="button"
            variant={status === o.value ? "default" : "outline"}
            size="sm"
            disabled={pending}
            onClick={() => save(o.value, o.value === "new" ? "Lead reset" : `Marked as ${o.label}`)}
            className={cn(o.value === "new" && "text-muted-foreground")}
          >
            {o.label}
          </Button>
        ))}
      </div>
      {status === "won" && (
        <div className="space-y-1.5">
          <Label htmlFor="job-value">Job value ($)</Label>
          <Input
            id="job-value"
            inputMode="decimal"
            autoComplete="off"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. 18500"
            maxLength={14}
          />
          <p className="text-xs text-muted-foreground">
            Optional. What the job is worth, as agreed with the customer. It feeds your Results and nothing is estimated.
          </p>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={pending || value.trim() === initialValueText}
            onClick={() => save("won", "Job value saved")}
          >
            Save job value
          </Button>
        </div>
      )}
      <div className="space-y-1.5">
        <Label htmlFor="note">Note</Label>
        <Textarea
          id="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Who you spoke with, quote amount, next step…"
          rows={3}
          maxLength={2000}
        />
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={pending || note === initialNote}
          onClick={() => save(status ?? "new", "Note saved")}
        >
          Save note
        </Button>
      </div>
    </div>
  );
}
