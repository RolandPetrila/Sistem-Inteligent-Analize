import { logApi } from "./logger";

const BASE = "/api";
const REQUEST_TIMEOUT_MS = 30_000;

// User-friendly error messages for common HTTP codes (Romanian)
const HTTP_ERROR_MESSAGES: Record<number, string> = {
  400: "Cerere invalida. Verifica datele introduse.",
  401: "Neautorizat. Verifica cheia API.",
  403: "Acces interzis.",
  404: "Resursa nu a fost gasita.",
  408: "Cererea a expirat. Incearca din nou.",
  429: "Prea multe cereri. Asteapta cateva secunde.",
  500: "Eroare server. Incearca din nou.",
  502: "Server indisponibil momentan.",
  503: "Serviciu temporar indisponibil.",
  504: "Timeout server. Incearca din nou.",
};

// D21: Auto-retry with exponential backoff for 429 and transient errors
// R2 Fix #8: Create NEW AbortController per attempt (not reused across retries)
async function request<T>(
  path: string,
  options?: RequestInit,
  _attempt = 0,
): Promise<T> {
  const method = options?.method || "GET";
  const start = performance.now();

  // R2 Fix: Fresh AbortController for each attempt
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
      signal: controller.signal,
    });
  } catch (netErr) {
    clearTimeout(timeoutId);
    const ms = Math.round(performance.now() - start);
    // Check if it was an abort (timeout)
    if (netErr instanceof DOMException && netErr.name === "AbortError") {
      logApi(method, path, 0, ms, "Request timeout");
      throw new ApiError(
        "Cererea a expirat. Incearca din nou.",
        "TIMEOUT",
        408,
      );
    }
    logApi(method, path, 0, ms, `Network error: ${netErr}`);
    throw new ApiError(
      "Eroare de retea. Verifica conexiunea.",
      "NETWORK_ERROR",
      0,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  const durationMs = Math.round(performance.now() - start);

  // D21: Auto-retry on 429 (rate limit) — up to 2 retries with backoff
  if (res.status === 429 && _attempt < 2) {
    logApi(
      method,
      path,
      429,
      durationMs,
      `Rate limited, retry ${_attempt + 1}`,
    );
    const retryAfter = parseInt(res.headers.get("Retry-After") || "3", 10);
    const delay = Math.min(retryAfter * 1000, 10_000);
    await new Promise((r) => setTimeout(r, delay));
    return request<T>(path, options, _attempt + 1);
  }

  if (res.status === 429) {
    logApi(
      method,
      path,
      429,
      durationMs,
      "Rate limited, max retries exhausted",
    );
    const retryAfter = parseInt(res.headers.get("Retry-After") || "5", 10);
    const err = await res.json().catch(() => ({}));
    const code = err.error_code || "RATE_LIMITED";
    throw new ApiError(
      `Prea multe cereri. Reincercati in ${retryAfter}s.`,
      code,
      res.status,
      retryAfter,
    );
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
    // Use user-friendly message, with server detail as fallback
    const friendlyMsg = HTTP_ERROR_MESSAGES[res.status];
    const serverMsg = err.detail || `HTTP ${res.status}`;
    const msg = friendlyMsg || serverMsg;
    logApi(method, path, res.status, durationMs, serverMsg);
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
  constructor(
    message: string,
    code: string,
    status: number,
    retryAfter?: number,
  ) {
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
      `/jobs${qs ? `?${qs}` : ""}`,
    );
  },
  getJob: (id: string) => request<import("./types").Job>(`/jobs/${id}`),
  createJob: (data: {
    analysis_type: string;
    report_level: number;
    input_params: Record<string, unknown>;
  }) =>
    request<import("./types").Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  startJob: (id: string) =>
    request<{ status: string }>(`/jobs/${id}/start`, { method: "POST" }),
  cancelJob: (id: string) =>
    request<{ status: string }>(`/jobs/${id}/cancel`, { method: "POST" }),
  getJobDiagnostics: (id: string) =>
    request<Record<string, unknown>>(`/jobs/${id}/diagnostics`),
  getLatestDiagnostics: () =>
    request<Record<string, unknown>>("/jobs/diagnostics/latest"),
  retrySource: (jobId: string, source: string) =>
    request<{
      job_id: string;
      source: string;
      success: boolean;
      data?: unknown;
      error?: string;
    }>(`/jobs/${jobId}/retry-source/${source}`, { method: "POST" }),

  // Reports
  listReports: (params?: {
    report_type?: string;
    limit?: number;
    offset?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.report_type) q.set("report_type", params.report_type);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{ reports: import("./types").Report[]; total: number }>(
      `/reports${qs ? `?${qs}` : ""}`,
    );
  },
  getReport: (id: string) =>
    request<
      import("./types").Report & { full_data: unknown; sources: unknown[] }
    >(`/reports/${id}`),

  // Companies
  listCompanies: (params?: {
    search?: string;
    limit?: number;
    offset?: number;
    sort?: string;
    county?: string;
    caen?: string;
    risk_score?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    if (params?.sort) q.set("sort", params.sort);
    if (params?.county) q.set("county", params.county);
    if (params?.caen) q.set("caen", params.caen);
    if (params?.risk_score) q.set("risk_score", params.risk_score);
    const qs = q.toString();
    return request<{ companies: import("./types").Company[]; total: number }>(
      `/companies${qs ? `?${qs}` : ""}`,
    );
  },

  // N4: Company detail page
  getCompany: (id: string) =>
    request<
      import("./types").Company & {
        reports: {
          id: string;
          report_type: string;
          report_level: number;
          title: string | null;
          summary: string | null;
          risk_score: string | null;
          created_at: string;
        }[];
        score_history: {
          numeric_score: number | null;
          dimensions: string | null;
          recorded_at: string;
        }[];
      }
    >(`/companies/${id}`),

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
    request<{
      analysis_type: string;
      input_params: Record<string, unknown>;
      confidence: number;
      suggestion: string;
    }>("/analysis/parse-query", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),

  // Settings
  getSettings: () =>
    request<{
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
    request<{ success: boolean }>("/settings/test-telegram", {
      method: "POST",
    }),

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
    request<{
      batch_id: string;
      resumed: number;
      cuis: string[];
      status: string;
    }>(`/batch/${batchId}/resume`, { method: "POST" }),

  // Monitoring (C24 fix: match backend MonitoringCreate schema)
  listMonitoring: () => request<{ alerts: unknown[] }>("/monitoring"),
  createMonitoring: (data: {
    company_id: string;
    alert_type?: string;
    check_frequency?: string;
    telegram_notify?: boolean;
  }) =>
    request<unknown>("/monitoring", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteMonitoring: (id: string) =>
    request<unknown>(`/monitoring/${id}`, { method: "DELETE" }),
  checkMonitoringNow: () =>
    request<unknown>("/monitoring/check-now", { method: "POST" }),

  // Stats trend
  getStatsTrend: () =>
    request<{ trend: { month: string; count: number }[] }>("/stats/trend"),

  // Health deep
  healthDeep: () => request<Record<string, unknown>>("/health/deep"),

  // Batch upload (FormData — not JSON, needs custom fetch with logging)
  uploadBatch: async (
    file: File,
    analysisType = "FULL_COMPANY_PROFILE",
    reportLevel = 2,
  ) => {
    const start = performance.now();
    const res = await fetch(
      `${BASE}/batch?analysis_type=${analysisType}&report_level=${reportLevel}`,
      {
        method: "POST",
        body: (() => {
          const fd = new FormData();
          fd.append("file", file);
          return fd;
        })(),
      },
    );
    const ms = Math.round(performance.now() - start);
    if (!res.ok) {
      logApi("POST", "/batch", res.status, ms, "Upload failed");
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(err.detail || `HTTP ${res.status}`, "", res.status);
    }
    logApi("POST", "/batch", res.status, ms);
    return res.json() as Promise<{ batch_id: string; total_cuis: number }>;
  },

  // Compare report PDF download (binary response)
  compareReport: async (cui1: string, cui2: string) => {
    const start = performance.now();
    const res = await fetch(`${BASE}/compare/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cui_1: cui1, cui_2: cui2 }),
    });
    const ms = Math.round(performance.now() - start);
    if (!res.ok) {
      logApi(
        "POST",
        "/compare/report",
        res.status,
        ms,
        "PDF generation failed",
      );
      throw new ApiError("PDF generation failed", "", res.status);
    }
    logApi("POST", "/compare/report", res.status, ms);
    return res.blob();
  },

  // Monitoring toggle
  toggleMonitoring: (id: string) =>
    request<unknown>(`/monitoring/${id}/toggle`, { method: "PUT" }),

  // Notifications
  listNotifications: (params?: { unread_only?: boolean; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.unread_only) q.set("unread_only", "true");
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<{
      notifications: import("./types").Notification[];
      unread_count: number;
    }>(`/notifications${qs ? `?${qs}` : ""}`);
  },
  markNotificationRead: (id: string) =>
    request<{ success: boolean }>(`/notifications/${id}/read`, {
      method: "PUT",
    }),
  markAllNotificationsRead: () =>
    request<{ success: boolean }>("/notifications/read-all", { method: "PUT" }),

  // Company favorites
  toggleFavorite: (id: string) =>
    request<{ is_favorite: boolean }>(`/companies/${id}/favorite`, {
      method: "PUT",
    }),

  // Risk movers
  getRiskMovers: () =>
    request<{ movers: import("./types").RiskMover[] }>(
      "/companies/stats/risk-movers",
    ),

  // Company timeline
  getCompanyTimeline: (id: string) =>
    request<{ events: import("./types").TimelineEvent[] }>(
      `/companies/${id}/timeline`,
    ),

  // Report email
  sendReportEmail: (
    reportId: string,
    data: { to: string; subject: string; message: string },
  ) =>
    request<{ success: boolean }>(`/reports/${reportId}/send-email`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Download report in any format (PDF, DOCX, HTML, Excel, PPTX)
  downloadReport: async (reportId: string, format: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/reports/${reportId}/download/${format}`);
    if (!res.ok)
      throw new ApiError(`Download ${format} failed`, "", res.status);
    return res.blob();
  },

  // Download one-pager PDF
  downloadOnePager: async (reportId: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/reports/${reportId}/download/one_pager`);
    if (!res.ok)
      throw new ApiError("Download one-pager failed", "", res.status);
    return res.blob();
  },

  // Download compare report PDF (alias for compareReport, explicit naming)
  downloadCompareReport: async (cui1: string, cui2: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/compare/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cui_1: cui1, cui_2: cui2 }),
    });
    if (!res.ok)
      throw new ApiError("Compare report generation failed", "", res.status);
    return res.blob();
  },

  // Get report data (lazy-load full JSON)
  getReportData: (
    reportId: string,
    section?: string,
  ): Promise<Record<string, unknown>> => {
    const url = section
      ? `/reports/${reportId}/data?section=${section}`
      : `/reports/${reportId}/data`;
    return request(url);
  },

  // Get report delta (changes vs previous analysis)
  getReportDelta: (reportId: string): Promise<import("./types").ReportDelta> =>
    request(`/reports/${reportId}/delta`),

  // List favorites
  listFavorites: (): Promise<{
    companies: import("./types").Company[];
    total: number;
  }> => request("/companies/favorites"),

  // Score trend with SQL window functions
  getScoreTrend: (
    companyId: number,
  ): Promise<import("./types").ScoreTrendPoint[]> =>
    request(`/companies/${companyId}/score-trend`),

  // Monitoring history
  getMonitoringHistory: (limit = 20) =>
    request<{ history: Record<string, unknown>[] }>(
      `/monitoring/history?limit=${limit}`,
    ),

  // Settings — test individual service
  testService: (service: string) =>
    request<{ ok: boolean; message: string }>(`/settings/test/${service}`, {
      method: "POST",
    }),

  // Company tags (F3-3)
  getCompanyTags: (companyId: string) =>
    request<{ tags: string[] }>(`/companies/${companyId}/tags`),
  addCompanyTag: (companyId: string, tag: string) =>
    request<{ ok: boolean }>(`/companies/${companyId}/tags`, {
      method: "POST",
      body: JSON.stringify({ tag }),
    }),
  removeCompanyTag: (companyId: string, tag: string) =>
    request<{ ok: boolean }>(
      `/companies/${companyId}/tags/${encodeURIComponent(tag)}`,
      {
        method: "DELETE",
      },
    ),

  // Company notes (F3-3)
  getCompanyNote: (companyId: string) =>
    request<{ note: string; updated_at: string | null }>(
      `/companies/${companyId}/note`,
    ),
  upsertCompanyNote: (companyId: string, note: string) =>
    request<{ ok: boolean }>(`/companies/${companyId}/note`, {
      method: "PUT",
      body: JSON.stringify({ note }),
    }),

  // Compare templates (F3-8)
  listCompareTemplates: () =>
    request<{
      templates: {
        id: string;
        name: string;
        cuis: string[];
        created_at: string;
      }[];
    }>("/compare/templates"),
  saveCompareTemplate: (name: string, cuis: string[]) =>
    request<{ ok: boolean; id: string }>("/compare/templates", {
      method: "POST",
      body: JSON.stringify({ name, cuis }),
    }),
  deleteCompareTemplate: (templateId: string) =>
    request<{ ok: boolean }>(`/compare/templates/${templateId}`, {
      method: "DELETE",
    }),

  // Sector CAEN dashboard (F3-6)
  getSectorDashboard: (caenCode: string) =>
    request<{
      caen_code: string;
      caen_description: string;
      stats: Record<string, number | null>;
      top_companies: {
        id: string;
        name: string;
        cui: string;
        score: number;
        county: string;
      }[];
    }>(`/compare/sector/${caenCode}/dashboard`),

  // F6-6: Auto re-analyze toggle
  toggleAutoReanalyze: (companyId: string) =>
    request<{ ok: boolean; auto_reanalyze: boolean }>(
      `/companies/${companyId}/auto-reanalyze`,
      {
        method: "POST",
      },
    ),

  // Batch preview CSV
  previewBatch: async (file: File) => {
    const start = performance.now();
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/batch/preview`, {
      method: "POST",
      body: fd,
    });
    const ms = Math.round(performance.now() - start);
    if (!res.ok) {
      logApi("POST", "/batch/preview", res.status, ms, "Preview failed");
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(err.detail || `HTTP ${res.status}`, "", res.status);
    }
    logApi("POST", "/batch/preview", res.status, ms);
    return res.json() as Promise<{
      valid_count: number;
      invalid_count: number;
      valid_cuis: string[];
      invalid_entries: { line: number; cui: string; error: string }[];
      estimated_time_minutes: number;
    }>;
  },
};
