import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  apiGet,
  apiPost,
  api,
  ApiError,
  buildQueryString,
} from "@/lib/api/client";

describe("Typed API Client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("buildQueryString", () => {
    it("serializes parameters and filters out empty values", () => {
      const qs = buildQueryString({
        category: "Banking",
        page: 2,
        empty: "",
        nil: null,
        undef: undefined,
      });

      expect(qs).toBe("?category=Banking&page=2");
    });

    it("handles array parameters correctly", () => {
      const qs = buildQueryString({
        category: ["Banking", "Payments"],
        state: ["CA", "NY"],
      });

      expect(qs).toContain("category=Banking");
      expect(qs).toContain("category=Payments");
      expect(qs).toContain("state=CA");
      expect(qs).toContain("state=NY");
    });

    it("returns empty string when no parameters given", () => {
      expect(buildQueryString()).toBe("");
      expect(buildQueryString({})).toBe("");
    });
  });

  describe("apiGet & Error Envelope Parsing", () => {
    it("returns parsed JSON on 200 response", async () => {
      const mockData = { status: "ready", total: 62516 };
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        new Response(JSON.stringify(mockData), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

      const data = await apiGet<typeof mockData>("/api/v1/meta/dataset");
      expect(data).toEqual(mockData);
    });

    it("parses structured error envelope into ApiError instance", async () => {
      const errorPayload = {
        error: {
          code: "FILTER_VALIDATION_ERROR",
          message: "Invalid product category requested",
          request_id: "req-12345",
          details: { field: "category" },
        },
      };

      vi.spyOn(globalThis, "fetch").mockImplementation(() =>
        Promise.resolve(
          new Response(JSON.stringify(errorPayload), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          })
        )
      );

      await expect(apiGet("/api/v1/dashboard/summary")).rejects.toThrow(ApiError);

      try {
        await apiGet("/api/v1/dashboard/summary");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.code).toBe("FILTER_VALIDATION_ERROR");
        expect(apiErr.status).toBe(400);
        expect(apiErr.requestId).toBe("req-12345");
        expect(apiErr.details).toEqual({ field: "category" });
        expect(apiErr.message).toBe("Invalid product category requested");
      }
    });

    it("handles non-JSON error responses gracefully", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        new Response("Gateway Timeout", {
          status: 504,
          statusText: "Gateway Timeout",
        })
      );

      try {
        await apiGet("/api/v1/analytics/trends");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(504);
        expect(apiErr.code).toBe("HTTP_ERROR");
      }
    });

    it("supports cancellation via AbortSignal", async () => {
      const controller = new AbortController();
      controller.abort();

      await expect(
        apiGet("/api/v1/meta/dataset", undefined, { signal: controller.signal })
      ).rejects.toThrow();
    });
  });

  describe("apiPost", () => {
    it("posts JSON payload with appropriate headers", async () => {
      const responseData = { response: "Analysis verified." };
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        new Response(JSON.stringify(responseData), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

      const result = await apiPost(
        "/api/v1/assistant/chat",
        { prompt: "Summary of complaints" }
      );

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/v1/assistant/chat",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            Accept: "application/json",
          }),
          body: JSON.stringify({ prompt: "Summary of complaints" }),
        })
      );
      expect(result).toEqual(responseData);
    });
  });

  describe("Domain Operations Helper", () => {
    it("constructs correct export URL with query parameters", () => {
      const url = api.getExportUrl({ category: "Banking", state: "CA" });
      expect(url).toBe("/api/v1/complaints/export?category=Banking&state=CA");
    });
  });
});
