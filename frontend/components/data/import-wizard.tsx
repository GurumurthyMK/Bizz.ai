"use client";

import * as React from "react";
import { ApiError, importCsv, previewCsvImport } from "@/lib/api";
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
import { ENTITY_META } from "@/components/data/data-sources";
import { formatNumber } from "@/lib/format";
import type { DataEntity, ImportPreview, ImportResult, ImportRowError } from "@/types";

const CLIENT_MAX_BYTES = 10 * 1024 * 1024;
const SHOWN_ERRORS = 20;

type Step = "select" | "preview" | "result";

function rowErrorsFrom(error: unknown): ImportRowError[] {
  if (error instanceof ApiError && Array.isArray(error.details)) {
    return (error.details as ImportRowError[]).filter(
      (item): item is ImportRowError =>
        typeof item === "object" && item !== null && "line" in item && "message" in item,
    );
  }
  return [];
}

/** CSV workflow: upload → validate → preview → import → completion result. */
export function ImportWizard({
  entity,
  onEntityChange,
  onImported,
}: {
  entity: DataEntity;
  onEntityChange: (entity: DataEntity) => void;
  onImported: () => void;
}) {
  const [step, setStep] = React.useState<Step>("select");
  const [file, setFile] = React.useState<File | null>(null);
  const [clientError, setClientError] = React.useState<string | null>(null);
  const [preview, setPreview] = React.useState<ImportPreview | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [failure, setFailure] = React.useState<{ message: string; errors: ImportRowError[] } | null>(null);
  const [result, setResult] = React.useState<ImportResult | null>(null);

  const resetToSelect = React.useCallback(() => {
    setStep("select");
    setFile(null);
    setClientError(null);
    setPreview(null);
    setFailure(null);
    setResult(null);
  }, []);

  React.useEffect(() => {
    resetToSelect();
  }, [entity, resetToSelect]);

  const chooseFile = (next: File | null) => {
    setClientError(null);
    setFailure(null);
    if (next === null) {
      setFile(null);
      return;
    }
    if (!next.name.toLowerCase().endsWith(".csv")) {
      setFile(null);
      setClientError(`"${next.name}" is not a .csv file. Export or rename it first.`);
      return;
    }
    if (next.size > CLIENT_MAX_BYTES) {
      setFile(null);
      setClientError("File exceeds the 10 MB upload limit. Split it and try again.");
      return;
    }
    if (next.size === 0) {
      setFile(null);
      setClientError("File is empty. Choose a CSV with a header row and data.");
      return;
    }
    setFile(next);
  };

  const runPreview = async () => {
    if (file === null) return;
    setBusy(true);
    setFailure(null);
    try {
      const report = await previewCsvImport(entity, file);
      setPreview(report);
      setStep("preview");
    } catch (error) {
      setFailure({
        message: error instanceof Error ? error.message : "Preview failed.",
        errors: rowErrorsFrom(error),
      });
    } finally {
      setBusy(false);
    }
  };

  const runImport = async () => {
    if (file === null) return;
    setBusy(true);
    setFailure(null);
    try {
      const outcome = await importCsv(entity, file);
      setResult(outcome);
      setStep("result");
      onImported();
    } catch (error) {
      setFailure({
        message: error instanceof Error ? error.message : "Import failed.",
        errors: rowErrorsFrom(error),
      });
    } finally {
      setBusy(false);
    }
  };

  const requiredColumns =
    ENTITY_META.find((meta) => meta.entity === entity)?.requiredColumns ?? [];

  return (
    <section aria-labelledby="csv-import" className="flex flex-col gap-3">
      <h2 id="csv-import" className="text-section-title">
        CSV import
      </h2>
      <ol aria-label="Import progress" className="flex flex-wrap gap-2 text-sm text-muted-foreground">
        {(["select", "preview", "result"] as Step[]).map((name, index) => (
          <li
            key={name}
            aria-current={step === name ? "step" : undefined}
            className={step === name ? "font-medium text-foreground" : undefined}
          >
            {index + 1}. {name === "select" ? "Choose file" : name === "preview" ? "Review" : "Done"}
            {index < 2 && <span aria-hidden="true"> · </span>}
          </li>
        ))}
      </ol>

      {step === "select" && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <Label htmlFor="import-entity">Data category</Label>
            <Select value={entity} onValueChange={(value) => onEntityChange(value as DataEntity)}>
              <SelectTrigger id="import-entity">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ENTITY_META.map((meta) => (
                  <SelectItem key={meta.entity} value={meta.entity}>
                    {meta.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-meta text-muted-foreground">
              Required columns: {requiredColumns.join(", ")}
            </p>
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="import-file">CSV file (max 10 MB)</Label>
            <Input
              id="import-file"
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
            />
            {file !== null && (
              <p className="text-meta text-muted-foreground" role="status">
                {file.name} · {(file.size / 1024).toFixed(1)} KB
              </p>
            )}
          </div>
        </div>
      )}
      {clientError !== null && (
        <p role="alert" className="text-sm text-danger">
          {clientError}
        </p>
      )}
      {step === "select" && (
        <div>
          <Button type="button" onClick={runPreview} disabled={file === null || busy}>
            {busy ? "Validating…" : "Validate & preview"}
          </Button>
        </div>
      )}

      {step === "preview" && preview !== null && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={preview.invalid_rows === 0 ? "success" : "warning"}>
              {formatNumber(preview.valid_rows)} valid / {formatNumber(preview.total_rows)} rows
            </Badge>
            <span className="text-muted-foreground">
              {preview.filename} · columns: {preview.columns.join(", ")}
            </span>
          </div>
          {preview.errors.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">
                Row errors{" "}
                <span className="font-normal text-muted-foreground">
                  (showing {Math.min(SHOWN_ERRORS, preview.errors.length)} of{" "}
                  {formatNumber(preview.errors.length)}
                  {preview.errors_truncated ? "+; fix and re-upload to see the rest" : ""})
                </span>
              </h3>
              <Table aria-label="Validation errors">
                <TableHeader>
                  <TableRow>
                    <TableHead>Line</TableHead>
                    <TableHead>Column</TableHead>
                    <TableHead>Problem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.errors.slice(0, SHOWN_ERRORS).map((error, index) => (
                    <TableRow key={`${error.line}-${error.column}-${index}`}>
                      <TableCell className="tabular-nums">{error.line}</TableCell>
                      <TableCell>{error.column || "—"}</TableCell>
                      <TableCell>{error.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {preview.sample.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">Sample of valid rows</h3>
              <Table aria-label="Sample rows">
                <TableHeader>
                  <TableRow>
                    {preview.columns.map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.sample.map((row, index) => (
                    <TableRow key={index}>
                      {preview.columns.map((column) => (
                        <TableCell key={column} className="max-w-48 truncate">
                          {row[column] ?? "—"}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {preview.valid_rows === 0 && (
            <EmptyState
              title="Nothing valid to import"
              description="Every row failed validation. Fix the errors above and upload again — nothing was written."
            />
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={runImport}
              disabled={busy || preview.valid_rows === 0}
            >
              {busy ? "Importing…" : `Import ${formatNumber(preview.valid_rows)} rows`}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setStep("select");
                setPreview(null);
              }}
              disabled={busy}
            >
              Back
            </Button>
          </div>
        </div>
      )}

      {failure !== null && step !== "result" && (
        <div className="flex flex-col gap-2" role="alert">
          <p className="text-sm text-danger">{failure.message}</p>
          {failure.errors.length > 0 && (
            <Table aria-label="Import errors">
              <TableHeader>
                <TableRow>
                  <TableHead>Line</TableHead>
                  <TableHead>Column</TableHead>
                  <TableHead>Problem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {failure.errors.slice(0, SHOWN_ERRORS).map((error, index) => (
                  <TableRow key={`${error.line}-${error.column}-${index}`}>
                    <TableCell className="tabular-nums">{error.line}</TableCell>
                    <TableCell>{error.column || "—"}</TableCell>
                    <TableCell>{error.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <p className="text-meta text-muted-foreground">
            Nothing was written: imports are all-or-nothing.
          </p>
        </div>
      )}

      {step === "result" && result !== null && (
        <div className="flex flex-col gap-3 rounded-lg border bg-card p-4" role="status">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success">{result.status}</Badge>
            <h3 className="text-section-title">Import complete</h3>
          </div>
          <dl className="grid grid-cols-3 gap-2 text-sm">
            <div className="flex flex-col">
              <dt className="text-muted-foreground">File</dt>
              <dd className="truncate" title={result.filename}>
                {result.filename}
              </dd>
            </div>
            <div className="flex flex-col">
              <dt className="text-muted-foreground">Rows read</dt>
              <dd className="tabular-nums">{formatNumber(result.rows_total)}</dd>
            </div>
            <div className="flex flex-col">
              <dt className="text-muted-foreground">Rows inserted</dt>
              <dd className="tabular-nums">{formatNumber(result.rows_inserted)}</dd>
            </div>
          </dl>
          <div>
            <Button type="button" variant="secondary" size="sm" onClick={resetToSelect}>
              Import another file
            </Button>
          </div>
        </div>
      )}

      {busy && step !== "preview" && step !== "result" && (
        <div className="flex flex-col gap-2" role="status" aria-label="Working">
          <Skeleton className="h-10 w-full" />
        </div>
      )}
    </section>
  );
}
