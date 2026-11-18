"use client";

import { Check, Pencil } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { SAVE_FAILED, useRun } from "@/components/deal-fields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { UserError } from "@/lib/action-result";
import { createPartner, updatePartner } from "@/lib/deal-actions";
import { cleanPartnerFields } from "@/lib/deals";
import { isHttpUrl } from "@/lib/links";

export interface PartnerItem {
  id: string;
  name: string;
  services: string;
  area: string;
  contactName: string;
  phone: string;
  email: string;
  website: string;
  feeTerms: string;
  agreementSigned: boolean;
  notes: string;
  dealCount: number;
}

function PartnerForm({ partner, onDone }: { partner: PartnerItem | null; onDone: () => void }) {
  const { pending, run } = useRun();
  const [name, setName] = useState(partner?.name ?? "");
  const [services, setServices] = useState(partner?.services ?? "");
  const [area, setArea] = useState(partner?.area ?? "");
  const [contactName, setContactName] = useState(partner?.contactName ?? "");
  const [phone, setPhone] = useState(partner?.phone ?? "");
  const [email, setEmail] = useState(partner?.email ?? "");
  const [website, setWebsite] = useState(partner?.website ?? "");
  const [feeTerms, setFeeTerms] = useState(partner?.feeTerms ?? "");
  const [signed, setSigned] = useState(partner?.agreementSigned ?? false);
  const [notes, setNotes] = useState(partner?.notes ?? "");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const fields = { name, services, area, contactName, phone, email, website, feeTerms, agreementSigned: signed, notes };
    try {
      const clean = cleanPartnerFields(fields);
      setWebsite(clean.website ?? "");
      setServices(clean.services ?? "");
    } catch (error) {
      toast.error(error instanceof UserError ? error.message : SAVE_FAILED);
      return;
    }
    if (partner) {
      run(() => updatePartner(partner.id, fields), "Partner saved", (ok) => ok && onDone());
      return;
    }
    run(
      async () => {
        const result = await createPartner(fields);
        return result.ok ? { ok: true as const } : result;
      },
      "Partner added",
      (ok) => ok && onDone(),
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border p-4" aria-label={partner ? "Edit partner" : "Add a partner"}>
      <h2 className="text-sm font-medium">{partner ? `Edit ${partner.name}` : "Add a partner"}</h2>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="pm-name">Business name</Label>
          <Input id="pm-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} autoComplete="off" />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="pm-services">Services (comma separated)</Label>
          <Input
            id="pm-services"
            value={services}
            onChange={(e) => setServices(e.target.value)}
            maxLength={300}
            placeholder="e.g. tent rental, tables and chairs"
            autoComplete="off"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pm-area">Area served</Label>
          <Input id="pm-area" value={area} onChange={(e) => setArea(e.target.value)} maxLength={120} placeholder="e.g. Chicago and near suburbs" autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pm-contact">Contact name</Label>
          <Input id="pm-contact" value={contactName} onChange={(e) => setContactName(e.target.value)} maxLength={120} autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pm-phone">Phone</Label>
          <Input id="pm-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={40} autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pm-email">Email</Label>
          <Input id="pm-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={200} autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pm-website">Website</Label>
          <Input id="pm-website" value={website} onChange={(e) => setWebsite(e.target.value)} maxLength={200} placeholder="https://" autoComplete="off" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pm-fee">Fee terms</Label>
          <Input
            id="pm-fee"
            value={feeTerms}
            onChange={(e) => setFeeTerms(e.target.value)}
            maxLength={200}
            placeholder="e.g. 10% of booking, or $75 per appointment"
            autoComplete="off"
          />
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="size-4 accent-primary" checked={signed} onChange={(e) => setSigned(e.target.checked)} />
        Agreement signed
      </label>
      <div className="space-y-1.5">
        <Label htmlFor="pm-notes">Notes</Label>
        <Textarea id="pm-notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} maxLength={4000} />
      </div>
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={pending}>
          {partner ? "Save changes" : "Add partner"}
        </Button>
        {partner && (
          <Button type="button" size="sm" variant="ghost" disabled={pending} onClick={onDone}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

export function PartnerManager({ partners, disabled }: { partners: PartnerItem[]; disabled: boolean }) {
  const [editingId, setEditingId] = useState<string | null>(null);
  // A new key remounts the form, which clears it after a partner is added or saved.
  const [formRun, setFormRun] = useState(0);
  const editing = partners.find((p) => p.id === editingId) ?? null;

  return (
    <div className="space-y-4">
      {!disabled && (
        <PartnerForm
          key={`${editing?.id ?? "new"}-${formRun}`}
          partner={editing}
          onDone={() => {
            setEditingId(null);
            setFormRun((n) => n + 1);
          }}
        />
      )}

      {partners.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No partners yet. Add the vendors who do the work: rental companies, caterers, contractors.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[56rem] text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Partner</th>
                <th className="px-4 py-2 font-medium">Services</th>
                <th className="px-4 py-2 font-medium">Area</th>
                <th className="px-4 py-2 font-medium">Contact</th>
                <th className="px-4 py-2 font-medium">Fee terms</th>
                <th className="px-4 py-2 font-medium">Agreement</th>
                <th className="px-4 py-2 font-medium">Deals</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {partners.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-2.5 font-medium">{p.name}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{p.services || "—"}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{p.area || "—"}</td>
                  <td className="px-4 py-2.5">
                    <div>{p.contactName || <span className="text-muted-foreground">—</span>}</div>
                    <div className="text-xs text-muted-foreground">{[p.phone, p.email].filter(Boolean).join(" · ")}</div>
                    {isHttpUrl(p.website) && (
                      <a
                        href={p.website}
                        target="_blank"
                        rel="noopener noreferrer nofollow"
                        className="text-xs text-primary underline-offset-4 hover:underline"
                      >
                        Website
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">{p.feeTerms || "—"}</td>
                  <td className="px-4 py-2.5">
                    {p.agreementSigned ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700">
                        <Check className="size-3.5" aria-hidden /> Signed
                      </span>
                    ) : (
                      <span className="text-amber-700">Not yet</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">{p.dealCount}</td>
                  <td className="px-4 py-2.5 text-right">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={disabled}
                      onClick={() => {
                        setEditingId(p.id);
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }}
                    >
                      <Pencil /> Edit
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
