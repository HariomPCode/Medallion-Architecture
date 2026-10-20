"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { DatasetStatusPill } from "./DatasetStatusPill";
import { MobileNav } from "./MobileNav";
import { NAV_ITEMS } from "./Sidebar";

export function TopBar() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const pathname = usePathname();

  // Determine current page title
  const currentNav = NAV_ITEMS.find((item) =>
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)
  );
  const pageTitle =
    pathname === "/design"
      ? "Design System Preview"
      : currentNav
      ? currentNav.name
      : "Finance Complaints Medallion";

  return (
    <>
      <header
        role="banner"
        className="h-14 border-b border-border bg-card/80 backdrop-blur px-4 md:px-6 flex items-center justify-between sticky top-0 z-30 select-none"
      >
        <div className="flex items-center gap-3">
          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            onClick={() => setIsMobileOpen(true)}
            aria-label="Open navigation menu"
            aria-expanded={isMobileOpen}
            className="lg:hidden rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Menu className="h-4 w-4" aria-hidden="true" />
          </button>

          {/* Current Page Context */}
          <span className="text-sm font-semibold tracking-tight text-foreground truncate max-w-[200px] sm:max-w-xs md:max-w-md">
            {pageTitle}
          </span>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <DatasetStatusPill status="local_snapshot" />
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Accessible Mobile Nav Sheet */}
      <MobileNav isOpen={isMobileOpen} onClose={() => setIsMobileOpen(false)} />
    </>
  );
}
