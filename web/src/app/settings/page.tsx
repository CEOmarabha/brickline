import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/bits";
import { SettingsForm } from "@/components/settings-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { pct } from "@/lib/format";
import { isHttpUrl } from "@/lib/links";
import { getSnapshot, leadsForWorkspace, TRADE_KEYS } from "@/lib/snapshot";
import { getWorkspace } from "@/lib/workspace";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Your trade and neighborhoods decide which leads you see and how they're scored." />
      <Suspense fallback={<Skeleton className="h-[36rem] w-full" />}>
        <Settings />
      </Suspense>
    </>
  );
}

async function Settings() {
  const [snap, ws] = await Promise.all([getSnapshot(), getWorkspace()]);
  const trades = Object.fromEntries(TRADE_KEYS.map((k) => [k, snap.trades[k].label]));
  const leads = leadsForWorkspace(snap, ws.trade, []);
  const areas = snap.areas
    .map((a) => ({ id: a.id, name: a.name, leads: leads.filter((l) => l.communityArea === a.id).length }))
    .sort((a, b) => a.name.localeCompare(b.name));
  const { winRate, margin } = snap.meta.assumptions;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardContent>
          <SettingsForm
            key={ws.id}
            initial={{
              businessName: ws.businessName,
              trade: ws.trade,
              areas: ws.areas,
              phone: ws.phone,
              mailingAddress: ws.mailingAddress,
              holdoutPct: ws.holdoutPct,
            }}
            trades={trades}
            areas={areas}
          />
        </CardContent>
      </Card>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>How scores work</CardTitle>
            <CardDescription>No guesses: every chance-of-work number is a historical rate.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              For each signal we measured how often the same kind of event in Chicago (2012–2025) was followed by a
              permitted job, then adjust for how much time has already passed.
            </p>
            <p>
              Expected value multiplies that by a close rate ({pct(winRate.individual, 0)} for mailed homeowners,{" "}
              {pct(winRate.company, 0)} for companies you can call), the typical permitted job size in your trade, and a{" "}
              {pct(margin, 0)} margin. As you mark leads won or lost, we&apos;ll replace those assumptions with your
              real numbers.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Data sources</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {snap.meta.sources.map((s) => (
                <li key={s.url}>
                  {isHttpUrl(s.url) ? (
                    <a href={s.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                      {s.name}
                    </a>
                  ) : (
                    s.name
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
