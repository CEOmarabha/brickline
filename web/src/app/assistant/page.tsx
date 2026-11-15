import type { Metadata } from "next";
import { Suspense } from "react";
import { AssistantChat } from "@/components/assistant-chat";
import { PageHeader } from "@/components/bits";
import { Skeleton } from "@/components/ui/skeleton";
import { assistantConfigured, QUICK_QUESTIONS } from "@/lib/assistant";
import { getWorkspace, workspaceLabel } from "@/lib/workspace";

export const metadata: Metadata = { title: "Assistant" };

export default function AssistantPage() {
  return (
    <>
      <PageHeader
        title="Assistant"
        description="Ask about your leads, neighborhoods, competitors and results. It looks answers up in the data instead of guessing, and it never sends anything on your behalf."
      />
      <Suspense fallback={<Skeleton className="h-[32rem] w-full" />}>
        <Assistant />
      </Suspense>
    </>
  );
}

async function Assistant() {
  const ws = await getWorkspace();
  return (
    <AssistantChat
      aiEnabled={assistantConfigured() && ws.signedIn}
      quick={{ ...QUICK_QUESTIONS }}
      businessLabel={workspaceLabel(ws)}
    />
  );
}
