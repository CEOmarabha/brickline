import type { Metadata } from "next";
import { Suspense } from "react";
import { PestView } from "@/components/pest/pest-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Pest-control pilot list" };

export default function PestPilotPage({ searchParams }: PageProps<"/pilots/pest">) {
  return (
    <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
      <PestView searchParams={searchParams} basePath="/pilots/pest" />
    </Suspense>
  );
}
