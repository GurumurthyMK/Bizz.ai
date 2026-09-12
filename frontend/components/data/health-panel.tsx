"use client";

import { Badge } from "@/components/ui/badge";
import { formatNumber } from "@/lib/format";
import type { DataHealth } from "@/types";

function prettyLabel(key: string): string {
  return key.replace(/_/g, " ");
}

function formatDateTime(value: string | null): string {
  if (value === null) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

/** Data health: freshness, missing values, integrity, last import. */
export function HealthPanel({ health }: { health: DataHealth }) {
  const integrityIssues =
    health.integrity.orphan_transactions +
    health.integrity.orphan_interactions +
    health.integrity.over_discounted_transactions;
  return (
    <section aria-labelledby="data-health" className="flex flex-col gap-3">
      <h2 id="data-health" className="text-section-title">
        Data health
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
          <h3 className="text-sm font-medium">Freshness</h3>
          <dl className="flex flex-col gap-1 text-sm text-muted-foreground">
            <div className="flex justify-between gap-2">
              <dt>First transaction</dt>
              <dd className="tabular-nums">{formatDateTime(health.freshness.transaction_date_min)}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Last transaction</dt>
              <dd className="tabular-nums">{formatDateTime(health.freshness.transaction_date_max)}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Last interaction</dt>
              <dd className="tabular-nums">{formatDateTime(health.freshness.last_interaction_at)}</dd>
            </div>
          </dl>
        </div>
        <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
          <h3 className="text-sm font-medium">Missing values</h3>
          <dl className="flex flex-col gap-1 text-sm text-muted-foreground">
            {Object.entries(health.missing_values).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-2">
                <dt className="capitalize">{prettyLabel(key)}</dt>
                <dd className="tabular-nums">{formatNumber(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-medium">Relationship integrity</h3>
            <Badge variant={integrityIssues === 0 ? "success" : "danger"}>
              {integrityIssues === 0 ? "Healthy" : `${formatNumber(integrityIssues)} issues`}
            </Badge>
          </div>
          <dl className="flex flex-col gap-1 text-sm text-muted-foreground">
            <div className="flex justify-between gap-2">
              <dt>Orphan transactions</dt>
              <dd className="tabular-nums">{formatNumber(health.integrity.orphan_transactions)}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Orphan interactions</dt>
              <dd className="tabular-nums">{formatNumber(health.integrity.orphan_interactions)}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Over-discounted</dt>
              <dd className="tabular-nums">{formatNumber(health.integrity.over_discounted_transactions)}</dd>
            </div>
          </dl>
        </div>
        <div className="flex flex-col gap-1 rounded-lg border bg-card p-4">
          <h3 className="text-sm font-medium">Last import</h3>
          {health.last_import === null ? (
            <p className="text-sm text-muted-foreground">No imports recorded yet.</p>
          ) : (
            <dl className="flex flex-col gap-1 text-sm text-muted-foreground">
              <div className="flex justify-between gap-2">
                <dt>File</dt>
                <dd className="max-w-40 truncate" title={health.last_import.filename}>
                  {health.last_import.filename}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Entity</dt>
                <dd>{health.last_import.entity}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Result</dt>
                <dd>
                  <Badge variant={health.last_import.status === "completed" ? "success" : "danger"}>
                    {health.last_import.status}
                  </Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Rows</dt>
                <dd className="tabular-nums">
                  {formatNumber(health.last_import.rows_inserted)} / {formatNumber(health.last_import.rows_total)}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>When</dt>
                <dd>{formatDateTime(health.last_import.created_at)}</dd>
              </div>
            </dl>
          )}
        </div>
      </div>
    </section>
  );
}
