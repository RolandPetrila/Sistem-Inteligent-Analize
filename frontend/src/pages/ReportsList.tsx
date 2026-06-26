import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Eye, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { logAction } from "@/lib/logger";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";
import type { Report } from "@/lib/types";
import clsx from "clsx";

const PAGE_SIZE = 20;

export default function ReportsList() {
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [reportType, setReportType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["reports", page, reportType],
    queryFn: () =>
      api
        .listReports({
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
          report_type: reportType || undefined,
        })
        .then((res) => {
          logAction("ReportsList", "loaded", {
            total: res.total,
            page,
            report_type: reportType || "all",
          });
          return res;
        }),
  });

  // Tipurile de analiza pentru dropdown-ul de filtrare (ca in NewAnalysis)
  const { data: analysisTypes } = useQuery({
    queryKey: ["analysisTypes"],
    queryFn: () => api.getAnalysisTypes(),
    staleTime: 60 * 60 * 1000,
  });
  const types = analysisTypes ?? [];

  const reports = data?.reports ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasTypeFilter = reportType !== "";

  // Filtrare client-side dupa titlu / nume firma in pagina incarcata
  const displayName = (r: Report) =>
    r.title || ANALYSIS_TYPE_LABELS[r.report_type] || r.report_type;
  const query = search.trim().toLowerCase();
  const filteredReports = query
    ? reports.filter((r) => displayName(r).toLowerCase().includes(query))
    : reports;

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-dark-card rounded w-48" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-dark-card rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Rapoarte</h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} rapoarte generate
          </p>
        </div>
      </div>

      {reports.length === 0 && !hasTypeFilter ? (
        <div className="card text-center py-16">
          <FileText className="w-16 h-16 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Niciun raport generat inca</p>
          <p className="text-gray-600 text-sm mt-2">
            Porneste o analiza pentru a genera primul raport
          </p>
        </div>
      ) : (
        <>
          {/* Cautare + filtru dupa tip raport */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                className="input-field w-full pl-9"
                placeholder="Cauta dupa nume firma sau titlu..."
                aria-label="Cauta rapoarte"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              className="input-field w-full sm:w-64"
              aria-label="Filtreaza dupa tipul raportului"
              value={reportType}
              onChange={(e) => {
                setReportType(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Toate tipurile</option>
              {types
                .filter((t) => !t.deferred)
                .map((t) => (
                  <option key={t.type} value={t.type}>
                    {t.name}
                  </option>
                ))}
            </select>
          </div>

          {reports.length === 0 ? (
            <div className="card text-center py-16">
              <FileText className="w-16 h-16 text-gray-700 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">
                Niciun raport pentru tipul selectat
              </p>
              <button
                onClick={() => {
                  setReportType("");
                  setPage(0);
                }}
                className="text-accent-secondary text-sm mt-2 hover:underline"
              >
                Reseteaza filtrul
              </button>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="card text-center py-16">
              <FileText className="w-16 h-16 text-gray-700 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">
                Niciun raport nu corespunde cautarii
              </p>
              <p className="text-gray-600 text-sm mt-2">
                Incearca alti termeni de cautare
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {filteredReports.map((report) => (
                  <div
                    key={report.id}
                    className="card flex items-center justify-between"
                  >
                    <div className="flex items-center gap-4">
                      <FileText className="w-8 h-8 text-accent-secondary" />
                      <div>
                        <p className="font-medium text-white">
                          {report.title ||
                            ANALYSIS_TYPE_LABELS[report.report_type] ||
                            report.report_type}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Nivel {report.report_level} |{" "}
                          {new Date(report.created_at).toLocaleDateString(
                            "ro-RO",
                          )}
                          {report.risk_score && (
                            <span
                              className={clsx(
                                "ml-2 font-medium",
                                report.risk_score === "Verde" &&
                                  "text-risk-verde",
                                report.risk_score === "Galben" &&
                                  "text-risk-galben",
                                report.risk_score === "Rosu" &&
                                  "text-risk-rosu",
                              )}
                            >
                              Risc: {report.risk_score}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/report/${report.id}`}
                        className="px-2.5 py-1 text-xs rounded bg-accent-primary/10
                               hover:bg-accent-primary/20 text-accent-secondary
                               transition-colors flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> Vezi
                      </Link>
                      {report.formats_available.map((fmt) => (
                        <a
                          key={fmt}
                          href={`/api/reports/${report.id}/download/${fmt}`}
                          className="px-2.5 py-1 text-xs rounded bg-dark-surface
                                 hover:bg-dark-hover text-gray-400 hover:text-white
                                 transition-colors uppercase font-mono"
                        >
                          {fmt}
                        </a>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <button
                    onClick={() => setPage((p) => p - 1)}
                    disabled={page === 0}
                    className="p-2 rounded-lg bg-dark-surface border border-dark-border
                           disabled:opacity-30 hover:bg-dark-hover transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    let p: number;
                    if (totalPages <= 7) {
                      p = i;
                    } else if (page < 3) {
                      p = i;
                    } else if (page > totalPages - 4) {
                      p = totalPages - 7 + i;
                    } else {
                      p = page - 3 + i;
                    }
                    return (
                      <button
                        key={p}
                        onClick={() => setPage(p)}
                        className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                          p === page
                            ? "bg-accent-primary text-white"
                            : "bg-dark-surface border border-dark-border text-gray-400 hover:bg-dark-hover"
                        }`}
                      >
                        {p + 1}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= totalPages - 1}
                    className="p-2 rounded-lg bg-dark-surface border border-dark-border
                           disabled:opacity-30 hover:bg-dark-hover transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
