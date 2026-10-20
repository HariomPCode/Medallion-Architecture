import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import {
  KpiStat,
  KpiStrip,
  DataState,
  ChartPanel,
  FilterBar,
  DatasetStatusPill,
} from "@/components/data";

describe("Day 4: Reusable Data Components", () => {
  describe("KpiStat Component", () => {
    it("renders formatted value, label, and description", () => {
      render(
        <KpiStat
          label="Total Complaints"
          value="62,516"
          description="Total records in snapshot"
        />
      );

      expect(screen.getByText("Total Complaints")).toBeInTheDocument();
      expect(screen.getByText("62,516")).toBeInTheDocument();
      expect(screen.getByText("Total records in snapshot")).toBeInTheDocument();
    });

    it("correctly renders zero as '0' without triggering fallback", () => {
      render(<KpiStat label="Unresolved Claims" value={0} />);

      const valueEl = screen.getByTestId("kpi-value");
      expect(valueEl.textContent).toBe("0");
    });

    it("renders fallback '—' when value is null, undefined, or empty", () => {
      const { rerender } = render(<KpiStat label="Missing Metric" value={null} />);
      expect(screen.getByTestId("kpi-value").textContent).toBe("—");

      rerender(<KpiStat label="Missing Metric" value={undefined} />);
      expect(screen.getByTestId("kpi-value").textContent).toBe("—");

      rerender(<KpiStat label="Missing Metric" value="" />);
      expect(screen.getByTestId("kpi-value").textContent).toBe("—");

      rerender(<KpiStat label="Custom Fallback" value={null} emptyFallback="N/A" />);
      expect(screen.getByTestId("kpi-value").textContent).toBe("N/A");
    });

    it("renders accessible trend indicators with directional icons and labels", () => {
      render(
        <KpiStat
          label="Timely Rate"
          value="96.1%"
          trend={{
            value: "+2.4%",
            direction: "up",
            sentiment: "positive",
            label: "vs prior year",
            accessibleText: "Trend: 2.4% increase versus prior year",
          }}
        />
      );

      const trendBadge = screen.getByLabelText("Trend: 2.4% increase versus prior year");
      expect(trendBadge).toBeInTheDocument();
      expect(trendBadge.textContent).toContain("+2.4%");
      expect(trendBadge.textContent).toContain("vs prior year");
    });

    it("renders loading skeleton with aria-busy", () => {
      render(<KpiStat label="Loading Metric" loading={true} />);

      const card = screen.getByTestId("kpi-stat-loading");
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute("aria-busy", "true");
      expect(screen.queryByTestId("kpi-value")).not.toBeInTheDocument();
    });

    it("passes automated axe accessibility check", async () => {
      const { container } = render(
        <KpiStat
          label="Resolution Rate"
          value="98.5%"
          unit="/ month"
          description="High compliance score"
          trend={{ value: "+0.5%", direction: "up", sentiment: "positive" }}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("KpiStrip Component", () => {
    it("renders a collection of KPI definitions responsively", () => {
      render(
        <KpiStrip
          title="Executive Summary"
          columns={3}
          items={[
            { label: "Complaints", value: "62,516" },
            { label: "Timely Rate", value: "96.1%" },
            { label: "Avg Lag", value: "1.2 days" },
          ]}
        />
      );

      expect(screen.getByRole("region", { name: "Executive Summary" })).toBeInTheDocument();
      expect(screen.getByText("Complaints")).toBeInTheDocument();
      expect(screen.getByText("Timely Rate")).toBeInTheDocument();
      expect(screen.getByText("Avg Lag")).toBeInTheDocument();
    });

    it("renders children directly when passed", () => {
      render(
        <KpiStrip>
          <div data-testid="custom-child-1">Card 1</div>
          <div data-testid="custom-child-2">Card 2</div>
        </KpiStrip>
      );

      expect(screen.getByTestId("custom-child-1")).toBeInTheDocument();
      expect(screen.getByTestId("custom-child-2")).toBeInTheDocument();
    });

    it("passes automated axe accessibility check", async () => {
      const { container } = render(
        <KpiStrip
          title="Key Metrics"
          items={[
            { label: "Metric A", value: "100" },
            { label: "Metric B", value: "200" },
          ]}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("DataState Component", () => {
    it("renders loading skeleton with role status and aria-live polite", () => {
      render(<DataState loading={true} loadingMessage="Fetching analytics..." />);

      const statusElements = screen.getAllByRole("status");
      expect(statusElements.length).toBeGreaterThan(0);
      const mainStatus = statusElements.find((el) => el.getAttribute("aria-live") === "polite");
      expect(mainStatus).toBeInTheDocument();
      expect(screen.getByText("Fetching analytics...")).toBeInTheDocument();
    });

    it("renders error state with role alert and sanitized message", () => {
      render(
        <DataState
          error={{
            code: "UPSTREAM_TIMEOUT",
            message: "The backend service timed out at http://localhost:8000/internal",
          }}
        />
      );

      const alertEl = screen.getByRole("alert");
      expect(alertEl).toBeInTheDocument();
      expect(screen.getByText("UPSTREAM_TIMEOUT")).toBeInTheDocument();
      // Verifies localhost:8000 URL was redacted
      expect(screen.queryByText(/localhost:8000/)).not.toBeInTheDocument();
      expect(
        screen.getByText("A communication error occurred with the analytics service.")
      ).toBeInTheDocument();
    });

    it("invokes onRetry callback when retry button is clicked", async () => {
      const user = userEvent.setup();
      const retryMock = vi.fn();

      render(
        <DataState
          error="Network failure"
          onRetry={retryMock}
          retryLabel="Retry Action"
        />
      );

      const retryBtn = screen.getByRole("button", { name: "Retry Action" });
      await user.click(retryBtn);

      expect(retryMock).toHaveBeenCalledTimes(1);
    });

    it("renders empty state with message and title", () => {
      render(
        <DataState
          empty={true}
          emptyTitle="No results found"
          emptyMessage="No complaints match this filter selection."
        />
      );

      expect(screen.getByText("No results found")).toBeInTheDocument();
      expect(
        screen.getByText("No complaints match this filter selection.")
      ).toBeInTheDocument();
    });

    it("renders children when state is ready", () => {
      render(
        <DataState>
          <div data-testid="ready-content">Content is ready</div>
        </DataState>
      );

      expect(screen.getByTestId("ready-content")).toBeInTheDocument();
    });

    it("passes automated axe accessibility check across all states", async () => {
      const { container: loadingContainer } = render(<DataState loading={true} />);
      expect(await axe(loadingContainer)).toHaveNoViolations();

      const { container: errorContainer } = render(
        <DataState error="Operation failed" onRetry={() => {}} />
      );
      expect(await axe(errorContainer)).toHaveNoViolations();

      const { container: emptyContainer } = render(
        <DataState empty={true} emptyTitle="Nothing here" />
      );
      expect(await axe(emptyContainer)).toHaveNoViolations();
    });
  });

  describe("ChartPanel Component", () => {
    it("renders title, description, actions, and summary callout", () => {
      render(
        <ChartPanel
          title="Category Distribution"
          description="Complaints breakdown by category"
          summary="Banking represents 39.7% of total volume."
          actions={<button type="button">Download</button>}
        >
          <div data-testid="chart-canvas">Chart Visualization</div>
        </ChartPanel>
      );

      expect(screen.getByText("Category Distribution")).toBeInTheDocument();
      expect(screen.getByText("Complaints breakdown by category")).toBeInTheDocument();
      expect(screen.getByTestId("chart-summary")).toHaveTextContent(
        "Banking represents 39.7% of total volume."
      );
      expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
      expect(screen.getByTestId("chart-canvas")).toBeInTheDocument();
    });

    it("integrates error and loading state", () => {
      const { rerender } = render(
        <ChartPanel title="Chart Title" loading={true}>
          <div>Chart Canvas</div>
        </ChartPanel>
      );
      expect(screen.getAllByRole("status").length).toBeGreaterThan(0);

      rerender(
        <ChartPanel title="Chart Title" error="Chart load failure">
          <div>Chart Canvas</div>
        </ChartPanel>
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("passes automated axe accessibility check", async () => {
      const { container } = render(
        <ChartPanel
          title="Accessible Chart"
          description="Detailed chart description"
          summary="Summary takeaway for screen readers"
        >
          <div>Visual elements</div>
        </ChartPanel>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("FilterBar Component", () => {
    it("renders filter controls, active count, and total results", () => {
      render(
        <FilterBar
          activeCount={3}
          isFiltered={true}
          totalResults={62516}
          resultsLabel="records"
          onReset={() => {}}
        >
          <input placeholder="Filter by product" aria-label="Product filter" />
        </FilterBar>
      );

      expect(screen.getByRole("region", { name: "Filter controls" })).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("62,516")).toBeInTheDocument();
      expect(screen.getByText("records")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reset filters" })).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Filter by product")).toBeInTheDocument();
    });

    it("calls onReset when reset button is clicked", async () => {
      const user = userEvent.setup();
      const resetMock = vi.fn();

      render(
        <FilterBar isFiltered={true} onReset={resetMock} resetLabel="Clear All Filters">
          <div>Filter inputs</div>
        </FilterBar>
      );

      const resetBtn = screen.getByRole("button", { name: "Clear All Filters" });
      await user.click(resetBtn);

      expect(resetMock).toHaveBeenCalledTimes(1);
    });

    it("passes automated axe accessibility check", async () => {
      const { container } = render(
        <FilterBar activeCount={1} isFiltered={true} onReset={() => {}}>
          <button type="button">Category: Banking</button>
        </FilterBar>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("DatasetStatusPill Component", () => {
    it("renders live snapshot status with icon and accessible text", () => {
      render(<DatasetStatusPill status="ready" />);

      const pill = screen.getByRole("status");
      expect(pill).toHaveTextContent("Snapshot Verified · 2017–2023");
      expect(pill).toHaveAttribute(
        "aria-label",
        "Dataset status: Live verified snapshot covering 2017 to 2023"
      );
    });

    it("renders local snapshot status with row count indicator", () => {
      render(<DatasetStatusPill status="local_snapshot" />);

      const pill = screen.getByRole("status");
      expect(pill).toHaveTextContent("Local Snapshot · 62,516 rows");
      expect(pill).toHaveAttribute(
        "aria-label",
        "Dataset status: Reproducible local snapshot containing 62,516 complaints"
      );
    });

    it("renders offline and degraded states with warning or error variants", () => {
      const { rerender } = render(<DatasetStatusPill status="fixture" />);
      expect(screen.getByRole("status")).toHaveTextContent("Fixture Snapshot · Offline");

      rerender(<DatasetStatusPill status="down" />);
      expect(screen.getByRole("status")).toHaveTextContent("Backend Offline");
    });

    it("passes automated axe accessibility check across variants", async () => {
      const { container } = render(
        <div>
          <DatasetStatusPill status="ready" />
          <DatasetStatusPill status="local_snapshot" />
          <DatasetStatusPill status="down" />
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
