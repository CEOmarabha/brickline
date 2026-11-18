import { Suspense } from "react";
import { cacheLife } from "next/cache";
import { DataFreshness } from "@/components/data-freshness";
import { MobileNav, SidebarNav } from "@/components/nav";
import { TargetSwitcher } from "@/components/target-switcher";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { getSnapshot } from "@/lib/snapshot";
import { targetOptions } from "@/lib/targets";
import { getWorkspace, listWorkspaces, viewerId, workspaceLabel } from "@/lib/workspace";

async function freshness() {
  "use cache";
  cacheLife("hours");
  const snap = await getSnapshot();
  return snap.meta.dataAsOf;
}

async function Freshness() {
  return <DataFreshness asOf={await freshness()} />;
}

/** Workspace switcher with the "looking for" picker right under it; signed-out viewers have neither. */
async function Workspaces() {
  const owner = await viewerId();
  if (!owner) return null;
  const [ws, list, snap] = await Promise.all([getWorkspace(), listWorkspaces(owner), getSnapshot()]);
  return (
    <div className="space-y-3">
      <WorkspaceSwitcher workspaces={list} currentId={ws.id} currentLabel={workspaceLabel(ws)} />
      <TargetSwitcher options={targetOptions(snap.trades)} current={ws.target} />
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside data-app-chrome className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col overflow-y-auto bg-sidebar text-sidebar-foreground lg:flex print:hidden">
        <Brand />
        <div className="px-4 pb-4">
          <Suspense fallback={<div className="h-28" />}>
            <Workspaces />
          </Suspense>
        </div>
        <SidebarNav />
        <div className="mt-auto border-t border-sidebar-border p-4">
          <Suspense fallback={<div className="h-10" />}>
            <Freshness />
          </Suspense>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header data-app-chrome className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur lg:hidden print:hidden">
          <MobileNav
            brand={<Brand compact />}
            footer={
              <Suspense fallback={null}>
                <Workspaces />
              </Suspense>
            }
          />
          <Brand compact dark />
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8 print:max-w-none print:p-0">{children}</main>
      </div>
    </div>
  );
}

function Brand({ compact = false, dark = false }: { compact?: boolean; dark?: boolean }) {
  return (
    <div className={compact ? "flex items-center gap-2" : "flex items-center gap-2.5 px-5 pt-6 pb-5"}>
      <span className="grid size-8 place-items-center rounded-md bg-sidebar-primary text-sm font-bold text-white">
        B
      </span>
      <div className="leading-tight">
        <div className={`font-semibold tracking-tight ${dark ? "text-foreground" : ""}`}>Brickline</div>
        {!compact && <div className="text-xs text-sidebar-foreground/60">Chicago lead intelligence</div>}
      </div>
    </div>
  );
}
