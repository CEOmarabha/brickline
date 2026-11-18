"use client";

import { useTransition } from "react";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ActionResult } from "@/lib/action-result";

export const SAVE_FAILED = "Couldn't save. Try again.";

/** A labelled Base UI select over a value-to-label map. */
export function EnumSelect({
  id,
  label,
  value,
  items,
  onChange,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  items: Record<string, string>;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select items={items} value={value} onValueChange={(v) => onChange(String(v))} disabled={disabled}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(items).map(([k, l]) => (
            <SelectItem key={k} value={k}>
              {l}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/** Runs a server action, toasts the outcome, and tracks the pending state. */
export function useRun() {
  const [pending, startTransition] = useTransition();
  function run(action: () => Promise<ActionResult>, success: string, onDone?: (ok: boolean) => void) {
    startTransition(async () => {
      try {
        const result = await action();
        if (result.ok) toast.success(success);
        else toast.error(result.error);
        onDone?.(result.ok);
      } catch {
        toast.error(SAVE_FAILED);
        onDone?.(false);
      }
    });
  }
  return { pending, run };
}
