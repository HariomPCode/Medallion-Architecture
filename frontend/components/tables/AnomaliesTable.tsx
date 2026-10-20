"use client";

import React, { useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { AlertTriangle, Clock } from "lucide-react";
import { AnomalyListItem } from "@/lib/api/client";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatDecimal, formatNumber } from "@/lib/format";

export interface AnomaliesTableProps {
  anomalies: AnomalyListItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  onPageChange: (newPage: number) => void;
  onPageSizeChange: (newPageSize: number) => void;
  onRowClick: (complaintId: number) => void;
}

export function AnomaliesTable({
  anomalies,
  total,
  page,
  pageSize,
  totalPages,
  loading = false,
  error,
  onRetry,
  onPageChange,
  onPageSizeChange,
  onRowClick,
}: AnomaliesTableProps) {
  const columns = useMemo<ColumnDef<AnomalyListItem, any>[]>(
    () => [
      {
        accessorKey: "complaint_id",
        header: "Complaint ID",
        enableSorting: false,
        cell: ({ row }) => (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRowClick(row.original.complaint_id);
            }}
            className="font-mono font-semibold text-accent hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded px-1 -mx-1"
            aria-label={`View anomaly details for complaint #${row.original.complaint_id}`}
          >
            #{row.original.complaint_id}
          </button>
        ),
      },
      {
        accessorKey: "date_submitted",
        header: "Date Submitted",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="font-mono text-muted-foreground whitespace-nowrap">
            {formatDate(row.original.date_submitted)}
          </span>
        ),
      },
      {
        accessorKey: "category",
        header: "Category",
        enableSorting: false,
        cell: ({ row }) => <span className="font-medium text-foreground">{row.original.category}</span>,
      },
      {
        accessorKey: "sub_category",
        header: "Sub-Category",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground">{row.original.sub_category || "—"}</span>
        ),
      },
      {
        accessorKey: "company_response",
        header: "Company Response",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-foreground/90 whitespace-nowrap">{row.original.company_response}</span>
        ),
      },
      {
        accessorKey: "days_submitted_to_received",
        header: "Routing Delay",
        enableSorting: false,
        meta: { align: "right" },
        cell: ({ row }) => {
          const days = row.original.days_submitted_to_received;
          return (
            <span className="font-mono text-foreground whitespace-nowrap">
              {days !== null && days !== undefined ? `${days}d` : "—"}
            </span>
          );
        },
      },
      {
        accessorKey: "anomaly_score",
        header: "Outlier Score",
        enableSorting: false,
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="font-mono text-destructive font-semibold">
            {formatDecimal(row.original.anomaly_score, 4)}
          </span>
        ),
      },
      {
        id: "annotations",
        header: "Factual Observations",
        enableSorting: false,
        cell: ({ row }) => {
          const { annotations } = row.original;
          return (
            <div className="flex flex-wrap items-center gap-1">
              {annotations.open_case && (
                <Badge variant="neutral" className="text-[10px] px-1.5 py-0">
                  Open case
                </Badge>
              )}
              {annotations.long_routing_delay && (
                <Badge variant="warning" className="text-[10px] px-1.5 py-0">
                  Delay ≥ 7 days
                </Badge>
              )}
              {annotations.timely_no && (
                <Badge variant="negative" className="text-[10px] px-1.5 py-0">
                  Late response
                </Badge>
              )}
            </div>
          );
        },
      },
    ],
    [onRowClick]
  );

  return (
    <div className="space-y-3 w-full" data-testid="anomalies-table-container">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div>
          <h3 className="text-sm font-bold text-foreground">
            Statistical Outlier Records
          </h3>
          <p className="text-xs text-muted-foreground">
            Statistically unusual records; many are open cases ({formatNumber(total)} total)
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={anomalies}
        loading={loading}
        error={error}
        onRetry={onRetry}
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
        onRowClick={(row) => onRowClick(row.complaint_id)}
        caption="Statistically unusual records; many are open cases"
        emptyTitle="No outlier records found"
        emptyMessage="There are no statistical anomaly records matching the selected parameters."
      />

      <p className="text-[11px] text-muted-foreground italic px-1">
        * Annotations indicate factual characteristics (e.g. open status or long intake lag), not ML feature importances.
      </p>
    </div>
  );
}
