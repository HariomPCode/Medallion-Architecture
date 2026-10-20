"use client";

import React from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "./theme-provider";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="group"
      aria-label="Theme selector"
      className={`inline-flex items-center rounded-md border border-border bg-card p-0.5 text-xs font-medium ${className}`}
    >
      <button
        type="button"
        onClick={() => setTheme("light")}
        aria-pressed={theme === "light"}
        aria-label="Switch to light theme"
        className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
          theme === "light"
            ? "bg-accent-soft text-accent font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Sun className="h-3.5 w-3.5" aria-hidden="true" />
        <span>Light</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme("dark")}
        aria-pressed={theme === "dark"}
        aria-label="Switch to dark theme"
        className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
          theme === "dark"
            ? "bg-accent-soft text-accent font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Moon className="h-3.5 w-3.5" aria-hidden="true" />
        <span>Dark</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme("system")}
        aria-pressed={theme === "system"}
        aria-label="Follow system theme"
        className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
          theme === "system"
            ? "bg-accent-soft text-accent font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Monitor className="h-3.5 w-3.5" aria-hidden="true" />
        <span>System</span>
      </button>
    </div>
  );
}
