"use client";

import * as React from "react";
import { ApiError } from "@/lib/api";
import type { AIAnswer } from "@/types";

export type AIStatus = "idle" | "loading" | "success" | "error";

export interface AIState {
  status: AIStatus;
  answer: AIAnswer | null;
  error: string | null;
  run: () => void;
  reset: () => void;
}

function friendlyError(fetchError: unknown): string {
  if (fetchError instanceof ApiError && fetchError.status === 401) {
    return "Your session expired. Please log in again.";
  }
  if (fetchError instanceof ApiError && fetchError.status === 503) {
    return fetchError.message;
  }
  if (fetchError instanceof ApiError && fetchError.status === 404) {
    return "The referenced record no longer exists.";
  }
  if (fetchError instanceof Error) {
    return `Request failed: ${fetchError.message}`;
  }
  return "Request failed.";
}

/**
 * One-shot AI operation lifecycle. Starts idle — the user explicitly
 * triggers generation — then loading / success / error with retry.
 */
export function useAiOperation(
  operation: (signal: AbortSignal) => Promise<AIAnswer>,
  key: string,
): AIState {
  const [status, setStatus] = React.useState<AIStatus>("idle");
  const [answer, setAnswer] = React.useState<AIAnswer | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  const [running, setRunning] = React.useState(false);

  React.useEffect(() => {
    if (!running) return;
    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    operation(controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setAnswer(response);
        setStatus("success");
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) return;
        setError(friendlyError(fetchError));
        setStatus("error");
      })
      .finally(() => {
        if (!controller.signal.aborted) setRunning(false);
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, attempt, key]);

  const run = React.useCallback(() => {
    setRunning(true);
    setAttempt((count) => count + 1);
  }, []);
  const reset = React.useCallback(() => {
    setStatus("idle");
    setAnswer(null);
    setError(null);
  }, []);
  return { status, answer, error, run, reset };
}
