"use client";

import * as React from "react";
import { DataSources } from "@/components/data/data-sources";
import { HealthPanel } from "@/components/data/health-panel";
import { ImportWizard } from "@/components/data/import-wizard";
import { PageHeader } from "@/components/layout/page-header";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getDataHealth } from "@/lib/api";
import type { DataEntity, DataHealth } from "@/types";

/** Data management: sources, health, and safe CSV import. */
export function DataDashboard() {
  const [health, setHealth] = React.useState<DataHealth | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  const [entity, setEntity] = React.useState<DataEntity>("customers");

  const load = React.useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDataHealth(signal);
      setHealth(data);
    } catch (fetchError) {
      if (fetchError instanceof ApiError && fetchError.status === 401) {
        setError("Your session expired. Please log in again.");
      } else if (fetchError instanceof Error) {
        setError(`Unable to load data health: ${fetchError.message}`);
      } else {
        setError("Unable to load data health.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load, attempt]);

  const refresh = React.useCallback(() => setAttempt((count) => count + 1), []);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Data"
        description="Inspect sources and health, then import CSV business data safely."
      />
      {loading ? (
        <div className="flex flex-col gap-3" role="status" aria-label="Loading data overview">
          <Skeleton className="h-32" />
          <Skeleton className="h-40" />
        </div>
      ) : error !== null || health === null ? (
        <ErrorState
          title="Unable to load data overview"
          description={error ?? "The data service could not be reached."}
          onRetry={refresh}
        />
      ) : (
        <>
          <DataSources
            health={health}
            onImport={(next) => {
              setEntity(next);
              document
                .getElementById("csv-import")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          />
          <HealthPanel health={health} />
          <ImportWizard entity={entity} onEntityChange={setEntity} onImported={refresh} />
        </>
      )}
    </div>
  );
}
