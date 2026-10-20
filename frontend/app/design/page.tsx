import { notFound } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Tooltip } from "@/components/ui/tooltip";
import { formatNumber, formatPercent, formatDate, formatCurrency } from "@/lib/format";
import { CATEGORY_COLORS, type CategoryKey } from "@/lib/colors";
import { AlertCircle, FileSearch, RefreshCw, Info } from "lucide-react";

export default function DesignSystemPage() {
  // Protect this route from being accessed in production builds
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-6 md:p-10 max-w-6xl mx-auto space-y-10">
      {/* Dev Advisory Notice */}
      <div
        role="region"
        aria-label="Design preview notice"
        className="rounded-md border border-status-warning/40 bg-status-warning-bg p-4 text-xs text-status-warning flex items-start gap-3"
      >
        <Info className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <p className="font-semibold">Development-Only Design System Preview</p>
          <p className="mt-0.5 text-muted-foreground">
            This route is excluded or blocked in production builds. All metric figures displayed on this
            page are illustrative sample values for visual testing and contrast validation.
          </p>
        </div>
      </div>

      {/* Header and Theme Controller */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Financial Editorial Design System
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Design tokens, typography hierarchy, accessible color palettes, and base UI primitives.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-muted-foreground">Theme:</span>
          <ThemeToggle />
        </div>
      </header>

      {/* 1. Typography Hierarchy */}
      <section aria-labelledby="typography-heading" className="space-y-4">
        <h2 id="typography-heading" className="text-base font-semibold text-foreground">
          1. Typography Hierarchy (IBM Plex)
        </h2>
        <Card>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border pb-3">
              <span className="text-xs text-muted-foreground">Page Title (22px / 700)</span>
              <span className="md:col-span-3 text-2xl font-bold tracking-tight text-foreground">
                Finance Complaints Overview
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border pb-3">
              <span className="text-xs text-muted-foreground">Section Heading (15px / 600)</span>
              <span className="md:col-span-3 text-[15px] font-semibold text-foreground">
                Complaints Volume by Product Category
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border pb-3">
              <span className="text-xs text-muted-foreground">KPI Value (28px / Tabular)</span>
              <span className="md:col-span-3 text-3xl font-semibold tracking-tight text-foreground tabular-nums">
                {formatNumber(62516)}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border pb-3">
              <span className="text-xs text-muted-foreground">Body & Table Text (13.5px)</span>
              <span className="md:col-span-3 text-sm text-foreground">
                Regulatory intelligence workbench providing structured analysis over CFPB financial records.
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border pb-3">
              <span className="text-xs text-muted-foreground">Secondary Label (12px)</span>
              <span className="md:col-span-3 text-xs font-medium text-muted-foreground">
                CFPB Routing Lag (Date received − Date submitted)
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2">
              <span className="text-xs text-muted-foreground">Metadata / Caption (11px)</span>
              <span className="md:col-span-3 text-[11px] text-muted-foreground tabular-nums">
                Sample Timestamp: {formatDate("2023-08-28")} · Refreshed UTC
              </span>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* 2. Color Palette & Category Tokens */}
      <section aria-labelledby="palette-heading" className="space-y-4">
        <h2 id="palette-heading" className="text-base font-semibold text-foreground">
          2. Color Tokens & Category Palette
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {(Object.keys(CATEGORY_COLORS) as CategoryKey[]).map((cat) => (
            <div
              key={cat}
              className="rounded-lg border border-border bg-card p-3 shadow-sm flex flex-col justify-between"
            >
              <div>
                <div
                  className="h-10 w-full rounded mb-2"
                  style={{
                    backgroundColor:
                      cat === "Banking"
                        ? "hsl(var(--cat-banking))"
                        : cat === "Payments"
                        ? "hsl(var(--cat-payments))"
                        : cat === "Credit Reporting"
                        ? "hsl(var(--cat-credit-reporting))"
                        : cat === "Lending"
                        ? "hsl(var(--cat-lending))"
                        : "hsl(var(--cat-collections))",
                  }}
                  aria-hidden="true"
                />
                <p className="text-xs font-semibold text-foreground">{cat}</p>
              </div>
              <p className="text-[11px] text-muted-foreground mt-2">
                Token: <span className="font-mono">--cat-{cat.toLowerCase().replace(/\s+/g, "-")}</span>
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Interactive UI Primitives */}
      <section aria-labelledby="primitives-heading" className="space-y-4">
        <h2 id="primitives-heading" className="text-base font-semibold text-foreground">
          3. Interactive Controls & Form Elements
        </h2>
        <Card>
          <CardHeader>
            <CardTitle as="h3">Buttons, Inputs, and Select Elements</CardTitle>
            <CardDescription>
              Styled with 1px border rules, 6px radius, and high-visibility focus indicators.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Buttons */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Button Variants:</p>
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="default">Primary Button</Button>
                <Button variant="accent">Accent Teal</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="destructive">Destructive</Button>
                <Button variant="default" disabled>Disabled</Button>
              </div>
            </div>

            <Separator />

            {/* Inputs & Selects */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Form Controls:</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label htmlFor="sample-text-input" className="block text-xs font-medium text-foreground mb-1">
                    Complaint ID Search
                  </label>
                  <Input id="sample-text-input" placeholder="e.g. 3197305" />
                </div>
                <div>
                  <label htmlFor="sample-select" className="block text-xs font-medium text-foreground mb-1">
                    Product Category
                  </label>
                  <Select id="sample-select" defaultValue="all">
                    <option value="all">All Categories</option>
                    <option value="banking">Banking</option>
                    <option value="payments">Payments</option>
                    <option value="lending">Lending</option>
                  </Select>
                </div>
                <div>
                  <label htmlFor="sample-disabled-input" className="block text-xs font-medium text-foreground mb-1">
                    Read-only / Disabled
                  </label>
                  <Input id="sample-disabled-input" disabled value="Dataset Frozen" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* 4. Status Indicators and Badges */}
      <section aria-labelledby="status-heading" className="space-y-4">
        <h2 id="status-heading" className="text-base font-semibold text-foreground">
          4. Semantic Status Badges
        </h2>
        <Card>
          <CardHeader>
            <CardTitle as="h3">Status Representation</CardTitle>
            <CardDescription>
              Never relies on color alone; incorporates status dots, border rules, and explicit text labels.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="positive" dot>Live System (Positive)</Badge>
              <Badge variant="warning" dot>Local Snapshot (Warning)</Badge>
              <Badge variant="negative" dot>Service Unavailable (Error)</Badge>
              <Badge variant="neutral" dot>Not Published (Neutral)</Badge>
              <Badge variant="default">Primary Badge</Badge>
              <Badge variant="secondary">Secondary Badge</Badge>
              <Badge variant="outline">Outline Filter Chip</Badge>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* 5. Representative KPI Stat Cards */}
      <section aria-labelledby="kpi-heading" className="space-y-4">
        <h2 id="kpi-heading" className="text-base font-semibold text-foreground">
          5. Illustrative KPI Cards
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-1">
              <CardDescription className="text-xs font-medium text-muted-foreground">
                Total Complaints (Sample)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight tabular-nums text-foreground">
                {formatNumber(62516)}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                All records in dataset
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1">
              <CardDescription className="text-xs font-medium text-muted-foreground flex items-center justify-between">
                <span>Timely Rate (Sample)</span>
                <Tooltip content="Legacy rate including open cases: 93.8%">
                  <button type="button" aria-label="Timely rate definition" className="text-muted-foreground hover:text-foreground">
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </Tooltip>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight tabular-nums text-status-success">
                {formatPercent(0.9606, 1)}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Of 61,022 resolved cases
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1">
              <CardDescription className="text-xs font-medium text-muted-foreground">
                Open / In Progress (Sample)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight tabular-nums text-status-warning">
                {formatNumber(1494)}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Timeliness undetermined
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1">
              <CardDescription className="text-xs font-medium text-muted-foreground">
                CFPB Routing Lag (Sample)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight tabular-nums text-foreground">
                1.22 days
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Mean routing delay
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 6. Loading Skeletons */}
      <section aria-labelledby="skeleton-heading" className="space-y-4">
        <h2 id="skeleton-heading" className="text-base font-semibold text-foreground">
          6. Loading Skeletons
        </h2>
        <Card>
          <CardHeader>
            <CardTitle as="h3">Skeleton Shimmer Placeholders</CardTitle>
            <CardDescription>
              Accessible loaders with subtle pulse animation (disabled when reduced motion is preferred).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <div className="grid grid-cols-3 gap-3 pt-2">
              <Skeleton className="h-16 rounded-md" />
              <Skeleton className="h-16 rounded-md" />
              <Skeleton className="h-16 rounded-md" />
            </div>
          </CardContent>
        </Card>
      </section>

      {/* 7. Representative Empty & Error States */}
      <section aria-labelledby="states-heading" className="space-y-4">
        <h2 id="states-heading" className="text-base font-semibold text-foreground">
          7. Representative Empty and Error States
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Empty State */}
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center p-8 text-center space-y-3">
              <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground">
                <FileSearch className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">No complaints match these filters</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                  Try adjusting the date range, category selections, or search terms to broaden results.
                </p>
              </div>
              <Button variant="outline" size="sm">
                Clear all filters
              </Button>
            </CardContent>
          </Card>

          {/* Error State */}
          <Card className="border-status-error/30 bg-status-error-bg/30">
            <CardContent className="flex flex-col items-center justify-center p-8 text-center space-y-3">
              <div className="h-10 w-10 rounded-full bg-status-error/10 text-status-error flex items-center justify-center">
                <AlertCircle className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold text-status-error">Unable to load analytics panel</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                  The upstream service encountered a transient timeout. Other panels remain functional.
                </p>
              </div>
              <Button variant="outline" size="sm" className="gap-1.5">
                <RefreshCw className="h-3 w-3" aria-hidden="true" />
                <span>Retry query</span>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
