"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, BellRing } from "lucide-react";
import { Pagination } from "@/components/data/pagination";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
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
import { acknowledgeAlert, detectAlerts, listAlerts } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Alert } from "@/types";

function severityVariant(severity: string): "danger" | "warning" | "info" | "default" {
  return severity === "high" ? "danger" : severity === "medium" ? "warning" : "info";
}

function entityHref(alert: Alert): { href: string; label: string } | null {
  switch (alert.entity_type) {
    case "customer":
      return alert.entity_id !== null
        ? { href: `/customers/${alert.entity_id}`, label: `Customer ${alert.entity_id}` }
        : null;
    case "segment":
      return alert.entity_id !== null
        ? { href: `/segments/${alert.entity_id}`, label: `Segment ${alert.entity_id}` }
        : null;
    case "opportunity":
      return alert.entity_id !== null
        ? { href: `/opportunities/${alert.entity_id}`, label: `Opportunity ${alert.entity_id}` }
        : null;
    case "prediction":
      return { href: "/predictions", label: "Predictions" };
    default:
      return { href: "/overview", label: "Overview" };
  }
}

const TYPE_LABELS: Record<string, string> = {
  high_churn_risk: "Churn risk",
  revenue_anomaly: "Revenue",
  engagement_decline: "Engagement",
  new_opportunity: "Opportunity",
  segment_change: "Segment",
};

/** Alerts workflow: filterable list, evidence links, acknowledge, detection. */
export function AlertList() {
  const [severity, setSeverity] = React.useState("all");
  const [alertType, setAlertType] = React.useState("all");
  const [status, setStatus] = React.useState("all");
  const [armedId, setArmedId] = React.useState<number | null>(null);
  const [detecting, setDetecting] = React.useState(false);
  const [detectNote, setDetectNote] = React.useState<string | null>(null);
  const resetKey = JSON.stringify({ severity, alertType, status });

  const load = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listAlerts(
        {
          page,
          page_size: 20,
          severity: severity === "all" ? undefined : severity,
          alert_type: alertType === "all" ? undefined : alertType,
          status: status === "all" ? undefined : status,
        },
        signal,
      ),
    [severity, alertType, status],
  );
  const query = usePagedQuery<Alert>("alerts", load, resetKey);

  const runDetection = async () => {
    setDetecting(true);
    setDetectNote(null);
    try {
      const report = await detectAlerts();
      setDetectNote(
        report.created === 0
          ? "Detection complete — no new alerts."
          : `Detection complete — ${report.created} new alert${report.created === 1 ? "" : "s"}.`,
      );
      query.retry();
    } catch {
      setDetectNote("Detection failed. The existing alerts are unaffected.");
    } finally {
      setDetecting(false);
    }
  };

  const acknowledge = async (id: number) => {
    if (armedId !== id) {
      setArmedId(id);
      return;
    }
    setArmedId(null);
    try {
      await acknowledgeAlert(id);
      query.retry();
    } catch {
      // Row keeps its state; the list error surface handles fetch failures.
      query.retry();
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Alerts"
        description="Deterministic business-event notifications with evidence and deep links."
        actions={
          <Button type="button" variant="secondary" size="sm" onClick={runDetection} disabled={detecting}>
            <BellRing aria-hidden="true" />
            {detecting ? "Detecting…" : "Check for new alerts"}
          </Button>
        }
      />
      {detectNote !== null && (
        <p role="status" className="text-sm text-muted-foreground">
          {detectNote}
        </p>
      )}
      <form
        aria-label="Alert filters"
        className="grid grid-cols-1 gap-2 sm:grid-cols-3"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor="alert-severity">Severity</Label>
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger id="alert-severity">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="alert-type">Type</Label>
          <Select value={alertType} onValueChange={setAlertType}>
            <SelectTrigger id="alert-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {Object.entries(TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="alert-status">Status</Label>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger id="alert-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </form>

      {query.loading ? (
        <div className="flex flex-col gap-2" role="status" aria-label="Loading alerts">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-12" />
          ))}
        </div>
      ) : query.error !== null ? (
        <ErrorState title="Unable to load alerts" description={query.error} onRetry={query.retry} />
      ) : query.items.length === 0 ? (
        <EmptyState
          title="No alerts match"
          description="No alerts exist for the current filters, or detection has not run yet. Use “Check for new alerts” to evaluate current conditions."
        />
      ) : (
        <>
          <Table aria-label="Alerts">
            <TableHeader>
              <TableRow>
                <TableHead>Severity</TableHead>
                <TableHead>Alert</TableHead>
                <TableHead>Evidence</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.items.map((alert) => {
                const target = entityHref(alert);
                return (
                  <TableRow key={alert.id}>
                    <TableCell>
                      <Badge variant={severityVariant(alert.severity)}>{alert.severity}</Badge>
                    </TableCell>
                    <TableCell>
                      <p className="font-medium">{alert.title}</p>
                      <p className="max-w-md text-sm text-muted-foreground">{alert.description}</p>
                    </TableCell>
                    <TableCell>
                      {target === null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={target.href}>
                            {target.label}
                            <ArrowRight aria-hidden="true" />
                          </Link>
                        </Button>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatDate(alert.created_at)}
                    </TableCell>
                    <TableCell>
                      {alert.status === "acknowledged" ? (
                        <Badge variant="default">Acknowledged</Badge>
                      ) : (
                        <Button
                          type="button"
                          variant={armedId === alert.id ? "destructive" : "secondary"}
                          size="sm"
                          onClick={() => void acknowledge(alert.id)}
                          onBlur={() => {
                            if (armedId === alert.id) setArmedId(null);
                          }}
                        >
                          {armedId === alert.id ? "Confirm" : "Acknowledge"}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
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
