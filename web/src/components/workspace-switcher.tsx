"use client";

import { Plus } from "lucide-react";
import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createWorkspace, switchWorkspace } from "@/lib/actions";

export function WorkspaceSwitcher({
  workspaces,
  currentId,
  currentLabel,
}: {
  workspaces: { id: string; label: string }[];
  currentId: string;
  currentLabel: string;
}) {
  const [pending, startTransition] = useTransition();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const list = workspaces.some((w) => w.id === currentId)
    ? workspaces
    : [{ id: currentId, label: currentLabel }, ...workspaces];
  const items = Object.fromEntries(list.map((w) => [w.id, w.label]));

  return (
    <div className="space-y-1.5">
      <div className="px-1 text-xs text-sidebar-foreground/60">Workspace</div>
      <div className="flex gap-1.5">
        <Select
          items={items}
          value={currentId}
          disabled={pending}
          onValueChange={(v) =>
            startTransition(async () => {
              try {
                const result = await switchWorkspace(String(v));
                if (!result.ok) toast.error(result.error);
              } catch {
                toast.error("Couldn't switch workspace");
              }
            })
          }
        >
          <SelectTrigger
            aria-label="Workspace"
            className="w-full min-w-0 border-sidebar-border bg-sidebar-accent text-sidebar-foreground"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent alignItemWithTrigger={false}>
            {list.map((w) => (
              <SelectItem key={w.id} value={w.id}>
                {w.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                aria-label="New client workspace"
                className="shrink-0 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              />
            }
          >
            <Plus />
          </DialogTrigger>
          <DialogContent>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                startTransition(async () => {
                  try {
                    const result = await createWorkspace(name);
                    if (!result.ok) {
                      toast.error(result.error);
                      return;
                    }
                    toast.success(`Created ${name.trim()}. Set its trade and neighborhoods in Settings.`);
                    setName("");
                    setOpen(false);
                  } catch {
                    toast.error("Couldn't create the workspace");
                  }
                });
              }}
              className="space-y-4"
            >
              <DialogHeader>
                <DialogTitle>New client workspace</DialogTitle>
                <DialogDescription>
                  One workspace per contractor you manage: its own trade, neighborhoods, letterhead and lead statuses.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-1.5">
                <Label htmlFor="ws-name">Client company name</Label>
                <Input
                  id="ws-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Northside Porch Co."
                  maxLength={120}
                  autoFocus
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={pending || !name.trim()}>
                  Create workspace
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
