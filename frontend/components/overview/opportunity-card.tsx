import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatScore } from "@/lib/format";
import type { OpportunityItem } from "@/types";

const tierVariant = { high: "success", medium: "warning", low: "default" } as const;

/** Opportunity: score, evidence, and a path to the underlying customers. */
export function OpportunityCard({ item }: { item: OpportunityItem }) {
  return (
    <Card aria-label={`Opportunity for customer ${item.customer_id}`}>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-[15px]">Customer {item.customer_id}</CardTitle>
          <span className="flex items-center gap-2">
            <Badge variant={tierVariant[item.tier as keyof typeof tierVariant] ?? "default"}>
              {item.tier}
            </Badge>
            <span className="text-sm font-semibold tabular-nums" aria-label={`Score ${formatScore(item.score)} of 100`}>
              {formatScore(item.score)}
            </span>
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
          {item.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
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
