import Link from "next/link";
import { DealStatusBadge } from "@/components/deal-bits";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getDeals } from "@/lib/deal-store";
import { DEAL_STATUS_LABEL, DEAL_STATUS_VALUES, isDealDue } from "@/lib/deals";
import { count, dateLabel } from "@/lib/format";
import { todayChicago } from "@/lib/pipeline";
import { cn } from "@/lib/utils";
import { viewerId } from "@/lib/workspace";

const DUE_ROWS = 5;

/** The founder's deals on the dashboard: follow-ups due today or overdue, and how many deals sit in each status. */
export async function DealsCard() {
  const owner = await viewerId();
  const today = todayChicago();
  const deals = owner ? await getDeals(owner) : [];
  const due = deals
    .filter((d) => isDealDue(d, today))
    .sort((a, b) => (a.nextFollowUp ?? "").localeCompare(b.nextFollowUp ?? "") || a.id.localeCompare(b.id));
  const byStatus = new Map(DEAL_STATUS_VALUES.map((s) => [s, deals.filter((d) => d.status === s).length]));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deals</CardTitle>
        <CardDescription>
          {owner
            ? `${count(deals.length)} ${deals.length === 1 ? "deal" : "deals"} in your pipeline.`
            : "Sign in to see your deals."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {owner && (
          <>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <h3 className="font-medium">
                  Due today or overdue{" "}
                  <span className={cn("tabular-nums", due.length > 0 ? "text-amber-700" : "text-muted-foreground")}>
                    ({count(due.length)})
                  </span>
                </h3>
                {due.length > 0 && (
                  <Link href="/deals?status=due" className="text-primary hover:underline">
                    See all
                  </Link>
                )}
              </div>
              {due.length === 0 ? (
                <p className="text-muted-foreground">No follow-ups are due.</p>
              ) : (
                <ul className="divide-y rounded-md border">
                  {due.slice(0, DUE_ROWS).map((d) => (
                    <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                      <Link href={`/deals/${encodeURIComponent(d.id)}`} className="font-medium underline-offset-4 hover:underline">
                        {d.title}
                      </Link>
                      <span className="flex items-center gap-2">
                        <DealStatusBadge status={d.status} />
                        <span className="whitespace-nowrap font-medium text-amber-700">
                          {d.nextFollowUp ? dateLabel(d.nextFollowUp) : ""}
                          {d.nextFollowUp && d.nextFollowUp < today ? " (overdue)" : " (today)"}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="mb-1.5 font-medium">Deals by status</h3>
              <ul className="grid grid-cols-3 gap-2">
                {DEAL_STATUS_VALUES.map((s) => (
                  <li key={s}>
                    <Link href={`/deals?status=${s}`} className="block rounded-md border px-3 py-2 hover:bg-muted">
                      <div className="text-xs text-muted-foreground">{DEAL_STATUS_LABEL[s]}</div>
                      <div className="text-lg font-semibold tabular-nums">{count(byStatus.get(s))}</div>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
        <Link href="/deals" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Open deals
        </Link>
      </CardContent>
    </Card>
  );
}
