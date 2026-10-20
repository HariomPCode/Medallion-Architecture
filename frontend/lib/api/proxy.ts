import { NextRequest, NextResponse } from "next/server";

/**
 * Server-only backend configuration.
 * Never import into client components.
 */
export function getBackendConfig() {
  const baseUrl = (process.env.BACKEND_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
  const internalApiKey = process.env.INTERNAL_API_KEY || "";
  return { baseUrl, internalApiKey };
}

/**
 * Allowed HTTP method and path patterns.
 * Derived from the frozen OpenAPI contract docs/openapi.json and §15.5.
 */
const ALLOWED_ENDPOINTS: Array<{ method: string; pattern: RegExp }> = [
  // Health
  { method: "GET", pattern: /^\/health\/(live|ready)$/ },
  // Meta
  { method: "GET", pattern: /^\/api\/v1\/meta\/(dataset|filters)$/ },
  // Dashboard
  { method: "GET", pattern: /^\/api\/v1\/dashboard\/summary$/ },
  // Analytics
  { method: "GET", pattern: /^\/api\/v1\/analytics\/(categories|by-category|trends|breakdown|kpis)$/ },
  // Complaints
  { method: "GET", pattern: /^\/api\/v1\/complaints$/ },
  { method: "GET", pattern: /^\/api\/v1\/complaints\/export$/ },
  { method: "GET", pattern: /^\/api\/v1\/complaints\/\d+$/ }, // Numeric complaint ID only
  // Quality
  { method: "GET", pattern: /^\/api\/v1\/quality\/(summary|anomalies)$/ },
  // Assistant
  { method: "GET", pattern: /^\/api\/v1\/assistant\/config$/ },
  { method: "POST", pattern: /^\/api\/v1\/assistant\/chat$/ },
];

/**
 * Normalize and validate an incoming relative path from the route parameters.
 * Strips 'backend/' or adds '/api' prefix where appropriate.
 * Rejects path traversal, malformed paths, schemes, and null bytes.
 */
export function normalizePath(pathSegments: string[] | string): string | null {
  const rawPath = Array.isArray(pathSegments) ? pathSegments.join("/") : pathSegments;

  // Reject path traversal attempts, backslashes, schemes, and null bytes
  if (
    !rawPath ||
    rawPath.includes("..") ||
    rawPath.includes("\\") ||
    rawPath.includes("://") ||
    rawPath.includes("\0") ||
    /%2e/i.test(rawPath) ||
    /%00/i.test(rawPath) ||
    rawPath.split("/").some((s) => s === "." || s === "..")
  ) {
    return null;
  }

  let cleaned = "/" + rawPath.replace(/^\/+/, "");

  // Handle optional namespaced 'backend/' prefix
  if (cleaned.startsWith("/backend/")) {
    cleaned = cleaned.replace(/^\/backend/, "");
  }

  // Handle /v1/... -> /api/v1/...
  if (cleaned.startsWith("/v1/")) {
    cleaned = "/api" + cleaned;
  }

  // Strip trailing slashes
  cleaned = cleaned.replace(/\/+$/, "") || "/";

  return cleaned;
}

/**
 * Check whether a normalized path and method combination is explicitly allowed.
 */
export function isPathAllowed(path: string, method: string): boolean {
  return ALLOWED_ENDPOINTS.some(
    (ep) => ep.method === method.toUpperCase() && ep.pattern.test(path)
  );
}

/**
 * Check whether a path matches any known endpoint pattern regardless of HTTP method.
 */
export function isPathKnown(path: string): boolean {
  return ALLOWED_ENDPOINTS.some((ep) => ep.pattern.test(path));
}

/**
 * Allow-list of headers permitted to be forwarded from client to upstream backend.
 * Everything else is stripped.
 */
const FORWARDED_UPSTREAM_HEADERS = new Set([
  "accept",
  "content-type",
  "user-agent",
  "x-request-id",
]);

/**
 * Hop-by-hop headers that must never be forwarded to or from the upstream service.
 */
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "cookie",
  "set-cookie",
  "authorization",
]);

/**
 * Filter headers for upstream requests using a strict allow-list.
 */
export function filterUpstreamHeaders(
  incomingHeaders: Headers,
  clientIp?: string | null,
  internalApiKey?: string
): Headers {
  const headers = new Headers();

  // Forward only explicitly approved client headers
  incomingHeaders.forEach((value, key) => {
    const lowerKey = key.toLowerCase();
    if (FORWARDED_UPSTREAM_HEADERS.has(lowerKey)) {
      headers.set(key, value);
    }
  });

  // Forward client IP
  if (clientIp) {
    headers.set("X-Forwarded-For", clientIp);
  }

  // Inject internal API key server-to-server (never from incoming client header)
  if (internalApiKey) {
    headers.set("X-Internal-Key", internalApiKey);
  }

  return headers;
}

/**
 * Filter headers for downstream client responses.
 */
export function filterDownstreamHeaders(
  upstreamHeaders: Headers,
  baseUrl?: string
): Headers {
  const headers = new Headers();

  upstreamHeaders.forEach((value, key) => {
    const lowerKey = key.toLowerCase();
    // Strip hop-by-hop, server information, and internal credential headers
    if (
      !HOP_BY_HOP_HEADERS.has(lowerKey) &&
      lowerKey !== "x-internal-key" &&
      lowerKey !== "server"
    ) {
      headers.set(key, value);
    }
  });

  // Rewrite Location header to prevent leaking internal backend base URL
  const location = headers.get("location");
  if (location && baseUrl && location.startsWith(baseUrl)) {
    headers.set("location", location.replace(baseUrl, "/api"));
  }

  // Enforce no-store on sensitive/dynamic data
  headers.set("Cache-Control", "no-store, no-cache, must-revalidate");

  return headers;
}

/**
 * Handle incoming Next.js BFF proxy requests.
 */
export async function handleProxyRequest(
  request: NextRequest,
  pathSegments: string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  const normalizedPath = normalizePath(pathSegments);

  // 1. Path validation & Traversal check
  if (!normalizedPath) {
    return NextResponse.json(
      {
        error: {
          code: "INVALID_PATH",
          message: "The requested path is malformed or contains invalid traversal tokens.",
        },
      },
      { status: 400 }
    );
  }

  // 2. Allow-list check
  if (!isPathAllowed(normalizedPath, method)) {
    if (isPathKnown(normalizedPath)) {
      return NextResponse.json(
        {
          error: {
            code: "METHOD_NOT_ALLOWED",
            message: `Method ${method} is not allowed for ${normalizedPath}.`,
          },
        },
        { status: 405 }
      );
    }

    return NextResponse.json(
      {
        error: {
          code: "NOT_FOUND",
          message: `The endpoint ${method} ${normalizedPath} is not available via this proxy.`,
        },
      },
      { status: 404 }
    );
  }

  // 3. Upstream URL assembly
  const { baseUrl, internalApiKey } = getBackendConfig();
  const searchParams = request.nextUrl.search; // includes query string (e.g. ?page=1)
  const upstreamUrl = `${baseUrl}${normalizedPath}${searchParams}`;

  // 4. Header filtering & credential injection
  const clientIp = request.headers.get("x-forwarded-for") || request.ip;
  const upstreamHeaders = filterUpstreamHeaders(
    request.headers,
    clientIp,
    internalApiKey
  );

  // 5. Timeout configuration (60s for assistant chat, 30s standard)
  const isAssistantChat = normalizedPath === "/api/v1/assistant/chat";
  const timeoutMs = isAssistantChat ? 60000 : 30000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const requestInit: RequestInit = {
      method,
      headers: upstreamHeaders,
      signal: controller.signal,
      redirect: "manual",
    };

    // Forward request body for POST
    if (method === "POST" && request.body) {
      // Consume body as text/json safely
      const bodyText = await request.text();
      requestInit.body = bodyText;
    }

    const upstreamResponse = await fetch(upstreamUrl, requestInit);
    clearTimeout(timeoutId);

    const downstreamHeaders = filterDownstreamHeaders(
      upstreamResponse.headers,
      baseUrl
    );

    // 6. Handle streaming responses (CSV export)
    if (normalizedPath === "/api/v1/complaints/export") {
      return new Response(upstreamResponse.body, {
        status: upstreamResponse.status,
        headers: downstreamHeaders,
      });
    }

    // 7. Standard JSON or text pass-through
    const responseBody = await upstreamResponse.arrayBuffer();
    return new Response(responseBody, {
      status: upstreamResponse.status,
      headers: downstreamHeaders,
    });
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    const isAbort =
      error instanceof Error && (error.name === "AbortError" || error.name === "TimeoutError");

    if (isAbort) {
      return NextResponse.json(
        {
          error: {
            code: "UPSTREAM_TIMEOUT",
            message: "The upstream analytics service timed out while processing your request.",
          },
        },
        { status: 504 }
      );
    }

    return NextResponse.json(
      {
        error: {
          code: "UPSTREAM_UNAVAILABLE",
          message: "The backend analytics service is currently unreachable.",
        },
      },
      { status: 502 }
    );
  }
}
