"use client";

import * as React from "react";
import { ApiError } from "@/lib/api";

export interface ResourceState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

/** Single-resource fetch lifecycle (detail pages). */
export function useResource<T>(
  resource: string,
  load: (signal: AbortSignal) => Promise<T>,
  key: string,
): ResourceState<T> {
  const [data, setData] = React.useState<T | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  React.useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    load(controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setData(response);
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) return;
        if (fetchError instanceof ApiError && fetchError.status === 401) {
          setError("Your session expired. Please log in again.");
        } else if (fetchError instanceof ApiError && fetchError.status === 404) {
          setError("This record does not exist or was removed.");
        } else if (fetchError instanceof Error) {
          setError(`Unable to load ${resource}: ${fetchError.message}`);
        } else {
          setError(`Unable to load ${resource}.`);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  const retry = React.useCallback(() => setAttempt((count) => count + 1), []);
  return { data, loading, error, retry };
}
