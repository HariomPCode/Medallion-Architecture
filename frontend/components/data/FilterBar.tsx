import React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Filter, RotateCcw } from "lucide-react";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface FilterBarProps {
  children?: React.ReactNode;
  activeCount?: number;
  isFiltered?: boolean;
  onReset?: () => void;
  resetLabel?: string;
  label?: string;
  totalResults?: number | null;
  resultsLabel?: string;
  className?: string;
}

/**
 * Reusable, responsive container for composing analytical filter controls.
 * Integrates with existing URL filter synchronization without maintaining duplicate state.
 */
export function FilterBar({
  children,
  activeCount = 0,
  isFiltered = false,
  onReset,
  resetLabel = "Reset filters",
  label = "Filters",
  totalResults,
  resultsLabel = "complaints",
  className,
}: FilterBarProps) {
  const showReset = Boolean(onReset && (isFiltered || activeCount > 0));

  return (
    <div
      role="region"
      aria-label="Filter controls"
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-border bg-card/60 transition-colors",
        className
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground mr-1 shrink-0">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
          <span>{label}</span>
          {activeCount > 0 && (
            <Badge variant="neutral" className="ml-1 px-1.5 py-0 text-[10px] font-mono">
              {activeCount}
            </Badge>
          )}
        </div>

        {/* Composed filter items */}
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {children}
        </div>

        {/* Clear/Reset button */}
        {showReset && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="text-xs text-muted-foreground hover:text-foreground h-8 px-2.5 gap-1 shrink-0"
            aria-label={resetLabel}
          >
            <RotateCcw className="w-3 h-3" aria-hidden="true" />
            <span>{resetLabel}</span>
          </Button>
        )}
      </div>

      {/* Optional total results indicator */}
      {totalResults !== undefined && totalResults !== null && (
        <div className="text-xs text-muted-foreground tabular-nums shrink-0 font-medium pl-2 border-l border-border/60">
          <span className="font-mono font-semibold text-foreground">
            {formatNumber(totalResults)}
          </span>{" "}
          <span>{resultsLabel}</span>
        </div>
      )}
    </div>
  );
}
