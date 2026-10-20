import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import QualityPage from "@/app/quality/page";
import { ThemeProvider } from "@/components/theme-provider";
import { http, HttpResponse } from "msw";
import { server } from "./mocks/server";
import { MOCK_QUALITY_SUMMARY } from "./mocks/handlers";

// Mock next/navigation
let mockSearchParams = new URLSearchParams();
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/quality",
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  useSearchParams: () => mockSearchParams,
}));

function renderQuality() {
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
        <QualityPage />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("Phase 9: Data Quality Center Page (/quality)", () => {
  beforeEach(() => {
    mockSearchParams = new URLSearchParams();
    vi.clearAllMocks();
  });

  it("renders composite score, status badge, and total evaluated records", async () => {
    renderQuality();

    expect(
      screen.getByRole("heading", { level: 1, name: /data quality center/i })
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("quality-score-panel")).toBeInTheDocument();
      expect(screen.getByTestId("composite-score-value")).toHaveTextContent("94.6");
      expect(screen.getByTestId("quality-status-badge")).toHaveTextContent("HIGH QUALITY");
      expect(screen.getAllByText(/62,516/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders all five decomposed quality dimension bars with weights and scores", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("dimension-bars-panel")).toBeInTheDocument();
    });

    // Check all 5 dimensions
    expect(screen.getByTestId("dimension-row-completeness")).toBeInTheDocument();
    expect(screen.getByTestId("dimension-row-validity")).toBeInTheDocument();
    expect(screen.getByTestId("dimension-row-consistency")).toBeInTheDocument();
    expect(screen.getByTestId("dimension-row-timeliness")).toBeInTheDocument();
    expect(screen.getByTestId("dimension-row-ml_normality")).toBeInTheDocument();

    // Verify weights (Completeness and Validity both have 25% weight)
    expect(screen.getAllByText(/Weight: 25%/i).length).toBe(2);
    expect(screen.getByText(/Weight: 20%/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Weight: 15%/i).length).toBe(2);
  });

  it("verifies ML Normality carries the special info marker and links to limitations", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("ml-normality-marker")).toBeInTheDocument();
    });

    const marker = screen.getByTestId("ml-normality-marker");
    expect(marker).toHaveTextContent(/fixed by contamination setting \(1.0%\)/i);
    expect(marker).toHaveAttribute("href", "#methodological-limitations");
  });

  it("ensures Methodological Limitations panel is ALWAYS visible on page without interaction", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("limitations-panel")).toBeInTheDocument();
    });

    const panel = screen.getByTestId("limitations-panel");
    expect(panel).toBeVisible();

    // Verify core limitations are visible
    expect(
      within(panel).getByText(/Isolation Forest identifies statistical outliers/i)
    ).toBeInTheDocument();
    expect(
      within(panel).getByText(/ML Normality dimension score is structurally bounded/i)
    ).toBeInTheDocument();
    expect(
      within(panel).getByText(/CFPB agency routing delay and is not an evaluation of company response/i)
    ).toBeInTheDocument();
  });

  it("displays AnomalySummary headline stats (flagged count, rate, and in-progress share)", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("anomaly-summary-panel")).toBeInTheDocument();
      expect(screen.getByTestId("flagged-count")).toHaveTextContent("625");
      expect(screen.getByTestId("flagged-rate")).toHaveTextContent("1.00%");
      expect(screen.getByTestId("open-cases-share")).toHaveTextContent("68.5%");
    });
  });

  it("renders AnomaliesTable with factual observation badges", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("anomalies-table-container")).toBeInTheDocument();
      expect(screen.getByText("#2001")).toBeInTheDocument();
    });

    // Check observation badges
    expect(screen.getAllByText("Open case").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Delay ≥ 7 days/i).length).toBeGreaterThan(0);
  });

  it("clicking an anomaly table row opens the shared ComplaintSheet", async () => {
    const user = userEvent.setup();
    renderQuality();

    await waitFor(() => {
      expect(screen.getByText("#2001")).toBeInTheDocument();
    });

    const link = screen.getByRole("button", { name: /view anomaly details for complaint #2001/i });
    await user.click(link);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("selected=2001"),
      expect.anything()
    );
  });

  it("displays ModelPanel with Isolation Forest parameters and copy button", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("model-panel")).toBeInTheDocument();
      expect(screen.getByText("IsolationForest")).toBeInTheDocument();
      expect(screen.getByText(/100 trees/i)).toBeInTheDocument();
      expect(screen.getByTestId("copy-run-id-button")).toBeInTheDocument();
    });
  });

  it("displays honest 'not published' state when model metadata is unavailable", async () => {
    server.use(
      http.get("*/api/v1/quality/summary", () => {
        return HttpResponse.json({
          ...MOCK_QUALITY_SUMMARY,
          model: {
            available: false,
            type: "IsolationForest",
            contamination: 0.01,
            n_estimators: 100,
            source: "notebook_constant",
          },
        });
      })
    );

    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("model-not-published-notice")).toBeInTheDocument();
      expect(
        screen.getByText(/model parameters not published by the latest pipeline run/i)
      ).toBeInTheDocument();
    });
  });

  it("handles 503 Service Unavailable state gracefully", async () => {
    server.use(
      http.get("*/api/v1/quality/summary", () => {
        return HttpResponse.json(
          { error: { code: "SERVICE_UNAVAILABLE", message: "Data Quality report unavailable" } },
          { status: 503 }
        );
      })
    );

    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("quality-503-panel")).toBeInTheDocument();
      expect(screen.getByText(/data quality report unavailable \(503\)/i)).toBeInTheDocument();
    });
  });

  it("enforces strict language rules (§15.4): never uses 'error' or 'accuracy' to describe anomaly score or quality score", async () => {
    renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("quality-score-panel")).toBeInTheDocument();
      expect(screen.getByTestId("limitations-panel")).toBeInTheDocument();
    });

    const bodyText = document.body.textContent || "";

    // 1. Never describe the composite quality score as an "accuracy" score
    expect(bodyText).not.toMatch(/accuracy score/i);
    expect(bodyText).not.toMatch(/pipeline accuracy/i);
    expect(bodyText).not.toMatch(/quality accuracy/i);

    // 2. Never describe anomalies as errors or fraud
    expect(bodyText).not.toMatch(/anomaly error/i);
    expect(bodyText).not.toMatch(/fraudulent/i);
    expect(bodyText).not.toMatch(/fraud score/i);
    expect(bodyText).not.toMatch(/record error/i);
    expect(bodyText).not.toMatch(/data error/i);
  });

  it("passes automated axe accessibility check with zero violations", async () => {
    const { container } = renderQuality();

    await waitFor(() => {
      expect(screen.getByTestId("quality-score-panel")).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
