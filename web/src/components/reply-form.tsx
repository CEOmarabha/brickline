"use client";

import Link from "next/link";
import { useRef, useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { recordReply } from "@/lib/reply-actions";

const CHANNELS = { phone: "Phone call", email: "Email", mail: "Letter", web: "Web form", other: "Other" };

export function ReplyForm({ today, initialCode = "" }: { today: string; initialCode?: string }) {
  const form = useRef<HTMLFormElement>(null);
  const [channel, setChannel] = useState("phone");
  const [lastLead, setLastLead] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    data.set("channel", channel);
    startTransition(async () => {
      const result = await recordReply(data);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      setLastLead(result.leadId || "");
      toast.success(result.leadId ? "Reply recorded" : "Reply recorded; the code matches no current lead");
      form.current?.reset();
    });
  }

  return (
    <form ref={form} onSubmit={submit} className="space-y-4 rounded-lg border bg-card p-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="code">Reply code</Label>
          <Input id="code" name="code" placeholder="ABCD-2346" defaultValue={initialCode} required autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label>How they replied</Label>
          <Select items={CHANNELS} value={channel} onValueChange={(v) => setChannel(String(v))}>
            <SelectTrigger aria-label="How they replied" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(CHANNELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="receivedOn">Date received</Label>
          <Input id="receivedOn" name="receivedOn" type="date" defaultValue={today} max={today} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="contactPhone">Phone they gave (optional)</Label>
          <Input id="contactPhone" name="contactPhone" autoComplete="off" />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="contactEmail">Email they gave (optional)</Label>
          <Input id="contactEmail" name="contactEmail" type="email" autoComplete="off" />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="message">What they said (optional)</Label>
        <Textarea id="message" name="message" rows={3} />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={pending}>
          {pending ? "Saving…" : "Record reply"}
        </Button>
        {lastLead && (
          <Link href={`/leads/${encodeURIComponent(lastLead)}`} className="text-sm text-primary underline-offset-4 hover:underline">
            Open the lead
          </Link>
        )}
        <p className="text-xs text-muted-foreground">
          Phones and emails typed here stay in this workspace&apos;s database. Call back only the number the owner gave
          you, by hand.
        </p>
      </div>
    </form>
  );
}
