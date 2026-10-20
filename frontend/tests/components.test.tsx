import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

describe("Base UI Components & Accessibility", () => {
  it("renders Button with accessible attributes and passes axe", async () => {
    const { container } = render(
      <Button variant="default" size="default">
        Filter Complaints
      </Button>
    );

    const button = screen.getByRole("button", { name: "Filter Complaints" });
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders disabled Button with disabled attribute", () => {
    render(<Button disabled>Submit</Button>);
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  });

  it("renders Input with accessible label association and passes axe", async () => {
    const { container } = render(
      <div>
        <label htmlFor="complaint-id">Complaint ID</label>
        <Input id="complaint-id" placeholder="e.g. 12345" />
      </div>
    );

    const input = screen.getByLabelText("Complaint ID");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("placeholder", "e.g. 12345");

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders Select with accessible options and passes axe", async () => {
    const { container } = render(
      <div>
        <label htmlFor="category-select">Category</label>
        <Select id="category-select" defaultValue="banking">
          <option value="banking">Banking</option>
          <option value="payments">Payments</option>
        </Select>
      </div>
    );

    const select = screen.getByLabelText("Category");
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue("banking");

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders Card structure cleanly and passes axe", async () => {
    const { container } = render(
      <Card>
        <CardHeader>
          <CardTitle>Total Volume</CardTitle>
          <CardDescription>All recorded complaints</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="tabular-nums font-bold">62,516</p>
        </CardContent>
        <CardFooter>
          <span>Verified Gold Baseline</span>
        </CardFooter>
      </Card>
    );

    expect(screen.getByText("Total Volume")).toBeInTheDocument();
    expect(screen.getByText("62,516")).toBeInTheDocument();

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders Badge variants with dot indicator and passes axe", async () => {
    const { container } = render(
      <div className="flex gap-2">
        <Badge variant="positive" dot>
          Live
        </Badge>
        <Badge variant="warning" dot>
          Local Snapshot
        </Badge>
        <Badge variant="negative" dot>
          Down
        </Badge>
      </div>
    );

    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("Local Snapshot")).toBeInTheDocument();

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders Skeleton loader with proper ARIA attributes and passes axe", async () => {
    const { container } = render(<Skeleton className="h-4 w-32" />);
    const skeleton = screen.getByRole("status");
    expect(skeleton).toHaveAttribute("aria-busy", "true");

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders Separator with proper ARIA role", () => {
    render(<Separator orientation="horizontal" decorative={false} />);
    const separator = screen.getByRole("separator");
    expect(separator).toBeInTheDocument();
    expect(separator).toHaveAttribute("aria-orientation", "horizontal");
  });
});
