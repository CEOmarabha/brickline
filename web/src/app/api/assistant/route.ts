import type { ToolContext } from "@/lib/assistant-tools";
import { askAssistant, assistantConfigured, type ChatTurn, QUICK_QUESTIONS, type QuickKey, quickAnswer } from "@/lib/assistant";
import { sql } from "@/lib/db";
import { getOutcomes } from "@/lib/outcomes";
import { getSnapshot } from "@/lib/snapshot";
import { getStatuses, getWorkspace, viewerId } from "@/lib/workspace";

const MAX_TURNS = 20;
const MAX_CHARS = 4000;
const HOURLY_LIMIT = 60;

function json(body: unknown, status = 200) {
  return Response.json(body, { status, headers: { "cache-control": "private, no-store" } });
}

export async function POST(request: Request) {
  // Browsers send Origin on cross-site POSTs; reject any that don't match the host serving this app.
  const origin = request.headers.get("origin");
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (origin && host && new URL(origin).host !== host) return json({ error: "Bad origin" }, 403);
  const owner = await viewerId();
  if (!owner) return json({ error: "Sign in required" }, 401);

  let body: { messages?: unknown; quick?: unknown };
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const [snap, ws, statuses, outcomes] = await Promise.all([getSnapshot(), getWorkspace(), getStatuses(), getOutcomes()]);
  const ctx: ToolContext = { snap, ws, statuses, rates: outcomes.rates, outcomes };

  if (typeof body.quick === "string") {
    if (!(body.quick in QUICK_QUESTIONS)) return json({ error: "Unknown question" }, 400);
    return json({ reply: quickAnswer(body.quick as QuickKey, ctx), tools: [], mode: "quick" });
  }

  if (!assistantConfigured()) {
    return json({ error: "The AI assistant isn't connected yet. Quick questions still work." }, 503);
  }

  const raw = Array.isArray(body.messages) ? body.messages : [];
  const history: ChatTurn[] = raw
    .slice(-MAX_TURNS)
    .filter(
      (m): m is ChatTurn =>
        typeof m === "object" &&
        m !== null &&
        ((m as ChatTurn).role === "user" || (m as ChatTurn).role === "assistant") &&
        typeof (m as ChatTurn).content === "string",
    )
    .map((m) => ({ role: m.role, content: m.content.slice(0, MAX_CHARS) }));
  if (history.length === 0 || history[history.length - 1].role !== "user") {
    return json({ error: "Send a question" }, 400);
  }
  while (history.length > 0 && history[0].role !== "user") history.shift();

  const recent = await sql<{ n: number }>(
    "select count(*)::int as n from assistant_usage where owner_id = $1 and created_at > now() - interval '1 hour'",
    [owner],
  );
  if ((recent[0]?.n ?? 0) >= HOURLY_LIMIT) return json({ error: "Hourly assistant limit reached. Try again soon." }, 429);
  await sql("insert into assistant_usage (owner_id) values ($1)", [owner]);

  try {
    const { reply, tools } = await askAssistant(history, ctx);
    return json({ reply, tools, mode: "ai" });
  } catch {
    return json({ error: "The assistant couldn't answer right now. Try again in a moment." }, 502);
  }
}
