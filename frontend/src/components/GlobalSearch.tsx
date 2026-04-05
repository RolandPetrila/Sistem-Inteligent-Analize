import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Building2, FileText, Zap, X, Command } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { Company, Report } from "@/lib/types";

interface SearchResults {
  companies: Company[];
  reports: Report[];
  actions: QuickAction[];
}

interface QuickAction {
  id: string;
  label: string;
  description: string;
  path: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  { id: "new-analysis", label: "Analiza noua", description: "Incepe o analiza noua", path: "/new-analysis" },
  { id: "compare", label: "Compara firme", description: "Compara 2 firme", path: "/compare" },
  { id: "batch", label: "Batch analiza", description: "Analiza multipla CSV", path: "/batch" },
  { id: "settings", label: "Setari", description: "Configurare sistem", path: "/settings" },
  { id: "monitoring", label: "Monitorizare", description: "Alerte firme", path: "/monitoring" },
];

export default function GlobalSearch() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults>({ companies: [], reports: [], actions: QUICK_ACTIONS.slice(0, 4) });
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Ctrl+K to open
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setResults({ companies: [], reports: [], actions: QUICK_ACTIONS.slice(0, 4) });
      setSelected(0);
    }
  }, [open]);

  // Search all sources with debounce
  const searchAll = useCallback(
    (q: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);

      if (!q || q.trim().length < 2) {
        setResults({ companies: [], reports: [], actions: QUICK_ACTIONS.slice(0, 4) });
        setLoading(false);
        return;
      }

      setLoading(true);
      debounceRef.current = setTimeout(async () => {
        const query = q.trim();

        // Detect CUI: numeric string 6-10 digits
        const isCui = /^\d{6,10}$/.test(query);

        // Filter quick actions matching query
        const matchingActions = QUICK_ACTIONS.filter(
          (a) =>
            a.label.toLowerCase().includes(query.toLowerCase()) ||
            a.description.toLowerCase().includes(query.toLowerCase())
        );

        // Add "Analizeaza CUI X" action for numeric queries
        if (isCui) {
          matchingActions.unshift({
            id: `analyze-${query}`,
            label: `Analizeaza CUI ${query}`,
            description: "Porneste analiza directa",
            path: `/new-analysis?cui=${query}`,
          });
        }

        try {
          const [companiesResult, reportsResult] = await Promise.all([
            api.listCompanies({ search: query, limit: 5 }),
            api.listReports({ limit: 20 }).catch(() => ({ reports: [], total: 0 })),
          ]);

          // Filter reports locally by title/type match (backend doesn't support search param)
          const allReports = reportsResult.reports || [];
          const filteredReports = allReports.filter(
            (r) =>
              (r.title && r.title.toLowerCase().includes(query.toLowerCase())) ||
              r.report_type.toLowerCase().includes(query.toLowerCase())
          ).slice(0, 5);

          setResults({
            companies: companiesResult?.companies || [],
            reports: filteredReports,
            actions: matchingActions,
          });
          setSelected(0);
        } catch {
          setResults({ companies: [], reports: [], actions: matchingActions });
        } finally {
          setLoading(false);
        }
      }, 300);
    },
    []
  );

  const handleInputChange = (value: string) => {
    setQuery(value);
    searchAll(value);
  };

  // Flatten all results for keyboard navigation
  const allItems = [
    ...results.actions.map((a) => ({ type: "action" as const, item: a })),
    ...results.companies.map((c) => ({ type: "company" as const, item: c })),
    ...results.reports.map((r) => ({ type: "report" as const, item: r })),
  ];

  const handleSelectAction = (action: QuickAction) => {
    setOpen(false);
    navigate(action.path);
  };

  const handleSelectCompany = (company: Company) => {
    setOpen(false);
    navigate(`/company/${company.id}`);
  };

  const handleSelectReport = (report: Report) => {
    setOpen(false);
    navigate(`/report/${report.id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((prev) => Math.min(prev + 1, allItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && allItems[selected]) {
      const sel = allItems[selected];
      if (sel.type === "action") handleSelectAction(sel.item as QuickAction);
      else if (sel.type === "company") handleSelectCompany(sel.item as Company);
      else handleSelectReport(sel.item as Report);
    }
  };

  const hasResults =
    results.companies.length > 0 ||
    results.reports.length > 0 ||
    results.actions.length > 0;

  if (!open) return null;

  // Running index for keyboard selection highlight
  let itemIdx = 0;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Command Palette */}
      <div className="fixed inset-x-0 top-[15%] z-[61] mx-auto w-full max-w-lg px-4">
        <div className="bg-dark-card border border-dark-border rounded-xl shadow-2xl overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-dark-border">
            <Search className="w-5 h-5 text-gray-500 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Cauta companie, raport sau actiune..."
              className="flex-1 bg-transparent text-white text-sm placeholder-gray-600 outline-none"
            />
            {query && (
              <button
                onClick={() => { setQuery(""); setResults({ companies: [], reports: [], actions: QUICK_ACTIONS.slice(0, 4) }); }}
                className="text-gray-600 hover:text-gray-400 transition-colors"
                aria-label="Sterge cautarea"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <kbd className="hidden sm:flex items-center gap-0.5 text-[10px] text-gray-600 bg-dark-surface px-1.5 py-0.5 rounded border border-dark-border">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-accent-primary" />
              </div>
            )}

            {!loading && query.length >= 2 && !hasResults && (
              <div className="py-8 text-center">
                <p className="text-sm text-gray-500">Niciun rezultat gasit</p>
                <p className="text-xs text-gray-600 mt-1">Incearca alt termen de cautare</p>
              </div>
            )}

            {!loading && hasResults && (
              <div className="py-1">
                {/* Actiuni rapide */}
                {results.actions.length > 0 && (
                  <>
                    <p className="px-4 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                      Actiuni
                    </p>
                    {results.actions.map((action) => {
                      const isSelected = itemIdx === selected;
                      const currentIdx = itemIdx++;
                      return (
                        <button
                          key={action.id}
                          onClick={() => handleSelectAction(action)}
                          onMouseEnter={() => setSelected(currentIdx)}
                          className={clsx(
                            "w-full flex items-center gap-3 px-4 py-2 text-left transition-colors",
                            isSelected
                              ? "bg-accent-primary/10 text-white"
                              : "text-gray-300 hover:bg-dark-hover"
                          )}
                        >
                          <div className="w-7 h-7 rounded-lg bg-dark-surface flex items-center justify-center shrink-0">
                            <Zap className="w-3.5 h-3.5 text-yellow-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{action.label}</p>
                            <p className="text-[10px] text-gray-500">{action.description}</p>
                          </div>
                        </button>
                      );
                    })}
                  </>
                )}

                {/* Firme */}
                {results.companies.length > 0 && (
                  <>
                    <p className="px-4 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                      Firme
                    </p>
                    {results.companies.map((company) => {
                      const isSelected = itemIdx === selected;
                      const currentIdx = itemIdx++;
                      return (
                        <button
                          key={company.id}
                          onClick={() => handleSelectCompany(company)}
                          onMouseEnter={() => setSelected(currentIdx)}
                          className={clsx(
                            "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                            isSelected
                              ? "bg-accent-primary/10 text-white"
                              : "text-gray-300 hover:bg-dark-hover"
                          )}
                        >
                          <div className="w-8 h-8 rounded-lg bg-dark-surface flex items-center justify-center shrink-0">
                            <Building2 className="w-4 h-4 text-accent-secondary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{company.name}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              {company.cui && (
                                <span className="text-[10px] text-gray-500 font-mono">
                                  CUI: {company.cui}
                                </span>
                              )}
                              {company.caen_code && (
                                <span className="text-[10px] text-gray-600">
                                  CAEN: {company.caen_code}
                                </span>
                              )}
                              {company.county && (
                                <span className="text-[10px] text-gray-600">
                                  {company.county}
                                </span>
                              )}
                            </div>
                          </div>
                          <span className="text-[10px] text-gray-600 shrink-0">
                            {company.analysis_count} analize
                          </span>
                        </button>
                      );
                    })}
                  </>
                )}

                {/* Rapoarte */}
                {results.reports.length > 0 && (
                  <>
                    <p className="px-4 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                      Rapoarte
                    </p>
                    {results.reports.map((report) => {
                      const isSelected = itemIdx === selected;
                      const currentIdx = itemIdx++;
                      return (
                        <button
                          key={report.id}
                          onClick={() => handleSelectReport(report)}
                          onMouseEnter={() => setSelected(currentIdx)}
                          className={clsx(
                            "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                            isSelected
                              ? "bg-accent-primary/10 text-white"
                              : "text-gray-300 hover:bg-dark-hover"
                          )}
                        >
                          <div className="w-8 h-8 rounded-lg bg-dark-surface flex items-center justify-center shrink-0">
                            <FileText className="w-4 h-4 text-accent-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {report.title || report.report_type}
                            </p>
                            <p className="text-[10px] text-gray-500">
                              Nivel {report.report_level} |{" "}
                              {new Date(report.created_at).toLocaleDateString("ro-RO")}
                            </p>
                          </div>
                          {report.risk_score && (
                            <span
                              className={clsx(
                                "text-[10px] px-1.5 py-0.5 rounded border shrink-0",
                                report.risk_score === "Verde" && "text-green-400 border-green-500/30 bg-green-500/10",
                                report.risk_score === "Galben" && "text-yellow-400 border-yellow-500/30 bg-yellow-500/10",
                                report.risk_score === "Rosu" && "text-red-400 border-red-500/30 bg-red-500/10"
                              )}
                            >
                              {report.risk_score}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </>
                )}
              </div>
            )}

            {!loading && query.length < 2 && (
              <div className="py-6 text-center">
                <Command className="w-6 h-6 text-gray-600 mx-auto mb-2" />
                <p className="text-xs text-gray-500">
                  Scrie minim 2 caractere pentru a cauta
                </p>
                <p className="text-[10px] text-gray-600 mt-1">
                  Firme, rapoarte, actiuni sau CUI numeric
                </p>
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div className="px-4 py-2 border-t border-dark-border flex items-center justify-between text-[10px] text-gray-600">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="bg-dark-surface px-1 py-0.5 rounded border border-dark-border/50">&#8593;</kbd>
                <kbd className="bg-dark-surface px-1 py-0.5 rounded border border-dark-border/50">&#8595;</kbd>
                navigheaza
              </span>
              <span className="flex items-center gap-1">
                <kbd className="bg-dark-surface px-1 py-0.5 rounded border border-dark-border/50">Enter</kbd>
                selecteaza
              </span>
            </div>
            <span className="flex items-center gap-1">
              <kbd className="bg-dark-surface px-1 py-0.5 rounded border border-dark-border/50">Esc</kbd>
              inchide
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
