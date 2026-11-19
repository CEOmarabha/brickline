import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { DealDraftsPanel } from "@/components/deal-drafts-panel";
import { DealStatusBadge, DoNotContactBadge } from "@/components/deal-bits";
import {
  type DealView,
  DealDetailsForm,
  DealHistory,
  DealMoneyForm,
  DealPartnersPicker,
  DealStatusSection,
} from "@/components/deal-panel";
import { EmptyState, PageHeader } from "@/components/bits";
import { PossibleJobsCard } from "@/components/possible-jobs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getDeal, getDealHistory, getDeals, getPartners } from "@/lib/deal-store";
import { BUYER_TYPE_LABEL, DEAL_SOURCE_LABEL, daysUntilLabel, matchesOptedOutContact } from "@/lib/deals";
import { getEventBoard } from "@/lib/event-board";
import { dateLabel, dateTimeLabel } from "@/lib/format";
import { getLifecycles } from "@/lib/lifecycles";
import { isHttpUrl } from "@/lib/links";
import { todayChicago } from "@/lib/pipeline";
import { eventJobs, findBoardEvent, type JobsPlan, leadJobs } from "@/lib/possible-jobs";
import { getSnapshot } from "@/lib/snapshot";
import { getWorkspace, viewerId } from "@/lib/workspace";

export const metadata: Metadata = { title: "Deal" };

export default function DealPage({ params }: PageProps<"/deals/[id]">) {
  return (
    <>
      <Link
        href="/deals"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> All deals
      </Link>
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <DealDetail params={params} />
      </Suspense>
    </>
  );
}

async function DealDetail({ params }: { params: PageProps<"/deals/[id]">["params"] }) {
  const { id: rawId } = await params;
  const owner = await viewerId();
  if (!owner) {
    return (
      <>
        <PageHeader title="Deal" />
        <EmptyState title="Sign in to use deals">Your deals are private to your account.</EmptyState>
      </>
    );
  }

  let id: string;
  try {
    id = decodeURIComponent(rawId);
  } catch {
    notFound();
  }
  const [deal, history, partners, allDeals, ws, snap, board, lifecycles] = await Promise.all([
    getDeal(owner, id),
    getDealHistory(owner, id),
    getPartners(owner),
    getDeals(owner),
    getWorkspace(),
    getSnapshot(),
    getEventBoard(),
    getLifecycles(),
  ]);
  if (!deal) notFound();
  const matchesOptedOut = matchesOptedOutContact(deal, allDeals);

  const today = todayChicago();
  const view: DealView = {
    id: deal.id,
    title: deal.title,
    status: deal.status,
    source: deal.source,
    sourceRef: deal.sourceRef,
    buyerName: deal.buyerName,
    buyerType: deal.buyerType,
    contactChannel: deal.contactChannel,
    contactInfo: deal.contactInfo,
    eventDate: deal.eventDate,
    guests: deal.guests,
    location: deal.location,
    needs: deal.needs,
    budgetUsd: deal.budgetUsd,
    lostReason: deal.lostReason,
    partnerIds: deal.partnerIds,
    quoteUsd: deal.quoteUsd,
    feeUsd: deal.feeUsd,
    feeModel: deal.feeModel,
    feeCollected: deal.feeCollected,
    nextFollowUp: deal.nextFollowUp,
    notes: deal.notes,
  };
  const internalRef = deal.sourceRef !== "" && !isHttpUrl(deal.sourceRef) ? deal.sourceRef : null;
  const refLead = internalRef ? snap.leads.find((l) => l.id === internalRef) : undefined;
  const refEvent = internalRef && !refLead ? findBoardEvent(board, internalRef) : undefined;
  let refLink: { href: string; label: string } | null = null;
  let jobs: JobsPlan | null = null;
  if (refLead) {
    refLink = { href: `/leads/${encodeURIComponent(refLead.id)}`, label: "Open this lead in Brickline" };
    jobs = leadJobs(refLead, snap, lifecycles);
  } else if (refEvent) {
    refLink = { href: `/event-board/${encodeURIComponent(refEvent.id)}`, label: "Open this event in Brickline" };
    jobs = eventJobs(refEvent, board, lifecycles);
  }
  const partnerName = new Map(partners.map((p) => [p.id, p.name]));
  const attachedNames = deal.partnerIds.map((pid) => partnerName.get(pid)).filter((n): n is string => Boolean(n));

  const detailsKey = JSON.stringify([
    deal.title,
    deal.buyerName,
    deal.buyerType,
    deal.contactChannel,
    deal.contactInfo,
    deal.source,
    deal.sourceRef,
    deal.eventDate,
    deal.guests,
    deal.location,
    deal.budgetUsd,
    deal.needs,
    deal.notes,
  ]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{deal.title}</h1>
          <DealStatusBadge status={deal.status} />
          {(deal.status === "opted_out" || matchesOptedOut) && <DoNotContactBadge />}
        </div>
        {matchesOptedOut && deal.status !== "opted_out" && (
          <p role="alert" className="text-sm font-medium text-destructive">
            This handle, email or phone number matches a buyer on another deal who opted out. Do not contact them.
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          {BUYER_TYPE_LABEL[deal.buyerType]}
          {deal.buyerName ? ` · ${deal.buyerName}` : ""} · {DEAL_SOURCE_LABEL[deal.source]}
          {deal.eventDate ? ` · ${dateLabel(deal.eventDate)} (${daysUntilLabel(deal.eventDate, today)})` : ""} · added{" "}
          {dateTimeLabel(deal.createdAt)}. Only you see this page.
        </p>
      </header>

      {jobs && refLink && (
        <PossibleJobsCard
          plan={jobs}
          description={
            <>
              {jobs.lifecycleName}, from the {refLead ? "lead" : "event"} this deal links to (
              <Link href={refLink.href} className="underline">
                open it
              </Link>
              ): the jobs you can place with partners, stage by stage.
            </>
          }
        />
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Status and follow-up</CardTitle>
              <CardDescription>
                Move the deal as it progresses. Opted out is final: it locks the drafts and the status.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DealStatusSection
                key={`${deal.status}|${deal.nextFollowUp ?? ""}|${deal.lostReason}`}
                deal={view}
                today={today}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
              <CardDescription>Contact details are private to you and never sent anywhere.</CardDescription>
            </CardHeader>
            <CardContent>
              <DealDetailsForm key={detailsKey} deal={view} refLink={refLink} />
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quote and fee</CardTitle>
              <CardDescription>What you quoted the buyer and what you earn on the deal.</CardDescription>
            </CardHeader>
            <CardContent>
              <DealMoneyForm key={`${deal.quoteUsd}|${deal.feeUsd}|${deal.feeModel}|${deal.feeCollected}|${deal.status}`} deal={view} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Partners</CardTitle>
              <CardDescription>The vendors who will do the work.</CardDescription>
            </CardHeader>
            <CardContent>
              <DealPartnersPicker
                key={deal.partnerIds.join(",")}
                dealId={deal.id}
                attached={deal.partnerIds}
                partners={partners.map((p) => ({
                  id: p.id,
                  name: p.name,
                  services: p.services,
                  agreementSigned: p.agreementSigned,
                }))}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>History</CardTitle>
            </CardHeader>
            <CardContent>
              <DealHistory
                history={history.map((h) => ({ id: h.id, status: h.status, note: h.note, at: dateTimeLabel(h.createdAt) }))}
              />
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Message drafts</CardTitle>
          <CardDescription>
            Personal, one-to-one drafts for you to review, edit and send yourself. The app never sends anything.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DealDraftsPanel
            deal={{
              status: deal.status,
              source: deal.source,
              buyerType: deal.buyerType,
              buyerName: deal.buyerName,
              channel: deal.contactChannel,
              eventDate: deal.eventDate,
              quoteUsd: deal.quoteUsd,
              feeUsd: deal.feeUsd,
              feeModel: deal.feeModel,
              partnerNames: attachedNames,
              matchesOptedOut,
            }}
            businessName={ws.businessName}
            mailingAddress={ws.mailingAddress}
          />
        </CardContent>
      </Card>
    </div>
  );
}
