import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Building2, AlertTriangle, Layers } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { getRiskBucket } from "@/lib/risk";
import { useToast } from "@/components/Toast";

// Etichete prietenoase (RO) pentru cheile de statistici returnate de backend.
// Fallback: humanize() pentru orice cheie necunoscuta.
const STAT_LABELS: Record<string, string> = {
  total_companies: "Companii in sector",
  avg_score: "Scor mediu",
  count_verde: "Risc scazut",
  count_galben: "Risc mediu",
  count_rosu: "Risc ridicat",
};

// Culoare valoare pentru cardurile de distributie a riscului.
const STAT_VALUE_COLOR: Record<string, string> = {
  count_verde: "text-risk-verde",
  count_galben: "text-risk-galben",
  count_rosu: "text-risk-rosu",
};

const humanize = (key: string): string =>
  key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

// Mapare scor -> culoare, via sursa unica de praguri (getRiskBucket, DRY #2 2026-07-14).
const scoreColor = (score: number): string => {
  const bucket = getRiskBucket(score);
  return bucket === "Verde"
    ? "text-risk-verde"
    : bucket === "Galben"
      ? "text-risk-galben"
      : "text-risk-rosu";
};

export default function SectorDashboard() {
  const { toast } = useToast();
  const [inputCode, setInputCode] = useState("");
  const [submittedCode, setSubmittedCode] = useState("");

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["sector-dashboard", submittedCode],
    queryFn: () => api.getSectorDashboard(submittedCode),
    enabled: submittedCode.length > 0,
    staleTime: 60_000,
  });

  // Afiseaza eroarea prin toast (Toast deduplica mesajele identice).
  useEffect(() => {
    if (isError) {
      const msg =
        error instanceof Error
          ? error.message
          : "Nu am putut incarca datele sectorului CAEN";
      toast(msg, "error");
    }
  }, [isError, error, toast]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = inputCode.trim();
    if (!/^\d{4}$/.test(trimmed)) {
      toast("Codul CAEN trebuie sa aiba exact 4 cifre (ex: 6201)", "warning");
      return;
    }
    // Acelasi cod retransmis -> refetch (queryKey nu se schimba).
    if (trimmed === submittedCode) {
      void refetch();
    } else {
      setSubmittedCode(trimmed);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Layers className="w-6 h-6 text-accent-secondary" />
          Dashboard Sector CAEN
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Agregat pe sector: scoruri de risc, distributie si firmele de top
          dintr-un cod CAEN.
        </p>
      </div>

      {/* Cautare cod CAEN */}
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            inputMode="numeric"
            maxLength={4}
            className="input-field w-full pl-9"
            placeholder="Cod CAEN (4 cifre, ex: 6201)"
            aria-label="Cod CAEN"
            value={inputCode}
            onChange={(e) => setInputCode(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={isFetching}
          className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <Search className="w-4 h-4" />
          {isFetching ? "Se cauta..." : "Cauta"}
        </button>
      </form>

      {/* Stari: initial / loading / error / date */}
      {!submittedCode ? (
        <div className="card text-center py-16">
          <Search className="w-16 h-16 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">
            Introdu un cod CAEN pentru a vedea sectorul
          </p>
          <p className="text-gray-600 text-sm mt-2">
            Ex: 6201 - Activitati de realizare a softului la comanda
          </p>
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-16 bg-dark-card rounded-xl" />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-dark-card rounded-xl" />
            ))}
          </div>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 bg-dark-card rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <div className="card text-center py-16">
          <AlertTriangle className="w-12 h-12 text-risk-rosu mx-auto mb-4" />
          <p className="text-gray-300 text-lg">
            Nu am putut incarca sectorul CAEN {submittedCode}
          </p>
          <p className="text-gray-500 text-sm mt-2">
            {error instanceof Error ? error.message : "Eroare necunoscuta"}
          </p>
          <button
            onClick={() => void refetch()}
            className="mt-4 px-4 py-2 rounded-lg bg-dark-surface border border-dark-border
                       text-gray-300 hover:bg-dark-hover transition-colors"
          >
            Reincearca
          </button>
        </div>
      ) : !data ? null : (
        <div className="space-y-6">
          {/* Descriere CAEN ca subtitlu */}
          <div className="card">
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              Cod CAEN {data.caen_code}
            </p>
            <p className="text-lg text-white mt-1">
              {data.caen_description || "Descriere indisponibila"}
            </p>
          </div>

          {/* Statistici sector */}
          {Object.keys(data.stats).length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {Object.entries(data.stats).map(([key, value]) => (
                <div key={key} className="card">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">
                    {STAT_LABELS[key] ?? humanize(key)}
                  </p>
                  <p
                    className={clsx(
                      "text-2xl font-bold mt-2",
                      STAT_VALUE_COLOR[key] ?? "text-white",
                    )}
                  >
                    {value === null ? "N/A" : value.toLocaleString("ro-RO")}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Top firme */}
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Top firme</h2>
            {data.top_companies.length === 0 ? (
              <div className="text-center py-12">
                <Building2 className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500">
                  Nicio firma cu scor in acest sector
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-dark-border">
                      <th className="pb-2 font-medium">Nume</th>
                      <th className="pb-2 font-medium">CUI</th>
                      <th className="pb-2 font-medium text-right">Scor</th>
                      <th className="pb-2 font-medium">Judet</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_companies.map((company) => (
                      <tr
                        key={company.id}
                        className="border-b border-dark-border/50 hover:bg-dark-hover transition-colors"
                      >
                        <td className="py-3 pr-3">
                          <Link
                            to={`/company/${company.id}`}
                            className="text-accent-secondary hover:text-accent-light font-medium"
                          >
                            {company.name}
                          </Link>
                        </td>
                        <td className="py-3 pr-3 text-gray-400 font-mono text-xs">
                          {company.cui}
                        </td>
                        <td
                          className={clsx(
                            "py-3 pr-3 text-right font-bold font-mono",
                            scoreColor(company.score),
                          )}
                        >
                          {company.score}
                        </td>
                        <td className="py-3 text-gray-400">
                          {company.county || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
