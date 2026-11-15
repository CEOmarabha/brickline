import { Globe, Phone } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { count, dateLabel } from "@/lib/format";
import type { PestContact, PestFinding } from "@/lib/pest";
import { isHttpUrl } from "@/lib/pipeline";
import { cn } from "@/lib/utils";

function Contact({ contact }: { contact: PestContact | null }) {
  if (!contact) return <span className="text-muted-foreground">—</span>;
  return (
    <div className="space-y-0.5">
      {contact.phone && (
        <div className="flex items-center gap-1 whitespace-nowrap">
          <Phone className="size-3 text-muted-foreground" aria-hidden /> {contact.phone}
        </div>
      )}
      {contact.website && isHttpUrl(contact.website) && (
        <div className="flex items-center gap-1">
          <Globe className="size-3 shrink-0 text-muted-foreground" aria-hidden />
          <a href={contact.website} target="_blank" rel="noopener noreferrer" className="max-w-40 truncate underline">
            {contact.website.replace(/^https?:\/\/(www\.)?/, "")}
          </a>
        </div>
      )}
      <div className="text-[11px] text-muted-foreground">{contact.source}, listed as {contact.placeName}</div>
    </div>
  );
}

function Since({ f }: { f: PestFinding }) {
  const last = f.lastInspection;
  if (!last) return <span className="text-muted-foreground">Not yet</span>;
  const closed = last.result === "Out of Business";
  return (
    <div className="whitespace-nowrap">
      <span className={cn(closed && "font-medium text-amber-700")}>{last.result}</span>
      <div className="text-xs text-muted-foreground">
        {dateLabel(last.date)}
        {f.inspectionsSince > 1 ? `, ${count(f.inspectionsSince)} inspections` : ""}
      </div>
    </div>
  );
}

export function PestFindingsTable({ rows }: { rows: PestFinding[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border print:overflow-visible">
      <table className="w-full min-w-[78rem] text-sm print:min-w-0 print:text-[8pt]">
        <thead className="border-b text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Restaurant</th>
            <th className="px-3 py-2 font-medium">Address</th>
            <th className="px-3 py-2 font-medium">Neighborhood</th>
            <th className="px-3 py-2 font-medium">Inspected</th>
            <th className="px-3 py-2 font-medium">Result</th>
            <th className="px-3 py-2 font-medium">Pest terms in record</th>
            <th className="px-3 py-2 font-medium">Findings, prior 2 yrs</th>
            <th className="px-3 py-2 font-medium">Re-inspected since</th>
            <th className="px-3 py-2 font-medium">Same-name locations</th>
            <th className="px-3 py-2 font-medium">Public listing contact</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((f) => (
            <tr key={f.inspectionId} className="align-top">
              <td className="px-3 py-2.5 font-medium">
                {f.restaurant}
                <div className="text-xs font-normal text-muted-foreground">License {f.licenseNo}</div>
              </td>
              <td className="px-3 py-2.5">{f.address}</td>
              <td className="px-3 py-2.5 text-muted-foreground">{f.communityArea?.name ?? "—"}</td>
              <td className="px-3 py-2.5 whitespace-nowrap">
                {dateLabel(f.date)}
                <div className="text-xs text-muted-foreground">{f.inspectionType}</div>
              </td>
              <td className="px-3 py-2.5">
                <Badge variant={f.result === "Fail" ? "destructive" : "secondary"}>{f.result}</Badge>
              </td>
              <td className="px-3 py-2.5">
                <span className="capitalize">{f.pestTerms.join(", ")}</span>
                {f.pestTermsGeneralOnly && (
                  <div className="text-xs text-muted-foreground">general mention only</div>
                )}
              </td>
              <td className="px-3 py-2.5 tabular-nums">{count(f.pestFindings2y)}</td>
              <td className="px-3 py-2.5">
                <Since f={f} />
              </td>
              <td className="px-3 py-2.5">
                {f.otherLocations === 0 ? (
                  <span className="text-muted-foreground">None</span>
                ) : (
                  <span title="Other licenses with the same normalized name inspected in the last 365 days; chains may be separately owned">
                    {count(f.otherLocations)} other{f.otherLocations === 1 ? "" : "s"}
                    <div className="text-xs text-muted-foreground">
                      {count(f.otherLocationsPest365)} pest finding{f.otherLocationsPest365 === 1 ? "" : "s"}, 12 mo
                    </div>
                  </span>
                )}
              </td>
              <td className="px-3 py-2.5">
                <Contact contact={f.contact} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
