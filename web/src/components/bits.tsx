import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { change } from "@/lib/format";
import { PROSPECT_STATUS_LABEL, type ProspectStatus } from "@/lib/pipeline";
import type { Tier } from "@/lib/snapshot";
import type { LeadStatus } from "@/lib/workspace";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardContent>
        <div className="text-xs font-medium text-muted-foreground">{label}</div>
        <div className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
        {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
      </CardContent>
    </Card>
  );
}

const TIER_STYLE: Record<Tier, { label: string; className: string }> = {
  act_now: { label: "Act now", className: "bg-primary/10 text-primary border-primary/20" },
  this_week: { label: "This week", className: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  monitor: { label: "Monitor", className: "bg-muted text-muted-foreground" },
};

export function TierBadge({ tier }: { tier: Tier }) {
  const t = TIER_STYLE[tier];
  return (
    <Badge variant="outline" className={t.className}>
      {t.label}
    </Badge>
  );
}

const STATUS_STYLE: Record<LeadStatus, string> = {
  new: "bg-muted text-muted-foreground",
  contacted: "bg-sky-500/10 text-sky-700 border-sky-500/20",
  meeting: "bg-violet-500/10 text-violet-700 border-violet-500/20",
  won: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  lost: "bg-zinc-500/10 text-zinc-600",
  not_relevant: "bg-zinc-500/10 text-zinc-500",
};

export function StatusBadge({ status, label }: { status: LeadStatus; label: string }) {
  return (
    <Badge variant="outline" className={STATUS_STYLE[status]}>
      {label}
    </Badge>
  );
}

const PROSPECT_STATUS_STYLE: Record<ProspectStatus, string> = {
  not_contacted: "bg-muted text-muted-foreground",
  emailed: "bg-sky-500/10 text-sky-700 border-sky-500/20",
  replied: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  meeting: "bg-violet-500/10 text-violet-700 border-violet-500/20",
  pilot: "bg-primary/10 text-primary border-primary/20",
  paying: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  not_interested: "bg-zinc-500/10 text-zinc-500",
};

export function ProspectStatusBadge({ status }: { status: ProspectStatus }) {
  return (
    <Badge variant="outline" className={PROSPECT_STATUS_STYLE[status]}>
      {PROSPECT_STATUS_LABEL[status]}
    </Badge>
  );
}

export function Trend({ now, before, invert = false }: { now: number; before: number; invert?: boolean }) {
  const c = change(now, before);
  const good = c.direction === "flat" ? null : (c.direction === "up") !== invert;
  const Icon = c.direction === "up" ? ArrowUpRight : c.direction === "down" ? ArrowDownRight : Minus;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs tabular-nums",
        good === null ? "text-muted-foreground" : good ? "text-emerald-700" : "text-zinc-500",
      )}
      title={`${now} vs ${before} a year earlier`}
    >
      <Icon className="size-3" />
      {c.label}
    </span>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed p-10 text-center">
      <div className="font-medium">{title}</div>
      {children && <div className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{children}</div>}
    </div>
  );
}

/** Previous/next links for a paged list; renders nothing for a single page. `href` builds the URL of page n. */
export function Pagination({
  page,
  pages,
  href,
  className,
}: {
  page: number;
  pages: number;
  href: (page: number) => string;
  className?: string;
}) {
  if (pages <= 1) return null;
  return (
    <nav className={cn("flex items-center justify-between text-sm", className)} aria-label="Pagination">
      <span className="text-muted-foreground">
        Page {page} of {pages}
      </span>
      <div className="flex gap-2">
        {page > 1 && (
          <Link href={href(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
            Previous
          </Link>
        )}
        {page < pages && (
          <Link href={href(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
            Next
          </Link>
        )}
      </div>
    </nav>
  );
}

export function ProbabilityBar({ value, max = 0.4 }: { value: number; max?: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
    </div>
  );
}
