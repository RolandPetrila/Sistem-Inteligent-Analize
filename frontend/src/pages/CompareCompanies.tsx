import { useState, useEffect } from "react";
import { Plus, Trash2, Search, ArrowUpDown, CheckCircle, XCircle, Download, BookmarkPlus, FolderOpen } from "lucide-react";
import { validateCUI } from "@/lib/cui-validator";
import { logAction } from "@/lib/logger";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
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

function riskColor(score: number | undefined | null): string {
  // C25 fix: score 0 is valid (red), only undefined/null is gray
  if (score === undefined || score === null) return "text-gray-500";
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

interface CompareTemplate {
  id: string;
  name: string;
  cuis: string[];
  created_at: string;
}

export default function CompareCompanies() {
  const { toast } = useToast();
  const [cuis, setCuis] = useState<string[]>(["", ""]);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // F3-8: Templates
  const [templates, setTemplates] = useState<CompareTemplate[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [showSaveForm, setShowSaveForm] = useState(false);

  useEffect(() => {
    api.listCompareTemplates()
      .then((res) => setTemplates(res.templates || []))
      .catch(() => { /* templates optional */ });
  }, []);

  const loadTemplate = (tpl: CompareTemplate) => {
    setCuis(tpl.cuis.length >= 2 ? [...tpl.cuis] : [...tpl.cuis, ""]);
    setResult(null);
    setError(null);
    toast(`Template "${tpl.name}" incarcat`, "success");
    logAction("Compare", "loadTemplate", { templateId: tpl.id, name: tpl.name });
  };

  const handleSaveTemplate = async () => {
    const name = templateName.trim();
    const validCuis = cuis.filter((c) => c.trim().length >= 2);
    if (!name) { toast("Introdu un nume pentru template", "warning"); return; }
    if (validCuis.length < 2) { toast("Introdu cel putin 2 CUI-uri", "warning"); return; }
    try {
      await api.saveCompareTemplate(name, validCuis);
      const res = await api.listCompareTemplates();
      setTemplates(res.templates || []);
      setTemplateName("");
      setShowSaveForm(false);
      toast(`Template "${name}" salvat`, "success");
      logAction("Compare", "saveTemplate", { name, cuis: validCuis });
    } catch {
      toast("Eroare la salvarea template-ului", "error");
    }
  };

  const handleDeleteTemplate = async (tpl: CompareTemplate) => {
    try {
      await api.deleteCompareTemplate(tpl.id);
      setTemplates(templates.filter((t) => t.id !== tpl.id));
      toast(`Template "${tpl.name}" sters`, "success");
      logAction("Compare", "deleteTemplate", { templateId: tpl.id });
    } catch {
      toast("Eroare la stergerea template-ului", "error");
    }
  };

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
    logAction("Compare", "start", { cuis: valid });
    try {
      const data = await api.compareCompanies(valid) as CompareResult;
      setResult(data);
      logAction("Compare", "done", { companies: data.companies?.length });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Eroare necunoscuta";
      logAction("Compare", "failed", { error: msg });
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = () => {
    if (!result) return;
    const headers = ["Indicator", ...result.companies.map((c) => c.denumire || `CUI ${c.cui}`)];
    const rows: string[][] = [];
    for (const ind of indicators) {
      const row = [ind.label];
      for (const c of result.companies) {
        const val = c[ind.key];
        if (ind.format === "number" && typeof val === "number") {
          row.push(String(val));
        } else if (ind.format === "bool") {
          row.push(val ? "Da" : "Nu");
        } else {
          row.push(val !== undefined && val !== null ? String(val) : "N/A");
        }
      }
      rows.push(row);
    }
    const csvContent = [headers, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `comparatie_${result.companies.map((c) => c.cui).join("_")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    logAction("Compare", "exportCSV", { companies: result.companies.length });
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

      {/* F3-8: Template-uri salvate */}
      {(templates.length > 0 || true) && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-400 uppercase flex items-center gap-2">
              <FolderOpen className="w-4 h-4" /> Template-uri salvate
            </h2>
            <button
              onClick={() => setShowSaveForm(!showSaveForm)}
              className="btn-secondary flex items-center gap-1.5 text-xs"
            >
              <BookmarkPlus className="w-3.5 h-3.5" />
              Salveaza comparatia curenta
            </button>
          </div>

          {/* Form salvare */}
          {showSaveForm && (
            <div className="flex items-center gap-2 p-3 bg-dark-surface rounded-lg border border-dark-border">
              <input
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value.slice(0, 50))}
                onKeyDown={(e) => e.key === "Enter" && handleSaveTemplate()}
                placeholder="Nume template (ex: Producatori Cluj)"
                maxLength={50}
                className="flex-1 bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-accent-primary"
              />
              <button onClick={handleSaveTemplate} className="btn-primary text-sm px-3">Salveaza</button>
              <button onClick={() => setShowSaveForm(false)} className="text-gray-500 hover:text-white text-sm px-2">Anuleaza</button>
            </div>
          )}

          {/* Lista templates */}
          {templates.length === 0 ? (
            <p className="text-xs text-gray-600 italic">Niciun template salvat inca. Compara firme si salveaza comparatia pentru reutilizare.</p>
          ) : (
            <div className="space-y-1.5">
              {templates.map((tpl) => (
                <div key={tpl.id} className="flex items-center justify-between p-2.5 bg-dark-surface rounded-lg hover:bg-dark-hover transition-colors">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300 font-medium truncate">{tpl.name}</p>
                    <p className="text-xs text-gray-600">{tpl.cuis.join(", ")}</p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 ml-2">
                    <button
                      onClick={() => loadTemplate(tpl)}
                      className="btn-secondary text-xs px-2 py-1"
                    >
                      Incarca
                    </button>
                    <button
                      onClick={() => handleDeleteTemplate(tpl)}
                      className="p-1.5 text-gray-600 hover:text-red-400 transition-colors"
                      aria-label={`Sterge template ${tpl.name}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
            <div className="flex items-center gap-2">
              <button
                onClick={exportCSV}
                className="btn-secondary flex items-center gap-1.5 text-sm"
              >
                <Download className="w-3.5 h-3.5" /> Export CSV
              </button>
              {result.companies.length === 2 && (
                <button
                  onClick={async () => {
                    try {
                      logAction("Compare", "downloadPDF", { cui1: result.companies[0].cui, cui2: result.companies[1].cui });
                      const blob = await api.compareReport(result.companies[0].cui, result.companies[1].cui);
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `comparativ_${result.companies[0].cui}_${result.companies[1].cui}.pdf`;
                      a.click();
                      URL.revokeObjectURL(url);
                    } catch {
                      setError("Eroare la generarea PDF comparativ");
                    }
                  }}
                  className="btn-secondary flex items-center gap-1.5 text-sm"
                >
                  <Download className="w-3.5 h-3.5" /> PDF Comparativ
                </button>
              )}
            </div>
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
