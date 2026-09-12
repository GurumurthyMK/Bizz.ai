"use client";

import * as React from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ToastProvider, Toaster } from "@/components/ui/toast";
import { CommandPalette } from "@/components/layout/command-palette";
import { Header } from "@/components/layout/header";
import { NavSection, Sidebar } from "@/components/layout/sidebar";
import { primaryNav, secondaryNav } from "@/lib/navigation";

/**
 * Application shell: sidebar + header + main content container
 * (Design.md §5). Desktop shows the sidebar; smaller screens collapse
 * navigation into a drawer instead of shrinking the desktop layout (§29).
 */
function AppShell({ children }: { children: React.ReactNode }) {
  const [navOpen, setNavOpen] = React.useState(false);
  const [paletteOpen, setPaletteOpen] = React.useState(false);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <ToastProvider>
      <TooltipProvider delayDuration={200}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[70] focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:text-sm"
        >
          Skip to main content
        </a>
        <div className="flex h-screen overflow-hidden supports-[height:100dvh]:h-dvh">
          <Sidebar />
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
            <Header onOpenNav={() => setNavOpen(true)} onOpenPalette={() => setPaletteOpen(true)} />
            {/*
              relative: the scrollport must also be the containing block for
              absolutely-positioned descendants (e.g. sr-only labels, tables,
              status text deep in page content). Otherwise they escape this
              scroller AND the shell's overflow clip, inflating the document
              scroll area with blank page-level overflow.
            */}
            <main id="main-content" className="relative min-h-0 flex-1 overflow-y-auto" tabIndex={-1}>
              <div className="mx-auto w-full max-w-6xl px-3 py-5 sm:px-5">{children}</div>
            </main>
          </div>
        </div>

        {/* Mobile navigation drawer */}
        {navOpen && (
          <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
            <div
              className="absolute inset-0 bg-foreground/20"
              onClick={() => setNavOpen(false)}
              aria-hidden="true"
            />
            <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col gap-5 border-r bg-card px-3 py-4">
              <div className="flex items-center justify-between px-1">
                <Link
                  href="/overview"
                  onClick={() => setNavOpen(false)}
                  className="flex items-center gap-2"
                  aria-label="Bizz AI home"
                >
                  <span className="flex size-7 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
                    B
                  </span>
                  <span className="text-[15px] font-semibold tracking-tight">Bizz AI</span>
                </Link>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Close navigation"
                  onClick={() => setNavOpen(false)}
                >
                  <X aria-hidden="true" />
                </Button>
              </div>
              <div className="flex flex-col gap-5 overflow-y-auto" onClick={() => setNavOpen(false)}>
                <NavSection items={primaryNav} label="Workspace" />
                <NavSection items={secondaryNav} label="System" />
              </div>
            </div>
          </div>
        )}

        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
        <Toaster />
      </TooltipProvider>
    </ToastProvider>
  );
}

export { AppShell };
