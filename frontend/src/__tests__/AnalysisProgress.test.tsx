/**
 * Test pentru butonul "Diagnostic Job" din AnalysisProgress — cableaza
 * GET /api/jobs/{id}/diagnostics (api.getJobDiagnostics), endpoint functional
 * dar fara niciun call-site in UI inainte de acest fix.
 *
 * Randeaza pagina reala (nu doar logica), gaseste butonul, da click, si
 * verifica: (1) api.getJobDiagnostics a fost apelat cu id-ul jobului,
 * (2) continutul diagnosticului apare randat, (3) eroarea e tratata onest
 * (toast + mesaj vizibil, nu buton mort).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import React from "react";

const mockJob = {
  id: "job-abc123",
  type: "FULL_COMPANY_PROFILE",
  status: "DONE",
  report_level: 2,
  input_data: null,
  created_at: "2026-01-01T00:00:00",
  started_at: "2026-01-01T00:00:00",
  completed_at: "2026-01-01T00:01:00",
  error_message: null,
  progress_percent: 100,
  current_step: null,
};

// Forma REALA emisa de backend/agents/verification/completeness.py — lista
// de OBIECTE {field, section, severity, reason}, NU string-uri. Verificat
// live pe GET /api/jobs/{id}/diagnostics (job real DONE, 2026-07-16):
// randarea unui obiect ca ReactNode direct (`{g}` intr-un <li>) arunca
// "Objects are not valid as a React child".
const mockDiagnostics = {
  job_id: "job-abc123",
  status: "DONE",
  completeness: {
    score: 82,
    quality_level: "Buna",
    passed: 13,
    total_checks: 16,
    gaps: [
      {
        field: "Actionariat (asociati + administratori)",
        section: "Actionariat",
        severity: "HIGH",
        reason: "openapi.ro nu a returnat date ONRC structurate",
      },
      {
        field: "Benchmark financiar sector",
        section: "Benchmark",
        severity: "MEDIUM",
        reason: "Necesita CAEN context + date financiare firma",
      },
    ],
  },
  risk_score: { score: "Verde", numeric_score: 87.3 },
  source_diagnostics: {
    per_source: {
      anaf: { status: "OK", data_found: true },
      bpi: { status: "ERROR", data_found: false, error: "DNS fail" },
    },
  },
};

const toastMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    getJob: vi.fn(() => Promise.resolve(mockJob)),
    getJobDiagnostics: vi.fn(() => Promise.resolve(mockDiagnostics)),
    startJob: vi.fn(),
    cancelJob: vi.fn(),
    retrySource: vi.fn(),
  },
}));

vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));

vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

function renderPage(jobId = "job-abc123") {
  return render(
    <MemoryRouter initialEntries={[`/analysis/${jobId}`]}>
      <Routes>
        <Route path="/analysis/:id" element={<AnalysisProgressComponent />} />
      </Routes>
    </MemoryRouter>,
  );
}

let AnalysisProgressComponent: React.ComponentType;

describe("AnalysisProgress — Diagnostic Job", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import("../pages/AnalysisProgress");
    AnalysisProgressComponent = mod.default;
  });

  it("randeaza butonul 'Vezi Diagnostic' dupa incarcarea unui job DONE", async () => {
    const { findByRole } = renderPage();
    const button = await findByRole("button", { name: /Vezi Diagnostic/i });
    expect(button).toBeTruthy();
  });

  it("click pe buton apeleaza api.getJobDiagnostics cu id-ul jobului si randeaza continutul", async () => {
    const { api } = await import("@/lib/api");
    const { findByRole, findByText } = renderPage();

    const button = await findByRole("button", { name: /Vezi Diagnostic/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(api.getJobDiagnostics).toHaveBeenCalledWith("job-abc123");
    });

    // Continutul real al diagnosticului trebuie sa apara randat, nu doar apelat
    await findByText(/82%/);
    await findByText(/Buna/);
    // "Lipsuri detectate" — gaps sunt OBIECTE (field/section/severity/reason),
    // nu string-uri. Daca randarea ar face `{g}` direct pe obiect, React ar
    // arunca inainte sa ajungem la aceste asertii.
    await findByText("Actionariat (asociati + administratori)");
    await findByText(/openapi.ro nu a returnat date ONRC structurate/);
    await findByText("HIGH");
    await findByText("Benchmark financiar sector");
    await findByText("MEDIUM");
  });

  it("eroare la incarcarea diagnosticului: afiseaza mesaj + toast, nu buton mort", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getJobDiagnostics).mockRejectedValueOnce(
      new Error("network fail"),
    );
    const { findByRole, findByText } = renderPage();

    const button = await findByRole("button", { name: /Vezi Diagnostic/i });
    fireEvent.click(button);

    await findByText(/Nu am putut incarca diagnosticul/i);
    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.stringMatching(/Eroare la incarcarea diagnosticului/i),
        "error",
      );
    });
  });
});
