import { describe, it, expect } from "vitest";
import {
  formatNumber,
  formatDecimal,
  formatCompact,
  formatPercent,
  formatCurrency,
  formatDate,
  formatDateRange,
} from "@/lib/format";

describe("Formatting Utilities", () => {
  describe("formatNumber", () => {
    it("formats valid integers with commas", () => {
      expect(formatNumber(62516)).toBe("62,516");
      expect(formatNumber(1494)).toBe("1,494");
      expect(formatNumber(0)).toBe("0");
      expect(formatNumber("1000000")).toBe("1,000,000");
    });

    it("handles null, undefined, empty strings, and NaN gracefully", () => {
      expect(formatNumber(null)).toBe("—");
      expect(formatNumber(undefined)).toBe("—");
      expect(formatNumber("")).toBe("—");
      expect(formatNumber("invalid")).toBe("—");
      expect(formatNumber(NaN)).toBe("—");
      expect(formatNumber(null, "N/A")).toBe("N/A");
    });
  });

  describe("formatDecimal", () => {
    it("formats decimal numbers with specified precision", () => {
      expect(formatDecimal(1.222, 2)).toBe("1.22");
      expect(formatDecimal(0, 2)).toBe("0.00");
      expect(formatDecimal(14.5, 1)).toBe("14.5");
    });

    it("handles invalid inputs with fallback", () => {
      expect(formatDecimal(null)).toBe("—");
      expect(formatDecimal(undefined)).toBe("—");
      expect(formatDecimal("abc")).toBe("—");
    });
  });

  describe("formatCompact", () => {
    it("formats numbers into compact notation", () => {
      expect(formatCompact(62516)).toBe("62.5K");
      expect(formatCompact(1200000)).toBe("1.2M");
      expect(formatCompact(500)).toBe("500");
    });

    it("handles missing inputs with fallback", () => {
      expect(formatCompact(null)).toBe("—");
      expect(formatCompact(undefined)).toBe("—");
    });
  });

  describe("formatPercent", () => {
    it("formats 0..1 ratio to percentage string", () => {
      expect(formatPercent(0.9606, 1)).toBe("96.1%");
      expect(formatPercent(0.9377, 1)).toBe("93.8%");
      expect(formatPercent(1.0, 0)).toBe("100%");
      expect(formatPercent(0, 1)).toBe("0.0%");
    });

    it("formats 0..100 numbers to percentage string", () => {
      expect(formatPercent(96.06, 1)).toBe("96.1%");
      expect(formatPercent(93.8, 1)).toBe("93.8%");
    });

    it("handles missing or invalid values with fallback", () => {
      expect(formatPercent(null)).toBe("—");
      expect(formatPercent(undefined)).toBe("—");
      expect(formatPercent("not a number")).toBe("—");
    });
  });

  describe("formatCurrency", () => {
    it("formats numbers to USD currency string", () => {
      expect(formatCurrency(1250)).toBe("$1,250");
      expect(formatCurrency(0)).toBe("$0");
      expect(formatCurrency(99.99)).toBe("$100");
    });

    it("handles missing values with fallback", () => {
      expect(formatCurrency(null)).toBe("—");
      expect(formatCurrency(undefined)).toBe("—");
    });
  });

  describe("formatDate", () => {
    it("formats ISO date string without timezone skew", () => {
      expect(formatDate("2023-08-28")).toBe("28 Aug 2023");
      expect(formatDate("2017-05-01")).toBe("1 May 2017");
      expect(formatDate("2020-01-15T00:00:00Z")).toBe("15 Jan 2020");
    });

    it("handles invalid date strings with fallback", () => {
      expect(formatDate("invalid-date")).toBe("—");
      expect(formatDate(null)).toBe("—");
      expect(formatDate(undefined)).toBe("—");
      expect(formatDate("")).toBe("—");
    });
  });

  describe("formatDateRange", () => {
    it("formats full date range across years", () => {
      expect(formatDateRange("2017-05-01", "2023-08-28")).toBe(
        "1 May 2017 – 28 Aug 2023"
      );
    });

    it("formats date range within same year", () => {
      expect(formatDateRange("2023-01-15", "2023-08-28")).toBe(
        "15 Jan – 28 Aug 2023"
      );
    });

    it("handles one-sided or missing date ranges", () => {
      expect(formatDateRange("2017-05-01", null)).toBe("From 1 May 2017");
      expect(formatDateRange(null, "2023-08-28")).toBe("Through 28 Aug 2023");
      expect(formatDateRange(null, null)).toBe("—");
    });
  });
});
