"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useFilters, filtersToApiParams } from "@/lib/filters";
import { DashboardFilterBar } from "@/components/filters/DashboardFilterBar";
import { CategoryTable } from "@/components/tables/CategoryTable";
import { YoyTable } from "@/components/tables/YoyTable";
import { CategoryBar } from "@/components/charts/CategoryBar";
import { TrendLine } from "@/components/charts/TrendLine";
import { Button } from "@/components/ui/button";
import { Layers, FolderTree } from "lucide-react";
import { formatNumber } from "@/lib/format";

export default function CategoryAnalyticsPage() {
  const { filters, updateFilters } = useFilters();
  const apiFilterParams = React.useMemo(() => filtersToApiParams(filters), [filters]);

  const [groupBy, setGroupBy] = useState<"category" | "sub_category">("category");
  const [trendGrain, setTrendGrain] = useState<"year" | "month">("year");

  // 1. Dashboard summary query for active filters (totals reconciliation)
  const { data: summary } = useQuery({
    queryKey: ["dashboard", "summary", apiFilterParams],
    queryFn: () => api.getDashboardSummary(apiFilterParams),
  });

  // 2. Category / Sub-Category analytical breakdown
  const {
    data: categoryData,
    isLoading: categoryLoading,
    error: categoryError,
    refetch: refetchCategories,
  } = useQuery({
    queryKey: ["analytics", "by-category", groupBy, apiFilterParams],
    queryFn: () =>
      api.getCategoryAnalytics({
        ...apiFilterParams,
        group_by: groupBy,
        sort_by: "total",
        sort_order: "desc",
      }),
  });

  // 3. Multi-line category trends query
  const {
    data: categoryTrends,
    isLoading: trendsLoading,
    error: trendsError,
    refetch: refetchTrends,
  } = useQuery({
    queryKey: ["analytics", "trends", "by-category", trendGrain, apiFilterParams],
    queryFn: () =>
      api.getTrends({
        ...apiFilterParams,
        grain: trendGrain,
        group_by: "category",
      }),
  });

  // 4. Annual overall trend query for YoY analysis table (complete vs partial years)
  const {
    data: yearlyTrends,
    isLoading: yoyLoading,
    error: yoyError,
    refetch: refetchYoy,
  } = useQuery({
    queryKey: ["analytics", "trends", "yearly-summary", apiFilterParams],
    queryFn: () =>
      api.getTrends({
        ...apiFilterParams,
        grain: "year",
      }),
  });

  // Row click drill-down handler
  const handleRowClick = (item: { category: string; sub_category?: string | null }) => {
    if (groupBy === "category") {
      updateFilters({ category: [item.category] });
    } else if (item.sub_category) {
      updateFilters({
        category: [item.category],
        sub_category: [item.sub_category],
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header and View Selector */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Category Analytics
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Category and sub-category market volume, compliance distribution, and longitudinal trends
          </p>
        </div>

        {/* Segmented Control (Category vs Sub-Category) */}
        <div
          role="group"
          aria-label="Granularity view selector"
          className="flex items-center rounded-lg border border-border p-1 bg-muted/50 shrink-0"
        >
          <button
            type="button"
            onClick={() => setGroupBy("category")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              groupBy === "category"
                ? "bg-card text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
            aria-pressed={groupBy === "category"}
          >
            <Layers className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Category View</span>
          </button>
          <button
            type="button"
            onClick={() => setGroupBy("sub_category")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              groupBy === "sub_category"
                ? "bg-card text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
            aria-pressed={groupBy === "sub_category"}
          >
            <FolderTree className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Sub-Category View</span>
          </button>
        </div>
      </header>

      {/* Shared Filter Bar */}
      <DashboardFilterBar
        totalResults={summary?.total_complaints}
        resultsLabel="matching complaints"
      />

      {/* Section 1: Comparison Table & Volume Chart Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        {/* Main Comparison Table (2 Cols on XL) */}
        <div className="xl:col-span-2">
          <CategoryTable
            data={categoryData?.items || []}
            groupBy={groupBy}
            totalComplaints={summary?.total_complaints}
            loading={categoryLoading}
            error={categoryError}
            onRetry={() => refetchCategories()}
            onRowClick={handleRowClick}
          />
        </div>

        {/* Volume Distribution Bar (1 Col on XL) */}
        <div className="xl:col-span-1">
          <CategoryBar
            title="Volume Distribution"
            description={`Complaints share by ${groupBy === "category" ? "category" : "sub-category"}`}
            data={categoryData?.items || []}
            loading={categoryLoading}
            error={categoryError}
            onRetry={() => refetchCategories()}
            onItemClick={handleRowClick}
          />
        </div>
      </div>

      {/* Section 2: Multi-Line Trend by Category */}
      <TrendLine
        title="Volume Trajectory by Product Category"
        description="Historical annual and monthly trend progression broken down by category"
        series={categoryTrends?.series}
        grain={trendGrain}
        onGrainChange={setTrendGrain}
        loading={trendsLoading}
        error={trendsError}
        onRetry={() => refetchTrends()}
      />

      {/* Section 3: Year-over-Year Analysis Table */}
      <YoyTable
        data={yearlyTrends?.total_series?.points || []}
        loading={yoyLoading}
        error={yoyError}
        onRetry={() => refetchYoy()}
      />
    </div>
  );
}
