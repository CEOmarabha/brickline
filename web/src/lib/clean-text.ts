import { UserError } from "@/lib/action-result";

const CONTROL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;

/** Control characters removed, whitespace collapsed; throws a UserError past `max` characters. */
export function singleLine(value: unknown, max: number, label: string): string {
  const s = String(value ?? "")
    .replace(CONTROL, "")
    .replace(/\s+/g, " ")
    .trim();
  if (s.length > max) throw new UserError(`${label} is too long (max ${max} characters)`);
  return s;
}

/** Like `singleLine` but keeps line breaks (notes). */
export function multiLine(value: unknown, max: number, label: string): string {
  const s = String(value ?? "")
    .replace(CONTROL, "")
    .replace(/\r\n?/g, "\n")
    .trim();
  if (s.length > max) throw new UserError(`${label} is too long (max ${max} characters)`);
  return s;
}
