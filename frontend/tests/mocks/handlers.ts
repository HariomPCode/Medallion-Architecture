import { http, HttpResponse } from "msw";

export const MOCK_DATASET_META = {
  data_origin: "local_snapshot",
  data_status: "local_snapshot",
  total_silver_records: 62516,
  row_counts: { Silver: 62516, Gold_Category: 9, Gold_Trends: 35 },
  coverage: { start: "2017-05-01", end: "2023-08-28" },
  pipeline_refreshed_at: "2026-10-19T12:00:00Z",
  quality_analysis_at: "2026-10-19T12:00:00Z",
  skew_warning: true,
  schema_version: "1.0.0",
  warnings: [],
};

export const MOCK_FILTERS_META = {
  categories: [
    { name: "Banking", sub_categories: ["Deposit Accounts"] },
    { name: "Payments", sub_categories: ["Card Products", "Money Movement"] },
    { name: "Credit Reporting", sub_categories: ["Consumer Reporting"] },
    {
      name: "Lending",
      sub_categories: [
        "Real Estate Lending",
        "Secured Lending",
        "Short-Term Lending",
        "Education Lending",
      ],
    },
    { name: "Collections", sub_categories: ["Third-Party Collections"] },
  ],
  submitted_via: ["Web", "Referral", "Phone", "Postal mail", "Fax", "Email"],
  state: ["CA", "FL", "TX", "NY", "GA"],
  company_response: [
    "Closed with explanation",
    "Closed with non-monetary relief",
    "In progress",
    "Closed with monetary relief",
    "Closed",
  ],
  timely: ["Yes", "No"],
  issues: ["Managing an account", "Problem with a credit reporting company"],
  coverage: { start: "2017-05-01", end: "2023-08-28" },
};

export const MOCK_DASHBOARD_SUMMARY = {
  filters_applied: {},
  total_complaints: 62516,
  timely: {
    yes: 58619,
    no: 2403,
    unknown: 1494,
    rate: 96.06,
    rate_denominator: 61022,
    rate_all_cases: 93.77,
  },
  in_progress_count: 1494,
  category_count: 5,
  sub_category_count: 9,
  coverage: { start: "2017-05-01", end: "2023-08-28" },
  pipeline_refreshed_at: "2026-10-19T12:00:00Z",
  data_origin: "local_snapshot",
};

export const MOCK_CATEGORIES = [
  {
    category: "Banking",
    sub_category: null,
    total: 24814,
    share_pct: 39.69,
    timely_yes: 23230,
    timely_no: 868,
    timely_unknown: 716,
    timely_rate: 96.4,
    timely_rate_all_cases: 93.6,
  },
  {
    category: "Payments",
    sub_category: null,
    total: 19650,
    share_pct: 31.43,
    timely_yes: 18338,
    timely_no: 840,
    timely_unknown: 472,
    timely_rate: 95.6,
    timely_rate_all_cases: 93.3,
  },
  {
    category: "Credit Reporting",
    sub_category: null,
    total: 7710,
    share_pct: 12.33,
    timely_yes: 7049,
    timely_no: 475,
    timely_unknown: 186,
    timely_rate: 93.7,
    timely_rate_all_cases: 91.4,
  },
  {
    category: "Lending",
    sub_category: null,
    total: 7606,
    share_pct: 12.17,
    timely_yes: 7487,
    timely_no: 58,
    timely_unknown: 61,
    timely_rate: 99.2,
    timely_rate_all_cases: 98.4,
  },
  {
    category: "Collections",
    sub_category: null,
    total: 2736,
    share_pct: 4.38,
    timely_yes: 2515,
    timely_no: 172,
    timely_unknown: 49,
    timely_rate: 93.6,
    timely_rate_all_cases: 91.9,
  },
];

export const MOCK_SUB_CATEGORIES = [
  {
    category: "Banking",
    sub_category: "Deposit Accounts",
    total: 24814,
    share_pct: 39.69,
    timely_yes: 23230,
    timely_no: 868,
    timely_unknown: 716,
    timely_rate: 96.4,
    timely_rate_all_cases: 93.6,
  },
  {
    category: "Payments",
    sub_category: "Card Products",
    total: 16197,
    share_pct: 25.91,
    timely_yes: 15096,
    timely_no: 700,
    timely_unknown: 401,
    timely_rate: 95.6,
    timely_rate_all_cases: 93.2,
  },
  {
    category: "Credit Reporting",
    sub_category: "Consumer Reporting",
    total: 7710,
    share_pct: 12.33,
    timely_yes: 7049,
    timely_no: 475,
    timely_unknown: 186,
    timely_rate: 93.7,
    timely_rate_all_cases: 91.4,
  },
  {
    category: "Lending",
    sub_category: "Real Estate Lending",
    total: 6601,
    share_pct: 10.56,
    timely_yes: 6540,
    timely_no: 15,
    timely_unknown: 46,
    timely_rate: 99.8,
    timely_rate_all_cases: 99.1,
  },
  {
    category: "Payments",
    sub_category: "Money Movement",
    total: 3453,
    share_pct: 5.52,
    timely_yes: 3242,
    timely_no: 140,
    timely_unknown: 71,
    timely_rate: 95.9,
    timely_rate_all_cases: 93.9,
  },
  {
    category: "Collections",
    sub_category: "Third-Party Collections",
    total: 2736,
    share_pct: 4.38,
    timely_yes: 2515,
    timely_no: 172,
    timely_unknown: 49,
    timely_rate: 93.6,
    timely_rate_all_cases: 91.9,
  },
  {
    category: "Lending",
    sub_category: "Secured Lending",
    total: 633,
    share_pct: 1.01,
    timely_yes: 584,
    timely_no: 33,
    timely_unknown: 16,
    timely_rate: 94.7,
    timely_rate_all_cases: 92.3,
  },
  {
    category: "Lending",
    sub_category: "Short-Term Lending",
    total: 333,
    share_pct: 0.53,
    timely_yes: 324,
    timely_no: 10,
    timely_unknown: 9,
    timely_rate: 97.0,
    timely_rate_all_cases: 96.4,
  },
  {
    category: "Lending",
    sub_category: "Education Lending",
    total: 39,
    share_pct: 0.06,
    timely_yes: 39,
    timely_no: 0,
    timely_unknown: 0,
    timely_rate: 100.0,
    timely_rate_all_cases: 100.0,
  },
];

export const MOCK_TRENDS_YEARLY = {
  grain: "year",
  group_by: "none",
  total_series: {
    key: "Total",
    points: [
      { period: "2017", total: 5394, is_partial: true, yoy_change_pct: null },
      { period: "2018", total: 7872, is_partial: false, yoy_change_pct: null },
      { period: "2019", total: 7075, is_partial: false, yoy_change_pct: -10.12 },
      { period: "2020", total: 8942, is_partial: false, yoy_change_pct: 26.39 },
      { period: "2021", total: 11149, is_partial: false, yoy_change_pct: 24.68 },
      { period: "2022", total: 12953, is_partial: false, yoy_change_pct: 16.18 },
      { period: "2023", total: 9131, is_partial: true, yoy_change_pct: null },
    ],
  },
  series: [
    {
      key: "Total",
      points: [
        { period: "2017", total: 5394, is_partial: true, yoy_change_pct: null },
        { period: "2018", total: 7872, is_partial: false, yoy_change_pct: null },
        { period: "2019", total: 7075, is_partial: false, yoy_change_pct: -10.12 },
        { period: "2020", total: 8942, is_partial: false, yoy_change_pct: 26.39 },
        { period: "2021", total: 11149, is_partial: false, yoy_change_pct: 24.68 },
        { period: "2022", total: 12953, is_partial: false, yoy_change_pct: 16.18 },
        { period: "2023", total: 9131, is_partial: true, yoy_change_pct: null },
      ],
    },
  ],
  filters_applied: {},
};

export const handlers = [
  http.get("*/api/v1/meta/dataset", () => {
    return HttpResponse.json(MOCK_DATASET_META);
  }),

  http.get("*/api/v1/meta/filters", () => {
    return HttpResponse.json(MOCK_FILTERS_META);
  }),

  http.get("*/api/v1/dashboard/summary", () => {
    return HttpResponse.json(MOCK_DASHBOARD_SUMMARY);
  }),

  http.get("*/api/v1/analytics/by-category", ({ request }) => {
    const url = new URL(request.url);
    const groupBy = url.searchParams.get("group_by");

    if (groupBy === "sub_category") {
      return HttpResponse.json({
        group_by: "sub_category",
        total: 62516,
        items: MOCK_SUB_CATEGORIES,
        filters_applied: {},
      });
    }

    return HttpResponse.json({
      group_by: "category",
      total: 62516,
      items: MOCK_CATEGORIES,
      filters_applied: {},
    });
  }),

  http.get("*/api/v1/analytics/trends", ({ request }) => {
    const url = new URL(request.url);
    const groupBy = url.searchParams.get("group_by");

    if (groupBy === "category") {
      return HttpResponse.json({
        grain: "year",
        group_by: "category",
        total_series: MOCK_TRENDS_YEARLY.total_series,
        series: MOCK_CATEGORIES.map((c) => ({
          key: c.category,
          points: [
            { period: "2018", total: Math.round(c.total * 0.15), is_partial: false, yoy_change_pct: null },
            { period: "2019", total: Math.round(c.total * 0.18), is_partial: false, yoy_change_pct: 20.0 },
            { period: "2020", total: Math.round(c.total * 0.22), is_partial: false, yoy_change_pct: 22.2 },
            { period: "2021", total: Math.round(c.total * 0.25), is_partial: false, yoy_change_pct: 13.6 },
            { period: "2022", total: Math.round(c.total * 0.20), is_partial: false, yoy_change_pct: -20.0 },
          ],
        })),
        filters_applied: {},
      });
    }

    return HttpResponse.json(MOCK_TRENDS_YEARLY);
  }),
];
