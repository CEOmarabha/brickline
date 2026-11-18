"use client";

import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";
import { groupedOptions, type TargetKey, type TargetOption } from "@/lib/targets";
import { cn } from "@/lib/utils";

/** The grouped "what are you looking for" select, shared by the sidebar picker and Settings. */
export function TargetSelect({
  options,
  value,
  onValueChange,
  id,
  ariaLabel,
  disabled,
  className,
  contentClassName,
}: {
  options: TargetOption[];
  value: TargetKey;
  onValueChange: (value: TargetKey) => void;
  id?: string;
  ariaLabel?: string;
  disabled?: boolean;
  className?: string;
  contentClassName?: string;
}) {
  const items = Object.fromEntries(options.map((o) => [o.key, o.label]));
  return (
    <Select items={items} value={value} disabled={disabled} onValueChange={(v) => onValueChange(String(v) as TargetKey)}>
      <SelectTrigger id={id} aria-label={ariaLabel} title={items[value]} className={cn("w-full min-w-0", className)}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false} className={contentClassName}>
        {groupedOptions(options).map(({ group, options: inGroup }) => (
          <SelectGroup key={group.key}>
            <SelectLabel>{group.label}</SelectLabel>
            {inGroup.map((o) => (
              <SelectItem key={o.key} value={o.key}>
                <span className="whitespace-normal">{o.label}</span>
              </SelectItem>
            ))}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
}
