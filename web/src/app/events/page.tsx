import type { Metadata } from "next";
import { Suspense } from "react";
import { EventsView } from "@/components/events/events-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Upcoming events" };

export default function EventsPage({ searchParams }: PageProps<"/events">) {
  return (
    <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
      <EventsView searchParams={searchParams} basePath="/events" />
    </Suspense>
  );
}
