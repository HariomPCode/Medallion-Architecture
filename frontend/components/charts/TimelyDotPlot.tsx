"use client";

import React, { useState } from "react";
import { ChartPanel } from "@/components/data/ChartPanel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table2, Dot, Info } from "lucide-react";
import { formatNumber, formatPercent } from "@/lib/format";
import { getCategoryColor } from "@/lib/colors";
import { useTheme } from "@/components/theme-provider";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

export interface TimelyItem {
  category: string;
  sub_category?: string | null;
  total: number;
  timely_yes: number;
  timely_no: number;
  timely_unknown: number;
  timely_rate: number | null;
  timely_rate_all_cases: number | null;
}

export interface TimelyDotPlotProps {
  data: TimelyItem[];
  title?: string;
  description?: string;
  summary?: string;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  className?: string;
}

/**
 * Timely Response Rate Dot Plot by Sub-Category.
 * Visualizes compliance against the 95% regulatory threshold with complete denominator clarity.
 */
export function TimelyDotPlot({
  data,
  title = "Timely Response Compliance by Sub-Category",
  description = "Primary rate (Yes / Rated Cases) with explicit denominators and in-progress case isolation",
  summary,
  loading = false,
  error,
  onRetry,
  className,
}: TimelyDotPlotProps) {
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const { theme } = useTheme();

  // Sort sub-categories by timely_rate ascending to highlight lowest compliance at the top
  const sortedData = React.useMemo(() => {
    return [...data].sort((a, b) => (a.timely_rate ?? 0) - (b.timely_rate ?? 0));
  }, [data]);

  // Transform for ScatterChart: y-axis is index or name
  const scatterData = React.useMemo(() => {
    return sortedData.map((item, idx) => ({
      yIndex: idx,
      name: item.sub_category || item.category,
      category: item.category,
      rate: item.timely_rate ?? 0,
      total: item.total,
      yes: item.timely_yes,
      no: item.timely_no,
      unknown: item.timely_unknown,
      denominator: item.timely_yes + item.timely_no,
      legacyRate: item.timely_rate_all_cases,
    }));
  }, [sortedData]);

  const effectiveSummary =
    summary ||
    (sortedData.length > 0
      ? `Sub-category timely response rates range from ${formatPercent(
          sortedData[0]?.timely_rate,
          1
        )} (${sortedData[0]?.sub_category || sortedData[0]?.category}) to ${formatPercent(
          sortedData[sortedData.length - 1]?.timely_rate,
          1
        )} (${sortedData[sortedData.length - 1]?.sub_category || sortedData[sortedData.length - 1]?.category}).`
      : undefined);

  const toggleAction = (
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
          <Dot className="w-3.5 h-3.5" aria-hidden="true" />
          <span>View as chart</span>
        </>
      )}
    </Button>
  );

  return (
    <ChartPanel
      data-testid="timely-dot-plot-panel"
      title={title}
      description={description}
      summary={effectiveSummary}
      actions={toggleAction}
      loading={loading}
      error={error}
      empty={data.length === 0}
      emptyTitle="No compliance data"
      emptyMessage="No sub-category records available for the active filters."
      onRetry={onRetry}
      className={className}
      height={viewMode === "chart" ? Math.max(300, sortedData.length * 36 + 60) : "auto"}
    >
      {viewMode === "chart" ? (
        <div className="w-full h-full flex flex-col justify-between" data-testid="timely-dot-plot">
          <div className="w-full flex-1 min-h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart
                margin={{ top: 12, right: 36, left: 20, bottom: 12 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  dataKey="rate"
                  domain={[88, 100]}
                  unit="%"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={150}
                  tick={{
                    fontSize: 11,
                    fill: "hsl(var(--foreground))",
                    fontWeight: 500,
                  }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickLine={false}
                />
                <ZAxis range={[70, 70]} />
                {/* 95% Target Line */}
                <ReferenceLine
                  x={95}
                  stroke="hsl(var(--accent))"
                  strokeDasharray="4 4"
                  label={{
                    value: "95% Target",
                    position: "insideTopRight",
                    fill: "hsl(var(--accent))",
                    fontSize: 10,
                  }}
                />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const item = payload[0].payload;
                      return (
                        <div className="rounded-md border border-border bg-card p-3 shadow-md text-xs space-y-1.5 min-w-[220px]">
                          <div className="border-b border-border pb-1">
                            <p className="font-semibold text-foreground">
                              {item.name}
                            </p>
                            <p className="text-[11px] text-muted-foreground">
                              Category: {item.category}
                            </p>
                          </div>
                          <div className="space-y-1 pt-0.5">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Primary Rate (M-03):</span>
                              <span className="font-mono font-bold text-status-success tabular-nums">
                                {formatPercent(item.rate, 1)}
                              </span>
                            </div>
                            <div className="flex justify-between text-[11px]">
                              <span className="text-muted-foreground">Rated Cases (Denom):</span>
                              <span className="font-mono tabular-nums text-foreground">
                                {formatNumber(item.denominator)}
                              </span>
                            </div>
                            <div className="flex justify-between text-[11px] pl-2 border-l border-border">
                              <span className="text-muted-foreground">Timely Yes:</span>
                              <span className="font-mono tabular-nums text-foreground">
                                {formatNumber(item.yes)}
                              </span>
                            </div>
                            <div className="flex justify-between text-[11px] pl-2 border-l border-border">
                              <span className="text-muted-foreground">Timely No:</span>
                              <span className="font-mono tabular-nums text-status-error">
                                {formatNumber(item.no)}
                              </span>
                            </div>
                            <div className="flex justify-between text-[11px] pt-1 border-t border-border/60">
                              <span className="text-muted-foreground">Pending (In Progress):</span>
                              <span className="font-mono tabular-nums text-status-warning">
                                {formatNumber(item.unknown)}
                              </span>
                            </div>
                            <div className="flex justify-between text-[11px] pt-1 text-muted-foreground">
                              <span>Legacy Rate (All Cases):</span>
                              <span className="font-mono tabular-nums">
                                {formatPercent(item.legacyRate, 1)}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter
                  data={scatterData}
                  fill="hsl(var(--accent))"
                  shape={(props: any) => {
                    const { cx, cy, payload } = props;
                    const catColor = getCategoryColor(
                      payload.category,
                      theme as "light" | "dark"
                    );
                    const meetsTarget = payload.rate >= 95;

                    return (
                      <g key={`scatter-dot-${cx}-${cy}`}>
                        <circle
                          cx={cx}
                          cy={cy}
                          r={6}
                          fill={catColor}
                          stroke={meetsTarget ? "hsl(var(--background))" : "hsl(var(--status-error))"}
                          strokeWidth={meetsTarget ? 1.5 : 2}
                        />
                      </g>
                    );
                  }}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground pt-1.5 px-1 border-t border-border/40">
            <Info className="w-3 h-3 text-muted-foreground shrink-0" aria-hidden="true" />
            <span>
              Truncated X-axis (88%–100%) expands variance. Primary rate excludes in-progress cases from the denominator.
            </span>
          </div>
        </div>
      ) : (
        /* Accessible Table Alternative */
        <div
          className="w-full overflow-x-auto rounded border border-border bg-card"
          data-testid="timely-dot-table"
        >
          <table className="w-full text-xs text-left border-collapse" role="table">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
              <tr>
                <th scope="col" className="px-3 py-2 text-left">
                  Sub-Category
                </th>
                <th scope="col" className="px-3 py-2 text-left">
                  Category
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Primary Rate (M-03)
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Rated Cases
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Timely Yes
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Timely No
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  In-Progress
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Legacy Rate (M-04)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {sortedData.map((item) => {
                const ratedCases = item.timely_yes + item.timely_no;
                const meetsTarget = (item.timely_rate ?? 0) >= 95;

                return (
                  <tr
                    key={item.sub_category || item.category}
                    className="hover:bg-muted/40 transition-colors"
                  >
                    <td className="px-3 py-2 text-foreground font-medium">
                      {item.sub_category || item.category}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full inline-block shrink-0"
                          style={{
                            backgroundColor: getCategoryColor(
                              item.category,
                              theme as "light" | "dark"
                            ),
                          }}
                        />
                        <span>{item.category}</span>
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums font-semibold">
                      <Badge
                        variant={meetsTarget ? "positive" : "warning"}
                        dot
                        className="font-mono text-xs"
                      >
                        {formatPercent(item.timely_rate, 1)}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-foreground">
                      {formatNumber(ratedCases)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-foreground">
                      {formatNumber(item.timely_yes)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-foreground">
                      {formatNumber(item.timely_no)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-muted-foreground">
                      {formatNumber(item.timely_unknown)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-muted-foreground">
                      {formatPercent(item.timely_rate_all_cases, 1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </ChartPanel>
  );
}
