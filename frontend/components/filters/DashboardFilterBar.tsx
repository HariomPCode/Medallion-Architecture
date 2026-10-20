"use client";

import React from "react";
import { FilterBar } from "@/components/data/FilterBar";
import { Select } from "@/components/ui/select";
import { useFilters } from "@/lib/filters";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export interface DashboardFilterBarProps {
  totalResults?: number | null;
  resultsLabel?: string;
  className?: string;
}

/**
 * Reusable, URL-synchronized analytical filter bar for overview and category analytics.
 * Automatically queries meta/filters for dimension options.
 */
export function DashboardFilterBar({
  totalResults,
  resultsLabel = "complaints",
  className,
}: DashboardFilterBarProps) {
  const { filters, updateFilters, clearFilters, hasActiveFilters } = useFilters();

  // Query filter options from meta/filters
  const { data: filterMeta } = useQuery({
    queryKey: ["meta", "filters"],
    queryFn: () => api.getFilterOptions(),
    staleTime: 5 * 60 * 1000,
  });

  // Calculate active filter count
  const activeCount = [
    Boolean(filters.category && filters.category.length > 0),
    Boolean(filters.sub_category && filters.sub_category.length > 0),
    Boolean(filters.submitted_via && filters.submitted_via.length > 0),
    Boolean(filters.timely),
    Boolean(filters.date_from || filters.date_to),
  ].filter(Boolean).length;

  const currentCategory = filters.category?.[0] || "";
  const currentSubCategory = filters.sub_category?.[0] || "";
  const currentChannel = filters.submitted_via?.[0] || "";
  const currentTimely = filters.timely || "";

  // Available sub-categories based on selected category
  const availableSubCategories = React.useMemo(() => {
    if (!filterMeta?.categories) return [];
    if (currentCategory) {
      const match = filterMeta.categories.find(
        (c) => c.name.toLowerCase() === currentCategory.toLowerCase()
      );
      return match ? match.sub_categories : [];
    }
    // All sub-categories
    return Array.from(
      new Set(filterMeta.categories.flatMap((c) => c.sub_categories))
    ).sort();
  }, [filterMeta, currentCategory]);

  return (
    <FilterBar
      activeCount={activeCount}
      isFiltered={hasActiveFilters}
      onReset={clearFilters}
      resetLabel="Reset filters"
      totalResults={totalResults}
      resultsLabel={resultsLabel}
      className={className}
    >
      {/* Category Filter */}
      <div className="flex items-center gap-1.5">
        <label htmlFor="filter-category" className="sr-only">
          Product Category
        </label>
        <Select
          id="filter-category"
          value={currentCategory}
          onChange={(e) => {
            const val = e.target.value;
            updateFilters({
              category: val ? [val] : undefined,
              // Reset sub-category if changing category
              sub_category: undefined,
            });
          }}
          className="h-8 text-xs min-w-[140px]"
          aria-label="Filter by Product Category"
        >
          <option value="">All Categories</option>
          {filterMeta?.categories.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      {/* Sub-Category Filter */}
      <div className="flex items-center gap-1.5">
        <label htmlFor="filter-sub-category" className="sr-only">
          Sub-Category
        </label>
        <Select
          id="filter-sub-category"
          value={currentSubCategory}
          onChange={(e) => {
            const val = e.target.value;
            updateFilters({
              sub_category: val ? [val] : undefined,
            });
          }}
          className="h-8 text-xs min-w-[150px]"
          aria-label="Filter by Sub-Category"
        >
          <option value="">All Sub-Categories</option>
          {availableSubCategories.map((sub) => (
            <option key={sub} value={sub}>
              {sub}
            </option>
          ))}
        </Select>
      </div>

      {/* Submission Channel */}
      <div className="flex items-center gap-1.5">
        <label htmlFor="filter-channel" className="sr-only">
          Submission Channel
        </label>
        <Select
          id="filter-channel"
          value={currentChannel}
          onChange={(e) => {
            const val = e.target.value;
            updateFilters({
              submitted_via: val ? [val] : undefined,
            });
          }}
          className="h-8 text-xs min-w-[130px]"
          aria-label="Filter by Channel"
        >
          <option value="">All Channels</option>
          {filterMeta?.submitted_via?.map((ch) => (
            <option key={ch} value={ch}>
              {ch}
            </option>
          ))}
        </Select>
      </div>

      {/* Timely Response Filter */}
      <div className="flex items-center gap-1.5">
        <label htmlFor="filter-timely" className="sr-only">
          Timely Response
        </label>
        <Select
          id="filter-timely"
          value={currentTimely}
          onChange={(e) => {
            const val = e.target.value as "Yes" | "No" | "";
            updateFilters({
              timely: val ? val : undefined,
            });
          }}
          className="h-8 text-xs min-w-[120px]"
          aria-label="Filter by Timeliness"
        >
          <option value="">All Timeliness</option>
          <option value="Yes">Timely Only (Yes)</option>
          <option value="No">Untimely Only (No)</option>
        </Select>
      </div>
    </FilterBar>
  );
}
