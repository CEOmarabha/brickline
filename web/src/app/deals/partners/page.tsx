import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EmptyState, PageHeader } from "@/components/bits";
import { PartnerManager } from "@/components/partner-manager";
import { Skeleton } from "@/components/ui/skeleton";
import { getDeals, getPartners } from "@/lib/deal-store";
import { viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Deal partners" };

export default function PartnersPage() {
  return (
    <>
      <Link href="/deals" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All deals
      </Link>
      <PageHeader
        title="Partners"
        description="The vendors who do the work once a buyer says yes: rental companies, caterers, contractors. Private to you."
      />
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <Partners />
      </Suspense>
    </>
  );
}

async function Partners() {
  const owner = await viewerId();
  if (!owner) return <EmptyState title="Sign in to use deals">Your partners are private to your account.</EmptyState>;
  const [partners, deals] = await Promise.all([getPartners(owner), getDeals(owner)]);
  const dealCount = new Map<string, number>();
  for (const d of deals) for (const id of d.partnerIds) dealCount.set(id, (dealCount.get(id) ?? 0) + 1);
  return (
    <PartnerManager
      disabled={false}
      partners={partners.map((p) => ({
        id: p.id,
        name: p.name,
        services: p.services,
        area: p.area,
        contactName: p.contactName,
        phone: p.phone,
        email: p.email,
        website: p.website,
        feeTerms: p.feeTerms,
        agreementSigned: p.agreementSigned,
        notes: p.notes,
        dealCount: dealCount.get(p.id) ?? 0,
      }))}
    />
  );
}
