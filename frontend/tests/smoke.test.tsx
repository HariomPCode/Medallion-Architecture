import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import HomePage from "@/app/page";

describe("Frontend Foundation Smoke Tests", () => {
  it("renders the application root page with the expected heading", () => {
    render(<HomePage />);
    const heading = screen.getByRole("heading", {
      level: 1,
      name: /finance complaints medallion/i,
    });
    expect(heading).toBeInTheDocument();
    expect(
      screen.getByText(/regulatory intelligence and complaint analytics workbench/i)
    ).toBeInTheDocument();
  });

  it("passes automated accessibility checks with zero violations", async () => {
    const { container } = render(<HomePage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("intercepts and mocks API requests deterministically via MSW", async () => {
    const response = await fetch("/api/v1/meta/dataset");
    expect(response.ok).toBe(true);
    const data = await response.json();
    expect(data).toEqual({
      status: "ready",
      data_mode: "fixture",
      total_complaints: 62516,
    });
  });
});
