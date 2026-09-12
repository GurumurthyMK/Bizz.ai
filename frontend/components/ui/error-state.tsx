import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description: string;
  onRetry?: () => void;
}

/**
 * Understandable error with retry (Design.md §28).
 * Never exposes raw stack traces.
 */
function ErrorState({ title, description, onRetry, className, ...props }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-2 rounded-lg border px-6 py-10 text-center",
        className
      )}
      {...props}
    >
      <span className="flex size-10 items-center justify-center rounded-md bg-danger/10">
        <TriangleAlert className="size-5 text-danger" aria-hidden="true" />
      </span>
      <h3 className="text-section-title">{title}</h3>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {onRetry != null && (
        <Button type="button" variant="secondary" size="sm" className="mt-2" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export { ErrorState };
