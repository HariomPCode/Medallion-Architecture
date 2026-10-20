import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { DataTable } from "@/components/data/DataTable";
import { ColumnDef } from "@tanstack/react-table";

interface TestRow {
  id: string;
  name: string;
  category: string;
  count: number | null;
  rate: number | null;
}

const testColumns: ColumnDef<TestRow, any>[] = [
  {
    accessorKey: "name",
    header: "Product Name",
    cell: (info) => info.getValue(),
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: (info) => info.getValue(),
  },
  {
    accessorKey: "count",
    header: "Complaints Count",
    meta: { align: "right" as const },
    cell: (info) => (info.getValue() != null ? String(info.getValue()) : null),
  },
  {
    accessorKey: "rate",
    header: "Timely Rate",
    meta: { align: "right" as const },
    cell: (info) => (info.getValue() != null ? `${info.getValue()}%` : null),
  },
];

const testData: TestRow[] = [
  { id: "1", name: "Checking Account", category: "Banking", count: 12000, rate: 96.5 },
  { id: "2", name: "Credit Card", category: "Payments", count: 15000, rate: 95.2 },
  { id: "3", name: "Mortgage", category: "Lending", count: 6000, rate: 99.1 },
  { id: "4", name: "Student Loan", category: "Lending", count: 500, rate: 97.4 },
  { id: "5", name: "Credit Report", category: "Credit Reporting", count: 7000, rate: 93.8 },
  { id: "6", name: "Money Transfer", category: "Payments", count: 3000, rate: 94.9 },
  { id: "7", name: "Vehicle Loan", category: "Lending", count: 800, rate: 92.1 },
  { id: "8", name: "Debt Collection", category: "Collections", count: 2500, rate: 91.5 },
  { id: "9", name: "Savings Account", category: "Banking", count: 4000, rate: 98.0 },
  { id: "10", name: "Prepaid Card", category: "Payments", count: 1200, rate: 93.2 },
  { id: "11", name: "Personal Loan", category: "Lending", count: 900, rate: 95.0 },
  { id: "12", name: "Overdraft Service", category: "Banking", count: 2200, rate: null }, // Null rate test
];

describe("Day 4: DataTable Component", () => {
  it("renders table headers, rows, and formatted data cells", () => {
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        pageSize={5}
      />
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Product Name")).toBeInTheDocument();
    expect(screen.getByText("Category")).toBeInTheDocument();
    expect(screen.getByText("Complaints Count")).toBeInTheDocument();

    // First page rows (pageSize = 5)
    expect(screen.getByText("Checking Account")).toBeInTheDocument();
    expect(screen.getByText("Credit Card")).toBeInTheDocument();
    expect(screen.getByText("Mortgage")).toBeInTheDocument();
    expect(screen.getByText("Student Loan")).toBeInTheDocument();
    expect(screen.getByText("Credit Report")).toBeInTheDocument();

    // 6th row should not be in the first page DOM
    expect(screen.queryByText("Money Transfer")).not.toBeInTheDocument();
  });

  it("safely handles null and missing values by displaying fallback '—'", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        pageSize={12} // Show all rows including row 12 with null rate
      />
    );

    expect(screen.getByText("Overdraft Service")).toBeInTheDocument();
    // The null rate cell renders "—"
    const row = screen.getByText("Overdraft Service").closest("tr")!;
    expect(within(row).getByText("—")).toBeInTheDocument();
  });

  it("handles sorting when a column header button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        pageSize={5}
      />
    );

    const sortButton = screen.getByRole("button", { name: "Sort by Product Name" });
    const headerTh = sortButton.closest("th")!;

    expect(headerTh).toHaveAttribute("aria-sort", "none");

    // Click once for ascending sort
    await user.click(sortButton);
    expect(headerTh).toHaveAttribute("aria-sort", "ascending");
    // "Checking Account" should remain first alphabetically
    expect(screen.getByText("Checking Account")).toBeInTheDocument();

    // Click again for descending sort
    await user.click(sortButton);
    expect(headerTh).toHaveAttribute("aria-sort", "descending");
    // Alphabetically last items on first page: Vehicle Loan, Student Loan, Savings Account, etc.
    expect(screen.getByText("Vehicle Loan")).toBeInTheDocument();
  });

  it("handles pagination navigation and disables buttons at boundaries", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        pageSize={5}
      />
    );

    const prevBtn = screen.getByRole("button", { name: "Go to previous page" });
    const nextBtn = screen.getByRole("button", { name: "Go to next page" });
    const summary = screen.getByTestId("table-pagination-summary");

    // Page 1: Previous is disabled, Next is enabled
    expect(prevBtn).toBeDisabled();
    expect(nextBtn).toBeEnabled();
    expect(summary).toHaveTextContent("Showing 1 to 5 of 12 entries");

    // Go to page 2
    await user.click(nextBtn);
    expect(prevBtn).toBeEnabled();
    expect(nextBtn).toBeEnabled();
    expect(summary).toHaveTextContent("Showing 6 to 10 of 12 entries");
    expect(screen.getByText("Money Transfer")).toBeInTheDocument();

    // Go to page 3 (last page with 2 records)
    await user.click(nextBtn);
    expect(prevBtn).toBeEnabled();
    expect(nextBtn).toBeDisabled();
    expect(summary).toHaveTextContent("Showing 11 to 12 of 12 entries");
    expect(screen.getByText("Personal Loan")).toBeInTheDocument();
    expect(screen.getByText("Overdraft Service")).toBeInTheDocument();

    // Go back to page 2
    await user.click(prevBtn);
    expect(summary).toHaveTextContent("Showing 6 to 10 of 12 entries");
  });

  it("updates rows per page when selector changes", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        pageSize={5}
        pageSizeOptions={[5, 10, 20]}
      />
    );

    const select = screen.getByRole("combobox", { name: "Select rows per page" });
    await user.selectOptions(select, "10");

    const summary = screen.getByTestId("table-pagination-summary");
    expect(summary).toHaveTextContent("Showing 1 to 10 of 12 entries");
    expect(screen.getByText("Prepaid Card")).toBeInTheDocument();
  });

  it("renders empty state when data array is empty", () => {
    render(
      <DataTable
        columns={testColumns}
        data={[]}
        emptyTitle="No complaints found"
        emptyMessage="Try adjusting filters."
      />
    );

    expect(screen.getByText("No complaints found")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting filters.")).toBeInTheDocument();
    expect(screen.getByText("0 entries")).toBeInTheDocument();
  });

  it("renders skeleton rows when loading is true", () => {
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        loading={true}
      />
    );

    // Buttons should be disabled during loading
    expect(screen.getByRole("button", { name: "Go to previous page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Go to next page" })).toBeDisabled();
  });

  it("renders error state when error is provided", () => {
    render(
      <DataTable
        columns={testColumns}
        data={testData}
        error="Failed to load records from backend."
      />
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Failed to load records from backend.")).toBeInTheDocument();
  });

  it("passes automated axe accessibility check", async () => {
    const { container } = render(
      <DataTable
        columns={testColumns}
        data={testData.slice(0, 5)}
        pageSize={5}
      />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
