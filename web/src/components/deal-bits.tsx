import { Ban } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DEAL_STATUS_LABEL, type DealStatus } from "@/lib/deals";

const STATUS_STYLE: Record<DealStatus, string> = {
  found: "bg-muted text-muted-foreground",
  contacted: "bg-sky-500/10 text-sky-700 border-sky-500/20",
  replied: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  interested: "bg-violet-500/10 text-violet-700 border-violet-500/20",
  quoted: "bg-primary/10 text-primary border-primary/20",
  booked: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  completed: "bg-emerald-600/15 text-emerald-800 border-emerald-600/25",
  lost: "bg-zinc-500/10 text-zinc-600",
  opted_out: "bg-destructive/10 text-destructive border-destructive/20",
};

export function DealStatusBadge({ status }: { status: DealStatus }) {
  return (
    <Badge variant="outline" className={STATUS_STYLE[status]}>
      {DEAL_STATUS_LABEL[status]}
    </Badge>
  );
}

/** Shown wherever an opted-out buyer appears: nothing is drafted and no follow-up is ever scheduled. */
export function DoNotContactBadge() {
  return (
    <Badge variant="destructive" title="This buyer asked not to be contacted. Never message them again.">
      <Ban /> Do not contact
    </Badge>
  );
}
