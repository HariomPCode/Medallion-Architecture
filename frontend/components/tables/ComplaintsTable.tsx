"use client";

import React, { useState, useMemo } from "react";
import { ColumnDef, VisibilityState } from "@tanstack/react-table";
import { SlidersHorizontal, AlertTriangle, Eye, EyeOff } from "lucide-react";
import { ComplaintListItem } from "@/lib/api/client";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface ComplaintsTableProps {
  complaints: ComplaintListItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  onSortChange: (sortBy: string, sortDir: "asc" | "desc") => void;
  onPageChange: (newPage: number) => void;
  onPageSizeChange: (newPageSize: number) => void;
  onRowClick: (complaint: ComplaintListItem) => void;
  onClearFilters?: () => void;
}

export function ComplaintsTable({
  complaints,
  total,
  page,
  pageSize,
  totalPages,
  loading = false,
  error,
  onRetry,
  sortBy = "date_submitted",
  sortDir = "desc",
  onSortChange,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  onClearFilters,
}: ComplaintsTableProps) {
  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    complaint_id: true,
    date_submitted: true,
    category: true,
    sub_category: true,
    issue: true,
    submitted_via: true,
    state: true,
    company_response: true,
    timely_response: true,
    is_anomaly: true,
  });

  const [showVisibilityMenu, setShowVisibilityMenu] = useState(false);

  // Define columns
  const columns = useMemo<ColumnDef<ComplaintListItem, any>[]>(
    () => [
      {
        accessorKey: "complaint_id",
        header: "Complaint ID",
        enableSorting: true,
        cell: ({ row }) => (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRowClick(row.original);
            }}
            className="font-mono font-semibold text-accent hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded px-1 -mx-1"
            aria-label={`View complaint #${row.original.complaint_id}`}
          >
            #{row.original.complaint_id}
          </button>
        ),
      },
      {
        accessorKey: "date_submitted",
        header: "Date Submitted",
        enableSorting: true,
        cell: ({ row }) => (
          <span className="font-mono text-muted-foreground whitespace-nowrap">
            {formatDate(row.original.date_submitted)}
          </span>
        ),
      },
      {
        accessorKey: "category",
        header: "Category",
        enableSorting: true,
        cell: ({ row }) => <span className="font-medium text-foreground">{row.original.category}</span>,
      },
      {
        accessorKey: "sub_category",
        header: "Sub-Category",
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground">{row.original.sub_category || "—"}</span>
        ),
      },
      {
        accessorKey: "issue",
        header: "Issue",
        enableSorting: true,
        cell: ({ row }) => (
          <div
            className="max-w-[220px] truncate text-foreground/90"
            title={row.original.issue}
          >
            {row.original.issue}
          </div>
        ),
      },
      {
        accessorKey: "submitted_via",
        header: "Channel",
        enableSorting: true,
        cell: ({ row }) => <span className="text-muted-foreground">{row.original.submitted_via}</span>,
      },
      {
        accessorKey: "state",
        header: "State",
        enableSorting: true,
        meta: { align: "center" },
        cell: ({ row }) => (
          <span className="font-mono font-medium text-foreground">{row.original.state || "—"}</span>
        ),
      },
      {
        accessorKey: "company_response",
        header: "Company Response",
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-foreground/90 whitespace-nowrap">{row.original.company_response}</span>
        ),
      },
      {
        accessorKey: "timely_response",
        header: "Timely",
        enableSorting: true,
        meta: { align: "center" },
        cell: ({ row }) => {
          const timely = row.original.timely_response;
          if (timely === "yes") {
            return (
              <Badge variant="positive" dot className="text-[10px] px-1.5 py-0">
                Yes
              </Badge>
            );
          }
          if (timely === "no") {
            return (
              <Badge variant="negative" dot className="text-[10px] px-1.5 py-0">
                No
              </Badge>
            );
          }
          return (
            <Badge variant="neutral" dot className="text-[10px] px-1.5 py-0">
              Open
            </Badge>
          );
        },
      },
      {
        accessorKey: "is_anomaly",
        header: "Outlier",
        enableSorting: false,
        meta: { align: "center" },
        cell: ({ row }) => {
          if (row.original.is_anomaly) {
            return (
              <span
                className="inline-flex items-center text-destructive"
                title="Flagged statistical outlier (Isolation Forest)"
              >
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="sr-only">Flagged statistical outlier</span>
              </span>
            );
          }
          return <span className="text-muted-foreground/40">—</span>;
        },
      },
    ],
    [onRowClick]
  );

  // Sorting state adapter for TanStack
  const sorting = useMemo(
    () => [{ id: sortBy, desc: sortDir === "desc" }],
    [sortBy, sortDir]
  );

  const toggleColumn = (columnId: string) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [columnId]: !prev[columnId],
    }));
  };

  return (
    <div className="space-y-3 w-full" data-testid="complaints-table-container">
      {/* Column Visibility Toolbar */}
      <div className="flex items-center justify-between gap-2 px-1">
        <div className="text-xs text-muted-foreground">
          {total > 0 && (
            <span>
              Page <span className="font-semibold text-foreground">{page}</span> of{" "}
              <span className="font-semibold text-foreground">{totalPages}</span>
            </span>
          )}
        </div>

        <div className="relative">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowVisibilityMenu((v) => !v)}
            className="h-7 text-xs gap-1.5"
            aria-expanded={showVisibilityMenu}
            aria-label="Toggle column visibility"
            data-testid="column-visibility-toggle"
          >
            <SlidersHorizontal className="h-3 w-3" />
            <span>Columns</span>
          </Button>

          {showVisibilityMenu && (
            <div
              className="absolute right-0 top-8 z-30 w-48 rounded-md border border-border bg-popover p-2 shadow-lg text-xs space-y-1"
              role="menu"
              aria-orientation="vertical"
              data-testid="column-visibility-menu"
            >
              <div className="px-1.5 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Toggle Columns
              </div>
              {[
                { id: "sub_category", label: "Sub-Category" },
                { id: "submitted_via", label: "Channel" },
                { id: "state", label: "State" },
                { id: "company_response", label: "Response" },
                { id: "timely_response", label: "Timely" },
                { id: "is_anomaly", label: "Outlier" },
              ].map(({ id, label }) => {
                const isVisible = columnVisibility[id] !== false;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => toggleColumn(id)}
                    className="flex w-full items-center justify-between rounded px-2 py-1 text-left hover:bg-muted transition-colors"
                    role="menuitem"
                  >
                    <span>{label}</span>
                    {isVisible ? (
                      <Eye className="h-3.5 w-3.5 text-accent" />
                    ) : (
                      <EyeOff className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Desktop & Tablet Table (>= 768px) */}
      <div className="hidden md:block">
        <DataTable
          columns={columns}
          data={complaints}
          loading={loading}
          error={error}
          onRetry={onRetry}
          manualSorting={true}
          defaultSorting={sorting}
          onSortingChange={(nextSorting) => {
            if (nextSorting.length > 0) {
              const col = nextSorting[0];
              onSortChange(col.id, col.desc ? "desc" : "asc");
            }
          }}
          manualPagination={true}
          pageIndex={page - 1}
          pageSize={pageSize}
          pageSizeOptions={[25, 50, 100]}
          pageCount={totalPages}
          totalRows={total}
          onPaginationChange={(nextPagination) => {
            if (nextPagination.pageIndex !== page - 1) {
              onPageChange(nextPagination.pageIndex + 1);
            }
            if (nextPagination.pageSize !== pageSize) {
              onPageSizeChange(nextPagination.pageSize);
            }
          }}
          columnVisibility={columnVisibility}
          onRowClick={onRowClick}
          caption="CFPB Consumer Financial Complaints record explorer table"
          emptyTitle="No complaints match these filters"
          emptyMessage="Try widening your date range, clearing specific product selections, or resetting search filters."
        />
      </div>

      {/* Mobile Stacked-List View (< 768px) */}
      <div className="block md:hidden space-y-3" data-testid="mobile-complaints-list">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={`mobile-skeleton-${i}`}
              className="rounded-lg border border-border bg-card p-3 space-y-2 animate-pulse"
            >
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-3 bg-muted rounded w-2/3" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </div>
          ))
        ) : complaints.length === 0 ? (
          <div className="rounded-lg border border-border bg-card p-6 text-center text-xs text-muted-foreground space-y-2">
            <p className="font-medium text-foreground">No complaints match these filters</p>
            <p>Try clearing filters to view available complaints.</p>
            {onClearFilters && (
              <Button variant="outline" size="sm" onClick={onClearFilters} className="mt-2">
                Clear Filters
              </Button>
            )}
          </div>
        ) : (
          complaints.map((complaint) => (
            <div
              key={complaint.complaint_id}
              onClick={() => onRowClick(complaint)}
              tabIndex={0}
              role="button"
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onRowClick(complaint);
                }
              }}
              className="rounded-lg border border-border bg-card p-3.5 space-y-2 hover:bg-muted/40 cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              data-testid={`mobile-complaint-card-${complaint.complaint_id}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-accent text-xs">
                  #{complaint.complaint_id}
                </span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {formatDate(complaint.date_submitted)}
                </span>
              </div>

              <div>
                <div className="text-xs font-semibold text-foreground">
                  {complaint.category}
                  {complaint.sub_category && (
                    <span className="text-muted-foreground font-normal"> · {complaint.sub_category}</span>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">
                  {complaint.issue}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-border/50 text-[10px]">
                {complaint.timely_response === "yes" ? (
                  <Badge variant="positive" dot className="px-1.5 py-0">
                    Timely
                  </Badge>
                ) : complaint.timely_response === "no" ? (
                  <Badge variant="negative" dot className="px-1.5 py-0">
                    Untimely
                  </Badge>
                ) : (
                  <Badge variant="neutral" dot className="px-1.5 py-0">
                    In Progress
                  </Badge>
                )}

                <span className="text-muted-foreground">{complaint.company_response}</span>

                {complaint.is_anomaly && (
                  <Badge variant="negative" className="ml-auto px-1.5 py-0 gap-1">
                    <AlertTriangle className="h-2.5 w-2.5" />
                    <span>Outlier</span>
                  </Badge>
                )}
              </div>
            </div>
          ))
        )}

        {/* Mobile Pagination Controls */}
        {total > 0 && (
          <div className="flex items-center justify-between pt-2 px-1 text-xs text-muted-foreground">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </Button>
            <span>
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
