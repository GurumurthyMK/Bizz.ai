"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Moon, Search, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { allNav } from "@/lib/navigation";

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Global command palette (⌘K). Navigates between sections and exposes
 * shell actions. An enhancement — never the primary navigation (Design.md §24).
 */
function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const { setTheme } = useTheme();

  const run = React.useCallback(
    (action: () => void) => {
      onOpenChange(false);
      action();
    },
    [onOpenChange]
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-label="Command palette"
        className="top-[20%] max-w-lg translate-y-0 gap-0 overflow-hidden p-0"
      >
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <Command label="Global commands" className="[&_[cmdk-input]]:border-0">
          <div className="flex items-center gap-2 border-b px-3">
            <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <Command.Input
              autoFocus
              placeholder="Search sections or run an action…"
              className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          <Command.List className="max-h-72 overflow-y-auto p-1.5">
            <Command.Empty className="px-2 py-6 text-center text-sm text-muted-foreground">
              No matching commands.
            </Command.Empty>
            <Command.Group
              heading="Sections"
              className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-meta [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground"
            >
              {allNav.map((item) => {
                const Icon = item.icon;
                return (
                  <Command.Item
                    key={item.href}
                    value={`${item.label} ${item.description}`}
                    onSelect={() => run(() => router.push(item.href))}
                    className="flex cursor-pointer items-center gap-2.5 rounded-sm px-2 py-2 text-sm data-[selected=true]:bg-muted [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted-foreground"
                  >
                    <Icon aria-hidden="true" />
                    <span>{item.label}</span>
                    <span className="ml-auto hidden truncate pl-4 text-dense text-muted-foreground sm:inline">
                      {item.description}
                    </span>
                  </Command.Item>
                );
              })}
            </Command.Group>
            <Command.Group
              heading="Appearance"
              className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-meta [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground"
            >
              <Command.Item
                value="Switch to light theme"
                onSelect={() => run(() => setTheme("light"))}
                className="flex cursor-pointer items-center gap-2.5 rounded-sm px-2 py-2 text-sm data-[selected=true]:bg-muted [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted-foreground"
              >
                <Sun aria-hidden="true" />
                Switch to light theme
              </Command.Item>
              <Command.Item
                value="Switch to dark theme"
                onSelect={() => run(() => setTheme("dark"))}
                className="flex cursor-pointer items-center gap-2.5 rounded-sm px-2 py-2 text-sm data-[selected=true]:bg-muted [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted-foreground"
              >
                <Moon aria-hidden="true" />
                Switch to dark theme
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}

export { CommandPalette };
