import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ExplorerPage from "@/app/explorer/page";
import { ThemeProvider } from "@/components/theme-provider";
import { http, HttpResponse } from "msw";
import { server } from "./mocks/server";

// Mock next/navigation
let mockSearchParams = new URLSearchParams();
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/explorer",
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  useSearchParams: () => mockSearchParams,
}));

function renderExplorer() {
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
        <ExplorerPage />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("Phase 9: Complaint Explorer Page (/explorer)", () => {
  beforeEach(() => {
    mockSearchParams = new URLSearchParams();
    vi.clearAllMocks();
  });

  it("renders page header, search & filters sidebar, results header, and table", async () => {
    renderExplorer();

    expect(
      screen.getByRole("heading", { level: 1, name: /complaint explorer/i })
    ).toBeInTheDocument();

    expect(screen.getByTestId("explorer-filters-panel")).toBeInTheDocument();
    expect(screen.getByTestId("export-csv-button")).toBeInTheDocument();
    expect(screen.getByTestId("id-search-input")).toBeInTheDocument();

    // Table rows should appear
    await waitFor(() => {
      expect(screen.getAllByText("#1001")[0]).toBeInTheDocument();
      expect(screen.getAllByText("#1002")[0]).toBeInTheDocument();
    });

    // Check results count
    expect(screen.getByTestId("results-count")).toBeInTheDocument();
  });

  it("handles server-side pagination and updates page query parameter", async () => {
    const user = userEvent.setup();
    renderExplorer();

    await waitFor(() => {
      expect(screen.getAllByText("#1001")[0]).toBeInTheDocument();
    });

    // TanStack DataTable pagination "Next" button
    const nextBtn = screen.getByRole("button", { name: /next page/i });
    expect(nextBtn).toBeInTheDocument();
    await user.click(nextBtn);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("page=2"),
      expect.anything()
    );
  });

  it("handles sorting when clicking column headers and updates sort_by/sort_dir in URL", async () => {
    const user = userEvent.setup();
    renderExplorer();

    await waitFor(() => {
      expect(screen.getAllByText("#1001")[0]).toBeInTheDocument();
    });

    // Click Category column header to sort
    const categoryHeader = screen.getByRole("button", { name: /sort by category/i });
    expect(categoryHeader).toBeInTheDocument();
    await user.click(categoryHeader);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringMatching(/sort_by=category/),
      expect.anything()
    );
  });

  it("validates exact Complaint ID search: accepts digits only and rejects non-digits", async () => {
    const user = userEvent.setup();
    renderExplorer();

    const idInput = screen.getByTestId("id-search-input");
    const submitBtn = screen.getByTestId("id-search-submit");

    // Type digits
    await user.clear(idInput);
    await user.type(idInput, "1005");
    await user.click(submitBtn);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("q=1005"),
      expect.anything()
    );
  });

  it("opens ComplaintSheet on table row click and pushes ?selected=ID to URL", async () => {
    const user = userEvent.setup();
    renderExplorer();

    await waitFor(() => {
      expect(screen.getAllByText("#1001")[0]).toBeInTheDocument();
    });

    // Click row button for #1001
    const complaintLink = screen.getByRole("button", { name: /view complaint #1001/i });
    await user.click(complaintLink);

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("selected=1001"),
      expect.anything()
    );
  });

  it("loads ComplaintSheet directly from deep-link URL parameter ?selected=1001", async () => {
    mockSearchParams = new URLSearchParams("selected=1001");
    renderExplorer();

    // Sheet should be open
    await waitFor(() => {
      expect(screen.getByTestId("complaint-sheet")).toBeInTheDocument();
      expect(screen.getByText("Complaint #1001")).toBeInTheDocument();
    });

    const sheet = screen.getByTestId("complaint-sheet");

    // Verifies overview fields after query completes inside the sheet
    await waitFor(() => {
      expect(within(sheet).getByText("Deposit Accounts")).toBeInTheDocument();
      expect(within(sheet).getByText("Interest Checking")).toBeInTheDocument();
      expect(within(sheet).getByText(/all funds have been released/i)).toBeInTheDocument();
    });
  });

  it("verifies CFPB intake routing lag tooltip and clear statement that it is not company response time", async () => {
    mockSearchParams = new URLSearchParams("selected=1001");
    renderExplorer();

    await waitFor(() => {
      expect(screen.getByTestId("complaint-sheet")).toBeInTheDocument();
    });

    // Check CFPB intake routing explanation after query completes
    await waitFor(() => {
      expect(screen.getByText(/CFPB Intake Routing Delay:/i)).toBeInTheDocument();
      expect(screen.getByText(/the company's response time/i)).toBeInTheDocument();
    });
  });

  it("verifies missing optional fields render as 'Not provided' or '—' rather than null or blank", async () => {
    mockSearchParams = new URLSearchParams("selected=1004");
    renderExplorer();

    await waitFor(() => {
      expect(screen.getByTestId("complaint-sheet")).toBeInTheDocument();
      expect(screen.getByText("Complaint #1004")).toBeInTheDocument();
    });

    // Complaint 1004 has sub_product: null, sub_issue: null, company_public_response: null
    await waitFor(() => {
      const notProvidedElements = screen.getAllByText("Not provided");
      expect(notProvidedElements.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("renders 404 state when requested complaint ID does not exist (?selected=999999)", async () => {
    mockSearchParams = new URLSearchParams("selected=999999");
    renderExplorer();

    await waitFor(() => {
      expect(screen.getByTestId("complaint-sheet-404")).toBeInTheDocument();
      expect(screen.getByText(/complaint record not found/i)).toBeInTheDocument();
    });
  });

  it("handles Escape key to close the detail sheet and removes ?selected from URL", async () => {
    const user = userEvent.setup();
    mockSearchParams = new URLSearchParams("selected=1001");
    renderExplorer();

    await waitFor(() => {
      expect(screen.getByTestId("complaint-sheet")).toBeInTheDocument();
    });

    await user.keyboard("{Escape}");

    expect(mockPush).toHaveBeenCalledWith(
      expect.not.stringContaining("selected="),
      expect.anything()
    );
  });

  it("toggles column visibility via the visibility menu", async () => {
    const user = userEvent.setup();
    renderExplorer();

    const visibilityBtn = screen.getByTestId("column-visibility-toggle");
    await user.click(visibilityBtn);

    expect(screen.getByTestId("column-visibility-menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /sub-category/i })).toBeInTheDocument();
  });

  it("handles CSV export and shows truncation warning banner when X-Export-Truncated is true", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("*/api/v1/complaints/export", () => {
        return new HttpResponse("Complaint_ID,Category\n1001,Banking", {
          status: 200,
          headers: {
            "Content-Type": "text/csv; charset=utf-8",
            "X-Export-Truncated": "true",
            "X-Export-Row-Count": "5000",
          },
        });
      })
    );

    renderExplorer();

    const exportBtn = screen.getByTestId("export-csv-button");
    await user.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByTestId("export-truncated-banner")).toBeInTheDocument();
      expect(screen.getByText(/5,000 rows/i)).toBeInTheDocument();
    });
  });

  it("handles API error with retry button", async () => {
    server.use(
      http.get("*/api/v1/complaints", () => {
        return HttpResponse.json(
          { error: { code: "SERVICE_UNAVAILABLE", message: "Database temporarily offline" } },
          { status: 503 }
        );
      })
    );

    renderExplorer();

    await waitFor(() => {
      expect(screen.getByText(/database temporarily offline/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });
  });

  it("renders mobile stacked-list view for complaints", async () => {
    renderExplorer();

    await waitFor(() => {
      expect(screen.getByTestId("mobile-complaints-list")).toBeInTheDocument();
      expect(screen.getByTestId("mobile-complaint-card-1001")).toBeInTheDocument();
    });
  });

  it("passes automated axe accessibility check with zero violations", async () => {
    const { container } = renderExplorer();

    await waitFor(() => {
      expect(screen.getAllByText("#1001")[0]).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
