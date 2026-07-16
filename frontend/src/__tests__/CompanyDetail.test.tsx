/**
 * Regression test — sectiunea "Evolutie Scor" din CompanyDetail apela
 * api.getScoreTrend(Number(id)), dar `id` (useParams) e UUID-ul companiei
 * (ex. "59fc67e4-6a75-46ae-984b-9cfd1522ee1f"), NU un id numeric — backend-ul
 * (backend/routers/companies.py:428) declara `company_id: str`.
 * `Number(uuid)` => NaN => request la /companies/NaN/score-trend => [] mereu,
 * verificat live pe serviciul real (vezi raportul agentului).
 *
 * Testul randeaza componenta REALA cu forma REALA de date si verifica ca
 * api.getScoreTrend e apelat cu string-ul UUID, nu cu NaN.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import React from "react";

const COMPANY_ID = "59fc67e4-6a75-46ae-984b-9cfd1522ee1f";

const mockCompany = {
  id: COMPANY_ID,
  cui: "12345678",
  name: "ACME TEST SRL",
  caen_code: "6201",
  caen_description: "Activitati de realizare a soft-ului la comanda",
  county: "Cluj",
  city: "Cluj-Napoca",
  first_analyzed_at: "2026-01-01T00:00:00",
  last_analyzed_at: "2026-01-02T00:00:00",
  analysis_count: 2,
  reports: [],
  score_history: [],
};

vi.mock("@/lib/api", () => ({
  api: {
    getCompany: vi.fn(() => Promise.resolve(mockCompany)),
    getCompanyTimeline: vi.fn(() => Promise.resolve({ events: [] })),
    getScoreTrend: vi.fn(() => Promise.resolve([])),
    getCompanyTags: vi.fn(() => Promise.resolve({ tags: [] })),
    getCompanyNote: vi.fn(() =>
      Promise.resolve({ note: "", updated_at: null }),
    ),
    getCreditExposure: vi.fn(() => Promise.reject(new Error("no report"))),
    chatCompany: vi.fn(),
    toggleFavorite: vi.fn(),
    toggleAutoReanalyze: vi.fn(),
    downloadTimelineReportPdf: vi.fn(),
    downloadReportFormat: vi.fn(),
    createMonitoring: vi.fn(),
    addCompanyTag: vi.fn(),
    removeCompanyTag: vi.fn(),
    upsertCompanyNote: vi.fn(),
  },
  downloadBlob: vi.fn(),
}));

vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

function renderPage(companyId = COMPANY_ID) {
  return render(
    <MemoryRouter initialEntries={[`/company/${companyId}`]}>
      <Routes>
        <Route path="/company/:id" element={<CompanyDetailComponent />} />
      </Routes>
    </MemoryRouter>,
  );
}

let CompanyDetailComponent: React.ComponentType;

describe("CompanyDetail — Evolutie Scor foloseste UUID-ul companiei", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import("../pages/CompanyDetail");
    CompanyDetailComponent = mod.default;
  });

  it("apeleaza api.getScoreTrend cu UUID-ul companiei (string), NU cu NaN", async () => {
    const { api } = await import("@/lib/api");
    renderPage();

    await waitFor(() => {
      expect(api.getScoreTrend).toHaveBeenCalled();
    });

    // Bug-ul reparat: Number(uuid) -> NaN. Regresia s-ar manifesta ca un
    // call cu NaN in loc de UUID-ul real.
    expect(api.getScoreTrend).toHaveBeenCalledWith(COMPANY_ID);
    expect(api.getScoreTrend).not.toHaveBeenCalledWith(NaN);
  });
});
