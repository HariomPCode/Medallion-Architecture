"use client";

import React, { useState, useTransition, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  Download,
  Search,
  Filter,
  X,
  AlertTriangle,
  RotateCcw,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { api, buildQueryString } from "@/lib/api/client";
import {
  useFilters,
  complaintsFiltersToApiParams,
  exportFiltersToApiParams,
  ComplaintFilterState,
} from "@/lib/filters";
import { ComplaintsTable } from "@/components/tables/ComplaintsTable";
import { ComplaintSheet } from "@/components/complaints/ComplaintSheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function ExplorerPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { filters, updateFilters, clearFilters, hasActiveFilters } = useFilters();
  const [, startTransition] = useTransition();

  // Mobile / Collapsible filter drawer state
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Exact ID search local state
  const [idSearchInput, setIdSearchInput] = useState(filters.q || "");
  const [idError, setIdError] = useState<string | null>(null);

  // Export state
  const [exportLoading, setExportLoading] = useState(false);
  const [exportTruncated, setExportTruncated] = useState(false);
  const [exportTruncatedCount, setExportTruncatedCount] = useState<number | null>(null);

  // Deep-linked complaint selection: ?selected=ID
  const selectedId = searchParams.get("selected");

  // Fetch filter taxonomy
  const { data: filterOptions } = useQuery({
    queryKey: ["filter-options"],
    queryFn: () => api.getFilterOptions(),
    staleTime: 300_000,
  });

  // Current page and page size
  const page = filters.page || 1;
  const pageSize = filters.page_size || 25;
  const sortBy = filters.sort_by || "date_submitted";
  const sortDir = (filters.sort_dir as "asc" | "desc") || "desc";

  // Fetch paginated complaints list
  const {
    data: complaintsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: [
      "complaints-list",
      page,
      pageSize,
      sortBy,
      sortDir,
      filters.category,
      filters.sub_category,
      filters.submitted_via,
      filters.company_response,
      filters.timely,
      filters.state,
      filters.issue,
      filters.date_from,
      filters.date_to,
      filters.q,
    ],
    queryFn: () => api.getComplaints(complaintsFiltersToApiParams(filters)),
    staleTime: 60_000,
  });

  // Handle Exact ID search submit (digits only)
  const handleIdSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = idSearchInput.trim();

    if (!cleanId) {
      setIdError(null);
      updateFilters({ q: undefined, page: 1 });
      return;
    }

    if (!/^\d+$/.test(cleanId)) {
      setIdError("Complaint ID must contain only digits");
      return;
    }

    if (cleanId.length > 12) {
      setIdError("Complaint ID must be 12 digits or less");
      return;
    }

    setIdError(null);
    updateFilters({ q: cleanId, page: 1 });
  };

  // Open detail sheet by updating URL (?selected=ID)
  const handleOpenDetail = useCallback(
    (complaintId: number | string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("selected", String(complaintId));
      startTransition(() => {
        router.push(`${pathname}?${params.toString()}`, { scroll: false });
      });
    },
    [pathname, router, searchParams]
  );

  // Close detail sheet by removing ?selected
  const handleCloseDetail = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("selected");
    const query = params.toString();
    startTransition(() => {
      router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
    });
  }, [pathname, router, searchParams]);

  // Handle Export CSV
  const handleExport = async () => {
    setExportLoading(true);
    setExportTruncated(false);
    try {
      const params = exportFiltersToApiParams(filters);
      const queryString = buildQueryString(params);
      const res = await fetch(`/api/v1/complaints/export${queryString}`, {
        headers: { Accept: "text/csv" },
      });

      if (!res.ok) {
        throw new Error(`Export failed with HTTP status ${res.status}`);
      }

      const isTrunc = res.headers.get("x-export-truncated") === "true";
      const rowCount = res.headers.get("x-export-row-count");
      if (isTrunc) {
        setExportTruncated(true);
        setExportTruncatedCount(rowCount ? parseInt(rowCount, 10) : 5000);
      }

      const blob = await res.blob();
      if (typeof window !== "undefined") {
        const downloadUrl =
          typeof window.URL.createObjectURL === "function"
            ? window.URL.createObjectURL(blob)
            : "";

        if (downloadUrl) {
          const a = document.createElement("a");
          a.href = downloadUrl;
          a.download = `complaints_export_${new Date().toISOString().slice(0, 10)}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(downloadUrl);
        }
      }
    } catch (err) {
      console.error("Export failure:", err);
    } finally {
      setExportLoading(false);
    }
  };

  // Sub-categories available based on selected category
  const availableSubCategories = React.useMemo(() => {
    if (!filterOptions?.categories) return [];
    if (!filters.category || filters.category.length === 0) {
      return filterOptions.categories.flatMap((c) => c.sub_categories);
    }
    return filterOptions.categories
      .filter((c) => filters.category?.includes(c.name))
      .flatMap((c) => c.sub_categories);
  }, [filterOptions, filters.category]);

  return (
    <div className="space-y-6" data-testid="complaint-explorer-page">
      {/* Page Header */}
      <header className="border-b border-border pb-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Complaint Explorer
            </h1>
            <p className="text-xs text-muted-foreground mt-1">
              Search, filter, and inspect record-level CFPB complaints with streaming CSV export
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={exportLoading}
              className="text-xs gap-1.5 h-8 font-medium"
              data-testid="export-csv-button"
            >
              {exportLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              <span>{exportLoading ? "Exporting..." : "Export CSV"}</span>
            </Button>
          </div>
        </div>

        {/* Truncation Warning Banner */}
        {exportTruncated && (
          <div
            className="mt-4 flex items-start gap-2.5 rounded-lg border border-warning/40 bg-warning/10 p-3.5 text-xs text-warning-foreground"
            role="alert"
            data-testid="export-truncated-banner"
          >
            <AlertTriangle className="h-4 w-4 shrink-0 text-warning mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-foreground">Export Capped:</span>
              <p className="text-muted-foreground leading-relaxed">
                The query exceeded the export safety limit. The downloaded file was capped at{" "}
                <strong>{formatNumber(exportTruncatedCount ?? 5000)} rows</strong>. To export
                specific records, narrow your category, issue, or date range filters.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setExportTruncated(false)}
              className="ml-auto text-muted-foreground hover:text-foreground"
              aria-label="Dismiss export truncation banner"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
      </header>

      {/* Main Grid: Filters Sidebar (left on xl) + Results Area */}
      <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-6 items-start">
        {/* Filter Controls Sidebar / Collapsible */}
        <div className="space-y-4">
          {/* Mobile Collapsible Toggle */}
          <div className="xl:hidden flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFiltersOpen((o) => !o)}
              className="w-full justify-between h-9 text-xs"
              aria-expanded={filtersOpen}
              aria-controls="explorer-filter-panel"
            >
              <span className="flex items-center gap-2">
                <Filter className="h-3.5 w-3.5" />
                <span>Filters {hasActiveFilters ? "(Active)" : ""}</span>
              </span>
              {filtersOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </Button>
          </div>

          {/* Filter Panel Card */}
          <Card
            id="explorer-filter-panel"
            className={cn(
              "border border-border bg-card",
              !filtersOpen && "hidden xl:block"
            )}
            data-testid="explorer-filters-panel"
          >
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle as="h2" className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Search & Filters
                </CardTitle>
                {hasActiveFilters && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearFilters}
                    className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground gap-1"
                    data-testid="clear-all-filters-button"
                  >
                    <RotateCcw className="h-3 w-3" />
                    <span>Reset</span>
                  </Button>
                )}
              </div>
            </CardHeader>

            <CardContent className="space-y-4 pt-4 text-xs">
              {/* Exact Complaint ID Search */}
              <form onSubmit={handleIdSearch} className="space-y-1.5" data-testid="id-search-form">
                <label
                  htmlFor="complaint-id-search"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Complaint ID
                </label>
                <div className="flex gap-1.5">
                  <Input
                    id="complaint-id-search"
                    type="text"
                    inputMode="numeric"
                    placeholder="e.g. 1001"
                    value={idSearchInput}
                    onChange={(e) => {
                      const clean = e.target.value.replace(/\D/g, "");
                      setIdSearchInput(clean);
                      if (idError) setIdError(null);
                    }}
                    className="h-8 text-xs font-mono"
                    maxLength={12}
                    aria-label="Search exact complaint ID digits only"
                    data-testid="id-search-input"
                  />
                  <Button
                    type="submit"
                    variant="secondary"
                    size="sm"
                    className="h-8 px-2.5 text-xs shrink-0"
                    aria-label="Submit complaint ID search"
                    data-testid="id-search-submit"
                  >
                    <Search className="h-3.5 w-3.5" />
                  </Button>
                </div>
                {idError && (
                  <p className="text-[10px] text-destructive font-medium" role="alert">
                    {idError}
                  </p>
                )}
              </form>

              {/* Category Filter */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-category"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Category
                </label>
                <Select
                  id="filter-category"
                  value={filters.category?.[0] || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    updateFilters({
                      category: val ? [val] : undefined,
                      sub_category: undefined, // reset sub_category when category changes
                    });
                  }}
                  data-testid="filter-category-select"
                >
                  <option value="">All Categories</option>
                  {filterOptions?.categories.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Sub-Category Filter */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-subcategory"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Sub-Category
                </label>
                <Select
                  id="filter-subcategory"
                  value={filters.sub_category?.[0] || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    updateFilters({ sub_category: val ? [val] : undefined });
                  }}
                  disabled={availableSubCategories.length === 0}
                  data-testid="filter-subcategory-select"
                >
                  <option value="">All Sub-Categories</option>
                  {availableSubCategories.map((sc) => (
                    <option key={sc} value={sc}>
                      {sc}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Submission Channel */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-channel"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Submission Channel
                </label>
                <Select
                  id="filter-channel"
                  value={filters.submitted_via?.[0] || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    updateFilters({ submitted_via: val ? [val] : undefined });
                  }}
                  data-testid="filter-channel-select"
                >
                  <option value="">All Channels</option>
                  {filterOptions?.submitted_via.map((ch) => (
                    <option key={ch} value={ch}>
                      {ch}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Timely Response */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-timely"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Timely Response
                </label>
                <Select
                  id="filter-timely"
                  value={filters.timely || ""}
                  onChange={(e) => {
                    const val = e.target.value as "Yes" | "No" | "";
                    updateFilters({ timely: val || undefined });
                  }}
                  data-testid="filter-timely-select"
                >
                  <option value="">All Timely Outcomes</option>
                  <option value="Yes">Yes (Timely)</option>
                  <option value="No">No (Untimely)</option>
                </Select>
              </div>

              {/* Company Response */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-response"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Company Response
                </label>
                <Select
                  id="filter-response"
                  value={filters.company_response?.[0] || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    updateFilters({ company_response: val ? [val] : undefined });
                  }}
                  data-testid="filter-response-select"
                >
                  <option value="">All Responses</option>
                  {filterOptions?.company_response.map((cr) => (
                    <option key={cr} value={cr}>
                      {cr}
                    </option>
                  ))}
                </Select>
              </div>

              {/* State */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-state"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Consumer State
                </label>
                <Select
                  id="filter-state"
                  value={filters.state?.[0] || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    updateFilters({ state: val ? [val] : undefined });
                  }}
                  data-testid="filter-state-select"
                >
                  <option value="">All States / Territories</option>
                  {filterOptions?.state.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Date From & To */}
              <div className="space-y-1.5">
                <label
                  htmlFor="filter-date-from"
                  className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block"
                >
                  Date Range
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  <Input
                    id="filter-date-from"
                    type="date"
                    value={filters.date_from || ""}
                    onChange={(e) => updateFilters({ date_from: e.target.value || undefined })}
                    className="h-8 text-[11px] px-2"
                    aria-label="Filter complaints submitted on or after this date"
                    data-testid="filter-date-from-input"
                  />
                  <Input
                    id="filter-date-to"
                    type="date"
                    value={filters.date_to || ""}
                    onChange={(e) => updateFilters({ date_to: e.target.value || undefined })}
                    className="h-8 text-[11px] px-2"
                    aria-label="Filter complaints submitted on or before this date"
                    data-testid="filter-date-to-input"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Results Column */}
        <div className="space-y-4">
          {/* Results Summary Header & Active Chips */}
          <div className="rounded-lg border border-border bg-card p-3.5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground text-sm" data-testid="results-count">
                  {formatNumber(complaintsData?.total ?? 0)}
                </span>
                <span className="text-muted-foreground">complaints found</span>
              </div>

              {/* Page Size Selector */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Rows per page:</span>
                <div className="w-20">
                  <Select
                    value={String(pageSize)}
                    onChange={(e) => updateFilters({ page_size: parseInt(e.target.value, 10), page: 1 })}
                    aria-label="Select rows per page"
                    data-testid="page-size-selector"
                  >
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                  </Select>
                </div>
              </div>
            </div>

            {/* Active Filter Chips */}
            {hasActiveFilters && (
              <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-border/60">
                <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mr-1">
                  Active:
                </span>

                {filters.q && (
                  <Badge variant="outline" className="text-[11px] gap-1 pr-1 font-mono">
                    ID: {filters.q}
                    <button
                      type="button"
                      onClick={() => {
                        setIdSearchInput("");
                        updateFilters({ q: undefined });
                      }}
                      className="hover:text-foreground"
                      aria-label="Remove complaint ID filter"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}

                {filters.category?.map((cat) => (
                  <Badge key={cat} variant="outline" className="text-[11px] gap-1 pr-1">
                    {cat}
                    <button
                      type="button"
                      onClick={() =>
                        updateFilters({
                          category: filters.category?.filter((c) => c !== cat),
                        })
                      }
                      className="hover:text-foreground"
                      aria-label={`Remove category filter ${cat}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}

                {filters.sub_category?.map((sc) => (
                  <Badge key={sc} variant="outline" className="text-[11px] gap-1 pr-1">
                    {sc}
                    <button
                      type="button"
                      onClick={() =>
                        updateFilters({
                          sub_category: filters.sub_category?.filter((c) => c !== sc),
                        })
                      }
                      className="hover:text-foreground"
                      aria-label={`Remove sub-category filter ${sc}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}

                {filters.submitted_via?.map((ch) => (
                  <Badge key={ch} variant="outline" className="text-[11px] gap-1 pr-1">
                    Channel: {ch}
                    <button
                      type="button"
                      onClick={() =>
                        updateFilters({
                          submitted_via: filters.submitted_via?.filter((c) => c !== ch),
                        })
                      }
                      className="hover:text-foreground"
                      aria-label={`Remove channel filter ${ch}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}

                {filters.timely && (
                  <Badge variant="outline" className="text-[11px] gap-1 pr-1">
                    Timely: {filters.timely}
                    <button
                      type="button"
                      onClick={() => updateFilters({ timely: undefined })}
                      className="hover:text-foreground"
                      aria-label="Remove timeliness filter"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}

                {filters.state?.map((st) => (
                  <Badge key={st} variant="outline" className="text-[11px] gap-1 pr-1 font-mono">
                    State: {st}
                    <button
                      type="button"
                      onClick={() =>
                        updateFilters({
                          state: filters.state?.filter((s) => s !== st),
                        })
                      }
                      className="hover:text-foreground"
                      aria-label={`Remove state filter ${st}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}

                {filters.company_response?.map((cr) => (
                  <Badge key={cr} variant="outline" className="text-[11px] gap-1 pr-1">
                    Response: {cr}
                    <button
                      type="button"
                      onClick={() =>
                        updateFilters({
                          company_response: filters.company_response?.filter((c) => c !== cr),
                        })
                      }
                      className="hover:text-foreground"
                      aria-label={`Remove company response filter ${cr}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}

                {(filters.date_from || filters.date_to) && (
                  <Badge variant="outline" className="text-[11px] gap-1 pr-1">
                    Dates: {filters.date_from || "Start"} to {filters.date_to || "Present"}
                    <button
                      type="button"
                      onClick={() => updateFilters({ date_from: undefined, date_to: undefined })}
                      className="hover:text-foreground"
                      aria-label="Remove date range filter"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="h-5 px-1.5 text-[10px] text-muted-foreground hover:text-foreground"
                >
                  Clear all
                </Button>
              </div>
            )}
          </div>

          {/* Table Container */}
          <ComplaintsTable
            complaints={complaintsData?.items ?? []}
            total={complaintsData?.total ?? 0}
            page={page}
            pageSize={pageSize}
            totalPages={complaintsData?.total_pages ?? 1}
            loading={isLoading}
            error={error}
            onRetry={() => refetch()}
            sortBy={sortBy}
            sortDir={sortDir}
            onSortChange={(col, dir) => updateFilters({ sort_by: col, sort_dir: dir, page: 1 })}
            onPageChange={(newPage) => updateFilters({ page: newPage })}
            onPageSizeChange={(newSize) => updateFilters({ page_size: newSize, page: 1 })}
            onRowClick={(complaint) => handleOpenDetail(complaint.complaint_id)}
            onClearFilters={clearFilters}
          />
        </div>
      </div>

      {/* Deep-Linked Complaint Detail Sheet */}
      <ComplaintSheet
        complaintId={selectedId}
        isOpen={Boolean(selectedId)}
        onClose={handleCloseDetail}
      />
    </div>
  );
}
