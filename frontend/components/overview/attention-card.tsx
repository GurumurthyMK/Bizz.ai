import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import type { AttentionItem } from "@/types";

const severityVariant = { high: "danger", medium: "warning", low: "info" } as const;

/** What-needs-attention item: problem, impact, evidence, priority, action. */
export function AttentionCard({ item }: { item: AttentionItem }) {
  return (
    <Card aria-label={item.title}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Badge variant={severityVariant[item.severity]}>{item.severity}</Badge>
          <CardTitle>{item.title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{item.description}</p>
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-dense">
          <div className="flex gap-1.5">
            <dt className="text-muted-foreground">Affected customers</dt>
            <dd className="font-medium tabular-nums">{formatNumber(item.affected_customers)}</dd>
          </div>
          {item.metric_value !== null && item.metric_label !== null && (
            <div className="flex gap-1.5">
              <dt className="text-muted-foreground">{item.metric_label}</dt>
              <dd className="font-medium tabular-nums">{formatNumber(item.metric_value)}</dd>
            </div>
          )}
        </dl>
        {item.links.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {item.links.map((link) => (
              <Button key={link.href + link.label} variant="secondary" size="sm" asChild>
                <Link href={link.href}>
                  {link.label}
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
