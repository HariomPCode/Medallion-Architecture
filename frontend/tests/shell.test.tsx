import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { AppShell } from "@/components/shell/AppShell";
import { ThemeProvider } from "@/components/theme-provider";

// Mock next/navigation
let currentMockPathname = "/";
vi.mock("next/navigation", () => ({
  usePathname: () => currentMockPathname,
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("Application Shell & Navigation", () => {
  beforeEach(() => {
    currentMockPathname = "/";
    vi.clearAllMocks();
  });

  it("renders desktop sidebar with all 5 core navigation destinations", () => {
    render(
      <ThemeProvider>
        <AppShell>
          <div>Page Content</div>
        </AppShell>
      </ThemeProvider>
    );

    expect(screen.getByRole("link", { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /category analytics/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /complaint explorer/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /data quality/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ai assistant/i })).toBeInTheDocument();
  });

  it("highlights the active navigation link based on current pathname", () => {
    currentMockPathname = "/explorer";

    render(
      <ThemeProvider>
        <AppShell>
          <div>Page Content</div>
        </AppShell>
      </ThemeProvider>
    );

    const explorerLink = screen.getByRole("link", { name: /complaint explorer/i });
    expect(explorerLink).toHaveAttribute("aria-current", "page");
    expect(explorerLink.className).toContain("bg-accent-soft");

    const overviewLink = screen.getByRole("link", { name: /overview/i });
    expect(overviewLink).not.toHaveAttribute("aria-current");
  });

  it("includes accessible skip-to-content link pointing to #main-content", () => {
    render(
      <ThemeProvider>
        <AppShell>
          <div>Page Content</div>
        </AppShell>
      </ThemeProvider>
    );

    const skipLink = screen.getByRole("link", { name: /skip to main content/i });
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");

    const mainLandmark = screen.getByRole("main");
    expect(mainLandmark).toHaveAttribute("id", "main-content");
  });

  it("opens, closes, and handles Escape key on mobile navigation drawer", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <AppShell>
          <div>Page Content</div>
        </AppShell>
      </ThemeProvider>
    );

    const menuToggle = screen.getByRole("button", { name: /open navigation menu/i });
    expect(menuToggle).toHaveAttribute("aria-expanded", "false");

    // Open mobile menu
    await user.click(menuToggle);

    const mobileDrawer = screen.getByRole("dialog", { name: /mobile navigation drawer/i });
    expect(mobileDrawer).toBeInTheDocument();

    // Close on Escape key
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: /mobile navigation drawer/i })).not.toBeInTheDocument();

    // Reopen and close via close button
    await user.click(menuToggle);
    const closeBtn = screen.getByRole("button", { name: /close navigation menu/i });
    await user.click(closeBtn);
    expect(screen.queryByRole("dialog", { name: /mobile navigation drawer/i })).not.toBeInTheDocument();
  });

  it("passes automated axe accessibility check with zero violations", async () => {
    const { container } = render(
      <ThemeProvider>
        <AppShell>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Overview Dashboard</h2>
            <p className="text-sm text-muted-foreground">Main panel test content.</p>
          </div>
        </AppShell>
      </ThemeProvider>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
