import { ArrowLeft, ExternalLink, MapPin } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ProbabilityBar, StatusBadge, TierBadge } from "@/components/bits";
import { CopyButton } from "@/components/copy-button";
import { LeadStatusPanel } from "@/components/lead-status-panel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ContactValue, SourceLine } from "@/components/contact-bits";
import { getLeadContacts } from "@/lib/contacts";
import { ago, count, dateLabel, dateTimeLabel, exactMoney, liftLabel, money, pct } from "@/lib/format";
import { isHttpUrl } from "@/lib/links";
import { draftOutreach } from "@/lib/outreach";
import { getCloseRates, MIN_DECIDED, MIN_VALUED_WON } from "@/lib/outcomes";
import { areaNames, closeRateFor, expectedValue, getSnapshot, jobValueFor, type Lead, type Snapshot, type TradeKey, tradeProbability } from "@/lib/snapshot";
import { cn } from "@/lib/utils";
import { getLeadHistory, getStatuses, getWorkspace, STATUS_LABEL } from "@/lib/workspace";

export const metadata: Metadata = { title: "Lead" };

const DATE_LABELS = new Set([
  "First cited",
  "Complaint filed",
  "Inspection requested",
  "Vacancy reported",
  "Closure recorded",
  "First food inspection on record",
]);

/** The event this lead is waiting for (citation or sale), with the historical rate behind it. Other kinds have none. */
function headlineFor(lead: Lead, snap: Snapshot): { label: string; note: string } | null {
  if (lead.kind === "complaint") {
    const m = snap.models.complaint;
    return {
      label: "Chance it gets cited",
      note: `Within 120 days of the complaint${m.medianDaysToViolation === null ? "" : `; when a citation comes, the median is ${m.medianDaysToViolation} days after it`}. Based on ${count(m.episodes)} complaints, ${m.period}.`,
    };
  }
  if (lead.kind === "vacant") {
    const m = snap.models.vacant;
    return {
      label: "Chance it sells",
      note: `Within a year of the report. Based on ${count(m.episodes)} reports, ${m.period}.`,
    };
  }
  if (lead.kind === "closed_restaurant") {
    const m = snap.models.closedRestaurant;
    return {
      label: "Chance a new food business is licensed",
      note: `A different business name at this address within a year of the closure. Based on ${count(m.episodes)} closures, ${m.period}.`,
    };
  }
  return null;
}

export default function LeadPage({ params }: PageProps<"/leads/[id]">) {
  return (
    <>
      <Link href="/leads" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All leads
      </Link>
      <Suspense fallback={<Skeleton className="h-[32rem] w-full" />}>
        <LeadDetail params={params} />
      </Suspense>
    </>
  );
}

async function LeadDetail({ params }: { params: PageProps<"/leads/[id]">["params"] }) {
  const { id } = await params;
  const leadId = decodeURIComponent(id);
  const [snap, ws, statuses, history, rates, suggestions] = await Promise.all([
    getSnapshot(),
    getWorkspace(),
    getStatuses(),
    getLeadHistory(leadId),
    getCloseRates(),
    getLeadContacts(leadId),
  ]);
  const lead = snap.leads.find((l) => l.id === leadId);
  if (!lead) notFound();

  const names = areaNames(snap);
  const area = lead.communityArea ? (names.get(lead.communityArea) ?? null) : null;
  const status = statuses.get(lead.id);
  const p = tradeProbability(lead, ws.trade, snap);
  const ev = expectedValue(lead, ws.trade, snap, rates);
  const close = closeRateFor(lead, snap, rates);
  const job = jobValueFor(lead, ws.trade, snap, rates);
  const draft = draftOutreach(lead, ws, snap, area);
  const { margin } = snap.meta.assumptions;
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lead.address}, Chicago, IL`)}`;
  const headline = headlineFor(lead, snap);
  const byTrade = lead.tradeProbabilities && lead.kind !== "investor_purchase" ? Object.entries(lead.tradeProbabilities) : [];
  const companyName = lead.kind === "investor_purchase" ? lead.buyer.name : lead.owner.type === "company" ? lead.owner.name : null;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <TierBadge tier={lead.tier} />
            {status && <StatusBadge status={status.status} label={STATUS_LABEL[status.status]} />}
            <span className="text-sm text-muted-foreground">
              {lead.title} · {ago(lead.ageDays)}
            </span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">{lead.address}</h1>
          <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="size-4" /> {area ?? "Chicago"} ·{" "}
            <a href={mapsUrl} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
              Open in Maps
            </a>
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Why this lead</CardTitle>
            <CardDescription>{lead.probabilityBasis}</CardDescription>
          </CardHeader>
          <CardContent className={cn("grid gap-6 sm:grid-cols-2", headline && "lg:grid-cols-3")}>
            {headline && (
              <div>
                <div className="flex items-baseline justify-between text-sm">
                  <span className="text-muted-foreground">{headline.label}</span>
                  <span className="text-lg font-semibold tabular-nums">{pct(lead.probability)}</span>
                </div>
                <div className="mt-2">
                  <ProbabilityBar value={lead.probability} />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{headline.note}</p>
              </div>
            )}
            <div>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-muted-foreground">Chance of {snap.trades[ws.trade].label.toLowerCase()} work</span>
                <span className="text-lg font-semibold tabular-nums">{pct(p)}</span>
              </div>
              <div className="mt-2">
                <ProbabilityBar value={p} />
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Counts permitted work only, so real demand is higher.
              </p>
            </div>
            <div>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-muted-foreground">Expected gross profit</span>
                <span className="text-lg font-semibold tabular-nums">{money(ev)}</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Chance of work × {pct(close.rate, 0)} close rate × {job.measured ? exactMoney(job.value) : money(job.value)} typical job × {pct(margin, 0)} margin.{" "}
                {close.measured
                  ? "Close rate measured from your own won and lost leads."
                  : `Close rate is an assumption until you've recorded ${MIN_DECIDED}+ won or lost leads.`}{" "}
                {job.measured
                  ? `Typical job is the median of the ${job.n} won jobs you entered for this kind of lead.`
                  : `Typical job comes from permits until you've entered job values on ${MIN_VALUED_WON}+ won leads of this kind.`}
              </p>
            </div>
          </CardContent>
        </Card>

        {byTrade.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Chance of work by trade</CardTitle>
              <CardDescription>
                {lead.kind === "vacant"
                  ? `Share of reported properties that pulled a permit of that type within two years (${snap.models.vacant.permitPeriod}); not adjusted for time passed.`
                  : lead.kind === "closed_restaurant"
                    ? `Share of closed restaurant addresses followed by a renovation, build-out or new-construction permit within a year (${snap.models.closedRestaurant.period}), adjusted for time passed. ${capitalize(liftLabel(snap.models.closedRestaurant.permit.lift))}: ${pct(snap.models.closedRestaurant.permit.p365)} vs ${pct(snap.models.closedRestaurant.permit.baseline365)} at ordinary restaurants.`
                    : `Share of complaints followed by a permit of that type at the same address within a year (${snap.models.complaint.period}), adjusted for time passed.`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                {byTrade
                  .sort(([, a], [, b]) => b - a)
                  .map(([trade, prob]) => (
                    <li key={trade}>
                      <div className="flex items-baseline justify-between">
                        <span className={trade === ws.trade ? "font-medium" : "text-muted-foreground"}>
                          {snap.trades[trade as TradeKey].label}
                        </span>
                        <span className="tabular-nums">{pct(prob)}</span>
                      </div>
                      <div className="mt-1.5">
                        <ProbabilityBar value={prob} />
                      </div>
                    </li>
                  ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {lead.kind === "closed_restaurant" && <ClosedRestaurantBasis snap={snap} />}

        {lead.kind === "investor_purchase" && (
          <Card>
            <CardHeader>
              <CardTitle>The buyer</CardTitle>
              <CardDescription>
                {`${lead.buyer.name} · ${lead.buyer.purchases24m} purchase${lead.buyer.purchases24m === 1 ? "" : "s"} in the last 2 years`}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-6 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground">Contractors they&apos;ve used</h3>
                {lead.buyer.contractorsUsed.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No permits on their properties yet.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {lead.buyer.contractorsUsed.map((c) => (
                      <li key={c.name} className="flex justify-between gap-2">
                        <span className="truncate">{c.name}</span>
                        <span className="text-muted-foreground tabular-nums">{c.jobs} jobs</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground">Other recent purchases</h3>
                {lead.buyer.otherProperties.length === 0 ? (
                  <p className="text-sm text-muted-foreground">None in the last 2 years.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {lead.buyer.otherProperties.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                )}
              </div>
              {lead.permitsSince.length > 0 && (
                <div className="sm:col-span-2">
                  <h3 className="mb-2 text-xs font-medium text-muted-foreground">Permits since the purchase</h3>
                  <ul className="space-y-2 text-sm">
                    {lead.permitsSince.map((pm) => (
                      <li key={`${pm.date}-${pm.description}`}>
                        <span className="font-medium">{dateLabel(pm.date)}</span> · {pm.type}
                        {pm.cost ? ` · ${money(pm.cost)}` : ""}
                        <div className="text-muted-foreground">{pm.description}</div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Evidence</CardTitle>
            <CardDescription>
              From public records.{" "}
              {isHttpUrl(lead.sourceUrl) && (
                <a href={lead.sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 underline-offset-2 hover:underline">
                  View source record <ExternalLink className="size-3" />
                </a>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
              {lead.evidence.map((e, i) => (
                <div key={`${e.label}-${i}`}>
                  <dt className="text-xs text-muted-foreground">{e.label}</dt>
                  <dd>{e.label.toLowerCase().includes("date") || DATE_LABELS.has(e.label) ? dateLabel(e.value) : e.value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>{draft.channel === "letter" ? "Letter draft" : "Email draft"}</CardTitle>
                <CardDescription>Review and edit before sending. Nothing is sent automatically.</CardDescription>
              </div>
              <CopyButton text={draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body} />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {draft.subject && (
              <div className="text-sm">
                <span className="text-muted-foreground">Subject:</span> {draft.subject}
              </div>
            )}
            <pre className="rounded-md border bg-muted/40 p-4 font-sans text-sm leading-relaxed whitespace-pre-wrap">
              {draft.body}
            </pre>
            <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
              {draft.compliance.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            {!ws.configured && (
              <p className="text-xs text-muted-foreground">
                Add your company name, phone and mailing address in{" "}
                <Link href="/settings" className="underline">
                  Settings
                </Link>{" "}
                to fill the placeholders.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Next step</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <p>{lead.action}</p>
            <Separator />
            <LeadStatusPanel
              leadId={lead.id}
              current={status?.status ?? null}
              note={status?.note ?? ""}
              jobValue={status?.status === "won" ? status.jobValueUsd : null}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{lead.kind === "investor_purchase" ? "Contact" : "Owner of record"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Name</div>
              <div>{lead.owner.name ?? "Not on the county tax roll"}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Mailing address</div>
              <div>{lead.owner.mailing ?? "—"}</div>
            </div>
            {lead.owner.note && <p className="text-xs text-muted-foreground">{lead.owner.note}</p>}
            {suggestions && (
              <div className="space-y-2.5 rounded-md border bg-muted/30 p-3">
                <div>
                  <div className="text-xs font-medium">Suggested from public sources</div>
                  <p className="text-xs text-muted-foreground">
                    Matched by name to {suggestions.name}. Verify before outreach; business contacts only.
                  </p>
                </div>
                {suggestions.contactName && (
                  <div>
                    <div className="text-xs text-muted-foreground">Contact</div>
                    <div>
                      <ContactValue field={suggestions.contactName} kind="text" />
                      <span className="ml-1.5 text-xs text-muted-foreground">({suggestions.contactName.title})</span>
                    </div>
                    <SourceLine field={suggestions.contactName} />
                  </div>
                )}
                {suggestions.website && (
                  <div>
                    <div className="text-xs text-muted-foreground">Website</div>
                    <ContactValue field={suggestions.website} kind="website" />
                    <SourceLine field={suggestions.website} />
                  </div>
                )}
                {suggestions.phones.map((f) => (
                  <div key={`p-${f.value}`}>
                    <div className="text-xs text-muted-foreground">Phone</div>
                    <ContactValue field={f} kind="text" />
                    <SourceLine field={f} />
                  </div>
                ))}
                {suggestions.emails.map((f) => (
                  <div key={`e-${f.value}`}>
                    <div className="text-xs text-muted-foreground">Email</div>
                    <ContactValue field={f} kind="text" />
                    <SourceLine field={f} />
                  </div>
                ))}
                {suggestions.address && (
                  <div>
                    <div className="text-xs text-muted-foreground">Business address</div>
                    <ContactValue field={suggestions.address} kind="text" />
                    <SourceLine field={suggestions.address} />
                  </div>
                )}
              </div>
            )}
            {lead.owner.type === "individual" && (
              <p className="text-xs text-muted-foreground">Individual owner: reach out by mail.</p>
            )}
            {companyName && (
              <a
                href="https://apps.ilsos.gov/businessentitysearch/"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                Look up {companyName} in the Illinois business registry <ExternalLink className="size-3" />
              </a>
            )}
          </CardContent>
        </Card>

        {history.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-3 text-sm">
                {history.map((h, i) => (
                  <li key={i}>
                    <div className="font-medium">
                      {STATUS_LABEL[h.status]}
                      {h.job_value_usd !== null && (
                        <span className="font-normal tabular-nums"> · job value {exactMoney(h.job_value_usd)}</span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {dateTimeLabel(new Date(h.created_at))}
                    </div>
                    {h.note && <div className="mt-0.5 text-muted-foreground">{h.note}</div>}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function ClosedRestaurantBasis({ snap }: { snap: Snapshot }) {
  const m = snap.models.closedRestaurant;
  const rows = [
    { label: "New food business license, different name", note: "Within 365 days of the closure", o: m.license },
    { label: "Same, issued 31+ days after the closure", note: "The usable lead time", o: m.licenseAfter30 },
    { label: "Renovation, build-out or new-construction permit", note: `Within 365 days; ${liftLabel(m.permit.lift)}`, o: m.permit },
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>What happened at similar spaces</CardTitle>
        <CardDescription>
          {count(m.episodes)} restaurant closures recorded {m.period} (about {m.closuresPerWeek.toFixed(1)} a week lately),
          compared with ordinary inspections of other restaurants at the same kind of address.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3 text-sm">
          {rows.map(({ label, note, o }) => (
            <li key={label}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-medium">{label}</span>
                <span className="tabular-nums">
                  {pct(o.p365)} <span className="text-muted-foreground">vs {pct(o.baseline365)} · {o.lift.toFixed(2)}x</span>
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {note}. Median {o.medianDays.toFixed(0)} days after the closure, middle half {o.daysP25.toFixed(0)}–
                {o.daysP75.toFixed(0)} days.
              </p>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-muted-foreground">
          Matched on street address; licenses cover retail food establishments only, so reopenings as a bar or non-food
          tenant are missed and rates are floors. Pilot list: the audience for it is unproven.
        </p>
      </CardContent>
    </Card>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
