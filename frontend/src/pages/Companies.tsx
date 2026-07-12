import { useEffect, useState, useOptimistic, useTransition } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Download,
  Search,
  ChevronLeft,
  ChevronRight,
  Star,
  AlertCircle,
  RefreshCw,
  CheckSquare,
  Square,
  MinusSquare,
  ArrowLeftRight,
  Bell,
  X,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
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

const JUDETE_RO = [
  "Alba",
  "Arad",
  "Arges",
  "Bacau",
  "Bihor",
  "Bistrita-Nasaud",
  "Botosani",
  "Brasov",
  "Braila",
  "Buzau",
  "Caras-Severin",
  "Cluj",
  "Constanta",
  "Covasna",
  "Dambovita",
  "Dolj",
  "Galati",
  "Giurgiu",
  "Gorj",
  "Harghita",
  "Hunedoara",
  "Ialomita",
  "Iasi",
  "Ilfov",
  "Maramures",
  "Mehedinti",
  "Mures",
  "Neamt",
  "Olt",
  "Prahova",
  "Salaj",
  "Satu Mare",
  "Sibiu",
  "Suceava",
  "Teleorman",
  "Timis",
  "Tulcea",
  "Vaslui",
  "Valcea",
  "Vrancea",
  "Bucuresti",
];

const PAGE_SIZE = 20;

// A2: Badge colorat cu scor numeric pentru risc
const riskBadge = (score: number | null | undefined) => {
  if (score == null)
    return (
      <span className="inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full border bg-gray-700/40 text-gray-400 border-gray-600/30">
        N/A
      </span>
    );
  if (score >= 70)
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full border bg-green-500/20 text-green-400 border-green-500/30"
        aria-label={`Risc scăzut: ${score}/100`}
      >
        {score}/100
      </span>
    );
  if (score >= 40)
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full border bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
        aria-label={`Risc mediu: ${score}/100`}
      >
        {score}/100
      </span>
    );
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full border bg-red-500/20 text-red-400 border-red-500/30"
      aria-label={`Risc ridicat: ${score}/100`}
    >
      {score}/100
    </span>
  );
};

export default function Companies() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  // Bulk-select state (scoped to current page/view — cleared on filter/page change)
  const [selected, setSelected] = useState<Record<string, Company>>({});
  const [bulkMonitoring, setBulkMonitoring] = useState(false);

  const sort = searchParams.get("sort") || "last_analyzed";
  const filterCounty = searchParams.get("county") || "";
  const filterCaen = searchParams.get("caen") || "";
  const filterRiskScore = searchParams.get("risk_score") || "";

  // 10C M12.4: Debounced search — auto-search after 300ms typing pause
  const debouncedSearch = useDebounce(search, 300);

  // G3: TanStack Query pentru lista companii (inlocuieste useEffect + loadCompanies)
  const {
    data: companiesData,
    isLoading: loading,
    isError,
    refetch,
  } = useQuery({
    queryKey: [
      "companies",
      debouncedSearch,
      sort,
      page,
      filterCounty,
      filterCaen,
      filterRiskScore,
      showFavoritesOnly,
    ],
    queryFn: () =>
      showFavoritesOnly
        ? api.listFavorites()
        : api.listCompanies({
            search: debouncedSearch || undefined,
            limit: PAGE_SIZE,
            offset: page * PAGE_SIZE,
            sort,
            county: filterCounty || undefined,
            caen: filterCaen || undefined,
            risk_score: filterRiskScore || undefined,
          }),
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  });

  const companies: Company[] = companiesData?.companies ?? [];
  const total: number = companiesData?.total ?? 0;

  // Log on data change
  useEffect(() => {
    if (companiesData) {
      logAction("Companies", "loaded", { total: companiesData.total, sort });
    }
  }, [companiesData]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reset page to 0 + clear bulk selection when filters change
  useEffect(() => {
    setPage(0);
    setSelected({});
  }, [
    debouncedSearch,
    sort,
    filterCounty,
    filterCaen,
    filterRiskScore,
    showFavoritesOnly,
  ]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
  };

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  };

  const [_isPending, startTransition] = useTransition();
  const [optimisticFavorites, setOptimisticFavorites] = useOptimistic(
    favorites,
    (
      _current: Record<string, boolean>,
      update: { id: string; value: boolean },
    ) => ({
      ..._current,
      [update.id]: update.value,
    }),
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
        logAction("Companies", "toggleFavorite", {
          companyId,
          isFavorite: res.is_favorite,
        });
        // G3: Invalidate companies query for fresh data
        queryClient.invalidateQueries({ queryKey: ["companies"] });
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
    setSelected({});
    // G3: TanStack Query auto-refetches when page changes in queryKey
  };

  // ----- Bulk select (scoped to current page) -----
  const selectedList = Object.values(selected);
  const selectedCount = selectedList.length;
  const allCurrentSelected =
    filteredCompanies.length > 0 &&
    filteredCompanies.every((c) => selected[c.id]);
  const someCurrentSelected =
    filteredCompanies.some((c) => selected[c.id]) && !allCurrentSelected;

  const toggleSelect = (company: Company, e: React.MouseEvent) => {
    // Card is a <Link>; mirror the favorites button — cancel nav + stop bubbling
    e.preventDefault();
    e.stopPropagation();
    setSelected((prev) => {
      const next = { ...prev };
      if (next[company.id]) {
        delete next[company.id];
      } else {
        next[company.id] = company;
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelected((prev) => {
      const next = { ...prev };
      if (allCurrentSelected) {
        filteredCompanies.forEach((c) => delete next[c.id]);
      } else {
        filteredCompanies.forEach((c) => {
          next[c.id] = c;
        });
      }
      return next;
    });
  };

  const clearSelection = () => setSelected({});

  const compareSelected = () => {
    const cuis = selectedList
      .map((c) => c.cui)
      .filter((cui): cui is string => Boolean(cui));
    if (cuis.length < 2) {
      toast("Selecteaza cel putin 2 firme cu CUI pentru comparatie", "warning");
      return;
    }
    // CompareCompanies reads ?cui= (prefills the first). Pass all selected as
    // repeated params (max 5) for forward-compat; a comma list would be corrupted
    // there by .replace(/\D/g, "").
    const params = new URLSearchParams();
    cuis.slice(0, 5).forEach((cui) => params.append("cui", cui));
    logAction("Companies", "compareSelected", { count: cuis.length });
    clearSelection();
    navigate(`/compare?${params.toString()}`);
  };

  const monitorSelected = async () => {
    if (selectedList.length === 0 || bulkMonitoring) return;
    setBulkMonitoring(true);
    let ok = 0;
    let fail = 0;
    for (const company of selectedList) {
      try {
        await api.createMonitoring({ company_id: company.id });
        ok += 1;
      } catch {
        fail += 1;
      }
    }
    logAction("Companies", "monitorSelected", { ok, fail });
    if (ok > 0) {
      toast(
        fail > 0
          ? `${ok} firme adaugate la monitorizare, ${fail} esuate`
          : `${ok} firme adaugate la monitorizare`,
        fail > 0 ? "warning" : "success",
      );
    } else {
      toast("Eroare la adaugarea firmelor la monitorizare", "error");
    }
    setBulkMonitoring(false);
    clearSelection();
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
              : "border-dark-border bg-dark-surface text-gray-400 hover:text-gray-300",
          )}
        >
          <Star
            className={clsx("w-4 h-4", showFavoritesOnly && "fill-yellow-400")}
          />
          Doar favorite
        </button>

        {/* Sort dropdown — persisted in URL */}
        <select
          value={sort}
          onChange={(e) => updateFilter("sort", e.target.value)}
          className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-accent-primary/50"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Filtru judet */}
        <select
          value={filterCounty}
          onChange={(e) => updateFilter("county", e.target.value)}
          className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-accent-primary/50"
          title="Filtru judet"
        >
          <option value="">Toate judetele</option>
          {JUDETE_RO.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
        </select>

        {/* Filtru CAEN */}
        <input
          type="text"
          value={filterCaen}
          onChange={(e) => updateFilter("caen", e.target.value)}
          maxLength={4}
          placeholder="CAEN (ex: 6201)"
          className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-accent-primary/50 w-36"
          title="Filtru cod CAEN"
        />

        {/* Filtru scor risc */}
        <select
          value={filterRiskScore}
          onChange={(e) => updateFilter("risk_score", e.target.value)}
          className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-accent-primary/50"
          title="Filtru scor risc"
        >
          <option value="">Orice scor</option>
          <option value="Verde">Verde (70+)</option>
          <option value="Galben">Galben (40-69)</option>
          <option value="Rosu">Rosu (sub 40)</option>
        </select>

        {/* Sterge filtre avansate */}
        {(filterCounty || filterCaen || filterRiskScore) && (
          <button
            type="button"
            onClick={() => {
              const next = new URLSearchParams(searchParams);
              next.delete("county");
              next.delete("caen");
              next.delete("risk_score");
              setSearchParams(next);
            }}
            className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded border border-dark-border bg-dark-surface"
          >
            Sterge filtre
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
            onClick={() => {
              setSearch("");
              setPage(0);
              // G3: TanStack re-fetches automatically when search state changes
            }}
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
      ) : isError ? (
        <div className="card text-center py-16">
          <AlertCircle className="w-16 h-16 text-red-500/70 mx-auto mb-4" />
          <p className="text-gray-300 text-lg">
            Eroare la incarcarea companiilor
          </p>
          <p className="text-gray-500 text-sm mt-2">
            Serverul a raspuns cu o eroare. Verifica conexiunea si incearca din
            nou.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-dark-card text-gray-200 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Reincearca
          </button>
        </div>
      ) : companies.length === 0 ? (
        <div className="card text-center py-16">
          <Building2 className="w-16 h-16 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Nicio companie analizata inca</p>
          <p className="text-gray-600 text-sm mt-2">
            Companiile apar automat dupa prima analiza
          </p>
          <Link
            to="/new"
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-primary text-white hover:opacity-90 transition-opacity"
          >
            Porneste analiza
          </Link>
        </div>
      ) : (
        <>
          {/* Bulk action bar — sticky, shown when >=1 selected */}
          {selectedCount > 0 && (
            <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-accent-primary/40 bg-dark-card/95 px-4 py-3 shadow-lg backdrop-blur">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-white">
                  {selectedCount}{" "}
                  {selectedCount === 1 ? "firma selectata" : "firme selectate"}
                </span>
                <button
                  type="button"
                  onClick={clearSelection}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-3.5 h-3.5" /> Deselecteaza
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={compareSelected}
                  className="btn-secondary flex items-center gap-2 text-sm"
                >
                  <ArrowLeftRight className="w-4 h-4" /> Compara selectate
                </button>
                <button
                  type="button"
                  onClick={monitorSelected}
                  disabled={bulkMonitoring}
                  className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50"
                >
                  <Bell className="w-4 h-4" />
                  {bulkMonitoring ? "Se adauga..." : "Monitorizeaza selectate"}
                </button>
              </div>
            </div>
          )}

          {/* Select all (current page) */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              role="checkbox"
              aria-checked={
                allCurrentSelected
                  ? true
                  : someCurrentSelected
                    ? "mixed"
                    : false
              }
              onClick={toggleSelectAll}
              className="flex items-center gap-2 rounded px-1.5 py-1 text-xs text-gray-400 hover:text-gray-200 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
            >
              {allCurrentSelected ? (
                <CheckSquare className="w-4 h-4 text-accent-primary" />
              ) : someCurrentSelected ? (
                <MinusSquare className="w-4 h-4 text-accent-primary" />
              ) : (
                <Square className="w-4 h-4 text-gray-600" />
              )}
              {allCurrentSelected
                ? "Deselecteaza toate"
                : "Selecteaza toate (pagina curenta)"}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredCompanies.map((company) => (
              <Link
                key={company.id}
                to={`/company/${company.id}`}
                className={clsx(
                  "card transition-colors group",
                  selected[company.id]
                    ? "border-accent-primary/60 bg-accent-primary/5"
                    : "hover:border-accent-primary/30",
                )}
              >
                <div className="flex items-start gap-3">
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={Boolean(selected[company.id])}
                    onClick={(e) => toggleSelect(company, e)}
                    className="shrink-0 mt-0.5 p-1 rounded hover:bg-dark-hover transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    aria-label={
                      selected[company.id]
                        ? "Deselecteaza firma"
                        : "Selecteaza firma"
                    }
                    title={selected[company.id] ? "Deselecteaza" : "Selecteaza"}
                  >
                    {selected[company.id] ? (
                      <CheckSquare className="w-4 h-4 text-accent-primary" />
                    ) : (
                      <Square className="w-4 h-4 text-gray-600 group-hover:text-gray-400" />
                    )}
                  </button>
                  <Building2 className="w-8 h-8 text-accent-secondary shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white truncate group-hover:text-accent-secondary">
                      {company.name}
                    </h3>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-gray-500">
                      {company.cui && <span>CUI: {company.cui}</span>}
                      {company.caen_code && (
                        <span>CAEN: {company.caen_code}</span>
                      )}
                      {company.county && <span>{company.county}</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <p className="text-xs text-gray-600">
                        {company.analysis_count} analize |{" "}
                        {company.last_analyzed_at
                          ? `Ultima: ${new Date(
                              company.last_analyzed_at,
                            ).toLocaleDateString("ro-RO")}`
                          : "Neanalizata"}
                      </p>
                      {/* F6-1: Badge scor risc */}
                      {riskBadge(company.last_risk_score_numeric)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => toggleFavorite(company.id, e)}
                    className="shrink-0 p-1 rounded hover:bg-dark-hover transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    aria-label={
                      optimisticFavorites[company.id]
                        ? "Elimina din favorite"
                        : "Adauga la favorite"
                    }
                    title={
                      optimisticFavorites[company.id]
                        ? "Sterge din favorite"
                        : "Adauga la favorite"
                    }
                  >
                    <Star
                      className={clsx(
                        "w-4 h-4 transition-colors",
                        optimisticFavorites[company.id]
                          ? "text-yellow-400 fill-yellow-400"
                          : "text-gray-600 hover:text-yellow-400",
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
