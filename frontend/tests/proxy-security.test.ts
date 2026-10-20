import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";
import {
  handleProxyRequest,
  normalizePath,
  isPathAllowed,
  filterUpstreamHeaders,
  filterDownstreamHeaders,
  getBackendConfig,
} from "@/lib/api/proxy";

describe("BFF Proxy Security & Controls", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = {
      ...originalEnv,
      BACKEND_BASE_URL: "http://localhost:8000",
      INTERNAL_API_KEY: "test-super-secret-internal-key",
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
  });

  describe("Path Normalization & Traversal Defense", () => {
    it("normalizes valid path segments to standard /api/v1/ paths", () => {
      expect(normalizePath(["api", "v1", "meta", "dataset"])).toBe("/api/v1/meta/dataset");
      expect(normalizePath(["v1", "meta", "dataset"])).toBe("/api/v1/meta/dataset");
      expect(normalizePath(["backend", "api", "v1", "meta", "dataset"])).toBe("/api/v1/meta/dataset");
    });

    it("rejects directory traversal attempts with null", () => {
      expect(normalizePath(["..", "admin"])).toBeNull();
      expect(normalizePath(["api", "v1", "..", "..", "etc", "passwd"])).toBeNull();
      expect(normalizePath(["api/v1/..%2f.."])).toBeNull();
      expect(normalizePath(["api\\v1\\admin"])).toBeNull();
      expect(normalizePath(["http://evil.com/api"])).toBeNull();
      expect(normalizePath(["https://evil.com/api"])).toBeNull();
      expect(normalizePath(["api", "\0", "v1"])).toBeNull();
      expect(normalizePath(["api", "%00", "v1"])).toBeNull();
      expect(normalizePath(["api", ".", "v1"])).toBeNull();
    });

    it("normalizes paths with trailing slashes", () => {
      expect(normalizePath(["api", "v1", "meta", "dataset", ""])).toBe("/api/v1/meta/dataset");
      expect(normalizePath(["api/v1/meta/dataset/"])).toBe("/api/v1/meta/dataset");
    });
  });

  describe("Endpoint & Method Allow-Listing", () => {
    it("allows approved GET endpoints from the frozen contract", () => {
      expect(isPathAllowed("/api/v1/meta/dataset", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/meta/filters", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/dashboard/summary", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/analytics/categories", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/analytics/trends", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/complaints", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/complaints/export", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/complaints/3197305", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/quality/summary", "GET")).toBe(true);
      expect(isPathAllowed("/api/v1/assistant/config", "GET")).toBe(true);
      expect(isPathAllowed("/health/live", "GET")).toBe(true);
      expect(isPathAllowed("/health/ready", "GET")).toBe(true);
    });

    it("allows approved POST endpoints", () => {
      expect(isPathAllowed("/api/v1/assistant/chat", "POST")).toBe(true);
    });

    it("rejects unapproved paths with false", () => {
      expect(isPathAllowed("/api/v1/users", "GET")).toBe(false);
      expect(isPathAllowed("/admin", "GET")).toBe(false);
      expect(isPathAllowed("/api/v1/database/drop", "POST")).toBe(false);
      expect(isPathAllowed("/api/v1/meta/dataset/delete", "GET")).toBe(false);
      expect(isPathAllowed("/api/v1/complaints/non-numeric-id", "GET")).toBe(false);
    });

    it("rejects disallowed HTTP methods on GET endpoints", () => {
      expect(isPathAllowed("/api/v1/dashboard/summary", "POST")).toBe(false);
      expect(isPathAllowed("/api/v1/meta/dataset", "DELETE")).toBe(false);
      expect(isPathAllowed("/api/v1/complaints", "PUT")).toBe(false);
      expect(isPathAllowed("/api/v1/complaints", "PATCH")).toBe(false);
    });
  });

  describe("Header Filtering & Credential Isolation", () => {
    it("injects X-Internal-Key on the server side and forwards client IP", () => {
      const incoming = new Headers({
        "Accept": "application/json",
        "User-Agent": "TestBrowser/1.0",
      });

      const filtered = filterUpstreamHeaders(
        incoming,
        "198.51.100.42",
        "secret-key-123"
      );

      expect(filtered.get("X-Internal-Key")).toBe("secret-key-123");
      expect(filtered.get("X-Forwarded-For")).toBe("198.51.100.42");
      expect(filtered.get("Accept")).toBe("application/json");
    });

    it("strips hop-by-hop headers, cookies, client-supplied internal keys, and unapproved headers", () => {
      const incoming = new Headers({
        "Cookie": "session_id=12345",
        "Authorization": "Bearer client-token",
        "X-Internal-Key": "client-injected-attacker-key",
        "X-Attacker-Custom": "malicious-header",
        "Referer": "https://evil.com",
        "Connection": "keep-alive",
        "Keep-Alive": "timeout=5",
        "Transfer-Encoding": "chunked",
        "Upgrade": "websocket",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-ID": "req-trace-123",
      });

      // When no internal key is configured on server
      const filteredWithoutKey = filterUpstreamHeaders(incoming);

      expect(filteredWithoutKey.has("Cookie")).toBe(false);
      expect(filteredWithoutKey.has("Authorization")).toBe(false);
      expect(filteredWithoutKey.has("X-Internal-Key")).toBe(false);
      expect(filteredWithoutKey.has("X-Attacker-Custom")).toBe(false);
      expect(filteredWithoutKey.has("Referer")).toBe(false);
      expect(filteredWithoutKey.has("Connection")).toBe(false);
      expect(filteredWithoutKey.has("Keep-Alive")).toBe(false);
      expect(filteredWithoutKey.has("Transfer-Encoding")).toBe(false);
      expect(filteredWithoutKey.has("Upgrade")).toBe(false);

      // Only approved headers are forwarded
      expect(filteredWithoutKey.get("Accept")).toBe("application/json");
      expect(filteredWithoutKey.get("Content-Type")).toBe("application/json");
      expect(filteredWithoutKey.get("X-Request-ID")).toBe("req-trace-123");
    });

    it("rewrites Location header in downstream responses to avoid exposing backend baseUrl", () => {
      const upstreamHeaders = new Headers({
        "Content-Type": "application/json",
        "Location": "http://localhost:8000/api/v1/complaints/123",
      });

      const downstream = filterDownstreamHeaders(upstreamHeaders, "http://localhost:8000");

      expect(downstream.get("Location")).toBe("/api/api/v1/complaints/123");
    });

    it("never returns X-Internal-Key or Server header in downstream response headers and sets no-store", () => {
      const upstreamHeaders = new Headers({
        "Content-Type": "application/json",
        "X-Internal-Key": "leaked-secret",
        "Server": "uvicorn",
        "Set-Cookie": "secret_cookie=bad",
      });

      const downstream = filterDownstreamHeaders(upstreamHeaders);

      expect(downstream.has("X-Internal-Key")).toBe(false);
      expect(downstream.has("Server")).toBe(false);
      expect(downstream.has("Set-Cookie")).toBe(false);
      expect(downstream.get("Cache-Control")).toBe(
        "no-store, no-cache, must-revalidate"
      );
    });
  });

  describe("Upstream Request Execution & Error Envelopes", () => {
    it("returns 400 for path traversal requests", async () => {
      const req = new NextRequest("http://localhost:3000/api/../admin");
      const res = await handleProxyRequest(req, ["..", "admin"]);

      expect(res.status).toBe(400);
      const data = await res.json();
      expect(data.error.code).toBe("INVALID_PATH");
    });

    it("returns 404 for unapproved endpoints without contacting upstream", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      const req = new NextRequest("http://localhost:3000/api/v1/forbidden/path");
      const res = await handleProxyRequest(req, ["v1", "forbidden", "path"]);

      expect(res.status).toBe(404);
      const data = await res.json();
      expect(data.error.code).toBe("NOT_FOUND");
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("returns 405 for disallowed HTTP methods on known endpoints", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      const req = new NextRequest("http://localhost:3000/api/v1/meta/dataset", {
        method: "POST",
      });
      const res = await handleProxyRequest(req, ["v1", "meta", "dataset"]);

      expect(res.status).toBe(405);
      const data = await res.json();
      expect(data.error.code).toBe("METHOD_NOT_ALLOWED");
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("never allows caller to override upstream base URL", () => {
      const config = getBackendConfig();
      expect(config.baseUrl).toBe("http://localhost:8000");
      expect(config.internalApiKey).toBe("test-super-secret-internal-key");
    });

    it("returns controlled 504 on upstream timeout without exposing internals", async () => {
      vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => {
        const err = new Error("The operation was aborted");
        err.name = "AbortError";
        return Promise.reject(err);
      });

      const req = new NextRequest("http://localhost:3000/api/v1/meta/dataset");
      const res = await handleProxyRequest(req, ["v1", "meta", "dataset"]);

      expect(res.status).toBe(504);
      const data = await res.json();
      expect(data.error.code).toBe("UPSTREAM_TIMEOUT");
      expect(data.error.message).toContain("timed out");
      // Must not leak URL or key
      expect(JSON.stringify(data)).not.toContain("localhost:8000");
      expect(JSON.stringify(data)).not.toContain("test-super-secret-internal-key");
    });

    it("returns controlled 502 on upstream network failure without exposing internals", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
        new Error("ECONNREFUSED connect 127.0.0.1:8000")
      );

      const req = new NextRequest("http://localhost:3000/api/v1/meta/dataset");
      const res = await handleProxyRequest(req, ["v1", "meta", "dataset"]);

      expect(res.status).toBe(502);
      const data = await res.json();
      expect(data.error.code).toBe("UPSTREAM_UNAVAILABLE");
      // Must not leak internal details
      expect(JSON.stringify(data)).not.toContain("ECONNREFUSED");
      expect(JSON.stringify(data)).not.toContain("test-super-secret-internal-key");
    });
  });
});
