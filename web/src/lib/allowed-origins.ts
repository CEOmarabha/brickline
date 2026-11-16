/**
 * Public hosts the published app is served from. Cursor's host proxy forwards requests with an internal Host /
 * X-Forwarded-Host, so same-origin checks (Next.js server actions, the assistant route) must also accept these.
 * Exact hosts only: a wildcard on the shared apps domain would let other people's apps post to this one.
 */
export const PUBLIC_HOSTS: readonly string[] = ["brickline-83d7.apps.grok.bot"];

/** True when a browser Origin header belongs to the host serving the request or to one of PUBLIC_HOSTS. */
export function isAllowedOrigin(origin: string, requestHost: string | null): boolean {
  let host: string;
  try {
    host = new URL(origin).host;
  } catch {
    return false;
  }
  return host === requestHost || PUBLIC_HOSTS.includes(host);
}
