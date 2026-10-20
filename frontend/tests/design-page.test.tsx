import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import DesignPage from "@/app/design/page";
import { ThemeProvider } from "@/components/theme-provider";

// Mock next/navigation notFound
const mockNotFound = vi.fn();
vi.mock("next/navigation", () => ({
  notFound: () => mockNotFound(),
}));

describe("Design System Preview Route (/design)", () => {
  const originalEnv = process.env.NODE_ENV;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // @ts-expect-error Restoring NODE_ENV
    process.env.NODE_ENV = originalEnv;
  });

  it("renders preview page with advisory disclaimer in non-production", () => {
    // @ts-expect-error setting NODE_ENV for test
    process.env.NODE_ENV = "development";

    render(
      <ThemeProvider>
        <DesignPage />
      </ThemeProvider>
    );

    expect(
      screen.getByText("Development-Only Design System Preview")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Financial Editorial Design System")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "1. Typography Hierarchy (IBM Plex)" })
    ).toBeInTheDocument();
  });

  it("triggers notFound() when NODE_ENV is production", () => {
    // @ts-expect-error setting NODE_ENV for test
    process.env.NODE_ENV = "production";

    DesignPage();

    expect(mockNotFound).toHaveBeenCalledTimes(1);
  });
});
