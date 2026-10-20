"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";

interface DatasetStatusPillProps {
  status?: "ready" | "local_snapshot" | "fixture" | "degraded" | "down";
  className?: string;
}

export function DatasetStatusPill({
  status = "local_snapshot",
  className = "",
}: DatasetStatusPillProps) {
  if (status === "ready") {
    return (
      <Badge variant="positive" dot className={className}>
        Live Snapshot · 2017–2023
      </Badge>
    );
  }

  if (status === "local_snapshot") {
    return (
      <Badge variant="warning" dot className={className}>
        Local Snapshot · 62,516 records
      </Badge>
    );
  }

  if (status === "fixture") {
    return (
      <Badge variant="warning" dot className={className}>
        Fixture Data · Offline
      </Badge>
    );
  }

  if (status === "down") {
    return (
      <Badge variant="negative" dot className={className}>
        Backend Offline
      </Badge>
    );
  }

  return (
    <Badge variant="neutral" dot className={className}>
      Dataset Synchronized
    </Badge>
  );
}
