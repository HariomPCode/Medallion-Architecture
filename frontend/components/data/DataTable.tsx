"use client";

import React, { useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  PaginationState,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataState } from "./DataState";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export type ColumnAlignment = "left" | "center" | "right";

export interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[];
  data: TData[];
  loading?: boolean;
  error?: unknown;
  emptyTitle?: string;
  emptyMessage?: string;
  onRetry?: () => void;
  getRowId?: (row: TData, index: number) => string;
  // Sorting options
  defaultSorting?: SortingState;
  onSortingChange?: (sorting: SortingState) => void;
  manualSorting?: boolean;
  // Pagination options
  pageSize?: number;
  pageSizeOptions?: number[];
  manualPagination?: boolean;
  pageCount?: number;
  pageIndex?: number;
  totalRows?: number;
  onPaginationChange?: (pagination: PaginationState) => void;
  className?: string;
}

/**
 * Reusable, accessible, keyboard-friendly data table for financial and complaint intelligence.
 * Supports client-side or server-driven sorting and pagination with stable row keys.
 */
export function DataTable<TData>({
  columns,
  data,
  loading = false,
  error,
  emptyTitle = "No records found",
  emptyMessage = "There are no records matching your current filter criteria.",
  onRetry,
  getRowId,
  defaultSorting = [],
  onSortingChange: onSortingChangeProp,
  manualSorting = false,
  pageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
  manualPagination = false,
  pageCount,
  pageIndex: controlledPageIndex,
  totalRows,
  onPaginationChange: onPaginationChangeProp,
  className,
}: DataTableProps<TData>) {
  // Internal state for sorting if not controlled externally
  const [internalSorting, setInternalSorting] = useState<SortingState>(defaultSorting);
  const sorting = internalSorting;

  // Internal state for pagination if not controlled externally
  const [internalPagination, setInternalPagination] = useState<PaginationState>({
    pageIndex: controlledPageIndex ?? 0,
    pageSize,
  });
  const pagination = {
    pageIndex: controlledPageIndex ?? internalPagination.pageIndex,
    pageSize: internalPagination.pageSize,
  };

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      pagination,
    },
    getRowId,
    manualSorting,
    manualPagination,
    pageCount: manualPagination ? pageCount : undefined,
    onSortingChange: (updater) => {
      const nextSorting = typeof updater === "function" ? updater(sorting) : updater;
      setInternalSorting(nextSorting);
      onSortingChangeProp?.(nextSorting);
    },
    onPaginationChange: (updater) => {
      const nextPagination = typeof updater === "function" ? updater(pagination) : updater;
      setInternalPagination(nextPagination);
      onPaginationChangeProp?.(nextPagination);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: manualSorting ? undefined : getSortedRowModel(),
    getPaginationRowModel: manualPagination ? undefined : getPaginationRowModel(),
  });

  const totalRowCount = totalRows ?? data.length;
  const currentPage = table.getState().pagination.pageIndex;
  const currentPageSize = table.getState().pagination.pageSize;
  const computedPageCount = table.getPageCount();

  const startRow = totalRowCount === 0 ? 0 : currentPage * currentPageSize + 1;
  const endRow = Math.min((currentPage + 1) * currentPageSize, totalRowCount);

  if (error) {
    return (
      <div className={cn("rounded-lg border border-border p-4 bg-card", className)}>
        <DataState error={error} onRetry={onRetry} />
      </div>
    );
  }

  return (
    <div className={cn("space-y-3 w-full", className)}>
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-xs text-left border-collapse" role="table">
            <thead className="bg-muted/60 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const canSort = header.column.getCanSort();
                    const isSorted = header.column.getIsSorted();
                    const meta = header.column.columnDef.meta as
                      | { align?: ColumnAlignment }
                      | undefined;
                    const align = meta?.align || "left";

                    return (
                      <th
                        key={header.id}
                        scope="col"
                        className={cn(
                          "px-3.5 py-2.5 font-medium select-none whitespace-nowrap",
                          align === "right" && "text-right",
                          align === "center" && "text-center",
                          align === "left" && "text-left"
                        )}
                        aria-sort={
                          isSorted === "asc"
                            ? "ascending"
                            : isSorted === "desc"
                            ? "descending"
                            : "none"
                        }
                      >
                        {header.isPlaceholder ? null : canSort ? (
                          <button
                            type="button"
                            onClick={header.column.getToggleSortingHandler()}
                            className={cn(
                              "inline-flex items-center gap-1.5 hover:text-foreground font-medium rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors",
                              align === "right" && "ml-auto"
                            )}
                            aria-label={`Sort by ${
                              typeof header.column.columnDef.header === "string"
                                ? header.column.columnDef.header
                                : header.id
                            }`}
                          >
                            <span>
                              {flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                            </span>
                            {isSorted === "asc" ? (
                              <ArrowUp className="w-3 h-3 text-accent shrink-0" aria-hidden="true" />
                            ) : isSorted === "desc" ? (
                              <ArrowDown className="w-3 h-3 text-accent shrink-0" aria-hidden="true" />
                            ) : (
                              <ArrowUpDown className="w-3 h-3 text-muted-foreground/60 shrink-0" aria-hidden="true" />
                            )}
                          </button>
                        ) : (
                          flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )
                        )}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>

            <tbody className="divide-y divide-border/60">
              {loading ? (
                // Loading Skeleton Rows
                Array.from({ length: 5 }).map((_, rIdx) => (
                  <tr key={`loading-row-${rIdx}`} className="bg-card">
                    {columns.map((_, cIdx) => (
                      <td key={`loading-col-${cIdx}`} className="px-3.5 py-3">
                        <Skeleton className="h-4 w-full max-w-[120px]" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="hover:bg-muted/40 transition-colors focus-within:bg-muted/40"
                  >
                    {row.getVisibleCells().map((cell) => {
                      const meta = cell.column.columnDef.meta as
                        | { align?: ColumnAlignment }
                        | undefined;
                      const align = meta?.align || "left";

                      let cellContent: React.ReactNode;
                      const cellDef = cell.column.columnDef.cell;

                      if (typeof cellDef === "function") {
                        try {
                          const result = (cellDef as Function)(cell.getContext());
                          cellContent =
                            result === null || result === undefined || result === ""
                              ? "—"
                              : result;
                        } catch {
                          cellContent = flexRender(cellDef, cell.getContext());
                        }
                      } else if (cellDef) {
                        cellContent = flexRender(cellDef, cell.getContext());
                      } else {
                        const val = cell.getValue();
                        cellContent =
                          val === null || val === undefined || val === ""
                            ? "—"
                            : String(val);
                      }

                      return (
                        <td
                          key={cell.id}
                          className={cn(
                            "px-3.5 py-2.5 text-foreground whitespace-nowrap",
                            align === "right" && "text-right tabular-nums font-mono",
                            align === "center" && "text-center",
                            align === "left" && "text-left"
                          )}
                        >
                          {cellContent}
                        </td>
                      );
                    })}
                  </tr>
                ))
              ) : (
                // Empty state row
                <tr>
                  <td
                    colSpan={columns.length}
                    className="h-36 text-center text-muted-foreground p-6"
                  >
                    <DataState
                      empty={true}
                      emptyTitle={emptyTitle}
                      emptyMessage={emptyMessage}
                      minHeight="min-h-[120px]"
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination & Row Summary Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground px-1">
        <div className="tabular-nums" data-testid="table-pagination-summary">
          {totalRowCount > 0 ? (
            <span>
              Showing <span className="font-semibold text-foreground">{startRow}</span> to{" "}
              <span className="font-semibold text-foreground">{endRow}</span> of{" "}
              <span className="font-semibold text-foreground">{formatNumber(totalRowCount)}</span>{" "}
              entries
            </span>
          ) : (
            <span>0 entries</span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Rows per page selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Rows per page</span>
            <select
              value={table.getState().pagination.pageSize}
              onChange={(e) => {
                table.setPageSize(Number(e.target.value));
              }}
              className="h-8 rounded border border-border bg-card px-2 py-1 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
              aria-label="Select rows per page"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>

          {/* Page counter & Navigation */}
          <div className="flex items-center gap-1">
            <span className="mr-1 tabular-nums">
              Page{" "}
              <span className="font-semibold text-foreground">
                {computedPageCount === 0 ? 0 : currentPage + 1}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-foreground">
                {computedPageCount}
              </span>
            </span>

            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage() || loading}
              className="h-8 w-8 p-0"
              aria-label="Go to previous page"
            >
              <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage() || loading}
              className="h-8 w-8 p-0"
              aria-label="Go to next page"
            >
              <ChevronRight className="w-4 h-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
