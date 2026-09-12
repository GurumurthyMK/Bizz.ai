"use client";

import * as React from "react";
import Link from "next/link";
import { Pagination } from "@/components/data/pagination";
import { SortHeader } from "@/components/data/sort-header";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { listOpportunities, listSegments } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/format";
import type { Opportunity, Segment } from "@/types";

function tierVariant(tier: string): "success" | "warning" | "default" {
  return tier === "high" ? "success" : tier === "medium" ? "warning" : "default";
}

interface OpportunityTableProps {
  initialCustomerId?: number;
  initialSegmentId?: number;
}

/** Opportunity list: tier/type filters, score sorting, customer linkage. */
export function OpportunityTable({ initialCustomerId, initialSegmentId }: OpportunityTableProps) {
  const [tier, setTier] = React.useState("all");
  const [opportunityType, setOpportunityType] = React.useState("all");
  const [customerInput, setCustomerInput] = React.useState(
    initialCustomerId !== undefined ? String(initialCustomerId) : "",
  );
  const [segment, setSegment] = React.useState(
    initialSegmentId !== undefined ? String(initialSegmentId) : "all",
  );
  const [order, setOrder] = React.useState<"asc" | "desc">("desc");
  const [segments, setSegments] = React.useState<Segment[]>([]);

  React.useEffect(() => {
    const controller = new AbortController();
    listSegments(controller.signal)
      .then((rows) => {
        if (!controller.signal.aborted) setSegments(rows);
      })
      .catch(() => {
        // Segment filter stays unusable-but-harmless when segments fail to load.
      });
    return () => controller.abort();
  }, []);

  const customerId =
    customerInput.trim() !== "" && Number.isInteger(Number(customerInput))
      ? Number(customerInput)
      : undefined;
  const segmentId = segment !== "all" && Number.isInteger(Number(segment)) ? Number(segment) : undefined;
  const resetKey = JSON.stringify({ tier, opportunityType, customerId, segmentId, order });

  const load = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listOpportunities(
        {
          page,
          page_size: 20,
          tier: tier === "all" ? undefined : tier,
          opportunity_type: opportunityType === "all" ? undefined : opportunityType,
          customer_id: customerId,
          segment_id: segmentId,
          sort_by: "score",
          order,
        },
        signal,
      ),
    [tier, opportunityType, customerId, segmentId, order],
  );
  const query = usePagedQuery<Opportunity>("opportunities", load, resetKey);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Opportunities"
        description="Scored sources of business value with evidence and next actions."
      />
      <form
        aria-label="Opportunity filters"
        className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor="opp-tier">Tier</Label>
          <Select value={tier} onValueChange={setTier}>
            <SelectTrigger id="opp-tier">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All tiers</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="opp-type">Type</Label>
          <Select value={opportunityType} onValueChange={setOpportunityType}>
            <SelectTrigger id="opp-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="high-value">High value</SelectItem>
              <SelectItem value="purchase">Purchase</SelectItem>
              <SelectItem value="retention">Retention</SelectItem>
              <SelectItem value="engagement">Engagement</SelectItem>
              <SelectItem value="growth">Growth</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="opp-segment">Segment</Label>
          <Select value={segment} onValueChange={setSegment}>
            <SelectTrigger id="opp-segment">
              <SelectValue placeholder="All segments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All segments</SelectItem>
              {segments.map((row) => (
                <SelectItem key={row.id} value={String(row.id)}>
                  {row.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="opp-customer">Customer ID</Label>
          <Input
            id="opp-customer"
            value={customerInput}
            onChange={(event) => setCustomerInput(event.target.value)}
            placeholder="e.g. 123"
            inputMode="numeric"
            autoComplete="off"
          />
        </div>
        <div className="flex items-end">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setTier("all");
              setOpportunityType("all");
              setSegment("all");
              setCustomerInput("");
              setOrder("desc");
            }}
          >
            Clear filters
          </Button>
        </div>
      </form>

      {query.loading ? (
        <div className="flex flex-col gap-2" role="status" aria-label="Loading opportunities">
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} className="h-10" />
          ))}
        </div>
      ) : query.error !== null ? (
        <ErrorState
          title="Unable to load opportunities"
          description={query.error}
          onRetry={query.retry}
        />
      ) : query.items.length === 0 ? (
        <EmptyState
          title="No opportunities found"
          description="No scored opportunities match the current filters. Opportunities appear after the engine runs and its output is materialized."
        />
      ) : (
        <>
          <Table aria-label="Opportunities">
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Tier</TableHead>
                <SortHeader
                  label="Score"
                  active
                  direction={order}
                  onToggle={() => setOrder((current) => (current === "asc" ? "desc" : "asc"))}
                />
                <TableHead className="text-right">Est. value</TableHead>
                <TableHead>
                  <span className="sr-only">Open</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.items.map((opp) => (
                <TableRow key={opp.id}>
                  <TableCell>
                    <Link
                      href={`/customers/${opp.customer_id}`}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      #{opp.customer_id}
                    </Link>
                  </TableCell>
                  <TableCell className="capitalize">{opp.opportunity_type.replace(/_/g, " ")}</TableCell>
                  <TableCell>
                    <Badge variant={tierVariant(opp.tier)}>{opp.tier}</Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{formatPercent(opp.score)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(opp.estimated_value)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="secondary" size="sm" asChild>
                      <Link href={`/opportunities/${opp.id}`}>Detail</Link>
                    </Button>
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
    </div>
  );
}
