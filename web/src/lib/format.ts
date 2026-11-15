const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const int = new Intl.NumberFormat("en-US");

export function money(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  return usd0.format(n);
}

export function count(n: number | null | undefined): string {
  return n === null || n === undefined ? "—" : int.format(n);
}

export function pct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function change(now: number, before: number): { label: string; direction: "up" | "down" | "flat" } {
  if (before === 0 && now === 0) return { label: "no change", direction: "flat" };
  if (before === 0) return { label: "new", direction: "up" };
  const c = (now - before) / before;
  if (Math.abs(c) < 0.05) return { label: "flat", direction: "flat" };
  return { label: `${c > 0 ? "+" : ""}${Math.round(c * 100)}%`, direction: c > 0 ? "up" : "down" };
}

export function dateLabel(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function ago(days: number): string {
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.round(days / 7)} weeks ago`;
  return `${Math.round(days / 30)} months ago`;
}

/** Plain-language strength of a lift; the signal lab's verdict cut-offs, as `lift_label` in engine/leads/snapshot.py. */
export function liftLabel(lift: number): string {
  if (lift < 1.25) return "no real signal";
  return lift < 1.8 ? "a weak signal" : lift < 3 ? "a useful lift" : "a strong lift";
}
