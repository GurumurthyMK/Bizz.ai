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
import { listPredictions } from "@/lib/api";
import { formatProbability } from "@/lib/format";
import type { Prediction } from "@/types";

function bandVariant(predictionType: string, band: string): "danger" | "warning" | "success" | "default" {
  if (predictionType === "churn") {
    return band === "high" ? "danger" : band === "medium" ? "warning" : "success";
  }
  return band === "high" ? "success" : band === "medium" ? "warning" : "default";
}

interface PredictionTableProps {
  initialCustomerId?: number;
  initialType?: "churn" | "purchase";
}

/** Prediction list: type/band filters, probability sorting, customer linkage. */
export function PredictionTable({ initialCustomerId, initialType }: PredictionTableProps) {
  const [predictionType, setPredictionType] = React.useState<"churn" | "purchase" | "all">(
    initialType ?? "all",
  );
  const [band, setBand] = React.useState<string>("all");
  const [customerInput, setCustomerInput] = React.useState(
    initialCustomerId !== undefined ? String(initialCustomerId) : "",
  );
  const [order, setOrder] = React.useState<"asc" | "desc">("desc");

  const customerId =
    customerInput.trim() !== "" && Number.isInteger(Number(customerInput))
      ? Number(customerInput)
      : undefined;
  const resetKey = JSON.stringify({ predictionType, band, customerId, order });

  const load = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listPredictions(
        {
          page,
          page_size: 20,
          prediction_type: predictionType === "all" ? undefined : predictionType,
          band: band === "all" ? undefined : band,
          customer_id: customerId,
          sort_by: "probability",
          order,
        },
        signal,
      ),
    [predictionType, band, customerId, order],
  );
  const query = usePagedQuery<Prediction>("predictions", load, resetKey);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Predictions"
        description="Churn risk and purchase likelihood with supporting signals."
      />
      <form
        aria-label="Prediction filters"
        className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor="pred-type">Type</Label>
          <Select
            value={predictionType}
            onValueChange={(value) => setPredictionType(value as "churn" | "purchase" | "all")}
          >
            <SelectTrigger id="pred-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="churn">Churn</SelectItem>
              <SelectItem value="purchase">Purchase</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="pred-band">Risk band</Label>
          <Select value={band} onValueChange={setBand}>
            <SelectTrigger id="pred-band">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All bands</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="pred-customer">Customer ID</Label>
          <Input
            id="pred-customer"
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
              setPredictionType("all");
              setBand("all");
              setCustomerInput("");
              setOrder("desc");
            }}
          >
            Clear filters
          </Button>
        </div>
      </form>

      {query.loading ? (
        <div className="flex flex-col gap-2" role="status" aria-label="Loading predictions">
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} className="h-10" />
          ))}
        </div>
      ) : query.error !== null ? (
        <ErrorState
          title="Unable to load predictions"
          description={query.error}
          onRetry={query.retry}
        />
      ) : query.items.length === 0 ? (
        <EmptyState
          title="No predictions found"
          description="No predictions match the current filters. Predictions appear after the models run and their output is materialized."
        />
      ) : (
        <>
          <Table aria-label="Predictions">
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead>Type</TableHead>
                <SortHeader
                  label="Probability"
                  active
                  direction={order}
                  onToggle={() => setOrder((current) => (current === "asc" ? "desc" : "asc"))}
                />
                <TableHead>Band</TableHead>
                <TableHead>Supporting signals</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.items.map((prediction) => (
                <TableRow key={prediction.id}>
                  <TableCell>
                    <Link
                      href={`/customers/${prediction.customer_id}`}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      #{prediction.customer_id}
                    </Link>
                  </TableCell>
                  <TableCell className="capitalize">{prediction.prediction_type}</TableCell>
                  <TableCell className="tabular-nums">
                    {formatProbability(prediction.probability)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={bandVariant(prediction.prediction_type, prediction.band)}>
                      {prediction.band}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-72">
                    {prediction.signals == null || prediction.signals.length === 0 ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      <ul className="flex flex-col gap-0.5 text-sm text-muted-foreground">
                        {prediction.signals.slice(0, 2).map((signal) => (
                          <li key={signal} className="truncate">
                            {signal}
                          </li>
                        ))}
                        {prediction.signals.length > 2 && (
                          <li>+{prediction.signals.length - 2} more</li>
                        )}
                      </ul>
                    )}
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
