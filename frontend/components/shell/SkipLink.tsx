import React from "react";

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-1.5 focus:rounded-md focus:bg-accent focus:text-accent-foreground focus:shadow-md focus:outline-none focus:ring-2 focus:ring-ring text-xs font-semibold"
    >
      Skip to main content
    </a>
  );
}
