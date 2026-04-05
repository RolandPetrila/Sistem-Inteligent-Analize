import { useEffect, useState, useOptimistic, useTransition } from "react";
import { Building2, Download, Search, ChevronLeft, ChevronRight, Star } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";
import { useDebounce } from "@/hooks/useDebounce";
import type { Company } from "@/lib/types";

const SORT_OPTIONS = [
  { value: "last_analyzed", label: "Ultima analiza" },
  { value: "score_desc", label: "Scor (mare \u2192 mic)" },
  { value: "score_asc", label: "Scor (mic \u2192 mare)" },
  { value: "name_asc", label: "Nume A-Z" },
  { value: "name_desc", label: "Nume Z-A" },
  { value: "analysis_count", label: "Nr. analize" },
];

const PAGE_SIZE = 20;

export default function Companies() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);

  const sort = searchParams.get("sort") || "last_analyzed";

  // 10C M12.4: Debounced search — auto-search after 300ms typing pause
  const debouncedSearch = useDebounce(search, 300);

  const loadCompanies = (searchTerm?: string, pageNum = 0, sortParam = sort) => {
    setLoading(true);
    const fetchFn = showFavoritesOnly
      ? api.listFavorites()
      : api.listCompanies({ search: searchTerm, limit: PAGE_SIZE, offset: pageNum * PAGE_SIZE, sort: sortParam });
    fetchFn
      .then((res) => {
        setCompanies(res.companies);
        setTotal(res.total);
        logAction("Companies", "loaded", { total: res.total, sort: sortParam });
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

  // Reload when sort changes
  useEffect(() => {
    setPage(0);
    loadCompanies(debouncedSearch, 0, sort);
  }, [sort]);

  // Reload when favorites filter changes
  useEffect(() => {
    setPage(0);
    loadCompanies(debouncedSearch, 0);
  }, [showFavoritesOnly]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadCompanies(search, 0);
  };

  const [_isPending, startTransition] = useTransition();
  const [optimisticFavorites, setOptimisticFavorites] = useOptimistic(
    favorites,
    (_current: Record<string, boolean>, update: { id: string; value: boolean }) => ({
      ..._current,
      [update.id]: update.value,
    })
  );

  const toggleFavorite = (companyId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const currentVal = optimisticFavorites[companyId] ?? false;
    startTransition(async () => {
      setOptimisticFavorites({ id: companyId, value: !currentVal });
      try {
        const res = await api.toggleFavorite(companyId);
        setFavorites((prev) => ({ ...prev, [companyId]: res.is_favorite }));
        logAction("Companies", "toggleFavorite", { companyId, isFavorite: res.is_favorite });
      } catch {
        // Rollback via setFavorites — optimistic state reverts on next render
        setFavorites((prev) => ({ ...prev, [companyId]: currentVal }));
        toast("Eroare la actualizarea favoritelor", "error");
      }
    });
  };

  // Initialize favorites from company data (backend may return 0/1 integer or boolean)
  useEffect(() => {
    const favMap: Record<string, boolean> = {};
    companies.forEach((c) => {
      if (c.is_favorite !== undefined && c.is_favorite !== null) {
        favMap[c.id] = Boolean(c.is_favorite);
      }
    });
    setFavorites((prev) => ({ ...prev, ...favMap }));
  }, [companies]);

  // When showFavoritesOnly, companies already come from listFavorites endpoint
  const filteredCompanies = companies;

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const goToPage = (p: number) => {
    setPage(p);
    loadCompanies(search, p, sort);
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

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
          className={clsx(
            "flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors",
            showFavoritesOnly
              ? "border-yellow-500/50 bg-yellow-500/10 text-yellow-400"
              : "border-dark-border bg-dark-surface text-gray-400 hover:text-gray-300"
          )}
        >
          <Star className={clsx("w-4 h-4", showFavoritesOnly && "fill-yellow-400")} />
          Doar favorite
        </button>

        {/* Sort dropdown — persisted in URL */}
        <select
          value={sort}
          onChange={(e) => setSearchParams({ sort: e.target.value })}
          className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-accent-primary/50"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
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
            {filteredCompanies.map((company) => (
              <Link
                key={company.id}
                to={`/company/${company.id}`}
                className="card hover:border-accent-primary/30 transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <Building2 className="w-8 h-8 text-accent-secondary shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white truncate group-hover:text-accent-secondary">
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
                  <button
                    onClick={(e) => toggleFavorite(company.id, e)}
                    className="shrink-0 p-1 rounded hover:bg-dark-hover transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    aria-label={optimisticFavorites[company.id] ? "Elimina din favorite" : "Adauga la favorite"}
                    title={optimisticFavorites[company.id] ? "Sterge din favorite" : "Adauga la favorite"}
                  >
                    <Star
                      className={clsx(
                        "w-4 h-4 transition-colors",
                        optimisticFavorites[company.id]
                          ? "text-yellow-400 fill-yellow-400"
                          : "text-gray-600 hover:text-yellow-400"
                      )}
                    />
                  </button>
                  <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-accent-secondary shrink-0 mt-1" />
                </div>
              </Link>
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
