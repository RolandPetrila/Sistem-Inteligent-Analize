import { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction, logValidation, validateReportData } from "@/lib/logger";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";
import type { AnalysisType } from "@/lib/types";
import { ReportHeader } from "@/components/report/ReportHeader";
import { ReportTabs } from "@/components/report/ReportTabs";
import { PredictiveScoresTab } from "@/components/report/PredictiveScoresTab";
import { RadarChartSVG } from "@/components/report/RadarChartSVG";
import { DeltaView } from "@/components/report/DeltaView";
import { SimpleBarChart } from "@/components/report/SimpleBarChart";
import { EmailModal } from "@/components/report/EmailModal";

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
    risk_score?: {
      score: string;
      factors: [string, string][];
      recommendation: string;
    };
    sources_used?: { name: string; level: number; status: string }[];
    [key: string]: unknown;
  } | null;
  sources: {
    source_name: string;
    source_url: string;
    status: string;
    data_found: boolean;
    response_time_ms: number;
  }[];
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
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailSubject, setEmailSubject] = useState("");
  const [predictiveScores, setPredictiveScores] = useState<any>(null);
  const [predictiveLoading, setPredictiveLoading] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getReport(id)
      .then((r) => {
        const rep = r as unknown as ReportFull;
        setReport(rep);
        const issues = validateReportData(
          rep.full_data as Record<string, unknown> | null,
        );
        if (issues.length > 0) {
          logValidation("ReportView", issues);
        }
        setEmailSubject(
          `Raport: ${rep.title || ANALYSIS_TYPE_LABELS[rep.report_type] || "Raport RIS"}`,
        );
        logAction("ReportView", "open", {
          reportId: id,
          type: rep.report_type,
          hasData: !!rep.full_data,
          sources: rep.sources?.length,
        });

        const cui = rep.full_data?.company?.cui?.value as string | undefined;
        if (cui) {
          setPredictiveLoading(true);
          fetch(`/api/companies/${cui}/predictive`)
            .then((r) => (r.ok ? r.json() : null))
            .then(setPredictiveScores)
            .catch(() => setPredictiveScores(null))
            .finally(() => setPredictiveLoading(false));
        }
      })
      .catch(() => toast("Eroare la incarcarea raportului", "error"))
      .finally(() => setLoading(false));
  }, [id]);

  const financialChartData = useMemo(() => {
    if (!report?.full_data?.financial) return null;
    const fin = report.full_data.financial as Record<
      string,
      { value?: number; historical?: Record<string, number> }
    >;
    const caHist = fin.cifra_afaceri?.historical || {};
    const profitHist = fin.profit_net?.historical || {};
    const angajatiHist = fin.numar_angajati?.historical || {};
    const years = [
      ...new Set([...Object.keys(caHist), ...Object.keys(profitHist)]),
    ]
      .sort()
      .slice(-5);
    if (years.length < 2) return null;
    return {
      years,
      ca: years.map((y) => caHist[y] ?? null),
      profit: years.map((y) => profitHist[y] ?? null),
      angajati: years.map((y) => angajatiHist[y] ?? null),
    };
  }, [report]);

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
  const riskScore = data?.risk_score as
    | {
        score: string;
        numeric_score?: number;
        dimensions?: Record<string, { score: number; weight: number }>;
        factors: [string, string][];
        recommendation: string;
      }
    | undefined;

  const DIMENSION_INFO: Record<
    string,
    { weight: number; label: string; desc: string }
  > = {
    financiar: {
      weight: 30,
      label: "Financiar",
      desc: "CA, profit, trend, solvabilitate",
    },
    juridic: { weight: 20, label: "Juridic", desc: "Litigii, insolventa" },
    fiscal: { weight: 15, label: "Fiscal", desc: "Stare TVA, inactivi ANAF" },
    operational: {
      weight: 15,
      label: "Operational",
      desc: "Angajati, vechime, stabilitate",
    },
    reputational: {
      weight: 10,
      label: "Reputational",
      desc: "Prezenta online",
    },
    piata: { weight: 10, label: "Piata", desc: "Competitie, SEAP, benchmark" },
  };

  const scoringDimensions:
    | Record<string, { score: number; weight: number }>
    | undefined =
    riskScore?.dimensions ||
    (
      data?.scoring as
        | { dimensions?: Record<string, { score: number; weight: number }> }
        | undefined
    )?.dimensions ||
    (
      data?.verification as
        | {
            scoring_dimensions?: Record<
              string,
              { score: number; weight: number }
            >;
          }
        | undefined
    )?.scoring_dimensions;

  const riskColor =
    {
      Verde: "text-risk-verde border-risk-verde/30 bg-risk-verde/5",
      Galben: "text-risk-galben border-risk-galben/30 bg-risk-galben/5",
      Rosu: "text-risk-rosu border-risk-rosu/30 bg-risk-rosu/5",
    }[riskScore?.score || ""] ||
    "text-gray-400 border-dark-border bg-dark-card";

  const tabs = [
    { key: "overview", label: "Rezumat" },
    { key: "company", label: "Profil Firma" },
    { key: "risk", label: "Risc" },
    { key: "charts", label: "Grafice" },
    { key: "delta", label: "Modificari" },
    { key: "predictive", label: "Predictiv" },
    { key: "raw", label: "Date JSON" },
  ];

  const handleReanalyze = async () => {
    if (reanalyzing) return;
    const cui = data?.company?.cui?.value || data?.company?.denumire?.value;
    if (!cui) {
      toast("CUI indisponibil pentru re-analiza", "error");
      return;
    }
    setReanalyzing(true);
    try {
      const job = await api.createJob({
        analysis_type: report.report_type as AnalysisType,
        report_level: report.report_level as number,
        input_params: {
          cui: String(typeof cui === "object" ? "" : cui),
        },
      });
      await api.startJob(job.id);
      navigate(`/analysis/${job.id}`);
    } catch {
      toast("Eroare la pornirea re-analizei", "error");
      setReanalyzing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header + Risk Score Card (extracted component) */}
      <ReportHeader
        report={report}
        fullData={data}
        riskScore={riskScore}
        riskColor={riskColor}
        reanalyzing={reanalyzing}
        onReanalyze={handleReanalyze}
        onEmailOpen={() => setEmailModalOpen(true)}
        onShare={async () => {
          try {
            const res = await api.shareReport(report.id);
            const fullUrl = `${window.location.origin}${res.share_url}`;
            setShareUrl(fullUrl);
            await navigator.clipboard.writeText(fullUrl).catch(() => {});
            toast("Link copiat in clipboard! Valabil 30 zile.", "success");
          } catch {
            toast("Eroare la generarea link-ului de partajare.", "error");
          }
        }}
      />
      {shareUrl && (
        <div className="p-3 rounded-lg border border-accent-primary/30 bg-accent-primary/5 flex items-center gap-3">
          <span className="text-xs text-gray-400 flex-1 truncate">
            {shareUrl}
          </span>
          <button
            onClick={async () => {
              await navigator.clipboard.writeText(shareUrl).catch(() => {});
              toast("Link copiat!", "success");
            }}
            className="text-xs text-accent-secondary hover:text-white transition-colors shrink-0"
          >
            Copiaza
          </button>
        </div>
      )}

      {/* F6-3: Completeness warning banner */}
      {report &&
        (report as any).completeness_score != null &&
        (report as any).completeness_score < 50 && (
          <div className="mb-4 p-3 rounded-lg border border-yellow-600 bg-yellow-900/20 text-yellow-300 text-sm">
            ⚠ Date insuficiente ({(report as any).completeness_score}%
            completitudine) — rezultatele pot fi imprecise.
            {(report as any).failed_sources?.length > 0 && (
              <span className="ml-1">
                Surse esuate: {(report as any).failed_sources.join(", ")}
              </span>
            )}
          </div>
        )}

      {/* Tabs (extracted component) */}
      <ReportTabs
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Tab Content */}
      <div className="card min-h-[200px]">
        {activeTab === "overview" && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase">
              Rezumat
            </h3>
            <p className="text-gray-300">
              {report.summary || "Niciun rezumat disponibil."}
            </p>
          </div>
        )}

        {activeTab === "company" && data?.company && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
              Profil Firma
            </h3>
            {Object.entries(data.company).map(([key, field]) => {
              if (!field || typeof field !== "object") return null;
              const f = field as {
                value: unknown;
                trust?: string;
                source?: string;
              };
              return (
                <div
                  key={key}
                  className="flex justify-between py-2 border-b border-dark-border"
                >
                  <span className="text-gray-500 text-sm">
                    {key.replace(/_/g, " ")}
                  </span>
                  <div className="text-right">
                    <span className="text-white text-sm">
                      {String(f.value ?? "N/A")}
                    </span>
                    {f.trust && (
                      <span
                        className={clsx(
                          "ml-2 text-[10px] font-mono",
                          f.trust === "OFICIAL" && "text-trust-oficial",
                          f.trust === "VERIFICAT" && "text-trust-verificat",
                          f.trust === "ESTIMAT" && "text-trust-estimat",
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

        {activeTab === "risk" && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
              Evaluare Risc
            </h3>

            {/* Breakdown scor per dimensiune */}
            {scoringDimensions && Object.keys(scoringDimensions).length > 0 ? (
              <div className="space-y-3 mb-4">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Scor per Dimensiune
                </h4>
                <div className="grid grid-cols-1 gap-3">
                  {Object.entries(DIMENSION_INFO).map(([key, info]) => {
                    const dim = scoringDimensions[key];
                    const score = dim?.score ?? 0;
                    const barColor =
                      score >= 70
                        ? "bg-green-400"
                        : score >= 40
                          ? "bg-yellow-400"
                          : "bg-red-400";
                    const scoreColor =
                      score >= 70
                        ? "text-green-400"
                        : score >= 40
                          ? "text-yellow-400"
                          : "text-red-400";
                    return (
                      <div key={key} className="p-3 bg-dark-surface rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <span className="text-sm font-medium text-gray-200">
                              {info.label}
                            </span>
                            <span className="ml-2 text-[10px] text-gray-500 bg-dark-border px-1.5 py-0.5 rounded">
                              {info.weight}%
                            </span>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {info.desc}
                            </p>
                          </div>
                          <span
                            className={clsx(
                              "text-xl font-bold font-mono",
                              scoreColor,
                            )}
                          >
                            {dim ? score : "—"}
                          </span>
                        </div>
                        {dim && (
                          <div className="w-full h-2 bg-dark-border rounded-full overflow-hidden">
                            <div
                              className={clsx(
                                "h-full rounded-full transition-all",
                                barColor,
                              )}
                              style={{ width: `${score}%` }}
                            />
                          </div>
                        )}
                        {!dim && (
                          <p className="text-[10px] text-gray-600 italic">
                            Date indisponibile
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="p-3 bg-dark-surface rounded-lg mb-4">
                <p className="text-xs text-gray-500 italic">
                  Scor detaliat per dimensiune nu este disponibil pentru acest
                  raport.
                </p>
              </div>
            )}

            {/* F6-2: Radar Chart SVG (extracted component) */}
            {scoringDimensions &&
              Object.keys(scoringDimensions).length >= 3 && (
                <RadarChartSVG scoringDimensions={scoringDimensions} />
              )}

            {/* F6-4: Sector Benchmark Bar */}
            {(() => {
              const sectorPos =
                (data?.risk as any)?.sector_position ||
                (data as any)?.sector_position;
              const percentile =
                sectorPos?.percentile || (data as any)?.benchmark?.percentile;
              if (!percentile) return null;
              return (
                <div className="p-3 bg-dark-surface rounded-lg mb-4">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Pozitie in Sector
                  </h4>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm text-gray-300">
                      Top {100 - percentile}% in sectorul tau
                    </span>
                    <span className="text-xs text-gray-500">
                      ({percentile}a percentila)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-dark-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${100 - percentile}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>Mai bun</span>
                    <span>Mai slab</span>
                  </div>
                </div>
              );
            })()}

            {/* Date risc din structura raportului */}
            {data?.risk &&
              Object.entries(data.risk).map(([key, field]) => {
                if (!field || typeof field !== "object") return null;
                const f = field as {
                  value: unknown;
                  trust?: string;
                  note?: string;
                };
                return (
                  <div
                    key={key}
                    className="p-3 bg-dark-surface rounded-lg mb-2"
                  >
                    <p className="text-sm font-medium text-gray-300">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {typeof f.value === "object"
                        ? JSON.stringify(f.value, null, 2).slice(0, 200)
                        : String(f.value)}
                    </p>
                    {f.note && (
                      <p className="text-[10px] text-gray-600 mt-1 italic">
                        {f.note}
                      </p>
                    )}
                  </div>
                );
              })}
          </div>
        )}

        {activeTab === "charts" && (
          <div className="space-y-6">
            <h3 className="text-sm font-semibold text-gray-400 uppercase">
              Evolutie Financiara Multi-An
            </h3>
            {financialChartData ? (
              <div className="space-y-8">
                <div className="text-xs text-gray-500 mb-2">
                  Ani disponibili: {financialChartData.years.join(", ")}
                </div>
                <SimpleBarChart
                  data={financialChartData.ca}
                  years={financialChartData.years}
                  label="Cifra de Afaceri"
                  color="#3b82f6"
                  unit="RON"
                />
                <SimpleBarChart
                  data={financialChartData.profit}
                  years={financialChartData.years}
                  label="Profit Net"
                  color="#22c55e"
                  unit="RON"
                />
                <SimpleBarChart
                  data={financialChartData.angajati}
                  years={financialChartData.years}
                  label="Numar Angajati"
                  color="#a855f7"
                />
              </div>
            ) : (
              <div className="p-4 bg-dark-surface rounded-lg text-center">
                <p className="text-sm text-gray-500">
                  Date financiare insuficiente pentru grafice (necesita minim 2
                  ani de date).
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "delta" && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase">
              Modificari fata de analiza anterioara
            </h3>
            <DeltaView reportId={report.id} />
          </div>
        )}

        {/* F2-6: Tab Scoruri Predictive (extracted component) */}
        {activeTab === "predictive" && (
          <PredictiveScoresTab
            loading={predictiveLoading}
            scores={predictiveScores}
          />
        )}

        {activeTab === "raw" && (
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
              Date Verificate (JSON)
            </h3>
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
            Surse Accesate ({(report.sources ?? []).length})
          </h3>
          {sourcesOpen ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {sourcesOpen && (
          <div className="mt-3 space-y-2">
            {(report.sources ?? []).map((src, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-sm p-2 bg-dark-surface rounded"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full",
                      src.data_found ? "bg-green-400" : "bg-red-400",
                    )}
                  />
                  <span className="text-gray-300">{src.source_name}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{src.response_time_ms}ms</span>
                  <span
                    className={clsx(
                      src.status === "OK" ? "text-green-400" : "text-red-400",
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

      {/* N5: Email Send Modal (extracted component) */}
      <EmailModal
        open={emailModalOpen}
        onClose={() => setEmailModalOpen(false)}
        reportId={report.id}
        initialSubject={emailSubject}
      />
    </div>
  );
}
