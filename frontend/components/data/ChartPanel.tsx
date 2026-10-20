import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { DataState } from "./DataState";
import { cn } from "@/lib/utils";

export interface ChartPanelProps {
  title: string;
  description?: string;
  summary?: string;
  actions?: React.ReactNode;
  height?: number | string;
  loading?: boolean;
  error?: unknown;
  empty?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
  onRetry?: () => void;
  className?: string;
  children?: React.ReactNode;
}

/**
 * Reusable, accessible container for analytical charts and visualizations.
 * Wraps Recharts components with standardized headers, summaries, and data states.
 */
export function ChartPanel({
  title,
  description,
  summary,
  actions,
  height = 320,
  loading = false,
  error,
  empty = false,
  emptyTitle,
  emptyMessage,
  onRetry,
  className,
  children,
}: ChartPanelProps) {
  const heightStyle = typeof height === "number" ? `${height}px` : height;

  return (
    <Card className={cn("flex flex-col justify-between", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-4 pb-3">
        <div className="space-y-1">
          <CardTitle as="h3" className="text-sm font-semibold tracking-tight text-foreground">
            {title}
          </CardTitle>
          {description && (
            <CardDescription className="text-xs text-muted-foreground leading-normal">
              {description}
            </CardDescription>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </CardHeader>

      <CardContent className="pt-0 flex-1 flex flex-col justify-center">
        {summary && (
          <div
            className="mb-3 px-2.5 py-1.5 rounded bg-muted/50 border border-border/60 text-[11px] text-muted-foreground leading-relaxed"
            data-testid="chart-summary"
          >
            <span className="font-semibold text-foreground mr-1">Summary:</span>
            {summary}
          </div>
        )}

        <DataState
          loading={loading}
          error={error}
          empty={empty}
          emptyTitle={emptyTitle}
          emptyMessage={emptyMessage}
          onRetry={onRetry}
          minHeight={`min-h-[${heightStyle}]`}
        >
          <div
            className="w-full relative"
            style={{ minHeight: heightStyle, height: heightStyle }}
          >
            {children}
          </div>
        </DataState>
      </CardContent>
    </Card>
  );
}
