import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { dateLabel } from "@/lib/format";

export function DataFreshness({ asOf }: { asOf: { permits: string; violations: string; sales: string; complaints: string } }) {
  return (
    <Tooltip>
      <TooltipTrigger className="w-full text-left">
        <div className="text-xs text-sidebar-foreground/60">Data current through</div>
        <div className="text-sm font-medium">{dateLabel(asOf.violations)}</div>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-64">
        Permits through {dateLabel(asOf.permits)}, violations through {dateLabel(asOf.violations)}, 311 requests through{" "}
        {dateLabel(asOf.complaints)}, property sales through {dateLabel(asOf.sales)} (Cook County publishes sales with a lag).
      </TooltipContent>
    </Tooltip>
  );
}
