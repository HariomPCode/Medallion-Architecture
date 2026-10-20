"use client";

import React, { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { X, AlertCircle, HelpCircle, ShieldAlert, CheckCircle2, Clock } from "lucide-react";
import { api, ApiError, ComplaintDetail } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatNullable } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface ComplaintSheetProps {
  complaintId: number | string | null;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Slide-out detail sheet for inspecting individual complaint records.
 * Follows CFPB routing delay disclosures and strict language rules (§15.4).
 */
export function ComplaintSheet({ complaintId, isOpen, onClose }: ComplaintSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  // Capture active element before opening to restore focus on close
  useEffect(() => {
    if (isOpen) {
      previousActiveElementRef.current = document.activeElement as HTMLElement;
      // Focus close button on open
      setTimeout(() => {
        closeButtonRef.current?.focus();
      }, 50);
    } else if (previousActiveElementRef.current) {
      previousActiveElementRef.current.focus();
      previousActiveElementRef.current = null;
    }
  }, [isOpen]);

  // Handle Escape key and focus trap
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === "Tab" && sheetRef.current) {
        const focusable = sheetRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Fetch complaint details
  const { data: complaint, isLoading, isError, error, refetch } = useQuery<ComplaintDetail>({
    queryKey: ["complaint-detail", complaintId],
    queryFn: () => api.getComplaintById(complaintId!),
    enabled: isOpen && Boolean(complaintId),
    staleTime: 60_000,
  });

  if (!isOpen) return null;

  const isNotFound =
    isError &&
    error instanceof ApiError &&
    (error.status === 404 || error.code === "NOT_FOUND");

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-background/80 backdrop-blur-sm transition-all duration-200"
      aria-modal="true"
      role="dialog"
      aria-labelledby="complaint-sheet-title"
      aria-describedby="complaint-sheet-description"
      data-testid="complaint-sheet"
    >
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 cursor-pointer"
        onClick={onClose}
        aria-hidden="true"
        data-testid="complaint-sheet-backdrop"
      />

      {/* Sheet Content Panel */}
      <div
        ref={sheetRef}
        className="relative z-10 flex h-full w-full flex-col border-l border-border bg-card shadow-2xl transition-transform duration-300 sm:max-w-[480px]"
        tabIndex={-1}
      >
        {/* Header */}
        <header className="flex items-center justify-between border-b border-border px-5 py-4 bg-muted/30">
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Complaint Record Detail
            </span>
            <h2 id="complaint-sheet-title" className="text-base font-bold text-foreground">
              {complaint ? `Complaint #${complaint.complaint_id}` : `Complaint #${complaintId ?? ""}`}
            </h2>
          </div>
          <Button
            ref={closeButtonRef}
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close detail sheet"
            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
            data-testid="complaint-sheet-close"
          >
            <X className="h-4 w-4" />
          </Button>
        </header>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6 text-xs text-foreground">
          <p id="complaint-sheet-description" className="sr-only">
            Full record attributes including category, response, routing lag, and anomaly status.
          </p>

          {isLoading ? (
            <div className="space-y-4" role="status" aria-label="Loading complaint details">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : isNotFound ? (
            <div
              className="rounded-lg border border-border bg-muted/20 p-6 text-center space-y-3"
              data-testid="complaint-sheet-404"
            >
              <AlertCircle className="mx-auto h-8 w-8 text-muted-foreground/80" />
              <h3 className="text-sm font-semibold text-foreground">Complaint Record Not Found</h3>
              <p className="text-xs text-muted-foreground">
                Complaint ID <span className="font-mono font-medium">{complaintId}</span> does not
                exist in the dataset or may have been removed.
              </p>
              <Button variant="outline" size="sm" onClick={onClose} className="mt-2">
                Close Sheet
              </Button>
            </div>
          ) : isError ? (
            <div
              className="rounded-lg border border-destructive/30 bg-destructive/10 p-5 space-y-3"
              data-testid="complaint-sheet-error"
            >
              <div className="flex items-center gap-2 text-destructive font-medium">
                <AlertCircle className="h-4 w-4" />
                <span>Failed to load complaint details</span>
              </div>
              <p className="text-muted-foreground">
                {error instanceof Error ? error.message : "An unexpected network error occurred."}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          ) : complaint ? (
            <>
              {/* Overview Section */}
              <section className="space-y-2.5">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Classification & Issue
                </h3>
                <div className="rounded-lg border border-border bg-card p-3.5 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <div className="text-[11px] text-muted-foreground">Category</div>
                      <div className="font-medium text-foreground">{complaint.category}</div>
                    </div>
                    <div>
                      <div className="text-[11px] text-muted-foreground">Sub-Category</div>
                      <div className="font-medium text-foreground">{complaint.sub_category}</div>
                    </div>
                  </div>

                  <div className="border-t border-border/50 pt-2 grid grid-cols-2 gap-2">
                    <div>
                      <div className="text-[11px] text-muted-foreground">Product</div>
                      <div className="font-medium text-foreground">{complaint.product}</div>
                    </div>
                    <div>
                      <div className="text-[11px] text-muted-foreground">Sub-Product</div>
                      <div className="text-foreground">
                        {formatNullable(complaint.sub_product, "Not provided")}
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-border/50 pt-2">
                    <div className="text-[11px] text-muted-foreground">Issue</div>
                    <div className="font-medium text-foreground mt-0.5">{complaint.issue}</div>
                  </div>

                  <div className="border-t border-border/50 pt-2">
                    <div className="text-[11px] text-muted-foreground">Sub-Issue</div>
                    <div className="text-foreground mt-0.5">
                      {formatNullable(complaint.sub_issue, "Not provided")}
                    </div>
                  </div>
                </div>
              </section>

              {/* Dates & CFPB Routing Lag */}
              <section className="space-y-2.5">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Dates & Agency Routing
                </h3>
                <div className="rounded-lg border border-border bg-card p-3.5 space-y-2.5">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <div className="text-[11px] text-muted-foreground">Date Submitted</div>
                      <div className="font-mono font-medium text-foreground">
                        {formatDate(complaint.date_submitted)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] text-muted-foreground">Date Received (CFPB)</div>
                      <div className="font-mono font-medium text-foreground">
                        {formatDate(complaint.date_received, "—")}
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-border/50 pt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground">Intake Routing Lag</span>
                      <span className="font-mono font-semibold text-foreground">
                        {complaint.days_submitted_to_received !== null &&
                        complaint.days_submitted_to_received !== undefined
                          ? `${complaint.days_submitted_to_received} days`
                          : "—"}
                      </span>
                    </div>
                    <div className="mt-1 flex items-start gap-1.5 rounded bg-muted/40 p-2 text-[11px] text-muted-foreground leading-normal">
                      <HelpCircle className="h-3.5 w-3.5 shrink-0 text-muted-foreground mt-0.5" />
                      <span>
                        <strong>CFPB Intake Routing Delay:</strong> Measures calendar delay from
                        consumer submission to agency intake and transmission to the institution.
                        This is <em>not</em> the company&apos;s response time.
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              {/* Company Response & Resolution */}
              <section className="space-y-2.5">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Company Response & Resolution
                </h3>
                <div className="rounded-lg border border-border bg-card p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-[11px] text-muted-foreground">Response Classification</div>
                      <div className="font-medium text-foreground mt-0.5">
                        {complaint.company_response}
                      </div>
                    </div>
                    <div>
                      {complaint.timely_response === "yes" ? (
                        <Badge variant="positive" dot>
                          Timely (Yes)
                        </Badge>
                      ) : complaint.timely_response === "no" ? (
                        <Badge variant="negative" dot>
                          Untimely (No)
                        </Badge>
                      ) : (
                        <Badge variant="neutral" dot>
                          In Progress / Pending
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-border/50 pt-2">
                    <div className="text-[11px] text-muted-foreground">Company Public Response</div>
                    <div className="mt-1 text-foreground leading-relaxed italic bg-muted/20 rounded p-2 border border-border/40">
                      {formatNullable(complaint.company_public_response, "Not provided")}
                    </div>
                  </div>
                </div>
              </section>

              {/* Submission Channel & Geography */}
              <section className="space-y-2.5">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Submission & Location
                </h3>
                <div className="rounded-lg border border-border bg-card p-3.5 grid grid-cols-2 gap-2">
                  <div>
                    <div className="text-[11px] text-muted-foreground">Submission Channel</div>
                    <div className="font-medium text-foreground">{complaint.submitted_via}</div>
                  </div>
                  <div>
                    <div className="text-[11px] text-muted-foreground">Consumer State</div>
                    <div className="font-mono font-medium text-foreground">
                      {formatNullable(complaint.state, "Not provided")}
                    </div>
                  </div>
                </div>
              </section>

              {/* Statistical Anomaly Detection */}
              <section className="space-y-2.5">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Distributional Analysis
                </h3>
                <div className="rounded-lg border border-border bg-card p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">Statistical Outlier Flag</span>
                    {complaint.is_anomaly ? (
                      <Badge variant="negative" dot>
                        Flagged Statistical Outlier
                      </Badge>
                    ) : (
                      <Badge variant="neutral" dot>
                        Normal Distribution
                      </Badge>
                    )}
                  </div>

                  <div className="border-t border-border/50 pt-2 flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">Isolation Forest Score</span>
                    <span className="font-mono text-xs font-medium text-foreground">
                      {complaint.anomaly_score !== null && complaint.anomaly_score !== undefined
                        ? complaint.anomaly_score.toFixed(4)
                        : "—"}
                    </span>
                  </div>

                  <div className="rounded bg-muted/40 p-2 text-[11px] text-muted-foreground leading-normal">
                    <strong>Notice:</strong> Anomaly detection uses Isolation Forest decision scores
                    to identify multi-attribute distributional outliers. This flag does{" "}
                    <strong>not</strong> indicate procedural error, regulatory infraction, or fraud.
                  </div>
                </div>
              </section>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <footer className="border-t border-border px-5 py-3 bg-muted/20 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </footer>
      </div>
    </div>
  );
}
