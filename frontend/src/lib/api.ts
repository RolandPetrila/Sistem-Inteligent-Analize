import { logApi } from "./logger";

const BASE = "/api";

// D21: Auto-retry with exponential backoff for 429 and transient errors
async function request<T>(path: string, options?: RequestInit, _attempt = 0): Promise<T> {
  const method = options?.method || "GET";
  const start = performance.now();

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
    });
  } catch (netErr) {
    const ms = Math.round(performance.now() - start);
    logApi(method, path, 0, ms, `Network error: ${netErr}`);
    throw netErr;
  }

  const durationMs = Math.round(performance.now() - start);

  // D21: Auto-retry on 429 (rate limit) — up to 2 retries with backoff
  if (res.status === 429 && _attempt < 2) {
    logApi(method, path, 429, durationMs, `Rate limited, retry ${_attempt + 1}`);
    const retryAfter = parseInt(res.headers.get("Retry-After") || "3", 10);
    const delay = Math.min(retryAfter * 1000, 10_000);
    await new Promise((r) => setTimeout(r, delay));
    return request<T>(path, options, _attempt + 1);
  }

  if (res.status === 429) {
    logApi(method, path, 429, durationMs, "Rate limited, max retries exhausted");
    const retryAfter = parseInt(res.headers.get("Retry-After") || "5", 10);
    const err = await res.json().catch(() => ({}));
    const code = err.error_code || "RATE_LIMITED";
    throw new ApiError(`Prea multe cereri. Reincercati in ${retryAfter}s.`, code, res.status, retryAfter);
  }

  // D21: Auto-retry on 503 (service unavailable) — 1 retry after 2s
  if (res.status === 503 && _attempt < 1) {
    logApi(method, path, 503, durationMs, "Service unavailable, retrying");
    await new Promise((r) => setTimeout(r, 2000));
    return request<T>(path, options, _attempt + 1);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const code = err.error_code || err.code || "";
    const msg = err.detail || `HTTP ${res.status}`;
    logApi(method, path, res.status, durationMs, msg);
    throw new ApiError(msg, code, res.status);
  }

  // Success — log it (skip frontend-log to avoid infinite loop)
  if (!path.includes("frontend-log")) {
    logApi(method, path, res.status, durationMs);
  }

  return res.json();
}

// 9C: ApiError class with error_code for toast display
export class ApiError extends Error {
  code: string;
  status: number;
  retryAfter?: number;
  constructor(message: string, code: string, status: number, retryAfter?: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export const api = {
  // Stats
  getStats: () => request<import("./types").Stats>("/stats"),
  health: () => request<{ status: string }>("/health"),

  // Jobs
  listJobs: (params?: { status?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{ jobs: import("./types").Job[]; total: number }>(
      `/jobs${qs ? `?${qs}` : ""}`
    );
  },
  getJob: (id: string) => request<import("./types").Job>(`/jobs/${id}`),
  createJob: (data: {
    analysis_type: string;
    report_level: number;
    input_params: Record<string, unknown>;
  }) => request<import("./types").Job>("/jobs", { method: "POST", body: JSON.stringify(data) }),
  startJob: (id: string) =>
    request<{ status: string }>(`/jobs/${id}/start`, { method: "POST" }),
  cancelJob: (id: string) =>
    request<{ status: string }>(`/jobs/${id}/cancel`, { method: "POST" }),
  getJobDiagnostics: (id: string) =>
    request<Record<string, unknown>>(`/jobs/${id}/diagnostics`),
  getLatestDiagnostics: () =>
    request<Record<string, unknown>>("/jobs/diagnostics/latest"),
  retrySource: (jobId: string, source: string) =>
    request<{ job_id: string; source: string; success: boolean; data?: unknown; error?: string }>(
      `/jobs/${jobId}/retry-source/${source}`, { method: "POST" }
    ),

  // Reports
  listReports: (params?: { report_type?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.report_type) q.set("report_type", params.report_type);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{ reports: import("./types").Report[]; total: number }>(
      `/reports${qs ? `?${qs}` : ""}`
    );
  },
  getReport: (id: string) => request<import("./types").Report & { full_data: unknown; sources: unknown[] }>(`/reports/${id}`),

  // Companies
  listCompanies: (params?: { search?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{ companies: import("./types").Company[]; total: number }>(
      `/companies${qs ? `?${qs}` : ""}`
    );
  },

  // N4: Company detail page
  getCompany: (id: string) =>
    request<import("./types").Company & {
      reports: { id: string; report_type: string; report_level: number; title: string | null; summary: string | null; risk_score: string | null; created_at: string }[];
      score_history: { numeric_score: number | null; dimensions: string | null; recorded_at: string }[];
    }>(`/companies/${id}`),

  exportCompaniesCSV: async () => {
    const res = await fetch(`${BASE}/companies/export/csv`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "companii_ris.csv";
    a.click();
    URL.revokeObjectURL(url);
  },

  // Analysis types
  getAnalysisTypes: () =>
    request<import("./types").AnalysisTypeInfo[]>("/analysis/types"),

  parseQuery: (query: string) =>
    request<{ analysis_type: string; input_params: Record<string, unknown>; confidence: number; suggestion: string }>(
      "/analysis/parse-query",
      { method: "POST", body: JSON.stringify({ query }) }
    ),

  // Settings
  getSettings: () => request<{
    fields: Record<string, string>;
    synthesis_mode: string;
    has_tavily: boolean;
    has_gemini: boolean;
    has_groq: boolean;
    has_cerebras: boolean;
    has_telegram: boolean;
    has_email: boolean;
  }>("/settings"),

  updateSettings: (fields: Record<string, string>) =>
    request<{ updated: string[]; count: number }>("/settings", {
      method: "PUT",
      body: JSON.stringify({ fields }),
    }),

  testTelegram: () =>
    request<{ success: boolean }>("/settings/test-telegram", { method: "POST" }),

  // Compare (C24 fix: match backend CompareRequest/SectorRequest schemas)
  compareCompanies: (cui_list: string[]) =>
    request<unknown>("/compare", {
      method: "POST",
      body: JSON.stringify({ cui_list }),
    }),
  compareSector: (caen_section: string, limit?: number) =>
    request<unknown>("/compare/sector", {
      method: "POST",
      body: JSON.stringify({ caen_section, limit: limit ?? 10 }),
    }),

  // Batch
  getBatchStatus: (batchId: string) =>
    request<{
      batch_id: string;
      status: string;
      progress_percent: number;
      current_step: string;
      total: number;
      completed: number;
      failed: number;
      current_cui: string;
    }>(`/batch/${batchId}`),

  resumeBatch: (batchId: string) =>
    request<{ batch_id: string; resumed: number; cuis: string[]; status: string }>(
      `/batch/${batchId}/resume`, { method: "POST" }
    ),

  // Monitoring (C24 fix: match backend MonitoringCreate schema)
  listMonitoring: () =>
    request<{ alerts: unknown[] }>("/monitoring"),
  createMonitoring: (data: { company_id: string; alert_type?: string; check_frequency?: string; telegram_notify?: boolean }) =>
    request<unknown>("/monitoring", { method: "POST", body: JSON.stringify(data) }),
  deleteMonitoring: (id: string) =>
    request<unknown>(`/monitoring/${id}`, { method: "DELETE" }),
  checkMonitoringNow: () =>
    request<unknown>("/monitoring/check-now", { method: "POST" }),

  // Stats trend
  getStatsTrend: () =>
    request<{ trend: { month: string; count: number }[] }>("/stats/trend"),

  // Health deep
  healthDeep: () => request<Record<string, unknown>>("/health/deep"),
};
