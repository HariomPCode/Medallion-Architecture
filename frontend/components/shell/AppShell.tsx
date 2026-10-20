import React from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { SkipLink } from "./SkipLink";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col lg:flex-row antialiased">
      {/* Accessibility: Skip to Content */}
      <SkipLink />

      {/* Desktop Sidebar Navigation */}
      <Sidebar />

      {/* Main App Layout */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 p-4 sm:p-6 lg:p-8 w-full max-w-7xl mx-auto focus:outline-none"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
