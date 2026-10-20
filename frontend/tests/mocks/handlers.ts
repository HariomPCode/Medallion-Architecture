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

export const MOCK_COMPLAINTS = [
  {
    complaint_id: 1001,
    date_submitted: "2023-04-28",
    category: "Banking",
    sub_category: "Deposit Accounts",
    product: "Checking account",
    issue: "Managing an account",
    submitted_via: "Web",
    state: "CA",
    company_response: "Closed with explanation",
    timely_response: "yes" as const,
    is_anomaly: false,
  },
  {
    complaint_id: 1002,
    date_submitted: "2023-04-27",
    category: "Payments",
    sub_category: "Card Products",
    product: "Credit card",
    issue: "Problem with a credit reporting company",
    submitted_via: "Referral",
    state: "NY",
    company_response: "Closed with non-monetary relief",
    timely_response: "yes" as const,
    is_anomaly: false,
  },
  {
    complaint_id: 1003,
    date_submitted: "2023-04-25",
    category: "Credit Reporting",
    sub_category: "Consumer Reporting",
    product: "Credit reporting",
    issue: "Incorrect information on your report",
    submitted_via: "Phone",
    state: "TX",
    company_response: "Closed with explanation",
    timely_response: "no" as const,
    is_anomaly: false,
  },
  {
    complaint_id: 1004,
    date_submitted: "2023-04-20",
    category: "Lending",
    sub_category: "Real Estate Lending",
    product: "Conventional home mortgage",
    issue: "Trouble during payment process",
    submitted_via: "Web",
    state: "FL",
    company_response: "In progress",
    timely_response: null,
    is_anomaly: false,
  },
  {
    complaint_id: 1005,
    date_submitted: "2023-04-18",
    category: "Collections",
    sub_category: "Third-Party Collections",
    product: "Other debt",
    issue: "Attempts to collect debt not owed",
    submitted_via: "Postal mail",
    state: "GA",
    company_response: "In progress",
    timely_response: null,
    is_anomaly: true,
  },
  ...Array.from({ length: 25 }, (_, i) => ({
    complaint_id: 1006 + i,
    date_submitted: `2023-01-${String(10 + (i % 18)).padStart(2, "0")}`,
    category: ["Banking", "Payments", "Credit Reporting", "Lending", "Collections"][i % 5],
    sub_category: ["Deposit Accounts", "Card Products", "Consumer Reporting", "Real Estate Lending", "Third-Party Collections"][i % 5],
    product: ["Checking account", "Credit card", "Credit reporting", "Conventional home mortgage", "Other debt"][i % 5],
    issue: ["Managing an account", "Problem with a credit reporting company", "Incorrect information on your report", "Trouble during payment process", "Attempts to collect debt not owed"][i % 5],
    submitted_via: ["Web", "Phone", "Referral", "Postal mail"][i % 4],
    state: ["CA", "NY", "TX", "FL", "GA"][i % 5],
    company_response: ["Closed with explanation", "Closed with monetary relief", "In progress", "Closed with non-monetary relief"][i % 4],
    timely_response: (i % 4 === 2 ? null : i % 7 === 0 ? "no" : "yes") as "yes" | "no" | null,
    is_anomaly: i === 6 || i === 18,
  })),
];

export const MOCK_COMPLAINT_DETAILS: Record<number, any> = {
  1001: {
    complaint_id: 1001,
    date_submitted: "2023-04-28",
    date_received: "2023-05-01",
    days_submitted_to_received: 3,
    category: "Banking",
    sub_category: "Deposit Accounts",
    product: "Checking account",
    sub_product: "Interest Checking",
    issue: "Managing an account",
    sub_issue: "Deposits and withdrawals",
    submitted_via: "Web",
    state: "CA",
    company_response: "Closed with explanation",
    company_public_response: "Company has responded to the consumer and the CFPB and confirms that all funds have been released.",
    timely_response: "yes",
    is_anomaly: false,
    anomaly_score: 0.1245,
  },
  1002: {
    complaint_id: 1002,
    date_submitted: "2023-04-27",
    date_received: "2023-04-29",
    days_submitted_to_received: 2,
    category: "Payments",
    sub_category: "Card Products",
    product: "Credit card",
    sub_product: "General-Purpose Credit Card",
    issue: "Problem with a credit reporting company",
    sub_issue: "Investigation findings not shared",
    submitted_via: "Referral",
    state: "NY",
    company_response: "Closed with non-monetary relief",
    company_public_response: null,
    timely_response: "yes",
    is_anomaly: false,
    anomaly_score: 0.0891,
  },
  1004: {
    complaint_id: 1004,
    date_submitted: "2023-04-20",
    date_received: "2023-04-22",
    days_submitted_to_received: 2,
    category: "Lending",
    sub_category: "Real Estate Lending",
    product: "Conventional home mortgage",
    sub_product: null,
    issue: "Trouble during payment process",
    sub_issue: null,
    submitted_via: "Web",
    state: "FL",
    company_response: "In progress",
    company_public_response: null,
    timely_response: null,
    is_anomaly: false,
    anomaly_score: 0.0452,
  },
  1005: {
    complaint_id: 1005,
    date_submitted: "2023-04-18",
    date_received: "2023-04-28",
    days_submitted_to_received: 10,
    category: "Collections",
    sub_category: "Third-Party Collections",
    product: "Other debt",
    sub_product: null,
    issue: "Attempts to collect debt not owed",
    sub_issue: null,
    submitted_via: "Postal mail",
    state: "GA",
    company_response: "In progress",
    company_public_response: null,
    timely_response: null,
    is_anomaly: true,
    anomaly_score: -0.1984,
  },
  2001: {
    complaint_id: 2001,
    date_submitted: "2023-03-12",
    date_received: "2023-03-22",
    days_submitted_to_received: 10,
    category: "Banking",
    sub_category: "Deposit Accounts",
    product: "Checking account",
    sub_product: null,
    issue: "Managing an account",
    sub_issue: null,
    submitted_via: "Postal mail",
    state: "NY",
    company_response: "In progress",
    company_public_response: null,
    timely_response: null,
    is_anomaly: true,
    anomaly_score: -0.1842,
  },
};

export const MOCK_QUALITY_SUMMARY = {
  overall_quality_score: 94.6,
  status: "HIGH QUALITY" as const,
  total_records: 62516,
  dimensions: [
    {
      id: "completeness",
      label: "Completeness",
      value: 98.2,
      weight: 0.25,
      definition: "Non-null rate across critical analytical fields (dates, categories, responses)",
      note: "State and sub-product have minor missingness",
    },
    {
      id: "validity",
      label: "Validity",
      value: 99.1,
      weight: 0.25,
      definition: "Conformity to expected reference categories, schemas, and formats",
      note: "Categorical mappings 100% verified against taxonomy",
    },
    {
      id: "consistency",
      label: "Consistency",
      value: 96.4,
      weight: 0.20,
      definition: "Cross-field relationship and temporal logic rules (e.g. Received >= Submitted)",
      note: "Routing lag verified non-negative across all records",
    },
    {
      id: "timeliness",
      label: "Timeliness",
      value: 96.06,
      weight: 0.15,
      definition: "Share of non-open cases resolved within 15-day statutory expectation",
      note: "Excludes 1,494 pending cases from statutory calculation",
    },
    {
      id: "ml_normality",
      label: "ML Normality",
      value: 83.2,
      weight: 0.15,
      definition: "Isolation Forest multivariate density conformance score",
      note: "Fixed by contamination parameter setting (1.0%)",
    },
  ],
  anomalies: {
    flagged: 625,
    rate_pct: 1.0,
    in_progress_share_pct: 68.48,
    by_category: [
      { category: "Banking", flagged: 248, total: 24814, rate_pct: 1.0 },
      { category: "Payments", flagged: 196, total: 19650, rate_pct: 1.0 },
      { category: "Credit Reporting", flagged: 77, total: 7710, rate_pct: 1.0 },
      { category: "Lending", flagged: 76, total: 7606, rate_pct: 1.0 },
      { category: "Collections", flagged: 28, total: 2736, rate_pct: 1.02 },
    ],
    by_company_response: [
      { company_response: "In progress", flagged: 428, total: 1494, rate_pct: 28.65 },
      { company_response: "Closed with explanation", flagged: 154, total: 51200, rate_pct: 0.30 },
      { company_response: "Closed with non-monetary relief", flagged: 25, total: 5400, rate_pct: 0.46 },
      { company_response: "Closed with monetary relief", flagged: 18, total: 4422, rate_pct: 0.41 },
    ],
  },
  model: {
    available: true,
    type: "IsolationForest",
    contamination: 0.01,
    n_estimators: 100,
    features: [
      "days_submitted_to_received",
      "category_encoded",
      "submitted_via_encoded",
      "company_response_encoded",
    ],
    mlflow_run_id: "dq-run-20230828-9842f1a",
    source: "run_metadata" as const,
  },
  timestamps: {
    quality_analysis_at: "2023-08-28T16:00:00Z",
    report_object_refreshed_at: "2026-10-19T12:00:00Z",
  },
  limitations: [
    "Isolation Forest identifies statistical outliers based on multi-attribute density, not procedural errors, fraud, or data inaccuracies.",
    "ML Normality dimension score is structurally bounded by the contamination hyperparameter (1.0% expected outliers).",
    "Intake routing lag ('Days submitted to received') measures CFPB agency routing delay and is not an evaluation of company response time.",
    "Open/in-progress cases have not received a company outcome and are excluded from the primary timeliness denominator.",
  ],
  warnings: [],
};

export const MOCK_ANOMALIES = [
  {
    complaint_id: 2001,
    date_submitted: "2023-03-12",
    category: "Banking",
    sub_category: "Deposit Accounts",
    product: "Checking account",
    issue: "Managing an account",
    submitted_via: "Postal mail",
    state: "NY",
    company_response: "In progress",
    timely_response: null,
    days_submitted_to_received: 10,
    anomaly_score: -0.1842,
    is_anomaly: true,
    annotations: {
      open_case: true,
      long_routing_delay: true,
      timely_no: false,
    },
    annotations_note: "Observations, not model explanations",
  },
  {
    complaint_id: 2002,
    date_submitted: "2023-03-18",
    category: "Payments",
    sub_category: "Card Products",
    product: "Credit card",
    issue: "Problem with a credit reporting company",
    submitted_via: "Fax",
    state: "FL",
    company_response: "Closed with explanation",
    timely_response: "no" as const,
    days_submitted_to_received: 14,
    anomaly_score: -0.1629,
    is_anomaly: true,
    annotations: {
      open_case: false,
      long_routing_delay: true,
      timely_no: true,
    },
    annotations_note: "Observations, not model explanations",
  },
  {
    complaint_id: 2003,
    date_submitted: "2023-04-02",
    category: "Credit Reporting",
    sub_category: "Consumer Reporting",
    product: "Credit reporting",
    issue: "Incorrect information on your report",
    submitted_via: "Referral",
    state: "CA",
    company_response: "In progress",
    timely_response: null,
    days_submitted_to_received: 8,
    anomaly_score: -0.1554,
    is_anomaly: true,
    annotations: {
      open_case: true,
      long_routing_delay: true,
      timely_no: false,
    },
    annotations_note: "Observations, not model explanations",
  },
  {
    complaint_id: 2004,
    date_submitted: "2023-04-15",
    category: "Lending",
    sub_category: "Real Estate Lending",
    product: "Conventional home mortgage",
    issue: "Trouble during payment process",
    submitted_via: "Web",
    state: "TX",
    company_response: "In progress",
    timely_response: null,
    days_submitted_to_received: 9,
    anomaly_score: -0.1481,
    is_anomaly: true,
    annotations: {
      open_case: true,
      long_routing_delay: true,
      timely_no: false,
    },
    annotations_note: "Observations, not model explanations",
  },
  {
    complaint_id: 2005,
    date_submitted: "2023-05-01",
    category: "Collections",
    sub_category: "Third-Party Collections",
    product: "Other debt",
    issue: "Attempts to collect debt not owed",
    submitted_via: "Phone",
    state: "GA",
    company_response: "Closed with non-monetary relief",
    timely_response: "no" as const,
    days_submitted_to_received: 7,
    anomaly_score: -0.1395,
    is_anomaly: true,
    annotations: {
      open_case: false,
      long_routing_delay: true,
      timely_no: true,
    },
    annotations_note: "Observations, not model explanations",
  },
];

// Append Phase 9 handlers to default handlers array
handlers.push(
  // GET /api/v1/complaints
  http.get("*/api/v1/complaints", ({ request }) => {
    const url = new URL(request.url);
    const q = url.searchParams.get("q");
    const categoryParam = url.searchParams.getAll("category");
    const subCategoryParam = url.searchParams.getAll("sub_category");
    const timelyParam = url.searchParams.get("timely");
    const companyResponseParam = url.searchParams.getAll("company_response");
    const stateParam = url.searchParams.getAll("state");
    const submittedViaParam = url.searchParams.getAll("submitted_via");

    const page = Math.max(1, parseInt(url.searchParams.get("page") || "1", 10));
    const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get("page_size") || "25", 10)));
    const sortBy = url.searchParams.get("sort_by") || url.searchParams.get("sort") || "date_submitted";
    const sortDir = url.searchParams.get("sort_dir") || url.searchParams.get("order") || "desc";

    let filtered = [...MOCK_COMPLAINTS];

    if (q) {
      filtered = filtered.filter((c) => String(c.complaint_id).includes(q));
    }
    if (categoryParam.length > 0) {
      filtered = filtered.filter((c) => categoryParam.includes(c.category));
    }
    if (subCategoryParam.length > 0) {
      filtered = filtered.filter((c) => subCategoryParam.includes(c.sub_category));
    }
    if (timelyParam) {
      const lower = timelyParam.toLowerCase();
      filtered = filtered.filter((c) => (c.timely_response ? c.timely_response.toLowerCase() === lower : false));
    }
    if (companyResponseParam.length > 0) {
      filtered = filtered.filter((c) => companyResponseParam.includes(c.company_response));
    }
    if (stateParam.length > 0) {
      filtered = filtered.filter((c) => c.state && stateParam.includes(c.state));
    }
    if (submittedViaParam.length > 0) {
      filtered = filtered.filter((c) => submittedViaParam.includes(c.submitted_via));
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal = (a as any)[sortBy];
      let bVal = (b as any)[sortBy];
      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      const cmp = aVal < bVal ? -1 : 1;
      return sortDir === "desc" ? -cmp : cmp;
    });

    const total = filtered.length;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const start = (page - 1) * pageSize;
    const items = filtered.slice(start, start + pageSize);

    return HttpResponse.json({
      items,
      page,
      page_size: pageSize,
      total,
      total_pages: totalPages,
      filters_applied: {},
    });
  }),

  // GET /api/v1/complaints/export
  http.get("*/api/v1/complaints/export", ({ request }) => {
    const url = new URL(request.url);
    const truncate = url.searchParams.get("truncate") === "true";
    const rowCount = truncate ? 5000 : MOCK_COMPLAINTS.length;

    const csvContent = [
      "Complaint ID,Date submitted,Category,Sub-category,Issue,Submitted via,State,Company response,Timely",
      ...MOCK_COMPLAINTS.slice(0, 5).map(
        (c) =>
          `${c.complaint_id},${c.date_submitted},"${c.category}","${c.sub_category}","${c.issue}","${c.submitted_via}","${c.state || ""}","${c.company_response}","${c.timely_response || ""}"`
      ),
    ].join("\n");

    return new HttpResponse(csvContent, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="complaints_export.csv"',
        "X-Export-Truncated": truncate ? "true" : "false",
        "X-Export-Row-Count": String(rowCount),
      },
    });
  }),

  // GET /api/v1/complaints/:id
  http.get("*/api/v1/complaints/:id", ({ params }) => {
    const id = Number(params.id);
    if (id === 999999) {
      return HttpResponse.json(
        { detail: `Complaint ${id} not found` },
        { status: 404 }
      );
    }

    if (MOCK_COMPLAINT_DETAILS[id]) {
      return HttpResponse.json(MOCK_COMPLAINT_DETAILS[id]);
    }

    const found = MOCK_COMPLAINTS.find((c) => c.complaint_id === id);
    if (found) {
      return HttpResponse.json({
        ...found,
        date_received: found.date_submitted,
        days_submitted_to_received: 2,
        sub_product: null,
        sub_issue: null,
        company_public_response: null,
        anomaly_score: found.is_anomaly ? -0.154 : 0.082,
      });
    }

    return HttpResponse.json(
      { detail: `Complaint ${id} not found` },
      { status: 404 }
    );
  }),

  // GET /api/v1/quality/summary
  http.get("*/api/v1/quality/summary", () => {
    return HttpResponse.json(MOCK_QUALITY_SUMMARY);
  }),

  // GET /api/v1/quality/anomalies
  http.get("*/api/v1/quality/anomalies", ({ request }) => {
    const url = new URL(request.url);
    const page = Math.max(1, parseInt(url.searchParams.get("page") || "1", 10));
    const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get("page_size") || "25", 10)));
    const categoryParam = url.searchParams.get("category");
    const responseParam = url.searchParams.get("company_response");

    let filtered = [...MOCK_ANOMALIES];
    if (categoryParam) {
      filtered = filtered.filter((a) => a.category === categoryParam);
    }
    if (responseParam) {
      filtered = filtered.filter((a) => a.company_response === responseParam);
    }

    const total = filtered.length;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const start = (page - 1) * pageSize;
    const items = filtered.slice(start, start + pageSize);

    return HttpResponse.json({
      items,
      page,
      page_size: pageSize,
      total,
      total_pages: totalPages,
      filters_applied: {},
    });
  })
);
