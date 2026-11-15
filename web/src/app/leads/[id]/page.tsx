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
import { ago, dateLabel, money, pct } from "@/lib/format";
import { draftOutreach } from "@/lib/outreach";
import { getCloseRates } from "@/lib/outcomes";
import { areaNames, closeRateFor, expectedValue, getSnapshot, tradeProbability } from "@/lib/snapshot";
import { getLeadHistory, getStatuses, getWorkspace, STATUS_LABEL } from "@/lib/workspace";

export const metadata: Metadata = { title: "Lead" };

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
  const [snap, ws, statuses, history, rates] = await Promise.all([
    getSnapshot(),
    getWorkspace(),
    getStatuses(),
    getLeadHistory(leadId),
    getCloseRates(),
  ]);
  const lead = snap.leads.find((l) => l.id === leadId);
  if (!lead) notFound();

  const names = areaNames(snap);
  const area = lead.communityArea ? (names.get(lead.communityArea) ?? null) : null;
  const status = statuses.get(lead.id);
  const p = tradeProbability(lead, ws.trade, snap);
  const ev = expectedValue(lead, ws.trade, snap, rates);
  const close = closeRateFor(lead, snap, rates);
  const draft = draftOutreach(lead, ws, snap, area);
  const { margin } = snap.meta.assumptions;
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lead.address}, Chicago, IL`)}`;
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
          <CardContent className="grid gap-6 sm:grid-cols-2">
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
                Chance of work × {pct(close.rate, 0)} close rate × {money(snap.trades[ws.trade].jobValue)} typical job ×{" "}
                {pct(margin, 0)} margin.{" "}
                {close.measured
                  ? "Close rate measured from your own won and lost leads."
                  : "Close rate is an assumption until you've recorded 10+ won or lost leads."}
              </p>
            </div>
          </CardContent>
        </Card>

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
              <a href={lead.sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 underline-offset-2 hover:underline">
                View source record <ExternalLink className="size-3" />
              </a>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
              {lead.evidence.map((e, i) => (
                <div key={`${e.label}-${i}`}>
                  <dt className="text-xs text-muted-foreground">{e.label}</dt>
                  <dd>{e.label.toLowerCase().includes("date") || e.label === "First cited" ? dateLabel(e.value) : e.value}</dd>
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
            <LeadStatusPanel leadId={lead.id} current={status?.status ?? null} note={status?.note ?? ""} />
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
                    <div className="font-medium">{STATUS_LABEL[h.status]}</div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(h.created_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}
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
