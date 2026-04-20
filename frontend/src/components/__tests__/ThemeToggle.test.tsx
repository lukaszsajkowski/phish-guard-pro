import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ThemeProvider } from "../theme-provider";
import { ThemeToggle } from "../app/ThemeToggle";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

function renderWithTheme() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  );
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorageMock.clear();
    document.documentElement.classList.remove("dark");
  });

  it("renders the toggle button", () => {
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    expect(button).toBeInTheDocument();
  });

  it("defaults to light mode when no localStorage value", () => {
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    expect(button).toHaveAttribute("aria-label", "Switch to dark mode");
  });

  it("reads dark mode from localStorage", () => {
    localStorageMock.getItem.mockReturnValueOnce("dark");
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    // After useEffect runs, aria-label should reflect dark mode
    expect(button).toHaveAttribute("aria-label", "Switch to light mode");
  });

  it("toggles from light to dark on click", () => {
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-label", "Switch to light mode");
    expect(localStorageMock.setItem).toHaveBeenCalledWith("pg_theme", "dark");
  });

  it("toggles from dark to light on click", () => {
    localStorageMock.getItem.mockReturnValueOnce("dark");
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-label", "Switch to dark mode");
    expect(localStorageMock.setItem).toHaveBeenCalledWith("pg_theme", "light");
  });

  it("applies .dark class to document.documentElement when toggled to dark", () => {
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    fireEvent.click(button); // light -> dark
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("removes .dark class from document.documentElement when toggled to light", () => {
    localStorageMock.getItem.mockReturnValueOnce("dark");
    renderWithTheme();
    const button = screen.getByTestId("theme-toggle");
    fireEvent.click(button); // dark -> light
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
