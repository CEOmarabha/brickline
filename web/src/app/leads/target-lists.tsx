import Link from "next/link";
import { PageHeader } from "@/components/bits";
import { ClosedRestaurants } from "@/components/commercial/closed-restaurants";
import { NewBusiness } from "@/components/commercial/new-business";
import { OpenTrades } from "@/components/commercial/open-trades";
import { EventsView } from "@/components/events/events-view";
import { PestView } from "@/components/pest/pest-view";
import { buttonVariants } from "@/components/ui/button";
import { areaNames, getSnapshot } from "@/lib/snapshot";
import { getTarget, targetLabel, type TargetKey } from "@/lib/targets";

const EXPLAIN: Partial<Record<TargetKey, string>> = {
  events:
    "Organizations running events in the next 120 days, recurring events to contact the season before, and block parties. Reach each organizer yourself, one at a time, and track every conversation in Deals.",
  new_business:
    "Build-out permits at commercial, mixed-use and 7+ unit addresses where no business license is in force yet: the tenants about to open, for cleaning, signs, security, payments, insurance and furniture.",
  restaurant_spaces:
    "Restaurants recorded out of business and new build-out permits at commercial addresses: spaces about to change hands, for build-out contractors, kitchen equipment, signs and brokers.",
  commercial_subs:
    "Recent $1M+ permits and which trades are still open at each building: elevator, fire-alarm, electrical and sign subcontractors.",
  pest_control:
    "Restaurants with a fresh pest finding in the published inspection records, and the Chicago pest-control companies to pitch.",
};

/** The pitch and buyers card on /pilots for this target, when it has one. */
function PitchLink({ target }: { target: TargetKey }) {
  const anchor = getTarget(target).pilotAnchor;
  if (!anchor) return null;
  return (
    <Link href={`/pilots#${anchor}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
      Who buys this
    </Link>
  );
}

/** What /leads shows when the workspace is looking for something other than a trade. */
export async function TargetLists({
  target,
  searchParams,
}: {
  target: TargetKey;
  searchParams: PageProps<"/leads">["searchParams"];
}) {
  const { leadsTitle } = getTarget(target);
  const description = `Looking for ${targetLabel(target)}. ${EXPLAIN[target] ?? ""} Everything here covers all of Chicago, not only your neighborhoods.`;
  const actions = (
    <>
      {target === "events" && (
        <Link href="/deals" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Deals
        </Link>
      )}
      <PitchLink target={target} />
    </>
  );

  if (target === "events") {
    return (
      <EventsView searchParams={searchParams} basePath="/leads" title={leadsTitle} description={description} actions={actions} />
    );
  }
  if (target === "pest_control") {
    return (
      <PestView searchParams={searchParams} basePath="/leads" title={leadsTitle} description={description} actions={actions} />
    );
  }

  const snap = await getSnapshot();
  const names = areaNames(snap);
  return (
    <div className="space-y-10">
      <PageHeader
        title={leadsTitle}
        description={description}
        actions={actions}
      />
      {target === "restaurant_spaces" && <ClosedRestaurants snap={snap} names={names} />}
      {(target === "new_business" || target === "restaurant_spaces") && <NewBusiness snap={snap} names={names} />}
      {target === "commercial_subs" && <OpenTrades snap={snap} names={names} />}
    </div>
  );
}
