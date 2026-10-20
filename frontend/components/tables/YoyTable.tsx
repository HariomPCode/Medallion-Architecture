"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { DataState } from "@/components/data/DataState";
import { TrendingUp, TrendingDown, Minus, Info, AlertTriangle } from "lucide-react";
import { formatNumber, formatSignedPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface YoyPoint {
  period: string;
  total: number;
  is_partial: boolean;
  yoy_change_pct: number | null;
}

export interface YoyTableProps {
  data: YoyPoint[];
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  className?: string;
}

/**
 * Year-over-Year Comparative Analysis Table.
 * Strictly adheres to AC-8.4: Never computes or displays a YoY percentage for partial periods.
 */
export function YoyTable({
  data,
  loading = false,
  error,
  onRetry,
  className,
}: YoyTableProps) {
  if (error) {
    return <DataState error={error} onRetry={onRetry} />;
  }

  // Sort periods chronologically
  const sortedData = [...data].sort((a, b) => a.period.localeCompare(b.period));

  return (
    <div className={cn("space-y-3 w-full", className)}>
      <div className="flex items-center justify-between gap-2 px-1">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Year-over-Year Volume Growth
        </h2>
        <span className="text-xs text-muted-foreground">
          Complete Periods Only (2018–2022)
        </span>
      </div>

      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table
            className="w-full text-xs text-left border-collapse"
            role="table"
            aria-label="Year-over-Year volume growth table"
          >
            <thead className="bg-muted/60 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
              <tr>
                <th scope="col" className="px-3.5 py-2.5 text-left">
                  Period
                </th>
                <th scope="col" className="px-3.5 py-2.5 text-left">
                  Period Completeness
                </th>
                <th scope="col" className="px-3.5 py-2.5 text-right">
                  Complaint Volume
                </th>
                <th scope="col" className="px-3.5 py-2.5 text-right">
                  YoY Change
                </th>
                <th scope="col" className="px-3.5 py-2.5 text-left">
                  Comparison Policy
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-border/60">
              {loading ? (
                Array.from({ length: 5 }).map((_, rIdx) => (
                  <tr key={`loading-yoy-${rIdx}`}>
                    <td colSpan={5} className="px-3.5 py-3">
                      <div className="h-4 bg-muted/60 animate-pulse rounded w-full" />
                    </td>
                  </tr>
                ))
              ) : sortedData.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3.5 py-8 text-center text-muted-foreground">
                    No yearly trend data available.
                  </td>
                </tr>
              ) : (
                sortedData.map((row) => {
                  const isPartial = row.is_partial;
                  const yoy = row.yoy_change_pct;

                  return (
                    <tr key={row.period} className="hover:bg-muted/40 transition-colors">
                      <td className="px-3.5 py-2.5 font-mono font-medium text-foreground">
                        {row.period}
                      </td>

                      <td className="px-3.5 py-2.5">
                        {isPartial ? (
                          <Badge variant="warning" dot className="text-xs font-normal">
                            Partial Period
                          </Badge>
                        ) : (
                          <Badge variant="positive" dot className="text-xs font-normal">
                            Complete (12 Months)
                          </Badge>
                        )}
                      </td>

                      <td className="px-3.5 py-2.5 text-right font-mono tabular-nums text-foreground font-medium">
                        {formatNumber(row.total)}
                      </td>

                      <td className="px-3.5 py-2.5 text-right font-mono tabular-nums">
                        {isPartial ? (
                          // Enforces AC-8.4: Never display a YoY percentage for partial periods
                          <span className="text-muted-foreground font-normal italic">
                            Excluded (Partial)
                          </span>
                        ) : yoy != null ? (
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 font-semibold",
                              yoy > 0
                                ? "text-status-success"
                                : yoy < 0
                                ? "text-status-error"
                                : "text-foreground"
                            )}
                          >
                            {yoy > 0 ? (
                              <TrendingUp className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                            ) : yoy < 0 ? (
                              <TrendingDown className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                            ) : (
                              <Minus className="w-3.5 h-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                            )}
                            <span>{formatSignedPercent(yoy, 1)}</span>
                          </span>
                        ) : (
                          // Base year (e.g. 2018) where previous year was partial
                          <span className="text-muted-foreground font-normal italic">
                            Baseline Year
                          </span>
                        )}
                      </td>

                      <td className="px-3.5 py-2.5 text-muted-foreground text-[11px]">
                        {row.period === "2017"
                          ? "Extraction begins 1 May 2017 (8 months)"
                          : row.period === "2018"
                          ? "First complete 12-month annual period"
                          : row.period === "2023"
                          ? "Extraction concludes 28 Aug 2023 (8 months)"
                          : "Full 12-month calendar year comparison"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mandatory Methodology & Exclusion Disclosure */}
      <div className="flex items-start gap-2 p-3 rounded-lg border border-border/80 bg-muted/30 text-xs text-muted-foreground leading-relaxed">
        <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <p className="font-semibold text-foreground">
            Year-over-Year Comparison Policy (AC-8.4)
          </p>
          <p className="mt-0.5">
            Annual YoY calculations are strictly computed across complete 12-month calendar years (2018–2022).
            Partial periods—2017 (May 1 to Dec 31) and 2023 (Jan 1 to Aug 28)—are marked as incomplete and excluded from percentage calculations to prevent misleading annualized growth rates.
          </p>
        </div>
      </div>
    </div>
  );
}
