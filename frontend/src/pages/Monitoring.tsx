import { useEffect, useState, useMemo } from "react";
import { Bell, BellOff, Trash2, RefreshCw, Plus, History } from "lucide-react";
import clsx from "clsx";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { logAction } from "@/lib/logger";

interface MonitoringAlert {
  id: string;
  company_id: string;
  company_name: string;
  cui: string;
  alert_type: string;
  is_active: boolean;
  check_frequency: string;
  last_checked_at: string | null;
  telegram_notify: boolean;
}

// F2-9: Mapare frecventa la eticheta lizibila
const FREQUENCY_LABELS: Record<string, string> = {
  "6h": "La 6h",
  "12h": "La 12h",
  "24h": "Zilnic",
  "168h": "Saptamanal",
};

interface CompanyOption {
  id: string;
  name: string;
  cui: string;
}

interface HistoryEntry {
  id?: string;
  company_id?: string;
  company_name?: string;
  message?: string;
  severity?: string;
  triggered_at?: string;
  created_at?: string;
}

type HistoryFilter = "zi" | "saptamana" | "toate";

export default function Monitoring() {
  const { toast } = useToast();
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState("");
  // F2-9: Frecventa de verificare configurabila
  const [frequency, setFrequency] = useState("6h");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyFilter, setHistoryFilter] =
    useState<HistoryFilter>("saptamana");

  const loadData = async () => {
    try {
      const [alertsRes, companiesRes, historyRes] = await Promise.all([
        api.listMonitoring(),
        api.listCompanies({ limit: 100 }),
        api.getMonitoringHistory(50).catch(() => ({ history: [] })),
      ]);
      setAlerts((alertsRes as { alerts: MonitoringAlert[] }).alerts || []);
      setCompanies(
        (companiesRes.companies || []) as unknown as CompanyOption[],
      );
      setHistory((historyRes.history ?? []) as HistoryEntry[]);
      logAction("Monitoring", "loaded", {
        alerts: (alertsRes as { alerts: unknown[] }).alerts?.length,
      });
    } catch {
      toast("Eroare la incarcarea datelor de monitorizare", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const addAlert = async () => {
    if (!selectedCompany) return;
    logAction("Monitoring", "addAlert", {
      companyId: selectedCompany,
      frequency,
    });
    try {
      // F2-9: Pasam frecventa selectata
      await api.createMonitoring({
        company_id: selectedCompany,
        check_frequency: frequency,
      });
      setSelectedCompany("");
      loadData();
    } catch {
      toast("Eroare la adaugarea alertei", "error");
    }
  };

  // C25 fix: Add try/catch to toggle and delete
  const toggleAlert = async (id: string) => {
    try {
      await api.toggleMonitoring(id);
      loadData();
    } catch {
      toast("Eroare la schimbarea starii alertei", "error");
    }
  };

  const deleteAlert = async (id: string) => {
    logAction("Monitoring", "deleteAlert", { alertId: id });
    try {
      await api.deleteMonitoring(id);
      loadData();
      toast("Alerta stearsa", "success");
    } catch {
      toast("Eroare la stergerea alertei", "error");
    }
  };

  const checkNow = async () => {
    setChecking(true);
    logAction("Monitoring", "checkNow");
    try {
      const data = (await api.checkMonitoringNow()) as {
        checked: number;
        alerts_triggered: number;
      };
      toast(
        `Verificare completa: ${data.checked} firme, ${data.alerts_triggered} alerte`,
        "success",
      );
      loadData();
    } catch {
      toast("Eroare la verificarea monitorizarii", "error");
    } finally {
      setChecking(false);
    }
  };

  // Filtrare istoric alerte
  const filteredHistory = useMemo(() => {
    if (historyFilter === "toate") return history;
    const now = Date.now();
    const cutoff =
      historyFilter === "zi" ? now - 86400_000 : now - 7 * 86400_000;
    return history.filter((h) => {
      const ts = h.triggered_at || h.created_at || "";
      if (!ts) return false;
      return new Date(ts).getTime() >= cutoff;
    });
  }, [history, historyFilter]);

  // Firme disponibile (care nu au deja monitorizare)
  const monitoredIds = new Set(alerts.map((a) => a.company_id));
  const availableCompanies = companies.filter((c) => !monitoredIds.has(c.id));

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-dark-card rounded w-48" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Monitorizare Firme</h1>
          <p className="text-sm text-gray-500 mt-1">
            Primesti alerta cand se schimba ceva la firmele monitorizate
          </p>
        </div>
        <button
          onClick={checkNow}
          disabled={checking || alerts.length === 0}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <RefreshCw className={clsx("w-4 h-4", checking && "animate-spin")} />
          {checking ? "Se verifica..." : "Verifica acum"}
        </button>
      </div>

      {/* Add new */}
      {availableCompanies.length > 0 && (
        <div className="card flex flex-wrap items-center gap-3">
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className="flex-1 min-w-[200px] bg-dark-surface border border-dark-border rounded-lg px-3 py-2
                       text-white text-sm focus:border-accent-primary focus:outline-none"
          >
            <option value="">Selecteaza firma de monitorizat...</option>
            {availableCompanies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} (CUI {c.cui})
              </option>
            ))}
          </select>
          {/* F2-9: Select frecventa verificare */}
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2
                       text-white text-sm focus:border-accent-primary focus:outline-none"
            title="Frecventa de verificare"
          >
            <option value="6h">La 6 ore</option>
            <option value="12h">La 12 ore</option>
            <option value="24h">Zilnic</option>
            <option value="168h">Saptamanal</option>
          </select>
          <button
            onClick={addAlert}
            disabled={!selectedCompany}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <Plus className="w-4 h-4" /> Adauga
          </button>
        </div>
      )}

      {/* Alerts list */}
      {alerts.length === 0 ? (
        <div className="card text-center py-12">
          <Bell className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">Nicio firma monitorizata</p>
          <p className="text-gray-600 text-sm mt-1">
            Ruleaza o analiza mai intai, apoi adauga firma aici
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={clsx(
                "card flex items-center justify-between",
                !alert.is_active && "opacity-50",
              )}
            >
              <div className="flex items-center gap-3">
                {alert.is_active ? (
                  <Bell className="w-5 h-5 text-green-400" />
                ) : (
                  <BellOff className="w-5 h-5 text-gray-600" />
                )}
                <div>
                  <p className="text-sm font-medium text-white">
                    {alert.company_name || "N/A"}
                  </p>
                  <p className="text-xs text-gray-500">
                    CUI {alert.cui} |{" "}
                    {FREQUENCY_LABELS[alert.check_frequency] ||
                      alert.check_frequency}
                    {alert.last_checked_at &&
                      ` | Ultima verificare: ${new Date(alert.last_checked_at).toLocaleDateString("ro-RO")}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleAlert(alert.id)}
                  className={clsx(
                    "text-xs px-2 py-1 rounded",
                    alert.is_active
                      ? "bg-green-500/20 text-green-400"
                      : "bg-gray-500/20 text-gray-400",
                  )}
                >
                  {alert.is_active ? "Activ" : "Inactiv"}
                </button>
                <button
                  onClick={() => deleteAlert(alert.id)}
                  className="p-1.5 text-gray-600 hover:text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Istoric Alerte */}
      <div className="space-y-3 mt-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-accent-secondary" />
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Istoric Alerte
            </h2>
          </div>
          <div className="flex gap-1">
            {(["zi", "saptamana", "toate"] as HistoryFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setHistoryFilter(f)}
                className={clsx(
                  "text-xs px-2.5 py-1 rounded transition-colors",
                  historyFilter === f
                    ? "bg-accent-primary/20 text-accent-secondary border border-accent-primary/30"
                    : "bg-dark-surface text-gray-500 border border-dark-border hover:text-gray-300",
                )}
              >
                {f === "zi"
                  ? "Ultima zi"
                  : f === "saptamana"
                    ? "Ultima saptamana"
                    : "Toate"}
              </button>
            ))}
          </div>
        </div>

        {filteredHistory.length === 0 ? (
          <div className="card text-center py-8">
            <History className="w-8 h-8 text-gray-700 mx-auto mb-2" />
            <p className="text-gray-600 text-sm">
              Niciun eveniment in intervalul selectat
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredHistory.map((entry, i) => {
              const sev = (entry.severity || "").toUpperCase();
              const severityClass =
                sev === "RED"
                  ? "text-red-400 bg-red-500/10 border border-red-500/20"
                  : sev === "YELLOW"
                    ? "text-yellow-400 bg-yellow-500/10 border border-yellow-500/20"
                    : "text-green-400 bg-green-500/10 border border-green-500/20";
              const ts = entry.triggered_at || entry.created_at || "";
              return (
                <div
                  key={entry.id || i}
                  className="card flex items-start gap-3 py-3"
                >
                  <span
                    className={clsx(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 mt-0.5",
                      severityClass,
                    )}
                  >
                    {sev || "INFO"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300 font-medium">
                      {entry.company_name ||
                        `Companie ${entry.company_id?.slice(0, 8) || "N/A"}`}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                      {entry.message || "—"}
                    </p>
                  </div>
                  {ts && (
                    <span className="text-[10px] text-gray-600 shrink-0 whitespace-nowrap">
                      {new Date(ts).toLocaleDateString("ro-RO", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
