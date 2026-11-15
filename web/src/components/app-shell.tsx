import { Suspense } from "react";
import { cacheLife } from "next/cache";
import { DataFreshness } from "@/components/data-freshness";
import { MobileNav, SidebarNav } from "@/components/nav";
import { getSnapshot } from "@/lib/snapshot";

async function freshness() {
  "use cache";
  cacheLife("hours");
  const snap = await getSnapshot();
  return snap.meta.dataAsOf;
}

async function Freshness() {
  return <DataFreshness asOf={await freshness()} />;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-sidebar text-sidebar-foreground lg:flex">
        <Brand />
        <SidebarNav />
        <div className="mt-auto border-t border-sidebar-border p-4">
          <Suspense fallback={<div className="h-10" />}>
            <Freshness />
          </Suspense>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur lg:hidden">
          <MobileNav brand={<Brand compact />} />
          <Brand compact dark />
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
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
