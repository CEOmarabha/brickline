/** RFC 4180 CSV with spreadsheet formula-injection protection. */
export function toCsv(header: string[], rows: (string | number | null | undefined)[][]): string {
  const cell = (v: string | number | null | undefined) => {
    if (v === null || v === undefined) return "";
    let s = String(v);
    if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
    return /[",\n\r]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
  };
  return [header, ...rows].map((r) => r.map(cell).join(",")).join("\r\n") + "\r\n";
}

/** Split "4101 W Addison St, Chicago Il 60641" into parts; falls back to the whole string as street. */
export function splitMailing(mailing: string | null): { street: string; city: string; state: string; zip: string } {
  if (!mailing) return { street: "", city: "", state: "", zip: "" };
  const i = mailing.lastIndexOf(",");
  if (i < 0) return { street: mailing, city: "", state: "", zip: "" };
  const street = mailing.slice(0, i).trim();
  const m = mailing
    .slice(i + 1)
    .trim()
    .match(/^(.*?)\s+([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$/);
  if (!m) return { street: mailing, city: "", state: "", zip: "" };
  return { street, city: m[1], state: m[2].toUpperCase(), zip: m[3] };
}
