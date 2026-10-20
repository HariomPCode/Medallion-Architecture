import React from "react";
import { KpiStat, KpiStatProps } from "./KpiStat";
import { cn } from "@/lib/utils";

export interface KpiStripProps {
  items?: KpiStatProps[];
  children?: React.ReactNode;
  columns?: 2 | 3 | 4 | 5;
  title?: string;
  className?: string;
}

const columnClasses: Record<2 | 3 | 4 | 5, string> = {
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  5: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5",
};

/**
 * Responsive layout container for multiple KPI metric cards.
 * Adapts seamlessly from 360px mobile viewports to 1920px widescreen.
 */
export function KpiStrip({
  items,
  children,
  columns = 4,
  title,
  className,
}: KpiStripProps) {
  const content = (
    <div
      className={cn(
        "grid gap-4 w-full",
        columnClasses[columns] || columnClasses[4],
        className
      )}
    >
      {items
        ? items.map((item, idx) => <KpiStat key={item.label || idx} {...item} />)
        : children}
    </div>
  );

  if (title) {
    return (
      <section aria-label={title} className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h2>
        {content}
      </section>
    );
  }

  return content;
}
