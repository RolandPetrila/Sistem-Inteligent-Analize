/**
 * F4-4: Vitest tests pentru Monitoring page — buton "Suprima alerta"
 * Verifica: randare componenta reala, click deschide formularul, submit
 * apeleaza api.suppressAlert cu payload-ul corect + toast succes, esec API
 * arata toast eroare (nu buton mort).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const toastMock = vi.fn();

// Mock api — alerta unica, activa, fara suppressed_until (varianta "curata")
vi.mock("@/lib/api", () => ({
  api: {
    listMonitoring: vi.fn(() =>
      Promise.resolve({
        alerts: [
          {
            id: "alert-1",
            company_id: "company-1",
            company_name: "Test Firma SRL",
            cui: "12345678",
            alert_type: "all",
            is_active: true,
            check_frequency: "6h",
            last_checked_at: null,
            telegram_notify: true,
            suppressed_until: null,
            suppress_reason: null,
          },
        ],
      }),
    ),
    listCompanies: vi.fn(() => Promise.resolve({ companies: [], total: 0 })),
    getMonitoringHistory: vi.fn(() => Promise.resolve({ history: [] })),
    toggleMonitoring: vi.fn(() => Promise.resolve({})),
    deleteMonitoring: vi.fn(() => Promise.resolve({})),
    checkMonitoringNow: vi.fn(() =>
      Promise.resolve({ checked: 0, alerts_triggered: 0 }),
    ),
    createMonitoring: vi.fn(() => Promise.resolve({})),
    getMonitoringAuditLog: vi.fn(() =>
      Promise.resolve({ alert_id: "alert-1", audit_log: [] }),
    ),
    suppressAlert: vi.fn(() =>
      Promise.resolve({
        alert_id: "alert-1",
        suppressed_until: "2026-08-01T00:00:00",
        reason: "verificare manuala facuta",
        status: "suppressed",
      }),
    ),
  },
}));

// Mock Toast
vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));

// Mock logger
vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

describe("Monitoring page — suprimare alerta", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("se randeaza fara crash si afiseaza alerta", async () => {
    const { default: Monitoring } = await import("../pages/Monitoring");
    render(<Monitoring />);
    expect(await screen.findByText("Test Firma SRL")).toBeInTheDocument();
  });

  it("click pe butonul de suprimare deschide formularul cu motiv + data", async () => {
    const user = userEvent.setup();
    const { default: Monitoring } = await import("../pages/Monitoring");
    render(<Monitoring />);
    await screen.findByText("Test Firma SRL");

    const suppressBtn = screen.getByTitle("Suprima alerta");
    await user.click(suppressBtn);

    expect(screen.getByLabelText(/Motiv suprimare/i)).toBeInTheDocument();
    expect(screen.getByText(/Confirma suprimarea/i)).toBeInTheDocument();
  });

  it("submit fara motiv arata toast eroare si NU apeleaza api.suppressAlert", async () => {
    const { api } = await import("@/lib/api");
    const user = userEvent.setup();
    const { default: Monitoring } = await import("../pages/Monitoring");
    render(<Monitoring />);
    await screen.findByText("Test Firma SRL");

    await user.click(screen.getByTitle("Suprima alerta"));
    await user.click(screen.getByText(/Confirma suprimarea/i));

    expect(api.suppressAlert).not.toHaveBeenCalled();
    expect(toastMock).toHaveBeenCalledWith(
      expect.stringMatching(/motiv/i),
      "error",
    );
  });

  it("submit cu motiv + data cheama api.suppressAlert cu payload-ul corect si arata toast succes", async () => {
    const { api } = await import("@/lib/api");
    const user = userEvent.setup();
    const { default: Monitoring } = await import("../pages/Monitoring");
    render(<Monitoring />);
    await screen.findByText("Test Firma SRL");

    await user.click(screen.getByTitle("Suprima alerta"));

    const reasonInput = screen.getByLabelText(/Motiv suprimare/i);
    await user.type(reasonInput, "verificare manuala facuta");

    const untilInput = screen.getByLabelText(/Suprima pana la/i);
    await user.type(untilInput, "2026-08-01");

    await user.click(screen.getByText(/Confirma suprimarea/i));

    expect(api.suppressAlert).toHaveBeenCalledWith("alert-1", {
      reason: "verificare manuala facuta",
      suppress_until: "2026-08-01T00:00:00",
    });
    expect(toastMock).toHaveBeenCalledWith(
      expect.stringMatching(/suprimata/i),
      "success",
    );
  });

  it("submit fara data optionala trimite suppress_until: null", async () => {
    const { api } = await import("@/lib/api");
    const user = userEvent.setup();
    const { default: Monitoring } = await import("../pages/Monitoring");
    render(<Monitoring />);
    await screen.findByText("Test Firma SRL");

    await user.click(screen.getByTitle("Suprima alerta"));
    await user.type(
      screen.getByLabelText(/Motiv suprimare/i),
      "firma in vacanta fiscala",
    );
    await user.click(screen.getByText(/Confirma suprimarea/i));

    expect(api.suppressAlert).toHaveBeenCalledWith("alert-1", {
      reason: "firma in vacanta fiscala",
      suppress_until: null,
    });
  });

  it("esec API la suprimare arata toast eroare (nu buton mort)", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.suppressAlert).mockRejectedValueOnce(new Error("500"));
    const user = userEvent.setup();
    const { default: Monitoring } = await import("../pages/Monitoring");
    render(<Monitoring />);
    await screen.findByText("Test Firma SRL");

    await user.click(screen.getByTitle("Suprima alerta"));
    await user.type(screen.getByLabelText(/Motiv suprimare/i), "motiv test");
    await user.click(screen.getByText(/Confirma suprimarea/i));

    await vi.waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.stringMatching(/eroare/i),
        "error",
      );
    });
    // formularul ramane deschis dupa esec (nu se inchide silentios)
    expect(screen.getByLabelText(/Motiv suprimare/i)).toBeInTheDocument();
  });
});
