import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OverviewDashboardPage from "@/app/page";
import { ThemeProvider } from "@/components/theme-provider";
import { http, HttpResponse } from "msw";
import { server } from "./mocks/server";

// Mock next/navigation
let mockSearchParams = new URLSearchParams();
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  useSearchParams: () => mockSearchParams,
}));

function renderOverview() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <OverviewDashboardPage />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("Phase 8: Overview Dashboard Page (/)", () => {
  beforeEach(() => {
    mockSearchParams = new URLSearchParams();
    vi.clearAllMocks();
  });

  it("renders page header, dynamic scope line, and dataset status pill", async () => {
    renderOverview();

    expect(
      screen.getByRole("heading", { level: 1, name: /finance complaints overview/i })
    ).toBeInTheDocument();

    // Verify dataset status pill
    expect(screen.getByText(/local snapshot/i)).toBeInTheDocument();

    // Scope line should populate from summary API response
    await waitFor(() => {
      const scopeLine = screen.getByTestId("dataset-scope-line");
      expect(scopeLine).toHaveTextContent(/62,516 complaints/);
      expect(scopeLine).toHaveTextContent(/5 categories/);
      expect(scopeLine).toHaveTextContent(/9 sub-categories/);
      expect(scopeLine).toHaveTextContent(/1 May 2017 – 28 Aug 2023/);
    });
  });

  it("renders CFPB skew notice when metadata indicates skew warning", async () => {
    renderOverview();

    await waitFor(() => {
      expect(screen.getByRole("region", { name: /dataset distribution notice/i })).toBeInTheDocument();
      expect(screen.getByText(/CFPB Distribution Notice:/i)).toBeInTheDocument();
    });
  });

  it("renders all 4 required KPI tiles with exact golden values and definitions (AC-8.2)", async () => {
    renderOverview();

    await waitFor(() => {
      const totalCard = screen.getByTestId("kpi-card-total-complaints");
      expect(within(totalCard).getByText("Total Complaints")).toBeInTheDocument();
      expect(within(totalCard).getByTestId("kpi-value")).toHaveTextContent("62,516");

      const timelyCard = screen.getByTestId("kpi-card-primary-timely-rate");
      expect(within(timelyCard).getByText("Primary Timely Rate")).toBeInTheDocument();
      expect(within(timelyCard).getByTestId("kpi-value")).toHaveTextContent("96.1%");
      expect(within(timelyCard).getByText(/of 61,022 cases with recorded outcome/i)).toBeInTheDocument();

      const inProgressCard = screen.getByTestId("kpi-card-in-progress-cases");
      expect(within(inProgressCard).getByText("In-Progress Cases")).toBeInTheDocument();
      expect(within(inProgressCard).getByTestId("kpi-value")).toHaveTextContent("1,494");

      const coverageCard = screen.getByTestId("kpi-card-coverage-end-date");
      expect(within(coverageCard).getByText("Coverage End Date")).toBeInTheDocument();
      expect(within(coverageCard).getByTestId("kpi-value")).toHaveTextContent("28 Aug 2023");
    });
  });

  it("renders Category Volume chart and supports 'View as table' parity toggle (AC-8.1)", async () => {
    const user = userEvent.setup();
    renderOverview();

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 2, name: /complaints by category/i })).toBeInTheDocument();
    });

    const categoryCard = screen.getByTestId("category-bar-panel");
    const tableToggle = within(categoryCard).getByRole("button", {
      name: /switch to table view|view as table/i,
    });
    expect(tableToggle).toBeInTheDocument();

    // Toggle to accessible table view
    await user.click(tableToggle);

    const table = within(categoryCard).getByRole("table");
    expect(table).toBeInTheDocument();
    expect(within(categoryCard).getByText("Banking")).toBeInTheDocument();
    expect(within(categoryCard).getByText("24,814")).toBeInTheDocument();
    expect(within(categoryCard).getByText("Payments")).toBeInTheDocument();
    expect(within(categoryCard).getByText("19,650")).toBeInTheDocument();

    // Toggle back to chart view
    const chartToggle = within(categoryCard).getByRole("button", {
      name: /switch to chart view|view as chart/i,
    });
    await user.click(chartToggle);
    expect(within(categoryCard).queryByRole("table")).not.toBeInTheDocument();
  });

  it("renders TrendLine with Year/Month grain toggle and partial period callout (AC-8.1)", async () => {
    const user = userEvent.setup();
    renderOverview();

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 2, name: /complaints over time/i })).toBeInTheDocument();
    });

    const trendPanel = screen.getByTestId("trend-line-panel");

    // Check grain toggles
    const yearBtn = within(trendPanel).getByRole("button", { name: /yearly grain/i });
    const monthBtn = within(trendPanel).getByRole("button", { name: /monthly grain/i });
    expect(yearBtn).toHaveAttribute("aria-pressed", "true");

    await user.click(monthBtn);
    expect(monthBtn).toHaveAttribute("aria-pressed", "true");

    // Check View as table toggle
    const tableToggle = within(trendPanel).getByRole("button", {
      name: /switch to table view|view as table/i,
    });
    await user.click(tableToggle);

    const table = within(trendPanel).getByRole("table");
    expect(table).toBeInTheDocument();
  });

  it("renders TimelyDotPlot with 88%-100% axis truncation note, 95% target, and denominator breakdown (AC-8.1)", async () => {
    const user = userEvent.setup();
    renderOverview();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /timely response compliance by sub-category/i })
      ).toBeInTheDocument();
    });

    const timelyPanel = screen.getByTestId("timely-dot-plot-panel");

    // Axis truncation note
    await waitFor(
      () => {
        expect(within(timelyPanel).getByText(/truncated x-axis/i)).toBeInTheDocument();
        expect(within(timelyPanel).getByText(/95%.*target/i)).toBeInTheDocument();
        expect(within(timelyPanel).getByText(/denominator/i)).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    // Toggle to accessible table view
    const tableToggle = within(timelyPanel).getByRole("button", {
      name: /switch to table view|view as table/i,
    });
    await user.click(tableToggle);

    const table = within(timelyPanel).getByRole("table");
    expect(table).toBeInTheDocument();
    const depositRow = within(table).getByText("Deposit Accounts").closest("tr")!;
    expect(within(depositRow).getByText("96.4%")).toBeInTheDocument();
  });

  it("handles independent panel errors without crashing the rest of the dashboard (AC-8.6)", async () => {
    // Override /api/v1/analytics/trends to simulate a panel failure
    server.use(
      http.get("/api/v1/analytics/trends", () => {
        return HttpResponse.json({ detail: "Trends database query timed out" }, { status: 504 });
      })
    );

    renderOverview();

    // Other panels should still render successfully
    await waitFor(() => {
      const totalCard = screen.getByTestId("kpi-card-total-complaints");
      expect(within(totalCard).getByTestId("kpi-value")).toHaveTextContent("62,516");
      expect(screen.getByRole("heading", { level: 2, name: /complaints by category/i })).toBeInTheDocument();
    });

    // Trend panel should show error state with retry button
    await waitFor(() => {
      const trendPanel = screen.getByTestId("trend-line-panel");
      expect(within(trendPanel).getByText(/trends database query timed out/i)).toBeInTheDocument();
      expect(within(trendPanel).getByRole("button", { name: /try again|retry/i })).toBeInTheDocument();
    });
  });

  it("passes automated accessibility checks with zero violations", async () => {
    const { container } = renderOverview();

    await waitFor(() => {
      const totalCard = screen.getByTestId("kpi-card-total-complaints");
      expect(within(totalCard).getByTestId("kpi-value")).toHaveTextContent("62,516");
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
