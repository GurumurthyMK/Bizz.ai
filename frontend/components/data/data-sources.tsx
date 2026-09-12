"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import type { DataEntity, DataHealth } from "@/types";

export const ENTITY_META: {
  entity: DataEntity;
  title: string;
  description: string;
  requiredColumns: string[];
}[] = [
  {
    entity: "customers",
    title: "Customers",
    description: "Identity and profile records. Referenced by transactions and interactions.",
    requiredColumns: ["first_name", "last_name", "email"],
  },
  {
    entity: "products",
    title: "Products",
    description: "Catalog items with pricing. SKUs must be unique.",
    requiredColumns: ["sku", "name", "category", "unit_price"],
  },
  {
    entity: "transactions",
    title: "Transactions",
    description: "Purchases linked by customer email and product SKU.",
    requiredColumns: ["customer_email", "product_sku", "quantity", "unit_price", "transaction_date"],
  },
  {
    entity: "campaigns",
    title: "Campaigns",
    description: "Marketing activity that interactions can reference by name.",
    requiredColumns: ["name", "channel", "campaign_type"],
  },
  {
    entity: "interactions",
    title: "Interactions",
    description: "Engagement events linked by customer email and optional campaign name.",
    requiredColumns: ["customer_email", "interaction_type", "channel", "occurred_at"],
  },
];

/** Data Sources view: supported categories with live record counts. */
export function DataSources({
  health,
  onImport,
}: {
  health: DataHealth | null;
  onImport: (entity: DataEntity) => void;
}) {
  return (
    <section aria-labelledby="data-sources" className="flex flex-col gap-3">
      <h2 id="data-sources" className="text-section-title">
        Data sources
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {ENTITY_META.map((meta) => (
          <Card key={meta.entity}>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>{meta.title}</CardTitle>
                <Badge variant="secondary" aria-label={`${formatNumber(health?.counts[meta.entity] ?? 0)} records`}>
                  {health === null ? "…" : formatNumber(health.counts[meta.entity] ?? 0)}
                </Badge>
              </div>
              <CardDescription>{meta.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onImport(meta.entity)}
              >
                Import CSV
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
