import { Fragment } from "react";
import { EmptyState } from "@/components/bits";
import type { BuyerList } from "@/lib/buyers";
import { count, pct } from "@/lib/format";
import { displayUrl, isHttpUrl } from "@/lib/links";

function searchUrl(name: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(`${name} Chicago`)}`;
}

/** "Who buys this": the list's buyers grouped by buyer type, with contact details and why each is listed. */
export function BuyersTable({ list }: { list: BuyerList }) {
  if (list.buyers.length === 0) return <EmptyState title="No buyers found for this list" />;
  const c = list.counts;
  return (
    <div className="space-y-2">
      <div className="max-h-[34rem] overflow-auto rounded-lg border">
        <table className="w-full min-w-[64rem] text-sm">
          <thead className="sticky top-0 z-10 border-b bg-background text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Company</th>
              <th className="px-3 py-2 font-medium">Phone</th>
              <th className="px-3 py-2 font-medium">Website</th>
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Why listed</th>
              <th className="px-3 py-2 font-medium">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {list.segments.map((seg) => {
              const rows = list.buyers.filter((b) => b.segment === seg.key);
              if (rows.length === 0) return null;
              return (
                <Fragment key={seg.key}>
                  <tr className="bg-muted/40">
                    <td colSpan={6} className="px-3 py-1.5 text-xs font-medium">
                      {seg.label}{" "}
                      <span className="font-normal text-muted-foreground">
                        top {count(rows.length)} of {count(seg.available)} found
                      </span>
                    </td>
                  </tr>
                  {rows.map((b, i) => (
                    <tr key={`${seg.key}-${i}`} className="align-top">
                      <td className="px-3 py-2">
                        <div className="font-medium">{b.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {b.category ?? "—"}
                          {b.address ? ` · ${b.address}` : ""}
                        </div>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">{b.phone ?? "—"}</td>
                      <td className="px-3 py-2">
                        {b.website && isHttpUrl(b.website) ? (
                          <a href={b.website} target="_blank" rel="noopener noreferrer" className="underline">
                            {displayUrl(b.website)}
                          </a>
                        ) : (
                          <a
                            href={searchUrl(b.name)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-muted-foreground underline"
                          >
                            Search the web
                          </a>
                        )}
                      </td>
                      <td className="px-3 py-2 break-all">{b.email ?? "—"}</td>
                      <td className="max-w-md px-3 py-2 text-xs text-muted-foreground">{b.evidence}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{b.sources.join(", ")}</td>
                    </tr>
                  ))}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        {count(c.buyers)} buyers: {pct(c.phoneShare, 0)} with a phone, {pct(c.websiteShare, 0)} with a website,{" "}
        {pct(c.emailShare, 0)} with an email, {pct(c.anyContactShare, 0)} with at least a phone or website.
      </p>
    </div>
  );
}
