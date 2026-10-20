import React from "react";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  Database,
  FileCode,
  AlertCircle,
  Clock,
  WifiOff,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type DatasetStatus =
  | "ready"
  | "live"
  | "local_snapshot"
  | "fixture"
  | "degraded"
  | "stale"
  | "down"
  | "unavailable";

export interface DatasetStatusPillProps {
  status?: DatasetStatus;
  showIcon?: boolean;
  className?: string;
}

interface StatusConfig {
  variant: "positive" | "warning" | "negative" | "neutral";
  label: string;
  accessibleText: string;
  Icon: React.ElementType;
}

const STATUS_CONFIGS: Record<DatasetStatus, StatusConfig> = {
  ready: {
    variant: "positive",
    label: "Snapshot Verified · 2017–2023",
    accessibleText: "Dataset status: Live verified snapshot covering 2017 to 2023",
    Icon: CheckCircle2,
  },
  live: {
    variant: "positive",
    label: "Snapshot Verified · 2017–2023",
    accessibleText: "Dataset status: Live verified snapshot covering 2017 to 2023",
    Icon: CheckCircle2,
  },
  local_snapshot: {
    variant: "warning",
    label: "Local Snapshot · 62,516 rows",
    accessibleText: "Dataset status: Reproducible local snapshot containing 62,516 complaints",
    Icon: Database,
  },
  fixture: {
    variant: "warning",
    label: "Fixture Snapshot · Offline",
    accessibleText: "Dataset status: Test fixture snapshot running offline",
    Icon: FileCode,
  },
  degraded: {
    variant: "warning",
    label: "Degraded · Partial Dataset",
    accessibleText: "Dataset status: Degraded mode with partial data coverage",
    Icon: AlertCircle,
  },
  stale: {
    variant: "warning",
    label: "Stale Snapshot · Refresh Due",
    accessibleText: "Dataset status: Stale dataset snapshot requiring refresh",
    Icon: Clock,
  },
  down: {
    variant: "negative",
    label: "Backend Offline",
    accessibleText: "Dataset status: Backend analytics service unreachable",
    Icon: WifiOff,
  },
  unavailable: {
    variant: "negative",
    label: "Backend Unavailable",
    accessibleText: "Dataset status: Backend service unavailable",
    Icon: WifiOff,
  },
};

/**
 * Compact, accessible dataset-status indicator.
 * Combines semantic text, accessible aria-labels, and distinct icons without relying on color alone.
 */
export function DatasetStatusPill({
  status = "local_snapshot",
  showIcon = true,
  className,
}: DatasetStatusPillProps) {
  const config = STATUS_CONFIGS[status] || STATUS_CONFIGS.local_snapshot;
  const { variant, label, accessibleText, Icon } = config;

  return (
    <Badge
      variant={variant}
      dot
      className={cn("inline-flex items-center gap-1.5 font-normal", className)}
      aria-label={accessibleText}
      role="status"
    >
      {showIcon && <Icon className="w-3 h-3 shrink-0" aria-hidden="true" />}
      <span className="truncate">{label}</span>
    </Badge>
  );
}
