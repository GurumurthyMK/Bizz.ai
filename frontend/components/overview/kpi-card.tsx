import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatChange } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { OverviewKpi } from "@/types";

interface KpiCardProps {
  kpi: OverviewKpi;
  formatValue: (value: number) => string;
  context?: string;
}

/**
 * Business-health metric: current value, change vs previous 30 days, and
 * comparison context. All four dashboard KPIs are higher-is-better, so
 * up = positive, down = negative.
 */
export function KpiCard({ kpi, formatValue, context = "vs previous 30 days" }: KpiCardProps) {
  const ChangeIcon = kpi.direction === "up" ? TrendingUp : kpi.direction === "down" ? TrendingDown : Minus;
  return (
    <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
      <p className="text-sm text-muted-foreground">{kpi.label}</p>
      <p className="text-page-title tabular-nums">{formatValue(kpi.value)}</p>
      <p className="flex items-center gap-2 text-dense">
        <Badge
          variant={kpi.direction === "up" ? "success" : kpi.direction === "down" ? "danger" : "default"}
        >
          <ChangeIcon aria-hidden="true" />
          {formatChange(kpi.change_pct)}
        </Badge>
        <span className={cn("text-muted-foreground")}>{context}</span>
      </p>
    </div>
  );
}
