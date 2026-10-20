/**
 * Formatting utilities for the Finance Complaints Medallion platform.
 * Follows CFPB metric definitions, tabular number alignment, and deterministic output.
 */

const DEFAULT_FALLBACK = "—";

/**
 * Safely parse a numeric value. Returns null if invalid or missing.
 */
function toValidNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const num = typeof value === "number" ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

/**
 * Format an integer with standard digit grouping (e.g. 62,516).
 */
export function formatNumber(
  value: unknown,
  fallback = DEFAULT_FALLBACK
): string {
  const num = toValidNumber(value);
  if (num === null) return fallback;
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(num);
}

/**
 * Format a decimal value with fixed precision.
 */
export function formatDecimal(
  value: unknown,
  digits = 2,
  fallback = DEFAULT_FALLBACK
): string {
  const num = toValidNumber(value);
  if (num === null) return fallback;
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(num);
}

/**
 * Format a compact metric count (e.g. 62.5K).
 */
export function formatCompact(
  value: unknown,
  fallback = DEFAULT_FALLBACK
): string {
  const num = toValidNumber(value);
  if (num === null) return fallback;
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: 1,
  }).format(num);
}

/**
 * Format a rate or share as a percentage.
 * Handles both 0..1 scale (e.g. 0.9606 -> "96.1%") and 0..100 scale (e.g. 96.06 -> "96.1%").
 */
export function formatPercent(
  value: unknown,
  digits = 1,
  fallback = DEFAULT_FALLBACK
): string {
  const num = toValidNumber(value);
  if (num === null) return fallback;

  // If already expressed as 0-100 percentage (e.g. 96.06 or > 1.0)
  const normalized = Math.abs(num) > 1.0 ? num : num * 100;

  return `${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(normalized)}%`;
}

/**
 * Format a rate or growth percentage with an explicit positive or negative sign (e.g. +16.2% or -10.1%).
 */
export function formatSignedPercent(
  value: unknown,
  digits = 1,
  fallback = DEFAULT_FALLBACK
): string {
  const num = toValidNumber(value);
  if (num === null) return fallback;
  const formatted = formatPercent(Math.abs(num), digits, fallback);
  return num > 0 ? `+${formatted}` : num < 0 ? `-${formatted}` : formatted;
}

/**
 * Format a currency value (e.g. $1,250).
 */
export function formatCurrency(
  value: unknown,
  currency = "USD",
  fallback = DEFAULT_FALLBACK
): string {
  const num = toValidNumber(value);
  if (num === null) return fallback;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

/**
 * Safely parse date input into UTC year, month, day to avoid timezone skew.
 */
function parseDateParts(
  dateInput: unknown
): { year: number; month: number; day: number } | null {
  if (!dateInput) return null;

  if (typeof dateInput === "string") {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateInput.trim());
    if (match) {
      return {
        year: parseInt(match[1], 10),
        month: parseInt(match[2], 10) - 1, // 0-indexed month
        day: parseInt(match[3], 10),
      };
    }
  }

  const date = dateInput instanceof Date ? dateInput : new Date(String(dateInput));
  if (isNaN(date.getTime())) return null;

  return {
    year: date.getUTCFullYear(),
    month: date.getUTCMonth(),
    day: date.getUTCDate(),
  };
}

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

/**
 * Format an ISO date string to standard editorial format (e.g. "28 Aug 2023").
 */
export function formatDate(
  dateInput: unknown,
  fallback = DEFAULT_FALLBACK
): string {
  const parts = parseDateParts(dateInput);
  if (!parts) return fallback;
  return `${parts.day} ${MONTH_NAMES[parts.month]} ${parts.year}`;
}

/**
 * Format a date range (e.g. "1 May 2017 – 28 Aug 2023").
 */
export function formatDateRange(
  startDateInput: unknown,
  endDateInput: unknown,
  fallback = DEFAULT_FALLBACK
): string {
  const start = parseDateParts(startDateInput);
  const end = parseDateParts(endDateInput);

  if (!start && !end) return fallback;
  if (!start && end) return `Through ${end.day} ${MONTH_NAMES[end.month]} ${end.year}`;
  if (start && !end) return `From ${start.day} ${MONTH_NAMES[start.month]} ${start.year}`;

  if (start && end) {
    if (start.year === end.year && start.month === end.month) {
      return `${start.day}–${end.day} ${MONTH_NAMES[start.month]} ${start.year}`;
    }
    if (start.year === end.year) {
      return `${start.day} ${MONTH_NAMES[start.month]} – ${end.day} ${MONTH_NAMES[end.month]} ${start.year}`;
    }
    return `${start.day} ${MONTH_NAMES[start.month]} ${start.year} – ${end.day} ${MONTH_NAMES[end.month]} ${end.year}`;
  }

  return fallback;
}

/**
 * Format a nullable or optional text value with an explicit fallback (e.g. "Not provided" or "—").
 * Ensures missing fields never render raw null, undefined, or empty strings.
 */
export function formatNullable(
  value: unknown,
  fallback = "Not provided"
): string {
  if (value === null || value === undefined) return fallback;
  const str = String(value).trim();
  return str === "" ? fallback : str;
}

