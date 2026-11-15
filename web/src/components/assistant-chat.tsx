"use client";

import { Bot, Loader2, SendHorizontal, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { RichText } from "@/components/rich-text";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface Turn {
  role: "user" | "assistant";
  content: string;
  error?: boolean;
}

export function AssistantChat({
  aiEnabled,
  quick,
  businessLabel,
}: {
  aiEnabled: boolean;
  quick: Record<string, string>;
  businessLabel: string;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy]);

  async function send(payload: { quick?: string; text?: string }) {
    const question = payload.quick ? quick[payload.quick] : (payload.text ?? "").trim();
    if (!question || busy) return;
    const next: Turn[] = [...turns, { role: "user", content: question }];
    setTurns(next);
    setInput("");
    setBusy(true);
    try {
      const history = next.filter((t) => !t.error).map(({ role, content }) => ({ role, content }));
      const res = await fetch("/api/assistant", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload.quick ? { quick: payload.quick } : { messages: history }),
      });
      const data = (await res.json()) as { reply?: string; error?: string };
      setTurns((t) => [
        ...t,
        data.reply
          ? { role: "assistant", content: data.reply }
          : { role: "assistant", content: data.error ?? "Something went wrong.", error: true },
      ]);
    } catch {
      setTurns((t) => [...t, { role: "assistant", content: "Network error. Try again.", error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[32rem] flex-col rounded-lg border bg-card">
      <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
        {turns.length === 0 && (
          <div className="mx-auto max-w-lg py-8 text-center">
            <Bot className="mx-auto size-8 text-primary" />
            <h2 className="mt-3 font-semibold">Ask about {businessLabel}&apos;s leads and market</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Answers come from this week&apos;s records and your own results.{" "}
              {aiEnabled
                ? "Ask anything, or start with a common question."
                : "Free-form chat turns on once an AI key is connected; these common questions work now."}
            </p>
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className={cn("flex gap-3", t.role === "user" && "flex-row-reverse")}>
            <span
              className={cn(
                "grid size-7 shrink-0 place-items-center rounded-full",
                t.role === "user" ? "bg-muted text-muted-foreground" : "bg-primary/10 text-primary",
              )}
            >
              {t.role === "user" ? <User className="size-4" /> : <Bot className="size-4" />}
            </span>
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-3.5 py-2 text-sm",
                t.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/60",
                t.error && "bg-destructive/10 text-destructive",
              )}
            >
              {t.role === "assistant" && !t.error ? <RichText text={t.content} /> : t.content}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Looking through the data…
          </div>
        )}
        <div ref={end} />
      </div>
      <div className="border-t p-3 sm:p-4">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {Object.entries(quick).map(([k, q]) => (
            <button
              key={k}
              type="button"
              disabled={busy}
              onClick={() => send({ quick: k })}
              className="rounded-full border px-3 py-1 text-xs transition-colors hover:bg-muted disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send({ text: input });
          }}
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send({ text: input });
              }
            }}
            rows={1}
            maxLength={4000}
            disabled={!aiEnabled || busy}
            placeholder={aiEnabled ? "e.g. Which repeat investors bought in Logan Square?" : "Connect an AI key to ask your own questions"}
            className="min-h-10 resize-none"
            aria-label="Ask the assistant"
          />
          <Button type="submit" size="icon" disabled={!aiEnabled || busy || !input.trim()} aria-label="Send">
            <SendHorizontal />
          </Button>
        </form>
      </div>
    </div>
  );
}
