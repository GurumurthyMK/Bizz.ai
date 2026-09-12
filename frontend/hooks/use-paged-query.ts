"use client";

import * as React from "react";
import { ApiError } from "@/lib/api";
import type { Page } from "@/types";

export interface PagedState<T> {
  items: T[];
  total: number;
  page: number;
  pageCount: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
  setPage: (page: number) => void;
  retry: () => void;
}

function friendlyError(fetchError: unknown, resource: string): string {
  if (fetchError instanceof ApiError && fetchError.status === 401) {
    return "Your session expired. Please log in again.";
  }
  if (fetchError instanceof Error) {
    return `Unable to load ${resource}: ${fetchError.message}`;
  }
  return `Unable to load ${resource}.`;
}

/**
 * Paged server-driven fetching. `load` receives the page and an abort
 * signal; `resetKey` resets to page 1 whenever filters/sorting change.
 */
export function usePagedQuery<T>(
  resource: string,
  load: (page: number, signal: AbortSignal) => Promise<Page<T>>,
  resetKey: string,
  pageSize = 20,
): PagedState<T> {
  const [page, setPage] = React.useState(1);
  const [data, setData] = React.useState<Page<T> | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  React.useEffect(() => {
    setPage(1);
  }, [resetKey]);

  React.useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    load(page, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setData(response);
      })
      .catch((fetchError: unknown) => {
        if (!controller.signal.aborted) setError(friendlyError(fetchError, resource));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, resetKey, attempt, load, resource]);

  const retry = React.useCallback(() => setAttempt((count) => count + 1), []);
  const total = data?.total ?? 0;
  return {
    items: data?.items ?? [],
    total,
    page,
    pageCount: Math.max(1, Math.ceil(total / pageSize)),
    pageSize,
    loading,
    error,
    setPage: React.useCallback(
      (next: number) => setPage(Math.min(Math.max(1, next), Math.max(1, Math.ceil(total / pageSize)))),
      [total, pageSize],
    ),
    retry,
  };
}
