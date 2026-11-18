/**
 * Reply codes: a short code printed on every letter and email draft so an owner who calls, writes or emails can be
 * matched to the lead, per workspace. Derived (not stored), so the same lead in the same workspace always prints the
 * same code. Letters that look alike (0/O, 1/I/L, 5/S, U/V) are left out so codes survive being read over the phone,
 * and the last character is a check character, so one misread character or two swapped neighbours are caught when
 * the code is typed in instead of being recorded against no lead.
 */

const ALPHABET = "ABCDEFGHJKMNPQRTWXYZ2346789";
const DATA_LENGTH = 7;
// Coprime with 27 and with each neighbour's difference, so any single substitution or adjacent swap changes the sum.
const WEIGHTS = [1, 2, 4, 5, 7, 8, 10];

/** 32-bit FNV-1a over the UTF-16 code units, unsigned. */
function fnv1a32(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function checkChar(data: string): string {
  let sum = 0;
  for (let i = 0; i < DATA_LENGTH; i++) sum += WEIGHTS[i] * ALPHABET.indexOf(data[i]);
  return ALPHABET[sum % ALPHABET.length];
}

/** Four characters from one salted hash and three from another (27^4 < 2^32, so each part is near uniform). */
export function replyCode(workspaceId: string, leadId: string): string {
  const key = `${workspaceId}\u0000${leadId}`;
  const part = (salt: string, n: number) => {
    let h = fnv1a32(salt + key);
    let out = "";
    for (let i = 0; i < n; i++) {
      out += ALPHABET[h % ALPHABET.length];
      h = Math.floor(h / ALPHABET.length);
    }
    return out;
  };
  const data = part("a", 4) + part("b", 3);
  const code = data + checkChar(data);
  return `${code.slice(0, 4)}-${code.slice(4)}`;
}

/** Upper-cases, drops spaces and dashes, and re-inserts the dash; null when it cannot be a reply code. */
export function normalizeReplyCode(raw: string): string | null {
  const s = raw.toUpperCase().replace(/[\s-]/g, "");
  if (s.length !== DATA_LENGTH + 1 || [...s].some((c) => !ALPHABET.includes(c))) return null;
  if (checkChar(s.slice(0, DATA_LENGTH)) !== s[DATA_LENGTH]) return null;
  return `${s.slice(0, 4)}-${s.slice(4)}`;
}
