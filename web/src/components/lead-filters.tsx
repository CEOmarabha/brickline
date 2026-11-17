"use client";

import { Search, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { KIND_LABEL } from "@/lib/kinds";
import type { LeadFiltersInput } from "@/lib/lead-query";

const KIND = { all: "All signals", ...KIND_LABEL };
const TIER = { all: "Any priority", act_now: "Act now", this_week: "This week", monitor: "Monitor" };
const STATUS = {
  all: "Any status",
  open: "Not worked yet",
  contacted: "Contacted",
  meeting: "Meeting booked",
  won: "Won",
  lost: "Lost",
  not_relevant: "Not relevant",
};
const SORT = { priority: "Priority", value: "Expected value", newest: "Newest", probability: "Chance of work" };
const FILTER_LABEL = { kind: "Signal type", tier: "Priority", area: "Neighborhood", status: "Status", sort: "Sort by" };

export function LeadFilters({ values, areas }: { values: LeadFiltersInput; areas: { id: number; name: string }[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();
  const [q, setQ] = useState(values.q);
  const areaItems: Record<string, string> = { all: "All my areas" };
  for (const a of areas) areaItems[String(a.id)] = a.name;

  function update(patch: Partial<LeadFiltersInput>) {
    const next = { ...values, ...patch };
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) {
      if (v && v !== "all" && !(k === "sort" && v === "priority")) params.set(k, v);
    }
    startTransition(() => router.push(`${pathname}?${params.toString()}`));
  }

  const select = (key: keyof typeof FILTER_LABEL, items: Record<string, string>, width: string) => (
    <Select items={items} value={values[key] || "all"} onValueChange={(v) => update({ [key]: String(v) })}>
      <SelectTrigger className={width} aria-label={FILTER_LABEL[key]}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {Object.entries(items).map(([value, label]) => (
          <SelectItem key={value} value={value}>
            {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  const active = ["kind", "tier", "area", "status"].some((k) => values[k as keyof LeadFiltersInput] !== "all") || values.q;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2" data-pending={pending || undefined}>
      <form
        className="relative w-full sm:w-64"
        onSubmit={(e) => {
          e.preventDefault();
          update({ q });
        }}
      >
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search address, owner, buyer"
          className="pl-8"
          aria-label="Search leads"
        />
      </form>
      {select("kind", KIND, "w-44")}
      {select("tier", TIER, "w-36")}
      {select("area", areaItems, "w-44")}
      {select("status", STATUS, "w-40")}
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Sort</span>
        {select("sort", SORT, "w-40")}
      </div>
      {active && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            setQ("");
            update({ kind: "all", tier: "all", area: "all", status: "all", q: "" });
          }}
        >
          <X /> Clear
        </Button>
      )}
    </div>
  );
}
