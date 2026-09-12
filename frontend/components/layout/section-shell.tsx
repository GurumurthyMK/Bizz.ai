import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/layout/page-header";

export interface PlannedItem {
  label: string;
  phase: string;
}

export interface SectionShellProps {
  icon: LucideIcon;
  title: string;
  description: string;
  emptyTitle: string;
  emptyDescription: string;
  planned: PlannedItem[];
  actions?: React.ReactNode;
}

/**
 * Honest placeholder for a not-yet-implemented section: states what will
 * live here and when, without fake metrics or lorem ipsum.
 */
function SectionShell({
  icon,
  title,
  description,
  emptyTitle,
  emptyDescription,
  planned,
  actions,
}: SectionShellProps) {
  return (
    <div className="flex flex-col gap-5">
      <PageHeader title={title} description={description} actions={actions} />
      <EmptyState icon={icon} title={emptyTitle} description={emptyDescription} />
      <section aria-label={`Planned for ${title}`} className="rounded-lg border">
        <h2 className="border-b px-4 py-2.5 text-section-title">Planned for this section</h2>
        <ul className="divide-y">
          {planned.map((item) => (
            <li key={item.label} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
              <span>{item.label}</span>
              <Badge variant="outline" className="shrink-0">
                {item.phase}
              </Badge>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export { SectionShell };
