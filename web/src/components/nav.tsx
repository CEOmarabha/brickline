"use client";

import { BarChart3, Bot, Briefcase, Building2, FileText, Handshake, LayoutDashboard, ListChecks, Map, MenuIcon, PartyPopper, Settings, Target, Trophy } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const ITEMS: { href: string; label: string; icon: typeof Map; section?: string }[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: ListChecks },
  { href: "/events", label: "Events", icon: PartyPopper },
  { href: "/assistant", label: "Assistant", icon: Bot },
  { href: "/areas", label: "Neighborhoods", icon: Map },
  { href: "/market", label: "Market & competitors", icon: Trophy },
  { href: "/commercial", label: "Commercial", icon: Building2 },
  { href: "/results", label: "Results", icon: BarChart3 },
  { href: "/report", label: "Weekly report", icon: FileText },
  { href: "/deals", label: "Deals", icon: Briefcase, section: "Our sales" },
  { href: "/prospects", label: "Prospects", icon: Target },
  { href: "/pilots", label: "Pilot lists", icon: Handshake },
  { href: "/settings", label: "Settings", icon: Settings },
];

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 mb-1 border-t border-sidebar-border px-3 pt-3 text-[11px] font-medium tracking-wide text-sidebar-foreground/50 uppercase">
      {children}
    </div>
  );
}

function useActive() {
  const pathname = usePathname();
  return (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
}

export function SidebarNav() {
  return (
    <Suspense fallback={<SidebarLinks isActive={() => false} />}>
      <ActiveSidebarLinks />
    </Suspense>
  );
}

function ActiveSidebarLinks() {
  return <SidebarLinks isActive={useActive()} />;
}

function SidebarLinks({ isActive }: { isActive: (href: string) => boolean }) {
  return (
    <nav className="flex flex-col gap-0.5 px-3">
      {ITEMS.map(({ href, label, icon: Icon, section }) => (
        <Fragment key={href}>
          {section && <SectionLabel>{section}</SectionLabel>}
          <Link
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-foreground/75 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              isActive(href) && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        </Fragment>
      ))}
    </nav>
  );
}

export function MobileNav({ brand, footer }: { brand: React.ReactNode; footer?: React.ReactNode }) {
  return (
    <Suspense fallback={<MobileMenu brand={brand} footer={footer} isActive={() => false} />}>
      <ActiveMobileMenu brand={brand} footer={footer} />
    </Suspense>
  );
}

function ActiveMobileMenu({ brand, footer }: { brand: React.ReactNode; footer?: React.ReactNode }) {
  return <MobileMenu brand={brand} footer={footer} isActive={useActive()} />;
}

function MobileMenu({
  brand,
  footer,
  isActive,
}: {
  brand: React.ReactNode;
  footer?: React.ReactNode;
  isActive: (href: string) => boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={<Button variant="ghost" size="icon" aria-label="Open menu" />}>
        <MenuIcon />
      </SheetTrigger>
      <SheetContent side="left" className="w-72 bg-sidebar text-sidebar-foreground">
        <SheetHeader>
          <SheetTitle className="text-sidebar-foreground">{brand}</SheetTitle>
        </SheetHeader>
        <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-3">
          {ITEMS.map(({ href, label, icon: Icon, section }) => (
            <Fragment key={href}>
              {section && <SectionLabel>{section}</SectionLabel>}
              <Link
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-sidebar-foreground/75 hover:bg-sidebar-accent",
                  isActive(href) && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            </Fragment>
          ))}
        </nav>
        {footer && <div className="mt-auto shrink-0 border-t border-sidebar-border p-4">{footer}</div>}
      </SheetContent>
    </Sheet>
  );
}
