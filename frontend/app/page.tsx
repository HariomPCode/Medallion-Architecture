"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useFilters, filtersToApiParams } from "@/lib/filters";
import { DashboardFilterBar } from "@/components/filters/DashboardFilterBar";
import { KpiStrip } from "@/components/data/KpiStrip";
import { DatasetStatusPill, DatasetStatus } from "@/components/data/DatasetStatusPill";
import { CategoryBar } from "@/components/charts/CategoryBar";
import { TrendLine } from "@/components/charts/TrendLine";
import { TimelyDotPlot } from "@/components/charts/TimelyDotPlot";
import { Tooltip } from "@/components/ui/tooltip";
import { formatNumber, formatPercent, formatDate } from "@/lib/format";
import { Info, AlertCircle } from "lucide-react";

export default function OverviewDashboardPage() {
  const { filters, updateFilters } = useFilters();
  const apiFilterParams = React.useMemo(() => filtersToApiParams(filters), [filters]);
  const [trendGrain, setTrendGrain] = useState<"year" | "month">("year");

  // 1. Dataset metadata query
  const { data: datasetMeta } = useQuery({
    queryKey: ["meta", "dataset"],
    queryFn: () => api.getDatasetMeta(),
    staleTime: 5 * 60 * 1000,
  });

  // 2. Dashboard summary query (KPI strip)
  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ["dashboard", "summary", apiFilterParams],
    queryFn: () => api.getDashboardSummary(apiFilterParams),
  });

  // 3. Category breakdown query
  const {
    data: categoryData,
    isLoading: categoryLoading,
    error: categoryError,
    refetch: refetchCategory,
  } = useQuery({
    queryKey: ["analytics", "by-category", "category", apiFilterParams],
    queryFn: () =>
      api.getCategoryAnalytics({
        ...apiFilterParams,
        group_by: "category",
        sort_by: "total",
        sort_order: "desc",
      }),
  });

  // 4. Trends query
  const {
    data: trendData,
    isLoading: trendLoading,
    error: trendError,
    refetch: refetchTrends,
  } = useQuery({
    queryKey: ["analytics", "trends", trendGrain, apiFilterParams],
    queryFn: () =>
      api.getTrends({
        ...apiFilterParams,
        grain: trendGrain,
      }),
  });

  // 5. Sub-category timeliness query
  const {
    data: subCategoryData,
    isLoading: subCategoryLoading,
    error: subCategoryError,
    refetch: refetchSubCategory,
  } = useQuery({
    queryKey: ["analytics", "by-category", "sub_category", apiFilterParams],
    queryFn: () =>
      api.getCategoryAnalytics({
        ...apiFilterParams,
        group_by: "sub_category",
        sort_by: "total",
        sort_order: "desc",
      }),
  });

  // Dynamic scope subtitle from API values
  const scopeLine = React.useMemo(() => {
    if (!summary) return "Loading dataset scope...";
    const total = formatNumber(summary.total_complaints);
    const cats = summary.category_count;
    const subs = summary.sub_category_count;
    const dateRange = `${formatDate(summary.coverage.start)} – ${formatDate(summary.coverage.end)}`;
    return `${total} complaints · ${cats} categories · ${subs} sub-categories · Date coverage ${dateRange}`;
  }, [summary]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Finance Complaints Overview
          </h1>
          <p
            className="text-xs text-muted-foreground mt-1 tabular-nums"
            data-testid="dataset-scope-line"
          >
            {scopeLine}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <DatasetStatusPill
            status={(datasetMeta?.data_status as DatasetStatus) || "local_snapshot"}
          />
        </div>
      </header>

      {/* Dataset Warnings or Skew Notices */}
      {datasetMeta?.skew_warning && (
        <div
          role="region"
          aria-label="Dataset distribution notice"
          className="rounded-md border border-status-warning/40 bg-status-warning-soft/40 p-3 text-xs text-status-warning flex items-start gap-2.5"
        >
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <span className="font-semibold text-foreground">
              CFPB Distribution Notice:
            </span>{" "}
            <span>
              The top two categories (Banking & Payments) constitute over 70% of total volume. Volume metrics reflect CFPB consumer submissions, not total financial transactions.
            </span>
          </div>
        </div>
      )}

      {/* Shared Filter Bar */}
      <DashboardFilterBar
        totalResults={summary?.total_complaints}
        resultsLabel="filtered complaints"
      />

      {/* KPI Strip (4 Tiles) */}
      <KpiStrip
        title="Key Performance Indicators"
        columns={4}
        items={[
          {
            label: "Total Complaints",
            value: summary ? formatNumber(summary.total_complaints) : null,
            description: "All records matching current filters",
            loading: summaryLoading,
          },
          {
            label: "Primary Timely Rate",
            value: summary && summary.timely.rate != null ? formatPercent(summary.timely.rate, 1) : null,
            description: summary
              ? `of ${formatNumber(summary.timely.rate_denominator)} cases with recorded outcome`
              : "Excludes in-progress cases",
            loading: summaryLoading,
            badge: summary ? (
              <Tooltip
                content={`Legacy M-04 rate: ${formatPercent(
                  summary.timely.rate_all_cases,
                  1
                )} (divides by all ${formatNumber(summary.total_complaints)} cases including in-progress)`}
              >
                <button
                  type="button"
                  aria-label="Legacy timely rate definition"
                  className="text-muted-foreground hover:text-foreground"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
              </Tooltip>
            ) : null,
          },
          {
            label: "In-Progress Cases",
            value: summary ? formatNumber(summary.in_progress_count) : null,
            description: "Outcome pending (timeliness undetermined)",
            loading: summaryLoading,
          },
          {
            label: "Coverage End Date",
            value: summary ? formatDate(summary.coverage.end) : null,
            description: summary
              ? `Pipeline refreshed: ${formatDate(summary.pipeline_refreshed_at)}`
              : undefined,
            loading: summaryLoading,
          },
        ]}
      />

      {/* 2-Column Analytical Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Complaints by Category Bar */}
        <CategoryBar
          title="Complaints by Category"
          description="Volume and market share across product categories"
          data={categoryData?.items || []}
          loading={categoryLoading}
          error={categoryError}
          onRetry={() => refetchCategory()}
          onItemClick={(item) => updateFilters({ category: [item.category] })}
        />

        {/* Complaints Over Time Trend Line */}
        <TrendLine
          title="Complaints Over Time"
          description="Annual and monthly volume progression"
          series={trendData?.series}
          totalSeries={trendData?.total_series}
          grain={trendGrain}
          onGrainChange={setTrendGrain}
          loading={trendLoading}
          error={trendError}
          onRetry={() => refetchTrends()}
        />
      </div>

      {/* Full-Width Sub-Category Timeliness Dot Plot */}
      <TimelyDotPlot
        title="Timely Response Compliance by Sub-Category"
        description="Primary compliance rate (Yes / Rated Cases) evaluated against the 95% regulatory target"
        data={subCategoryData?.items || []}
        loading={subCategoryLoading}
        error={subCategoryError}
        onRetry={() => refetchSubCategory()}
      />
    </div>
  );
}
