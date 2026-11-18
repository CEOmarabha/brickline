"use client";

import { useMemo, useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TargetSelect } from "@/components/target-select";
import { saveWorkspace } from "@/lib/actions";
import { getTarget, isTradeTarget, type TargetKey, type TargetOption } from "@/lib/targets";
import { cn } from "@/lib/utils";

interface Props {
  initial: { businessName: string; target: TargetKey; areas: number[]; phone: string; mailingAddress: string };
  targets: TargetOption[];
  areas: { id: number; name: string; leads: number }[];
}

export function SettingsForm({ initial, targets, areas }: Props) {
  const [target, setTarget] = useState(initial.target);
  // The sidebar picker can change the target while this form is open: follow it without touching the other fields.
  const [savedTarget, setSavedTarget] = useState(initial.target);
  if (savedTarget !== initial.target) {
    setSavedTarget(initial.target);
    setTarget(initial.target);
  }
  const [selected, setSelected] = useState<Set<number>>(new Set(initial.areas));
  const [filter, setFilter] = useState("");
  const [pending, startTransition] = useTransition();
  const visible = useMemo(
    () => areas.filter((a) => a.name.toLowerCase().includes(filter.toLowerCase())),
    [areas, filter],
  );

  function toggle(id: number) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <form
      className="space-y-8"
      action={(fd) => {
        fd.set("target", target);
        fd.delete("areas");
        for (const id of selected) fd.append("areas", String(id));
        startTransition(async () => {
          try {
            const result = await saveWorkspace(fd);
            if (result.ok) toast.success("Saved. Your leads are updated.");
            else toast.error(result.error);
          } catch {
            toast.error("Couldn't save. Try again.");
          }
        });
      }}
    >
      <section className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="businessName">Company name</Label>
          <Input
            id="businessName"
            name="businessName"
            defaultValue={initial.businessName}
            placeholder="Northside Porch Co."
            maxLength={120}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="target">What are you looking for?</Label>
          <TargetSelect id="target" options={targets} value={target} onValueChange={setTarget} />
          <p className="text-xs text-muted-foreground">{getTarget(target).description}.</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone">Phone for letters and emails</Label>
          <Input id="phone" name="phone" defaultValue={initial.phone} placeholder="(312) 555-0142" maxLength={40} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="mailingAddress">Business mailing address</Label>
          <Input
            id="mailingAddress"
            name="mailingAddress"
            defaultValue={initial.mailingAddress}
            placeholder="1234 N Milwaukee Ave, Chicago, IL 60622"
            maxLength={200}
          />
          <p className="text-xs text-muted-foreground">Required by law on marketing emails (CAN-SPAM).</p>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-medium">Neighborhoods you serve</h2>
            <p className="text-sm text-muted-foreground">
              {selected.size === 0 ? "None selected: you'll see all 77 community areas." : `${selected.size} selected.`}
            </p>
            {!isTradeTarget(target) && (
              <p className="mt-1 text-xs text-muted-foreground">
                Neighborhoods narrow trade leads. The list for what you&apos;re looking for now covers all of Chicago.
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter"
              aria-label="Filter neighborhoods"
              className="w-40"
            />
            <Button type="button" variant="ghost" size="sm" onClick={() => setSelected(new Set())}>
              Clear
            </Button>
          </div>
        </div>
        <div className="grid max-h-96 grid-cols-1 gap-1.5 overflow-y-auto rounded-lg border p-2 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => toggle(a.id)}
              aria-pressed={selected.has(a.id)}
              className={cn(
                "flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition-colors hover:bg-muted",
                selected.has(a.id) && "border-primary bg-primary/10 text-primary",
              )}
            >
              <span>{a.name}</span>
              <span className="text-xs text-muted-foreground tabular-nums">{a.leads} leads</span>
            </button>
          ))}
        </div>
      </section>

      <Button type="submit" disabled={pending}>
        {pending ? "Saving…" : "Save settings"}
      </Button>
    </form>
  );
}
