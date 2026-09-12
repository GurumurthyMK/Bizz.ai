"use client";

import Link from "next/link";
import { Bell, LogOut, Menu, Search } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export interface HeaderProps {
  onOpenNav: () => void;
  onOpenPalette: () => void;
}

/**
 * Quiet top header: mobile nav trigger, command palette trigger,
 * theme toggle, alerts shortcut, and the signed-in user menu.
 */
function Header({ onOpenNav, onOpenPalette }: HeaderProps) {
  const { user, logout } = useAuth();
  const initial = user != null ? user.email.charAt(0).toUpperCase() : "?";
  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b bg-card px-3 sm:px-4">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="lg:hidden"
        aria-label="Open navigation"
        onClick={onOpenNav}
      >
        <Menu aria-hidden="true" />
      </Button>

      <button
        type="button"
        onClick={onOpenPalette}
        aria-label="Open command palette (Control or Command K)"
        className="flex h-9 w-full max-w-sm items-center gap-2 rounded-md border border-input bg-background px-3 text-sm text-muted-foreground hover:bg-muted/60"
      >
        <Search className="size-4 shrink-0" aria-hidden="true" />
        <span className="truncate">Search or jump to…</span>
        <kbd className="ml-auto hidden rounded border bg-muted px-1.5 text-meta sm:inline" aria-hidden="true">
          ⌘K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <Tooltip>
          <TooltipTrigger asChild>
            <Button type="button" variant="ghost" size="icon" asChild>
              <Link href="/alerts" aria-label="Alerts">
                <Bell aria-hidden="true" />
              </Link>
            </Button>
          </TooltipTrigger>
          <TooltipContent>Alerts</TooltipContent>
        </Tooltip>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={user != null ? `Account: ${user.email}` : "Account"}
            >
              <span
                aria-hidden="true"
                className="flex size-6 items-center justify-center rounded-full bg-muted text-meta font-medium text-muted-foreground"
              >
                {initial}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{user != null ? user.email : "Not signed in"}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void logout()}>
              <LogOut aria-hidden="true" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

export { Header };
