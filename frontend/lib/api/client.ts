import type { paths } from "./types";

/**
 * Standard typed ApiError wrapping backend and proxy error envelopes.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(
    message: string,
    code: string,
    status: number,
    requestId?: string,
    details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

/**
 * Build a query string from a parameters record, filtering out null/undefined values.
 */
export function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return "";
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, val]) => {
    if (val === undefined || val === null || val === "") return;

    if (Array.isArray(val)) {
      val.forEach((item) => {
        if (item !== undefined && item !== null && item !== "") {
          searchParams.append(key, String(item));
        }
      });
    } else {
      searchParams.set(key, String(val));
    }
  });

  const str = searchParams.toString();
  return str ? `?${str}` : "";
}

/**
 * Base HTTP GET helper targeting same-origin Next.js BFF proxy.
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, unknown>,
  options?: RequestOptions
): Promise<T> {
  const url = `${path}${buildQueryString(params)}`;
  const response = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...options?.headers,
    },
    signal: options?.signal,
  });

  if (!response.ok) {
    let errorCode = "HTTP_ERROR";
    let errorMessage = `Request failed with status ${response.status}`;
    let requestId: string | undefined;
    let details: unknown;

    try {
      const errorJson = await response.json();
      if (errorJson && typeof errorJson === "object" && "error" in errorJson) {
        const errObj = errorJson.error;
        errorCode = errObj.code || errorCode;
        errorMessage = errObj.message || errorMessage;
        requestId = errObj.request_id;
        details = errObj.details;
      }
    } catch {
      // Fallback if response is not JSON
    }

    throw new ApiError(errorMessage, errorCode, response.status, requestId, details);
  }

  return response.json() as Promise<T>;
}

/**
 * Base HTTP POST helper targeting same-origin Next.js BFF proxy.
 */
export async function apiPost<T, B>(
  path: string,
  body: B,
  options?: RequestOptions
): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options?.headers,
    },
    body: JSON.stringify(body),
    signal: options?.signal,
  });

  if (!response.ok) {
    let errorCode = "HTTP_ERROR";
    let errorMessage = `Request failed with status ${response.status}`;
    let requestId: string | undefined;
    let details: unknown;

    try {
      const errorJson = await response.json();
      if (errorJson && typeof errorJson === "object" && "error" in errorJson) {
        const errObj = errorJson.error;
        errorCode = errObj.code || errorCode;
        errorMessage = errObj.message || errorMessage;
        requestId = errObj.request_id;
        details = errObj.details;
      }
    } catch {
      // Fallback if response is not JSON
    }

    throw new ApiError(errorMessage, errorCode, response.status, requestId, details);
  }

  return response.json() as Promise<T>;
}

// -----------------------------------------------------------------------------
// Typed Domain Operations
// -----------------------------------------------------------------------------

export type DatasetMeta =
  paths["/api/v1/meta/dataset"]["get"]["responses"]["200"]["content"]["application/json"];

export type FilterOptions =
  paths["/api/v1/meta/filters"]["get"]["responses"]["200"]["content"]["application/json"];

export type DashboardSummary =
  paths["/api/v1/dashboard/summary"]["get"]["responses"]["200"]["content"]["application/json"];

export type CategoryAnalytics =
  paths["/api/v1/analytics/by-category"]["get"]["responses"]["200"]["content"]["application/json"];

export type TrendsAnalytics =
  paths["/api/v1/analytics/trends"]["get"]["responses"]["200"]["content"]["application/json"];

export type BreakdownAnalytics =
  paths["/api/v1/analytics/breakdown"]["get"]["responses"]["200"]["content"]["application/json"];

export type ComplaintsList =
  paths["/api/v1/complaints"]["get"]["responses"]["200"]["content"]["application/json"];

export type ComplaintDetail =
  paths["/api/v1/complaints/{complaint_id}"]["get"]["responses"]["200"]["content"]["application/json"];

export type QualitySummary =
  paths["/api/v1/quality/summary"]["get"]["responses"]["200"]["content"]["application/json"];

export type QualityAnomalies =
  paths["/api/v1/quality/anomalies"]["get"]["responses"]["200"]["content"]["application/json"];

export type AssistantConfig =
  paths["/api/v1/assistant/config"]["get"]["responses"]["200"]["content"]["application/json"];

export type AssistantChatRequest =
  paths["/api/v1/assistant/chat"]["post"]["requestBody"]["content"]["application/json"];

export type AssistantChatResponse =
  paths["/api/v1/assistant/chat"]["post"]["responses"]["200"]["content"]["application/json"];

export const api = {
  getDatasetMeta: (options?: RequestOptions) =>
    apiGet<DatasetMeta>("/api/v1/meta/dataset", undefined, options),

  getFilterOptions: (options?: RequestOptions) =>
    apiGet<FilterOptions>("/api/v1/meta/filters", undefined, options),

  getDashboardSummary: (params?: Record<string, unknown>, options?: RequestOptions) =>
    apiGet<DashboardSummary>("/api/v1/dashboard/summary", params, options),

  getCategoryAnalytics: (params?: Record<string, unknown>, options?: RequestOptions) =>
    apiGet<CategoryAnalytics>("/api/v1/analytics/by-category", params, options),

  getTrends: (params?: Record<string, unknown>, options?: RequestOptions) =>
    apiGet<TrendsAnalytics>("/api/v1/analytics/trends", params, options),

  getBreakdown: (params?: Record<string, unknown>, options?: RequestOptions) =>
    apiGet<BreakdownAnalytics>("/api/v1/analytics/breakdown", params, options),

  getComplaints: (params?: Record<string, unknown>, options?: RequestOptions) =>
    apiGet<ComplaintsList>("/api/v1/complaints", params, options),

  getComplaintById: (id: string | number, options?: RequestOptions) =>
    apiGet<ComplaintDetail>(`/api/v1/complaints/${id}`, undefined, options),

  getQualitySummary: (options?: RequestOptions) =>
    apiGet<QualitySummary>("/api/v1/quality/summary", undefined, options),

  getQualityAnomalies: (params?: Record<string, unknown>, options?: RequestOptions) =>
    apiGet<QualityAnomalies>("/api/v1/quality/anomalies", params, options),

  getAssistantConfig: (options?: RequestOptions) =>
    apiGet<AssistantConfig>("/api/v1/assistant/config", undefined, options),

  sendAssistantChat: (body: AssistantChatRequest, options?: RequestOptions) =>
    apiPost<AssistantChatResponse, AssistantChatRequest>("/api/v1/assistant/chat", body, options),

  getExportUrl: (params?: Record<string, unknown>) =>
    `/api/v1/complaints/export${buildQueryString(params)}`,
};
