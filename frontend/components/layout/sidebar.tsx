"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { primaryNav, secondaryNav, type NavItem } from "@/lib/navigation";
import { cn } from "@/lib/utils";

function NavSection({ items, label }: { items: NavItem[]; label: string }) {
  const pathname = usePathname();
  return (
    <nav aria-label={label} className="flex flex-col gap-0.5">
      <p className="px-2 pb-1 text-meta font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
              active
                ? "bg-muted font-medium text-foreground"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

/** Quiet desktop sidebar; navigation never competes with content (Design.md §5). */
function Sidebar() {
  return (
    <aside className="hidden min-h-0 w-60 shrink-0 flex-col gap-6 overflow-y-auto border-r bg-card px-3 py-4 lg:flex">
      <Link href="/overview" className="flex items-center gap-2 px-2" aria-label="Bizz AI home">
        <span className="flex size-7 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
          B
        </span>
        <span className="text-[15px] font-semibold tracking-tight">Bizz AI</span>
      </Link>
      <div className="flex min-h-0 flex-col gap-6">
        <NavSection items={primaryNav} label="Workspace" />
        <NavSection items={secondaryNav} label="System" />
      </div>
    </aside>
  );
}

export { Sidebar, NavSection };
