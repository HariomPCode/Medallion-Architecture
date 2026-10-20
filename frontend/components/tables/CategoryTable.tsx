"use client";

import React, { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { DataState } from "@/components/data/DataState";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Info,
  Check,
  ChevronRight,
} from "lucide-react";
import { formatNumber, formatPercent } from "@/lib/format";
import { getCategoryColor } from "@/lib/colors";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

export interface CategoryTableItem {
  category: string;
  sub_category?: string | null;
  total: number;
  share_pct: number | null;
  timely_yes: number;
  timely_no: number;
  timely_unknown: number;
  timely_rate: number | null;
  timely_rate_all_cases: number | null;
}

export type SortField =
  | "name"
  | "total"
  | "share_pct"
  | "timely_rate"
  | "timely_rate_all_cases";

export interface CategoryTableProps {
  data: CategoryTableItem[];
  groupBy?: "category" | "sub_category";
  totalComplaints?: number;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  onRowClick?: (item: CategoryTableItem) => void;
  className?: string;
}

/**
 * Authoritative Category & Sub-Category Comparison Table.
 * Features column sorting, legacy rate toggle, interactive drill-down, and totals reconciliation.
 */
export function CategoryTable({
  data,
  groupBy = "category",
  totalComplaints,
  loading = false,
  error,
  onRetry,
  onRowClick,
  className,
}: CategoryTableProps) {
  const { theme } = useTheme();
  const [showLegacyRate, setShowLegacyRate] = useState(false);
  const [sortField, setSortField] = useState<SortField>("total");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => {
      let valA: string | number = 0;
      let valB: string | number = 0;

      switch (sortField) {
        case "name":
          valA = (a.sub_category || a.category).toLowerCase();
          valB = (b.sub_category || b.category).toLowerCase();
          return sortDir === "asc"
            ? (valA as string).localeCompare(valB as string)
            : (valB as string).localeCompare(valA as string);
        case "total":
          valA = a.total;
          valB = b.total;
          break;
        case "share_pct":
          valA = a.share_pct ?? 0;
          valB = b.share_pct ?? 0;
          break;
        case "timely_rate":
          valA = a.timely_rate ?? 0;
          valB = b.timely_rate ?? 0;
          break;
        case "timely_rate_all_cases":
          valA = a.timely_rate_all_cases ?? 0;
          valB = b.timely_rate_all_cases ?? 0;
          break;
      }

      return sortDir === "asc" ? Number(valA) - Number(valB) : Number(valB) - Number(valA);
    });
  }, [data, sortField, sortDir]);

  // Compute table totals
  const totals = useMemo(() => {
    const totalVol = data.reduce((acc, item) => acc + item.total, 0);
    const timelyYes = data.reduce((acc, item) => acc + item.timely_yes, 0);
    const timelyNo = data.reduce((acc, item) => acc + item.timely_no, 0);
    const timelyUnknown = data.reduce((acc, item) => acc + item.timely_unknown, 0);
    const ratedDenom = timelyYes + timelyNo;
    const overallRate = ratedDenom > 0 ? (timelyYes / ratedDenom) * 100 : null;
    const overallLegacyRate = totalVol > 0 ? (timelyYes / totalVol) * 100 : null;

    return {
      total: totalVol,
      timelyYes,
      timelyNo,
      timelyUnknown,
      ratedDenom,
      overallRate,
      overallLegacyRate,
    };
  }, [data]);

  const renderSortIndicator = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-muted-foreground/60 shrink-0" aria-hidden="true" />;
    }
    return sortDir === "asc" ? (
      <ArrowUp className="w-3 h-3 text-accent shrink-0" aria-hidden="true" />
    ) : (
      <ArrowDown className="w-3 h-3 text-accent shrink-0" aria-hidden="true" />
    );
  };

  if (error) {
    return <DataState error={error} onRetry={onRetry} />;
  }

  return (
    <div className={cn("space-y-3 w-full", className)}>
      {/* Table Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {groupBy === "category" ? "Categories" : "Sub-Categories"} Breakdown
          </h2>
          <span className="text-xs text-muted-foreground">
            ({data.length} {groupBy === "category" ? "categories" : "sub-categories"})
          </span>
        </div>

        {/* Legacy Rate Column Toggle */}
        <div className="flex items-center gap-2">
          <Tooltip content="Toggle display of secondary M-04 legacy rate dividing by all complaints">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowLegacyRate((prev) => !prev)}
              className={cn(
                "text-xs h-7 gap-1.5 transition-colors",
                showLegacyRate && "bg-muted font-medium text-foreground"
              )}
              aria-label="Toggle secondary legacy response rate column"
            >
              {showLegacyRate && <Check className="w-3 h-3 text-accent" aria-hidden="true" />}
              <span>Legacy Rate (M-04)</span>
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Main Table Container */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table
            className="w-full text-xs text-left border-collapse"
            role="table"
            aria-label={groupBy === "category" ? "Category breakdown table" : "Sub-category breakdown table"}
          >
            <thead className="bg-muted/60 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
              <tr>
                <th
                  scope="col"
                  className="px-3.5 py-2.5 text-left select-none"
                  aria-sort={sortField === "name" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button
                    type="button"
                    onClick={() => handleSort("name")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground font-medium rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span>{groupBy === "category" ? "Category" : "Sub-Category"}</span>
                    {renderSortIndicator("name")}
                  </button>
                </th>

                {groupBy === "sub_category" && (
                  <th scope="col" className="px-3 py-2.5 text-left">
                    Category
                  </th>
                )}

                <th
                  scope="col"
                  className="px-3 py-2.5 text-right select-none"
                  aria-sort={sortField === "total" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button
                    type="button"
                    onClick={() => handleSort("total")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground font-medium rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ml-auto"
                  >
                    <span>Total</span>
                    {renderSortIndicator("total")}
                  </button>
                </th>

                <th
                  scope="col"
                  className="px-3 py-2.5 text-right select-none"
                  aria-sort={sortField === "share_pct" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button
                    type="button"
                    onClick={() => handleSort("share_pct")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground font-medium rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ml-auto"
                  >
                    <span>Share</span>
                    {renderSortIndicator("share_pct")}
                  </button>
                </th>

                <th scope="col" className="px-3 py-2.5 text-right">
                  Timely Yes
                </th>

                <th scope="col" className="px-3 py-2.5 text-right">
                  Timely No
                </th>

                <th scope="col" className="px-3 py-2.5 text-right">
                  In Progress
                </th>

                <th
                  scope="col"
                  className="px-3.5 py-2.5 text-right select-none"
                  aria-sort={sortField === "timely_rate" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button
                    type="button"
                    onClick={() => handleSort("timely_rate")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground font-medium rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ml-auto"
                  >
                    <span>Timely Rate</span>
                    {renderSortIndicator("timely_rate")}
                  </button>
                </th>

                {showLegacyRate && (
                  <th
                    scope="col"
                    className="px-3.5 py-2.5 text-right select-none text-muted-foreground bg-muted/40"
                    aria-sort={
                      sortField === "timely_rate_all_cases"
                        ? sortDir === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                    }
                  >
                    <button
                      type="button"
                      onClick={() => handleSort("timely_rate_all_cases")}
                      className="inline-flex items-center gap-1.5 hover:text-foreground font-medium rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ml-auto"
                    >
                      <span>Legacy Rate</span>
                      {renderSortIndicator("timely_rate_all_cases")}
                    </button>
                  </th>
                )}

                {onRowClick && (
                  <th scope="col" className="w-10 px-2 py-2.5">
                    <span className="sr-only">Actions</span>
                  </th>
                )}
              </tr>
            </thead>

            <tbody className="divide-y divide-border/60">
              {loading ? (
                Array.from({ length: 5 }).map((_, rIdx) => (
                  <tr key={`loading-cat-${rIdx}`}>
                    <td colSpan={showLegacyRate ? 9 : 8} className="px-3.5 py-3 text-center">
                      <div className="h-4 bg-muted/60 animate-pulse rounded w-full" />
                    </td>
                  </tr>
                ))
              ) : sortedData.length === 0 ? (
                <tr>
                  <td
                    colSpan={showLegacyRate ? 9 : 8}
                    className="px-3.5 py-8 text-center text-muted-foreground"
                  >
                    No category data available for the active filters.
                  </td>
                </tr>
              ) : (
                sortedData.map((item) => {
                  const meetsTarget = (item.timely_rate ?? 0) >= 95;
                  const catColor = getCategoryColor(
                    item.category,
                    theme as "light" | "dark"
                  );

                  return (
                    <tr
                      key={item.sub_category || item.category}
                      onClick={() => onRowClick?.(item)}
                      className={cn(
                        "hover:bg-muted/40 transition-colors",
                        onRowClick && "cursor-pointer"
                      )}
                    >
                      <td className="px-3.5 py-2.5 text-foreground font-medium flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: catColor }}
                          aria-hidden="true"
                        />
                        <span className="truncate">
                          {item.sub_category || item.category}
                        </span>
                      </td>

                      {groupBy === "sub_category" && (
                        <td className="px-3 py-2.5 text-muted-foreground">
                          {item.category}
                        </td>
                      )}

                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-foreground">
                        {formatNumber(item.total)}
                      </td>

                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-foreground">
                        {formatPercent(item.share_pct, 1)}
                      </td>

                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-foreground">
                        {formatNumber(item.timely_yes)}
                      </td>

                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-foreground">
                        {formatNumber(item.timely_no)}
                      </td>

                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-muted-foreground">
                        {formatNumber(item.timely_unknown)}
                      </td>

                      <td className="px-3.5 py-2.5 text-right font-mono tabular-nums">
                        <Badge
                          variant={meetsTarget ? "positive" : "warning"}
                          dot
                          className="font-mono text-xs"
                        >
                          {formatPercent(item.timely_rate, 1)}
                        </Badge>
                      </td>

                      {showLegacyRate && (
                        <td className="px-3.5 py-2.5 text-right font-mono tabular-nums text-muted-foreground bg-muted/20">
                          {formatPercent(item.timely_rate_all_cases, 1)}
                        </td>
                      )}

                      {onRowClick && (
                        <td className="px-2 py-2.5 text-right text-muted-foreground">
                          <button
                            type="button"
                            className="p-1 rounded hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Drill down into ${groupBy === "category" ? "category" : "sub-category"} ${item.sub_category || item.category}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              onRowClick?.(item);
                            }}
                          >
                            <ChevronRight className="w-3.5 h-3.5 ml-auto text-muted-foreground/60" aria-hidden="true" />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>

            {/* Reconciliation Totals Row */}
            {sortedData.length > 0 && !loading && (
              <tfoot className="border-t-2 border-border bg-muted/40 font-semibold text-foreground">
                <tr>
                  <td className="px-3.5 py-2.5 text-left uppercase text-xs tracking-wider">
                    Total
                  </td>
                  {groupBy === "sub_category" && <td className="px-3 py-2.5" />}
                  <td
                    className="px-3 py-2.5 text-right font-mono tabular-nums"
                    data-testid="category-table-total"
                  >
                    {formatNumber(totals.total)}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                    100.0%
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                    {formatNumber(totals.timelyYes)}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                    {formatNumber(totals.timelyNo)}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                    {formatNumber(totals.timelyUnknown)}
                  </td>
                  <td className="px-3.5 py-2.5 text-right font-mono tabular-nums font-bold">
                    {formatPercent(totals.overallRate, 1)}
                  </td>
                  {showLegacyRate && (
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums text-muted-foreground bg-muted/30">
                      {formatPercent(totals.overallLegacyRate, 1)}
                    </td>
                  )}
                  {onRowClick && <td className="px-2 py-2.5" />}
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* Methodology Disclosures */}
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground px-1">
        <Info className="w-3.5 h-3.5 text-muted-foreground shrink-0" aria-hidden="true" />
        <span>
          Primary Timely Rate divides Yes by Rated cases (Yes + No), isolating the {formatNumber(totals.timelyUnknown)} in-progress cases with unrecorded outcomes.
        </span>
      </div>
    </div>
  );
}
