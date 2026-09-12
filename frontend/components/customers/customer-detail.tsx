"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { InsightCard } from "@/components/ai/insight-card";
import { Pagination } from "@/components/data/pagination";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePagedQuery } from "@/hooks/use-paged-query";
import { useResource } from "@/hooks/use-resource";
import { getCustomerIntelligence, listInteractions, listTransactions } from "@/lib/api";
import {
  formatCurrency,
  formatDate,
  formatDays,
  formatNumber,
  formatPercent,
  formatProbability,
} from "@/lib/format";
import type { Interaction, Prediction, Transaction } from "@/types";

function bandVariant(
  predictionType: string,
  band: string,
): "danger" | "warning" | "success" | "default" {
  if (predictionType === "churn") {
    return band === "high" ? "danger" : band === "medium" ? "warning" : "success";
  }
  return band === "high" ? "success" : band === "medium" ? "warning" : "default";
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2.5">
      <dt className="text-meta text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
      {hint != null && <dd className="text-meta text-muted-foreground">{hint}</dd>}
    </div>
  );
}

function ProbabilityBar({ probability, label }: { probability: number; label: string }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={Math.round(probability * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
    >
      <div className="h-full rounded-full bg-primary" style={{ width: `${probability * 100}%` }} />
    </div>
  );
}

function PredictionPanel({ prediction }: { prediction: Prediction }) {
  const isChurn = prediction.prediction_type === "churn";
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-section-title capitalize">{prediction.prediction_type} risk</h4>
        <span className="flex items-center gap-2">
          <Badge variant={bandVariant(prediction.prediction_type, prediction.band)}>
            {prediction.band} risk
          </Badge>
          <span className="text-sm font-semibold tabular-nums">
            {formatProbability(prediction.probability)}
          </span>
        </span>
      </div>
      <ProbabilityBar
        probability={prediction.probability}
        label={`${prediction.prediction_type} probability ${formatProbability(prediction.probability)}`}
      />
      {prediction.signals != null && prediction.signals.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-meta font-medium text-muted-foreground">Supporting signals</p>
          <ul className="flex flex-col gap-0.5 text-sm">
            {prediction.signals.map((signal) => (
              <li key={signal}>{signal}</li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <Button variant="secondary" size="sm" asChild>
          <Link
            href={`/predictions?customer_id=${prediction.customer_id}&prediction_type=${prediction.prediction_type}`}
          >
            {isChurn ? "Churn history" : "Purchase history"}
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </div>
  );
}

function PurchaseHistory({ customerId }: { customerId: number }) {
  const load = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listTransactions({ page, page_size: 10, customer_id: customerId }, signal),
    [customerId],
  );
  const query = usePagedQuery<Transaction>("purchase history", load, `transactions-${customerId}`, 10);
  return (
    <section aria-labelledby="purchase-history" className="flex flex-col gap-3">
      <h3 id="purchase-history" className="text-section-title">
        Purchase history
      </h3>
      {query.loading ? (
        <Skeleton className="h-40" />
      ) : query.error !== null ? (
        <ErrorState
          title="Unable to load transactions"
          description={query.error}
          onRetry={query.retry}
        />
      ) : query.items.length === 0 ? (
        <EmptyState
          title="No purchases recorded"
          description="This customer has no transactions in the system yet."
        />
      ) : (
        <>
          <Table aria-label="Purchase history">
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Product</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.items.map((txn) => (
                <TableRow key={txn.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(txn.transaction_date)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">#{txn.product_id}</TableCell>
                  <TableCell className="text-right tabular-nums">{txn.quantity}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(txn.total_amount)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        txn.status === "completed"
                          ? "success"
                          : txn.status === "refunded"
                            ? "warning"
                            : "default"
                      }
                    >
                      {txn.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination
            page={query.page}
            pageCount={query.pageCount}
            total={query.total}
            onPageChange={query.setPage}
          />
        </>
      )}
    </section>
  );
}

function Engagement({ customerId }: { customerId: number }) {
  const load = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listInteractions({ page, page_size: 10, customer_id: customerId }, signal),
    [customerId],
  );
  const query = usePagedQuery<Interaction>(
    "interactions",
    load,
    `interactions-${customerId}`,
    10,
  );
  return (
    <section aria-labelledby="engagement" className="flex flex-col gap-3">
      <h3 id="engagement" className="text-section-title">
        Engagement
      </h3>
      {query.loading ? (
        <Skeleton className="h-40" />
      ) : query.error !== null ? (
        <ErrorState
          title="Unable to load interactions"
          description={query.error}
          onRetry={query.retry}
        />
      ) : query.items.length === 0 ? (
        <EmptyState
          title="No engagement recorded"
          description="No interactions have been logged for this customer yet."
        />
      ) : (
        <>
          <Table aria-label="Recent interactions">
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Summary</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.items.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(event.occurred_at)}
                  </TableCell>
                  <TableCell className="capitalize">
                    {event.interaction_type.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell className="capitalize">{event.channel.replace(/_/g, " ")}</TableCell>
                  <TableCell className="max-w-64 truncate text-muted-foreground">
                    {event.summary ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination
            page={query.page}
            pageCount={query.pageCount}
            total={query.total}
            onPageChange={query.setPage}
          />
        </>
      )}
    </section>
  );
}

/** Customer intelligence profile: metrics, segment, predictions, opportunities. */
export function CustomerDetail({ customerId }: { customerId: number }) {
  const load = React.useCallback(
    (signal: AbortSignal) => getCustomerIntelligence(customerId, signal),
    [customerId],
  );
  const { data, loading, error, retry } = useResource(
    "customer intelligence",
    load,
    `customer-${customerId}`,
  );

  if (loading) {
    return (
      <div className="flex flex-col gap-4" role="status" aria-label="Loading customer">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" asChild className="self-start">
          <Link href="/customers">
            <ArrowLeft aria-hidden="true" />
            Customers
          </Link>
        </Button>
        <ErrorState
          title="Unable to load customer"
          description={error ?? "Unknown error."}
          onRetry={retry}
        />
      </div>
    );
  }

  const { customer, metrics, segment, predictions, opportunities } = data;
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link href="/customers">
            <ArrowLeft aria-hidden="true" />
            Customers
          </Link>
        </Button>
        <PageHeader
          title={`${customer.first_name} ${customer.last_name}`}
          description={[customer.email, customer.city, customer.country]
            .filter(Boolean)
            .join(" · ")}
          actions={
            segment !== null ? (
              <Button variant="secondary" size="sm" asChild>
                <Link href={`/segments/${segment.id}`}>Segment: {segment.name}</Link>
              </Button>
            ) : undefined
          }
        />
      </div>

      <section aria-label="Key metrics">
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat
            label="Lifetime revenue"
            value={formatCurrency(metrics.total_revenue)}
            hint={`${formatNumber(metrics.completed_orders)} completed orders`}
          />
          <Stat
            label="Average order"
            value={formatCurrency(metrics.avg_order_value)}
            hint={`Peak ${formatCurrency(metrics.max_order_value)}`}
          />
          <Stat
            label="Recency"
            value={
              metrics.recency_days === null
                ? "No orders"
                : formatDays(metrics.recency_days, "day", "days")
            }
            hint={metrics.is_inactive_90d ? "Inactive 90+ days" : "Active"}
          />
          <Stat
            label="Interactions"
            value={formatNumber(metrics.total_interactions)}
            hint={`${formatNumber(metrics.distinct_campaigns)} campaigns touched`}
          />
        </dl>
      </section>

      <InsightCard
        context={{ kind: "customer", id: customer.id }}
        title="Explain this customer"
        description="Explain this customer's value, risks, and opportunities from verified metrics and predictions."
      />

      <section aria-labelledby="predictions" className="flex flex-col gap-3">
        <h3 id="predictions" className="text-section-title">
          Predictions
        </h3>
        {predictions.length === 0 ? (
          <EmptyState
            title="No predictions yet"
            description="No model predictions have been materialized for this customer."
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {predictions.map((prediction) => (
              <PredictionPanel key={prediction.id} prediction={prediction} />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="opportunities" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="opportunities" className="text-section-title">
            Opportunities
          </h3>
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/opportunities?customer_id=${customer.id}`}>
              All for this customer
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </div>
        {opportunities.length === 0 ? (
          <EmptyState
            title="No open opportunities"
            description="No scored opportunities currently target this customer."
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {opportunities.slice(0, 4).map((opp) => (
              <div key={opp.id} className="flex flex-col gap-1.5 rounded-lg border bg-card p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium capitalize">
                    {opp.opportunity_type.replace(/_/g, " ")}
                  </span>
                  <Badge
                    variant={
                      opp.tier === "high" ? "success" : opp.tier === "medium" ? "warning" : "default"
                    }
                  >
                    {opp.tier} · {formatPercent(opp.score)}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{opp.recommended_action}</p>
                <div>
                  <Button variant="secondary" size="sm" asChild>
                    <Link href={`/opportunities/${opp.id}`}>
                      View detail
                      <ArrowRight aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <PurchaseHistory customerId={customer.id} />
      <Engagement customerId={customer.id} />
    </div>
  );
}
