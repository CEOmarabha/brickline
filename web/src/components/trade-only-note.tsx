import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { targetLabel, type TargetKey } from "@/lib/targets";
import type { Snapshot } from "@/lib/snapshot";

/** Shown instead of trade-specific data when the workspace is looking for events or a commercial list. */
export function TradeOnlyNote({ target, snap, detail }: { target: TargetKey; snap: Snapshot; detail?: string }) {
  return (
    <Card className="border-primary/30 bg-primary/5" role="note" aria-label="Trade targets only">
      <CardContent className="space-y-1 text-sm">
        <p className="font-medium">These views are for trade targets.</p>
        <p className="text-muted-foreground">
          You&apos;re looking for {targetLabel(target, snap.trades)}. Switch the target in the sidebar or{" "}
          <Link href="/settings" className="underline underline-offset-2">
            Settings
          </Link>
          , or see{" "}
          <Link href="/leads" className="underline underline-offset-2">
            Leads
          </Link>
          .
        </p>
        {detail && <p className="text-muted-foreground">{detail}</p>}
      </CardContent>
    </Card>
  );
}
