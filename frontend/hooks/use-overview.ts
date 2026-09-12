"use client";

import * as React from "react";
import { ApiError, getOverview } from "@/lib/api";
import type { OverviewResponse } from "@/types";

export interface OverviewState {
  data: OverviewResponse | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

/** Fetch lifecycle for the overview contract: loading / success / error. */
export function useOverview(): OverviewState {
  const [data, setData] = React.useState<OverviewResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  React.useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getOverview(controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setData(response);
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) return;
        if (fetchError instanceof ApiError && fetchError.status === 401) {
          setError("Your session expired. Please log in again.");
        } else if (fetchError instanceof Error) {
          setError(`Unable to load business overview: ${fetchError.message}`);
        } else {
          setError("Unable to load business overview.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [attempt]);

  const retry = React.useCallback(() => setAttempt((count) => count + 1), []);
  return { data, loading, error, retry };
}
