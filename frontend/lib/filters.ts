"use client";

import { useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

export interface ComplaintFilterState {
  category?: string[];
  sub_category?: string[];
  product?: string[];
  state?: string[];
  submitted_via?: string[];
  company_response?: string[];
  timely?: "Yes" | "No";
  date_from?: string;
  date_to?: string;
  issue?: string[];
  q?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 25;

/**
 * Known filter keys used by the analytics and complaints APIs.
 */
const KNOWN_FILTER_KEYS = new Set([
  "category",
  "sub_category",
  "product",
  "state",
  "submitted_via",
  "company_response",
  "timely",
  "date_from",
  "date_to",
  "issue",
  "q",
  "page",
  "page_size",
  "sort_by",
  "sort_dir",
]);

/**
 * Parse and validate URLSearchParams into a typed ComplaintFilterState.
 */
export function parseFiltersFromSearchParams(
  searchParams: URLSearchParams | { get: (k: string) => string | null; getAll: (k: string) => string[] }
): ComplaintFilterState {
  const result: ComplaintFilterState = {};

  const getArray = (key: string): string[] | undefined => {
    const values = searchParams.getAll(key);
    if (!values || values.length === 0) {
      const single = searchParams.get(key);
      if (!single) return undefined;
      return single.split(",").map((s) => s.trim()).filter(Boolean);
    }
    const flattened = values.flatMap((v) => v.split(",")).map((s) => s.trim()).filter(Boolean);
    return flattened.length > 0 ? flattened : undefined;
  };

  const category = getArray("category");
  if (category) result.category = category;

  const sub_category = getArray("sub_category");
  if (sub_category) result.sub_category = sub_category;

  const product = getArray("product");
  if (product) result.product = product;

  const state = getArray("state");
  if (state) result.state = state.map((s) => s.toUpperCase());

  const submitted_via = getArray("submitted_via");
  if (submitted_via) result.submitted_via = submitted_via;

  const company_response = getArray("company_response");
  if (company_response) result.company_response = company_response;

  const issue = getArray("issue");
  if (issue) result.issue = issue;

  const timely = searchParams.get("timely");
  if (timely === "Yes" || timely === "No") {
    result.timely = timely;
  }

  const date_from = searchParams.get("date_from");
  if (date_from && /^\d{4}-\d{2}-\d{2}$/.test(date_from)) {
    result.date_from = date_from;
  }

  const date_to = searchParams.get("date_to");
  if (date_to && /^\d{4}-\d{2}-\d{2}$/.test(date_to)) {
    result.date_to = date_to;
  }

  const q = searchParams.get("q");
  if (q && q.trim()) {
    result.q = q.trim();
  }

  const pageStr = searchParams.get("page");
  if (pageStr) {
    const p = parseInt(pageStr, 10);
    if (!isNaN(p) && p >= 1) result.page = p;
  }

  const pageSizeStr = searchParams.get("page_size");
  if (pageSizeStr) {
    const ps = parseInt(pageSizeStr, 10);
    if (!isNaN(ps) && ps >= 1 && ps <= 100) result.page_size = ps;
  }

  const sort_by = searchParams.get("sort_by");
  if (sort_by) result.sort_by = sort_by;

  const sort_dir = searchParams.get("sort_dir");
  if (sort_dir === "asc" || sort_dir === "desc") {
    result.sort_dir = sort_dir;
  }

  return result;
}

/**
 * Serialize a ComplaintFilterState into URLSearchParams while preserving unrelated query params.
 */
export function serializeFiltersToSearchParams(
  filters: Partial<ComplaintFilterState>,
  existingParams?: URLSearchParams | { forEach: (cb: (value: string, key: string) => void) => void }
): URLSearchParams {
  const params = new URLSearchParams();

  // Preserve unrelated query parameters (e.g. theme, tab, debug, selected)
  if (existingParams) {
    existingParams.forEach((val, key) => {
      if (!KNOWN_FILTER_KEYS.has(key)) {
        params.set(key, val);
      }
    });
  }

  // Serialize filter state
  Object.entries(filters).forEach(([key, val]) => {
    if (val === undefined || val === null || val === "") return;

    if (Array.isArray(val)) {
      if (val.length > 0) {
        params.set(key, val.join(","));
      }
    } else {
      params.set(key, String(val));
    }
  });

  return params;
}

/**
 * Determine whether any analytical filters are currently active (excluding pagination and sort).
 */
export function hasActiveFilters(filters: ComplaintFilterState): boolean {
  return Boolean(
    (filters.category && filters.category.length > 0) ||
      (filters.sub_category && filters.sub_category.length > 0) ||
      (filters.product && filters.product.length > 0) ||
      (filters.state && filters.state.length > 0) ||
      (filters.submitted_via && filters.submitted_via.length > 0) ||
      (filters.company_response && filters.company_response.length > 0) ||
      filters.timely ||
      filters.date_from ||
      filters.date_to ||
      (filters.issue && filters.issue.length > 0) ||
      filters.q
  );
}

/**
 * React hook to synchronize filter state with URL search parameters in Next.js App Router.
 */
export function useFilters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const filters = useMemo(() => {
    return parseFiltersFromSearchParams(searchParams);
  }, [searchParams]);

  const updateFilters = useCallback(
    (updater: Partial<ComplaintFilterState> | ((prev: ComplaintFilterState) => Partial<ComplaintFilterState>)) => {
      const nextFilters = typeof updater === "function" ? updater(filters) : { ...filters, ...updater };
      const newParams = serializeFiltersToSearchParams(nextFilters, searchParams);
      const query = newParams.toString();
      const nextUrl = query ? `${pathname}?${query}` : pathname;
      router.push(nextUrl, { scroll: false });
    },
    [filters, pathname, router, searchParams]
  );

  const clearFilters = useCallback(() => {
    const params = new URLSearchParams();
    // Preserve non-filter keys
    searchParams.forEach((val, key) => {
      if (!KNOWN_FILTER_KEYS.has(key)) {
        params.set(key, val);
      }
    });
    const query = params.toString();
    const nextUrl = query ? `${pathname}?${query}` : pathname;
    router.push(nextUrl, { scroll: false });
  }, [pathname, router, searchParams]);

  return {
    filters,
    updateFilters,
    clearFilters,
    hasActiveFilters: hasActiveFilters(filters),
  };
}
