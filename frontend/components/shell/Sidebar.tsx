"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PieChart,
  FileSearch,
  ShieldCheck,
  Bot,
  Palette,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
}

export const NAV_ITEMS: NavItem[] = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Category Analytics", href: "/categories", icon: PieChart },
  { name: "Complaint Explorer", href: "/explorer", icon: FileSearch },
  { name: "Data Quality", href: "/quality", icon: ShieldCheck },
  { name: "AI Assistant", href: "/assistant", icon: Bot },
];

export function Sidebar({ className = "" }: { className?: string }) {
  const pathname = usePathname();

  return (
    <aside
      aria-label="Desktop sidebar"
      className={cn(
        "hidden lg:flex w-[232px] flex-col shrink-0 border-r border-border bg-card text-card-foreground select-none h-screen sticky top-0",
        className
      )}
    >
      {/* Brand Header */}
      <div className="h-14 border-b border-border px-5 flex items-center gap-2.5">
        <div className="h-6 w-6 rounded bg-primary flex items-center justify-center text-primary-foreground font-bold text-xs tracking-wider">
          FC
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-bold tracking-tight text-foreground leading-tight">
            Finance Complaints
          </span>
          <span className="text-[10px] text-muted-foreground leading-none">
            Medallion Platform
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav aria-label="Main navigation" className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-accent-soft text-accent font-semibold border-l-2 border-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{item.name}</span>
            </Link>
          );
        })}

        {/* Development preview link */}
        {process.env.NODE_ENV !== "production" && (
          <div className="pt-4 mt-4 border-t border-border">
            <span className="px-3 text-[10px] font-semibold tracking-wider uppercase text-muted-foreground">
              Development
            </span>
            <Link
              href="/design"
              aria-current={pathname === "/design" ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 mt-1 rounded-md text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                pathname === "/design"
                  ? "bg-accent-soft text-accent font-semibold border-l-2 border-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Palette className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>Design Preview</span>
            </Link>
          </div>
        )}
      </nav>

      {/* Sidebar Footer */}
      <div className="p-3 border-t border-border text-[11px] text-muted-foreground">
        <p className="font-mono">v1.0-frozen</p>
        <p className="mt-0.5">CFPB Research Dataset</p>
      </div>
    </aside>
  );
}
