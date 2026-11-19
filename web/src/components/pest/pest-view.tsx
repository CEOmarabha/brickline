import { Download } from "lucide-react";
import Link from "next/link";
import { EmptyState, PageHeader, StatCard } from "@/components/bits";
import { CopyButton } from "@/components/copy-button";
import { PestFindingsTable } from "@/components/pest-findings-table";
import { PrintButton } from "@/components/print-button";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { count, dateLabel, pct } from "@/lib/format";
import { draftPilotEmail, findingsFor, getPest, parsePestRange, type PestCompany, type PestFile, type PestRange } from "@/lib/pest";
import { displayUrl, isHttpUrl } from "@/lib/links";
import { cn } from "@/lib/utils";
import { viewerId } from "@/lib/workspace";

type SearchParams = Record<string, string | string[] | undefined>;

/**
 * The pest-control pilot list: restaurants with a fresh pest finding, pest-control companies to pitch and the pilot
 * offer. Rendered by /pilots/pest and by /leads when the workspace is looking for pest control; the range links stay on
 * `basePath`. `title`, `description` and `actions` let a route give it its own header.
 */
export async function PestView({
  searchParams,
  basePath,
  title = "Pest-control pilot list",
  description,
  actions,
}: {
  searchParams: Promise<SearchParams>;
  basePath: string;
  title?: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  const sp = await searchParams;
  const range = parsePestRange(sp.range);
  const [owner, file] = await Promise.all([viewerId(), getPest()]);

  if (!file) {
    return (
      <>
        <PageHeader title={title} actions={actions} />
        <EmptyState title="The pest pilot list has not been generated yet">
          Run <code>uv run python -m engine.leads.pest</code> from the repository root, then reload.
        </EmptyState>
      </>
    );
  }

  const rows = findingsFor(file, range);
  const ctx = file.context;
  const email = draftPilotEmail(file);
  const emailText = `Subject: ${email.subject}\n\n${email.body}`;
  const pill = (active: boolean) =>
    cn("rounded-full border px-3 py-1 text-sm hover:bg-muted", active && "border-primary bg-primary/10 text-primary");
  const rangeLabel = range === "week" ? `last ${file.windows.weekDays} days` : `last ${file.windows.backfillDays} days`;

  return (
    <div className="space-y-8 print:space-y-4">
      <PageHeader
        title={title}
        description={
          description ?? (
            <>
              Restaurants with a fresh pest finding in the published inspection records, through {dateLabel(file.asOf)}.
              This is a pilot: one pest-control company gets the list and we record their win rate.
            </>
          )
        }
        actions={
          <>
            {actions}
            {owner && (
              <a href={`/export/pest?range=${range}`} className={buttonVariants({ variant: "outline" })}>
                <Download /> CSV ({range === "week" ? "this week" : "28 days"})
              </a>
            )}
            <PrintButton label="Print list" />
          </>
        }
      />

      <section className="space-y-3">
        <Card>
          <CardHeader>
            <CardTitle>What this list is</CardTitle>
            <CardDescription>
              {file.definition} It is a targeting list, not a prediction. Nearly every restaurant is already required to
              keep pest control, so a pest-control company&rsquo;s realistic offer is to switch or add service, and the
              pilot exists to measure how often that works.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard label="Fresh findings, latest week" value={count(file.counts.latestWeek)} />
              <StatCard label={`Fresh findings, ${file.windows.backfillDays} days`} value={count(file.counts.last28Days)} />
              <StatCard
                label={`Per week, last ${ctx.weeks} weeks`}
                value={ctx.perWeek === null ? "—" : String(ctx.perWeek)}
                hint={
                  ctx.weeklyMin === null
                    ? undefined
                    : `weekly range ${count(ctx.weeklyMin)} to ${count(ctx.weeklyMax)}; ${count(ctx.episodes)} in total`
                }
              />
              <StatCard
                label="Of those inspections, Fail"
                value={pct(ctx.failShare)}
                hint={`vs ${pct(ctx.ordinaryFailShare)} of ${count(ctx.ordinaryInspections)} ordinary restaurant inspections`}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {ctx.label}: counts and shares are computed from the inspection records for the {ctx.weeks} weeks since{" "}
              {dateLabel(ctx.windowStart)}. They describe what happened before; they say nothing about whether any
              restaurant will hire a pest-control company.
              {ctx.generalMentionOnlyShare !== null && (
                <>
                  {" "}
                  {pct(ctx.generalMentionOnlyShare, 0)} of these records mention only the generic word &ldquo;pests&rdquo; (usually an
                  entry point or clutter that could harbor them) rather than rodents, roaches, flies or insects, so read the
                  pest terms column before calling.
                </>
              )}
              {ctx.typicalWeekInspections !== null && (
                <>
                  {" "}
                  Inspections are posted with a delay: the latest 7 days show {count(ctx.latestWeekInspections)} restaurant inspections
                  against a typical {count(Math.round(ctx.typicalWeekInspections))} per week, so more rows may appear for these
                  dates in later refreshes.
                </>
              )}
            </p>
            {ctx.topAreas.length > 0 && (
              <div>
                <div className="mb-1.5 text-sm font-medium">Where the findings were, top {ctx.topAreas.length} neighborhoods</div>
                <div className="flex flex-wrap gap-2 text-sm">
                  {ctx.topAreas.map((a) => (
                    <span key={a.id} className="rounded-md border px-2 py-1">
                      {a.name} <span className="tabular-nums text-muted-foreground">{count(a.episodes)} ({pct(a.share)})</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <Link href={basePath} className={pill(range === "week")}>
            This week ({count(file.counts.latestWeek)})
          </Link>
          <Link href={`${basePath}?range=28d`} className={pill(range === "28d")}>
            Last 28 days ({count(file.counts.last28Days)})
          </Link>
        </div>
        <h2 className="text-lg font-semibold">
          {range === "week" ? "This week" : "Last 28 days"}{" "}
          <span className="text-sm font-normal text-muted-foreground">
            ({rangeLabel}, {count(rows.length)} restaurants)
          </span>
        </h2>
        {rows.length === 0 ? (
          <EmptyState title="No fresh pest findings in this window" />
        ) : (
          <PestFindingsTable rows={rows} />
        )}
        <p className="text-xs text-muted-foreground">
          &ldquo;Re-inspected since&rdquo; is the newest restaurant inspection after the finding; a Pass there means the
          problem may already be handled. &ldquo;Same-name locations&rdquo; counts other licenses inspected in the last 12
          months under the same normalized name: chains and franchises can be separately owned, so check before treating
          them as one account. Contact details come from Overture Maps public business listings ({count(file.counts.withContact)} of{" "}
          {count(file.counts.last28Days)} restaurants in the 28 days have one); they are never guessed and can be out of
          date. {file.attribution.contactMatch}
        </p>
        <Card size="sm" className="print:hidden">
          <CardContent className="text-sm text-muted-foreground">
            <strong className="text-foreground">How to reach restaurants:</strong> manual phone calls to business lines
            during business hours, walk-in visits, or one-to-one email with a real sender, postal address and opt-out. No
            autodialed, prerecorded or AI-voice calls and no text messages. Never say or imply you represent a government
            or health agency.
          </CardContent>
        </Card>
      </section>

      <PestCompanies companies={file.pestCompanies} />
      <PilotOffer file={file} range={range} emailText={emailText} subject={email.subject} body={email.body} />
    </div>
  );
}

function PestCompanies({ companies }: { companies: PestCompany[] }) {
  return (
    <section className="space-y-3 print:hidden">
      <h2 className="text-lg font-semibold">
        Pest-control companies to pitch{" "}
        <span className="text-sm font-normal text-muted-foreground">({count(companies.length)} in Chicago)</span>
      </h2>
      {companies.length === 0 ? (
        <EmptyState title="No pest-control listings found" />
      ) : (
        <div className="max-h-[36rem] overflow-auto rounded-lg border">
          <table className="w-full min-w-[56rem] text-sm">
            <thead className="sticky top-0 border-b bg-background text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Company</th>
                <th className="px-3 py-2 font-medium">Phone</th>
                <th className="px-3 py-2 font-medium">Website</th>
                <th className="px-3 py-2 font-medium">Email</th>
                <th className="px-3 py-2 font-medium">Address</th>
                <th className="px-3 py-2 font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {companies.map((c, i) => (
                <tr key={`${c.name}-${c.phone}-${i}`} className="align-top">
                  <td className="px-3 py-2 font-medium">
                    {c.name}
                    {c.licensedLegalName && (
                      <div className="text-xs font-normal text-muted-foreground">
                        Licensed as {c.licensedLegalName} (Chicago business licenses)
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">{c.phone ?? "—"}</td>
                  <td className="px-3 py-2">
                    {c.website && isHttpUrl(c.website) ? (
                      <a href={c.website} target="_blank" rel="noopener noreferrer" className="underline">
                        {displayUrl(c.website)}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-2">{c.email ?? "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.address ?? "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        Business listings from Overture Maps (not verified; some may be closed or duplicates). Call or email business
        contacts by hand only.
      </p>
    </section>
  );
}

function PilotOffer({
  file,
  range,
  emailText,
  subject,
  body,
}: {
  file: PestFile;
  range: PestRange;
  emailText: string;
  subject: string;
  body: string;
}) {
  return (
    <section className="print:hidden">
      <Card>
        <CardHeader>
          <CardTitle>Pilot offer</CardTitle>
          <CardDescription>
            Free 4-week trial list in exchange for the pest-control company telling us which restaurants they contacted and
            which they won. Review and personalize by hand before sending from your own mailbox; fill in every bracketed
            field.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border bg-muted/30 p-4 text-sm">
            <div className="mb-2 font-medium">Subject: {subject}</div>
            <pre className="font-sans whitespace-pre-wrap">{body}</pre>
          </div>
          <div className="flex flex-wrap gap-2">
            <CopyButton text={emailText} label="Copy email" />
            <a href={`/export/pest?range=${range}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <Download /> Download list to attach
            </a>
          </div>
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>
              <strong className="text-foreground">Record outcomes every week.</strong> The pilot only teaches us something
              if we write down, per restaurant (license number and inspection id are in the CSV): who contacted it, when,
              by phone, visit or email, and whether it was won, lost or got no answer. The CSV has empty date_contacted,
              outcome and notes columns for the pest-control company to fill in.
            </p>
            <p>
              Send only to business addresses. Honor opt-outs the same day and keep an internal do-not-contact list. List
              data as of {dateLabel(file.asOf)}; {file.attribution.text}
            </p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
