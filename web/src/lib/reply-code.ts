/**
 * Reply codes: a short code printed on every letter and email draft so an owner who calls, writes or emails can be
 * matched to the lead, per workspace. Derived (not stored), so the same lead in the same workspace always prints the
 * same code. Letters that look alike (0/O, 1/I/L, 5/S, U/V) are left out so codes survive being read over the phone.
 */

const ALPHABET = "ABCDEFGHJKMNPQRTWXYZ2346789";
const LENGTH = 8;

/** 32-bit FNV-1a over the UTF-16 code units, unsigned. */
function fnv1a32(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Four characters from each of two independently salted hashes (27^4 < 2^32, so each half is near uniform). */
export function replyCode(workspaceId: string, leadId: string): string {
  const key = `${workspaceId}\u0000${leadId}`;
  const half = (salt: string) => {
    let h = fnv1a32(salt + key);
    let out = "";
    for (let i = 0; i < LENGTH / 2; i++) {
      out += ALPHABET[h % ALPHABET.length];
      h = Math.floor(h / ALPHABET.length);
    }
    return out;
  };
  return `${half("a")}-${half("b")}`;
}

/** Upper-cases, drops spaces and dashes, and re-inserts the dash; null when it cannot be a reply code. */
export function normalizeReplyCode(raw: string): string | null {
  const s = raw.toUpperCase().replace(/[\s-]/g, "");
  if (s.length !== LENGTH || [...s].some((c) => !ALPHABET.includes(c))) return null;
  return `${s.slice(0, 4)}-${s.slice(4)}`;
}
