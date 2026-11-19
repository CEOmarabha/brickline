import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/bits";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count, dateLabel, pct } from "@/lib/format";
import { FAMILY_LABEL, getLifecycles, type Lifecycle, type LifecycleFamily, type LifecyclesFile } from "@/lib/lifecycles";
import { firstParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Opportunity map" };

const FAMILIES = Object.keys(FAMILY_LABEL) as LifecycleFamily[];

export default function OpportunitiesPage({ searchParams }: PageProps<"/opportunities">) {
  return (
    <>
      <PageHeader
        title="Opportunity map"
        description="Every public trigger we can see, the jobs it sets off stage by stage, how many Chicago companies sell each job, and whether public records show who already has it. Use it to pick lists to sell and partners to sign."
      />
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <OpportunityMap searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function OpportunityMap({ searchParams }: { searchParams: PageProps<"/opportunities">["searchParams"] }) {
  const sp = await searchParams;
  const data = await getLifecycles();
  const family = FAMILIES.find((f) => f === firstParam(sp.family)) ?? null;
  const shown = data.lifecycles.filter((l) => !family || l.family === family);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <FamilyLink href="/opportunities" active={!family} label={`All (${data.lifecycles.length})`} />
        {FAMILIES.map((f) => (
          <FamilyLink
            key={f}
            href={`/opportunities?family=${f}`}
            active={family === f}
            label={`${FAMILY_LABEL[f]} (${data.lifecycles.filter((l) => l.family === f).length})`}
          />
        ))}
        <span className="ml-auto self-center text-xs text-muted-foreground">Records through {dateLabel(data.asOf)}</span>
      </div>
      {shown.map((l) => (
        <LifecycleCard key={l.id} l={l} data={data} />
      ))}
    </div>
  );
}

function FamilyLink({ href, active, label }: { href: string; active: boolean; label: string }) {
  return (
    <Link
      href={href}
      className={cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary")}
    >
      {label}
    </Link>
  );
}

function LifecycleCard({ l, data }: { l: Lifecycle; data: LifecyclesFile }) {
  return (
    <Card id={l.id}>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{l.name}</CardTitle>
            <CardDescription>
              {FAMILY_LABEL[l.family]} · {l.trigger}
            </CardDescription>
          </div>
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums">{l.volume12m === null ? "—" : count(l.volume12m)}</div>
            <div className="max-w-56 text-xs text-muted-foreground">{l.volumeNote ?? "in the last 12 months"}</div>
          </div>
        </div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {l.tags.map((t) => (
            <Badge key={t} variant="outline">
              {t}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p className="text-muted-foreground">{l.story}</p>
        <dl className="grid gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">How early we see it</dt>
            <dd>{l.notice}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Who buys</dt>
            <dd>{l.buyer}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">How to reach them</dt>
            <dd>{l.reach}</dd>
          </div>
        </dl>
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {l.stages.map((s) => (
            <div key={s.name} className="rounded-md border p-3">
              <div className="font-medium">{s.name}</div>
              <div className="mb-2 text-xs text-muted-foreground">{s.when}</div>
              <ul className="space-y-2">
                {s.services.map((sv) => {
                  const v = data.vendors[sv.vendor];
                  return (
                    <li key={`${s.name}-${sv.name}`}>
                      <div>{sv.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {v ? `${count(v.companies)} Chicago companies (${count(v.withPhone)} with a phone)` : "—"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Incumbent: {sv.incumbentShare !== null ? `${pct(sv.incumbentShare, 0)} of permits name one. ` : ""}
                        {sv.incumbent}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
        <div className="text-xs text-muted-foreground">
          Source: {l.source}
          {l.appLink && (
            <>
              {" · "}
              <Link href={l.appLink} className="text-primary hover:underline">
                Open the list
              </Link>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
