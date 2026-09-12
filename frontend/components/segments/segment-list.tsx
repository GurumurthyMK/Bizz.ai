"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
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
import { useResource } from "@/hooks/use-resource";
import { listSegments } from "@/lib/api";
import { formatCurrency, formatDays, formatNumber, formatPercent } from "@/lib/format";
import type { Segment } from "@/types";

/** Segment list with metrics and characteristics. */
export function SegmentList() {
  const load = React.useCallback((signal: AbortSignal) => listSegments(signal), []);
  const { data, loading, error, retry } = useResource<Segment[]>(
    "segments",
    load,
    "segments",
  );

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Segments"
        description="Customer groups derived from purchasing and engagement behavior."
      />
      {loading ? (
        <div className="flex flex-col gap-2" role="status" aria-label="Loading segments">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-12" />
          ))}
        </div>
      ) : error !== null || data === null ? (
        <ErrorState title="Unable to load segments" description={error ?? "Unknown error."} onRetry={retry} />
      ) : data.length === 0 ? (
        <EmptyState
          title="No segments yet"
          description="Segments appear here after the segmentation model runs and its output is materialized."
        />
      ) : (
        <Table aria-label="Customer segments">
          <TableHeader>
            <TableRow>
              <TableHead>Segment</TableHead>
              <TableHead className="text-right">Customers</TableHead>
              <TableHead className="text-right">Share</TableHead>
              <TableHead className="text-right">Avg revenue</TableHead>
              <TableHead className="text-right">Avg recency</TableHead>
              <TableHead className="text-right">Avg orders</TableHead>
              <TableHead>
                <span className="sr-only">Open</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((segment) => (
              <TableRow key={segment.id}>
                <TableCell>
                  <Link
                    href={`/segments/${segment.id}`}
                    className="font-medium underline-offset-4 hover:underline"
                  >
                    {segment.name}
                  </Link>
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatNumber(segment.size)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatPercent(segment.share)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(segment.avg_revenue)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatDays(Math.round(segment.avg_recency_days), "day", "days")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {segment.avg_completed_orders.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/segments/${segment.id}`} aria-label={`Open ${segment.name}`}>
                      <ArrowRight aria-hidden="true" />
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
