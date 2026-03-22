import { useEffect, useState } from "react";
import { Building2, Download, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useDebounce } from "@/hooks/useDebounce";
import type { Company } from "@/lib/types";

const PAGE_SIZE = 20;

export default function Companies() {
  const { toast } = useToast();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  // 10C M12.4: Debounced search — auto-search after 300ms typing pause
  const debouncedSearch = useDebounce(search, 300);

  const loadCompanies = (searchTerm?: string, pageNum = 0) => {
    setLoading(true);
    api
      .listCompanies({ search: searchTerm, limit: PAGE_SIZE, offset: pageNum * PAGE_SIZE })
      .then((res) => {
        setCompanies(res.companies);
        setTotal(res.total);
      })
      .catch(() => toast("Eroare la incarcarea companiilor", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  // Auto-search on debounced value change
  useEffect(() => {
    setPage(0);
    loadCompanies(debouncedSearch, 0);
  }, [debouncedSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadCompanies(search, 0);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const goToPage = (p: number) => {
    setPage(p);
    loadCompanies(search, p);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Companii</h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} companii in baza de date
          </p>
        </div>
        {total > 0 && (
          <button
            onClick={() => api.exportCompaniesCSV()}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            className="input-field w-full pl-9"
            placeholder="Cauta dupa nume sau CUI..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button type="submit" className="btn-primary">
          Cauta
        </button>
        {/* B27 fix: Clear search button that also resets pagination */}
        {search && (
          <button
            type="button"
            onClick={() => { setSearch(""); setPage(0); loadCompanies("", 0); }}
            className="btn-secondary text-sm"
          >
            Sterge
          </button>
        )}
      </form>

      {loading ? (
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-dark-card rounded-xl" />
          ))}
        </div>
      ) : companies.length === 0 ? (
        <div className="card text-center py-16">
          <Building2 className="w-16 h-16 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Nicio companie analizata inca</p>
          <p className="text-gray-600 text-sm mt-2">
            Companiile apar automat dupa prima analiza
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {companies.map((company) => (
              <div key={company.id} className="card">
                <div className="flex items-start gap-3">
                  <Building2 className="w-8 h-8 text-accent-secondary shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white truncate">
                      {company.name}
                    </h3>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-gray-500">
                      {company.cui && <span>CUI: {company.cui}</span>}
                      {company.caen_code && <span>CAEN: {company.caen_code}</span>}
                      {company.county && <span>{company.county}</span>}
                    </div>
                    <p className="text-xs text-gray-600 mt-2">
                      {company.analysis_count} analize |{" "}
                      {company.last_analyzed_at
                        ? `Ultima: ${new Date(
                            company.last_analyzed_at
                          ).toLocaleDateString("ro-RO")}`
                        : "Neanalizata"}
                    </p>
                  </div>
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
