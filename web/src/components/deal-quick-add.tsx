"use client";

import { Plus } from "lucide-react";
import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { UserError } from "@/lib/action-result";
import { createDeal } from "@/lib/deal-actions";
import {
  BUYER_TYPE_LABEL,
  BUYER_TYPES,
  cleanDealFields,
  DEAL_SOURCE_LABEL,
  DEAL_SOURCES,
} from "@/lib/deals";

const SAVE_FAILED = "Couldn't save. Try again.";

export function DealQuickAdd({ disabled }: { disabled: boolean }) {
  const [link, setLink] = useState("");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [type, setType] = useState<string>("person");
  const [source, setSource] = useState<string>("social");
  const [needs, setNeeds] = useState("");
  const [pending, startTransition] = useTransition();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const fields = { sourceRef: link, title, eventDate: date || null, buyerType: type, source, needs };
    try {
      const clean = cleanDealFields(fields);
      if (clean.title === undefined) throw new UserError("Add a short title so you can find this deal again");
    } catch (error) {
      toast.error(error instanceof UserError ? error.message : SAVE_FAILED);
      return;
    }
    startTransition(async () => {
      try {
        const result = await createDeal(fields);
        if (result.ok) {
          toast.success("Deal added");
          setLink("");
          setTitle("");
          setDate("");
          setNeeds("");
        } else {
          toast.error(result.error);
        }
      } catch {
        toast.error(SAVE_FAILED);
      }
    });
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border p-4" aria-label="Quick add a deal">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">Quick add</h2>
        <p className="text-xs text-muted-foreground">
          Paste the public link, name the deal, and add what you know. Contact details go on the deal page.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-6">
        <div className="space-y-1.5 sm:col-span-3">
          <Label htmlFor="qa-link">Link to the public post or page (or a lead or event id)</Label>
          <Input
            id="qa-link"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            placeholder="https://"
            maxLength={400}
            autoComplete="off"
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5 sm:col-span-3">
          <Label htmlFor="qa-title">Title</Label>
          <Input
            id="qa-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Graduation party, Pilsen"
            maxLength={120}
            autoComplete="off"
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="qa-date">Event or job date</Label>
          <Input id="qa-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} disabled={disabled} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="qa-type">Type</Label>
          <Select items={BUYER_TYPE_LABEL} value={type} onValueChange={(v) => setType(String(v))} disabled={disabled}>
            <SelectTrigger id="qa-type" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BUYER_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {BUYER_TYPE_LABEL[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="qa-source">Source</Label>
          <Select items={DEAL_SOURCE_LABEL} value={source} onValueChange={(v) => setSource(String(v))} disabled={disabled}>
            <SelectTrigger id="qa-source" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DEAL_SOURCES.map((s) => (
                <SelectItem key={s} value={s}>
                  {DEAL_SOURCE_LABEL[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5 sm:col-span-1 sm:self-end">
          <Button type="submit" className="w-full" disabled={disabled || pending}>
            <Plus /> Add
          </Button>
        </div>
        <div className="space-y-1.5 sm:col-span-6">
          <Label htmlFor="qa-needs">What they need</Label>
          <Input
            id="qa-needs"
            value={needs}
            onChange={(e) => setNeeds(e.target.value)}
            placeholder="e.g. tent, tables and chairs for about 60 guests"
            maxLength={2000}
            autoComplete="off"
            disabled={disabled}
          />
        </div>
      </div>
    </form>
  );
}
