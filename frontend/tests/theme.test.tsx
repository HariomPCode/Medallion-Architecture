import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, useTheme } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

function ThemeConsumer() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="active-theme">{theme}</span>
      <span data-testid="resolved-theme">{resolvedTheme}</span>
      <button onClick={() => setTheme("dark")}>Set Dark</button>
      <button onClick={() => setTheme("light")}>Set Light</button>
      <button onClick={() => setTheme("system")}>Set System</button>
    </div>
  );
}

describe("Theme System & Persistence", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    // Mock matchMedia
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: false, // Default to light system theme
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("defaults to system theme when no preference is stored", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("active-theme").textContent).toBe("system");
    expect(screen.getByTestId("resolved-theme").textContent).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("updates and persists theme selection in localStorage", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    await user.click(screen.getByText("Set Dark"));

    expect(screen.getByTestId("active-theme").textContent).toBe("dark");
    expect(screen.getByTestId("resolved-theme").textContent).toBe("dark");
    expect(localStorage.getItem("fcm-theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    await user.click(screen.getByText("Set Light"));

    expect(screen.getByTestId("active-theme").textContent).toBe("light");
    expect(screen.getByTestId("resolved-theme").textContent).toBe("light");
    expect(localStorage.getItem("fcm-theme")).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("restores stored theme from localStorage on initialization", () => {
    localStorage.setItem("fcm-theme", "dark");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("active-theme").textContent).toBe("dark");
    expect(screen.getByTestId("resolved-theme").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("supports interaction via ThemeToggle component", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const darkButton = screen.getByRole("button", { name: /switch to dark theme/i });
    await user.click(darkButton);

    expect(darkButton).toHaveAttribute("aria-pressed", "true");
    expect(localStorage.getItem("fcm-theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    const lightButton = screen.getByRole("button", { name: /switch to light theme/i });
    await user.click(lightButton);

    expect(lightButton).toHaveAttribute("aria-pressed", "true");
    expect(localStorage.getItem("fcm-theme")).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
