import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Eye, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";
import type { Report } from "@/lib/types";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";
import clsx from "clsx";

const PAGE_SIZE = 20;

export default function ReportsList() {
  const { toast } = useToast();
  const [reports, setReports] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  const loadReports = (pageNum = 0) => {
    setLoading(true);
    api
      .listReports({ limit: PAGE_SIZE, offset: pageNum * PAGE_SIZE })
      .then((res) => {
        setReports(res.reports);
        setTotal(res.total);
        logAction("ReportsList", "loaded", { total: res.total, page: pageNum });
      })
      .catch(() => toast("Eroare la incarcarea rapoartelor", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadReports();
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const goToPage = (p: number) => {
    setPage(p);
    loadReports(p);
  };

  if (loading) {
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

      {reports.length === 0 ? (
        <div className="card text-center py-16">
          <FileText className="w-16 h-16 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Niciun raport generat inca</p>
          <p className="text-gray-600 text-sm mt-2">
            Porneste o analiza pentru a genera primul raport
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {reports.map((report) => (
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
                      {new Date(report.created_at).toLocaleDateString("ro-RO")}
                      {report.risk_score && (
                        <span
                          className={clsx(
                            "ml-2 font-medium",
                            report.risk_score === "Verde" && "text-risk-verde",
                            report.risk_score === "Galben" && "text-risk-galben",
                            report.risk_score === "Rosu" && "text-risk-rosu"
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
                onClick={() => goToPage(page - 1)}
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
                    onClick={() => goToPage(p)}
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
                onClick={() => goToPage(page + 1)}
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
    </div>
  );
}
