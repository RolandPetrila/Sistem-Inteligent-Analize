/**
 * RIS Frontend Logger — 5 componente:
 * 1. Error Capture (window.onerror + unhandledrejection)
 * 2. Action Tracker (user actions pe pagini)
 * 3. API Interceptor (toate fetch calls — logat din api.ts)
 * 4. Data Validator (campuri lipsa/malformate)
 * 5. Session Context (browser, rezolutie, app version)
 *
 * Toate se trimit la POST /api/frontend-log → logs/ris_frontend.log
 * Fire-and-forget: nu blocheaza UI, batch send la 5s sau 10 entries.
 */

const ENDPOINT = "/api/frontend-log";
const BATCH_INTERVAL = 5_000; // 5 secunde
const BATCH_SIZE = 10;

interface LogEntry {
  ts: string;
  level: string;
  page: string;
  message: string;
  details?: string;
  stack?: string;
}

let _queue: LogEntry[] = [];
let _currentPage = "-";

function _now(): string {
  return new Date().toLocaleTimeString("ro-RO", { hour12: false });
}

function _flush(): void {
  if (_queue.length === 0) return;
  const batch = _queue.splice(0);
  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(batch),
  }).catch(() => {}); // fire-and-forget
}

function _enqueue(entry: LogEntry): void {
  _queue.push(entry);
  if (_queue.length >= BATCH_SIZE) {
    _flush();
  }
}

// --- Componenta 5: Session Context ---

function _sendSessionStart(): void {
  const ua = navigator.userAgent;
  const browser =
    ua.includes("Chrome") ? "Chrome" :
    ua.includes("Firefox") ? "Firefox" :
    ua.includes("Safari") ? "Safari" :
    ua.includes("Edge") ? "Edge" : "Other";
  const resolution = `${window.innerWidth}x${window.innerHeight}`;
  const platform = navigator.platform || "unknown";

  _enqueue({
    ts: _now(),
    level: "SESSION",
    page: "-",
    message: `${browser} | ${resolution} | ${platform}`,
    details: `App version: 3.1.0 | API: ${window.location.origin}`,
  });
}

// --- Componenta 1b (G3): Console.warn/error interception ---

function _setupConsoleInterception(): void {
  const origWarn = console.warn;
  const origError = console.error;

  console.warn = (...args: unknown[]) => {
    origWarn.apply(console, args);
    const msg = args.map(String).join(" ").slice(0, 200);
    // Skip React internal noise (StrictMode double-renders)
    if (!msg.includes("findDOMNode") && !msg.includes("UNSAFE_")) {
      _enqueue({ ts: _now(), level: "CONSOLE", page: _currentPage, message: `WARN: ${msg}` });
    }
  };

  console.error = (...args: unknown[]) => {
    origError.apply(console, args);
    const msg = args.map(String).join(" ").slice(0, 200);
    // Skip errors already captured by window.onerror
    if (!msg.includes("The above error occurred")) {
      _enqueue({ ts: _now(), level: "CONSOLE", page: _currentPage, message: `ERROR: ${msg}` });
    }
  };
}

// --- Componenta 1: Error Capture ---

function _setupErrorHandlers(): void {
  window.onerror = (message, source, lineno, colno, error) => {
    const file = source ? source.split("/").pop() : "unknown";
    _enqueue({
      ts: _now(),
      level: "ERROR",
      page: _currentPage,
      message: `${message}`,
      details: `${file}:${lineno}:${colno}`,
      stack: error?.stack,
    });
    return false; // don't suppress default handling
  };

  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const message =
      reason instanceof Error ? reason.message : String(reason);
    _enqueue({
      ts: _now(),
      level: "ERROR",
      page: _currentPage,
      message: `Unhandled Promise: ${message}`,
      stack: reason instanceof Error ? reason.stack : undefined,
    });
  });
}

// --- Public API ---

/** Initialize logger — call once in main.tsx */
export function initLogger(): void {
  _setupErrorHandlers();
  _setupConsoleInterception();
  _sendSessionStart();
  setInterval(_flush, BATCH_INTERVAL);

  // Flush on page unload
  window.addEventListener("beforeunload", _flush);
}

/** Set current page context (call on route change) */
export function setPage(page: string): void {
  _currentPage = page;
}

/** Componenta 2: Action Tracker — log user action */
export function logAction(
  page: string,
  action: string,
  details?: Record<string, unknown>,
): void {
  _currentPage = page;
  _enqueue({
    ts: _now(),
    level: "ACTION",
    page,
    message: action,
    details: details ? JSON.stringify(details) : undefined,
  });
}

/** Componenta 1: Error logging (from ErrorBoundary or catch blocks) */
export function logError(
  page: string,
  error: Error | string,
  context?: string,
): void {
  const err = error instanceof Error ? error : new Error(String(error));
  _enqueue({
    ts: _now(),
    level: "ERROR",
    page,
    message: `${err.message}${context ? ` | ${context}` : ""}`,
    stack: err.stack,
  });
}

/** Componenta 3: API call logging (called from api.ts interceptor) */
export function logApi(
  method: string,
  path: string,
  status: number,
  durationMs: number,
  error?: string,
): void {
  const level = error ? "API_FAIL" : "API";
  const msg = `${method} ${path} | ${status} | ${durationMs}ms`;
  _enqueue({
    ts: _now(),
    level,
    page: _currentPage,
    message: error ? `${msg} | ${error}` : msg,
  });
}

/** Componenta 4: Data Validator — log missing/malformed fields */
export function logValidation(
  page: string,
  issues: string[],
): void {
  if (issues.length === 0) return;
  _enqueue({
    ts: _now(),
    level: "VALIDATE",
    page,
    message: issues.join(" | "),
  });
}

/**
 * Componenta 4: Validate report data and log issues.
 * Returns the list of issues found (empty = all OK).
 */
export function validateReportData(
  data: Record<string, unknown> | null,
): string[] {
  const issues: string[] = [];
  if (!data) {
    issues.push("full_data is null");
    return issues;
  }
  if (!data.risk_score) {
    issues.push("risk_score missing");
  } else {
    const rs = data.risk_score as Record<string, unknown>;
    if (rs.score === null || rs.score === undefined) {
      issues.push("risk_score.score is null");
    }
    if (!rs.factors || !Array.isArray(rs.factors)) {
      issues.push("risk_score.factors missing or not array");
    }
  }
  if (!data.company) {
    issues.push("company data missing");
  }
  // Count empty sections in report_sections
  const sections = data.report_sections as Record<string, string> | undefined;
  if (sections) {
    const total = Object.keys(sections).length;
    const empty = Object.values(sections).filter(
      (v) => !v || String(v).length < 20,
    ).length;
    if (empty > 0) {
      issues.push(`sections: ${empty}/${total} empty or minimal`);
    }
  }
  return issues;
}

/**
 * Componenta 4: Validate compare data and log issues.
 */
export function validateCompareData(
  data: unknown,
): string[] {
  const issues: string[] = [];
  if (!data) {
    issues.push("compare data is null");
    return issues;
  }
  const d = data as Record<string, unknown>;
  if (!d.company_a) issues.push("company_a missing");
  if (!d.company_b) issues.push("company_b missing");
  if (!d.comparison) issues.push("comparison data missing");
  return issues;
}

/** G5: Get recent log entries as text (for copy-to-clipboard button) */
export function getLogBuffer(): string {
  return _queue
    .map((e) => `[${e.ts}] ${e.level.padEnd(8)} | ${e.page} | ${e.message}${e.details ? ` | ${e.details}` : ""}`)
    .join("\n");
}

/** G4: WebSocket event logging */
export function logWs(
  jobId: string,
  event: string,
  details?: string,
): void {
  _enqueue({
    ts: _now(),
    level: "WS",
    page: _currentPage,
    message: `${event} | job=${jobId}${details ? ` | ${details}` : ""}`,
  });
}
