import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "vitest-axe";
import HomePage from "@/app/page";
import { ThemeProvider } from "@/components/theme-provider";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{ui}</ThemeProvider>
    </QueryClientProvider>
  );
}

describe("Frontend Foundation Smoke Tests", () => {
  it("renders the application root page with the expected heading", async () => {
    renderWithClient(<HomePage />);
    const heading = screen.getByRole("heading", {
      level: 1,
      name: /finance complaints overview/i,
    });
    expect(heading).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("dataset-scope-line")).toHaveTextContent(
        /62,516 complaints/i
      );
    });
  });

  it("passes automated accessibility checks with zero violations", async () => {
    const { container } = renderWithClient(<HomePage />);
    await waitFor(() => {
      expect(screen.getByTestId("dataset-scope-line")).toHaveTextContent(
        /62,516 complaints/i
      );
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("intercepts and mocks API requests deterministically via MSW", async () => {
    const response = await fetch("/api/v1/meta/dataset");
    expect(response.ok).toBe(true);
    const data = await response.json();
    expect(data.total_silver_records).toBe(62516);
    expect(data.data_origin).toBe("local_snapshot");
    expect(data.coverage.start).toBe("2017-05-01");
    expect(data.coverage.end).toBe("2023-08-28");
  });
});
