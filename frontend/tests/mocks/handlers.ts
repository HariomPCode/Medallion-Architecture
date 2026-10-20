import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("/api/v1/meta/dataset", () => {
    return HttpResponse.json({
      status: "ready",
      data_mode: "fixture",
      total_complaints: 62516,
    });
  }),
];
