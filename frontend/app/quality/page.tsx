"use client";

import React, { useState, useTransition, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { AlertCircle, RefreshCw, ShieldAlert } from "lucide-react";
import { api, ApiError } from "@/lib/api/client";
import { ScorePanel } from "@/components/quality/ScorePanel";
import { DimensionBars } from "@/components/quality/DimensionBars";
import { AnomalySummary } from "@/components/quality/AnomalySummary";
import { ModelPanel } from "@/components/quality/ModelPanel";
import { Limitations } from "@/components/quality/Limitations";
import { AnomaliesTable } from "@/components/tables/AnomaliesTable";
import { ComplaintSheet } from "@/components/complaints/ComplaintSheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function QualityPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  // Selected complaint deep-link
  const selectedId = searchParams.get("selected");

  // Anomaly table pagination state
  const [anomalyPage, setAnomalyPage] = useState(1);
  const [anomalyPageSize, setAnomalyPageSize] = useState(25);

  // Fetch Quality Summary
  const {
    data: summaryData,
    isLoading: summaryLoading,
    isError: summaryError,
    error: summaryErrObj,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ["quality-summary"],
    queryFn: () => api.getQualitySummary(),
    staleTime: 60_000,
  });

  // Fetch Quality Anomalies
  const {
    data: anomaliesData,
    isLoading: anomaliesLoading,
    isError: anomaliesError,
    error: anomaliesErrObj,
    refetch: refetchAnomalies,
  } = useQuery({
    queryKey: ["quality-anomalies", anomalyPage, anomalyPageSize],
    queryFn: () =>
      api.getQualityAnomalies({
        page: anomalyPage,
        page_size: anomalyPageSize,
      }),
    staleTime: 60_000,
  });

  // Open detail sheet
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

  // Close detail sheet
  const handleCloseDetail = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("selected");
    const query = params.toString();
    startTransition(() => {
      router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
    });
  }, [pathname, router, searchParams]);

  // Handle 503 / Backend Service Unavailable
  const is503 =
    (summaryError && summaryErrObj instanceof ApiError && summaryErrObj.status === 503) ||
    (anomaliesError && anomaliesErrObj instanceof ApiError && anomaliesErrObj.status === 503);

  return (
    <div className="space-y-6" data-testid="data-quality-page">
      {/* Page Header */}
      <header className="border-b border-border pb-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Data Quality Center
            </h1>
            <p className="text-xs text-muted-foreground mt-1">
              Pipeline data quality score, dimension breakdown, anomaly observations, and model metadata
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchSummary();
              refetchAnomalies();
            }}
            className="text-xs gap-1.5 h-8"
            aria-label="Refresh quality analytics data"
          >
            <RefreshCw className="h-3 w-3" />
            <span>Refresh</span>
          </Button>
        </div>
      </header>

      {/* 503 / Service Unavailable Fallback */}
      {is503 ? (
        <Card className="border border-destructive/40 bg-destructive/10 p-6" data-testid="quality-503-panel">
          <div className="flex flex-col items-center justify-center text-center space-y-3">
            <ShieldAlert className="h-10 w-10 text-destructive" />
            <h2 className="text-base font-bold text-foreground">Data Quality Report Unavailable (503)</h2>
            <p className="text-xs text-muted-foreground max-w-md leading-relaxed">
              The Data Quality report and anomaly evaluation files were not found in pipeline storage.
              Please ensure the Gold quality transformation step has completed.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchSummary();
                refetchAnomalies();
              }}
              className="mt-2 text-xs"
            >
              Retry Connection
            </Button>
          </div>
        </Card>
      ) : summaryLoading ? (
        <div className="space-y-6" role="status" aria-label="Loading quality metrics">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Skeleton className="h-32 lg:col-span-2 rounded-lg" />
            <Skeleton className="h-32 rounded-lg" />
          </div>
          <Skeleton className="h-44 w-full rounded-lg" />
          <Skeleton className="h-64 w-full rounded-lg" />
        </div>
      ) : summaryError ? (
        <Card className="border border-destructive/40 bg-destructive/10 p-6" data-testid="quality-error-panel">
          <div className="flex items-center gap-3 text-destructive font-medium text-sm">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>Failed to load Data Quality Center summary</span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {summaryErrObj instanceof Error ? summaryErrObj.message : "An unexpected error occurred."}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetchSummary()} className="mt-3 text-xs">
            Retry
          </Button>
        </Card>
      ) : summaryData ? (
        <>
          {/* 1. Score Panel & How to Read side card */}
          <ScorePanel
            score={summaryData.overall_quality_score}
            status={summaryData.status}
            totalRecords={summaryData.total_records}
            analysisDate={summaryData.timestamps?.quality_analysis_at}
            reportRefreshedAt={summaryData.timestamps?.report_object_refreshed_at}
          />

          {/* 2. Methodological Limitations (Always Visible without interaction per AC-9.5) */}
          <Limitations limitations={summaryData.limitations} />

          {/* 3. Five Decomposed Dimension Bars */}
          <DimensionBars dimensions={summaryData.dimensions || []} />

          {/* 4. Anomaly Summary KPIs & Distributions */}
          {summaryData.anomalies && <AnomalySummary summary={summaryData.anomalies} />}

          {/* 5. Browsable Anomaly Records Table */}
          <AnomaliesTable
            anomalies={anomaliesData?.items ?? []}
            total={anomaliesData?.total ?? summaryData.anomalies?.flagged ?? 0}
            page={anomalyPage}
            pageSize={anomalyPageSize}
            totalPages={anomaliesData?.total_pages ?? 1}
            loading={anomaliesLoading}
            error={anomaliesError ? anomaliesErrObj : undefined}
            onRetry={() => refetchAnomalies()}
            onPageChange={(p) => setAnomalyPage(p)}
            onPageSizeChange={(ps) => {
              setAnomalyPageSize(ps);
              setAnomalyPage(1);
            }}
            onRowClick={(id) => handleOpenDetail(id)}
          />

          {/* 6. Model Parameters & Run Metadata Panel */}
          <ModelPanel model={summaryData.model} />
        </>
      ) : null}

      {/* Deep-Linked Complaint Detail Sheet */}
      <ComplaintSheet
        complaintId={selectedId}
        isOpen={Boolean(selectedId)}
        onClose={handleCloseDetail}
      />
    </div>
  );
}
