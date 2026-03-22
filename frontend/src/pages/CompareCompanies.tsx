import { useState } from "react";
import { Plus, Trash2, Search, ArrowUpDown, CheckCircle, XCircle } from "lucide-react";
import { validateCUI } from "@/lib/cui-validator";
import clsx from "clsx";

interface CompanyResult {
  cui: string;
  denumire?: string;
  stare?: string;
  platitor_tva?: boolean;
  inactiv?: boolean;
  cifra_afaceri?: number;
  profit_brut?: number;
  profit_net?: number;
  angajati?: number;
  capitaluri?: number;
  caen_code?: string;
  caen_description?: string;
  scor_risc?: number;
  an_financiar?: number;
}

interface CompareResult {
  companies: CompanyResult[];
  best_per_indicator: Record<string, number>;
  an_financiar: number;
}

function formatNumber(val: number | undefined | null): string {
  if (val === undefined || val === null) return "N/A";
  return val.toLocaleString("ro-RO");
}

function riskColor(score: number | undefined): string {
  if (!score) return "text-gray-500";
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

export default function CompareCompanies() {
  const [cuis, setCuis] = useState<string[]>(["", ""]);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addCui = () => {
    if (cuis.length < 5) setCuis([...cuis, ""]);
  };

  const removeCui = (index: number) => {
    if (cuis.length > 2) setCuis(cuis.filter((_, i) => i !== index));
  };

  const updateCui = (index: number, value: string) => {
    const updated = [...cuis];
    updated[index] = value.replace(/\D/g, "").slice(0, 10);
    setCuis(updated);
  };

  const compare = async () => {
    const valid = cuis.filter((c) => c.trim().length >= 2);
    if (valid.length < 2) {
      setError("Introdu cel putin 2 CUI-uri valide");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cui_list: valid }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Eroare necunoscuta");
    } finally {
      setLoading(false);
    }
  };

  const indicators: { key: keyof CompanyResult; label: string; format?: "number" | "bool" }[] = [
    { key: "denumire", label: "Denumire" },
    { key: "caen_code", label: "CAEN" },
    { key: "stare", label: "Stare ANAF" },
    { key: "platitor_tva", label: "Platitor TVA", format: "bool" },
    { key: "cifra_afaceri", label: "Cifra Afaceri (RON)", format: "number" },
    { key: "profit_net", label: "Profit Net (RON)", format: "number" },
    { key: "angajati", label: "Nr. Angajati", format: "number" },
    { key: "capitaluri", label: "Capitaluri Proprii (RON)", format: "number" },
    { key: "scor_risc", label: "Scor Risc (/100)", format: "number" },
  ];

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Comparator Firme</h1>
        <p className="text-sm text-gray-500 mt-1">
          Introdu 2-5 CUI-uri pentru comparatie side-by-side (date ANAF + Bilant)
        </p>
      </div>

      {/* CUI inputs */}
      <div className="card space-y-3">
        {cuis.map((cui, i) => {
          const cuiResult = cui.length >= 2 ? validateCUI(cui) : null;
          return (
          <div key={i} className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-6">{i + 1}.</span>
            <div className="flex-1 relative">
              <input
                type="text"
                value={cui}
                onChange={(e) => updateCui(i, e.target.value)}
                placeholder="Introdu CUI (ex: 18189442)"
                className={clsx(
                  "w-full bg-dark-surface border rounded-lg px-3 py-2 pr-8",
                  "text-white text-sm placeholder-gray-600 focus:outline-none",
                  cuiResult === null ? "border-dark-border focus:border-accent-primary"
                    : cuiResult.valid ? "border-green-600 focus:border-green-500"
                    : "border-red-600 focus:border-red-500"
                )}
                onKeyDown={(e) => e.key === "Enter" && compare()}
              />
              {/* 10C M12.2: Real-time CUI validation indicator */}
              {cuiResult && (
                <span className="absolute right-2 top-1/2 -translate-y-1/2">
                  {cuiResult.valid
                    ? <CheckCircle className="w-4 h-4 text-green-400" />
                    : <XCircle className="w-4 h-4 text-red-400" />}
                </span>
              )}
            </div>
            {cuis.length > 2 && (
              <button onClick={() => removeCui(i)} className="p-1.5 text-gray-600 hover:text-red-400">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
          );
        })}

        <div className="flex items-center gap-3 pt-2">
          {cuis.length < 5 && (
            <button onClick={addCui} className="btn-secondary flex items-center gap-1.5 text-sm">
              <Plus className="w-3.5 h-3.5" /> Adauga CUI
            </button>
          )}
          <button
            onClick={compare}
            disabled={loading}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <Search className="w-3.5 h-3.5" />
            {loading ? "Se interogheaza ANAF..." : "Compara"}
          </button>
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </div>

      {/* Results table */}
      {result && (
        <div className="card overflow-x-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <ArrowUpDown className="w-5 h-5 text-accent-primary" />
              Comparatie — Date {result.an_financiar}
            </h2>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-border">
                <th className="text-left py-2 px-3 text-gray-500 text-xs uppercase">Indicator</th>
                {result.companies.map((c, i) => (
                  <th key={i} className="text-right py-2 px-3 text-gray-400 text-xs uppercase">
                    {c.denumire?.split(" ").slice(0, 3).join(" ") || `CUI ${c.cui}`}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {indicators.map((ind) => (
                <tr key={ind.key} className="border-b border-dark-border/50 hover:bg-dark-hover/30">
                  <td className="py-2.5 px-3 text-gray-400">{ind.label}</td>
                  {result.companies.map((c, i) => {
                    const val = c[ind.key];
                    const isBest = result.best_per_indicator[ind.key] === i;
                    const isRisk = ind.key === "scor_risc";

                    let display: string;
                    if (ind.format === "number" && typeof val === "number") {
                      display = formatNumber(val);
                    } else if (ind.format === "bool") {
                      display = val ? "Da" : "Nu";
                    } else {
                      display = val !== undefined && val !== null ? String(val) : "N/A";
                    }

                    return (
                      <td
                        key={i}
                        className={clsx(
                          "py-2.5 px-3 text-right font-mono text-sm",
                          isBest && !isRisk && "text-green-400 font-bold",
                          isRisk && riskColor(val as number),
                          !isBest && !isRisk && "text-gray-300"
                        )}
                      >
                        {display}
                        {isRisk && typeof val === "number" && (
                          <span className="ml-1 text-[10px]">
                            {val >= 70 ? "Verde" : val >= 40 ? "Galben" : "Rosu"}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
