"use client";

import React from "react";
import { ShieldCheck, Info, Clock, Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatDecimal, formatNumber, formatDate } from "@/lib/format";

export interface ScorePanelProps {
  score: number;
  status: "HIGH QUALITY" | "MODERATE QUALITY" | "LOW QUALITY";
  totalRecords: number;
  analysisDate?: string | null;
  reportRefreshedAt?: string | null;
}

export function ScorePanel({
  score,
  status,
  totalRecords,
  analysisDate,
  reportRefreshedAt,
}: ScorePanelProps) {
  const badgeVariant =
    status === "HIGH QUALITY"
      ? "positive"
      : status === "MODERATE QUALITY"
      ? "warning"
      : "negative";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="quality-score-panel">
      {/* Primary Score Tile */}
      <Card className="lg:col-span-2 border border-border bg-card">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Pipeline Composite Score
            </span>
            <Badge variant={badgeVariant} dot data-testid="quality-status-badge">
              {status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-1">
          <div className="flex flex-wrap items-baseline gap-3">
            <span className="text-4xl font-extrabold tracking-tight text-foreground font-mono" data-testid="composite-score-value">
              {formatDecimal(score, 1)}
            </span>
            <span className="text-sm font-medium text-muted-foreground">/ 100</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 border-t border-border/60 pt-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-muted-foreground/70 shrink-0" />
              <span>
                Evaluated: <strong className="text-foreground font-mono">{formatNumber(totalRecords)}</strong> records
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground/70 shrink-0" />
              <span>
                Analysis Run:{" "}
                <strong className="text-foreground">
                  {analysisDate ? formatDate(analysisDate) : "Not published"}
                </strong>
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Compact How-to-Read Panel */}
      <Card className="border border-border bg-muted/20">
        <CardHeader className="pb-2">
          <CardTitle as="h2" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 text-accent" />
            <span>How to Read This Score</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-muted-foreground leading-relaxed pt-1">
          <p>
            The composite pipeline score is a weighted multi-attribute index synthesizing
            Completeness (25%), Validity (25%), Consistency (20%), Timeliness (15%), and
            Distributional Normality (15%).
          </p>
          <p className="text-[11px] italic text-muted-foreground/80 border-t border-border/50 pt-2">
            This metric evaluates pipeline execution and contract conformance; it does not measure
            procedural accuracy or consumer factual truthfulness.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
