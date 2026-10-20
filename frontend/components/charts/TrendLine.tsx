"use client";

import React, { useState, useMemo } from "react";
import { ChartPanel } from "@/components/data/ChartPanel";
import { Button } from "@/components/ui/button";
import { Table2, LineChart as LineChartIcon, Info } from "lucide-react";
import { formatNumber, formatSignedPercent } from "@/lib/format";
import { getCategoryColor } from "@/lib/colors";
import { useTheme } from "@/components/theme-provider";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

export interface TrendPoint {
  period: string;
  total: number;
  is_partial: boolean;
  yoy_change_pct: number | null;
}

export interface TrendSeries {
  key: string;
  points: TrendPoint[];
}

export interface TrendLineProps {
  series?: TrendSeries[];
  totalSeries?: TrendSeries;
  grain?: "year" | "month";
  onGrainChange?: (grain: "year" | "month") => void;
  title?: string;
  description?: string;
  summary?: string;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  showGrainToggle?: boolean;
  className?: string;
}

/**
 * Time-series Trend Visualization supporting yearly and monthly granularities.
 * Accurately highlights partial periods and provides an exact table alternative.
 */
export function TrendLine({
  series = [],
  totalSeries,
  grain = "year",
  onGrainChange,
  title = "Complaints Over Time",
  description = "Historical volume trajectory with data-driven partial-period indicators",
  summary,
  loading = false,
  error,
  onRetry,
  showGrainToggle = true,
  className,
}: TrendLineProps) {
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const { theme } = useTheme();

  // If totalSeries is present and series is empty or single, treat as primary
  const effectiveSeries = useMemo(() => {
    if (series && series.length > 0) return series;
    if (totalSeries) return [totalSeries];
    return [];
  }, [series, totalSeries]);

  // Combine points across series into a unified time-indexed dataset for Recharts
  const chartData = useMemo(() => {
    if (effectiveSeries.length === 0) return [];

    // Collect all unique periods preserving chronological order
    const periodMap = new Map<string, Record<string, unknown>>();

    effectiveSeries.forEach((s) => {
      s.points.forEach((pt) => {
        if (!periodMap.has(pt.period)) {
          periodMap.set(pt.period, {
            period: pt.period,
            is_partial: pt.is_partial,
            yoy_change_pct: pt.yoy_change_pct,
          });
        }
        const entry = periodMap.get(pt.period)!;
        entry[s.key] = pt.total;
        if (s.key === "Total") {
          entry.total = pt.total;
        }
      });
    });

    return Array.from(periodMap.values());
  }, [effectiveSeries]);

  // Determine if any partial periods are in the dataset
  const hasPartialPeriods = useMemo(() => {
    return chartData.some((d) => d.is_partial === true);
  }, [chartData]);

  // Summary generation
  const effectiveSummary =
    summary ||
    (chartData.length >= 2
      ? `Trends span ${chartData[0].period} through ${
          chartData[chartData.length - 1].period
        }. ${
          hasPartialPeriods
            ? "2017 (starts May 1) and 2023 (ends Aug 28) represent partial coverage."
            : ""
        }`
      : undefined);

  // Actions: Grain toggle and Table/Chart switcher
  const actions = (
    <div className="flex items-center gap-2">
      {showGrainToggle && onGrainChange && (
        <div
          role="group"
          aria-label="Select trend grain"
          className="flex items-center rounded-md border border-border p-0.5 bg-muted/40"
        >
          <button
            type="button"
            onClick={() => onGrainChange("year")}
            aria-pressed={grain === "year"}
            aria-label="Yearly grain"
            className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
              grain === "year"
                ? "bg-card text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Year
          </button>
          <button
            type="button"
            onClick={() => onGrainChange("month")}
            aria-pressed={grain === "month"}
            aria-label="Monthly grain"
            className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
              grain === "month"
                ? "bg-card text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Month
          </button>
        </div>
      )}

      <Button
        variant="outline"
        size="sm"
        onClick={() => setViewMode((m) => (m === "chart" ? "table" : "chart"))}
        className="text-xs h-7 gap-1.5"
        aria-label={viewMode === "chart" ? "Switch to table view" : "Switch to chart view"}
      >
        {viewMode === "chart" ? (
          <>
            <Table2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span>View as table</span>
          </>
        ) : (
          <>
            <LineChartIcon className="w-3.5 h-3.5" aria-hidden="true" />
            <span>View as chart</span>
          </>
        )}
      </Button>
    </div>
  );

  return (
    <ChartPanel
      data-testid="trend-line-panel"
      title={title}
      description={description}
      summary={effectiveSummary}
      actions={actions}
      loading={loading}
      error={error}
      empty={chartData.length === 0}
      emptyTitle="No trend data"
      emptyMessage="No time-series data matching active filters."
      onRetry={onRetry}
      className={className}
      height={320}
    >
      {viewMode === "chart" ? (
        <div className="w-full h-full flex flex-col justify-between" data-testid="trend-line-chart">
          <div className="w-full flex-1 min-h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 12, right: 24, left: 10, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  vertical={false}
                />
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => formatNumber(v)}
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickLine={false}
                  width={60}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const isPartial = payload[0].payload.is_partial;
                      const yoy = payload[0].payload.yoy_change_pct;

                      return (
                        <div className="rounded-md border border-border bg-card p-2.5 shadow-md text-xs space-y-1.5">
                          <div className="flex items-center justify-between gap-2 border-b border-border pb-1">
                            <span className="font-semibold text-foreground">
                              {label}
                            </span>
                            {isPartial && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-status-warning-soft text-status-warning border border-status-warning/30 font-medium">
                                Partial Period
                              </span>
                            )}
                          </div>
                          {payload.map((entry) => (
                            <div
                              key={entry.name}
                              className="flex items-center justify-between gap-4 text-xs"
                            >
                              <span
                                className="flex items-center gap-1.5 text-muted-foreground"
                                style={{ color: entry.color }}
                              >
                                <span
                                  className="w-2 h-2 rounded-full inline-block"
                                  style={{ backgroundColor: entry.color }}
                                />
                                {entry.name}:
                              </span>
                              <span className="font-mono font-medium text-foreground tabular-nums">
                                {formatNumber(entry.value)}
                              </span>
                            </div>
                          ))}
                          {yoy != null && !isPartial && (
                            <p className="pt-1 text-[11px] text-muted-foreground border-t border-border">
                              YoY Change:{" "}
                              <span
                                className={`font-mono font-medium tabular-nums ${
                                  yoy > 0
                                    ? "text-status-success"
                                    : yoy < 0
                                    ? "text-status-error"
                                    : "text-foreground"
                                }`}
                              >
                                {formatSignedPercent(yoy, 1)}
                              </span>
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {effectiveSeries.length > 1 && (
                  <Legend
                    wrapperStyle={{ fontSize: 11, paddingTop: 6 }}
                    iconType="circle"
                  />
                )}
                {effectiveSeries.map((s) => {
                  const color =
                    s.key === "Total"
                      ? "hsl(var(--accent))"
                      : getCategoryColor(s.key, theme as "light" | "dark");

                  return (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      name={s.key}
                      stroke={color}
                      strokeWidth={2}
                      dot={(props: any) => {
                        const isPartial = props.payload.is_partial;
                        return (
                          <circle
                            key={`dot-${props.cx}-${props.cy}`}
                            cx={props.cx}
                            cy={props.cy}
                            r={isPartial ? 4 : 3}
                            fill={isPartial ? "hsl(var(--background))" : color}
                            stroke={color}
                            strokeWidth={isPartial ? 2 : 1}
                            strokeDasharray={isPartial ? "2 2" : "0"}
                          />
                        );
                      }}
                      activeDot={{ r: 5 }}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {hasPartialPeriods && (
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground pt-1 px-1">
              <Info className="w-3 h-3 text-status-warning shrink-0" aria-hidden="true" />
              <span>
                2017 (starts May 1) and 2023 (ends Aug 28) are partial periods (dashed markers).
              </span>
            </div>
          )}
        </div>
      ) : (
        /* Accessible Table Alternative */
        <div
          className="w-full overflow-x-auto rounded border border-border bg-card"
          data-testid="trend-line-table"
        >
          <table className="w-full text-xs text-left border-collapse" role="table">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
              <tr>
                <th scope="col" className="px-3 py-2 text-left">
                  Period
                </th>
                <th scope="col" className="px-3 py-2 text-left">
                  Status
                </th>
                {effectiveSeries.map((s) => (
                  <th key={s.key} scope="col" className="px-3 py-2 text-right">
                    {s.key}
                  </th>
                ))}
                {effectiveSeries.length === 1 && (
                  <th scope="col" className="px-3 py-2 text-right">
                    YoY Change
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {chartData.map((row) => (
                <tr key={String(row.period)} className="hover:bg-muted/40 transition-colors">
                  <td className="px-3 py-2 text-foreground font-medium font-mono">
                    {String(row.period)}
                  </td>
                  <td className="px-3 py-2">
                    {row.is_partial ? (
                      <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-status-warning-soft text-status-warning border border-status-warning/30">
                        Partial Period
                      </span>
                    ) : (
                      <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-status-success-soft text-status-success border border-status-success/30">
                        Complete
                      </span>
                    )}
                  </td>
                  {effectiveSeries.map((s) => (
                    <td
                      key={s.key}
                      className="px-3 py-2 text-right font-mono tabular-nums text-foreground"
                    >
                      {formatNumber(row[s.key])}
                    </td>
                  ))}
                  {effectiveSeries.length === 1 && (
                    <td className="px-3 py-2 text-right font-mono tabular-nums">
                      {row.is_partial ? (
                        <span className="text-muted-foreground font-normal italic">
                          Excluded (Partial)
                        </span>
                      ) : row.yoy_change_pct != null ? (
                        <span
                          className={
                            Number(row.yoy_change_pct) > 0
                              ? "text-status-success"
                              : Number(row.yoy_change_pct) < 0
                              ? "text-status-error"
                              : "text-foreground"
                          }
                        >
                          {formatSignedPercent(row.yoy_change_pct, 1)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartPanel>
  );
}
