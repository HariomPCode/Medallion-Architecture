"use client";

import React from "react";
import { AlertCircle, ShieldAlert, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export interface LimitationsProps {
  limitations?: string[];
}

const DEFAULT_LIMITATIONS = [
  "Isolation Forest identifies statistical outliers based on multi-attribute density, not procedural errors, fraud, or data inaccuracies.",
  "ML Normality dimension score is structurally bounded by the contamination hyperparameter (1.0% expected outliers).",
  "Intake routing lag ('Days submitted to received') measures CFPB agency routing delay and is not an evaluation of company response time.",
  "Open/in-progress cases have not received a company outcome and are excluded from the primary timeliness denominator.",
];

/**
 * Methodological Caveats and Audit Limitations panel.
 * Per AC-9.5, this panel is ALWAYS visible on the page without user interaction.
 */
export function Limitations({ limitations }: LimitationsProps) {
  const items = limitations && limitations.length > 0 ? limitations : DEFAULT_LIMITATIONS;

  return (
    <Card
      id="methodological-limitations"
      className="border border-border bg-card"
      data-testid="limitations-panel"
    >
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-warning" />
          <CardTitle as="h2" className="text-sm font-bold text-foreground">
            Methodological Caveats & Data Limitations
          </CardTitle>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Mandatory audit disclosures regarding data collection, ML scoring bounds, and metric definitions
        </p>
      </CardHeader>

      <CardContent className="pt-4 text-xs space-y-3">
        <ul className="space-y-2.5" role="list">
          {items.map((limitation, index) => (
            <li
              key={index}
              className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3 leading-relaxed text-foreground/90"
              data-testid={`limitation-item-${index}`}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground font-mono">
                {index + 1}
              </span>
              <span>{limitation}</span>
            </li>
          ))}
        </ul>

        <div className="rounded border border-border/50 bg-muted/10 p-2.5 text-[11px] text-muted-foreground leading-normal mt-2">
          <strong>Compliance Notice:</strong> These limitations are published transparently to prevent
          misattribution of agency routing lag to financial institutions and to clarify that statistical
          outliers are not regulatory violations.
        </div>
      </CardContent>
    </Card>
  );
}
