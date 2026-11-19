import { Download } from "lucide-react";
import Link from "next/link";
import { StatCard } from "@/components/bits";
import { CopyButton } from "@/components/copy-button";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { EventsPilotCard } from "@/lib/pilot-pitches";

export function EventsListCard({ card, signedIn }: { card: EventsPilotCard; signedIn: boolean }) {
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
          <h3 id={`${card.anchor}-buyers`} className="text-base font-semibold">
            Who buys this
          </h3>
          <ul className="space-y-2 text-sm">
            {card.buyerTypes.map((b) => (
              <li key={b.label} className="rounded-md border px-4 py-2.5">
                <div className="font-medium">{b.label}</div>
                <div className="text-muted-foreground">{b.why}</div>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            No company list is generated for these buyers yet; search for local tent, restroom, fencing, generator and
            security companies by hand and check each one&rsquo;s website before sending the draft.
          </p>
        </section>

        {card.emails.length > 0 && (
          <section className="space-y-2" aria-labelledby={`${card.anchor}-pitch`}>
            <h3 id={`${card.anchor}-pitch`} className="text-base font-semibold">
              Pitch email draft
            </h3>
            <p className="text-sm text-muted-foreground">
              A one-to-one draft for rental and service companies: a free sample of 5 rows, then a 4-week trial in
              exchange for recording outcomes. Fill every bracketed field, personalize by hand and send from your own
              mailbox. Send only to business addresses and honor opt-outs the same day.
            </p>
            <div className="space-y-2">
              {card.emails.map((e) => (
                <details key={e.key} className="group rounded-md border">
                  <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium select-none">{e.label}</summary>
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
