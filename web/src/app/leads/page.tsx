import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/bits";
import { Skeleton } from "@/components/ui/skeleton";
import { isTradeTarget } from "@/lib/targets";
import { getWorkspace } from "@/lib/workspace";
import { TargetLists } from "./target-lists";
import { TradeLeads } from "./trade-leads";

export const metadata: Metadata = { title: "Leads" };

/** One URL for every target: a trade shows the trade lead list, any other target shows its own list. */
export default function LeadsPage({ searchParams }: PageProps<"/leads">) {
  return (
    <Suspense fallback={<LeadsSkeleton />}>
      <LeadsForTarget searchParams={searchParams} />
    </Suspense>
  );
}

async function LeadsForTarget({ searchParams }: { searchParams: PageProps<"/leads">["searchParams"] }) {
  const ws = await getWorkspace();
  if (isTradeTarget(ws.target)) return <TradeLeads searchParams={searchParams} />;
  return <TargetLists target={ws.target} searchParams={searchParams} />;
}

function LeadsSkeleton() {
  return (
    <>
      <PageHeader title="Leads" />
      <div className="space-y-3">
        <Skeleton className="h-9 w-full" />
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    </>
  );
}
