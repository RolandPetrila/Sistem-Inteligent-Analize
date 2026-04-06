import { useEffect, useState } from "react";
import {
  Bell,
  Mail,
  Save,
  Loader2,
  CheckCircle,
  XCircle,
  Send,
  Cpu,
  Eye,
  EyeOff,
  Copy,
  FlaskConical,
} from "lucide-react";
import { requestNotificationPermission, getNotificationPermission, isNotificationSupported } from "@/lib/notifications";
import clsx from "clsx";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { logAction, getLogBuffer } from "@/lib/logger";

interface SettingsData {
  fields: Record<string, string>;
  synthesis_mode: string;
  has_tavily: boolean;
  has_gemini: boolean;
  has_telegram: boolean;
  has_email: boolean;
}

const FIELD_CONFIG: {
  key: string;
  label: string;
  placeholder: string;
  type: string;
  group: string;
  hint?: string;
}[] = [
  { key: "TAVILY_API_KEY", label: "Tavily API Key", placeholder: "tvly-...", type: "password", group: "api", hint: "Web search (1000 req/luna gratuit)" },
  { key: "GOOGLE_AI_API_KEY", label: "Google AI Key (Gemini)", placeholder: "AIza...", type: "password", group: "api", hint: "Fallback AI autonom (gratuit)" },
  { key: "SYNTHESIS_MODE", label: "Mod Synthesis", placeholder: "claude_code", type: "text", group: "api", hint: "claude_code | autonomous" },
  { key: "TELEGRAM_BOT_TOKEN", label: "Bot Token", placeholder: "123456:ABC-...", type: "password", group: "telegram" },
  { key: "TELEGRAM_CHAT_ID", label: "Chat ID", placeholder: "123456789", type: "text", group: "telegram" },
  { key: "GMAIL_USER", label: "Gmail Address", placeholder: "user@gmail.com", type: "email", group: "email" },
  { key: "GMAIL_APP_PASSWORD", label: "App Password", placeholder: "xxxx xxxx xxxx xxxx", type: "password", group: "email" },
];

export default function Settings() {
  const { toast } = useToast();
  const [data, setData] = useState<SettingsData | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [integrationTests, setIntegrationTests] = useState<Record<string, { status: "loading" | "ok" | "fail"; message?: string }>>({});
  const [serviceTests, setServiceTests] = useState<Record<string, { ok: boolean; message: string } | null>>({});
  const [notifPermission, setNotifPermission] = useState(getNotificationPermission());

  useEffect(() => {
    api.getSettings()
      .then((d) => {
        setData(d as unknown as SettingsData);
        setFields((d as unknown as SettingsData).fields);
        logAction("Settings", "loaded");
      })
      .catch(() => toast("Eroare la incarcarea setarilor", "error"));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    logAction("Settings", "save");
    try {
      await api.updateSettings(fields);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      toast("Eroare la salvarea setarilor", "error");
    } finally {
      setSaving(false);
    }
  };

  // Generic integration test using /health/deep endpoint
  const handleTestIntegration = async (name: string) => {
    setIntegrationTests((prev) => ({ ...prev, [name]: { status: "loading" } }));
    logAction("Settings", "testIntegration", { name });
    try {
      const health = await api.healthDeep() as Record<string, unknown>;
      // Map integration name to health key
      const keyMap: Record<string, string> = {
        "api": "ai_providers",
        "tavily": "search",
        "telegram": "notifications",
        "email": "email",
      };
      const healthKey = keyMap[name] || name;
      const status = health[healthKey] as Record<string, unknown> | undefined;
      if (status && status.status === "ok") {
        setIntegrationTests((prev) => ({ ...prev, [name]: { status: "ok", message: "Conectat" } }));
      } else if (status) {
        const errMsg = (status.error as string) || (status.status as string) || "Indisponibil";
        setIntegrationTests((prev) => ({ ...prev, [name]: { status: "fail", message: errMsg } }));
      } else {
        // Try to find status in nested keys
        const dbStatus = health.database as Record<string, unknown> | undefined;
        if (name === "api" && dbStatus?.status === "ok") {
          setIntegrationTests((prev) => ({ ...prev, [name]: { status: "ok", message: "Backend OK" } }));
        } else {
          setIntegrationTests((prev) => ({ ...prev, [name]: { status: "fail", message: "Nedetectat in health" } }));
        }
      }
    } catch {
      setIntegrationTests((prev) => ({ ...prev, [name]: { status: "fail", message: "Eroare conexiune" } }));
    }
  };

  const handleTestTelegram = async () => {
    setTestResult(null);
    logAction("Settings", "testTelegram");
    try {
      const d = await api.testTelegram();
      setTestResult(d.success ? "Mesaj trimis cu succes!" : "Trimitere esuata");
    } catch {
      setTestResult("Eroare conexiune");
    }
  };

  const handleTestService = async (service: string) => {
    setServiceTests((prev) => ({ ...prev, [service]: null }));
    logAction("Settings", "testService", { service });
    try {
      const result = await api.testService(service);
      setServiceTests((prev) => ({ ...prev, [service]: result }));
    } catch {
      setServiceTests((prev) => ({ ...prev, [service]: { ok: false, message: "Eroare conexiune" } }));
    }
  };

  const renderGroup = (
    groupKey: string,
    title: string,
    icon: React.ReactNode
  ) => (
    <div className="card space-y-4">
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <h2 className="font-semibold text-white">{title}</h2>
        {groupKey === "api" && data && (
          <div className="flex gap-2 ml-auto">
            {data.has_tavily && (
              <span className="text-[10px] bg-green-500/10 text-green-400 px-2 py-0.5 rounded">
                Tavily OK
              </span>
            )}
            {data.has_gemini && (
              <span className="text-[10px] bg-green-500/10 text-green-400 px-2 py-0.5 rounded">
                Gemini OK
              </span>
            )}
          </div>
        )}
      </div>
      {FIELD_CONFIG.filter((f) => f.group === groupKey).map((field) => {
        const isPassword = field.type === "password";
        const isVisible = visibleKeys.has(field.key);
        // Servicii testabile individual per camp
        const serviceMap: Record<string, string> = {
          GROQ_API_KEY: "groq",
          GOOGLE_AI_API_KEY: "gemini",
          TAVILY_API_KEY: "tavily",
          TELEGRAM_BOT_TOKEN: "telegram",
        };
        const testServiceKey = serviceMap[field.key];
        const svcResult = testServiceKey ? serviceTests[testServiceKey] : undefined;
        return (
          <div key={field.key}>
            <label className="block text-sm text-gray-400 mb-1">
              {field.label}
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type={isPassword && !isVisible ? "password" : "text"}
                  className={clsx("input-field w-full", isPassword && "pr-10")}
                  placeholder={field.placeholder}
                  value={fields[field.key] || ""}
                  onChange={(e) =>
                    setFields({ ...fields, [field.key]: e.target.value })
                  }
                />
                {isPassword && fields[field.key] && (
                  <button
                    type="button"
                    onClick={() => {
                      const next = new Set(visibleKeys);
                      if (isVisible) next.delete(field.key);
                      else next.add(field.key);
                      setVisibleKeys(next);
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500
                               hover:text-gray-300 transition-colors p-1"
                    title={isVisible ? "Ascunde" : "Arata"}
                  >
                    {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                )}
              </div>
              {testServiceKey && (
                <button
                  type="button"
                  onClick={() => handleTestService(testServiceKey)}
                  disabled={svcResult === null}
                  className="btn-secondary text-xs px-2 py-1.5 flex items-center gap-1 shrink-0"
                  title={`Testeaza ${testServiceKey}`}
                >
                  {svcResult === null ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <FlaskConical className="w-3 h-3" />
                  )}
                  Test
                </button>
              )}
            </div>
            {/* Rezultat test serviciu individual */}
            {testServiceKey && svcResult !== undefined && svcResult !== null && (
              <p className={clsx("text-xs mt-1 flex items-center gap-1", svcResult.ok ? "text-green-400" : "text-red-400")}>
                {svcResult.ok ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                {svcResult.message}
              </p>
            )}
            {field.hint && (
              <p className="text-xs text-gray-600 mt-1">{field.hint}</p>
            )}
          </div>
        );
      })}
      {groupKey === "telegram" && (
        <button
          onClick={handleTestTelegram}
          className="btn-secondary text-sm flex items-center gap-2"
        >
          <Send className="w-3.5 h-3.5" /> Test Telegram
        </button>
      )}
      {groupKey === "telegram" && testResult && (
        <p
          className={clsx(
            "text-xs",
            testResult.includes("succes") ? "text-green-400" : "text-red-400"
          )}
        >
          {testResult}
        </p>
      )}

      {/* Test integration via /health/deep */}
      <div className="flex items-center gap-3 pt-2 border-t border-dark-border/50">
        <button
          onClick={() => handleTestIntegration(groupKey)}
          disabled={integrationTests[groupKey]?.status === "loading"}
          className="btn-secondary text-sm flex items-center gap-2"
        >
          {integrationTests[groupKey]?.status === "loading" ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <FlaskConical className="w-3.5 h-3.5" />
          )}
          Testeaza
        </button>
        {integrationTests[groupKey]?.status === "ok" && (
          <span className="flex items-center gap-1 text-xs text-green-400">
            <CheckCircle className="w-3.5 h-3.5" /> {integrationTests[groupKey].message}
          </span>
        )}
        {integrationTests[groupKey]?.status === "fail" && (
          <span className="flex items-center gap-1 text-xs text-red-400">
            <XCircle className="w-3.5 h-3.5" /> {integrationTests[groupKey].message}
          </span>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Configurare</h1>
          <p className="text-sm text-gray-500 mt-1">
            Setari sistem si chei API
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center gap-2"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saved ? "Salvat!" : "Salveaza"}
        </button>
      </div>

      {renderGroup("api", "AI & Search", <Cpu className="w-5 h-5 text-accent-secondary" />)}
      {renderGroup("telegram", "Notificari Telegram", <Bell className="w-5 h-5 text-accent-secondary" />)}
      {renderGroup("email", "Email (Gmail SMTP)", <Mail className="w-5 h-5 text-accent-secondary" />)}

      {/* Status */}
      {data && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
            Status Integrari
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Tavily Search", ok: data.has_tavily },
              { label: "Gemini AI", ok: data.has_gemini },
              { label: "Telegram", ok: data.has_telegram },
              { label: "Email", ok: data.has_email },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center gap-2 text-sm"
              >
                {item.ok ? (
                  <CheckCircle className="w-4 h-4 text-green-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-gray-600" />
                )}
                <span className={item.ok ? "text-gray-300" : "text-gray-600"}>
                  {item.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* F3-9: Notificari Browser */}
      {isNotificationSupported() && (
        <div className="card space-y-3">
          <h3 className="text-sm font-semibold text-gray-400 uppercase">Notificari Browser</h3>
          <p className="text-xs text-gray-500">
            Primeste notificari native cand o analiza se finalizeaza, chiar daca tab-ul e minimizat.
          </p>
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2 py-1 rounded-full ${
              notifPermission === "granted" ? "bg-green-500/20 text-green-400" :
              notifPermission === "denied" ? "bg-red-500/20 text-red-400" :
              "bg-gray-500/20 text-gray-400"
            }`}>
              {notifPermission === "granted" ? "Active" : notifPermission === "denied" ? "Blocate" : "Neactivate"}
            </span>
            {notifPermission !== "granted" && notifPermission !== "denied" && (
              <button
                onClick={async () => {
                  const ok = await requestNotificationPermission();
                  setNotifPermission(ok ? "granted" : "denied");
                  if (ok) toast("Notificari browser activate!", "success");
                }}
                className="btn-secondary text-sm"
              >
                Activeaza Notificari
              </button>
            )}
          </div>
        </div>
      )}

      {/* G5: Buton copiaza loguri frontend */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
          Diagnostice
        </h3>
        <button
          onClick={() => {
            const logs = getLogBuffer();
            if (logs) {
              navigator.clipboard.writeText(logs).then(
                () => toast("Loguri copiate in clipboard!", "success"),
                () => toast("Nu s-au putut copia logurile", "error"),
              );
            } else {
              toast("Nu exista loguri in aceasta sesiune", "info");
            }
          }}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <Copy className="w-4 h-4" />
          Copiaza loguri sesiune
        </button>
        <p className="text-xs text-gray-600 mt-2">
          Copiaza logurile din sesiunea curenta in clipboard. Utile pentru depanare.
        </p>
      </div>
    </div>
  );
}
