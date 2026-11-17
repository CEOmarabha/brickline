import { UserError } from "@/lib/action-result";

/** Largest job value a person can enter on a Won lead. */
export const MAX_JOB_VALUE = 10_000_000;

/** A validated dollar amount typed in by a person: whole cents, never rounded on the way in. */
export interface MoneyAmount {
  cents: number;
  /** Exact decimal text for SQL, like "12500.00". */
  text: string;
}

const PLAIN = /^(?:\d+(?:\.\d{1,2})?|\.\d{1,2})$/;
const GROUPED = /^\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?$/;

export function centsToText(cents: number): string {
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
}

/** Text for an input box: "12500" or "12500.50". */
export function centsToInput(cents: number | null): string {
  if (cents === null) return "";
  return cents % 100 === 0 ? String(cents / 100) : centsToText(cents);
}

/** Dollars read back from the database (a float8) to whole cents. */
export function dollarsToCents(dollars: number | null | undefined): number | null {
  return dollars === null || dollars === undefined ? null : Math.round(dollars * 100);
}

/**
 * Validates an optional dollar amount: finite, 0 <= value <= max, at most two decimals. Blank or null means "no value".
 * Accepts "$12,500.50", "12500", 12500.5. Anything else (negative, exponent notation, text, three decimals) is
 * rejected with a message rather than rounded, so what is stored is exactly what the person typed.
 */
export function parseMoney(value: unknown, { label, max }: { label: string; max: number }): MoneyAmount | null {
  if (value === null || value === undefined) return null;
  const tooBig = () => new UserError(`${label} can't be more than $${max.toLocaleString("en-US")}`);
  const malformed = () => new UserError(`${label} must be a dollar amount, like 12500 or 12,500.50`);

  let cents: number;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw malformed();
    if (value < 0) throw new UserError(`${label} can't be negative`);
    if (value > max) throw tooBig();
    cents = Math.round(value * 100);
    if (Math.abs(value * 100 - cents) > 1e-6) throw new UserError(`${label} can have at most two decimals`);
  } else if (typeof value === "string") {
    const s = value.trim().replace(/^\$\s*/, "");
    if (s === "") return null;
    if (s.startsWith("-")) throw new UserError(`${label} can't be negative`);
    if (!PLAIN.test(s) && !GROUPED.test(s)) {
      if (/^[\d,]*\.\d{3,}$/.test(s)) throw new UserError(`${label} can have at most two decimals`);
      throw malformed();
    }
    const [whole = "", fraction = ""] = s.split(".");
    const digits = whole.replaceAll(",", "") || "0";
    if (digits.length > 9) throw tooBig();
    cents = Number(digits) * 100 + Number(fraction.padEnd(2, "0"));
  } else {
    throw malformed();
  }
  if (cents > max * 100) throw tooBig();
  return { cents, text: centsToText(cents) };
}
