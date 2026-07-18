import { logApi } from "./logger";

// Rezultatul verificarii live a conexiunilor (GET /api/settings/preflight).
export interface PreflightItem {
  service: string;
  ok: boolean;
  message: string;
}
export interface PreflightResult {
  ready: boolean;
  verdict: string;
  claude: { ok: boolean; message: string };
  categories: {
    ai: PreflightItem[];
    principale: PreflightItem[];
    secundare: PreflightItem[];
  };
  known_dead: string[];
  critical_down: string[];
  synthesis_ok: boolean;
  summary: { ok: number; total: number };
}

const BASE = "/api";
const REQUEST_TIMEOUT_MS = 30_000;
// Bagat la build-time (frontend/.env, VITE_RIS_API_KEY) — trimis pe fiecare
// cerere cand backend-ul are RIS_API_KEY setat. Fara el, ApiKeyMiddleware
// respinge orice /api/* cu 401 daca RIS_API_KEY e configurat server-side.
const RIS_API_KEY = import.meta.env.VITE_RIS_API_KEY as string | undefined;

// Pentru fetch()-urile din afara request() (download-uri binare, FormData) —
// trebuie sa poarte acelasi header, altfel ApiKeyMiddleware le respinge cu 401.
function risHeaders(extra?: Record<string, string>): HeadersInit {
  return RIS_API_KEY ? { "X-RIS-Key": RIS_API_KEY, ...extra } : { ...extra };
}

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
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const method = options?.method || "GET";
  const start = performance.now();

  // R2 Fix: Fresh AbortController for each attempt
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(RIS_API_KEY ? { "X-RIS-Key": RIS_API_KEY } : {}),
        ...options?.headers,
      },
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
    return request<T>(path, options, _attempt + 1, timeoutMs);
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
    return request<T>(path, options, _attempt + 1, timeoutMs);
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

// --- Binary downloads (report formats, batch ZIP, timeline PDF, one-pager) ---
//
// A plain `<a href="/api/...">` is a browser navigation, which CANNOT attach
// the X-RIS-Key header — since RIS_API_KEY went live (2026-07-12) every such
// link 401s with a raw JSON body in a new tab instead of downloading. Every
// binary download must go through fetch() + risHeaders() + Blob, same as
// exportCompaniesCSV below (the pattern this was extracted from).

// Extracts the server-provided filename from Content-Disposition, handling
// both forms the backend actually emits:
//   filename*=UTF-8''name.ext   (reports.py download/{format}, RFC 5987)
//   filename="name.ext"         (FileResponse(filename=...) — one_pager,
//                                 batch ZIP, timeline PDF)
function filenameFromResponse(res: Response, fallback: string): string {
  const cd = res.headers.get("Content-Disposition");
  if (!cd) return fallback;
  const starMatch = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(cd);
  if (starMatch) {
    try {
      return decodeURIComponent(starMatch[1]);
    } catch {
      /* malformed percent-encoding — fall through to the plain form below */
    }
  }
  const plainMatch = /filename\s*=\s*"?([^";]+)"?/i.exec(cd);
  return plainMatch ? plainMatch[1] : fallback;
}

// Triggers a browser "Save As" for an in-memory Blob. Shared by every binary
// download call site instead of re-implementing the
// createObjectURL/a.download/click/revoke dance per component.
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Fetches a binary endpoint with the API key header, surfaces HTTP errors as
// ApiError (same contract as request()), and reads the real filename off
// Content-Disposition when the server sends one.
async function fetchBinary(
  path: string,
  fallbackFilename: string,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${BASE}${path}`, { headers: risHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const friendly = HTTP_ERROR_MESSAGES[res.status];
    throw new ApiError(
      friendly || err.detail || `HTTP ${res.status}`,
      err.error_code || err.code || "",
      res.status,
    );
  }
  const blob = await res.blob();
  return { blob, filename: filenameFromResponse(res, fallbackFilename) };
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
    const { blob, filename } = await fetchBinary(
      "/companies/export/csv",
      "companii_ris.csv",
    );
    downloadBlob(blob, filename);
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

  // Preflight: verificare LIVE a tuturor conexiunilor inainte de o analiza.
  // Ruleaza ~18 teste reale concurent server-side (~8-15s), de aceea timeout extins.
  preflight: () =>
    request<PreflightResult>("/settings/preflight", {}, 0, 90_000),

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
        headers: risHeaders(),
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
      headers: risHeaders({ "Content-Type": "application/json" }),
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

  // Predictive scores (Altman/Piotroski/Beneish/Zmijewski)
  getPredictive: (cui: string) =>
    request<Record<string, unknown>>(`/companies/${cui}/predictive`),

  // P1-4: Bonitate & Expunere comerciala recomandata (RON)
  getCreditExposure: (cui: string) =>
    request<{
      expunere_ron: number;
      metode_folosite: number;
      formula: string;
      kill_switch: boolean;
      disclaimer: string;
      cui: string;
      computed_at: string;
    }>(`/companies/${cui}/credit-exposure`),

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
    const res = await fetch(`${BASE}/reports/${reportId}/download/${format}`, {
      headers: risHeaders(),
    });
    if (!res.ok)
      throw new ApiError(`Download ${format} failed`, "", res.status);
    return res.blob();
  },

  // Download one-pager PDF
  downloadOnePager: async (reportId: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/reports/${reportId}/download/one_pager`, {
      headers: risHeaders(),
    });
    if (!res.ok)
      throw new ApiError("Download one-pager failed", "", res.status);
    return res.blob();
  },

  // Download compare report PDF (alias for compareReport, explicit naming)
  downloadCompareReport: async (cui1: string, cui2: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/compare/report`, {
      method: "POST",
      headers: risHeaders({ "Content-Type": "application/json" }),
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

  // Score trend with SQL window functions.
  // companyId is the company's UUID (TEXT primary key), NOT a numeric id —
  // backend/routers/companies.py:428 declares `company_id: str`. A previous
  // `number` signature forced callers to do `Number(uuid)` -> NaN -> silent
  // empty result (verified live: /companies/NaN/score-trend -> []).
  getScoreTrend: (
    companyId: string,
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

  // Frontend log viewer (returns recent log lines from ris_frontend.log)
  getFrontendLogs: (lines = 200) =>
    request<{ lines: string[]; total: number }>(
      `/frontend-log/recent?lines=${lines}`,
    ),

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

  // RAG Chat with Company
  chatCompany: (companyId: string, question: string, reportId?: string) =>
    request<{
      question: string;
      answer: string;
      provider: string;
      report_id: string;
      report_title: string;
      company_name: string;
    }>(`/companies/${companyId}/chat`, {
      method: "POST",
      body: JSON.stringify({ question, report_id: reportId ?? null }),
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
      headers: risHeaders(),
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

  // B1: NLQ Ask RIS Chatbot
  askRIS: (question: string) =>
    request<{
      answer: string;
      intent: string;
      data?: Record<string, unknown>[];
    }>("/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  // B5: Share link raport HTML
  shareReport: (reportId: string, ttlDays = 30) =>
    request<{ share_url: string; expires_at: string }>(
      `/reports/${reportId}/share`,
      {
        method: "POST",
        body: JSON.stringify({ ttl_days: ttlDays }),
      },
    ),

  // E3: Mistral OCR
  ocrDocument: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE}/documents/ocr`, {
      method: "POST",
      headers: risHeaders(),
      body: formData,
    });
    if (!res.ok) {
      const err = await res
        .json()
        .catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new ApiError(err.detail || `HTTP ${res.status}`, "", res.status);
    }
    return res.json() as Promise<{
      filename: string;
      type: string;
      pages: number;
      text: string;
      char_count: number;
      model: string;
    }>;
  },

  // B2: Knowledge Graph Visualizer
  getCompanyNetwork: (companyId: string) =>
    request<{
      cui: string;
      company_name: string;
      nodes: {
        id: string;
        label: string;
        type: string;
        status?: string;
        cui?: string;
        depth?: number;
        toxic?: boolean;
      }[];
      edges: { source: string; target: string; label?: string }[];
      stats?: Record<string, unknown>;
    }>(`/companies/${companyId}/network`),

  // FTS5 full-text company search
  searchFts: (q: string, limit = 20) =>
    request<
      {
        id: number;
        name: string;
        cui: string;
        caen_code?: string;
        county?: string;
        city?: string;
      }[]
    >(`/companies/search/fts?q=${encodeURIComponent(q)}&limit=${limit}`),

  // Quick-score (bulk, no AI) — POST /analysis/quick-score
  quickScore: (cuis: string[]) =>
    request<{
      results: {
        cui: string;
        name?: string;
        ca_last_year?: number | null;
        angajati?: number | null;
        tva_activ?: boolean;
        inactiv_anaf?: boolean;
        quick_score?: number;
        risk?: string;
        error?: string;
      }[];
      note: string;
    }>("/analysis/quick-score", {
      method: "POST",
      body: JSON.stringify({ cuis }),
    }),

  // VIES — validare TVA intracomunitar UE (partener/contraparte) — POST /analysis/vies
  checkVies: (countryCode: string, vatNumber: string) =>
    request<{
      available: boolean;
      valid: boolean | null;
      country_code?: string;
      vat_number?: string;
      name?: string;
      address?: string;
      request_date?: string;
      consultation_number?: string;
      error?: string;
    }>("/analysis/vies", {
      method: "POST",
      body: JSON.stringify({
        country_code: countryCode,
        vat_number: vatNumber,
      }),
    }),

  // Versiune care ruleaza + stare auto-update ('Vercel local')
  getVersion: () =>
    request<{
      version: string;
      running: { sha: string; date: string; branch: string; build: string };
      local?: string | null;
      remote?: string | null;
      update_available?: boolean;
      behind?: number;
      last_check?: string | null;
      updating?: boolean;
    }>("/version"),

  // Monitoring audit-log for an alert
  getMonitoringAuditLog: (alertId: string) =>
    request<{
      alert_id: string;
      audit_log: {
        timestamp?: string;
        triggered_at?: string;
        change_type: string;
        old_value: string;
        new_value: string;
        severity: string;
      }[];
    }>(`/monitoring/${alertId}/audit-log`),

  // F4-4: Suprima o alerta de monitorizare pentru o perioada definita (sau
  // nedefinit, daca suppress_until lipseste). Backend: POST /monitoring/{id}/suppress
  // (SuppressRequest: reason: str, suppress_until: str | None). Poate raspunde
  // si cu {status:"accepted", note} daca migrarea coloanei nu a rulat inca.
  suppressAlert: (
    alertId: string,
    data: { reason: string; suppress_until?: string | null },
  ) =>
    request<{
      alert_id: string;
      suppressed_until?: string | null;
      reason?: string;
      status: string;
      note?: string;
    }>(`/monitoring/${alertId}/suppress`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Regenerate a single report section (re-runs synthesis for one section).
  // Quality-route sections (e.g. executive_summary via Claude Opus) take 264-324s at
  // --effort max — server cap = SYNTHESIS_CLAUDE_TIMEOUT + 120 (~480s la default). Clientul
  // trebuie sa astepte peste cap-ul server ca 504-ul serverului sa castige, nu abort-ul local.
  regenerateSection: (jobId: string, sectionKey: string) =>
    request<{
      job_id: string;
      section_key: string;
      status: string;
      section: { title?: string; content?: string; word_count?: number };
    }>(
      `/jobs/${jobId}/section/${sectionKey}/regenerate`,
      { method: "POST" },
      0,
      520_000,
    ),

  // Export SEAP tenders as .ics calendar file
  exportIcs: async (reportId: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/reports/${reportId}/export/ics`, {
      headers: risHeaders(),
    });
    if (!res.ok) {
      const err = await res
        .json()
        .catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new ApiError(err.detail || `HTTP ${res.status}`, "", res.status);
    }
    return res.blob();
  },

  // Multi-year timeline report PDF (binary)
  downloadTimelineReportPdf: async (cui: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/companies/${cui}/timeline-report/pdf`, {
      headers: risHeaders(),
    });
    if (!res.ok)
      throw new ApiError("Timeline PDF generation failed", "", res.status);
    return res.blob();
  },

  // Download any generated report format (pdf/docx/excel/html/pptx/one_pager)
  // and trigger a browser save in one call — replaces the <a href="/api/..."> links
  // in ReportHeader/ReportsList/CompanyDetail, which cannot carry X-RIS-Key.
  downloadReportFormat: async (
    reportId: string,
    format: string,
  ): Promise<void> => {
    const ext =
      format === "excel" ? "xlsx" : format === "one_pager" ? "pdf" : format;
    const { blob, filename } = await fetchBinary(
      `/reports/${reportId}/download/${format}`,
      `raport_${reportId}.${ext}`,
    );
    downloadBlob(blob, filename);
  },

  // Download the batch ZIP and trigger a browser save (same reasoning as above)
  // — replaces the <a href="/api/batch/{id}/download"> link in BatchAnalysis.
  downloadBatchZip: async (batchId: string): Promise<void> => {
    const { blob, filename } = await fetchBinary(
      `/batch/${batchId}/download`,
      `batch_${batchId.slice(0, 8)}.zip`,
    );
    downloadBlob(blob, filename);
  },
};
