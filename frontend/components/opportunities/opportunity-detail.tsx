"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { InsightCard } from "@/components/ai/insight-card";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/hooks/use-resource";
import { getOpportunity } from "@/lib/api";
import { formatCurrency, formatDate, formatPercent } from "@/lib/format";

function tierVariant(tier: string): "success" | "warning" | "default" {
  return tier === "high" ? "success" : tier === "medium" ? "warning" : "default";
}

/** Opportunity detail: type, value, customer, segment, score, evidence, action. */
export function OpportunityDetail({ opportunityId }: { opportunityId: number }) {
  const load = React.useCallback(
    (signal: AbortSignal) => getOpportunity(opportunityId, signal),
    [opportunityId],
  );
  const { data, loading, error, retry } = useResource(
    "opportunity",
    load,
    `opportunity-${opportunityId}`,
  );

  if (loading) {
    return (
      <div className="flex flex-col gap-4" role="status" aria-label="Loading opportunity">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" asChild className="self-start">
          <Link href="/opportunities">
            <ArrowLeft aria-hidden="true" />
            Opportunities
          </Link>
        </Button>
        <ErrorState
          title="Unable to load opportunity"
          description={error ?? "Unknown error."}
          onRetry={retry}
        />
      </div>
    );
  }

  const signalEntries =
    data.signals !== null
      ? Object.entries(data.signals).sort(([, a], [, b]) => b - a)
      : [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link href="/opportunities">
            <ArrowLeft aria-hidden="true" />
            Opportunities
          </Link>
        </Button>
        <PageHeader
          title={`${data.opportunity_type.replace(/_/g, " ")} opportunity`}
          description={`Customer #${data.customer_id} · scored ${formatDate(data.reference_date)}`}
          actions={
            <Badge variant={tierVariant(data.tier)}>
              {data.tier} · {formatPercent(data.score)}
            </Badge>
          }
        />
      </div>

      <section aria-label="Opportunity facts">
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2.5">
            <dt className="text-meta text-muted-foreground">Estimated value</dt>
            <dd className="text-lg font-semibold tabular-nums">
              {formatCurrency(data.estimated_value)}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2.5">
            <dt className="text-meta text-muted-foreground">Score</dt>
            <dd className="text-lg font-semibold tabular-nums">{formatPercent(data.score)}</dd>
          </div>
          <div className="flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2.5">
            <dt className="text-meta text-muted-foreground">Customer</dt>
            <dd className="text-lg font-semibold">
              <Link
                href={`/customers/${data.customer_id}`}
                className="underline-offset-4 hover:underline"
              >
                #{data.customer_id}
              </Link>
            </dd>
          </div>
          <div className="flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2.5">
            <dt className="text-meta text-muted-foreground">Segment</dt>
            <dd className="text-lg font-semibold">
              {data.segment_id !== null ? (
                <Link
                  href={`/segments/${data.segment_id}`}
                  className="underline-offset-4 hover:underline"
                >
                  #{data.segment_id}
                </Link>
              ) : (
                "—"
              )}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="opp-why" className="flex flex-col gap-2">
        <h3 id="opp-why" className="text-section-title">
          Why this was identified
        </h3>
        {data.reasons == null || data.reasons.length === 0 ? (
          <EmptyState
            title="No recorded rationale"
            description="This opportunity has no stored detection reasons."
          />
        ) : (
          <ul className="flex flex-col gap-1 text-sm">
            {data.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
        {signalEntries.length > 0 && (
          <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-sm">
            {signalEntries.map(([name, value]) => (
              <div key={name} className="flex gap-1.5">
                <dt className="text-muted-foreground capitalize">{name.replace(/_/g, " ")}</dt>
                <dd className="font-medium tabular-nums">{formatPercent(value)}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section aria-labelledby="opp-action" className="flex flex-col gap-2">
        <h3 id="opp-action" className="text-section-title">
          Recommended action
        </h3>
        <p className="text-sm">{data.recommended_action}</p>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" asChild>
            <Link href={`/customers/${data.customer_id}`}>
              Inspect customer
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
          {data.segment_id !== null && (
            <Button variant="secondary" size="sm" asChild>
              <Link href={`/segments/${data.segment_id}`}>
                Inspect segment
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          )}
        </div>
      </section>

      <InsightCard
        context={{ kind: "opportunity", id: data.id }}
        title="Why this opportunity"
        description="Explain why this opportunity was identified and what evidence supports it."
      />
    </div>
  );
}
