import { describe, it, expect } from "vitest";
import {
  getCategoryColor,
  getStatusVariant,
  getStatusMeta,
  CATEGORY_COLORS,
  type CategoryKey,
} from "@/lib/colors";

describe("Color & Visual Tokens", () => {
  describe("getCategoryColor", () => {
    it("returns correct light and dark palette colors for all five categories", () => {
      const categories: CategoryKey[] = [
        "Banking",
        "Payments",
        "Credit Reporting",
        "Lending",
        "Collections",
      ];

      for (const cat of categories) {
        const lightColor = getCategoryColor(cat, "light");
        const darkColor = getCategoryColor(cat, "dark");

        expect(lightColor).toBe(CATEGORY_COLORS[cat].light);
        expect(darkColor).toBe(CATEGORY_COLORS[cat].dark);
        expect(lightColor).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(darkColor).toMatch(/^#[0-9A-Fa-f]{6}$/);
      }
    });

    it("handles case-insensitive category lookup", () => {
      expect(getCategoryColor("banking", "light")).toBe("#2F5D8A");
      expect(getCategoryColor("PAYMENTS", "light")).toBe("#0F766E");
    });

    it("returns neutral fallback color for unknown categories", () => {
      expect(getCategoryColor("Unknown Category", "light")).toBe("#475467");
      expect(getCategoryColor("Unknown Category", "dark")).toBe("#94A3B8");
    });
  });

  describe("getStatusVariant", () => {
    it("maps operational / healthy states to positive", () => {
      expect(getStatusVariant("ready")).toBe("positive");
      expect(getStatusVariant("live")).toBe("positive");
      expect(getStatusVariant("healthy")).toBe("positive");
      expect(getStatusVariant("good")).toBe("positive");
      expect(getStatusVariant("timely")).toBe("positive");
      expect(getStatusVariant("yes")).toBe("positive");
    });

    it("maps advisory / snapshot states to warning", () => {
      expect(getStatusVariant("warning")).toBe("warning");
      expect(getStatusVariant("degraded")).toBe("warning");
      expect(getStatusVariant("stale")).toBe("warning");
      expect(getStatusVariant("local_snapshot")).toBe("warning");
      expect(getStatusVariant("fixture")).toBe("warning");
      expect(getStatusVariant("in_progress")).toBe("warning");
    });

    it("maps error / outage states to negative", () => {
      expect(getStatusVariant("down")).toBe("negative");
      expect(getStatusVariant("error")).toBe("negative");
      expect(getStatusVariant("critical")).toBe("negative");
      expect(getStatusVariant("failing")).toBe("negative");
      expect(getStatusVariant("no")).toBe("negative");
      expect(getStatusVariant("untimely")).toBe("negative");
    });

    it("maps missing or unknown states to neutral", () => {
      expect(getStatusVariant(null)).toBe("neutral");
      expect(getStatusVariant(undefined)).toBe("neutral");
      expect(getStatusVariant("not_published")).toBe("neutral");
      expect(getStatusVariant("arbitrary_status")).toBe("neutral");
    });
  });

  describe("getStatusMeta", () => {
    it("returns structured metadata with variant, label, and description", () => {
      const liveMeta = getStatusMeta("ready");
      expect(liveMeta.variant).toBe("positive");
      expect(liveMeta.label).toBe("Live");
      expect(liveMeta.description).toBeTruthy();

      const snapshotMeta = getStatusMeta("local_snapshot");
      expect(snapshotMeta.variant).toBe("warning");
      expect(snapshotMeta.label).toBe("Local Snapshot");

      const errorMeta = getStatusMeta("error");
      expect(errorMeta.variant).toBe("negative");

      const nullMeta = getStatusMeta(null);
      expect(nullMeta.variant).toBe("neutral");
    });
  });
});
