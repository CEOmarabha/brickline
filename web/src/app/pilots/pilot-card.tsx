import { Download } from "lucide-react";
import Link from "next/link";
import { StatCard } from "@/components/bits";
import { CopyButton } from "@/components/copy-button";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { BuyerList } from "@/lib/buyers";
import type { PilotCard } from "@/lib/pilot-pitches";
import { BuyersTable } from "./buyers-table";

export function PilotListCard({
  card,
  list,
  signedIn,
}: {
  card: PilotCard;
  list: BuyerList | undefined;
  signedIn: boolean;
}) {
  return (
    <Card id={card.anchor} className="scroll-mt-6">
      <CardHeader>
        <CardTitle className="text-lg">{card.title}</CardTitle>
        <CardDescription>{card.summary}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {card.stats.length > 0 && (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {card.stats.map((s) => (
              <StatCard key={s.label} label={s.label} value={s.value} hint={s.hint} />
            ))}
          </div>
        )}
        <p className="text-xs text-muted-foreground">{card.caveat}</p>

        <div className="flex flex-wrap gap-2">
          {card.links
            .filter((l) => !l.csv || signedIn)
            .map((l) =>
              l.csv ? (
                <a key={l.href} href={l.href} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  <Download /> {l.label}
                </a>
              ) : (
                <Link key={l.href} href={l.href} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  {l.label}
                </Link>
              ),
            )}
        </div>

        <section className="space-y-2" aria-labelledby={`${card.anchor}-buyers`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 id={`${card.anchor}-buyers`} className="text-base font-semibold">
              Who buys this
            </h3>
            {signedIn && list && (
              <a
                href={`/export/buyers?list=${list.key}`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                <Download /> Buyers CSV
              </a>
            )}
          </div>
          {list ? (
            <BuyersTable list={list} />
          ) : (
            <p className="text-sm text-muted-foreground">
              No buyers file yet. Run <code>uv run python -m engine.leads.buyers</code>, then reload.
            </p>
          )}
        </section>

        {card.emails.length > 0 && (
          <section className="space-y-2" aria-labelledby={`${card.anchor}-pitch`}>
            <h3 id={`${card.anchor}-pitch`} className="text-base font-semibold">
              Pitch email drafts
            </h3>
            <p className="text-sm text-muted-foreground">
              One-to-one drafts, one per buyer type: a free sample of 5 rows, then a 4-week trial in exchange for
              recording outcomes. Fill every bracketed field, personalize by hand and send from your own mailbox. Send
              only to business addresses, honor opt-outs the same day, and phone business lines by hand only.
            </p>
            <div className="space-y-2">
              {card.emails.map((e, i) => (
                <details key={e.key} className="group rounded-md border" open={i === 0 && card.emails.length === 1}>
                  <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium select-none">
                    {e.label}
                  </summary>
                  <div className="space-y-3 border-t p-4 text-sm">
                    <div className="rounded-md border bg-muted/30 p-4">
                      <div className="mb-2 font-medium">Subject: {e.subject}</div>
                      <pre className="font-sans whitespace-pre-wrap">{e.body}</pre>
                    </div>
                    <CopyButton text={`Subject: ${e.subject}\n\n${e.body}`} label="Copy email" />
                  </div>
                </details>
              ))}
            </div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}
