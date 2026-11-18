import type { Metadata } from "next";
import { Suspense } from "react";
import { EventsView } from "@/components/events/events-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Upcoming events" };

/** The same list as /events, kept at its older address (the pilot cards and saved links point here). */
export default function PilotEventsPage({ searchParams }: PageProps<"/pilots/events">) {
  return (
    <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
      <EventsView searchParams={searchParams} basePath="/pilots/events" />
    </Suspense>
  );
}
