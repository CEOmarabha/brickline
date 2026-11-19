import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { count, dateLabel, pct } from "@/lib/format";
import { INCUMBENT_UNKNOWN, type JobStage, type JobsPlan, type PossibleJob } from "@/lib/possible-jobs";
import { cn } from "@/lib/utils";

function StageBadge({ st }: { st: JobStage }) {
  if (st.state === "now") return <Badge>Now</Badge>;
  if (st.state === "passed") return <Badge variant="outline">Passed</Badge>;
  if (st.state === "next") {
    return <Badge variant="outline">{st.startsIn === 1 ? "Starts tomorrow" : `Starts in ${st.startsIn} days`}</Badge>;
  }
  return null;
}

function windowLabel(st: JobStage): string {
  if (!st.from || !st.to) return st.when;
  return `${st.from === st.to ? dateLabel(st.from) : `${dateLabel(st.from)} – ${dateLabel(st.to)}`} · ${st.when}`;
}

function Job({ job, emphasize }: { job: PossibleJob; emphasize: boolean }) {
  const top = job.chances[0];
  return (
    <li className="space-y-0.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className={cn(emphasize && "font-medium")}>{job.name}</span>
        {top && (
          <span className="shrink-0 text-sm tabular-nums" title={`Chance of a ${top.label.toLowerCase()} permit`}>
            {pct(top.p)}
          </span>
        )}
      </div>
      {job.chances.length > 0 && (
        <div className="text-xs text-muted-foreground">
          Chance of a permit: {job.chances.map((c) => `${c.label} ${pct(c.p)}`).join(" · ")}
        </div>
      )}
      {job.companies !== null && (
        <div className="text-xs text-muted-foreground">
          {count(job.companies)} Chicago companies sell it ({count(job.withPhone)} with a phone)
        </div>
      )}
      {job.partners.length > 0 && (
        <div className="text-xs text-muted-foreground">
          e.g.{" "}
          {job.partners.slice(0, 3).map((p, i) => (
            <span key={p.name}>
              {i > 0 && ", "}
              {p.name}
              {p.phone && (
                <>
                  {" "}
                  <a href={`tel:${p.phone.replace(/\D/g, "")}`} className="text-primary hover:underline">
                    {p.phone}
                  </a>
                </>
              )}
            </span>
          ))}
        </div>
      )}
      {job.usedBefore.length > 0 && (
        <div className="text-xs text-muted-foreground">
          This buyer used before: {job.usedBefore.slice(0, 3).map((c) => `${c.name} (${c.jobs} ${c.jobs === 1 ? "job" : "jobs"})`).join(", ")}
        </div>
      )}
      {job.incumbent !== INCUMBENT_UNKNOWN && (
        <div className="text-xs text-muted-foreground">
          Who has it: {job.incumbentShare !== null ? `${pct(job.incumbentShare, 0)} of permits name one. ` : ""}
          {job.incumbent}
        </div>
      )}
    </li>
  );
}

/** The dated stages and their jobs, with a footnote on where the dates, chances and partners come from. */
export function PossibleJobs({ plan }: { plan: JobsPlan }) {
  const jobs = plan.stages.flatMap((s) => s.jobs);
  const hasChances = jobs.some((j) => j.chances.length > 0);
  const hasPartners = jobs.some((j) => j.partners.length > 0);
  const unknownIncumbent = jobs.some((j) => j.incumbent === INCUMBENT_UNKNOWN);
  const dated = plan.stages.some((s) => s.state !== "undated");
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {plan.stages.map((st) => (
          <div
            key={st.name}
            className={cn(
              "rounded-md border p-3",
              st.state === "now" && "border-primary/40 bg-primary/5",
              st.state === "passed" && "opacity-60",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-medium">{st.name}</span>
              <StageBadge st={st} />
            </div>
            <div className="text-xs text-muted-foreground">{windowLabel(st)}</div>
            <ul className="mt-2 space-y-2 text-sm">
              {st.jobs.map((job) => (
                <Job key={job.name} job={job} emphasize={st.state === "now"} />
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="space-y-1 text-xs text-muted-foreground">
        {dated && (
          <p>
            Stage dates are rules of thumb counted from {plan.anchorLabel} ({dateLabel(plan.anchor)}), as of{" "}
            {dateLabel(plan.asOf)}; work can run early or late.
          </p>
        )}
        {hasChances && (
          <p>
            Chance of a permit: how often similar leads were followed by a permit of that trade at the address. It counts
            permitted work only, so real demand is higher.
          </p>
        )}
        {unknownIncumbent && (
          <p>Jobs without a &ldquo;Who has it&rdquo; line: public records don&apos;t show the current provider. Ask, or offer to match them.</p>
        )}
        {hasPartners && (
          <p>Partner examples are public business listings (Overture Maps); call to confirm they do this work before you sign them.</p>
        )}
        <p>
          <Link href={`/opportunities#${plan.lifecycleId}`} className="text-primary hover:underline">
            Full lifecycle on the opportunity map
          </Link>
        </p>
      </div>
    </div>
  );
}

export function PossibleJobsCard({ plan, description }: { plan: JobsPlan; description?: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle>Possible jobs</CardTitle>
            <CardDescription>
              {description ?? `${plan.lifecycleName}: the jobs it sets off, stage by stage, and who sells each one.`}
            </CardDescription>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-2xl font-semibold tabular-nums">{plan.jobs}</div>
            <div className="text-xs text-muted-foreground">
              {plan.openNow} open now · {plan.comingUp} coming up
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <PossibleJobs plan={plan} />
      </CardContent>
    </Card>
  );
}
