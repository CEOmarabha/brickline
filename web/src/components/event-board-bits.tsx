import { type BoardEvent, type EventBoard, HOST_TYPE_LABEL } from "@/lib/event-board";
import { isHttpUrl } from "@/lib/links";

export function ContactLinks({ phone, email, website }: { phone: string | null; email: string | null; website: string | null }) {
  if (!phone && !email && !website) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
      {phone && (
        <a href={`tel:${phone.replace(/\D/g, "")}`} className="text-primary hover:underline">
          {phone}
        </a>
      )}
      {email && (
        <a href={`mailto:${email}`} className="text-primary hover:underline">
          {email}
        </a>
      )}
      {website && isHttpUrl(website) && (
        <a href={website} target="_blank" rel="noopener noreferrer nofollow" className="text-primary hover:underline">
          website
        </a>
      )}
    </div>
  );
}

/** The host with its public contact details, and the alderman's office for the ward (or the permit status). */
export function EventHostPanels({ e, board }: { e: BoardEvent; board: EventBoard }) {
  const ward = e.ward ? board.wards[String(e.ward)] : undefined;
  return (
    <div className="grid gap-3 text-sm sm:grid-cols-2">
      <div className="rounded-md border p-3">
        <div className="text-xs text-muted-foreground">Host · {HOST_TYPE_LABEL[e.host.type]}</div>
        <div className="font-medium">{e.host.name ?? "Not published"}</div>
        {e.host.mailing && <div>{e.host.mailing}</div>}
        <ContactLinks phone={e.host.phone} email={e.host.email} website={e.host.website} />
        {e.host.needsSkipTrace && (
          <div className="mt-1 text-xs text-amber-700">
            No public phone: skip trace (about ${board.skipTrace.priceLow.toFixed(2)}–${board.skipTrace.priceHigh.toFixed(2)}), then a Do
            Not Call scrub. Mail or a door hanger works now.
          </div>
        )}
        {e.host.source && <div className="mt-1 text-xs text-muted-foreground">Contact source: {e.host.source}</div>}
      </div>
      {ward && e.host.type !== "ward_office" ? (
        <div className="rounded-md border p-3">
          <div className="text-xs text-muted-foreground">Alderman&apos;s office (approves block parties and street events)</div>
          <div className="font-medium">
            Ward {ward.ward} · {ward.alderman}
          </div>
          <div>{ward.address}</div>
          <ContactLinks phone={ward.phone} email={ward.email} website={ward.website} />
        </div>
      ) : (
        <div className="rounded-md border p-3 text-xs text-muted-foreground">
          Status: {e.status ?? "—"}
          <br />
          Source: {e.source}
        </div>
      )}
    </div>
  );
}
