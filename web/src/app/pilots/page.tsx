import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader } from "@/components/bits";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getBuyers, listOf } from "@/lib/buyers";
import { getEvents } from "@/lib/events";
import { dateLabel } from "@/lib/format";
import { getPest } from "@/lib/pest";
import { buildEventsCard, buildPilotCards } from "@/lib/pilot-pitches";
import { getSnapshot } from "@/lib/snapshot";
import { viewerId } from "@/lib/workspace";
import { EventsListCard } from "./events-card";
import { PilotListCard } from "./pilot-card";

export const metadata: Metadata = { title: "Pilot lists" };

export default function PilotsPage() {
  return (
    <>
      <PageHeader
        title="Pilot lists"
        description="Four validated lists and the upcoming-events list, none with a paying buyer yet. For each one: what it is, where to see it, who to sell it to, and an email to send."
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Pilots />
      </Suspense>
    </>
  );
}

async function Pilots() {
  const [owner, snap, pest, buyers, events] = await Promise.all([
    viewerId(),
    getSnapshot(),
    getPest(),
    getBuyers(),
    getEvents(),
  ]);
  const cards = buildPilotCards(snap, pest, buyers);
  const eventsCard = buildEventsCard(events);

  return (
    <div className="space-y-8">
      <Card size="sm">
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong className="text-foreground">How to use this page.</strong> Pick 3 to 5 buyers from a list, check their
            website, then send the draft email from your own mailbox or call the business line by hand. Offer the free
            5-row sample, then the 4-week trial in exchange for the buyer recording which rows they contacted and which
            became work. Write the outcomes down: that is what turns a pilot list into something a buyer pays for.
          </p>
          <p>
            Quick links:{" "}
            {cards.map((c, i) => (
              <span key={c.key}>
                {i > 0 && " · "}
                <a href={`#${c.anchor}`} className="underline underline-offset-2">
                  {c.title}
                </a>
              </span>
            ))}
            {" · "}
            <a href={`#${eventsCard.anchor}`} className="underline underline-offset-2">
              {eventsCard.title}
            </a>
            {" · "}
            <Link href="/pilots/pest" className="underline underline-offset-2">
              Pest list in full
            </Link>
            {" · "}
            <Link href="/events" className="underline underline-offset-2">
              Events list in full
            </Link>
          </p>
          {buyers && (
            <p className="text-xs">
              Buyers as of {dateLabel(buyers.asOf)}. {buyers.attribution.contactMatch}
            </p>
          )}
        </CardContent>
      </Card>

      {!buyers && (
        <EmptyState title="The buyers list has not been generated yet">
          Run <code>uv run python -m engine.leads.buyers</code> from the repository root, then reload.
        </EmptyState>
      )}

      {cards.map((card) => (
        <PilotListCard key={card.key} card={card} list={buyers ? listOf(buyers, card.key) : undefined} signedIn={Boolean(owner)} />
      ))}

      <EventsListCard card={eventsCard} signedIn={Boolean(owner)} />

      {buyers && <p className="text-xs text-muted-foreground print:hidden">{buyers.attribution.text}</p>}
    </div>
  );
}
