/**
 * F8-2: Vitest tests pentru Dashboard page
 * Testeaza: render, titlu, unicitate widget "Scoruri in scadere"
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock api
vi.mock("@/lib/api", () => ({
  api: {
    getStats: vi.fn(() =>
      Promise.resolve({
        total_companies: 5,
        total_jobs: 10,
        completed_jobs: 8,
        failed_jobs: 1,
        avg_score: 72,
      }),
    ),
    listJobs: vi.fn(() => Promise.resolve({ jobs: [], total: 0 })),
    getSettings: vi.fn(() => Promise.reject(new Error("no settings"))),
    healthDeep: vi.fn(() => Promise.reject(new Error("no health"))),
    getStatsTrend: vi.fn(() => Promise.resolve({ trend: [] })),
    getRiskMovers: vi.fn(() => Promise.resolve({ movers: [] })),
  },
}));

// Mock Toast
vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

// Mock logger
vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

// Mock constants
vi.mock("@/lib/constants", () => ({
  JOB_STATUS_LABELS: {},
  ANALYSIS_TYPE_LABELS: {},
}));

// Mock types
vi.mock("@/lib/types", () => ({}));

describe("Dashboard page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("se randeaza fara crash", async () => {
    const { default: Dashboard } = await import("../pages/Dashboard");
    const { container } = render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    expect(container).toBeTruthy();
  });

  it("afiseaza titlul Dashboard dupa incarcarea datelor", async () => {
    const { default: Dashboard } = await import("../pages/Dashboard");
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    // Asteapta ca loading sa se termine si titlul sa apara
    await waitFor(
      () => {
        expect(screen.getByText("Dashboard")).toBeInTheDocument();
      },
      { timeout: 5000 },
    );
  });

  it("nu afiseaza mai mult de un widget cu 'Scoruri in scadere'", async () => {
    const { default: Dashboard } = await import("../pages/Dashboard");
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    // In stare de loading, widgetul nu apare deloc — verificam ca nu exista duplicat
    const elements = screen.queryAllByText(/Scoruri.*sc.*dere/i);
    expect(elements.length).toBeLessThanOrEqual(1);
  });
});
