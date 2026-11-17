"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { setLeadStatus } from "@/lib/actions";
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
}: {
  leadId: string;
  current: LeadStatus | null;
  note: string;
}) {
  const [status, setStatus] = useState<LeadStatus | null>(current);
  const [note, setNote] = useState(initialNote);
  const [pending, startTransition] = useTransition();

  function save(next: LeadStatus, success: string) {
    setStatus(next);
    startTransition(async () => {
      try {
        const result = await setLeadStatus(leadId, next, note);
        if (result.ok) {
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
