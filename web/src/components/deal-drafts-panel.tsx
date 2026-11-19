"use client";

import { Ban, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { CopyButton } from "@/components/copy-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  buildDealDrafts,
  COMPLIANCE_CHECKLIST,
  DEFAULT_SENDER_ADDRESS,
  DEFAULT_SENDER_BUSINESS,
  DEFAULT_SENDER_NAME,
  type DraftInput,
  type DraftKind,
  DRAFT_LABEL,
} from "@/lib/deal-drafts";

const ORDER: DraftKind[] = ["dm", "email", "follow_up", "quote"];

export type DraftDeal = Omit<DraftInput, "occasion" | "sender">;

/**
 * Drafts for one deal, rebuilt as the sender fields change. Nothing here is saved or sent: the founder copies a draft
 * and sends it himself. An opted-out buyer gets a refusal instead of drafts.
 */
export function DealDraftsPanel({
  deal,
  businessName,
  mailingAddress,
}: {
  deal: DraftDeal;
  businessName: string;
  mailingAddress: string;
}) {
  const [name, setName] = useState("");
  const [business, setBusiness] = useState(businessName);
  const [address, setAddress] = useState(mailingAddress);
  const [occasion, setOccasion] = useState("");

  const result = useMemo(
    () =>
      buildDealDrafts({
        ...deal,
        occasion,
        sender: {
          name: name.trim() || DEFAULT_SENDER_NAME,
          business: business.trim() || DEFAULT_SENDER_BUSINESS,
          address: address.trim() || DEFAULT_SENDER_ADDRESS,
        },
      }),
    [deal, occasion, name, business, address],
  );

  const initial: DraftKind = deal.channel === "email" ? "email" : "dm";

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="min-w-0 space-y-4">
        {result.refused ? (
          <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
            <Ban className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
            <div>
              <div className="font-medium text-destructive">Do not contact</div>
              <p className="text-muted-foreground">{result.reason}</p>
            </div>
          </div>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="dr-name">Your name</Label>
                <Input id="dr-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} placeholder={DEFAULT_SENDER_NAME} autoComplete="off" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="dr-business">Business name</Label>
                <Input id="dr-business" value={business} onChange={(e) => setBusiness(e.target.value)} maxLength={120} placeholder={DEFAULT_SENDER_BUSINESS} autoComplete="off" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="dr-address">Mailing address (for email)</Label>
                <Input id="dr-address" value={address} onChange={(e) => setAddress(e.target.value)} maxLength={200} placeholder={DEFAULT_SENDER_ADDRESS} autoComplete="off" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="dr-occasion">What you saw, in general terms</Label>
                <Input id="dr-occasion" value={occasion} onChange={(e) => setOccasion(e.target.value)} maxLength={80} placeholder="e.g. a graduation party" autoComplete="off" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Business name and address start from the current workspace&apos;s Settings; change them here if this
              workspace belongs to a client. Nothing on this form is saved.
            </p>

            {result.warnings.length > 0 && (
              <ul className="space-y-1 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-900">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}

            <Tabs defaultValue={initial}>
              <TabsList className="h-auto flex-wrap">
                {ORDER.map((k) => (
                  <TabsTrigger key={k} value={k}>
                    {DRAFT_LABEL[k]}
                  </TabsTrigger>
                ))}
              </TabsList>
              {ORDER.map((k) => {
                const draft = result.drafts.find((d) => d.kind === k);
                if (!draft) return null;
                const text = draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body;
                return (
                  <TabsContent key={k} value={k} className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="text-sm">
                        {draft.subject ? (
                          <>
                            <span className="text-muted-foreground">Subject: </span>
                            <span className="font-medium">{draft.subject}</span>
                          </>
                        ) : (
                          <span className="text-xs text-muted-foreground">{draft.body.length} characters</span>
                        )}
                      </div>
                      <CopyButton text={text} label="Copy draft" />
                    </div>
                    <pre
                      className="rounded-md border bg-muted/40 p-4 font-sans text-sm leading-relaxed whitespace-pre-wrap"
                      data-draft={k}
                    >
                      {draft.body}
                    </pre>
                  </TabsContent>
                );
              })}
            </Tabs>
          </>
        )}
      </div>

      <aside className="space-y-3 rounded-lg border bg-muted/30 p-4" aria-label="Compliance checklist">
        <div className="flex items-center gap-2 text-sm font-medium">
          <ShieldCheck className="size-4 text-primary" aria-hidden /> Before you send
        </div>
        <ul className="space-y-2.5 text-sm">
          {COMPLIANCE_CHECKLIST.map((c) => (
            <li key={c.rule}>
              <div className="font-medium">{c.rule}</div>
              <div className="text-xs text-muted-foreground">{c.detail}</div>
            </li>
          ))}
        </ul>
        <p className="text-xs text-muted-foreground">
          Operating rules, not legal advice. Drafts are starting points: you read, edit and send each one yourself.
        </p>
      </aside>
    </div>
  );
}
