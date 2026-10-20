"use client";

import React from "react";
import { Info, HelpCircle } from "lucide-react";
import { QualityDimension } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatDecimal } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface DimensionBarsProps {
  dimensions: QualityDimension[];
}

export function DimensionBars({ dimensions }: DimensionBarsProps) {
  return (
    <Card className="border border-border bg-card" data-testid="dimension-bars-panel">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle as="h2" className="text-sm font-bold text-foreground">
              Quality Dimensions Breakdown
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              Five decomposed dimensions contributing to the composite pipeline index
            </p>
          </div>
          <span className="text-xs text-muted-foreground font-mono">Formula: Σ (Weight × Value)</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-4">
        {dimensions.map((dim) => {
          const isMlNormality = dim.id === "ml_normality" || dim.label.toLowerCase().includes("ml normality");
          const weightPct = Math.round(dim.weight * 100);

          // Color scale based on score
          const barColor =
            dim.value >= 90
              ? "bg-success"
              : dim.value >= 80
              ? "bg-warning"
              : "bg-destructive";

          return (
            <div
              key={dim.id}
              className="space-y-1.5 border-b border-border/40 pb-4 last:border-0 last:pb-0"
              data-testid={`dimension-row-${dim.id}`}
            >
              {/* Header row: Label, Weight, Score */}
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-foreground">{dim.label}</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-normal">
                    Weight: {weightPct}%
                  </Badge>

                  {/* ML Normality specific constraint badge */}
                  {isMlNormality && (
                    <a
                      href="#methodological-limitations"
                      className="inline-flex items-center gap-1 text-[10px] text-warning bg-warning/10 border border-warning/30 rounded px-1.5 py-0.5 hover:bg-warning/20 transition-colors"
                      title="Click to view contamination setting constraint"
                      data-testid="ml-normality-marker"
                    >
                      <Info className="h-3 w-3" />
                      <span>fixed by contamination setting (1.0%)</span>
                    </a>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-foreground text-sm">
                    {formatDecimal(dim.value, 1)}%
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div
                className="h-2 w-full rounded-full bg-muted overflow-hidden"
                role="progressbar"
                aria-valuenow={dim.value}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${dim.label} score: ${dim.value.toFixed(1)} percent`}
              >
                <div
                  className={cn("h-full rounded-full transition-all duration-500", barColor)}
                  style={{ width: `${Math.min(100, Math.max(0, dim.value))}%` }}
                />
              </div>

              {/* Definition & Contextual Note */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-muted-foreground pt-0.5">
                <p className="leading-normal">{dim.definition}</p>
                {dim.note && (
                  <span className="italic text-muted-foreground/80 shrink-0 sm:text-right">
                    {dim.note}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
