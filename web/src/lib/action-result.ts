/**
 * Server actions report expected problems (bad input, signed out) as a value, because Next.js replaces the message of
 * an error thrown from an action with a generic one in production builds. Anything else still throws.
 */
export type ActionResult = { ok: true } | { ok: false; error: string };

/** An error whose message is safe and useful to show to the person who triggered the action. */
export class UserError extends Error {}

export async function runAction(fn: () => Promise<void>): Promise<ActionResult> {
  try {
    await fn();
    return { ok: true };
  } catch (error) {
    if (error instanceof UserError) return { ok: false, error: error.message };
    throw error;
  }
}
