import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  RefreshCw,
  Mail,
  Share2,
  Database,
  Calendar,
  Layers,
  GitCompare,
  Shield,
} from "lucide-react";
import clsx from "clsx";
import { logAction } from "@/lib/logger";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";

interface ReportSource {
  source_name: string;
  source_url: string;
  status: string;
  data_found: boolean;
  response_time_ms: number;
}

interface RiskScore {
  score: string;
  numeric_score?: number;
  dimensions?: Record<string, { score: number; weight: number }>;
  factors: [string, string][];
  recommendation: string;
}

interface ReportHeaderProps {
  report: {
    id: string;
    job_id: string;
    report_type: string;
    report_level: number;
    title: string | null;
    created_at: string;
    formats_available: string[];
    sources: ReportSource[];
  };
  fullData: Record<string, unknown> | null;
  riskScore: RiskScore | undefined;
  riskColor: string;
  reanalyzing: boolean;
  onReanalyze: () => void;
  onEmailOpen: () => void;
  onShare?: () => void;
}

export function ReportHeader({
  report,
  fullData,
  riskScore,
  riskColor,
  reanalyzing,
  onReanalyze,
  onEmailOpen,
  onShare,
}: ReportHeaderProps) {
  return (
    <>
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
            {report.title ||
              ANALYSIS_TYPE_LABELS[report.report_type] ||
              "Raport"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Nivel {report.report_level} |{" "}
            {new Date(report.created_at).toLocaleDateString("ro-RO")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Re-analyze button */}
          <button
            onClick={onReanalyze}
            disabled={reanalyzing}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <RefreshCw
              className={clsx("w-3.5 h-3.5", reanalyzing && "animate-spin")}
            />
            {reanalyzing ? "Se porneste..." : "Re-analiza"}
          </button>
          {report.formats_available.map((fmt) => (
            <a
              key={fmt}
              href={`/api/reports/${report.id}/download/${fmt}`}
              onClick={() =>
                logAction("ReportView", "download", {
                  reportId: report.id,
                  format: fmt,
                })
              }
              className="btn-secondary flex items-center gap-1.5 text-sm"
            >
              <Download className="w-3.5 h-3.5" />
              {fmt.toUpperCase()}
            </a>
          ))}
          <button
            onClick={onEmailOpen}
            className="btn-secondary flex items-center gap-1.5 text-sm"
          >
            <Mail className="w-3.5 h-3.5" />
            Trimite email
          </button>
          {onShare && (
            <button
              onClick={onShare}
              className="btn-secondary flex items-center gap-1.5 text-sm"
              aria-label="Genereaza link partajabil"
            >
              <Share2 className="w-3.5 h-3.5" />
              Partajeaza
            </button>
          )}
        </div>
      </div>

      {/* Report Metadata Bar */}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        {report.sources && report.sources.length > 0 && (
          <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-dark-surface text-gray-400">
            <Database className="w-3.5 h-3.5" />
            Surse: {report.sources.filter((s) => s.data_found).length}/
            {report.sources.length} OK
          </span>
        )}
        <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-dark-surface text-gray-400">
          <Calendar className="w-3.5 h-3.5" />
          {new Date(report.created_at).toLocaleDateString("ro-RO", {
            day: "2-digit",
            month: "long",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
        <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-dark-surface text-gray-400">
          <Layers className="w-3.5 h-3.5" />
          Nivel {report.report_level}
        </span>
        {Boolean((fullData as any)?.delta_info) && (
          <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-accent-primary/10 text-accent-secondary border border-accent-primary/20">
            <GitCompare className="w-3.5 h-3.5" />
            vs anterior
          </span>
        )}
        {Boolean((fullData as any)?.previous_report_id) &&
          !(fullData as any)?.delta_info && (
            <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <GitCompare className="w-3.5 h-3.5" />
              vs anterior
            </span>
          )}
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
                const barColor =
                  d.score >= 70
                    ? "bg-green-400"
                    : d.score >= 40
                      ? "bg-yellow-400"
                      : "bg-red-400";
                return (
                  <div key={key} className="bg-dark-surface/50 rounded-lg p-2">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[10px] text-gray-500 uppercase">
                        {key} ({d.weight}%)
                      </span>
                      <span className="text-xs font-mono text-gray-300">
                        {d.score}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-dark-border rounded-full overflow-hidden">
                      <div
                        className={clsx(
                          "h-full rounded-full transition-all",
                          barColor,
                        )}
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
                      severity === "MEDIUM" &&
                        "bg-yellow-500/20 text-yellow-400",
                      severity === "LOW" && "bg-blue-500/20 text-blue-400",
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
    </>
  );
}
