"use client";

import React, { useState } from "react";
import { Cpu, Copy, Check, Info } from "lucide-react";
import { ModelMetadata } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export interface ModelPanelProps {
  model?: ModelMetadata | null;
}

export function ModelPanel({ model }: ModelPanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyRunId = (runId: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(runId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // If run metadata is missing or model not published
  if (!model || !model.available) {
    return (
      <Card className="border border-border bg-card" data-testid="model-panel">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-muted-foreground" />
            <CardTitle as="h2" className="text-sm font-bold text-foreground">
              Isolation Forest Model & Run Metadata
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-4 text-xs space-y-2">
          <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2" data-testid="model-not-published-notice">
            <div className="flex items-center gap-2 font-semibold text-foreground">
              <Info className="h-4 w-4 text-muted-foreground" />
              <span>Model parameters not published by the latest pipeline run</span>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              The Isolation Forest scoring artifact was generated using documented baseline
              hyperparameters (Contamination: 1.0%, 100 Estimators) rather than an MLflow tracked
              artifact. This does not prevent anomaly scoring.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border bg-card" data-testid="model-panel">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-accent" />
            <CardTitle as="h2" className="text-sm font-bold text-foreground">
              Isolation Forest Model & Provenance
            </CardTitle>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono">
            Source: {model.source === "run_metadata" ? "MLflow Run" : "Notebook Constants"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4 text-xs">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded border border-border/80 bg-muted/20 p-3">
            <span className="text-[11px] text-muted-foreground uppercase font-semibold block">
              Algorithm Type
            </span>
            <span className="font-mono font-medium text-foreground text-sm mt-0.5 block">
              {model.type || "IsolationForest"}
            </span>
          </div>

          <div className="rounded border border-border/80 bg-muted/20 p-3">
            <span className="text-[11px] text-muted-foreground uppercase font-semibold block">
              Contamination Rate
            </span>
            <span className="font-mono font-medium text-foreground text-sm mt-0.5 block">
              {(model.contamination * 100).toFixed(1)}% ({model.contamination})
            </span>
          </div>

          <div className="rounded border border-border/80 bg-muted/20 p-3">
            <span className="text-[11px] text-muted-foreground uppercase font-semibold block">
              Ensemble Estimators
            </span>
            <span className="font-mono font-medium text-foreground text-sm mt-0.5 block">
              {model.n_estimators} trees
            </span>
          </div>
        </div>

        {/* Features list */}
        {model.features && model.features.length > 0 && (
          <div className="space-y-1.5 border-t border-border/60 pt-3">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Trained Feature Vector
            </span>
            <div className="flex flex-wrap gap-1.5">
              {model.features.map((feat: string) => (
                <code
                  key={feat}
                  className="rounded bg-muted px-2 py-0.5 font-mono text-[11px] text-foreground border border-border/50"
                >
                  {feat}
                </code>
              ))}
            </div>
          </div>
        )}

        {/* MLflow Run ID with copy button */}
        {model.mlflow_run_id && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">MLflow Run ID:</span>
              <code className="rounded bg-muted px-2 py-0.5 font-mono text-[11px] text-foreground font-semibold">
                {model.mlflow_run_id}
              </code>
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleCopyRunId(model.mlflow_run_id!)}
              className="h-7 text-xs gap-1.5"
              data-testid="copy-run-id-button"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-success" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy ID</span>
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
