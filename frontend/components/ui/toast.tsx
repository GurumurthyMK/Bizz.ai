"use client";

import * as React from "react";
import { CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastTone = "default" | "success" | "warning" | "danger" | "info";

export interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone?: ToastTone;
}

type ToastInput = Omit<ToastItem, "id">;
type Listener = (toast: ToastInput) => void;

const listeners = new Set<Listener>();

/** Imperative helper usable outside React components. */
function toast(input: ToastInput) {
  listeners.forEach((listener) => listener(input));
}

let nextId = 1;

function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const dismiss = React.useCallback((id: number) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const push = React.useCallback(
    (input: ToastInput) => {
      const id = nextId++;
      setToasts((current) => [...current.slice(-3), { ...input, id }]);
      window.setTimeout(() => dismiss(id), 5000);
    },
    [dismiss]
  );

  React.useEffect(() => {
    listeners.add(push);
    return () => {
      listeners.delete(push);
    };
  }, [push]);

  const value = React.useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

const ToastContext = React.createContext<{
  toasts: ToastItem[];
  push: (toast: ToastInput) => void;
  dismiss: (id: number) => void;
} | null>(null);

function useToast() {
  const store = React.useContext(ToastContext);
  if (store == null) throw new Error("useToast must be used within ToastProvider");
  return store;
}

const toneIcon = {
  success: CheckCircle2,
  warning: TriangleAlert,
  danger: XCircle,
  info: Info,
} as const;

function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2"
    >
      {toasts.map((item) => {
        const Icon = item.tone != null && item.tone !== "default" ? toneIcon[item.tone] : null;
        return (
          <div
            key={item.id}
            role="status"
            className="pointer-events-auto flex items-start gap-2 rounded-lg border bg-card p-3 shadow-sm"
          >
            {Icon != null && (
              <Icon
                aria-hidden="true"
                className={cn(
                  "mt-0.5 size-4 shrink-0",
                  item.tone === "success" && "text-success",
                  item.tone === "warning" && "text-warning",
                  item.tone === "danger" && "text-danger",
                  item.tone === "info" && "text-info"
                )}
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{item.title}</p>
              {item.description != null && (
                <p className="mt-0.5 text-dense text-muted-foreground">{item.description}</p>
              )}
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => dismiss(item.id)}
              className="rounded-sm p-0.5 text-muted-foreground hover:bg-muted"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

export { ToastProvider, useToast, toast, Toaster };
