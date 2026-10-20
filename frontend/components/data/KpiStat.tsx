import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export type TrendDirection = "up" | "down" | "flat";
export type TrendSentiment = "positive" | "negative" | "neutral";

export interface KpiTrend {
  value: number | string;
  direction?: TrendDirection;
  sentiment?: TrendSentiment;
  label?: string;
  accessibleText?: string;
}

export interface KpiStatProps {
  label: string;
  value?: string | number | null;
  unit?: string;
  description?: string;
  trend?: KpiTrend;
  loading?: boolean;
  emptyFallback?: string;
  className?: string;
  badge?: React.ReactNode;
  as?: "h2" | "h3" | "div";
}

/**
 * Format a raw value for KPI presentation.
 * Returns deterministic fallback for null/undefined/empty string.
 * Retains zero as "0".
 */
function renderValue(value: string | number | null | undefined, fallback: string): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

/**
 * Reusable, accessible KPI display component following Financial Editorial design tokens.
 */
export function KpiStat({
  label,
  value,
  unit,
  description,
  trend,
  loading = false,
  emptyFallback = "—",
  className,
  badge,
  as = "h3",
}: KpiStatProps) {
  const HeadingTag = as;

  if (loading) {
    return (
      <Card
        className={cn("p-4 space-y-2", className)}
        aria-busy="true"
        data-testid="kpi-stat-loading"
      >
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-12" />
        </div>
        <Skeleton className="h-8 w-32" />
        {description && <Skeleton className="h-3 w-40" />}
      </Card>
    );
  }

  const displayValue = renderValue(value, emptyFallback);

  // Derive trend sentiment classes
  const sentiment = trend?.sentiment || (
    trend?.direction === "up" ? "positive" :
    trend?.direction === "down" ? "negative" : "neutral"
  );

  const trendColorClass =
    sentiment === "positive"
      ? "text-status-success bg-status-success-soft/70 border-status-success/30"
      : sentiment === "negative"
      ? "text-status-error bg-status-error-soft/70 border-status-error/30"
      : "text-muted-foreground bg-muted border-border";

  const TrendIcon =
    trend?.direction === "up"
      ? TrendingUp
      : trend?.direction === "down"
      ? TrendingDown
      : Minus;

  const accessibleTrend =
    trend?.accessibleText ||
    (trend
      ? `Trend: ${trend.direction || "change"} ${trend.value}${
          trend.label ? ` ${trend.label}` : ""
        }`
      : undefined);

  return (
    <Card className={cn("p-4 flex flex-col justify-between transition-colors", className)}>
      <CardContent className="p-0 space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <HeadingTag className="text-xs font-medium uppercase tracking-wider text-muted-foreground truncate">
            {label}
          </HeadingTag>
          {badge}
        </div>

        <div className="flex items-baseline gap-1.5 pt-0.5">
          <span
            className="text-2xl font-bold font-mono tracking-tight text-foreground tabular-nums"
            data-testid="kpi-value"
          >
            {displayValue}
          </span>
          {unit && (
            <span className="text-xs font-medium text-muted-foreground">{unit}</span>
          )}
        </div>

        {(trend || description) && (
          <div className="flex items-center flex-wrap gap-2 pt-1 text-xs text-muted-foreground">
            {trend && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border tabular-nums",
                  trendColorClass
                )}
                aria-label={accessibleTrend}
              >
                <TrendIcon className="w-3 h-3 shrink-0" aria-hidden="true" />
                <span>{trend.value}</span>
                {trend.label && (
                  <span className="text-muted-foreground font-normal ml-0.5">
                    {trend.label}
                  </span>
                )}
              </span>
            )}
            {description && (
              <span className="text-[11px] text-muted-foreground leading-tight">
                {description}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
