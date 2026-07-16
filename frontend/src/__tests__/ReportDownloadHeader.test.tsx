/**
 * BUG (raportat de utilizator, 2026-07-16): click pe formatele de descarcare
 * ale unui raport deschidea un tab cu JSON brut
 * {"detail":"API key invalid sau lipsa. Trimite header X-RIS-Key."}.
 *
 * Cauza-radacina: butoanele erau <a href="/api/reports/{id}/download/{fmt}">
 * — navigare de BROWSER, care NU poate atasa header-e HTTP. RIS_API_KEY e
 * activ din 2026-07-12, deci ApiKeyMiddleware respinge orice /api/* fara
 * X-RIS-Key cu 401 — exact ce lovea orice click din UI.
 *
 * Fix: fetch() + risHeaders() + Blob (api.downloadReportFormat), acelasi
 * tipar deja folosit de api.ts::exportCompaniesCSV / ReportView.tsx (.ics).
 *
 * Acest test verifica DOUA lucruri, cerute explicit:
 * 1. Click pe un buton de format trimite request-ul cu header-ul X-RIS-Key
 *    real (cel din frontend/.env, citit de api.ts la import).
 * 2. Niciuna din cele 4 componente atinse de fix nu mai contine un
 *    `<a href="/api/...">` catre un endpoint de download (scan static pe
 *    sursa fisierului — string-ul `/api/` langa `href` NU mai exista).
 *
 * Non-vacuitate: pe codul dinainte de fix (ReportHeader randa <a href=...>),
 * acest test PICA — verificat cu `git stash` (vezi raportul agentului).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ReportHeader } from "@/components/report/ReportHeader";
// `?raw` (typed by vite/client.d.ts, no Node fs/path needed) — reads the real
// source of each touched component so the scan below can't drift from what
// actually ships.
import ReportHeaderSource from "@/components/report/ReportHeader.tsx?raw";
import ReportsListSource from "@/pages/ReportsList.tsx?raw";
import CompanyDetailSource from "@/pages/CompanyDetail.tsx?raw";
import BatchAnalysisSource from "@/pages/BatchAnalysis.tsx?raw";

const toastMock = vi.fn();
vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));
vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

const baseReport = {
  id: "test-report-id",
  job_id: "test-job-id",
  report_type: "FULL_COMPANY_PROFILE",
  report_level: 2,
  title: "Test Raport SRL",
  created_at: "2026-01-01T00:00:00",
  formats_available: ["pdf"],
  sources: [],
};

function renderHeader() {
  return render(
    <MemoryRouter>
      <ReportHeader
        report={baseReport}
        hasDelta={null}
        riskScore={undefined}
        riskColor=""
        reanalyzing={false}
        onReanalyze={() => {}}
        onEmailOpen={() => {}}
      />
    </MemoryRouter>,
  );
}

describe("ReportHeader — descarcare format trimite X-RIS-Key (fix bug 401)", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    toastMock.mockClear();
    fetchMock = vi.fn().mockResolvedValue(
      new Response(new Blob(["continut-fals-pdf"]), {
        status: 200,
        headers: {
          "Content-Disposition": "attachment; filename*=UTF-8''raport_real.pdf",
        },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    // jsdom nu implementeaza URL.createObjectURL/revokeObjectURL
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:mock-url"),
      revokeObjectURL: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("NU mai exista niciun element <a> care navigheaza direct la /api/", () => {
    const { container } = renderHeader();
    const anchors = Array.from(container.querySelectorAll("a"));
    const apiAnchors = anchors.filter((a) =>
      (a.getAttribute("href") || "").includes("/api/"),
    );
    expect(apiAnchors).toHaveLength(0);
  });

  it("click pe butonul PDF cheama fetch cu URL-ul corect si header-ul X-RIS-Key real", async () => {
    const { findByRole } = renderHeader();
    const button = await findByRole("button", { name: /PDF/i });
    fireEvent.click(button);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/reports/test-report-id/download/pdf");

    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers).toBeDefined();
    // Valoarea reala e cea din frontend/.env (VITE_RIS_API_KEY), citita de
    // api.ts la import — comparam cu ea, nu cu un string fix, ca testul sa nu
    // depinda de/nu expuna cheia locala de dezvoltare.
    expect(headers!["X-RIS-Key"]).toBe(
      (import.meta as unknown as { env: Record<string, string | undefined> })
        .env.VITE_RIS_API_KEY,
    );
    expect(headers!["X-RIS-Key"]).toBeTruthy();
  });

  it("fetch esuat (401) arata toast de eroare in romana, nu JSON brut", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: "API key invalid sau lipsa. Trimite header X-RIS-Key.",
        }),
        { status: 401 },
      ),
    );
    const { findByRole } = renderHeader();
    const button = await findByRole("button", { name: /PDF/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.stringMatching(/Eroare la descarcarea formatului PDF/i),
        "error",
      );
    });
  });
});

describe("Scan static — nicio componenta atinsa nu mai are <a href> direct catre /api/download", () => {
  const sources: [string, string][] = [
    ["ReportHeader.tsx", ReportHeaderSource],
    ["ReportsList.tsx", ReportsListSource],
    ["CompanyDetail.tsx", CompanyDetailSource],
    ["BatchAnalysis.tsx", BatchAnalysisSource],
  ];

  it.each(sources)(
    "%s nu contine href catre /api/ (navigare de browser fara header)",
    (_name, source) => {
      // Comentariile din fix (adaugate de acest patch) documenteaza in proza
      // exact pattern-ul vechi buggy ("// <a href=\"/api/...\"> is a plain
      // browser navigation") — le eliminam inainte de scan ca sa nu se
      // auto-declanseze pe propria lor documentatie. Codul JSX real ramane.
      const codeOnly = source
        .split("\n")
        .filter((line) => !line.trim().startsWith("//"))
        .join("\n");
      // Pattern-ul exact al bug-ului: href={`/api/... sau href="/api/...
      const hasDirectApiHref = /href=[{"]`?\/api\//.test(codeOnly);
      expect(hasDirectApiHref).toBe(false);
    },
  );
});
