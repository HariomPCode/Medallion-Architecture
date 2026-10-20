/**
 * Color and visual variant tokens for the Finance Complaints Medallion platform.
 * Enforces the approved Financial Editorial palette and accessible status mappings.
 */

export type CategoryKey =
  | "Banking"
  | "Payments"
  | "Credit Reporting"
  | "Lending"
  | "Collections";

export type StatusVariant = "positive" | "warning" | "negative" | "neutral";

export interface StatusMeta {
  variant: StatusVariant;
  label: string;
  description: string;
}

/**
 * Authoritative category palette defined in Section 15.2 of the development plan.
 * Color-blind-checked set. Every category is also identifiable by text label.
 */
export const CATEGORY_COLORS: Record<CategoryKey, { light: string; dark: string }> = {
  Banking: {
    light: "#2F5D8A",
    dark: "#60A5FA",
  },
  Payments: {
    light: "#0F766E",
    dark: "#2DD4BF",
  },
  "Credit Reporting": {
    light: "#C27C2C",
    dark: "#FBBF24",
  },
  Lending: {
    light: "#7A5C99",
    dark: "#C084FC",
  },
  Collections: {
    light: "#A8483E",
    dark: "#F87171",
  },
};

/**
 * Retrieve the category color code for a given category name and theme.
 */
export function getCategoryColor(
  category: string,
  theme: "light" | "dark" = "light"
): string {
  const normalized = Object.keys(CATEGORY_COLORS).find(
    (k) => k.toLowerCase() === category.trim().toLowerCase()
  ) as CategoryKey | undefined;

  if (normalized && CATEGORY_COLORS[normalized]) {
    return CATEGORY_COLORS[normalized][theme];
  }

  // Neutral fallback for unmatched categories
  return theme === "dark" ? "#94A3B8" : "#475467";
}

/**
 * Map an API, dataset, or data-quality status string to a semantic variant.
 */
export function getStatusVariant(status: string | null | undefined): StatusVariant {
  if (!status) return "neutral";
  const normalized = status.trim().toLowerCase().replace(/[\s-_]+/g, "");

  switch (normalized) {
    case "ready":
    case "live":
    case "good":
    case "healthy":
    case "normal":
    case "timely":
    case "yes":
    case "pass":
      return "positive";

    case "warning":
    case "degraded":
    case "stale":
    case "fixture":
    case "localsnapshot":
    case "pending":
    case "inprogress":
      return "warning";

    case "down":
    case "error":
    case "critical":
    case "failing":
    case "fail":
    case "anomaly":
    case "no":
    case "untimely":
      return "negative";

    default:
      return "neutral";
  }
}

/**
 * Provide human-readable metadata, variant, and description for a status.
 */
export function getStatusMeta(status: string | null | undefined): StatusMeta {
  const variant = getStatusVariant(status);
  const raw = (status ?? "Unknown").trim();

  switch (variant) {
    case "positive":
      return {
        variant,
        label: raw === "ready" ? "Live" : raw,
        description: "System operational and metrics healthy",
      };
    case "warning":
      return {
        variant,
        label: raw === "local_snapshot" ? "Local Snapshot" : raw,
        description: "Operating with advisory conditions or non-production data",
      };
    case "negative":
      return {
        variant,
        label: raw,
        description: "Requires operational attention or metric outside tolerance",
      };
    default:
      return {
        variant,
        label: raw === "not_published" ? "Not Published" : raw,
        description: "Informational or unclassified status",
      };
  }
}
