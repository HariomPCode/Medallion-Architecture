"use client";

import React, { useState } from "react";
import { ChartPanel } from "@/components/data/ChartPanel";
import { Button } from "@/components/ui/button";
import { Table2, BarChart2 } from "lucide-react";
import { formatNumber, formatPercent } from "@/lib/format";
import { getCategoryColor } from "@/lib/colors";
import { useTheme } from "@/components/theme-provider";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";

export interface CategoryBarItem {
  category: string;
  sub_category?: string | null;
  total: number;
  share_pct: number | null;
  timely_rate: number | null;
}

export interface CategoryBarProps {
  data: CategoryBarItem[];
  title?: string;
  description?: string;
  summary?: string;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  onItemClick?: (item: CategoryBarItem) => void;
  className?: string;
}

/**
 * Horizontal Category / Sub-Category Volume Bar Chart with integrated "View as table" toggle.
 * Follows the authoritative Financial Editorial category palette.
 */
export function CategoryBar({
  data,
  title = "Complaints by Category",
  description = "Volume and market share across CFPB product categories",
  summary,
  loading = false,
  error,
  onRetry,
  onItemClick,
  className,
}: CategoryBarProps) {
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const { theme } = useTheme();

  // Compute dynamic summary if not supplied
  const effectiveSummary =
    summary ||
    (data.length > 0
      ? `${data[0].category} accounts for the highest volume with ${formatNumber(
          data[0].total
        )} complaints (${formatPercent(data[0].share_pct, 1)}).`
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
          <BarChart2 className="w-3.5 h-3.5" aria-hidden="true" />
          <span>View as chart</span>
        </>
      )}
    </Button>
  );

  return (
    <ChartPanel
      data-testid="category-bar-panel"
      title={title}
      description={description}
      summary={effectiveSummary}
      actions={toggleAction}
      loading={loading}
      error={error}
      empty={data.length === 0}
      emptyTitle="No category complaints"
      emptyMessage="No complaints match the current filter selection."
      onRetry={onRetry}
      className={className}
      height={viewMode === "chart" ? Math.max(260, data.length * 44) : "auto"}
    >
      {viewMode === "chart" ? (
        <div
          className="w-full h-full min-h-[240px]"
          data-testid="category-bar-chart"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 8, right: 36, left: 10, bottom: 8 }}
            >
              <XAxis
                type="number"
                tickFormatter={(v) => formatNumber(v)}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="category"
                width={120}
                tick={{
                  fontSize: 11,
                  fill: "hsl(var(--foreground))",
                  fontWeight: 500,
                }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const item = payload[0].payload as CategoryBarItem;
                    return (
                      <div className="rounded-md border border-border bg-card p-2.5 shadow-md text-xs space-y-1">
                        <p className="font-semibold text-foreground">
                          {item.sub_category || item.category}
                        </p>
                        <p className="text-muted-foreground">
                          Complaints:{" "}
                          <span className="font-mono font-medium text-foreground">
                            {formatNumber(item.total)}
                          </span>
                        </p>
                        <p className="text-muted-foreground">
                          Share:{" "}
                          <span className="font-mono font-medium text-foreground">
                            {formatPercent(item.share_pct, 1)}
                          </span>
                        </p>
                        {item.timely_rate != null && (
                          <p className="text-muted-foreground">
                            Timely Rate:{" "}
                            <span className="font-mono font-medium text-status-success">
                              {formatPercent(item.timely_rate, 1)}
                            </span>
                          </p>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar
                dataKey="total"
                radius={[0, 4, 4, 0]}
                cursor={onItemClick ? "pointer" : "default"}
                onClick={(entry) => onItemClick?.(entry as unknown as CategoryBarItem)}
              >
                {data.map((entry) => (
                  <Cell
                    key={entry.sub_category || entry.category}
                    fill={getCategoryColor(entry.category, theme as "light" | "dark")}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        /* Accessible Table Alternative */
        <div
          className="w-full overflow-x-auto rounded border border-border bg-card"
          data-testid="category-bar-table"
        >
          <table className="w-full text-xs text-left border-collapse" role="table">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
              <tr>
                <th scope="col" className="px-3 py-2 text-left">
                  Category
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Volume
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Share
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Timely Rate
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {data.map((item) => (
                <tr
                  key={item.sub_category || item.category}
                  className="hover:bg-muted/40 transition-colors cursor-pointer"
                  onClick={() => onItemClick?.(item)}
                >
                  <td className="px-3 py-2 text-foreground font-medium flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{
                        backgroundColor: getCategoryColor(
                          item.category,
                          theme as "light" | "dark"
                        ),
                      }}
                      aria-hidden="true"
                    />
                    <span>{item.sub_category || item.category}</span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-foreground">
                    {formatNumber(item.total)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-foreground">
                    {formatPercent(item.share_pct, 1)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-foreground">
                    {formatPercent(item.timely_rate, 1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartPanel>
  );
}
