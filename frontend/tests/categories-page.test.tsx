import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CategoryAnalyticsPage from "@/app/categories/page";
import { ThemeProvider } from "@/components/theme-provider";
import { http, HttpResponse } from "msw";
import { server } from "./mocks/server";

// Mock next/navigation
let mockSearchParams = new URLSearchParams();
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/categories",
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  useSearchParams: () => mockSearchParams,
}));

function renderCategories() {
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
        <CategoryAnalyticsPage />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("Phase 8: Category Analytics Page (/categories)", () => {
  beforeEach(() => {
    mockSearchParams = new URLSearchParams();
    vi.clearAllMocks();
  });

  it("renders page header, segmented view controls, and filter bar", async () => {
    renderCategories();

    expect(
      screen.getByRole("heading", { level: 1, name: /category analytics/i })
    ).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /^category view$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sub-category view$/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /categories breakdown/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/\(5 categories\)/i)).toBeInTheDocument();
    });
  });

  it("toggles between Category View and Sub-Category View", async () => {
    const user = userEvent.setup();
    renderCategories();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /categories breakdown/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/\(5 categories\)/i)).toBeInTheDocument();
    });

    const subCategoryBtn = screen.getByRole("button", { name: /^sub-category view$/i });
    await user.click(subCategoryBtn);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /sub-categories breakdown/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/\(9 sub-categories\)/i)).toBeInTheDocument();
    });
  });

  it("toggles secondary legacy response rate (M-04) column on and off", async () => {
    const user = userEvent.setup();
    renderCategories();

    const table = await screen.findByRole("table", { name: /category breakdown table/i });
    expect(within(table).queryByText(/legacy rate/i)).not.toBeInTheDocument();

    // Toggle legacy rate column
    const toggleBtn = screen.getByRole("button", {
      name: /toggle secondary legacy response rate column/i,
    });
    await user.click(toggleBtn);

    // Column header should now be visible
    expect(within(table).getByText(/legacy rate/i)).toBeInTheDocument();
  });

  it("sorts table columns by total volume descending and ascending", async () => {
    const user = userEvent.setup();
    renderCategories();

    const table = await screen.findByRole("table", { name: /category breakdown table/i });
    await waitFor(() => {
      expect(within(table).getByText("Banking")).toBeInTheDocument();
    });

    const totalSortBtn = within(table).getByRole("button", { name: /total/i });

    // Initial state is desc: Banking (24,814) should be top data row
    const tbody = table.querySelector("tbody")!;
    const rowsBefore = within(tbody).getAllByRole("row");
    expect(rowsBefore[0]).toHaveTextContent("Banking");

    // Click to toggle to asc
    await user.click(totalSortBtn);

    const rowsAfter = within(tbody).getAllByRole("row");
    // Smallest category should now be top row: Collections (2,736)
    expect(rowsAfter[0]).toHaveTextContent("Collections");
  });

  it("triggers drill-down filter update when clicking a category row", async () => {
    const user = userEvent.setup();
    renderCategories();

    const table = await screen.findByRole("table", { name: /category breakdown table/i });
    await waitFor(() => {
      expect(within(table).getByText("Banking")).toBeInTheDocument();
    });

    // Find drill down button
    const row = within(table).getByRole("button", {
      name: /drill down into category banking/i,
    });
    await user.click(row);

    // Verify router was updated with category parameter
    expect(mockPush.mock.calls[0][0]).toContain("category=Banking");
  });

  it("verifies totals row reconciles against summary total (AC-8.3)", async () => {
    renderCategories();

    await waitFor(() => {
      const totalCell = screen.getByTestId("category-table-total");
      expect(totalCell).toHaveTextContent("62,516");
    });
  });

  it("enforces Year-over-Year partial year exclusion policy (AC-8.4)", async () => {
    renderCategories();

    const yoyTable = await screen.findByRole("table", {
      name: /year-over-year volume growth table/i,
    });

    await waitFor(() => {
      expect(within(yoyTable).getByText("2017")).toBeInTheDocument();
    });

    // 2017 & 2023 must show partial badges and exclusion text
    const row2017 = within(yoyTable).getByText("2017").closest("tr")!;
    expect(within(row2017).getByText(/partial period/i)).toBeInTheDocument();
    expect(within(row2017).getByText(/excluded \(partial\)/i)).toBeInTheDocument();

    const row2023 = within(yoyTable).getByText("2023").closest("tr")!;
    expect(within(row2023).getByText(/partial period/i)).toBeInTheDocument();
    expect(within(row2023).getByText(/excluded \(partial\)/i)).toBeInTheDocument();

    // Complete year 2022 must show +16.2% signed growth percentage
    const row2022 = within(yoyTable).getByText("2022").closest("tr")!;
    expect(within(row2022).getByText("+16.2%")).toBeInTheDocument();
  });

  it("handles independent panel errors gracefully with retry mechanism (AC-8.6)", async () => {
    server.use(
      http.get("/api/v1/analytics/by-category", () => {
        return HttpResponse.json({ detail: "Database connection lost" }, { status: 503 });
      })
    );

    renderCategories();

    await waitFor(() => {
      expect(screen.getAllByText(/database connection lost/i).length).toBeGreaterThan(0);
    });

    expect(screen.getAllByRole("button", { name: /try again|retry/i }).length).toBeGreaterThan(0);
  });

  it("passes automated accessibility checks with zero violations", async () => {
    const { container } = renderCategories();

    await waitFor(() => {
      expect(screen.getByTestId("category-table-total")).toHaveTextContent("62,516");
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
