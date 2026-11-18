"use client";

import { useOptimistic, useTransition } from "react";
import { toast } from "sonner";
import { TargetSelect } from "@/components/target-select";
import { setTarget } from "@/lib/actions";
import type { TargetKey, TargetOption } from "@/lib/targets";

/** Sidebar and mobile-menu picker: what the current workspace is looking for. Saves on change and refreshes. */
export function TargetSwitcher({ options, current }: { options: TargetOption[]; current: TargetKey }) {
  const [pending, startTransition] = useTransition();
  const [shown, setShown] = useOptimistic(current);

  return (
    <div className="space-y-1.5">
      <div className="px-1 text-xs text-sidebar-foreground/60">Looking for</div>
      <TargetSelect
        options={options}
        value={shown}
        ariaLabel="Looking for"
        disabled={pending}
        className="border-sidebar-border bg-sidebar-accent text-sidebar-foreground"
        contentClassName="min-w-60"
        onValueChange={(next) =>
          startTransition(async () => {
            setShown(next);
            try {
              const result = await setTarget(next);
              if (!result.ok) toast.error(result.error);
            } catch {
              toast.error("Couldn't change what you're looking for");
            }
          })
        }
      />
    </div>
  );
}
