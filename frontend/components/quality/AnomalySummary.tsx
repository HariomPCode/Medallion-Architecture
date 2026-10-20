"use client";

import React from "react";
import { AlertCircle, HelpCircle, FileText } from "lucide-react";
import {
  AnomalySummaryBlock,
  CategoryAnomalyItem,
  CompanyResponseAnomalyItem,
} from "@/lib/api/client";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatNumber, formatDecimal } from "@/lib/format";

export interface AnomalySummaryProps {
  summary: AnomalySummaryBlock;
}

export function AnomalySummary({ summary }: AnomalySummaryProps) {
  return (
    <Card className="border border-border bg-card" data-testid="anomaly-summary-panel">
      <CardHeader className="pb-3 border-b border-border/60">
        <div>
          <CardTitle as="h2" className="text-sm font-bold text-foreground">
            Distributional Outlier Summary
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            Statistically unusual records; many are open cases
          </p>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-4">
        {/* Top KPIs Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Flagged Records
            </span>
            <div className="text-2xl font-bold font-mono text-foreground" data-testid="flagged-count">
              {formatNumber(summary.flagged)}
            </div>
            <p className="text-[10px] text-muted-foreground">Statistical outliers in dataset</p>
          </div>

          <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Flagged Proportion
            </span>
            <div className="text-2xl font-bold font-mono text-foreground" data-testid="flagged-rate">
              {formatDecimal(summary.rate_pct, 2)}%
            </div>
            <p className="text-[10px] text-muted-foreground">Of 62,516 total silver records</p>
          </div>

          <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Open Cases Share
            </span>
            <div className="text-2xl font-bold font-mono text-foreground" data-testid="open-cases-share">
              {summary.in_progress_share_pct !== null && summary.in_progress_share_pct !== undefined
                ? `${formatDecimal(summary.in_progress_share_pct, 1)}%`
                : "—"}
            </div>
            <p className="text-[10px] text-muted-foreground">Share that are in-progress cases</p>
          </div>
        </div>

        {/* Distributions Grid: By Category & By Company Response */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* By Category */}
          <div className="rounded-lg border border-border p-3.5 space-y-2.5">
            <span className="text-xs font-semibold text-foreground block">
              Outlier Distribution by Category
            </span>
            <div className="space-y-2 text-xs">
              {summary.by_category?.map((cat: CategoryAnomalyItem) => (
                <div key={cat.category} className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground truncate">{cat.category}</span>
                  <div className="flex items-center gap-2 font-mono shrink-0">
                    <span className="text-foreground font-semibold">{formatNumber(cat.flagged)}</span>
                    <span className="text-[10px] text-muted-foreground">
                      ({formatDecimal(cat.rate_pct, 1)}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* By Company Response */}
          <div className="rounded-lg border border-border p-3.5 space-y-2.5">
            <span className="text-xs font-semibold text-foreground block">
              Outlier Distribution by Company Response
            </span>
            <div className="space-y-2 text-xs">
              {summary.by_company_response?.map((cr: CompanyResponseAnomalyItem) => (
                <div key={cr.company_response} className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground truncate">{cr.company_response}</span>
                  <div className="flex items-center gap-2 font-mono shrink-0">
                    <span className="text-foreground font-semibold">{formatNumber(cr.flagged)}</span>
                    <span className="text-[10px] text-muted-foreground">
                      ({formatDecimal(cr.rate_pct, 1)}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Informative Caveat Notice */}
        <div className="rounded-md border border-border/80 bg-muted/30 p-3 text-xs text-muted-foreground leading-relaxed flex items-start gap-2.5">
          <HelpCircle className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" />
          <p>
            The Isolation Forest detector isolates multivariate outliers across joint feature
            spaces (including routing delay, submission channel, and response outcome). Flagged
            records represent rare combinations rather than procedural violations or irregular
            submissions.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
