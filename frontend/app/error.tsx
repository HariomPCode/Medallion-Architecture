"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log sanitized error message without sensitive state
    console.error("Application error boundary triggered:", error.message);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full border-status-error/30 bg-card text-center">
        <CardHeader className="flex flex-col items-center space-y-2 pb-2">
          <div className="h-12 w-12 rounded-full bg-status-error/10 text-status-error flex items-center justify-center">
            <AlertCircle className="h-6 w-6" aria-hidden="true" />
          </div>
          <CardTitle as="h2" className="text-status-error">
            Application Error
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-2">
          <p className="text-xs text-muted-foreground">
            An unexpected error occurred while rendering this view. Your filter and
            navigation context are preserved.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Button variant="default" size="sm" onClick={() => reset()} className="gap-1.5">
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Try Again</span>
            </Button>
            <Link href="/">
              <Button variant="outline" size="sm">
                Overview
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
