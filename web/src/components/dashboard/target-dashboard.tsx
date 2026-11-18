import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/bits";
import { CommercialDashboard } from "@/components/dashboard/commercial-dashboard";
import { EventsDashboard } from "@/components/dashboard/events-dashboard";
import { buttonVariants } from "@/components/ui/button";
import { getSnapshot } from "@/lib/snapshot";
import { getTarget, targetLabel } from "@/lib/targets";
import type { Workspace } from "@/lib/workspace";

/** The dashboard for a workspace that is looking for events or a commercial list instead of a trade. */
export async function TargetDashboard({ ws }: { ws: Workspace }) {
  const snap = await getSnapshot();
  return (
    <>
      <PageHeader
        title={ws.businessName ? `This week for ${ws.businessName}` : "This week in Chicago"}
        description={`Looking for ${targetLabel(ws.target, snap.trades)}. ${getTarget(ws.target).description}. Every number comes from public records or your own deals.`}
        actions={
          <Link href="/leads" className={buttonVariants()}>
            Open leads <ArrowRight />
          </Link>
        }
      />
      {ws.target === "events" ? <EventsDashboard /> : <CommercialDashboard target={ws.target} />}
    </>
  );
}
