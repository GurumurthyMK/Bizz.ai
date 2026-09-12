"use client";

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface SortHeaderProps {
  label: string;
  active: boolean;
  direction: "asc" | "desc";
  onToggle: () => void;
}

/** Sortable column header with aria-sort and visible direction. */
export function SortHeader({ label, active, direction, onToggle }: SortHeaderProps) {
  const Icon = active ? (direction === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <TableHead aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        onClick={onToggle}
        aria-label={`Sort by ${label}${active ? ` (${direction})` : ""}`}
        className={cn(
          "inline-flex items-center gap-1 rounded-sm hover:text-foreground",
          active && "text-foreground",
        )}
      >
        {label}
        <Icon aria-hidden="true" />
      </button>
    </TableHead>
  );
}
