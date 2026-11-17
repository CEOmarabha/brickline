import type { PermitContractor } from "@/lib/snapshot";
import { dateLabel } from "@/lib/format";
import { isHttpUrl } from "@/lib/links";

export function classLabel(c: string): string {
  return c === "unknown class" ? "Class not on record" : c.charAt(0).toUpperCase() + c.slice(1);
}

export function SourceDate({ url, date }: { url: string; date: string }) {
  if (!isHttpUrl(url)) return <>{dateLabel(date)}</>;
  return (
    <a href={url} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
      {dateLabel(date)}
    </a>
  );
}

export function contractorList(list: PermitContractor[], max: number): string {
  const shown = list.slice(0, max).map((c) => `${c.name} (${c.role.toLowerCase()})`);
  return list.length > max ? `${shown.join("; ")}; +${list.length - max} more` : shown.join("; ");
}

export function range(lo: number | null, hi: number | null): string {
  return lo === null || hi === null ? "—" : `${lo.toFixed(0)}–${hi.toFixed(0)}`;
}
