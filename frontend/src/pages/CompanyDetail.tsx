import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  FileText,
  Shield,
  PlusCircle,
  TrendingUp,
  TrendingDown,
  Calendar,
  MapPin,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";

interface CompanyReport {
  id: string;
  report_type: string;
  report_level: number;
  title: string | null;
  summary: string | null;
  risk_score: string | null;
  created_at: string;
}

interface ScoreEntry {
  numeric_score: number | null;
  dimensions: string | null;
  recorded_at: string;
}

interface CompanyFull {
  id: string;
  cui: string | null;
  name: string;
  caen_code: string | null;
  caen_description: string | null;
  county: string | null;
  city: string | null;
  first_analyzed_at: string | null;
  last_analyzed_at: string | null;
  analysis_count: number;
  reports: CompanyReport[];
  score_history: ScoreEntry[];
}

const riskBadge = (score: string | null) => {
  const map: Record<string, string> = {
    Verde: "bg-green-500/15 text-green-400 border-green-500/30",
    Galben: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    Rosu: "bg-red-500/15 text-red-400 border-red-500/30",
  };
  return map[score || ""] || "bg-gray-500/15 text-gray-400 border-gray-500/30";
};

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [company, setCompany] = useState<CompanyFull | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api
      .getCompany(id)
      .then((c) => {
        setCompany(c as unknown as CompanyFull);
        logAction("CompanyDetail", "open", { companyId: id, name: (c as unknown as CompanyFull).name });
      })
      .catch(() => toast("Eroare la incarcarea companiei", "error"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleNewAnalysis = () => {
    if (!company?.cui) return;
    navigate(`/new-analysis?cui=${company.cui}&name=${encodeURIComponent(company.name)}`);
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-dark-card rounded w-48" />
        <div className="h-40 bg-dark-card rounded-xl" />
        <div className="h-64 bg-dark-card rounded-xl" />
      </div>
    );
  }

  if (!company) {
    return <p className="text-gray-500">Compania nu a fost gasita.</p>;
  }

  // Parse latest score from score_history
  const latestScore = company.score_history[0];
  const prevScore = company.score_history[1];
  const scoreDelta =
    latestScore?.numeric_score != null && prevScore?.numeric_score != null
      ? latestScore.numeric_score - prevScore.numeric_score
      : null;

  // Parse dimensions from latest score
  let dimensions: Record<string, { score: number; weight: number }> | null = null;
  if (latestScore?.dimensions) {
    try {
      dimensions = JSON.parse(latestScore.dimensions);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <Link
          to="/companies"
          className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 mb-3"
        >
          <ArrowLeft className="w-3 h-3" /> Inapoi la companii
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
              <Building2 className="w-7 h-7 text-accent-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">{company.name}</h1>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-sm text-gray-500">
                {company.cui && <span>CUI: {company.cui}</span>}
                {company.caen_code && (
                  <span>
                    CAEN: {company.caen_code}
                    {company.caen_description && ` — ${company.caen_description}`}
                  </span>
                )}
                {(company.city || company.county) && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {[company.city, company.county].filter(Boolean).join(", ")}
                  </span>
                )}
              </div>
            </div>
          </div>

          <button onClick={handleNewAnalysis} className="btn-primary flex items-center gap-2">
            <PlusCircle className="w-4 h-4" />
            Re-analiza
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Score */}
        <div className="card flex flex-col items-center justify-center py-5">
          <Shield className="w-5 h-5 text-gray-500 mb-1" />
          {latestScore?.numeric_score != null ? (
            <>
              <span className="text-3xl font-bold text-white font-mono">
                {latestScore.numeric_score}
              </span>
              <span className="text-xs text-gray-500">/100</span>
              {scoreDelta != null && scoreDelta !== 0 && (
                <span
                  className={clsx(
                    "text-xs flex items-center gap-0.5 mt-1",
                    scoreDelta > 0 ? "text-green-400" : "text-red-400"
                  )}
                >
                  {scoreDelta > 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  {scoreDelta > 0 ? "+" : ""}
                  {scoreDelta.toFixed(0)}
                </span>
              )}
            </>
          ) : (
            <span className="text-lg text-gray-600">N/A</span>
          )}
          <span className="text-[10px] text-gray-600 mt-1">Scor Risc</span>
        </div>

        {/* Analyses */}
        <div className="card flex flex-col items-center justify-center py-5">
          <FileText className="w-5 h-5 text-gray-500 mb-1" />
          <span className="text-3xl font-bold text-white font-mono">
            {company.analysis_count}
          </span>
          <span className="text-[10px] text-gray-600 mt-1">Analize</span>
        </div>

        {/* First analyzed */}
        <div className="card flex flex-col items-center justify-center py-5">
          <Calendar className="w-5 h-5 text-gray-500 mb-1" />
          <span className="text-sm font-medium text-white">
            {company.first_analyzed_at
              ? new Date(company.first_analyzed_at).toLocaleDateString("ro-RO")
              : "—"}
          </span>
          <span className="text-[10px] text-gray-600 mt-1">Prima Analiza</span>
        </div>

        {/* Last analyzed */}
        <div className="card flex flex-col items-center justify-center py-5">
          <Calendar className="w-5 h-5 text-gray-500 mb-1" />
          <span className="text-sm font-medium text-white">
            {company.last_analyzed_at
              ? new Date(company.last_analyzed_at).toLocaleDateString("ro-RO")
              : "—"}
          </span>
          <span className="text-[10px] text-gray-600 mt-1">Ultima Analiza</span>
        </div>
      </div>

      {/* Dimensions Breakdown */}
      {dimensions && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
            Scor pe Dimensiuni
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(dimensions).map(([key, dim]) => {
              const barColor =
                dim.score >= 70
                  ? "bg-green-400"
                  : dim.score >= 40
                    ? "bg-yellow-400"
                    : "bg-red-400";
              return (
                <div key={key} className="bg-dark-surface rounded-lg p-3">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs text-gray-400 capitalize">{key}</span>
                    <span className="text-sm font-mono font-medium text-gray-300">
                      {dim.score}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-dark-border rounded-full overflow-hidden">
                    <div
                      className={clsx("h-full rounded-full transition-all", barColor)}
                      style={{ width: `${dim.score}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-600 mt-1 block">
                    Pondere: {dim.weight}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Score History */}
      {company.score_history.length > 1 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
            Istoric Scor ({company.score_history.length} inregistrari)
          </h3>
          <div className="flex items-end gap-1 h-24">
            {[...company.score_history].reverse().map((entry, i) => {
              const score = entry.numeric_score ?? 0;
              const barColor =
                score >= 70
                  ? "bg-green-400"
                  : score >= 40
                    ? "bg-yellow-400"
                    : "bg-red-400";
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] text-gray-500 font-mono">{score}</span>
                  <div
                    className={clsx("w-full rounded-t", barColor)}
                    style={{ height: `${Math.max(score, 4)}%` }}
                    title={`${score}/100 — ${new Date(entry.recorded_at).toLocaleDateString("ro-RO")}`}
                  />
                  <span className="text-[8px] text-gray-600 truncate w-full text-center">
                    {new Date(entry.recorded_at).toLocaleDateString("ro-RO", {
                      day: "2-digit",
                      month: "short",
                    })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reports List */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase">
            Rapoarte ({company.reports.length})
          </h3>
        </div>

        {company.reports.length === 0 ? (
          <p className="text-gray-600 text-sm py-4 text-center">
            Niciun raport generat inca.
          </p>
        ) : (
          <div className="space-y-2">
            {company.reports.map((report) => (
              <Link
                key={report.id}
                to={`/report/${report.id}`}
                className="flex items-center justify-between p-3 bg-dark-surface rounded-lg hover:bg-dark-hover transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-gray-500 group-hover:text-accent-secondary" />
                  <div>
                    <p className="text-sm text-gray-300 group-hover:text-white">
                      {report.title ||
                        ANALYSIS_TYPE_LABELS[report.report_type] ||
                        report.report_type}
                    </p>
                    <p className="text-xs text-gray-600">
                      Nivel {report.report_level} |{" "}
                      {new Date(report.created_at).toLocaleDateString("ro-RO")}
                    </p>
                  </div>
                </div>

                {report.risk_score && (
                  <span
                    className={clsx(
                      "text-xs font-medium px-2 py-0.5 rounded border",
                      riskBadge(report.risk_score)
                    )}
                  >
                    {report.risk_score}
                  </span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
