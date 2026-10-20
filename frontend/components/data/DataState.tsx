import React from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface DataStateProps {
  loading?: boolean;
  error?: unknown;
  empty?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
  emptyAction?: React.ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  loadingMessage?: string;
  minHeight?: string;
  className?: string;
  children?: React.ReactNode;
}

/**
 * Sanitize error message to ensure no secrets, internal URLs, or stack traces are displayed.
 */
function sanitizeErrorMessage(error: unknown): { code?: string; message: string } {
  if (!error) {
    return { message: "An unexpected error occurred." };
  }

  // Handle ApiError or structured backend errors
  if (typeof error === "object" && error !== null) {
    const errObj = error as { code?: string; message?: string; status?: number };
    let msg = errObj.message || "An error occurred while loading data.";
    const code = errObj.code;

    // Redact internal endpoints or credential leaks if present in message
    if (
      msg.includes("localhost") ||
      msg.includes("127.0.0.1") ||
      msg.includes("INTERNAL_API_KEY") ||
      msg.includes("secret") ||
      msg.includes("Traceback")
    ) {
      msg = "A communication error occurred with the analytics service.";
    }

    return { code, message: msg };
  }

  if (typeof error === "string") {
    return { message: error };
  }

  return { message: "Unable to complete request. Please try again." };
}

/**
 * Reusable, accessible component representing loading, error, empty, and ready data states.
 */
export function DataState({
  loading = false,
  error,
  empty = false,
  emptyTitle = "No data available",
  emptyMessage = "There are no complaints or metrics matching the current criteria.",
  emptyAction,
  onRetry,
  retryLabel = "Try Again",
  loadingMessage = "Loading analytics...",
  minHeight = "min-h-[200px]",
  className,
  children,
}: DataStateProps) {
  // 1. Loading state
  if (loading) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-6 space-y-3 text-center",
          minHeight,
          className
        )}
        role="status"
        aria-live="polite"
      >
        <div className="w-full max-w-md space-y-2.5">
          <Skeleton className="h-6 w-3/4 mx-auto" />
          <Skeleton className="h-4 w-1/2 mx-auto" />
          <Skeleton className="h-20 w-full" />
        </div>
        <span className="text-xs text-muted-foreground animate-pulse mt-2">
          {loadingMessage}
        </span>
      </div>
    );
  }

  // 2. Error state
  if (error) {
    const { code, message } = sanitizeErrorMessage(error);

    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-6 text-center rounded-lg border border-status-error/30 bg-status-error-soft/30 space-y-3",
          minHeight,
          className
        )}
        role="alert"
      >
        <div className="p-2.5 rounded-full bg-status-error/10 text-status-error">
          <AlertTriangle className="w-5 h-5" aria-hidden="true" />
        </div>
        <div className="space-y-1 max-w-md">
          {code && (
            <span className="inline-block px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider rounded bg-status-error/15 text-status-error mb-1">
              {code}
            </span>
          )}
          <h3 className="text-sm font-semibold text-foreground">
            Error loading data
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {message}
          </p>
        </div>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="mt-2 text-xs gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{retryLabel}</span>
          </Button>
        )}
      </div>
    );
  }

  // 3. Empty state
  if (empty) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-6 text-center rounded-lg border border-dashed border-border bg-card/50 space-y-3",
          minHeight,
          className
        )}
      >
        <div className="p-2.5 rounded-full bg-muted text-muted-foreground">
          <Inbox className="w-5 h-5" aria-hidden="true" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h3 className="text-sm font-medium text-foreground">{emptyTitle}</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {emptyMessage}
          </p>
        </div>
        {emptyAction && <div className="pt-1">{emptyAction}</div>}
      </div>
    );
  }

  // 4. Ready / Content state
  return <>{children}</>;
}
