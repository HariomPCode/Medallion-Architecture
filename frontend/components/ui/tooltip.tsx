"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  className?: string;
  id?: string;
}

export function Tooltip({
  content,
  children,
  className,
  id,
}: TooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false);
  const generatedId = React.useId();
  const tooltipId = id || `tooltip-${generatedId}`;

  const child = React.Children.only(children);

  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {React.cloneElement(child, {
        "aria-describedby": isVisible ? tooltipId : undefined,
      })}
      {isVisible && (
        <span
          id={tooltipId}
          role="tooltip"
          className={cn(
            "pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded border border-border bg-popover px-2 py-1 text-[11px] font-medium text-popover-foreground shadow-md transition-opacity animate-in fade-in-0 zoom-in-95",
            className
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
