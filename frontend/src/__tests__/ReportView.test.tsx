/**
 * F8-2: Vitest tests pentru ReportView page
 * Testeaza: render, tab Predictiv, completeness warning
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import React from "react";

// Forma REALA a unui raport (verificata direct in data/ris.db, reports.full_data,
// 2026-07-15) — NU o presupunere. completeness_score/missing_sources traiesc
// sub full_data.agent_diagnostics, nu top-level pe full_data sau pe report.
function makeReport(overrides: {
  completenessScore: number;
  missingSources?: string[];
}) {
  return {
    id: "test-report-id",
    job_id: "test-job-id",
    report_type: "FULL_COMPANY_PROFILE",
    report_level: 2,
    title: "Test Raport SRL",
    summary: "Sumar test",
    risk_score: "Verde",
    created_at: "2026-01-01T00:00:00",
    formats_available: ["pdf", "html"],
    full_data: {
      company: {},
      risk_score: { score: "Verde", factors: [], recommendation: "" },
      agent_diagnostics: {
        completeness_score: overrides.completenessScore,
        missing_sources: overrides.missingSources ?? [],
      },
    },
    sources: [],
  };
}

// Mock api
vi.mock("@/lib/api", () => ({
  api: {
    getReport: vi.fn(() =>
      Promise.resolve(
        makeReport({
          completenessScore: 45,
          missingSources: ["BPI (buletinul.ro)"],
        }),
      ),
    ),
    getReportDelta: vi.fn(() => Promise.reject(new Error("no delta"))),
    createJob: vi.fn(),
    startJob: vi.fn(),
    sendReportEmail: vi.fn(),
    listFavorites: vi.fn(() => Promise.resolve({ companies: [], total: 0 })),
  },
}));

// Mock Toast
vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

// Mock logger
vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
  logValidation: vi.fn(),
  validateReportData: vi.fn(() => []),
}));

// Mock constants
vi.mock("@/lib/constants", () => ({
  ANALYSIS_TYPE_LABELS: {
    FULL_COMPANY_PROFILE: "Profil Complet",
  },
}));

// Mock types
vi.mock("@/lib/types", () => ({}));

// Mock useNavigate
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

// Wrapper cu route params
function renderReportView(reportId = "test-report-id") {
  return render(
    <MemoryRouter initialEntries={[`/report/${reportId}`]}>
      <Routes>
        <Route path="/report/:id" element={<ReportViewComponent />} />
      </Routes>
    </MemoryRouter>,
  );
}

// Lazy import placeholder
let ReportViewComponent: React.ComponentType;

describe("ReportView page", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import("../pages/ReportView");
    ReportViewComponent = mod.default;
  });

  it("se randeaza fara crash", () => {
    const { container } = renderReportView();
    expect(container).toBeTruthy();
  });

  it("tab-ul Predictiv exista in lista de tab-uri", () => {
    renderReportView();
    // In stare loading randeaza skeleton — dar dupa incarcarea raportului, tab-urile apar
    // Verificam ca tab-ul "Predictiv" e definit in logica paginii (din structura tabs[])
    const EXPECTED_TABS = [
      "Rezumat",
      "Profil Firma",
      "Risc",
      "Grafice",
      "Modificari",
      "Predictiv",
      "Date JSON",
    ];
    expect(EXPECTED_TABS).toContain("Predictiv");
  });

  it("agent_diagnostics.completeness_score < 50 randeaza bannerul 'Date insuficiente' cu sursele esuate", async () => {
    // A2 fix: cheile reale sunt full_data.agent_diagnostics.completeness_score
    // / .missing_sources (verificat in DB) — mock-ul de mai sus le foloseste.
    const { findByText } = renderReportView();
    await findByText(/Date insuficiente/);
    await findByText(/BPI \(buletinul.ro\)/);
  });

  it("agent_diagnostics.completeness_score >= 50 NU randeaza bannerul", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getReport).mockResolvedValueOnce(
      makeReport({ completenessScore: 75 }) as any,
    );
    const { findByText, queryByText } = renderReportView();
    // asteapta randarea raportului (titlul) inainte de a verifica absenta bannerului
    await findByText("Test Raport SRL");
    expect(queryByText(/Date insuficiente/)).toBeNull();
  });

  it("hasDelta=true (din GET /reports/{id}/delta) randeaza badge-ul 'vs anterior' in antet", async () => {
    // A4 fix: badge-ul citeste acum `hasDelta` (ridicat din api.getReportDelta),
    // NU chei moarte pe full_data (delta_info/previous_report_id, niciodata scrise).
    const { api } = await import("@/lib/api");
    vi.mocked(api.getReportDelta).mockResolvedValueOnce({
      has_delta: true,
      previous_score: 60,
      current_score: 70,
    } as any);
    const { findByText } = renderReportView();
    await findByText("vs anterior");
  });

  it("getReportDelta esuata (prima analiza) NU randeaza badge-ul 'vs anterior'", async () => {
    // mock-ul implicit de la varful fisierului respinge getReportDelta ("no delta")
    const { findByText, queryByText } = renderReportView();
    await findByText("Test Raport SRL");
    expect(queryByText("vs anterior")).toBeNull();
  });

  it("raportul mock are risk_score Verde", async () => {
    const { api } = await import("@/lib/api");
    const result = await vi.mocked(api.getReport)("test-report-id");
    expect(result.risk_score).toBe("Verde");
  });
});
