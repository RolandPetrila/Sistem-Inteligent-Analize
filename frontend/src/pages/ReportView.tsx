import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  FileText,
  Shield,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";

interface ReportFull {
  id: string;
  job_id: string;
  report_type: string;
  report_level: number;
  title: string | null;
  summary: string | null;
  risk_score: string | null;
  created_at: string;
  formats_available: string[];
  full_data: {
    company?: Record<string, { value: unknown; trust: string; source: string }>;
    financial?: Record<string, unknown>;
    risk?: Record<string, unknown>;
    risk_score?: { score: string; factors: [string, string][]; recommendation: string };
    sources_used?: { name: string; level: number; status: string }[];
    [key: string]: unknown;
  } | null;
  sources: { source_name: string; source_url: string; status: string; data_found: boolean; response_time_ms: number }[];
}

export default function ReportView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [report, setReport] = useState<ReportFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);

  useEffect(() => {
    if (!id) return;
    api
      .getReport(id)
      .then((r) => setReport(r as unknown as ReportFull))
      .catch(() => toast("Eroare la incarcarea raportului", "error"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-dark-card rounded w-64" />
        <div className="h-64 bg-dark-card rounded-xl" />
      </div>
    );
  }

  if (!report) {
    return <p className="text-gray-500">Raportul nu a fost gasit.</p>;
  }

  const data = report.full_data;
  const riskScore = data?.risk_score as {
    score: string;
    numeric_score?: number;
    dimensions?: Record<string, { score: number; weight: number }>;
    factors: [string, string][];
    recommendation: string;
  } | undefined;
  const riskColor = {
    Verde: "text-risk-verde border-risk-verde/30 bg-risk-verde/5",
    Galben: "text-risk-galben border-risk-galben/30 bg-risk-galben/5",
    Rosu: "text-risk-rosu border-risk-rosu/30 bg-risk-rosu/5",
  }[riskScore?.score || ""] || "text-gray-400 border-dark-border bg-dark-card";

  const tabs = [
    { key: "overview", label: "Rezumat" },
    { key: "company", label: "Profil Firma" },
    { key: "risk", label: "Risc" },
    { key: "raw", label: "Date JSON" },
  ];

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/reports"
            className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 mb-2"
          >
            <ArrowLeft className="w-3 h-3" /> Inapoi la rapoarte
          </Link>
          <h1 className="text-xl font-bold text-white">
            {report.title || ANALYSIS_TYPE_LABELS[report.report_type] || "Raport"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Nivel {report.report_level} | {new Date(report.created_at).toLocaleDateString("ro-RO")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* E13: Re-analyze button */}
          <button
            onClick={async () => {
              if (reanalyzing) return;
              const cui = data?.company?.cui?.value || data?.company?.denumire?.value;
              if (!cui) { toast("CUI indisponibil pentru re-analiza", "error"); return; }
              setReanalyzing(true);
              try {
                const job = await api.createJob({
                  analysis_type: report.report_type as any,
                  report_level: report.report_level as any,
                  input_params: { cui: String(typeof cui === "object" ? "" : cui) },
                });
                await api.startJob(job.id);
                navigate(`/analysis/${job.id}`);
              } catch {
                toast("Eroare la pornirea re-analizei", "error");
                setReanalyzing(false);
              }
            }}
            disabled={reanalyzing}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <RefreshCw className={clsx("w-3.5 h-3.5", reanalyzing && "animate-spin")} />
            {reanalyzing ? "Se porneste..." : "Re-analiza"}
          </button>
          {report.formats_available.map((fmt) => (
            <a
              key={fmt}
              href={`/api/reports/${report.id}/download/${fmt}`}
              className="btn-secondary flex items-center gap-1.5 text-sm"
            >
              <Download className="w-3.5 h-3.5" />
              {fmt.toUpperCase()}
            </a>
          ))}
        </div>
      </div>

      {/* Risk Score Card */}
      {riskScore && (
        <div className={clsx("card border", riskColor)}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-6 h-6" />
              <div>
                <p className="text-lg font-bold">
                  Scor Risc: {riskScore.score}
                  {riskScore.numeric_score !== undefined && (
                    <span className="ml-2 text-2xl font-mono">
                      {riskScore.numeric_score}/100
                    </span>
                  )}
                </p>
                <p className="text-sm opacity-80">{riskScore.recommendation}</p>
              </div>
            </div>
          </div>

          {/* Dimensions breakdown */}
          {riskScore.dimensions && (
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(riskScore.dimensions).map(([key, dim]) => {
                const d = dim as { score: number; weight: number };
                const barColor = d.score >= 70 ? "bg-green-400" : d.score >= 40 ? "bg-yellow-400" : "bg-red-400";
                return (
                  <div key={key} className="bg-dark-surface/50 rounded-lg p-2">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[10px] text-gray-500 uppercase">{key} ({d.weight}%)</span>
                      <span className="text-xs font-mono text-gray-300">{d.score}</span>
                    </div>
                    <div className="w-full h-1.5 bg-dark-border rounded-full overflow-hidden">
                      <div
                        className={clsx("h-full rounded-full transition-all", barColor)}
                        style={{ width: `${d.score}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {riskScore.factors && riskScore.factors.length > 0 && (
            <div className="mt-3 space-y-1">
              {riskScore.factors.map(([factor, severity], i) => (
                <div key={i} className="text-xs flex items-center gap-2">
                  <span
                    className={clsx(
                      "px-1.5 py-0.5 rounded text-[10px] font-mono",
                      severity === "HIGH" && "bg-red-500/20 text-red-400",
                      severity === "MEDIUM" && "bg-yellow-500/20 text-yellow-400",
                      severity === "LOW" && "bg-blue-500/20 text-blue-400"
                    )}
                  >
                    {severity}
                  </span>
                  <span className="text-gray-400">{factor}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-dark-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={clsx(
              "px-4 py-2.5 text-sm font-medium transition-colors border-b-2",
              activeTab === tab.key
                ? "text-accent-secondary border-accent-primary"
                : "text-gray-500 border-transparent hover:text-gray-300"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="card min-h-[200px]">
        {activeTab === "overview" && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase">Rezumat</h3>
            <p className="text-gray-300">
              {report.summary || "Niciun rezumat disponibil."}
            </p>
          </div>
        )}

        {activeTab === "company" && data?.company && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">Profil Firma</h3>
            {Object.entries(data.company).map(([key, field]) => {
              if (!field || typeof field !== "object") return null;
              const f = field as { value: unknown; trust?: string; source?: string };
              return (
                <div key={key} className="flex justify-between py-2 border-b border-dark-border">
                  <span className="text-gray-500 text-sm">{key.replace(/_/g, " ")}</span>
                  <div className="text-right">
                    <span className="text-white text-sm">{String(f.value ?? "N/A")}</span>
                    {f.trust && (
                      <span
                        className={clsx(
                          "ml-2 text-[10px] font-mono",
                          f.trust === "OFICIAL" && "text-trust-oficial",
                          f.trust === "VERIFICAT" && "text-trust-verificat",
                          f.trust === "ESTIMAT" && "text-trust-estimat"
                        )}
                      >
                        [{f.trust}]
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "risk" && data?.risk && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">Evaluare Risc</h3>
            {Object.entries(data.risk).map(([key, field]) => {
              if (!field || typeof field !== "object") return null;
              const f = field as { value: unknown; trust?: string; note?: string };
              return (
                <div key={key} className="p-3 bg-dark-surface rounded-lg mb-2">
                  <p className="text-sm font-medium text-gray-300">{key.replace(/_/g, " ")}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {typeof f.value === "object"
                      ? JSON.stringify(f.value, null, 2).slice(0, 200)
                      : String(f.value)}
                  </p>
                  {f.note && <p className="text-[10px] text-gray-600 mt-1 italic">{f.note}</p>}
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "raw" && (
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">Date Verificate (JSON)</h3>
            <pre className="text-xs text-gray-400 bg-dark-surface p-4 rounded-lg overflow-auto max-h-96 font-mono">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Sources Audit Panel */}
      <div className="card">
        <button
          onClick={() => setSourcesOpen(!sourcesOpen)}
          className="flex items-center justify-between w-full"
        >
          <h3 className="text-sm font-semibold text-gray-400 uppercase">
            Surse Accesate ({report.sources.length})
          </h3>
          {sourcesOpen ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {sourcesOpen && (
          <div className="mt-3 space-y-2">
            {report.sources.map((src, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-sm p-2 bg-dark-surface rounded"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full",
                      src.data_found ? "bg-green-400" : "bg-red-400"
                    )}
                  />
                  <span className="text-gray-300">{src.source_name}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{src.response_time_ms}ms</span>
                  <span
                    className={clsx(
                      src.status === "OK" ? "text-green-400" : "text-red-400"
                    )}
                  >
                    {src.status}
                  </span>
                  {src.source_url && (
                    <a
                      href={src.source_url}
                      target="_blank"
                      rel="noopener"
                      className="text-accent-secondary hover:text-accent-light"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
