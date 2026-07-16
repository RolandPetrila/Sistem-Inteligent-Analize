/**
 * Test pentru butonul "Reia CUI-urile esuate" din BatchAnalysis — cableaza
 * POST /api/batch/{id}/resume (api.resumeBatch), endpoint functional dar fara
 * niciun call-site in UI inainte de acest fix.
 *
 * Seteaza direct localStorage['ris_active_batch'] pentru a randa panoul de
 * progres batch (evita drive-ul complet al upload-ului CSV), apoi verifica
 * click -> apel real -> reactia UI (toast + polling repornit).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

const toastMock = vi.fn();

const errorBatchStatus = {
  batch_id: "batch-xyz",
  status: "ERROR",
  progress_percent: 60,
  current_step: "Batch oprit — eroare",
  total: 5,
  completed: 3,
  failed: 2,
  current_cui: "",
};

vi.mock("@/lib/api", () => ({
  api: {
    getBatchStatus: vi.fn(() => Promise.resolve(errorBatchStatus)),
    resumeBatch: vi.fn(() =>
      Promise.resolve({
        batch_id: "batch-xyz",
        resumed: 2,
        cuis: ["11111111", "22222222"],
        status: "resuming",
      }),
    ),
    uploadBatch: vi.fn(),
    previewBatch: vi.fn(),
  },
}));

vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));

vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

let BatchAnalysisComponent: React.ComponentType;

describe("BatchAnalysis — Reia CUI-uri esuate", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    localStorage.setItem("ris_active_batch", "batch-xyz");
    vi.resetModules();
    const mod = await import("../pages/BatchAnalysis");
    BatchAnalysisComponent = mod.default;
  });

  it("randeaza butonul de resume cand batch-ul e ERROR cu CUI-uri esuate", async () => {
    const { findByRole } = render(<BatchAnalysisComponent />);
    const button = await findByRole("button", {
      name: /Reia CUI-urile esuate \(2\)/i,
    });
    expect(button).toBeTruthy();
  });

  it("click apeleaza api.resumeBatch cu id-ul batch-ului si arata toast de succes", async () => {
    const { api } = await import("@/lib/api");
    const { findByRole } = render(<BatchAnalysisComponent />);

    const button = await findByRole("button", {
      name: /Reia CUI-urile esuate \(2\)/i,
    });
    fireEvent.click(button);

    await waitFor(() => {
      expect(api.resumeBatch).toHaveBeenCalledWith("batch-xyz");
    });
    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.stringMatching(/Se reiau 2 CUI-uri esuate/i),
        "success",
      );
    });
  });

  it("eroare la resume: arata toast de eroare, nu buton mort", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.resumeBatch).mockRejectedValueOnce(new Error("fail"));
    const { findByRole } = render(<BatchAnalysisComponent />);

    const button = await findByRole("button", {
      name: /Reia CUI-urile esuate \(2\)/i,
    });
    fireEvent.click(button);

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.stringMatching(/Eroare la reluarea batch-ului/i),
        "error",
      );
    });
  });
});
