"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { InsightCard } from "@/components/ai/insight-card";
import { Pagination } from "@/components/data/pagination";
import { PageHeader } from "@/components/layout/page-header";
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
import { getSegment, listSegmentCustomers } from "@/lib/api";
import { formatCurrency, formatDate, formatDays, formatNumber, formatPercent } from "@/lib/format";
import type { Customer } from "@/types";

/** Segment overview: metrics, characteristics, and member customers. */
export function SegmentDetail({ segmentId }: { segmentId: number }) {
  const loadSegment = React.useCallback(
    (signal: AbortSignal) => getSegment(segmentId, signal),
    [segmentId],
  );
  const segment = useResource("segment", loadSegment, `segment-${segmentId}`);

  const loadMembers = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listSegmentCustomers(segmentId, { page, page_size: 20 }, signal),
    [segmentId],
  );
  const members = usePagedQuery<Customer>(
    "segment members",
    loadMembers,
    `segment-members-${segmentId}`,
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link href="/segments">
            <ArrowLeft aria-hidden="true" />
            Segments
          </Link>
        </Button>
        {segment.loading ? (
          <Skeleton className="h-10 w-64" />
        ) : segment.error !== null || segment.data === null ? (
          <ErrorState
            title="Unable to load segment"
            description={segment.error ?? "Unknown error."}
            onRetry={segment.retry}
          />
        ) : (
          <PageHeader
            title={segment.data.name}
            description={`Cluster ${segment.data.cluster_id} · ${formatNumber(segment.data.size)} customers (${formatPercent(segment.data.share)} of base)`}
          />
        )}
      </div>

      {segment.data !== null && !segment.loading && (
        <section aria-label="Segment characteristics">
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              { label: "Avg revenue", value: formatCurrency(segment.data.avg_revenue) },
              {
                label: "Avg recency",
                value: formatDays(Math.round(segment.data.avg_recency_days), "day", "days"),
              },
              {
                label: "Avg orders",
                value: segment.data.avg_completed_orders.toFixed(1),
              },
              {
                label: "Model",
                value: segment.data.model_version,
              },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2.5">
                <dt className="text-meta text-muted-foreground">{stat.label}</dt>
                <dd className="text-lg font-semibold tabular-nums">{stat.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {segment.data !== null && !segment.loading && (
        <InsightCard
          context={{ kind: "segment", id: segment.data.id }}
          title="Why this segment matters"
          description="Explain what defines this segment and why it matters for the business."
        />
      )}

      <section aria-labelledby="segment-members" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="segment-members" className="text-section-title">
            Member customers
          </h3>
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/opportunities?segment_id=${segmentId}`}>
              Opportunities in this segment
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </div>
        {members.loading ? (
          <div className="flex flex-col gap-2" role="status" aria-label="Loading members">
            {Array.from({ length: 6 }, (_, index) => (
              <Skeleton key={index} className="h-10" />
            ))}
          </div>
        ) : members.error !== null ? (
          <ErrorState
            title="Unable to load members"
            description={members.error}
            onRetry={members.retry}
          />
        ) : members.items.length === 0 ? (
          <EmptyState
            title="No members in this segment"
            description="No customers are currently assigned to this segment."
          />
        ) : (
          <>
            <Table aria-label="Segment members">
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>City</TableHead>
                  <TableHead>Joined</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.items.map((customer) => (
                  <TableRow key={customer.id}>
                    <TableCell>
                      <Link
                        href={`/customers/${customer.id}`}
                        className="font-medium underline-offset-4 hover:underline"
                      >
                        {customer.first_name} {customer.last_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{customer.email}</TableCell>
                    <TableCell>{customer.city ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatDate(customer.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination
              page={members.page}
              pageCount={members.pageCount}
              total={members.total}
              onPageChange={members.setPage}
            />
          </>
        )}
      </section>
    </div>
  );
}
