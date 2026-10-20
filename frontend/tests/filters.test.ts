import { describe, it, expect } from "vitest";
import {
  parseFiltersFromSearchParams,
  serializeFiltersToSearchParams,
  hasActiveFilters,
  type ComplaintFilterState,
} from "@/lib/filters";

describe("URL Filter Utilities", () => {
  describe("parseFiltersFromSearchParams", () => {
    it("parses single and comma-separated categories and sub-categories", () => {
      const params = new URLSearchParams("category=Banking,Payments&sub_category=Card%20Products");
      const filters = parseFiltersFromSearchParams(params);

      expect(filters.category).toEqual(["Banking", "Payments"]);
      expect(filters.sub_category).toEqual(["Card Products"]);
    });

    it("parses multiple repeated query parameters into arrays", () => {
      const params = new URLSearchParams();
      params.append("state", "ca");
      params.append("state", "ny");

      const filters = parseFiltersFromSearchParams(params);
      expect(filters.state).toEqual(["CA", "NY"]);
    });

    it("validates timely response parameter strictly to 'Yes' or 'No'", () => {
      expect(parseFiltersFromSearchParams(new URLSearchParams("timely=Yes")).timely).toBe("Yes");
      expect(parseFiltersFromSearchParams(new URLSearchParams("timely=No")).timely).toBe("No");
      expect(parseFiltersFromSearchParams(new URLSearchParams("timely=Maybe")).timely).toBeUndefined();
    });

    it("validates ISO YYYY-MM-DD date filters and ignores invalid formats", () => {
      const valid = parseFiltersFromSearchParams(
        new URLSearchParams("date_from=2020-01-01&date_to=2023-08-28")
      );
      expect(valid.date_from).toBe("2020-01-01");
      expect(valid.date_to).toBe("2023-08-28");

      const invalid = parseFiltersFromSearchParams(
        new URLSearchParams("date_from=invalid-date&date_to=2023/08/28")
      );
      expect(invalid.date_from).toBeUndefined();
      expect(invalid.date_to).toBeUndefined();
    });

    it("validates pagination boundaries (page >= 1, 1 <= page_size <= 100)", () => {
      const valid = parseFiltersFromSearchParams(
        new URLSearchParams("page=3&page_size=50&sort_by=date_received&sort_dir=desc")
      );
      expect(valid.page).toBe(3);
      expect(valid.page_size).toBe(50);
      expect(valid.sort_by).toBe("date_received");
      expect(valid.sort_dir).toBe("desc");

      const invalid = parseFiltersFromSearchParams(
        new URLSearchParams("page=-5&page_size=500&sort_dir=invalid")
      );
      expect(invalid.page).toBeUndefined();
      expect(invalid.page_size).toBeUndefined();
      expect(invalid.sort_dir).toBeUndefined();
    });
  });

  describe("serializeFiltersToSearchParams", () => {
    it("serializes filter state into URL parameters", () => {
      const filters: ComplaintFilterState = {
        category: ["Banking", "Lending"],
        timely: "Yes",
        date_from: "2021-01-01",
        page: 2,
      };

      const params = serializeFiltersToSearchParams(filters);
      expect(params.get("category")).toBe("Banking,Lending");
      expect(params.get("timely")).toBe("Yes");
      expect(params.get("date_from")).toBe("2021-01-01");
      expect(params.get("page")).toBe("2");
    });

    it("preserves unrelated query parameters when serializing", () => {
      const existing = new URLSearchParams("theme=dark&selected=3197305&category=OldCategory");
      const filters: ComplaintFilterState = {
        category: ["Banking"],
      };

      const serialized = serializeFiltersToSearchParams(filters, existing);

      // Unrelated parameters preserved
      expect(serialized.get("theme")).toBe("dark");
      expect(serialized.get("selected")).toBe("3197305");
      // Updated filter replaced
      expect(serialized.get("category")).toBe("Banking");
    });

    it("omits empty or undefined filter fields", () => {
      const filters: ComplaintFilterState = {
        category: [],
        q: "",
        date_from: undefined,
      };

      const params = serializeFiltersToSearchParams(filters);
      expect(params.toString()).toBe("");
    });
  });

  describe("hasActiveFilters", () => {
    it("returns false when no analytical filters are set", () => {
      expect(hasActiveFilters({})).toBe(false);
      // Pagination or sort alone does not count as active analytical filters
      expect(hasActiveFilters({ page: 2, page_size: 50, sort_by: "date_received" })).toBe(false);
    });

    it("returns true when any filter is active", () => {
      expect(hasActiveFilters({ category: ["Banking"] })).toBe(true);
      expect(hasActiveFilters({ timely: "Yes" })).toBe(true);
      expect(hasActiveFilters({ q: "mortgage" })).toBe(true);
      expect(hasActiveFilters({ date_from: "2020-01-01" })).toBe(true);
    });
  });
});
